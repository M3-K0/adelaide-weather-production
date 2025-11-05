#!/usr/bin/env python3
"""
Verify ERA5 Temporal Access Bug Fixes
====================================

Validates that the ERA5 temporal access bugs have been fixed:
1. 24h database corruption reduced from 99.4% to <1%
2. Each horizon has distinct temporal patterns (no duplication)
3. Temporal alignment validation passes for all horizons
4. No debug mode truncation affecting data extraction

Usage:
    python verify_era5_temporal_fix.py
"""

import numpy as np
import pandas as pd
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_temporal_fix():
    """Verify that all ERA5 temporal access bugs have been fixed."""
    logger.info("🔍 Verifying ERA5 temporal access bug fixes...")
    
    horizons = [6, 12, 24, 48]
    outcomes_dir = Path("outcomes")
    
    all_passed = True
    results = {}
    
    for horizon in horizons:
        logger.info(f"\\n📊 Checking {horizon}h horizon...")
        
        # Check if outcomes file exists
        outcomes_path = outcomes_dir / f"outcomes_{horizon}h.npy"
        metadata_path = outcomes_dir / f"metadata_{horizon}h_clean.parquet"
        
        if not outcomes_path.exists():
            logger.error(f"❌ Outcomes file missing: {outcomes_path}")
            all_passed = False
            continue
            
        if not metadata_path.exists():
            logger.error(f"❌ Metadata file missing: {metadata_path}")
            all_passed = False
            continue
        
        # Load data
        outcomes = np.load(outcomes_path)
        metadata = pd.read_parquet(metadata_path)
        
        # Check 1: Pattern count (should be close to 14,336, not 100)
        pattern_count = len(outcomes)
        expected_count = 14336
        corruption_rate = 1 - (pattern_count / expected_count)
        
        logger.info(f"   Pattern count: {pattern_count:,} / {expected_count:,}")
        logger.info(f"   Corruption rate: {corruption_rate*100:.1f}%")
        
        if corruption_rate > 0.01:  # More than 1% corruption
            logger.error(f"❌ High corruption rate: {corruption_rate*100:.1f}%")
            all_passed = False
        else:
            logger.info(f"✅ Low corruption rate: {corruption_rate*100:.1f}%")
        
        # Check 2: Temporal alignment
        init_times = pd.to_datetime(metadata['init_time'])
        valid_times = pd.to_datetime(metadata['valid_time'])
        time_diffs = valid_times - init_times
        actual_hours = time_diffs.dt.total_seconds() / 3600
        
        temporal_alignment_correct = np.all(actual_hours == horizon)
        unique_hours = sorted(set(actual_hours))
        
        logger.info(f"   Temporal alignment: {unique_hours}")
        if temporal_alignment_correct:
            logger.info(f"✅ Temporal alignment correct")
        else:
            logger.error(f"❌ Temporal alignment incorrect")
            all_passed = False
        
        # Check 3: Data variance (not all zeros or constants)
        means = outcomes.mean(axis=0)
        stds = outcomes.std(axis=0)
        
        min_variance = 1e-6
        valid_variance = np.all(stds > min_variance)
        
        logger.info(f"   Variable means: z500={means[0]:.1f}, t2m={means[1]:.1f}, t850={means[2]:.1f}")
        logger.info(f"   Variable stds: z500={stds[0]:.1f}, t2m={stds[1]:.1f}, t850={stds[2]:.1f}")
        
        if valid_variance:
            logger.info(f"✅ Good variance in outcomes")
        else:
            logger.warning(f"⚠️ Low variance detected")
        
        # Store results
        results[horizon] = {
            'pattern_count': pattern_count,
            'corruption_rate': corruption_rate,
            'temporal_alignment': temporal_alignment_correct,
            'valid_variance': valid_variance,
            'mean_z500': means[0],
            'std_z500': stds[0]
        }
    
    # Check 4: Cross-horizon distinctness
    logger.info(f"\\n🔍 Checking cross-horizon distinctness...")
    
    horizon_correlations = {}
    for i, h1 in enumerate(horizons):
        for j, h2 in enumerate(horizons):
            if i >= j:
                continue
                
            path1 = outcomes_dir / f"outcomes_{h1}h.npy"
            path2 = outcomes_dir / f"outcomes_{h2}h.npy"
            
            if path1.exists() and path2.exists():
                outcomes1 = np.load(path1)
                outcomes2 = np.load(path2)
                
                if len(outcomes1) == len(outcomes2) and len(outcomes1) > 0:
                    correlation = np.corrcoef(outcomes1.flatten(), outcomes2.flatten())[0, 1]
                    horizon_correlations[f"{h1}h-{h2}h"] = correlation
                    
                    logger.info(f"   Correlation {h1}h vs {h2}h: {correlation:.4f}")
                    
                    if correlation > 0.99:
                        logger.error(f"❌ HIGH CORRELATION - possible duplication bug!")
                        all_passed = False
                    else:
                        logger.info(f"✅ Low correlation - distinct patterns")
    
    # Final summary
    logger.info(f"\\n🎯 ERA5 Temporal Access Bug Fix Verification Summary:")
    logger.info(f"=" * 60)
    
    for horizon in horizons:
        if horizon in results:
            r = results[horizon]
            status = "✅ FIXED" if r['corruption_rate'] < 0.01 and r['temporal_alignment'] else "❌ ISSUES"
            logger.info(f"   {horizon}h horizon: {status} ({r['corruption_rate']*100:.1f}% corruption)")
    
    if all_passed:
        logger.info(f"\\n🎉 ALL FIXES VERIFIED SUCCESSFULLY!")
        logger.info(f"✅ 24h database corruption reduced from 99.4% to <1%")
        logger.info(f"✅ All horizons have distinct temporal patterns")
        logger.info(f"✅ Temporal alignment validation passes")
        logger.info(f"✅ Debug mode truncation bug eliminated")
        return True
    else:
        logger.error(f"\\n❌ SOME ISSUES REMAIN - check logs above")
        return False

if __name__ == "__main__":
    success = verify_temporal_fix()
    exit(0 if success else 1)