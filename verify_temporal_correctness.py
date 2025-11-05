#!/usr/bin/env python3
"""
Verify temporal correctness - are 6h and 12h databases actually correct?
"""
import numpy as np
import pandas as pd
import xarray as xr
from pathlib import Path

print("=== TEMPORAL CORRECTNESS VERIFICATION ===")

# Load databases
outcomes_6h = np.load('outcomes/outcomes_6h.npy')
outcomes_12h = np.load('outcomes/outcomes_12h.npy')
metadata_6h = pd.read_parquet('outcomes/metadata_6h_clean.parquet')
metadata_12h = pd.read_parquet('outcomes/metadata_12h_clean.parquet')

print(f"Database shapes: 6h={outcomes_6h.shape}, 12h={outcomes_12h.shape}")

# Test case: For the SAME init_time, extract weather at t+6h and t+12h manually
# This is what SHOULD be in the databases if they're correct

print("\n=== MANUAL ERA5 EXTRACTION TEST ===")

# Load ERA5 data
surface_ds = xr.open_zarr("data/era5/zarr/era5_surface_2010_2020.zarr")
pressure_ds = xr.open_zarr("data/era5/zarr/era5_pressure_2010_2019.zarr")

adelaide_lat = -34.93
adelaide_lon = 138.60

# Test with first init_time from both databases
test_init_time = metadata_6h.iloc[0]['init_time']
print(f"Test init_time: {test_init_time}")

# Calculate expected valid_times
test_init_dt = pd.to_datetime(test_init_time)
expected_valid_6h = test_init_dt + pd.Timedelta(hours=6)
expected_valid_12h = test_init_dt + pd.Timedelta(hours=12)

print(f"Expected 6h valid_time: {expected_valid_6h}")
print(f"Expected 12h valid_time: {expected_valid_12h}")

# Extract manually from ERA5 at both times
def extract_z500_manually(valid_time):
    """Extract z500 manually from ERA5"""
    try:
        valid_time_np = pd.to_datetime(valid_time).to_numpy()
        pressure_data = pressure_ds.sel(
            time=valid_time_np,
            latitude=adelaide_lat,
            longitude=adelaide_lon,
            method='nearest'
        )
        z500 = pressure_data['z'].sel(isobaricInhPa=500, method='nearest')
        return float(z500.values) / 9.81  # Convert to geopotential height
    except Exception as e:
        print(f"Failed to extract at {valid_time}: {e}")
        return None

manual_z500_6h = extract_z500_manually(expected_valid_6h)
manual_z500_12h = extract_z500_manually(expected_valid_12h)

print(f"\nManual extraction results:")
print(f"  z500 at t+6h:  {manual_z500_6h:.3f}")
print(f"  z500 at t+12h: {manual_z500_12h:.3f}")

# Compare with what's in the databases
db_z500_6h = outcomes_6h[0, 0]
db_z500_12h = outcomes_12h[0, 0]

print(f"\nDatabase values:")
print(f"  6h database z500:  {db_z500_6h:.3f}")
print(f"  12h database z500: {db_z500_12h:.3f}")

print(f"\nComparison:")
print(f"  6h manual vs database: {abs(manual_z500_6h - db_z500_6h):.6f} difference")
print(f"  12h manual vs database: {abs(manual_z500_12h - db_z500_12h):.6f} difference")

if abs(manual_z500_6h - db_z500_6h) < 0.001:
    print("  ✅ 6h database extraction is CORRECT")
else:
    print("  ❌ 6h database extraction is WRONG")

if abs(manual_z500_12h - db_z500_12h) < 0.001:
    print("  ✅ 12h database extraction is CORRECT")
else:
    print("  ❌ 12h database extraction is WRONG")

# Now check the key question: Are the correlations high because weather is predictable?
print(f"\n=== WEATHER PERSISTENCE ANALYSIS ===")
print(f"Weather difference between t+6h and t+12h: {abs(manual_z500_12h - manual_z500_6h):.3f}")
print(f"This represents weather change over 6 hours")

# Calculate actual correlation between t+6h and t+12h weather
print("\n=== NATURAL WEATHER CORRELATION (t+6h vs t+12h) ===")

# For multiple test cases
correlations = []
test_indices = [0, 100, 500, 1000]  # Test a few different times

for idx in test_indices:
    if idx < len(metadata_6h):
        init_time = metadata_6h.iloc[idx]['init_time']
        init_dt = pd.to_datetime(init_time)
        
        valid_6h = init_dt + pd.Timedelta(hours=6)
        valid_12h = init_dt + pd.Timedelta(hours=12)
        
        z500_6h = extract_z500_manually(valid_6h)
        z500_12h = extract_z500_manually(valid_12h)
        
        db_6h = outcomes_6h[idx, 0]
        db_12h = outcomes_12h[idx, 0]
        
        print(f"Test {idx}: init={init_time}")
        print(f"  Manual: 6h={z500_6h:.3f}, 12h={z500_12h:.3f}")
        print(f"  Database: 6h={db_6h:.3f}, 12h={db_12h:.3f}")
        print(f"  Weather evolution: {z500_12h-z500_6h:.3f}")

# Test correlation across first 100 patterns
print(f"\n=== BATCH CORRELATION TEST ===")
manual_6h_values = []
manual_12h_values = []
db_6h_values = []
db_12h_values = []

for idx in range(min(100, len(metadata_6h))):
    init_time = metadata_6h.iloc[idx]['init_time']
    init_dt = pd.to_datetime(init_time)
    
    # Skip if we can't extract (data availability)
    try:
        valid_6h = init_dt + pd.Timedelta(hours=6)
        valid_12h = init_dt + pd.Timedelta(hours=12)
        
        z500_6h = extract_z500_manually(valid_6h)
        z500_12h = extract_z500_manually(valid_12h)
        
        if z500_6h is not None and z500_12h is not None:
            manual_6h_values.append(z500_6h)
            manual_12h_values.append(z500_12h)
            db_6h_values.append(outcomes_6h[idx, 0])
            db_12h_values.append(outcomes_12h[idx, 0])
    except:
        continue

if len(manual_6h_values) > 10:
    manual_corr = np.corrcoef(manual_6h_values, manual_12h_values)[0, 1]
    db_corr = np.corrcoef(db_6h_values, db_12h_values)[0, 1]
    
    print(f"Manual extraction correlation (t+6h vs t+12h): {manual_corr:.6f}")
    print(f"Database correlation (6h vs 12h): {db_corr:.6f}")
    print(f"Difference: {abs(manual_corr - db_corr):.6f}")
    
    if abs(manual_corr - db_corr) < 0.01:
        print("✅ DATABASES ARE CORRECT - High correlation is natural weather persistence!")
    else:
        print("❌ DATABASES HAVE EXTRACTION ERRORS")

print(f"\n=== CONCLUSION ===")
print("The high correlation between 6h and 12h databases might be NATURAL")
print("Weather at t+6h and t+12h are highly correlated due to atmospheric persistence")
print("This is expected behavior in meteorology - weather doesn't change drastically in 6 hours")
print("The reported 0.999990 correlation might be an exaggeration or measurement error")