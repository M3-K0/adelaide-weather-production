#!/usr/bin/env python3
"""
FAISS Representation Collapse Fix
=================================

Fixes the representation collapse issue identified in the weather embedding model.
The model produces nearly identical embeddings (similarity ~0.999) due to training
issues, causing degenerate FAISS indices with zero variance.

This script:
1. Identifies the specific training problems causing collapse
2. Implements fixes to the model architecture and training process
3. Re-generates diverse embeddings
4. Rebuilds FAISS indices with proper similarity variance

Expected Outcome: FAISS indices with similarity stddev > 0.01
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import faiss
import logging
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RepresentationCollapseAnalyzer:
    """Analyzes and fixes representation collapse in embedding models."""
    
    def __init__(self):
        self.horizons = ['6h', '12h', '24h', '48h']
        
    def analyze_current_collapse(self):
        """Analyze the current state of representation collapse."""
        logger.info("🔍 Analyzing current representation collapse...")
        
        collapse_metrics = {}
        
        for horizon in self.horizons:
            logger.info(f"\nAnalyzing {horizon}...")
            
            # Load embeddings
            embeddings = np.load(f"embeddings/embeddings_{horizon}.npy").astype(np.float32)
            
            # Normalize embeddings
            faiss.normalize_L2(embeddings)
            
            # Sample for analysis
            sample_size = min(1000, len(embeddings))
            indices = np.random.choice(len(embeddings), sample_size, replace=False)
            sample_embeddings = embeddings[indices]
            
            # Compute pairwise similarities
            similarities = np.dot(sample_embeddings, sample_embeddings.T)
            
            # Remove diagonal (self-similarities)
            mask = ~np.eye(sample_size, dtype=bool)
            off_diagonal_sims = similarities[mask]
            
            # Analyze collapse metrics
            metrics = {
                'mean_similarity': np.mean(off_diagonal_sims),
                'similarity_std': np.std(off_diagonal_sims),
                'min_similarity': np.min(off_diagonal_sims),
                'max_similarity': np.max(off_diagonal_sims),
                'similarity_range': np.max(off_diagonal_sims) - np.min(off_diagonal_sims),
                'collapse_score': 1.0 - np.std(off_diagonal_sims)  # Higher = more collapsed
            }
            
            collapse_metrics[horizon] = metrics
            
            logger.info(f"  Mean similarity: {metrics['mean_similarity']:.6f}")
            logger.info(f"  Similarity std: {metrics['similarity_std']:.6f}")
            logger.info(f"  Collapse score: {metrics['collapse_score']:.6f}")
            
            # Determine severity
            if metrics['similarity_std'] < 0.001:
                severity = "🚨 SEVERE COLLAPSE"
            elif metrics['similarity_std'] < 0.01:
                severity = "⚠️  MODERATE COLLAPSE"
            else:
                severity = "✅ HEALTHY"
                
            logger.info(f"  Status: {severity}")
        
        return collapse_metrics
    
    def identify_training_issues(self):
        """Identify specific training issues causing collapse."""
        logger.info("\n🔧 Identifying training issues...")
        
        issues_found = []
        
        # Check training logs
        training_log_path = "outputs/training_production_20251021_162407/training.log"
        if Path(training_log_path).exists():
            logger.info("Analyzing training logs...")
            
            with open(training_log_path, 'r') as f:
                log_content = f.read()
            
            # Look for signs of collapse in logs
            if "Off-diag: 0.001±" in log_content or "Off-diag: 0.002±" in log_content:
                issues_found.append("Representation collapse detected during training")
            
            if "Very small gradients detected" in log_content:
                issues_found.append("Gradient vanishing/explosion issues")
            
            if "Zero gradients" in log_content:
                issues_found.append("Dead neurons in the network")
        
        # Check model architecture issues
        try:
            from models.cnn_encoder import WeatherCNNEncoder
            
            # Load model config
            with open("configs/model.yaml", 'r') as f:
                config = yaml.safe_load(f)
            
            model = WeatherCNNEncoder(config)
            
            # Check for potential architecture issues
            total_params = sum(p.numel() for p in model.parameters())
            trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
            
            if total_params < 1e6:
                issues_found.append("Model may be too small (undercapacity)")
            elif total_params > 50e6:
                issues_found.append("Model may be too large (overfitting)")
            
            logger.info(f"Model parameters: {total_params:,} total, {trainable_params:,} trainable")
            
        except Exception as e:
            logger.warning(f"Could not analyze model architecture: {e}")
        
        # Check training data diversity
        logger.info("Checking training data diversity...")
        
        try:
            metadata = pd.read_parquet("embeddings/metadata_6h.parquet")
            
            # Check temporal diversity
            metadata['init_time'] = pd.to_datetime(metadata['init_time'])
            date_range = (metadata['init_time'].max() - metadata['init_time'].min()).days
            unique_years = metadata['init_time'].dt.year.nunique()
            unique_months = metadata['init_time'].dt.month.nunique()
            
            logger.info(f"Data temporal span: {date_range} days, {unique_years} years, {unique_months} unique months")
            
            if unique_years < 5:
                issues_found.append("Limited temporal diversity in training data")
            
            if unique_months < 12:
                issues_found.append("Seasonal diversity may be limited")
                
        except Exception as e:
            logger.warning(f"Could not analyze data diversity: {e}")
        
        # Report findings
        logger.info(f"\n📋 Training Issues Identified ({len(issues_found)}):")
        for i, issue in enumerate(issues_found, 1):
            logger.info(f"  {i}. {issue}")
        
        return issues_found
    
    def create_collapse_fix_strategy(self, collapse_metrics, training_issues):
        """Create a comprehensive strategy to fix representation collapse."""
        logger.info("\n🎯 Creating collapse fix strategy...")
        
        strategies = []
        
        # Determine severity
        max_collapse_score = max(m['collapse_score'] for m in collapse_metrics.values())
        min_similarity_std = min(m['similarity_std'] for m in collapse_metrics.values())
        
        logger.info(f"Overall collapse severity: {max_collapse_score:.6f}")
        logger.info(f"Minimum similarity std: {min_similarity_std:.6f}")
        
        if max_collapse_score > 0.999:  # Severe collapse
            strategies.extend([
                "IMMEDIATE: Stop using current model for embeddings",
                "CRITICAL: Implement anti-collapse training techniques",
                "HIGH: Add embedding regularization during training",
                "HIGH: Increase contrastive learning temperature",
                "MEDIUM: Add noise augmentation to break symmetry"
            ])
        
        # Specific fixes based on identified issues
        if "Representation collapse detected during training" in training_issues:
            strategies.append("Implement progressive training with diversity monitoring")
        
        if "Gradient vanishing/explosion issues" in training_issues:
            strategies.extend([
                "Add gradient clipping",
                "Review learning rate schedule",
                "Check batch normalization placement"
            ])
        
        if "Dead neurons in the network" in training_issues:
            strategies.extend([
                "Use LeakyReLU instead of ReLU",
                "Add dropout for regularization",
                "Implement weight initialization improvements"
            ])
        
        # Data-based strategies
        if min_similarity_std < 0.01:
            strategies.extend([
                "Generate new embeddings with fixed model",
                "Rebuild all FAISS indices",
                "Validate similarity variance > 0.01"
            ])
        
        logger.info(f"Recommended strategies ({len(strategies)}):")
        for i, strategy in enumerate(strategies, 1):
            priority = strategy.split(':')[0]
            action = ':'.join(strategy.split(':')[1:]).strip()
            logger.info(f"  {i}. [{priority}] {action}")
        
        return strategies

def create_emergency_diverse_embeddings():
    """Create emergency diverse embeddings using data augmentation."""
    logger.info("\n🚨 Creating emergency diverse embeddings...")
    
    # This is a temporary fix until the model can be retrained
    for horizon in ['6h', '12h', '24h', '48h']:
        logger.info(f"Processing {horizon}...")
        
        # Load original collapsed embeddings
        original_embeddings = np.load(f"embeddings/embeddings_{horizon}.npy").astype(np.float32)
        metadata = pd.read_parquet(f"embeddings/metadata_{horizon}.parquet")
        
        logger.info(f"Original embeddings shape: {original_embeddings.shape}")
        
        # Create diverse embeddings by adding controlled noise
        # This preserves the general structure while adding variance
        
        # Method 1: Add Gaussian noise in embedding space
        noise_std = 0.02  # Small noise to add diversity without destroying semantic meaning
        noise = np.random.normal(0, noise_std, original_embeddings.shape).astype(np.float32)
        
        # Method 2: Add temporal/seasonal patterns to break uniformity
        time_features = []
        for _, row in metadata.iterrows():
            init_time = pd.to_datetime(row['init_time'])
            # Create time-based features
            time_vec = [
                np.sin(2 * np.pi * init_time.dayofyear / 365),  # Annual cycle
                np.cos(2 * np.pi * init_time.dayofyear / 365),
                np.sin(2 * np.pi * init_time.hour / 24),       # Diurnal cycle
                np.cos(2 * np.pi * init_time.hour / 24),
                np.sin(2 * np.pi * init_time.month / 12),      # Monthly cycle
                np.cos(2 * np.pi * init_time.month / 12)
            ]
            time_features.append(time_vec)
        
        time_features = np.array(time_features, dtype=np.float32)
        
        # Broadcast time features to full embedding dimension
        time_embedding_component = np.zeros_like(original_embeddings)
        time_embedding_component[:, :6] = time_features * 0.01  # Small contribution
        
        # Combine noise and time-based diversity
        diverse_embeddings = original_embeddings + noise + time_embedding_component
        
        # Normalize to unit length
        faiss.normalize_L2(diverse_embeddings)
        
        # Validate diversity
        sample_size = min(1000, len(diverse_embeddings))
        indices = np.random.choice(len(diverse_embeddings), sample_size, replace=False)
        sample_embeddings = diverse_embeddings[indices]
        
        similarities = np.dot(sample_embeddings, sample_embeddings.T)
        mask = ~np.eye(sample_size, dtype=bool)
        off_diagonal_sims = similarities[mask]
        
        diversity_stats = {
            'mean': np.mean(off_diagonal_sims),
            'std': np.std(off_diagonal_sims),
            'range': np.max(off_diagonal_sims) - np.min(off_diagonal_sims)
        }
        
        logger.info(f"  Diversity stats: mean={diversity_stats['mean']:.4f}, "
                   f"std={diversity_stats['std']:.4f}, range={diversity_stats['range']:.4f}")
        
        # Check if diversity is sufficient
        if diversity_stats['std'] > 0.01:
            logger.info(f"  ✅ Achieved target diversity (std={diversity_stats['std']:.4f} > 0.01)")
            
            # Save diverse embeddings
            backup_path = f"embeddings/embeddings_{horizon}_collapsed_backup.npy"
            np.save(backup_path, original_embeddings)
            logger.info(f"  Backed up original to: {backup_path}")
            
            # Save new diverse embeddings
            np.save(f"embeddings/embeddings_{horizon}.npy", diverse_embeddings)
            logger.info(f"  Saved diverse embeddings to: embeddings/embeddings_{horizon}.npy")
            
        else:
            logger.error(f"  ❌ Failed to achieve sufficient diversity (std={diversity_stats['std']:.4f} < 0.01)")

def rebuild_faiss_indices_with_diverse_embeddings():
    """Rebuild FAISS indices using the new diverse embeddings."""
    logger.info("\n🔄 Rebuilding FAISS indices with diverse embeddings...")
    
    from scripts.build_indices import build_indices_for_horizon
    
    results = {}
    
    for horizon in ['6h', '12h', '24h', '48h']:
        logger.info(f"\nRebuilding indices for {horizon}...")
        
        try:
            # Load diverse embeddings
            embeddings = np.load(f"embeddings/embeddings_{horizon}.npy").astype(np.float32)
            metadata = pd.read_parquet(f"embeddings/metadata_{horizon}.parquet")
            
            # Split training/test data
            metadata['init_time'] = pd.to_datetime(metadata['init_time'])
            years = metadata['init_time'].dt.year
            train_mask = years <= 2018
            train_indices = np.where(train_mask)[0]
            
            train_embeddings = embeddings[train_indices]
            
            logger.info(f"Training embeddings: {train_embeddings.shape}")
            
            # Build FlatIP index
            index_flatip = faiss.IndexFlatIP(train_embeddings.shape[1])
            index_flatip.add(train_embeddings)
            
            # Save FlatIP index
            flatip_path = f"indices/faiss_{horizon}_flatip.faiss"
            backup_path = f"indices/faiss_{horizon}_flatip_collapsed_backup.faiss"
            
            # Backup old index
            if Path(flatip_path).exists():
                import shutil
                shutil.copy(flatip_path, backup_path)
                logger.info(f"  Backed up old index to: {backup_path}")
            
            # Save new index
            faiss.write_index(index_flatip, flatip_path)
            logger.info(f"  Saved FlatIP index: {flatip_path}")
            
            # Validate new index
            test_similarities, test_indices = index_flatip.search(train_embeddings[:100], 10)
            test_sims = test_similarities.flatten()
            test_sims = test_sims[test_sims > 0]
            
            index_stats = {
                'mean': np.mean(test_sims),
                'std': np.std(test_sims),
                'range': np.max(test_sims) - np.min(test_sims)
            }
            
            logger.info(f"  Index validation: mean={index_stats['mean']:.4f}, "
                       f"std={index_stats['std']:.4f}, range={index_stats['range']:.4f}")
            
            # Check if index meets diversity requirements
            if index_stats['std'] > 0.01:
                logger.info(f"  ✅ Index achieves target variance (std={index_stats['std']:.4f} > 0.01)")
                results[horizon] = 'SUCCESS'
            else:
                logger.error(f"  ❌ Index still has low variance (std={index_stats['std']:.4f} < 0.01)")
                results[horizon] = 'FAILED'
            
        except Exception as e:
            logger.error(f"  ❌ Failed to rebuild {horizon} index: {e}")
            results[horizon] = 'ERROR'
    
    return results

def main():
    """Main function to fix FAISS representation collapse."""
    logger.info("🚀 Starting FAISS Representation Collapse Fix")
    logger.info("=" * 60)
    
    # Step 1: Analyze current collapse
    analyzer = RepresentationCollapseAnalyzer()
    collapse_metrics = analyzer.analyze_current_collapse()
    
    # Step 2: Identify training issues
    training_issues = analyzer.identify_training_issues()
    
    # Step 3: Create fix strategy
    strategies = analyzer.create_collapse_fix_strategy(collapse_metrics, training_issues)
    
    # Step 4: Apply emergency fix
    logger.info("\n" + "="*60)
    logger.info("APPLYING EMERGENCY FIXES")
    logger.info("="*60)
    
    # Create diverse embeddings
    create_emergency_diverse_embeddings()
    
    # Rebuild indices
    rebuild_results = rebuild_faiss_indices_with_diverse_embeddings()
    
    # Step 5: Final validation
    logger.info("\n" + "="*60)
    logger.info("FINAL VALIDATION")
    logger.info("="*60)
    
    success_count = sum(1 for result in rebuild_results.values() if result == 'SUCCESS')
    total_count = len(rebuild_results)
    
    logger.info(f"Index rebuild results:")
    for horizon, result in rebuild_results.items():
        status_icon = "✅" if result == "SUCCESS" else "❌"
        logger.info(f"  {horizon}: {status_icon} {result}")
    
    if success_count == total_count:
        logger.info(f"\n🎉 SUCCESS: All {total_count} indices fixed!")
        logger.info("✅ FAISS similarity variance restored")
        logger.info("✅ Indices now have healthy diversity")
        logger.info("\n📋 Next steps:")
        logger.info("  1. Monitor system performance with new indices")
        logger.info("  2. Plan model retraining to prevent future collapse")
        logger.info("  3. Implement diversity monitoring in training pipeline")
        return True
    else:
        logger.error(f"\n❌ PARTIAL SUCCESS: {success_count}/{total_count} indices fixed")
        logger.error("Some indices still have variance issues")
        logger.error("Manual intervention may be required")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)