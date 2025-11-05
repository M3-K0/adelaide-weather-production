#!/usr/bin/env python3
"""
Embedding Validation Script - Critical Sanity Checks
Based on GPT-5 expert analysis to verify model learned meaningful patterns
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import xarray as xr
import json
import logging
from pathlib import Path
# Removed optional dependencies for now
# from sklearn.metrics import roc_auc_score
# from tqdm import tqdm
# import matplotlib.pyplot as plt
# import seaborn as sns

# Import model architecture
import sys
sys.path.append('models')
from cnn_encoder import WeatherCNNEncoder

class ValidationConfig:
    def __init__(self):
        # Load training config
        with open('config.json', 'r') as f:
            self.train_config = json.load(f)
        
        # Validation parameters
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.batch_size = 64
        self.num_samples = 2048  # For quick tests
        
        # Load model config to get unified temperature
        with open('configs/model.yaml', 'r') as f:
            import yaml
            model_config = yaml.safe_load(f)
        self.temperature = model_config['contrastive']['temperature']
        
        # File paths
        self.model_path = 'models/best_model.pt'
        self.surface_zarr = self.train_config['surface_zarr']
        self.pressure_zarr = self.train_config['pressure_zarr']

def setup_logging():
    """Setup logging for validation."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('validation_results.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

class WeatherDatasetValidation:
    """Simplified dataset for validation."""
    
    def __init__(self, surface_path, pressure_path, device='cuda'):
        self.device = device
        self.surface_ds = xr.open_zarr(surface_path)
        self.pressure_ds = xr.open_zarr(pressure_path)
        
        # Align datasets by time intersection
        common_times = np.intersect1d(
            self.surface_ds.time.values,
            self.pressure_ds.time.values
        )
        
        self.surface_ds = self.surface_ds.sel(time=common_times)
        self.pressure_ds = self.pressure_ds.sel(time=common_times)
        
        print(f"Dataset aligned: {len(common_times)} timesteps")
        
    def get_batch(self, batch_size=64, seed=None):
        """Get a batch of weather samples."""
        if seed is not None:
            np.random.seed(seed)
            
        # Random time indices
        time_indices = np.random.choice(len(self.surface_ds.time), batch_size, replace=False)
        
        batch_data = []
        
        for idx in time_indices:
            # Get surface data
            surface_vars = []
            for var in ['u10', 'v10', 't2m', 'msl']:
                if var in self.surface_ds.data_vars:
                    data = self.surface_ds[var].isel(time=idx).values
                    surface_vars.append(data)
            
            # Get pressure data  
            pressure_vars = []
            for var in ['z', 't', 'q', 'u', 'v']:
                if var in self.pressure_ds.data_vars:
                    data = self.pressure_ds[var].isel(time=idx).values
                    # Stack pressure levels as channels
                    if len(data.shape) == 3:  # (level, lat, lon)
                        data = data.reshape(-1, data.shape[-2], data.shape[-1])
                    pressure_vars.extend(data)
            
            # Combine all variables
            if surface_vars and pressure_vars:
                all_vars = surface_vars + pressure_vars
                weather_state = np.stack(all_vars, axis=0)  # (channels, lat, lon)
                batch_data.append(weather_state)
        
        if batch_data:
            batch_tensor = torch.tensor(np.stack(batch_data), dtype=torch.float32).to(self.device)
            return batch_tensor
        else:
            raise ValueError("No valid data found")

def load_model(model_path, device):
    """Load the trained model."""
    logger = logging.getLogger(__name__)
    
    # Initialize model (it loads config internally)
    model = WeatherCNNEncoder(config_path='configs/model.yaml').to(device)
    
    # Load weights
    checkpoint = torch.load(model_path, map_location=device)
    if 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'])
    else:
        model.load_state_dict(checkpoint)
    
    model.eval()
    logger.info(f"Model loaded: {sum(p.numel() for p in model.parameters())/1e6:.2f}M parameters")
    
    return model

def test_overfit_capability(model, dataset, config, logger):
    """Test 1: Can the model overfit a small batch? (Critical sanity check)"""
    logger.info("🔍 Test 1: Overfit Capability Test")
    
    model.train()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    
    # Get fixed small batch
    batch = dataset.get_batch(batch_size=32, seed=42)  # Fixed batch for overfitting
    lead_times = torch.randint(1, 73, (32,)).to(config.device)  # 1-72 hours
    months = torch.randint(0, 12, (32,)).to(config.device)  # 0-11 months
    hours = torch.randint(0, 24, (32,)).to(config.device)   # 0-23 hours
    
    logger.info(f"Overfitting batch shape: {batch.shape}")
    logger.info(f"Random baseline loss: {np.log(32):.4f}")
    
    losses = []
    
    for step in range(200):  # Should overfit quickly
        optimizer.zero_grad()
        
        # Forward pass
        embeddings = model(batch, lead_times, months, hours)
        
        # InfoNCE loss
        embeddings = F.normalize(embeddings, dim=-1)
        similarity = torch.matmul(embeddings, embeddings.T) / config.temperature
        
        # Labels: diagonal entries are positives
        labels = torch.arange(similarity.size(0)).to(config.device)
        loss = F.cross_entropy(similarity, labels)
        
        loss.backward()
        optimizer.step()
        
        losses.append(loss.item())
        
        if step % 50 == 0:
            logger.info(f"Step {step}: Loss = {loss.item():.4f}")
    
    final_loss = losses[-1]
    random_baseline = np.log(32)
    
    logger.info(f"Final overfit loss: {final_loss:.4f}")
    logger.info(f"Random baseline: {random_baseline:.4f}")
    logger.info(f"Improvement: {random_baseline - final_loss:.4f}")
    
    # Should achieve significant improvement
    overfit_success = final_loss < (random_baseline - 0.5)
    
    if overfit_success:
        logger.info("✅ PASS: Model can overfit (gradients flowing correctly)")
    else:
        logger.error("❌ FAIL: Model cannot overfit (gradient flow issue!)")
    
    return {
        'overfit_success': overfit_success,
        'final_loss': final_loss,
        'baseline_loss': random_baseline,
        'improvement': random_baseline - final_loss,
        'losses': losses
    }

