#!/usr/bin/env python3
"""
Debug the 24h outcomes database to find the -273.1°C issue.
"""

import numpy as np
import pandas as pd
from pathlib import Path

def debug_24h_outcomes():
    """Debug temperature values in 24h outcomes."""
    
    outcomes_path = Path("outcomes/outcomes_24h.npy")
    
    if not outcomes_path.exists():
        print(f"❌ Outcomes not found: {outcomes_path}")
        return
    
    print("🔍 Loading 24h outcomes for debugging...")
    outcomes = np.load(outcomes_path)
    
    print(f"📊 Outcomes shape: {outcomes.shape}")
    
    # Check temperature variable (t2m is index 1)
    t2m_values = outcomes[:, 1]
    
    print(f"\n🌡️ Temperature (t2m) statistics:")
    print(f"   Min: {np.min(t2m_values):.2f}K ({np.min(t2m_values) - 273.15:.2f}°C)")
    print(f"   Max: {np.max(t2m_values):.2f}K ({np.max(t2m_values) - 273.15:.2f}°C)")
    print(f"   Mean: {np.mean(t2m_values):.2f}K ({np.mean(t2m_values) - 273.15:.2f}°C)")
    print(f"   Std: {np.std(t2m_values):.2f}K")
    
    # Check for problematic values
    zero_values = np.sum(t2m_values == 0)
    very_low_values = np.sum(t2m_values < 200)  # Below -73°C
    very_high_values = np.sum(t2m_values > 350)  # Above 77°C
    
    print(f"\n⚠️ Problematic values:")
    print(f"   Zero values: {zero_values}")
    print(f"   < 200K (-73°C): {very_low_values}")
    print(f"   > 350K (77°C): {very_high_values}")
    
    if zero_values > 0:
        print(f"\n🔍 Zero value indices:")
        zero_indices = np.where(t2m_values == 0)[0]
        print(f"   First 10: {zero_indices[:10]}")
        
        # Check the corresponding rows
        print(f"\n📋 Full records for first zero temperature:")
        for i in zero_indices[:3]:
            print(f"   Row {i}: {outcomes[i]}")
    
    if very_low_values > 0:
        print(f"\n🔍 Very low value indices:")
        low_indices = np.where(t2m_values < 200)[0]
        print(f"   First 10: {low_indices[:10]}")
        print(f"   Values: {t2m_values[low_indices[:10]]}")

if __name__ == "__main__":
    debug_24h_outcomes()