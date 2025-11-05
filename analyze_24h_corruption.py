#!/usr/bin/env python3
"""
Analyze 24h database corruption patterns
"""
import numpy as np

# Load 24h outcomes for detailed analysis
outcomes_24h = np.load('outcomes/outcomes_24h.npy')
print('=== 24H CORRUPTION ANALYSIS ===')
print(f'Shape: {outcomes_24h.shape}')
print(f'Total values: {outcomes_24h.size}')

# Analyze zeros by column (variable)
for col in range(outcomes_24h.shape[1]):
    zeros = np.sum(outcomes_24h[:, col] == 0)
    total = outcomes_24h.shape[0]
    print(f'Column {col}: {zeros}/{total} zeros ({100*zeros/total:.1f}%)')

print()
# Find rows with ANY non-zero values
non_zero_rows = np.any(outcomes_24h != 0, axis=1)
valid_rows = np.sum(non_zero_rows)
print(f'Rows with ANY non-zero values: {valid_rows}/{outcomes_24h.shape[0]} ({100*valid_rows/outcomes_24h.shape[0]:.1f}%)')

# Sample valid rows
valid_indices = np.where(non_zero_rows)[0]
print(f'First 10 valid row indices: {valid_indices[:10]}')
if len(valid_indices) > 0:
    print(f'Sample valid row (index {valid_indices[0]}): {outcomes_24h[valid_indices[0]]}')

# Check if corruption is random or systematic
zero_rows = np.all(outcomes_24h == 0, axis=1)
all_zero_count = np.sum(zero_rows)
print(f'Completely zero rows: {all_zero_count}/{outcomes_24h.shape[0]} ({100*all_zero_count/outcomes_24h.shape[0]:.1f}%)')

# Check for contiguous corruption patterns
zero_indices = np.where(zero_rows)[0]
if len(zero_indices) > 1:
    gaps = np.diff(zero_indices)
    print(f'Zero row gaps - min: {gaps.min()}, max: {gaps.max()}, mean: {gaps.mean():.2f}')
    
# Compare with working databases for verification
print('\n=== COMPARISON WITH WORKING DATABASES ===')
for horizon in ['6h', '12h', '48h']:
    data = np.load(f'outcomes/outcomes_{horizon}.npy')
    zero_rows_h = np.all(data == 0, axis=1)
    zero_count_h = np.sum(zero_rows_h)
    print(f'{horizon}: {zero_count_h}/{data.shape[0]} completely zero rows ({100*zero_count_h/data.shape[0]:.1f}%)')