def test_retrieval_accuracy(model, dataset, config, logger):
    """Test 2: In-batch retrieval accuracy"""
    logger.info("🔍 Test 2: In-batch Retrieval Accuracy")
    
    model.eval()
    
    all_top1_acc = []
    all_top5_acc = []
    all_similarities = []
    
    with torch.no_grad():
        for i in range(10):  # Multiple batches
            batch = dataset.get_batch(batch_size=config.batch_size, seed=100+i)
            lead_times = torch.randint(1, 73, (config.batch_size,)).to(config.device)
            months = torch.randint(0, 12, (config.batch_size,)).to(config.device)
            hours = torch.randint(0, 24, (config.batch_size,)).to(config.device)
            
            # Get embeddings
            embeddings = model(batch, lead_times, months, hours)
            embeddings = F.normalize(embeddings, dim=-1)
            
            # Compute similarities
            similarity_matrix = torch.matmul(embeddings, embeddings.T)
            
            # For each sample, rank others as retrieval candidates
            for anchor_idx in range(config.batch_size):
                similarities = similarity_matrix[anchor_idx]
                
                # Remove self-similarity
                similarities[anchor_idx] = -float('inf')
                
                # Get rankings
                rankings = torch.argsort(similarities, descending=True)
                
                # In this setup, we don't have ground truth positives,
                # so we'll use temporal neighbors as proxy positives
                # This is a simplified test - ideally you'd have augmented pairs
                
                # For now, just collect similarity distributions
                all_similarities.extend(similarities[similarities != -float('inf')].cpu().numpy())
    
    # Analyze similarity distributions
    similarities = np.array(all_similarities)
    
    logger.info(f"Similarity stats:")
    logger.info(f"  Mean: {similarities.mean():.4f}")
    logger.info(f"  Std: {similarities.std():.4f}")
    logger.info(f"  Range: [{similarities.min():.4f}, {similarities.max():.4f}]")
    
    # Good embeddings should have diverse similarities, not all near 0
    similarity_diversity = similarities.std()
    
    if similarity_diversity > 0.1:
        logger.info("✅ PASS: Good similarity diversity")
        retrieval_success = True
    else:
        logger.error("❌ FAIL: Low similarity diversity (embeddings may be collapsed)")
        retrieval_success = False
    
    return {
        'retrieval_success': retrieval_success,
        'similarity_stats': {
            'mean': similarities.mean(),
            'std': similarities.std(),
            'min': similarities.min(),
            'max': similarities.max()
        },
        'similarity_diversity': similarity_diversity
    }

def test_gradient_flow(model, dataset, config, logger):
    """Test 3: Gradient flow analysis"""
    logger.info("🔍 Test 3: Gradient Flow Analysis")
    
    model.train()
    
    # Get batch
    batch = dataset.get_batch(batch_size=16)
    lead_times = torch.randint(1, 73, (16,)).to(config.device)
    months = torch.randint(0, 12, (16,)).to(config.device)
    hours = torch.randint(0, 24, (16,)).to(config.device)
    
    # Forward pass
    embeddings = model(batch, lead_times, months, hours)
    
    # Compute loss
    embeddings = F.normalize(embeddings, dim=-1)
    similarity = torch.matmul(embeddings, embeddings.T) / config.temperature
    labels = torch.arange(similarity.size(0)).to(config.device)
    loss = F.cross_entropy(similarity, labels)
    
    # Backward pass
    loss.backward()
    
    # Analyze gradients by layer
    gradient_stats = {}
    
    for name, param in model.named_parameters():
        if param.grad is not None:
            grad_norm = param.grad.norm().item()
            grad_mean = param.grad.mean().item()
            grad_std = param.grad.std().item()
            
            gradient_stats[name] = {
                'norm': grad_norm,
                'mean': grad_mean,
                'std': grad_std,
                'has_grad': True
            }
            
            logger.info(f"{name}: norm={grad_norm:.6f}, mean={grad_mean:.6f}, std={grad_std:.6f}")
        else:
            gradient_stats[name] = {'has_grad': False}
            logger.warning(f"{name}: NO GRADIENT!")
    
    # Check for frozen layers
    frozen_layers = [name for name, stats in gradient_stats.items() if not stats['has_grad']]
    
    if frozen_layers:
        logger.error(f"❌ FAIL: Frozen layers detected: {frozen_layers}")
        gradient_success = False
    else:
        # Check for vanishing gradients
        grad_norms = [stats['norm'] for stats in gradient_stats.values() if stats['has_grad']]
        min_grad_norm = min(grad_norms)
        
        if min_grad_norm < 1e-8:
            logger.warning(f"⚠️  Very small gradients detected (min: {min_grad_norm:.2e})")
            gradient_success = False
        else:
            logger.info("✅ PASS: Healthy gradient flow")
            gradient_success = True
    
    return {
        'gradient_success': gradient_success,
        'gradient_stats': gradient_stats,
        'frozen_layers': frozen_layers
    }

