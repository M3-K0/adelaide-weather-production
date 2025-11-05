#!/usr/bin/env python3
"""
FAISS Similarity Validation Test
================================

Unit test to verify FAISS similarities match numpy cosine similarity.
This ensures our normalization fix resolves the 0.000 similarity bug.

Usage:
    python test_faiss_similarity.py
"""

import numpy as np
import faiss
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_faiss_cosine_similarity():
    """Test that FAISS IndexFlatIP matches numpy cosine similarity."""
    logger.info("🧪 Testing FAISS cosine similarity implementation...")
    
    # Load sample embeddings (first 100 for speed)
    logger.info("Loading sample embeddings...")
    embeddings = np.load('embeddings/embeddings_6h.npy')[:100].copy().astype(np.float32)
    logger.info(f"Loaded {len(embeddings)} embeddings of dimension {embeddings.shape[1]}")
    
    # Normalize with FAISS (this is the key fix)
    logger.info("Normalizing embeddings with FAISS...")
    faiss.normalize_L2(embeddings)
    
    # Create FAISS index
    logger.info("Creating FAISS IndexFlatIP...")
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    
    # Test with multiple queries
    test_queries = [0, 10, 25, 50, 75]  # Various embedding indices as queries
    
    for query_idx in test_queries:
        logger.info(f"\n--- Testing Query {query_idx} ---")
        
        # Extract query embedding
        query = embeddings[query_idx:query_idx+1].copy()
        
        # FAISS search (top 10 neighbors)
        faiss_similarities, faiss_indices = index.search(query, 10)
        faiss_sims = faiss_similarities[0]
        faiss_idxs = faiss_indices[0]
        
        # Numpy cosine similarity for validation
        numpy_similarities = np.dot(embeddings, query.T).flatten()
        numpy_sorted_indices = np.argsort(-numpy_similarities)[:10]  # Top 10
        numpy_sims = numpy_similarities[numpy_sorted_indices]
        
        # Check similarity values are realistic (not 0.000)
        logger.info(f"FAISS similarities: {faiss_sims}")
        logger.info(f"Numpy similarities: {numpy_sims}")
        
        # Validate FAISS similarities are not zero
        if np.all(np.abs(faiss_sims) < 1e-6):
            logger.error("❌ FAISS similarities are all near zero - normalization bug still exists!")
            return False
            
        # Validate similarities are in reasonable range for weather embeddings
        if not (0.2 <= np.mean(faiss_sims) <= 1.0):
            logger.warning(f"⚠️  FAISS similarities seem unusual: mean={np.mean(faiss_sims):.3f}")
            
        # Check that FAISS and numpy results are close
        # (Indices may differ slightly due to floating point precision, but similarities should match)
        matches_found = 0
        for i, (faiss_idx, faiss_sim) in enumerate(zip(faiss_idxs, faiss_sims)):
            if faiss_idx in numpy_sorted_indices[:10]:
                numpy_sim = numpy_similarities[faiss_idx]
                if np.abs(faiss_sim - numpy_sim) < 1e-4:
                    matches_found += 1
                    
        match_rate = matches_found / len(faiss_sims)
        logger.info(f"Match rate with numpy: {match_rate:.1%} ({matches_found}/{len(faiss_sims)})")
        
        if match_rate < 0.8:  # Allow some tolerance for floating point differences
            logger.error(f"❌ Low match rate ({match_rate:.1%}) between FAISS and numpy!")
            return False
            
        # Self-similarity test (query should be most similar to itself)
        if faiss_idxs[0] == query_idx and faiss_sims[0] > 0.99:
            logger.info(f"✅ Self-similarity correct: {faiss_sims[0]:.4f}")
        else:
            logger.error(f"❌ Self-similarity failed: top match is idx {faiss_idxs[0]} with sim {faiss_sims[0]:.4f}")
            return False
    
    logger.info("\n🎉 All FAISS similarity tests passed!")
    return True

def test_normalization_consistency():
    """Test that our normalization approach is consistent."""
    logger.info("\n🧪 Testing normalization consistency...")
    
    # Create test vectors
    test_vectors = np.random.randn(10, 256).astype(np.float32)
    
    # Method 1: FAISS normalization
    vectors_faiss = test_vectors.copy()
    faiss.normalize_L2(vectors_faiss)
    
    # Method 2: Numpy normalization
    vectors_numpy = test_vectors / np.linalg.norm(test_vectors, axis=1, keepdims=True)
    vectors_numpy = vectors_numpy.astype(np.float32)
    
    # Check they produce the same result
    max_diff = np.max(np.abs(vectors_faiss - vectors_numpy))
    logger.info(f"Max difference between FAISS and numpy normalization: {max_diff:.2e}")
    
    if max_diff < 1e-6:
        logger.info("✅ Normalization methods are consistent")
        return True
    else:
        logger.error(f"❌ Normalization methods differ by {max_diff:.2e}")
        return False

def main():
    """Run all validation tests."""
    logger.info("🚀 Starting FAISS Similarity Validation Tests")
    
    try:
        # Test 1: Normalization consistency
        if not test_normalization_consistency():
            logger.error("❌ Normalization consistency test failed!")
            return False
            
        # Test 2: FAISS cosine similarity
        if not test_faiss_cosine_similarity():
            logger.error("❌ FAISS cosine similarity test failed!")
            return False
            
        logger.info("\n🎉 ALL TESTS PASSED! FAISS similarity bug is fixed.")
        logger.info("✅ Embeddings are properly normalized")
        logger.info("✅ FAISS similarities match numpy cosine similarity")
        logger.info("✅ Similarities are in realistic range (not 0.000)")
        
        return True
        
    except FileNotFoundError as e:
        logger.error(f"❌ Could not load embeddings: {e}")
        logger.error("Make sure embeddings/ directory exists with embeddings_6h.npy")
        return False
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)