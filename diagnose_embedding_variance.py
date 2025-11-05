#!/usr/bin/env python3
"""
FAISS Embedding Variance Diagnostic Tool
========================================

Diagnoses the root cause of low similarity variance in FAISS indices.
This tool identifies whether the issue is in:
1. Embedding generation process
2. Data preprocessing
3. Model architecture
4. Index construction

Expected Outcome: Similarity variance stddev > 0.01 for healthy indices
"""

import numpy as np
import pandas as pd
import faiss
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_embedding_diversity(embeddings, horizon, sample_size=1000):
    """Analyze embedding diversity and similarity distribution."""
    logger.info(f"\n🔍 Analyzing {horizon} embedding diversity...")
    
    # Sample for performance
    n_samples = min(sample_size, len(embeddings))
    indices = np.random.choice(len(embeddings), n_samples, replace=False)
    sample_embeddings = embeddings[indices].copy().astype(np.float32)
    
    # Normalize embeddings
    faiss.normalize_L2(sample_embeddings)
    
    # Raw embedding statistics (before normalization)
    raw_stats = {
        'mean': np.mean(embeddings),
        'std': np.std(embeddings),
        'min': np.min(embeddings),
        'max': np.max(embeddings),
        'l2_norms_mean': np.mean(np.linalg.norm(embeddings, axis=1)),
        'l2_norms_std': np.std(np.linalg.norm(embeddings, axis=1))
    }
    
    logger.info(f"Raw embedding statistics:")
    logger.info(f"  Mean: {raw_stats['mean']:.6f}")
    logger.info(f"  Std: {raw_stats['std']:.6f}")
    logger.info(f"  L2 norm mean: {raw_stats['l2_norms_mean']:.6f}")
    logger.info(f"  L2 norm std: {raw_stats['l2_norms_std']:.6f}")
    
    # Pairwise similarity analysis
    similarities = np.dot(sample_embeddings, sample_embeddings.T)
    
    # Remove diagonal (self-similarities)
    mask = ~np.eye(n_samples, dtype=bool)
    off_diagonal_sims = similarities[mask]
    
    similarity_stats = {
        'mean': np.mean(off_diagonal_sims),
        'std': np.std(off_diagonal_sims),
        'min': np.min(off_diagonal_sims),
        'max': np.max(off_diagonal_sims),
        'range': np.max(off_diagonal_sims) - np.min(off_diagonal_sims),
        'percentiles': np.percentile(off_diagonal_sims, [5, 25, 50, 75, 95])
    }
    
    logger.info(f"Similarity statistics (n={n_samples}):")
    logger.info(f"  Mean: {similarity_stats['mean']:.6f}")
    logger.info(f"  Std: {similarity_stats['std']:.6f}")
    logger.info(f"  Range: {similarity_stats['range']:.6f}")
    logger.info(f"  Percentiles [5,25,50,75,95]: {similarity_stats['percentiles']}")
    
    # Variance health check
    variance_threshold = 0.01
    is_healthy = similarity_stats['std'] > variance_threshold
    
    logger.info(f"Variance health: {'✅ HEALTHY' if is_healthy else '❌ DEGENERATE'}")
    logger.info(f"  Threshold: {variance_threshold}")
    logger.info(f"  Actual: {similarity_stats['std']:.6f}")
    
    return raw_stats, similarity_stats, is_healthy

def analyze_temporal_patterns(metadata, embeddings, horizon):
    """Analyze if temporal patterns affect embedding diversity."""
    logger.info(f"\n📅 Analyzing temporal patterns for {horizon}...")
    
    # Ensure datetime
    if not pd.api.types.is_datetime64_any_dtype(metadata['init_time']):
        metadata['init_time'] = pd.to_datetime(metadata['init_time'])
    
    # Group by month and year
    metadata['year'] = metadata['init_time'].dt.year
    metadata['month'] = metadata['init_time'].dt.month
    
    # Sample embeddings by time periods
    sample_size = 100
    periods = [
        ('2010', metadata['year'] == 2010),
        ('2015', metadata['year'] == 2015),
        ('2018', metadata['year'] == 2018),
        ('2020', metadata['year'] == 2020)
    ]
    
    temporal_variance = {}
    
    for period_name, mask in periods:
        if mask.sum() < sample_size:
            continue
            
        indices = np.where(mask)[0]
        sample_indices = np.random.choice(indices, min(sample_size, len(indices)), replace=False)
        sample_embeddings = embeddings[sample_indices].copy().astype(np.float32)
        
        # Normalize and compute similarities
        faiss.normalize_L2(sample_embeddings)
        similarities = np.dot(sample_embeddings, sample_embeddings.T)
        
        # Remove diagonal
        mask_diag = ~np.eye(len(sample_embeddings), dtype=bool)
        off_diagonal_sims = similarities[mask_diag]
        
        temporal_variance[period_name] = {
            'mean_similarity': np.mean(off_diagonal_sims),
            'std_similarity': np.std(off_diagonal_sims),
            'sample_count': len(sample_embeddings)
        }
        
        logger.info(f"  {period_name}: mean={temporal_variance[period_name]['mean_similarity']:.4f}, "
                   f"std={temporal_variance[period_name]['std_similarity']:.4f}")
    
    return temporal_variance

