#!/usr/bin/env python3
"""
Simple test to see what we can access without full dependencies
"""

import os
import sys
from pathlib import Path

def test_basic_imports():
    """Test basic Python functionality"""
    print("✓ Python 3 working")
    print(f"Python version: {sys.version}")
    
def test_data_access():
    """Test data directory access"""
    data_dir = Path("/home/micha/weather-forecast-final/data")
    
    if data_dir.exists():
        print(f"✓ Data directory exists: {data_dir}")
        
        # List contents
        for item in data_dir.rglob("*.zarr"):
            print(f"  Found zarr: {item}")
            
        for item in data_dir.rglob("*.nc"):
            print(f"  Found nc: {item}")
            
    else:
        print(f"✗ Data directory not found: {data_dir}")
        
def test_model_access():
    """Test model file access"""
    model_path = Path("/home/micha/weather-forecast-final/outputs/training_production_20251021_162407/best_model.pt")
    
    if model_path.exists():
        print(f"✓ Model file exists: {model_path}")
        size_mb = model_path.stat().st_size / (1024*1024)
        print(f"  Model size: {size_mb:.1f} MB")
    else:
        print(f"✗ Model file not found: {model_path}")

def test_configs():
    """Test config files"""
    config_dir = Path("/home/micha/weather-forecast-final/configs")
    
    if config_dir.exists():
        print(f"✓ Configs directory exists: {config_dir}")
        for item in config_dir.glob("*"):
            print(f"  Found config: {item.name}")
    else:
        print(f"✗ Configs directory not found: {config_dir}")

if __name__ == "__main__":
    print("🔍 Testing Adelaide Weather Forecast System Setup")
    print("=" * 50)
    
    test_basic_imports()
    print()
    
    test_data_access()
    print()
    
    test_model_access()
    print()
    
    test_configs()
    print()
    
    print("✅ Basic system test completed!")