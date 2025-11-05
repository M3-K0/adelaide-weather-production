#!/usr/bin/env python3
"""
Adelaide Weather Forecasting: FAISS Index Construction
====================================================

Builds FAISS indices for fast similarity search of weather embeddings.
Creates both baseline (FlatIP) and optimized (IVF-PQ) indices per horizon.

Usage:
    python build_indices.py --embeddings embeddings/ --output indices/
"""

import os
import sys
import argparse
import time
import json
from pathlib import Path
import numpy as np
import pandas as pd
import faiss
import logging
from typing import Dict, List, Tuple, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FAISSIndexBuilder:
    """Build FAISS indices for weather embedding retrieval."""
    
    def __init__(self, embeddings_dir: str):
        """Initialize FAISS index builder.
        
        Args:
            embeddings_dir: Directory containing embedding files
        """
        self.embeddings_dir = Path(embeddings_dir)
        self.lead_times = [6, 12, 24, 48]
        self.dimension = 256  # CNN encoder output dimension
        
        logger.info(f"Initializing FAISS index builder")
        logger.info(f"Embeddings directory: {self.embeddings_dir}")
        
    def load_embeddings(self, lead_time: int) -> Tuple[np.ndarray, pd.DataFrame]:
        """Load embeddings and metadata for a specific horizon.
        
        Args:
            lead_time: Forecast lead time in hours
            
        Returns:
            embeddings: (N, 256) L2-normalized embeddings
            metadata: DataFrame with timestamp and target info
        """
        # Load embeddings
        emb_path = self.embeddings_dir / f"embeddings_{lead_time}h.npy"
        if not emb_path.exists():
            raise FileNotFoundError(f"Embeddings not found: {emb_path}")
            
        embeddings = np.load(emb_path).astype(np.float32)
        logger.info(f"Loaded embeddings: {embeddings.shape}")
        
        # Load metadata
        meta_path = self.embeddings_dir / f"metadata_{lead_time}h.parquet"
        if not meta_path.exists():
            raise FileNotFoundError(f"Metadata not found: {meta_path}")
            
        metadata = pd.read_parquet(meta_path)
        logger.info(f"Loaded metadata: {len(metadata)} records")
        
        # Verify dimensions match
        if len(embeddings) != len(metadata):
            raise ValueError(f"Dimension mismatch: {len(embeddings)} embeddings vs {len(metadata)} metadata")
            
        # Ensure L2 normalization for cosine similarity using FAISS
        norms = np.linalg.norm(embeddings, axis=1)
        if not np.allclose(norms, 1.0, atol=1e-6):
            logger.warning("Embeddings not L2-normalized, normalizing with FAISS...")
            # Convert to float32 for FAISS compatibility
            embeddings = embeddings.astype(np.float32)
            faiss.normalize_L2(embeddings)
        else:
            logger.info("Embeddings already L2-normalized")
            embeddings = embeddings.astype(np.float32)
            
        return embeddings, metadata
        
    def create_train_test_split(self, metadata: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Create train/test split based on year for temporal consistency.
        
        Args:
            metadata: DataFrame with init_time column
            
        Returns:
            train_indices: Indices for training set (2010-2018)
            test_indices: Indices for test set (2019-2020)
        """
        # Convert init_time to datetime if needed
        if not pd.api.types.is_datetime64_any_dtype(metadata['init_time']):
            metadata['init_time'] = pd.to_datetime(metadata['init_time'])
            
        # Extract years
        years = metadata['init_time'].dt.year
        
        # Split by year
        train_mask = years <= 2018
        test_mask = years >= 2019
        
        train_indices = np.where(train_mask)[0]
        test_indices = np.where(test_mask)[0]
        
        logger.info(f"Train set: {len(train_indices)} samples (2010-2018)")
        logger.info(f"Test set: {len(test_indices)} samples (2019-2020)")
        
        return train_indices, test_indices
        
    def build_flat_index(self, embeddings: np.ndarray, train_indices: np.ndarray) -> faiss.IndexFlatIP:
        """Build baseline flat index for exact search.
        
        Args:
            embeddings: All embeddings
            train_indices: Indices for training set
            
        Returns:
            Trained flat index
        """
        logger.info("Building FlatIP index (baseline)...")
        
        # Create index
        index = faiss.IndexFlatIP(self.dimension)
        
        # Add training embeddings with explicit FAISS normalization
        train_embeddings = embeddings[train_indices].copy().astype(np.float32)
        faiss.normalize_L2(train_embeddings)  # Ensure FAISS normalization
        index.add(train_embeddings)
        
        logger.info(f"✅ FlatIP index built with {index.ntotal} vectors")
        return index
        
    def build_ivf_pq_index(self, embeddings: np.ndarray, train_indices: np.ndarray) -> faiss.IndexIVFPQ:
        """Build IVF-PQ index for fast approximate search.
        
        Args:
            embeddings: All embeddings
            train_indices: Indices for training set
            
        Returns:
            Trained IVF-PQ index
        """
        logger.info("Building IVF-PQ index (optimized)...")
        
        train_embeddings = embeddings[train_indices].copy().astype(np.float32)
        faiss.normalize_L2(train_embeddings)  # Ensure FAISS normalization
        n_vectors = len(train_embeddings)
        
        # Choose parameters based on data size
        if n_vectors < 10000:
            nlist = 256
            m = 16
        elif n_vectors < 100000:
            nlist = 512
            m = 32
        else:
            nlist = 1024
            m = 32
            
        nbits = 8
        
        logger.info(f"IVF-PQ parameters: nlist={nlist}, m={m}, nbits={nbits}")
        
        # Create quantizer
        quantizer = faiss.IndexFlatIP(self.dimension)
        
        # Create IVF-PQ index
        index = faiss.IndexIVFPQ(quantizer, self.dimension, nlist, m, nbits)
        
        # Train the index
        logger.info("Training IVF-PQ index...")
        index.train(train_embeddings)
        
        # Add vectors
        index.add(train_embeddings)
        
        # Set search parameters
        index.nprobe = min(32, nlist // 4)  # Reasonable default
        
        logger.info(f"✅ IVF-PQ index built with {index.ntotal} vectors")
        logger.info(f"Search parameters: nprobe={index.nprobe}")
        
        return index
        
    def benchmark_index(self, index: faiss.Index, embeddings: np.ndarray, 
                       test_indices: np.ndarray, k: int = 100) -> Dict:
        """Benchmark index performance.
        
        Args:
            index: FAISS index to benchmark
            embeddings: All embeddings
            test_indices: Test set indices
            k: Number of neighbors to retrieve
            
        Returns:
            Performance metrics
        """
        logger.info(f"Benchmarking index with k={k}...")
        
        # Sample test queries (limit for speed)
        n_queries = min(100, len(test_indices))
        query_indices = np.random.choice(test_indices, n_queries, replace=False)
        query_embeddings = embeddings[query_indices]
        
        # Measure search time
        start_time = time.time()
        distances, indices = index.search(query_embeddings, k)
        search_time = time.time() - start_time
        
        # Calculate metrics
        latency_per_query = search_time / n_queries * 1000  # ms
        throughput = n_queries / search_time  # queries/sec
        
        # Check for valid results
        valid_results = np.sum(indices >= 0) / (n_queries * k)
        
        metrics = {
            'n_queries': n_queries,
            'k': k,
            'total_time_ms': search_time * 1000,
            'latency_per_query_ms': latency_per_query,
            'throughput_qps': throughput,
            'valid_results_ratio': valid_results,
            'index_type': index.__class__.__name__
        }
        
        logger.info(f"Latency: {latency_per_query:.2f}ms per query")
        logger.info(f"Throughput: {throughput:.1f} queries/sec")
        logger.info(f"Valid results: {valid_results:.1%}")
        
        return metrics
        
    def save_index(self, index: faiss.Index, output_dir: Path, 
                  lead_time: int, index_type: str):
        """Save FAISS index to disk.
        
        Args:
            index: FAISS index to save
            output_dir: Output directory
            lead_time: Forecast lead time
            index_type: Type of index (flatip, ivfpq)
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        index_path = output_dir / f"faiss_{lead_time}h_{index_type}.faiss"
        faiss.write_index(index, str(index_path))
        logger.info(f"💾 Saved {index_type} index to {index_path}")
        
    def build_indices_for_horizon(self, lead_time: int, output_dir: Path) -> Dict:
        """Build all indices for a specific forecast horizon.
        
        Args:
            lead_time: Forecast lead time in hours
            output_dir: Output directory for indices
            
        Returns:
            Performance benchmarks
        """
        logger.info(f"🚀 Building indices for {lead_time}h horizon")
        
        # Load data
        embeddings, metadata = self.load_embeddings(lead_time)
        train_indices, test_indices = self.create_train_test_split(metadata)
        
        benchmarks = {}
        
        # Build FlatIP index (baseline)
        flat_index = self.build_flat_index(embeddings, train_indices)
        self.save_index(flat_index, output_dir, lead_time, 'flatip')
        benchmarks['flatip'] = self.benchmark_index(flat_index, embeddings, test_indices)
        
        # Build IVF-PQ index (optimized)
        ivfpq_index = self.build_ivf_pq_index(embeddings, train_indices)
        self.save_index(ivfpq_index, output_dir, lead_time, 'ivfpq')
        benchmarks['ivfpq'] = self.benchmark_index(ivfpq_index, embeddings, test_indices)
        
        # Calculate recall (IVF-PQ vs FlatIP)
        logger.info("Calculating recall@K...")
        
        # Sample queries for recall calculation
        n_queries = min(50, len(test_indices))
        query_indices = np.random.choice(test_indices, n_queries, replace=False)
        query_embeddings = embeddings[query_indices]
        
        # Get ground truth from FlatIP
        k = 100
        _, flat_neighbors = flat_index.search(query_embeddings, k)
        _, ivfpq_neighbors = ivfpq_index.search(query_embeddings, k)
        
        # Calculate recall@k
        recall_scores = []
        for i in range(n_queries):
            flat_set = set(flat_neighbors[i])
            ivfpq_set = set(ivfpq_neighbors[i])
            recall = len(flat_set.intersection(ivfpq_set)) / k
            recall_scores.append(recall)
            
        recall_at_k = np.mean(recall_scores)
        benchmarks['ivfpq']['recall_at_100'] = recall_at_k
        
        logger.info(f"Recall@{k}: {recall_at_k:.3f}")
        logger.info(f"✅ {lead_time}h indices completed")
        
        return benchmarks
        
    def build_all_indices(self, output_dir: str):
        """Build indices for all forecast horizons.
        
        Args:
            output_dir: Output directory for indices
        """
        output_path = Path(output_dir)
        
        logger.info(f"🎯 Building FAISS indices for all horizons")
        logger.info(f"Output directory: {output_path}")
        
        all_benchmarks = {}
        total_start = time.time()
        
        for lead_time in self.lead_times:
            horizon_start = time.time()
            
            benchmarks = self.build_indices_for_horizon(lead_time, output_path)
            all_benchmarks[f'{lead_time}h'] = benchmarks
            
            horizon_time = time.time() - horizon_start
            logger.info(f"⏱️ {lead_time}h horizon completed in {horizon_time:.1f}s")
            
        total_time = time.time() - total_start
        logger.info(f"🎉 All indices built in {total_time:.1f}s")
        
        # Save benchmarks
        benchmark_path = output_path / "index_benchmarks.json"
        with open(benchmark_path, 'w') as f:
            json.dump(all_benchmarks, f, indent=2)
        logger.info(f"📊 Benchmarks saved to {benchmark_path}")

def main():
    parser = argparse.ArgumentParser(description='Build FAISS indices for weather forecasting')
    parser.add_argument('--embeddings', default='embeddings/',
                       help='Directory containing embeddings')
    parser.add_argument('--output', default='indices/',
                       help='Output directory for indices')
    
    args = parser.parse_args()
    
    # Initialize builder
    builder = FAISSIndexBuilder(embeddings_dir=args.embeddings)
    
    # Build all indices
    builder.build_all_indices(output_dir=args.output)
    
    logger.info("🎉 Index building completed successfully!")

if __name__ == "__main__":
    main()