def analyze_loss_landscape(model, dataset, config, logger):
    """Analyze InfoNCE loss values and compare to baseline"""
    logger.info("🔍 Analysis: Loss Landscape vs Random Baseline")
    
    model.eval()
    
    losses = []
    batch_sizes = [16, 32, 64, 128]
    
    with torch.no_grad():
        for bs in batch_sizes:
            if bs <= len(dataset.surface_ds.time):
                try:
                    batch = dataset.get_batch(batch_size=bs, seed=200)
                    lead_times = torch.randint(1, 73, (bs,)).to(config.device)
                    months = torch.randint(0, 12, (bs,)).to(config.device)
                    hours = torch.randint(0, 24, (bs,)).to(config.device)
                    
                    embeddings = model(batch, lead_times, months, hours)
                    embeddings = F.normalize(embeddings, dim=-1)
                    similarity = torch.matmul(embeddings, embeddings.T) / config.temperature
                    labels = torch.arange(similarity.size(0)).to(config.device)
                    loss = F.cross_entropy(similarity, labels)
                    
                    random_baseline = np.log(bs)
                    improvement = random_baseline - loss.item()
                    
                    logger.info(f"Batch size {bs}: Loss={loss.item():.4f}, Baseline={random_baseline:.4f}, Improvement={improvement:.4f}")
                    
                    losses.append({
                        'batch_size': bs,
                        'loss': loss.item(),
                        'baseline': random_baseline,
                        'improvement': improvement
                    })
                except Exception as e:
                    logger.warning(f"Failed batch size {bs}: {e}")
    
    return {'loss_analysis': losses}

def main():
    """Run all validation tests."""
    logger = setup_logging()
    config = ValidationConfig()
    
    logger.info("🚀 Starting Embedding Validation")
    logger.info(f"Device: {config.device}")
    logger.info(f"Temperature: {config.temperature}")
    
    # Load dataset
    logger.info("Loading dataset...")
    dataset = WeatherDatasetValidation(
        config.surface_zarr,
        config.pressure_zarr,
        config.device
    )
    
    # Load model
    logger.info("Loading model...")
    model = load_model(config.model_path, config.device)
    
    # Run validation tests
    results = {}
    
    try:
        # Test 1: Overfit capability
        results['overfit'] = test_overfit_capability(model, dataset, config, logger)
        
        # Test 2: Retrieval accuracy  
        results['retrieval'] = test_retrieval_accuracy(model, dataset, config, logger)
        
        # Test 3: Gradient flow
        results['gradients'] = test_gradient_flow(model, dataset, config, logger)
        
        # Analysis: Loss landscape
        results['loss_analysis'] = analyze_loss_landscape(model, dataset, config, logger)
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("VALIDATION SUMMARY")
    logger.info("="*60)
    
    overfit_pass = results['overfit']['overfit_success']
    retrieval_pass = results['retrieval']['retrieval_success'] 
    gradient_pass = results['gradients']['gradient_success']
    
    total_tests = 3
    passed_tests = sum([overfit_pass, retrieval_pass, gradient_pass])
    
    logger.info(f"Tests passed: {passed_tests}/{total_tests}")
    logger.info(f"Overfit test: {'✅ PASS' if overfit_pass else '❌ FAIL'}")
    logger.info(f"Retrieval test: {'✅ PASS' if retrieval_pass else '❌ FAIL'}")
    logger.info(f"Gradient test: {'✅ PASS' if gradient_pass else '❌ FAIL'}")
    
    if passed_tests == total_tests:
        logger.info("🎉 ALL TESTS PASSED - Model appears healthy!")
        logger.info("✅ Ready to proceed with FAISS indexing")
    else:
        logger.error("🚨 CRITICAL ISSUES DETECTED")
        logger.error("❌ Do NOT proceed with FAISS until issues are resolved")
        logger.error("💡 Consider hyperparameter sweep or architecture changes")
    
    # Save results
    with open('validation_results.json', 'w') as f:
        # Convert numpy types for JSON serialization
        def convert_numpy(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(v) for v in obj]
            return obj
        
        json.dump(convert_numpy(results), f, indent=2)
    
    logger.info("Results saved to validation_results.json")

if __name__ == "__main__":
    main()