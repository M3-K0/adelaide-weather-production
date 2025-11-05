#!/usr/bin/env python3
"""
Test CAPE extraction specifically during summer months (Dec-Feb) in Adelaide
to verify we get higher CAPE values during convective season.
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
import logging

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent / 'scripts'))

from scripts.build_outcomes_database import OutcomesDatabaseBuilder

logging.basicConfig(level=logging.WARNING)  # Reduce log noise

def test_cape_summer():
    """Test CAPE extraction during summer months."""
    
    print("Testing CAPE Extraction During Summer (Dec-Feb)")
    print("=" * 55)
    
    # Create database builder
    builder = OutcomesDatabaseBuilder()
    
    # Load ERA5 data
    if not builder.load_era5_data():
        print("❌ Failed to load ERA5 data")
        return False
    
    # Load metadata for 6h horizon
    metadata_path = Path("embeddings/metadata_6h.parquet")
    metadata = pd.read_parquet(metadata_path)
    
    # Filter for summer months (Dec, Jan, Feb) in Southern Hemisphere
    metadata['month'] = pd.to_datetime(metadata['valid_time']).dt.month
    summer_metadata = metadata[metadata['month'].isin([12, 1, 2])]
    
    print(f"✅ Total patterns: {len(metadata)}")
    print(f"✅ Summer patterns: {len(summer_metadata)}")
    
    # Test with 20 random summer patterns
    test_count = min(20, len(summer_metadata))
    sample_indices = np.random.choice(len(summer_metadata), test_count, replace=False)
    
    cape_values = []
    high_cape_count = 0
    
    print(f"\nTesting {test_count} random summer patterns:")
    print("-" * 50)
    
    for i, idx in enumerate(sample_indices):
        row = summer_metadata.iloc[idx]
        valid_time = row['valid_time']
        
        # Extract outcome
        outcome = builder.extract_outcome_at_time(valid_time)
        
        if outcome is not None:
            cape_val = outcome[8]  # CAPE is index 8
            t850_c = outcome[7] - 273.15  # Convert to Celsius
            cape_values.append(cape_val)
            
            # Count high CAPE values (>500 J/kg indicates moderate instability)
            if cape_val > 500:
                high_cape_count += 1
                status = "🌩️ MODERATE-HIGH"
            elif cape_val > 100:
                status = "⛅ LOW-MODERATE"  
            elif cape_val > 0:
                status = "🟡 WEAK"
            else:
                status = "⚪ STABLE"
            
            print(f"{i+1:2d}. {valid_time.strftime('%Y-%m-%d %H:%M')} | "
                  f"CAPE: {cape_val:5.0f} J/kg | T850: {t850_c:5.1f}°C | {status}")
    
    # Statistics
    if cape_values:
        print(f"\nSummer CAPE Statistics:")
        print(f"  Mean CAPE: {np.mean(cape_values):.1f} J/kg")
        print(f"  Max CAPE:  {np.max(cape_values):.1f} J/kg")
        print(f"  Min CAPE:  {np.min(cape_values):.1f} J/kg")
        print(f"  Std CAPE:  {np.std(cape_values):.1f} J/kg")
        
        non_zero = sum(1 for cape in cape_values if cape > 0)
        print(f"  Non-zero CAPE: {non_zero}/{len(cape_values)} ({non_zero/len(cape_values)*100:.1f}%)")
        print(f"  High CAPE (>500): {high_cape_count}/{len(cape_values)} ({high_cape_count/len(cape_values)*100:.1f}%)")
        
        # Check if we have realistic variability
        if np.max(cape_values) > 1000:
            print(f"\n🎉 SUCCESS: Found high CAPE values (>{np.max(cape_values):.0f} J/kg) - thunderstorm conditions!")
        elif np.max(cape_values) > 500:
            print(f"\n✅ GOOD: Found moderate CAPE values - convective potential detected!")
        elif non_zero > 0:
            print(f"\n👍 OK: Found some CAPE values - algorithm working correctly!")
        else:
            print(f"\n⚠️ All CAPE values zero - may need algorithm tuning")
            
        return True
    else:
        print("❌ No valid extractions")
        return False

if __name__ == "__main__":
    test_cape_summer()