#!/usr/bin/env python3
"""
Analyze CAPE variable corruption across all outcomes databases.
"""

import numpy as np
from pathlib import Path

def analyze_cape_corruption():
    """Analyze CAPE variable corruption in all horizon databases."""
    
    horizons = [6, 12, 24, 48]
    variable_names = ['msl', 't2m', 'd2m', 'u10', 'v10', 'u850', 'v850', 't850', 'cape', 'tp']
    
    print('CAPE Variable Analysis (Column 8):')
    print('=' * 50)
    
    for horizon in horizons:
        outcomes_path = Path(f'outcomes/outcomes_{horizon}h.npy')
        
        if outcomes_path.exists():
            outcomes = np.load(outcomes_path)
            cape_values = outcomes[:, 8]  # CAPE is column 8
            
            total_records = len(cape_values)
            zero_values = np.sum(cape_values == 0.0)
            non_zero_values = total_records - zero_values
            
            print(f'{horizon}h database:')
            print(f'  Total records: {total_records:,}')
            print(f'  Zero values: {zero_values:,} ({zero_values/total_records*100:.1f}%)')
            print(f'  Non-zero values: {non_zero_values:,} ({non_zero_values/total_records*100:.1f}%)')
            
            if non_zero_values > 0:
                non_zero_cape = cape_values[cape_values != 0.0]
                print(f'  CAPE range: {np.min(non_zero_cape):.2f} - {np.max(non_zero_cape):.2f} J/kg')
                print(f'  CAPE mean (non-zero): {np.mean(non_zero_cape):.2f} J/kg')
                print(f'  CAPE mean (all): {np.mean(cape_values):.2f} J/kg')
                
                # Calculate corruption rate
                corruption_rate = zero_values / total_records * 100
                print(f'  🎯 CORRUPTION RATE: {corruption_rate:.1f}%')
                
                if corruption_rate < 1.0:
                    print(f'  ✅ SUCCESS: CAPE corruption < 1%!')
                elif corruption_rate < 10:
                    print(f'  👍 GOOD: CAPE corruption < 10%')
                elif corruption_rate < 50:
                    print(f'  ⚠️ MODERATE: CAPE corruption {corruption_rate:.1f}%')
                else:
                    print(f'  ❌ HIGH: CAPE corruption {corruption_rate:.1f}%')
            else:
                print(f'  ❌ ALL CAPE VALUES ARE ZERO - 100% CORRUPTION')
            
            print()
        else:
            print(f'{horizon}h database: FILE NOT FOUND')
            print()

if __name__ == "__main__":
    analyze_cape_corruption()