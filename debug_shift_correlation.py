#!/usr/bin/env python3
"""
Debug the 1.000000 shift correlation issue
"""
import numpy as np
import pandas as pd

print("=== SHIFT CORRELATION DEBUG ===")

# Load databases
outcomes_6h = np.load('outcomes/outcomes_6h.npy')
outcomes_12h = np.load('outcomes/outcomes_12h.npy')

print(f"Database shapes: 6h={outcomes_6h.shape}, 12h={outcomes_12h.shape}")

# Focus on z500 column (index 0)
z500_6h = outcomes_6h[:, 0]
z500_12h = outcomes_12h[:, 0]

print(f"\n=== DETAILED CORRELATION ANALYSIS ===")

# Direct correlation (what we saw: 0.969940)
direct_corr = np.corrcoef(z500_6h, z500_12h)[0, 1]
print(f"Direct correlation (6h vs 12h): {direct_corr:.6f}")

# Forward shift: 6h[i+1] vs 12h[i] (what we saw: 1.000000)
if len(z500_6h) > 1:
    forward_corr = np.corrcoef(z500_6h[1:], z500_12h[:-1])[0, 1]
    print(f"Forward shift correlation (6h[i+1] vs 12h[i]): {forward_corr:.6f}")

# Backward shift: 6h[i] vs 12h[i+1]
if len(z500_12h) > 1:
    backward_corr = np.corrcoef(z500_6h[:-1], z500_12h[1:])[0, 1]
    print(f"Backward shift correlation (6h[i] vs 12h[i+1]): {backward_corr:.6f}")

# The 1.000000 correlation is PROOF of duplication!
print(f"\n=== DUPLICATION ANALYSIS ===")

# Check specific values to understand the shift
print("Sample values to show the pattern:")
for i in range(min(10, len(z500_6h)-1)):
    z6h_curr = z500_6h[i]
    z6h_next = z500_6h[i+1]
    z12h_curr = z500_12h[i]
    
    print(f"Index {i}: 6h[{i}]={z6h_curr:.3f}, 6h[{i+1}]={z6h_next:.3f}, 12h[{i}]={z12h_curr:.3f}")
    
    # Check if 6h[i+1] == 12h[i]
    if abs(z6h_next - z12h_curr) < 0.001:
        print(f"  ✅ MATCH: 6h[{i+1}] == 12h[{i}] (exact duplicate!)")
    else:
        print(f"  No match (diff: {abs(z6h_next - z12h_curr):.6f})")

# Count exact matches for the shift pattern
exact_matches = 0
for i in range(min(len(z500_6h)-1, len(z500_12h))):
    if abs(z500_6h[i+1] - z500_12h[i]) < 0.001:
        exact_matches += 1

total_checks = min(len(z500_6h)-1, len(z500_12h))
match_percentage = 100 * exact_matches / total_checks

print(f"\nExact matches for shift pattern: {exact_matches}/{total_checks} ({match_percentage:.1f}%)")

if match_percentage > 99:
    print("🚨 CRITICAL FINDING: 12h database is a SHIFTED COPY of 6h database!")
    print("   This means: 12h[i] = 6h[i+1]")
    print("   ROOT CAUSE: Time indexing error in database construction")
    
    # Check the temporal implications
    print(f"\n=== TIME INDEX ERROR ANALYSIS ===")
    
    # Load metadata to understand the indexing
    metadata_6h = pd.read_parquet('outcomes/metadata_6h_clean.parquet')
    metadata_12h = pd.read_parquet('outcomes/metadata_12h_clean.parquet')
    
    print("Checking if time indexing explains the shift:")
    for i in range(min(5, len(metadata_6h)-1, len(metadata_12h))):
        init_6h_curr = metadata_6h.iloc[i]['init_time']
        init_6h_next = metadata_6h.iloc[i+1]['init_time']
        init_12h_curr = metadata_12h.iloc[i]['init_time']
        
        valid_6h_curr = metadata_6h.iloc[i]['valid_time']
        valid_6h_next = metadata_6h.iloc[i+1]['valid_time']
        valid_12h_curr = metadata_12h.iloc[i]['valid_time']
        
        print(f"\nPattern {i}:")
        print(f"  6h[{i}]:   init={init_6h_curr} -> valid={valid_6h_curr}")
        print(f"  6h[{i+1}]: init={init_6h_next} -> valid={valid_6h_next}")
        print(f"  12h[{i}]:  init={init_12h_curr} -> valid={valid_12h_curr}")
        
        # Check if valid_6h_next == valid_12h_curr
        if str(valid_6h_next) == str(valid_12h_curr):
            print(f"  🎯 TIME MATCH: 6h[{i+1}] valid_time == 12h[{i}] valid_time")
            print(f"      This means 12h[{i}] extracted from same time as 6h[{i+1}]!")
        else:
            print(f"  No time match")

print(f"\n=== SOLUTION REQUIRED ===")
print("The 12h database contains shifted data from the 6h timeline")
print("This is NOT a correlation issue - it's a database construction bug")
print("SOLUTION: Fix the ERA5 time coordinate access in build_outcomes_database.py")
print("The issue is likely in the extract_outcome_at_time() method")