#!/usr/bin/env python3
"""
Analyze horizon database duplication and temporal alignment issues
"""
import numpy as np
import pandas as pd
from pathlib import Path

print("=== HORIZON DUPLICATION ANALYSIS ===")

# Load all horizon databases
horizons = ['6h', '12h', '48h']  # Skip 24h due to corruption
databases = {}

for horizon in horizons:
    outcomes_path = f'outcomes/outcomes_{horizon}.npy'
    metadata_path = f'outcomes/metadata_{horizon}_clean.parquet'
    
    outcomes = np.load(outcomes_path)
    metadata = pd.read_parquet(metadata_path)
    
    databases[horizon] = {
        'outcomes': outcomes,
        'metadata': metadata,
        'shape': outcomes.shape,
        'variables': ['z500', 't2m', 't850', 'q850', 'u10', 'v10', 'u850', 'v850', 'cape']
    }
    
    print(f"\n{horizon} Database:")
    print(f"  Shape: {outcomes.shape}")
    print(f"  Time range: {metadata['valid_time'].min()} to {metadata['valid_time'].max()}")
    
    # Variable statistics
    for i, var in enumerate(databases[horizon]['variables']):
        vals = outcomes[:, i]
        print(f"  {var}: {vals.min():.3f} to {vals.max():.3f} (mean: {vals.mean():.3f})")

print("\n=== IDENTICAL RANGES INVESTIGATION ===")

# Check if databases are actually identical
for i, var in enumerate(databases['6h']['variables']):
    print(f"\n{var} (Column {i}):")
    
    var_data = {}
    for horizon in horizons:
        vals = databases[horizon]['outcomes'][:, i]
        var_data[horizon] = {
            'min': vals.min(),
            'max': vals.max(),
            'mean': vals.mean(),
            'std': vals.std()
        }
    
    # Check if ranges are truly identical
    mins = [var_data[h]['min'] for h in horizons]
    maxs = [var_data[h]['max'] for h in horizons]
    
    if len(set(f"{x:.6f}" for x in mins)) == 1 and len(set(f"{x:.6f}" for x in maxs)) == 1:
        print(f"  ⚠️  IDENTICAL ranges across all horizons!")
    else:
        print(f"  ✅ Different ranges across horizons")
    
    for horizon in horizons:
        d = var_data[horizon]
        print(f"    {horizon}: {d['min']:.6f} to {d['max']:.6f} (μ={d['mean']:.3f}, σ={d['std']:.3f})")

print("\n=== TEMPORAL ALIGNMENT CHECK ===")

# Check if the same init_times are being used across horizons
for horizon in horizons:
    metadata = databases[horizon]['metadata']
    print(f"\n{horizon} temporal info:")
    print(f"  init_time range: {metadata['init_time'].min()} to {metadata['init_time'].max()}")
    print(f"  valid_time range: {metadata['valid_time'].min()} to {metadata['valid_time'].max()}")
    
    # Check if valid_time = init_time + horizon
    time_diff = pd.to_datetime(metadata['valid_time']) - pd.to_datetime(metadata['init_time'])
    expected_diff = pd.Timedelta(hours=int(horizon[:-1]))
    
    correct_alignment = (time_diff == expected_diff).all()
    print(f"  Temporal alignment correct: {correct_alignment}")
    
    if not correct_alignment:
        wrong_count = (~(time_diff == expected_diff)).sum()
        print(f"  ⚠️  {wrong_count}/{len(metadata)} records have incorrect alignment!")

print("\n=== WIND COMPONENT ANALYSIS ===")

# Check for wind component artifacts
for horizon in horizons:
    outcomes = databases[horizon]['outcomes']
    
    # Check u10, v10, u850, v850 (columns 4, 5, 6, 7)
    wind_cols = [4, 5, 6, 7]  # u10, v10, u850, v850
    wind_names = ['u10', 'v10', 'u850', 'v850']
    
    print(f"\n{horizon} wind analysis:")
    
    for i, (col, name) in enumerate(zip(wind_cols, wind_names)):
        wind_data = outcomes[:, col]
        zero_count = np.sum(wind_data == 0.0)
        zero_pct = 100 * zero_count / len(wind_data)
        
        print(f"  {name}: {zero_count}/{len(wind_data)} exact zeros ({zero_pct:.1f}%)")
        
        if zero_pct > 1.0:  # Expert threshold: >1% exact zeros indicates corruption
            print(f"    ⚠️  CORRUPTION: >1% exact zeros detected!")