#!/usr/bin/env python3
"""
Debug FAISS Similarities
========================

This script directly tests FAISS similarity values to understand
why the distance calculation is failing.
"""

import asyncio
import numpy as np
import sys
from pathlib import Path
import logging

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from api.services.analog_search import AnalogSearchService, AnalogSearchConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def debug_similarities():
    """Debug FAISS similarity values directly."""
    logger.info("🔍 Debugging FAISS Similarity Values")
    
    # Initialize service
    config = AnalogSearchConfig()
    service = AnalogSearchService(config)
    await service.initialize()
    
    try:
        # Get a forecaster from the pool
        forecaster = await service.pool.acquire()
        if not forecaster:
            logger.error("Failed to acquire forecaster")
            return
        
        try:
            # Test with 24h horizon
            horizon = 24
            faiss_index = forecaster.indices[horizon]
            
            logger.info(f"FAISS Index Info:")
            logger.info(f"  Index type: {type(faiss_index).__name__}")
            logger.info(f"  Dimensions: {faiss_index.d}")
            logger.info(f"  Total vectors: {faiss_index.ntotal}")
            
            # Generate a simple test embedding
            test_embedding = np.random.randn(1, 256).astype(np.float32)
            
            # Test without normalization first
            logger.info(f"\n1. Raw embedding search (no normalization):")
            raw_similarities, raw_indices = faiss_index.search(test_embedding, 5)
            logger.info(f"   Similarities: {raw_similarities[0]}")
            logger.info(f"   Range: {np.min(raw_similarities)} to {np.max(raw_similarities)}")
            
            # Test with L2 normalization
            import faiss
            normalized_embedding = test_embedding.copy()
            faiss.normalize_L2(normalized_embedding)
            
            logger.info(f"\n2. Normalized embedding search:")
            norm_similarities, norm_indices = faiss_index.search(normalized_embedding, 5)
            logger.info(f"   Similarities: {norm_similarities[0]}")
            logger.info(f"   Range: {np.min(norm_similarities)} to {np.max(norm_similarities)}")
            
            # Test distance conversion formulas
            logger.info(f"\n3. Distance conversion tests:")
            sims = norm_similarities[0]
            
            # Current formula
            current_distances = 2.0 - 2.0 * sims
            logger.info(f"   Current formula (2 - 2*sim): {current_distances}")
            
            # Alternative formulas
            sqrt_distances = np.sqrt(2.0 - 2.0 * sims)
            logger.info(f"   Sqrt formula: {sqrt_distances}")
            
            inv_distances = 1.0 - sims
            logger.info(f"   Simple inversion (1 - sim): {inv_distances}")
            
            # Check if similarities are already cosine similarities (should be in [-1, 1])
            logger.info(f"\n4. Similarity Analysis:")
            logger.info(f"   Mean similarity: {np.mean(sims):.6f}")
            logger.info(f"   Std similarity: {np.std(sims):.6f}")
            logger.info(f"   In range [0,1]? {np.all(sims >= 0) and np.all(sims <= 1)}")
            logger.info(f"   In range [-1,1]? {np.all(sims >= -1) and np.all(sims <= 1)}")
            
            # Get actual embedding from index to compare
            logger.info(f"\n5. Index embedding analysis:")
            # Get the first stored embedding for comparison
            stored_embeddings = forecaster.embeddings[horizon][:5]
            
            logger.info(f"   Stored embeddings shape: {stored_embeddings.shape}")
            logger.info(f"   Embedding norms: {np.linalg.norm(stored_embeddings, axis=1)}")
            
            # Manual cosine similarity calculation
            manual_cosine = np.dot(stored_embeddings, normalized_embedding.T).flatten()
            logger.info(f"   Manual cosine similarities: {manual_cosine}")
            logger.info(f"   Match with FAISS?: {np.allclose(manual_cosine, sims, atol=1e-5)}")
            
        finally:
            await service.pool.release(forecaster)
        
    finally:
        await service.shutdown()

if __name__ == "__main__":
    asyncio.run(debug_similarities())