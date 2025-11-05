#!/usr/bin/env python3
"""
Check all outcomes databases for data quality issues.
"""

import numpy as np
from pathlib import Path

def check_outcomes_quality():
    """Check data quality for all horizon outcomes."""
    
    horizons = [6, 12, 24, 48]
    
    for horizon in horizons:
        outcomes_path = Path(f"outcomes/outcomes_{horizon}h.npy")
        
        if not outcomes_path.exists():
            print(f"❌ {horizon}h: File not found")
            continue
        
        outcomes = np.load(outcomes_path)
        t2m_values = outcomes[:, 1]  # t2m is index 1
        
        # Check data quality
        total_records = len(outcomes)
        zero_values = np.sum(t2m_values == 0)
        valid_values = total_records - zero_values
        
        print(f"📊 {horizon}h outcomes:")
        print(f"   Total records: {total_records}")
        print(f"   Zero values: {zero_values}")
        print(f"   Valid values: {valid_values}")
        print(f"   Valid %: {valid_values/total_records*100:.1f}%")
        
        if valid_values > 0:
            valid_temps = t2m_values[t2m_values > 0]
            print(f"   Temp range: {np.min(valid_temps):.1f}K - {np.max(valid_temps):.1f}K")
            print(f"   Temp range: {np.min(valid_temps)-273.15:.1f}°C - {np.max(valid_temps)-273.15:.1f}°C")
        
        print()

if __name__ == "__main__":
    check_outcomes_quality()