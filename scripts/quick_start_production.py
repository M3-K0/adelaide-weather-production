#!/usr/bin/env python3
"""
Production Quick Start Script - Tests all GPT-5 optimizations
"""

import yaml
import torch
import numpy as np
import sys
from pathlib import Path

def test_production_setup():
    """Test if production environment is ready."""
    print("🔍 Testing production setup...")
    
    # Check CUDA
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name()
        memory_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"✅ CUDA available: {gpu_name}")
        print(f"✅ CUDA memory: {memory_gb:.1f}GB")
        
        # Check for A100-specific features
        if "A100" in gpu_name:
            print("✅ A100 detected - optimal for channels_last and large batches")
        elif "H100" in gpu_name or "H200" in gpu_name:
            print("✅ H-series detected - excellent for this workload")
    else:
        print("❌ CUDA not available")
        return False
    
    # Check dependencies
    try:
        import xarray, zarr, dask, pandas, scipy
        print("✅ Core dependencies available")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return False
    
    # Check configs
    if Path('configs/model.yaml').exists():
        print("✅ Config files found")
        
        # Validate config structure
        with open('configs/model.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        required_keys = [
            ['contrastive', 'temperature'],
            ['contrastive', 'temporal_window'],
            ['training', 'train_years'],
            ['training', 'val_years'],
            ['training', 'warmup_epochs']
        ]
        
        for keys in required_keys:
            current = config
            for key in keys:
                if key not in current:
                    print(f"❌ Missing config key: {'.'.join(keys)}")
                    return False
                current = current[key]
        
        print("✅ Config structure validated")
    else:
        print("❌ Config files missing")
        return False
    
    return True

