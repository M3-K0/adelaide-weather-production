#!/usr/bin/env python3
"""
Create Test FAISS Indices for T-001 Implementation
==================================================

Creates minimal FAISS indices with realistic dimensions and sizes
to test the analog search integration without requiring full data pipeline.
"""

import numpy as np
import pandas as pd
import faiss
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_indices():
    """Create test FAISS indices and metadata for all horizons."""
    
    # Create directories
    indices_dir = Path("indices")
    embeddings_dir = Path("embeddings")
    indices_dir.mkdir(exist_ok=True)
    embeddings_dir.mkdir(exist_ok=True)
    
    # Configuration based on startup validation system
    horizons = [6, 12, 24, 48]
    embedding_dim = 256
    expected_sizes = {6: 6574, 12: 6574, 24: 13148, 48: 13148}
    
    for horizon in horizons:
        logger.info(f"Creating test data for {horizon}h horizon...")
        
        # Generate realistic number of embeddings
        n_embeddings = expected_sizes[horizon]
        
        # Generate random normalized embeddings
        np.random.seed(42 + horizon)  # Deterministic for testing
        embeddings = np.random.randn(n_embeddings, embedding_dim).astype(np.float32)
        faiss.normalize_L2(embeddings)  # L2 normalize for cosine similarity
        
        # Save embeddings
        embeddings_path = embeddings_dir / f"embeddings_{horizon}h.npy"
        np.save(embeddings_path, embeddings)
        logger.info(f"  Saved embeddings: {embeddings.shape}")
        
        # Create metadata DataFrame
        base_time = pd.Timestamp('2010-01-01')
        timestamps = [base_time + pd.Timedelta(hours=i*6) for i in range(n_embeddings)]
        
        metadata = pd.DataFrame({
            'init_time': timestamps,
            'horizon': horizon,
            'embedding_idx': range(n_embeddings)
        })
        
        # Save metadata
        metadata_path = embeddings_dir / f"metadata_{horizon}h.parquet"
        metadata.to_parquet(metadata_path)
        logger.info(f"  Saved metadata: {len(metadata)} records")
        
        # Create FlatIP index (baseline)
        flat_index = faiss.IndexFlatIP(embedding_dim)
        flat_index.add(embeddings)
        
        flat_path = indices_dir / f"faiss_{horizon}h_flatip.faiss"
        faiss.write_index(flat_index, str(flat_path))
        logger.info(f"  Created FlatIP index: {flat_index.ntotal} vectors")
        
        # Create IVF-PQ index (optimized) if we have enough data
        if n_embeddings >= 1000:
            nlist = min(256, n_embeddings // 39)  # Reasonable number of clusters
            m = 16  # Number of subquantizers
            nbits = 8  # Bits per subquantizer
            
            quantizer = faiss.IndexFlatIP(embedding_dim)
            ivfpq_index = faiss.IndexIVFPQ(quantizer, embedding_dim, nlist, m, nbits)
            
            # Train and add
            ivfpq_index.train(embeddings)
            ivfpq_index.add(embeddings)
            ivfpq_index.nprobe = min(32, nlist // 4)
            
            ivfpq_path = indices_dir / f"faiss_{horizon}h_ivfpq.faiss"
            faiss.write_index(ivfpq_index, str(ivfpq_path))
            logger.info(f"  Created IVF-PQ index: {ivfpq_index.ntotal} vectors, nlist={nlist}")
        
        logger.info(f"✅ Completed {horizon}h horizon")
    
    logger.info("🎉 All test indices created successfully!")

if __name__ == "__main__":
    create_test_indices()