def analyze_spatial_patterns(metadata, embeddings, horizon):
    """Analyze if spatial patterns affect embedding diversity."""
    logger.info(f"\n🌍 Analyzing spatial patterns for {horizon}...")
    
    # Group by latitude/longitude regions
    lat_bins = pd.cut(metadata['lat'], bins=3, labels=['South', 'Central', 'North'])
    lon_bins = pd.cut(metadata['lon'], bins=3, labels=['West', 'Central', 'East'])
    
    spatial_variance = {}
    sample_size = 100
    
    for lat_region in ['South', 'Central', 'North']:
        for lon_region in ['West', 'Central', 'East']:
            mask = (lat_bins == lat_region) & (lon_bins == lon_region)
            
            if mask.sum() < sample_size:
                continue
                
            indices = np.where(mask)[0]
            sample_indices = np.random.choice(indices, min(sample_size, len(indices)), replace=False)
            sample_embeddings = embeddings[sample_indices].copy().astype(np.float32)
            
            # Normalize and compute similarities
            faiss.normalize_L2(sample_embeddings)
            similarities = np.dot(sample_embeddings, sample_embeddings.T)
            
            # Remove diagonal
            mask_diag = ~np.eye(len(sample_embeddings), dtype=bool)
            off_diagonal_sims = similarities[mask_diag]
            
            region_name = f"{lat_region}-{lon_region}"
            spatial_variance[region_name] = {
                'mean_similarity': np.mean(off_diagonal_sims),
                'std_similarity': np.std(off_diagonal_sims),
                'sample_count': len(sample_embeddings)
            }
            
            logger.info(f"  {region_name}: mean={spatial_variance[region_name]['mean_similarity']:.4f}, "
                       f"std={spatial_variance[region_name]['std_similarity']:.4f}")
    
    return spatial_variance

def check_faiss_index_variance(horizon, index_type='flatip'):
    """Check actual FAISS index similarity variance."""
    logger.info(f"\n🔍 Checking FAISS index variance for {horizon}h {index_type}...")
    
    # Load index
    index_path = Path(f"indices/faiss_{horizon}h_{index_type}.faiss")
    if not index_path.exists():
        logger.error(f"Index not found: {index_path}")
        return None
    
    index = faiss.read_index(str(index_path))
    
    # Load training embeddings for queries
    embeddings = np.load(f"embeddings/embeddings_{horizon}h.npy").astype(np.float32)
    metadata = pd.read_parquet(f"embeddings/metadata_{horizon}h.parquet")
    
    # Get training indices (pre-2019)
    if not pd.api.types.is_datetime64_any_dtype(metadata['init_time']):
        metadata['init_time'] = pd.to_datetime(metadata['init_time'])
    
    years = metadata['init_time'].dt.year
    train_mask = years <= 2018
    train_indices = np.where(train_mask)[0]
    
    # Sample queries from training set
    n_queries = min(50, len(train_indices))
    query_indices = np.random.choice(train_indices, n_queries, replace=False)
    query_embeddings = embeddings[query_indices]
    
    # Normalize queries
    faiss.normalize_L2(query_embeddings)
    
    # Search index
    similarities, indices = index.search(query_embeddings, 100)
    
    # Analyze similarity variance
    all_similarities = similarities.flatten()
    all_similarities = all_similarities[all_similarities > 0]  # Remove any zeros
    
    variance_stats = {
        'mean': np.mean(all_similarities),
        'std': np.std(all_similarities),
        'min': np.min(all_similarities),
        'max': np.max(all_similarities),
        'range': np.max(all_similarities) - np.min(all_similarities),
        'percentiles': np.percentile(all_similarities, [5, 25, 50, 75, 95])
    }
    
    logger.info(f"FAISS index similarity statistics:")
    logger.info(f"  Mean: {variance_stats['mean']:.6f}")
    logger.info(f"  Std: {variance_stats['std']:.6f}")
    logger.info(f"  Range: {variance_stats['range']:.6f}")
    logger.info(f"  Percentiles [5,25,50,75,95]: {variance_stats['percentiles']}")
    
    # Check if degenerate
    variance_threshold = 0.01
    is_healthy = variance_stats['std'] > variance_threshold
    
    logger.info(f"Index health: {'✅ HEALTHY' if is_healthy else '❌ DEGENERATE'}")
    
    return variance_stats, is_healthy

