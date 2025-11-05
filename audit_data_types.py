#!/usr/bin/env python3
"""
Audit data types and memory usage across all databases
"""
import numpy as np
import pandas as pd
from pathlib import Path
import os

print("=== DATA TYPE AND MEMORY AUDIT ===")

# Check all database files
horizons = ['6h', '12h', '24h', '48h']
files_to_check = []

for horizon in horizons:
    outcomes_path = f'outcomes/outcomes_{horizon}.npy'
    metadata_path = f'outcomes/metadata_{horizon}_clean.parquet'
    
    files_to_check.extend([outcomes_path, metadata_path])

print("File sizes and data types:")
for file_path in sorted(files_to_check):
    if os.path.exists(file_path):
        size_bytes = os.path.getsize(file_path)
        size_mb = size_bytes / 1024 / 1024
        
        if file_path.endswith('.npy'):
            # Load numpy array to check dtype
            arr = np.load(file_path)
            print(f"{file_path:35} : {size_mb:6.2f} MB - {arr.dtype} - shape {arr.shape}")
            
            # Check for mixed precision issues
            if arr.dtype == np.float32:
                # Check if values could be float64 precision
                test_val = arr[0, 0] if arr.size > 0 else 0
                print(f"  Sample value: {test_val} (as {arr.dtype})")
                
        elif file_path.endswith('.parquet'):
            # Load metadata to check dtypes
            df = pd.read_parquet(file_path)
            print(f"{file_path:35} : {size_mb:6.2f} MB - {len(df)} rows")
            
            # Check datetime precision
            if 'valid_time' in df.columns:
                print(f"  valid_time dtype: {df['valid_time'].dtype}")
                print(f"  valid_time sample: {df['valid_time'].iloc[0]}")
    else:
        print(f"{file_path:35} : NOT FOUND")

print("\n=== MEMORY LAYOUT ANALYSIS ===")

# Check if all databases have same memory footprint
sizes = {}
for horizon in horizons:
    path = f'outcomes/outcomes_{horizon}.npy'
    if os.path.exists(path):
        size = os.path.getsize(path)
        sizes[horizon] = size
        arr = np.load(path)
        expected_size = arr.size * arr.itemsize
        print(f"{horizon}: File {size} bytes, Expected {expected_size} bytes, Match: {size == expected_size}")

# Check for unexpected size differences
unique_sizes = set(sizes.values())
if len(unique_sizes) == 1:
    print("⚠️  All databases have IDENTICAL file sizes - suspicious for different horizons!")
else:
    print("✅ Databases have different file sizes as expected")

print("\n=== PRECISION ANALYSIS ===")

# Check floating point precision consistency
for horizon in ['6h', '12h', '48h']:  # Skip corrupted 24h
    path = f'outcomes/outcomes_{horizon}.npy'
    if os.path.exists(path):
        arr = np.load(path)
        
        # Check for precision patterns
        col_0 = arr[:, 0]  # z500 values
        
        # Look for repeated decimal patterns that might indicate data duplication
        unique_vals = len(np.unique(col_0))
        total_vals = len(col_0)
        uniqueness_ratio = unique_vals / total_vals
        
        print(f"{horizon} z500 uniqueness: {unique_vals}/{total_vals} ({uniqueness_ratio:.3f})")
        
        # Check decimal precision
        sample_vals = col_0[:10]
        print(f"  First 10 z500 values: {sample_vals}")

print("\n=== STORAGE EFFICIENCY ANALYSIS ===")

# Recommend optimal data types
print("Storage recommendations:")
print("- Current: float32 (4 bytes/value)")
print("- Alternative: float64 (8 bytes/value) - higher precision")
print("- Alternative: float16 (2 bytes/value) - if precision allows")

for horizon in ['6h', '12h', '48h']:
    path = f'outcomes/outcomes_{horizon}.npy'
    if os.path.exists(path):
        arr = np.load(path)
        current_size = arr.nbytes / 1024 / 1024
        
        # Test float64 storage
        float64_size = arr.size * 8 / 1024 / 1024
        
        print(f"{horizon}: {current_size:.2f}MB (float32) vs {float64_size:.2f}MB (float64)")