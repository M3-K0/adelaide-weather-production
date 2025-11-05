#!/usr/bin/env python3
"""
Diagnose 6h-12h temporal correlation issue
"""
import numpy as np
import pandas as pd
from pathlib import Path

print("=== 6H-12H TEMPORAL CORRELATION DIAGNOSIS ===")

# Load 6h and 12h databases
outcomes_6h = np.load('outcomes/outcomes_6h.npy')
outcomes_12h = np.load('outcomes/outcomes_12h.npy')
metadata_6h = pd.read_parquet('outcomes/metadata_6h_clean.parquet')
metadata_12h = pd.read_parquet('outcomes/metadata_12h_clean.parquet')

print(f"6h database shape: {outcomes_6h.shape}")
print(f"12h database shape: {outcomes_12h.shape}")

# Calculate correlation matrix for all variables
variables = ['z500', 't2m', 't850', 'q850', 'u10', 'v10', 'u850', 'v850', 'cape']

print("\n=== VARIABLE-BY-VARIABLE CORRELATION ANALYSIS ===")
for i, var in enumerate(variables):
    if outcomes_6h.shape[0] == outcomes_12h.shape[0]:
        correlation = np.corrcoef(outcomes_6h[:, i], outcomes_12h[:, i])[0, 1]
        print(f"{var:>8}: {correlation:.6f}")
        
        if correlation > 0.999:
            print(f"         ⚠️  CRITICAL: Nearly identical ({correlation:.6f})")
        elif correlation > 0.95:
            print(f"         ⚠️  WARNING: High correlation ({correlation:.6f})")

# Check for exact duplicates
print("\n=== EXACT DUPLICATE ANALYSIS ===")
for i, var in enumerate(variables):
    if outcomes_6h.shape[0] == outcomes_12h.shape[0]:
        exact_matches = np.sum(outcomes_6h[:, i] == outcomes_12h[:, i])
        match_percentage = 100 * exact_matches / len(outcomes_6h)
        print(f"{var:>8}: {exact_matches:,}/{len(outcomes_6h):,} exact matches ({match_percentage:.1f}%)")

# Check temporal offset patterns
print("\n=== TEMPORAL PATTERN ANALYSIS ===")
print(f"6h  init_time range: {metadata_6h['init_time'].min()} to {metadata_6h['init_time'].max()}")
print(f"12h init_time range: {metadata_12h['init_time'].min()} to {metadata_12h['init_time'].max()}")
print(f"6h  valid_time range: {metadata_6h['valid_time'].min()} to {metadata_6h['valid_time'].max()}")  
print(f"12h valid_time range: {metadata_12h['valid_time'].min()} to {metadata_12h['valid_time'].max()}")

# Check if datasets are using same init_times
init_times_6h = set(metadata_6h['init_time'])
init_times_12h = set(metadata_12h['init_time'])
common_init_times = init_times_6h.intersection(init_times_12h)
print(f"\nCommon init_times: {len(common_init_times):,}/{len(init_times_6h):,} ({100*len(common_init_times)/len(init_times_6h):.1f}%)")

if len(common_init_times) == len(init_times_6h):
    print("⚠️  PROBLEM: Both databases use IDENTICAL init_times!")
    print("   This means they're extracting from the same temporal pattern set")
    print("   6h should extract weather at t+6h, 12h should extract at t+12h")

# Sample a few patterns to show the issue
print("\n=== SAMPLE PATTERN COMPARISON ===")
for idx in [0, 100, 1000]:
    if idx < len(metadata_6h) and idx < len(metadata_12h):
        print(f"\nPattern {idx}:")
        print(f"  6h:  init={metadata_6h.iloc[idx]['init_time']} -> valid={metadata_6h.iloc[idx]['valid_time']}")
        print(f"  12h: init={metadata_12h.iloc[idx]['init_time']} -> valid={metadata_12h.iloc[idx]['valid_time']}")
        print(f"  z500: 6h={outcomes_6h[idx, 0]:.3f}, 12h={outcomes_12h[idx, 0]:.3f}")
        print(f"  t2m:  6h={outcomes_6h[idx, 1]:.3f}, 12h={outcomes_12h[idx, 1]:.3f}")

# Test the theory: Are both databases using the same ERA5 time slices?
print("\n=== ERA5 ACCESS PATTERN DIAGNOSIS ===")
print("Testing hypothesis: Both databases extract from same ERA5 time coordinates")

# Check if there's a systematic offset pattern
if outcomes_6h.shape[0] == outcomes_12h.shape[0] and outcomes_6h.shape[0] > 1:
    # Test if 6h[i] == 12h[i-1] or 12h[i] == 6h[i-1] (shifted access)
    z500_6h = outcomes_6h[:, 0]
    z500_12h = outcomes_12h[:, 0]
    
    # Test forward shift: 6h[i+1] vs 12h[i]
    if len(z500_6h) > 1:
        forward_correlation = np.corrcoef(z500_6h[1:], z500_12h[:-1])[0, 1]
        print(f"Forward shift correlation (6h[i+1] vs 12h[i]): {forward_correlation:.6f}")
    
    # Test backward shift: 6h[i] vs 12h[i+1] 
    if len(z500_12h) > 1:
        backward_correlation = np.corrcoef(z500_6h[:-1], z500_12h[1:])[0, 1]
        print(f"Backward shift correlation (6h[i] vs 12h[i+1]): {backward_correlation:.6f}")

print("\n=== ROOT CAUSE ASSESSMENT ===")
# Calculate the key correlation that was reported as 0.999990
correlation_z500 = np.corrcoef(outcomes_6h[:, 0], outcomes_12h[:, 0])[0, 1]
print(f"z500 correlation (reported as 0.999990): {correlation_z500:.6f}")

if correlation_z500 > 0.999:
    print("✅ CONFIRMED: 6h and 12h databases are essentially identical")
    print("ROOT CAUSE: Both horizons extract weather from same temporal coordinates")
    print("SOLUTION NEEDED: Fix ERA5 temporal access logic in build_outcomes_database.py")
else:
    print("⚠️  Correlation not as high as expected - need further investigation")