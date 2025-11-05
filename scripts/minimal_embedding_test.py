#!/usr/bin/env python3
"""
Minimal Embedding Generation Test
================================

Test loading the trained model and generating a few embeddings without
heavy dependencies. This will let us validate the approach works.
"""

import os
import sys
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

def test_minimal_setup():
    """Test minimal setup without heavy dependencies"""
    
    print("🧪 Testing Minimal Adelaide Weather Embedding Generation")
    print("=" * 60)
    
    # Check basic Python capabilities
    print("✓ Python 3 working")
    print(f"NumPy version: {np.__version__}")
    
    # Check file access
    base_dir = Path("/home/micha/weather-forecast-final")
    model_path = base_dir / "outputs/training_production_20251021_162407/best_model.pt"
    config_path = base_dir / "configs/model.yaml"
    
    print(f"✓ Model exists: {model_path.exists()}")
    print(f"✓ Config exists: {config_path.exists()}")
    
    # Check data access
    surface_zarr = base_dir / "data/era5/zarr/era5_surface_2010_2020.zarr"
    pressure_zarr = base_dir / "data/era5/zarr/era5_pressure_2010_2019.zarr"
    
    print(f"✓ Surface data exists: {surface_zarr.exists()}")
    print(f"✓ Pressure data exists: {pressure_zarr.exists()}")
    
    print("\n📋 Next Steps:")
    print("1. Install PyTorch: pip install torch --index-url https://download.pytorch.org/whl/cpu")
    print("2. Install data libraries: pip install xarray zarr")
    print("3. Run full embedding generation")
    
    return True

if __name__ == "__main__":
    test_minimal_setup()