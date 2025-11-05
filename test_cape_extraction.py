#!/usr/bin/env python3
"""
Test CAPE extraction from the fixed build_outcomes_database.py
"""

import sys
import numpy as np
import pandas as pd
import xarray as xr
from pathlib import Path
import logging

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent / 'scripts'))

from cape_calculator import extract_cape_from_era5
from scripts.build_outcomes_database import OutcomesDatabaseBuilder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_cape_extraction():
    """Test CAPE extraction with a few sample timestamps."""
    
    print("Testing CAPE Extraction from ERA5 Data")
    print("=" * 50)
    
    # Create database builder
    builder = OutcomesDatabaseBuilder()
    
    # Load ERA5 data
    if not builder.load_era5_data():
        print("❌ Failed to load ERA5 data")
        return False
    
    # Load metadata for 6h horizon to get sample timestamps
    metadata_path = Path("embeddings/metadata_6h.parquet")
    if not metadata_path.exists():
        print(f"❌ Metadata not found: {metadata_path}")
        return False
    
    metadata = pd.read_parquet(metadata_path)
    print(f"✅ Loaded metadata: {len(metadata)} patterns")
    
    # Test with first 5 patterns
    test_count = 5
    cape_values = []
    
    print(f"\nTesting CAPE extraction for first {test_count} patterns:")
    print("-" * 60)
    
    for i in range(test_count):
        row = metadata.iloc[i]
        valid_time = row['valid_time']
        
        print(f"Pattern {i+1}: {valid_time}")
        
        # Extract outcome using the new method
        outcome = builder.extract_outcome_at_time(valid_time)
        
        if outcome is not None:
            cape_val = outcome[8]  # CAPE is index 8
            cape_values.append(cape_val)
            
            print(f"  CAPE: {cape_val:.1f} J/kg")
            print(f"  T850: {outcome[7]-273.15:.1f}°C")
            print(f"  MSL: {outcome[0]/100:.1f} hPa")
            print(f"  U850: {outcome[5]:.1f} m/s")
            
            # Check if CAPE is non-zero (success!)
            if cape_val > 0:
                print(f"  ✅ CAPE successfully calculated!")
            else:
                print(f"  ⚠️ CAPE is zero")
        else:
            print(f"  ❌ Failed to extract outcome")
        
        print()
    
    # Summary
    non_zero_cape = sum(1 for cape in cape_values if cape > 0)
    total_tested = len(cape_values)
    
    print("Summary:")
    print(f"  Total patterns tested: {total_tested}")
    print(f"  Non-zero CAPE values: {non_zero_cape}")
    print(f"  Zero CAPE values: {total_tested - non_zero_cape}")
    
    if cape_values:
        print(f"  CAPE range: {min(cape_values):.1f} - {max(cape_values):.1f} J/kg")
        print(f"  CAPE mean: {np.mean(cape_values):.1f} J/kg")
    
    success_rate = non_zero_cape / total_tested * 100 if total_tested > 0 else 0
    print(f"  Success rate: {success_rate:.1f}%")
    
    if success_rate > 0:
        print("\n🎉 CAPE extraction is working! Ready to rebuild databases.")
        return True
    else:
        print("\n❌ CAPE extraction failed - need to debug further.")
        return False

if __name__ == "__main__":
    test_cape_extraction()