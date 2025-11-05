#!/usr/bin/env python3
"""
Quick Start Script - Test setup and run smoke test only
"""

import yaml
import torch
import sys
from pathlib import Path

def test_setup():
    """Test if environment is ready."""
    print("🔍 Testing setup...")
    
    # Check CUDA
    if torch.cuda.is_available():
        print(f"✅ CUDA available: {torch.cuda.get_device_name()}")
        print(f"✅ CUDA memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB")
    else:
        print("❌ CUDA not available")
        return False
    
    # Check dependencies
    try:
        import xarray, zarr, dask
        print("✅ Core dependencies available")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return False
    
    # Check configs
    if Path('configs/model.yaml').exists():
        print("✅ Config files found")
    else:
        print("❌ Config files missing")
        return False
    
    return True

def quick_test():
    """Run minimal training test."""
    print("🚀 Running quick test...")
    
    # Add models to path
    sys.path.append(str(Path(__file__).parent.parent / 'models'))
    
    try:
        from cnn_encoder import CNNEncoder
        
        # Create tiny model
        model = CNNEncoder(
            input_shape=[21, 21, 11],
            embedding_dim=64,
            lead_time_embedding_dim=32,
            seasonal_embedding_dim=16
        ).cuda()
        
        # Test forward pass
        batch_size = 2
        weather_data = torch.randn(batch_size, 21, 21, 11).cuda()
        lead_times = torch.randint(6, 73, (batch_size,)).cuda()
        months = torch.randint(1, 13, (batch_size,)).cuda()
        hours = torch.randint(0, 24, (batch_size,)).cuda()
        
        with torch.no_grad():
            embeddings = model(weather_data, lead_times, months, hours)
        
        print(f"✅ Model forward pass: {embeddings.shape}")
        print(f"✅ GPU memory used: {torch.cuda.memory_allocated() / 1e6:.1f}MB")
        
        return True
        
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        return False

def main():
    """Quick setup validation."""
    print("=" * 50)
    print("🚀 Weather Forecasting - Quick Start Test")
    print("=" * 50)
    
    if not test_setup():
        print("\n❌ Setup test failed")
        return False
    
    if not quick_test():
        print("\n❌ Model test failed")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All tests passed! Ready for training:")
    print("  python scripts/train_embeddings_optimized.py")
    print("=" * 50)
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)