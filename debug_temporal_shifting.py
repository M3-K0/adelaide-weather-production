#!/usr/bin/env python3
"""
Debug temporal shifting issue - determine where the 6h->12h shift occurs
"""
import numpy as np
import pandas as pd
from pathlib import Path

print("=== TEMPORAL SHIFTING DEBUG ===")

# Load metadata for both horizons
metadata_6h = pd.read_parquet('outcomes/metadata_6h_clean.parquet')
metadata_12h = pd.read_parquet('outcomes/metadata_12h_clean.parquet')

print(f"6h metadata shape: {metadata_6h.shape}")
print(f"12h metadata shape: {metadata_12h.shape}")

# Check if they have the same init_times (bad) or different ones (good)
print("\n=== METADATA TEMPORAL ALIGNMENT ===")
print("First 10 patterns comparison:")
for i in range(min(10, len(metadata_6h), len(metadata_12h))):
    init_6h = metadata_6h.iloc[i]['init_time']
    init_12h = metadata_12h.iloc[i]['init_time']
    valid_6h = metadata_6h.iloc[i]['valid_time']
    valid_12h = metadata_12h.iloc[i]['valid_time']
    
    print(f"Pattern {i}:")
    print(f"  6h:  init={init_6h} -> valid={valid_6h}")
    print(f"  12h: init={init_12h} -> valid={valid_12h}")
    
    if str(init_6h) == str(init_12h):
        print(f"  ⚠️  SAME init_time - this is the problem!")
    
    # Check the time offset
    init_6h_dt = pd.to_datetime(init_6h)
    init_12h_dt = pd.to_datetime(init_12h)
    valid_6h_dt = pd.to_datetime(valid_6h)
    valid_12h_dt = pd.to_datetime(valid_12h)
    
    offset_6h = (valid_6h_dt - init_6h_dt).total_seconds() / 3600
    offset_12h = (valid_12h_dt - init_12h_dt).total_seconds() / 3600
    
    print(f"  6h offset:  {offset_6h:.0f}h")
    print(f"  12h offset: {offset_12h:.0f}h")
    print()

# Check for shifted pattern: Does 6h[i+1] match 12h[i]?
print("\n=== SHIFT PATTERN INVESTIGATION ===")
print("Testing if 6h[i+1] init_time matches 12h[i] init_time:")

matches = 0
total_checks = min(len(metadata_6h)-1, len(metadata_12h))

for i in range(total_checks):
    init_6h_next = metadata_6h.iloc[i+1]['init_time']
    init_12h_current = metadata_12h.iloc[i]['init_time']
    
    if str(init_6h_next) == str(init_12h_current):
        matches += 1
        
    if i < 5:  # Show first 5 examples
        print(f"  Pattern {i}: 6h[{i+1}]={init_6h_next} vs 12h[{i}]={init_12h_current} - {'MATCH' if str(init_6h_next) == str(init_12h_current) else 'no match'}")

match_percentage = 100 * matches / total_checks if total_checks > 0 else 0
print(f"\nShift pattern analysis: {matches}/{total_checks} matches ({match_percentage:.1f}%)")

if match_percentage > 95:
    print("✅ CONFIRMED: 6h and 12h databases are shifted by 1 time step!")
    print("   6h[i+1] init_time == 12h[i] init_time")
    print("   This means 12h database is accessing 6h-delayed data")

# Check original embedding metadata to see if issue is there
print("\n=== ORIGINAL EMBEDDING METADATA CHECK ===")
try:
    emb_meta_6h = pd.read_parquet('embeddings/metadata_6h.parquet')
    emb_meta_12h = pd.read_parquet('embeddings/metadata_12h.parquet')
    
    print(f"Embedding metadata shapes: 6h={emb_meta_6h.shape}, 12h={emb_meta_12h.shape}")
    
    # Check first few patterns in embedding metadata
    print("First 3 patterns in embedding metadata:")
    for i in range(min(3, len(emb_meta_6h), len(emb_meta_12h))):
        init_6h = emb_meta_6h.iloc[i]['init_time']
        init_12h = emb_meta_12h.iloc[i]['init_time']
        valid_6h = emb_meta_6h.iloc[i]['valid_time']
        valid_12h = emb_meta_12h.iloc[i]['valid_time']
        
        print(f"  Pattern {i}:")
        print(f"    6h:  init={init_6h} -> valid={valid_6h}")
        print(f"    12h: init={init_12h} -> valid={valid_12h}")
        
        if str(init_6h) == str(init_12h):
            print(f"    ⚠️  SAME init_time in embedding metadata!")
            
except Exception as e:
    print(f"Could not load embedding metadata: {e}")

print("\n=== DIAGNOSIS SUMMARY ===")
print("The issue appears to be that both 6h and 12h databases:")
print("1. Use the SAME set of init_times")
print("2. Extract weather at different valid_times (init + horizon)")
print("3. But this creates a temporal shift rather than true distinctness")
print()
print("EXPECTED BEHAVIOR:")
print("- 6h should extract weather patterns at t+6h for a given set of init_times")
print("- 12h should extract weather patterns at t+12h for THE SAME init_times")
print("- This would show how weather evolves from 6h to 12h forecast horizon")
print()
print("ACTUAL BEHAVIOR:")
print("- Both use same init_times")
print("- 6h extracts at t+6h, 12h extracts at t+12h")
print("- This gives different time slices but not comparable forecasts")
print()
print("SOLUTION: Keep same init_times but ensure outcomes extraction is correct")