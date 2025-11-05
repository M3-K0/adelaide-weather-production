#!/usr/bin/env python3
"""
Verify if databases are shifted copies of the same data
"""
import numpy as np

print("=== DATA SHIFTING VERIFICATION ===")

# Load working databases
data_6h = np.load('outcomes/outcomes_6h.npy')
data_12h = np.load('outcomes/outcomes_12h.npy')
data_48h = np.load('outcomes/outcomes_48h.npy')

print(f"Database shapes: 6h={data_6h.shape}, 12h={data_12h.shape}, 48h={data_48h.shape}")

# Test hypothesis: 12h = 6h shifted by 1 position
print("\n=== TESTING SHIFT HYPOTHESIS ===")

# Check if 12h[0:n-1] == 6h[1:n] (12h is 6h shifted left by 1)
n = min(data_6h.shape[0], data_12h.shape[0]) - 1

shift_match_6h_12h = np.allclose(data_12h[:n], data_6h[1:n+1], rtol=1e-5)
print(f"12h = 6h shifted left by 1: {shift_match_6h_12h}")

# Check if 48h[0:n-1] == 12h[1:n] (48h is 12h shifted left by 1)
shift_match_12h_48h = np.allclose(data_48h[:n], data_12h[1:n+1], rtol=1e-5)
print(f"48h = 12h shifted left by 1: {shift_match_12h_48h}")

# Check if 48h[0:n-2] == 6h[2:n] (48h is 6h shifted left by 2)
n2 = n - 1
shift_match_6h_48h = np.allclose(data_48h[:n2], data_6h[2:n2+2], rtol=1e-5)
print(f"48h = 6h shifted left by 2: {shift_match_6h_48h}")

if shift_match_6h_12h or shift_match_12h_48h or shift_match_6h_48h:
    print("\n⚠️  CRITICAL BUG CONFIRMED: Databases are shifted copies!")
    print("This indicates the extraction logic is not actually accessing different temporal slices.")
    print("The metadata has correct temporal alignment, but the ERA5 data access is broken.")
else:
    print("\n✅ No shifting pattern detected - databases contain unique data")

# Detailed analysis of first few rows
print("\n=== DETAILED ROW COMPARISON ===")
print("Comparing z500 values (column 0) for first 5 rows:")

for i in range(5):
    print(f"Row {i}: 6h={data_6h[i,0]:.3f}, 12h={data_12h[i,0]:.3f}, 48h={data_48h[i,0]:.3f}")

print("\nChecking if 12h[i] == 6h[i+1]:")
for i in range(5):
    if i < data_6h.shape[0] - 1:
        match = np.isclose(data_12h[i,0], data_6h[i+1,0], rtol=1e-5)
        print(f"  12h[{i}] vs 6h[{i+1}]: {data_12h[i,0]:.3f} vs {data_6h[i+1,0]:.3f} -> {match}")

print("\n=== CORRELATION ANALYSIS ===")
# Calculate correlation between datasets to quantify similarity
for col in range(3):  # Check first 3 variables
    var_names = ['z500', 't2m', 't850'][col]
    
    # Correlations with proper alignment
    corr_6h_12h_aligned = np.corrcoef(data_6h[1:1000, col], data_12h[:999, col])[0,1]
    corr_6h_48h_aligned = np.corrcoef(data_6h[2:1000, col], data_48h[:998, col])[0,1]
    
    print(f"{var_names}: 6h-12h correlation (aligned): {corr_6h_12h_aligned:.6f}")
    print(f"{var_names}: 6h-48h correlation (aligned): {corr_6h_48h_aligned:.6f}")
    
    if corr_6h_12h_aligned > 0.999 or corr_6h_48h_aligned > 0.999:
        print(f"  ⚠️  EXTREMELY HIGH CORRELATION - LIKELY DUPLICATE DATA!")