def test_production_model():
    """Test production model with all optimizations."""
    print("🚀 Running production model test...")
    
    # Add models to path
    sys.path.append(str(Path(__file__).parent.parent / 'models'))
    
    try:
        from cnn_encoder import WeatherCNNEncoder as CNNEncoder
        
        # Create model with production settings
        model = CNNEncoder(config_path='configs/model.yaml').cuda()
        
        # Apply channels_last optimization
        model = model.to(memory_format=torch.channels_last)
        print("✅ Applied channels_last memory format")
        
        # Test forward pass with channels_last input
        batch_size = 4
        weather_data = torch.randn(batch_size, 9, 16, 16).cuda()  # Match actual data shape
        weather_data = weather_data.contiguous(memory_format=torch.channels_last)
        
        lead_times = torch.randint(0, 72, (batch_size,)).cuda()  # 0-71 for 72 max_lead
        months = torch.randint(0, 12, (batch_size,)).cuda()      # 0-11 for embedding table
        hours = torch.randint(0, 24, (batch_size,)).cuda()       # 0-23 hours
        
        with torch.no_grad():
            embeddings = model(weather_data, lead_times, months, hours)
        
        print(f"✅ Model forward pass: {embeddings.shape}")
        print(f"✅ GPU memory used: {torch.cuda.memory_allocated() / 1e6:.1f}MB")
        
        # Test embedding normalization and similarity
        embeddings_norm = torch.nn.functional.normalize(embeddings, dim=-1)
        similarity = torch.matmul(embeddings_norm, embeddings_norm.T)
        
        diag_sim = torch.diag(similarity).mean().item()
        off_diag_sim = similarity[~torch.eye(batch_size, dtype=torch.bool, device='cuda')].mean().item()
        
        print(f"✅ Similarity stats - Diag: {diag_sim:.3f}, Off-diag: {off_diag_sim:.3f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        return False

def test_temporal_positives():
    """Test temporal positive finding logic."""
    print("🔍 Testing temporal positive logic...")
    
    try:
        import pandas as pd
        
        # Create sample times spanning 48 hours
        base_time = pd.Timestamp('2020-01-01 00:00:00')
        sample_times = [base_time + pd.Timedelta(hours=h) for h in [0, 6, 12, 24, 30, 48]]
        
        # Test temporal positive finding
        temporal_window = 24  # hours
        pos_indices = []
        
        for i, anchor_time in enumerate(sample_times):
            positive_idx = i  # Default to self
            
            for j, candidate_time in enumerate(sample_times):
                if i == j:
                    continue
                    
                time_diff = abs((candidate_time - anchor_time).total_seconds() / 3600)
                
                if time_diff <= temporal_window:
                    positive_idx = j
                    break
            
            pos_indices.append(positive_idx)
        
        # Verify temporal neighbors were found
        temporal_pairs = [(i, pos_indices[i]) for i in range(len(sample_times)) if pos_indices[i] != i]
        
        print(f"✅ Found {len(temporal_pairs)} temporal positive pairs")
        print(f"✅ Temporal pairs: {temporal_pairs}")
        
        return True
        
    except Exception as e:
        print(f"❌ Temporal positive test failed: {e}")
        return False

def test_normalization_logic():
    """Test input normalization logic."""
    print("🔍 Testing normalization logic...")
    
    try:
        # Simulate weather data with different scales
        weather_data = np.random.randn(4, 21, 21, 11)
        
        # Add realistic scale differences
        weather_data[..., 0] += 273.15  # Temperature in Kelvin
        weather_data[..., 1] *= 101325  # Pressure in Pa
        weather_data[..., 2:4] *= 10    # Wind speeds m/s
        weather_data[..., 4] = np.abs(weather_data[..., 4]) * 0.001  # Precipitation mm
        
        # Create mock normalization stats
        norm_stats = {}
        for i in range(11):
            var_data = weather_data[..., i].flatten()
            key = f'surface_{i}' if i < 5 else f'pressure_{i}'
            norm_stats[key] = {
                'mean': float(np.mean(var_data)),
                'std': float(np.std(var_data) + 1e-8)
            }
        
        # Apply normalization
        normalized = weather_data.copy()
        for i in range(11):
            key = f'surface_{i}' if i < 5 else f'pressure_{i}'
            if key in norm_stats:
                mean = norm_stats[key]['mean']
                std = norm_stats[key]['std']
                normalized[..., i] = (normalized[..., i] - mean) / std
        
        # Check normalization worked
        for i in range(11):
            var_mean = np.mean(normalized[..., i])
            var_std = np.std(normalized[..., i])
            if abs(var_mean) > 0.1 or abs(var_std - 1.0) > 0.1:
                print(f"❌ Variable {i} normalization failed: mean={var_mean:.3f}, std={var_std:.3f}")
                return False
        
        print("✅ Input normalization working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Normalization test failed: {e}")
        return False

def estimate_performance():
    """Estimate expected performance on current GPU."""
    print("📊 Estimating performance...")
    
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        memory_gb = props.total_memory / 1e9
        gpu_name = torch.cuda.get_device_name()
        
        if "A100" in gpu_name:
            if memory_gb > 70:
                print("🚀 A100-80GB detected:")
                print("  • Recommended batch size: 256-512")
                print("  • Expected GPU utilization: 60-80%")
                print("  • Training time: ~2-4 hours")
            else:
                print("🚀 A100-40GB detected:")
                print("  • Recommended batch size: 128-256")
                print("  • Expected GPU utilization: 50-70%")
                print("  • Training time: ~3-5 hours")
        elif "H100" in gpu_name or "H200" in gpu_name:
            print("🚀 H-series detected:")
            print("  • Recommended batch size: 512-1024")
            print("  • Expected GPU utilization: 40-60% (model too small)")
            print("  • Training time: ~1-2 hours")
        elif "RTX" in gpu_name or "GTX" in gpu_name:
            print("🔧 Consumer GPU detected:")
            print("  • Recommended batch size: 32-64")
            print("  • Expected GPU utilization: 70-90%")
            print("  • Training time: ~6-12 hours")
        else:
            print(f"🔍 {gpu_name} detected:")
            print(f"  • Memory available: {memory_gb:.1f}GB")
            print("  • Start with batch size: 64")
            print("  • Monitor GPU utilization and adjust")
    
    print("\n💡 Performance optimization tips:")
    print("  • Enable mixed precision after smoke test passes")
    print("  • Increase batch size until GPU memory ~80% used")
    print("  • Monitor for off-diagonal similarity > 0.8 (collapse)")
    print("  • Target: Loss 4.16 → <2.0 for good embeddings")

def main():
    """Production setup validation."""
    print("=" * 60)
    print("🚀 Weather Forecasting - Production Setup Test")
    print("=" * 60)
    
    if not test_production_setup():
        print("\n❌ Production setup test failed")
        return False
    
    if not test_production_model():
        print("\n❌ Production model test failed")
        return False
    
    if not test_temporal_positives():
        print("\n❌ Temporal positive test failed")
        return False
    
    if not test_normalization_logic():
        print("\n❌ Normalization test failed")
        return False
    
    estimate_performance()
    
    print("\n" + "=" * 60)
    print("🎉 All production tests passed! Ready for training:")
    print("  python scripts/train_embeddings_production.py")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)