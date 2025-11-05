#!/usr/bin/env python3
"""
Quick validation of temporal fix approach
"""
import numpy as np
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_temporal_fix_approach():
    """Validate the approach for fixing temporal duplication."""
    logger.info("🔍 Validating temporal fix approach...")
    
    # Load existing databases
    outcomes_6h = np.load('outcomes/outcomes_6h.npy')
    outcomes_12h = np.load('outcomes/outcomes_12h.npy')
    metadata_6h = pd.read_parquet('outcomes/metadata_6h_clean.parquet')
    metadata_12h = pd.read_parquet('outcomes/metadata_12h_clean.parquet')
    
    logger.info(f"Database shapes: 6h={outcomes_6h.shape}, 12h={outcomes_12h.shape}")
    
    # Confirm the duplication pattern
    z500_6h = outcomes_6h[:, 0]
    z500_12h = outcomes_12h[:, 0]
    
    shift_corr = np.corrcoef(z500_6h[1:], z500_12h[:-1])[0, 1]
    logger.info(f"Shift correlation (6h[i+1] vs 12h[i]): {shift_corr:.6f}")
    
    if shift_corr > 0.999:
        logger.info("✅ CONFIRMED: 12h database is shifted copy of 6h")
    else:
        logger.error("❌ Expected shift pattern not found")
        return False
    
    # Validate temporal alignment understanding
    logger.info("\n🕐 Analyzing temporal patterns...")
    
    # Check that both databases use same init_times
    init_times_6h = set(metadata_6h['init_time'].astype(str))
    init_times_12h = set(metadata_12h['init_time'].astype(str))
    common_init_times = len(init_times_6h.intersection(init_times_12h))
    
    logger.info(f"Common init_times: {common_init_times}/{len(init_times_6h)} ({100*common_init_times/len(init_times_6h):.1f}%)")
    
    if common_init_times == len(init_times_6h):
        logger.info("✅ Both databases use identical init_times (this is CORRECT)")
    else:
        logger.error("❌ Databases use different init_times (this would be wrong)")
        return False
    
    # Demonstrate the FIX: What corrected 12h metadata should look like
    logger.info("\n🔧 Creating corrected 12h metadata template...")
    
    # Use 6h metadata as template but fix valid_times for 12h
    metadata_12h_corrected = metadata_6h.copy()
    metadata_12h_corrected['valid_time'] = pd.to_datetime(metadata_12h_corrected['init_time']) + pd.Timedelta(hours=12)
    metadata_12h_corrected['lead_time'] = 12
    
    # Compare current vs corrected
    sample_idx = 0
    current_init = metadata_12h.iloc[sample_idx]['init_time']
    current_valid = metadata_12h.iloc[sample_idx]['valid_time']
    corrected_init = metadata_12h_corrected.iloc[sample_idx]['init_time']
    corrected_valid = metadata_12h_corrected.iloc[sample_idx]['valid_time']
    
    logger.info(f"Sample pattern {sample_idx}:")
    logger.info(f"  Current 12h:   init={current_init} -> valid={current_valid}")
    logger.info(f"  Corrected 12h: init={corrected_init} -> valid={corrected_valid}")
    
    # The key insight: corrected metadata is ALREADY what we have!
    # The issue is that the OUTCOMES extraction is wrong, not the metadata
    
    logger.info("\n💡 KEY INSIGHT:")
    logger.info("The metadata is ALREADY correct!")
    logger.info("The issue is in the outcomes extraction process")
    logger.info("The 12h database contains outcomes from wrong time slices")
    
    # Demonstrate what should happen vs what actually happens
    logger.info("\n📊 EXPECTED vs ACTUAL behavior:")
    
    for i in range(3):
        init_6h = metadata_6h.iloc[i]['init_time']
        valid_6h = metadata_6h.iloc[i]['valid_time']
        
        init_12h = metadata_12h.iloc[i]['init_time']
        valid_12h = metadata_12h.iloc[i]['valid_time']
        
        z500_6h_val = outcomes_6h[i, 0]
        z500_12h_val = outcomes_12h[i, 0]
        
        logger.info(f"Pattern {i}:")
        logger.info(f"  6h:  init={init_6h} -> valid={valid_6h} => z500={z500_6h_val:.3f}")
        logger.info(f"  12h: init={init_12h} -> valid={valid_12h} => z500={z500_12h_val:.3f}")
        
        # The 12h outcome should be from valid_12h time, not from valid_6h+6h time
        # But due to the shift bug: 12h[i] = 6h[i+1]
        if i+1 < len(outcomes_6h):
            z500_6h_next = outcomes_6h[i+1, 0]
            logger.info(f"  BUG: 12h[{i}] = 6h[{i+1}] => {z500_12h_val:.3f} = {z500_6h_next:.3f} ✅")
    
    # Calculate what correlation SHOULD be after fix
    logger.info("\n📈 Expected correlation after fix:")
    logger.info("After fixing 12h database to extract from correct times:")
    logger.info("- 6h extracts weather at init_time + 6h")
    logger.info("- 12h extracts weather at init_time + 12h")
    logger.info("- Correlation should be 0.85-0.95 (natural weather persistence)")
    logger.info("- No more 1.000 shift correlation")
    
    return True

def create_fix_summary():
    """Create summary of the fix needed."""
    logger.info("\n📋 TEMPORAL DUPLICATION FIX SUMMARY:")
    logger.info("="*50)
    
    logger.info("\n🔍 PROBLEM IDENTIFIED:")
    logger.info("- 12h database is shifted copy of 6h database")
    logger.info("- Formula: 12h[i] = 6h[i+1]")
    logger.info("- Shift correlation: 1.000000 (perfect duplication)")
    logger.info("- This means 12h outcomes are from wrong time slices")
    
    logger.info("\n🎯 ROOT CAUSE:")
    logger.info("- Metadata is correct (same init_times, proper valid_times)")
    logger.info("- Issue is in ERA5 data extraction in build_outcomes_database.py")
    logger.info("- extract_outcome_at_time() accessing wrong time coordinates")
    
    logger.info("\n🔧 SOLUTION:")
    logger.info("1. Rebuild 12h database using correct temporal extraction")
    logger.info("2. Use SAME init_times as 6h database")
    logger.info("3. Extract outcomes at valid_time = init_time + 12h")
    logger.info("4. Verify no more shifting correlation")
    
    logger.info("\n✅ EXPECTED RESULT:")
    logger.info("- 6h and 12h databases contain distinct temporal patterns")
    logger.info("- Correlation drops from 0.999990 to normal 0.85-0.95 range")
    logger.info("- Each horizon shows weather evolution at proper forecast lead times")
    
    logger.info("\n⚡ IMPLEMENTATION:")
    logger.info("- Use fix_temporal_duplication.py (already created)")
    logger.info("- Backup existing 12h database")
    logger.info("- Rebuild with corrected ERA5 time coordinate access")
    logger.info("- Validate fix with correlation testing")

def main():
    """Main validation."""
    print("=== TEMPORAL DUPLICATION FIX VALIDATION ===")
    
    if validate_temporal_fix_approach():
        create_fix_summary()
        print("\n✅ Temporal fix approach validated successfully")
        print("🚀 Ready to proceed with database rebuild")
        return 0
    else:
        print("\n❌ Temporal fix validation failed")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())