def investigate_embedding_generation():
    """Investigate the embedding generation process."""
    logger.info(f"\n🧬 Investigating embedding generation process...")
    
    # Check if we can find the model or generation script
    model_paths = [
        "models/best_model.pt",
        "models/cnn_encoder.py",
        "scripts/generate_embeddings.py"
    ]
    
    found_files = []
    for path in model_paths:
        if Path(path).exists():
            found_files.append(path)
            logger.info(f"  Found: {path}")
    
    if not found_files:
        logger.warning("  No model or generation files found for analysis")
    
    # Check embedding file creation dates
    embedding_files = list(Path("embeddings").glob("embeddings_*.npy"))
    if embedding_files:
        logger.info("  Embedding file timestamps:")
        for emb_file in embedding_files:
            mtime = datetime.fromtimestamp(emb_file.stat().st_mtime)
            logger.info(f"    {emb_file.name}: {mtime}")

def main():
    """Run comprehensive embedding variance diagnosis."""
    logger.info("🚀 Starting FAISS Embedding Variance Diagnosis")
    logger.info("=" * 60)
    
    results = {}
    
    # Check all horizons
    horizons = ['6h', '12h', '24h', '48h']
    
    for horizon in horizons:
        logger.info(f"\n{'='*20} {horizon.upper()} ANALYSIS {'='*20}")
        
        try:
            # Load data
            embeddings = np.load(f"embeddings/embeddings_{horizon}.npy")
            metadata = pd.read_parquet(f"embeddings/metadata_{horizon}.parquet")
            
            # 1. Embedding diversity analysis
            raw_stats, sim_stats, is_healthy = analyze_embedding_diversity(embeddings, horizon)
            
            # 2. Temporal pattern analysis
            temporal_stats = analyze_temporal_patterns(metadata, embeddings, horizon)
            
            # 3. Spatial pattern analysis  
            spatial_stats = analyze_spatial_patterns(metadata, embeddings, horizon)
            
            # 4. FAISS index variance check
            index_stats, index_healthy = check_faiss_index_variance(horizon)
            
            results[horizon] = {
                'embedding_healthy': is_healthy,
                'index_healthy': index_healthy,
                'similarity_std': sim_stats['std'],
                'index_similarity_std': index_stats['std'] if index_stats else 0,
                'raw_embedding_std': raw_stats['std'],
                'temporal_variance': temporal_stats,
                'spatial_variance': spatial_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze {horizon}: {e}")
            results[horizon] = {'error': str(e)}
    
    # 5. Investigate embedding generation
    investigate_embedding_generation()
    
    # Generate summary report
    logger.info(f"\n{'='*20} DIAGNOSIS SUMMARY {'='*20}")
    
    healthy_count = 0
    total_count = 0
    
    for horizon, result in results.items():
        if 'error' in result:
            logger.error(f"{horizon}: Analysis failed - {result['error']}")
            continue
        
        total_count += 1
        is_healthy = result['embedding_healthy'] and result['index_healthy']
        if is_healthy:
            healthy_count += 1
        
        status = "✅ HEALTHY" if is_healthy else "❌ DEGENERATE"
        logger.info(f"{horizon}: {status}")
        logger.info(f"  Embedding variance: {result['similarity_std']:.6f}")
        logger.info(f"  Index variance: {result['index_similarity_std']:.6f}")
    
    # Overall diagnosis
    logger.info(f"\n📊 OVERALL DIAGNOSIS:")
    logger.info(f"  Healthy indices: {healthy_count}/{total_count}")
    
    if healthy_count == 0:
        logger.error("🚨 CRITICAL: All indices are degenerate!")
        logger.error("   Root cause: Embeddings lack sufficient diversity")
        logger.error("   Recommended actions:")
        logger.error("   1. Check embedding model architecture")
        logger.error("   2. Verify data preprocessing pipeline")
        logger.error("   3. Investigate training data diversity")
        logger.error("   4. Consider model retraining with better regularization")
    elif healthy_count < total_count:
        logger.warning("⚠️  Some indices are degenerate")
        logger.warning("   Review embedding generation for affected horizons")
    else:
        logger.info("✅ All indices have healthy variance")
    
    return healthy_count == total_count

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)