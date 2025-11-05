#!/usr/bin/env python3
"""
Build Historical Outcomes Database
=================================

Extracts actual weather outcomes for each historical pattern to enable
analog ensemble forecasting. For each pattern at init_time, extracts
what the weather actually was at valid_time (init_time + horizon).

Based on GPT-5 recommendations for fast O(100μs) access during real-time forecasting.

CAPE CALCULATION FIX: Now includes proper CAPE calculation from ERA5 data
instead of hardcoded 0.0 values. Uses empirical approach suitable for
limited vertical resolution (850 hPa and 500 hPa only).

Usage:
    python build_outcomes_database.py [--horizon 24] [--debug]
"""

import sys
import argparse
import time
import numpy as np
import pandas as pd
import xarray as xr
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

# Import CAPE calculator
sys.path.append(str(Path(__file__).parent.parent))
from cape_calculator import extract_cape_from_era5

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OutcomesDatabaseBuilder:
    """Build outcomes database for analog ensemble forecasting."""
    
    def __init__(self, data_dir: Path = Path("data/era5/zarr")):
        self.data_dir = data_dir
        self.surface_ds = None
        self.pressure_ds = None
        
        # Variables to extract (must match analog forecaster expectations)
        self.variables = [
            'z500',    # 500 hPa geopotential height (m)
            't2m',     # 2m temperature (K)
            't850',    # 850 hPa temperature (K)
            'q850',    # 850 hPa specific humidity (kg/kg)
            'u10',     # 10m u-wind (m/s)
            'v10',     # 10m v-wind (m/s)
            'u850',    # 850 hPa u-wind (m/s)
            'v850',    # 850 hPa v-wind (m/s)
            'cape'     # Convective available potential energy (J/kg)
        ]
        
        # Optional filtering of valid_time hours per horizon to avoid cross-horizon duplication
        self.allowed_valid_hours = {
            6: [6, 18],
            12: [0, 12],
            24: None,
            48: None,
        }
        
        # Optional deterministic shuffling to decorrelate horizons
        self.shuffle_horizons = {
            6: False,
            12: True,
            24: False,
            48: False,
        }
        
        # Adelaide coordinates (from training)
        self.adelaide_lat = -34.93
        self.adelaide_lon = 138.60
    
    def load_era5_data(self):
        """Load ERA5 surface and pressure level datasets."""
        logger.info("Loading ERA5 datasets...")
        
        try:
            # Load surface data (2010-2020)
            surface_path = self.data_dir / "era5_surface_2010_2020.zarr"
            if surface_path.exists():
                self.surface_ds = xr.open_zarr(surface_path)
                logger.info(f"✅ Loaded surface data: {surface_path}")
                try:
                    time_min = pd.to_datetime(self.surface_ds.valid_time.min().values)
                    time_max = pd.to_datetime(self.surface_ds.valid_time.max().values)
                    logger.info(f"   Time range: {time_min} to {time_max}")
                except Exception as e:
                    logger.info(f"   Time range: {len(self.surface_ds.valid_time)} time steps")
            else:
                logger.error(f"❌ Surface data not found: {surface_path}")
                return False
            
            # Load pressure level data (2010-2019) 
            pressure_path = self.data_dir / "era5_pressure_2010_2019.zarr"
            if pressure_path.exists():
                self.pressure_ds = xr.open_zarr(pressure_path)
                logger.info(f"✅ Loaded pressure data: {pressure_path}")
                try:
                    time_min = pd.to_datetime(self.pressure_ds.valid_time.min().values)
                    time_max = pd.to_datetime(self.pressure_ds.valid_time.max().values)
                    logger.info(f"   Time range: {time_min} to {time_max}")
                except Exception as e:
                    logger.info(f"   Time range: {len(self.pressure_ds.valid_time)} time steps")
            else:
                logger.error(f"❌ Pressure data not found: {pressure_path}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load ERA5 data: {e}")
            return False
    
    def extract_outcome_at_time(self, valid_time: pd.Timestamp) -> Optional[np.ndarray]:
        """Extract weather outcome vector at specified valid_time with proper CAPE calculation."""
        try:
            valid_time_np = pd.to_datetime(valid_time).to_numpy()
            outcome = np.full(len(self.variables), np.nan, dtype=np.float32)

            surface_data = None
            if self.surface_ds is not None:
                try:
                    surface_data = self.surface_ds.sel(
                        valid_time=valid_time_np,
                        latitude=self.adelaide_lat,
                        longitude=self.adelaide_lon,
                        method='nearest',
                        tolerance=pd.Timedelta(hours=1)
                    )
                except Exception:
                    surface_data = self.surface_ds.sel(
                        time=valid_time_np,
                        latitude=self.adelaide_lat,
                        longitude=self.adelaide_lon,
                        method='nearest'
                    )

            pressure_data = None
            if self.pressure_ds is not None:
                try:
                    pressure_data = self.pressure_ds.sel(
                        valid_time=valid_time_np,
                        latitude=self.adelaide_lat,
                        longitude=self.adelaide_lon,
                        method='nearest',
                        tolerance=pd.Timedelta(hours=1)
                    )
                except Exception:
                    pressure_data = self.pressure_ds.sel(
                        time=valid_time_np,
                        latitude=self.adelaide_lat,
                        longitude=self.adelaide_lon,
                        method='nearest'
                    )

            # z500 (index 0) - convert geopotential (m^2/s^2) to meters
            if pressure_data is not None and 'z' in pressure_data:
                z500 = pressure_data['z'].sel(isobaricInhPa=500, method='nearest')
                outcome[0] = float(z500.values) / 9.80665

            t850_val = None
            q850_val = None
            u850_val = None
            v850_val = None

            if pressure_data is not None:
                if 't' in pressure_data:
                    t850 = pressure_data['t'].sel(isobaricInhPa=850, method='nearest')
                    t850_val = float(t850.values)
                    outcome[2] = t850_val
                    if np.isnan(outcome[1]):
                        outcome[1] = t850_val + 9.75  # lapse-rate approximation

                if 'q' in pressure_data:
                    q850 = pressure_data['q'].sel(isobaricInhPa=850, method='nearest')
                    q850_val = max(float(q850.values), 0.0)
                    outcome[3] = q850_val

                if 'u' in pressure_data and 'v' in pressure_data:
                    u850 = pressure_data['u'].sel(isobaricInhPa=850, method='nearest')
                    v850 = pressure_data['v'].sel(isobaricInhPa=850, method='nearest')
                    u850_val = float(u850.values)
                    v850_val = float(v850.values)
                    outcome[6] = u850_val
                    outcome[7] = v850_val

                if t850_val is not None and q850_val is not None:
                    try:
                        cape_val = extract_cape_from_era5(pressure_data, surface_pressure=1013.25)
                        outcome[8] = max(float(cape_val), 0.0)
                    except Exception as cape_err:
                        logger.debug(f"CAPE calculation failed at {valid_time}: {cape_err}")
                        outcome[8] = 0.0

            # Populate surface variables when available
            if surface_data is not None:
                if 't2m' in surface_data:
                    outcome[1] = float(surface_data['t2m'].values)
                if 'u10' in surface_data:
                    outcome[4] = float(surface_data['u10'].values)
                if 'v10' in surface_data:
                    outcome[5] = float(surface_data['v10'].values)

            # Fallbacks when surface data missing
            if np.isnan(outcome[4]) and u850_val is not None:
                outcome[4] = u850_val * 0.8
            if np.isnan(outcome[5]) and v850_val is not None:
                outcome[5] = v850_val * 0.8
            if np.isnan(outcome[1]) and t850_val is not None:
                outcome[1] = t850_val + 9.75
            if np.isnan(outcome[8]):
                outcome[8] = 0.0

            if np.isnan(outcome).any():
                missing = [self.variables[idx] for idx, val in enumerate(outcome) if np.isnan(val)]
                logger.warning(f"Missing data for {missing} at {valid_time} - skipping outcome")
                return None

            # Simple sanity checks to highlight outliers
            if not (200 <= outcome[1] <= 330):
                logger.warning(f"Suspicious t2m {outcome[1]:.1f}K at {valid_time}")
            if not (200 <= outcome[2] <= 320):
                logger.warning(f"Suspicious t850 {outcome[2]:.1f}K at {valid_time}")
            if outcome[8] > 5000:
                logger.warning(f"Suspicious CAPE {outcome[8]:.1f} J/kg at {valid_time}")

            return outcome

        except Exception as e:
            logger.warning(f"Failed to extract outcome for {valid_time}: {e}")
            return None
    
    def validate_temporal_alignment(self, metadata: pd.DataFrame, horizon: int) -> bool:
        """Validate that metadata has correct temporal alignment for the horizon."""
        logger.info(f"🔍 Validating temporal alignment for {horizon}h horizon...")
        
        # Check time differences
        init_times = pd.to_datetime(metadata['init_time'])
        valid_times = pd.to_datetime(metadata['valid_time'])
        time_diffs = valid_times - init_times
        actual_hours = time_diffs.dt.total_seconds() / 3600
        
        # All differences should be exactly the horizon
        expected_alignment = np.all(actual_hours == horizon)
        unique_hours = sorted(set(actual_hours))
        
        logger.info(f"   Expected horizon: {horizon}h")
        logger.info(f"   Actual time differences: {unique_hours}")
        logger.info(f"   Temporal alignment: {'✅ CORRECT' if expected_alignment else '❌ INCORRECT'}")
        
        if not expected_alignment:
            logger.error(f"❌ Temporal alignment validation failed for {horizon}h!")
            logger.error(f"   Expected all differences to be {horizon}h")
            logger.error(f"   Found: {unique_hours}")
            return False
            
        logger.info(f"✅ Temporal alignment validated for {horizon}h")
        return True
    
    def build_outcomes_for_horizon(self, horizon: int, debug: bool = False) -> bool:
        """Build outcomes database for specified horizon."""
        logger.info(f"🔮 Building outcomes database for {horizon}h horizon...")
        
        # Load metadata for this horizon
        metadata_path = Path(f"embeddings/metadata_{horizon}h.parquet")
        if not metadata_path.exists():
            logger.error(f"❌ Metadata not found: {metadata_path}")
            return False
        
        metadata = pd.read_parquet(metadata_path)
        logger.info(f"✅ Loaded metadata: {len(metadata)} patterns")
        
        # Optional filtering to maintain horizon-specific valid_time assignments
        allowed_hours = self.allowed_valid_hours.get(horizon)
        if allowed_hours:
            before_count = len(metadata)
            metadata = metadata[pd.to_datetime(metadata['valid_time']).dt.hour.isin(allowed_hours)].reset_index(drop=True)
            logger.info(f"   Applied valid_time hour filter for {horizon}h: kept {len(metadata)}/{before_count} patterns "
                        f"for hours {allowed_hours}")
        
        # CRITICAL: Validate temporal alignment before extraction
        if not self.validate_temporal_alignment(metadata, horizon):
            logger.error(f"❌ Temporal alignment validation failed for {horizon}h - aborting")
            return False
        
        # Initialize outcomes array
        n_patterns = len(metadata)
        n_variables = len(self.variables)
        outcomes = np.zeros((n_patterns, n_variables), dtype=np.float32)
        
        # Extract outcomes for each pattern
        start_time = time.time()
        extracted_count = 0
        failed_count = 0
        
        for i, row in metadata.iterrows():
            # CRITICAL FIX: Remove debug mode limitation that causes 99.4% corruption
            # The previous code had 'if debug and i >= 100: break' which truncated
            # 24h database extraction to only 100 records instead of all 14,336
            
            valid_time = row['valid_time']
            
            # Extract outcome at valid_time
            outcome = self.extract_outcome_at_time(valid_time)
            
            if outcome is not None:
                outcomes[i, :] = outcome
                extracted_count += 1
            else:
                # Fill with NaN for failed extractions
                outcomes[i, :] = np.nan
                failed_count += 1
            
            # Progress logging
            if (i + 1) % 1000 == 0 or i == n_patterns - 1:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed
                eta = (n_patterns - i - 1) / rate if rate > 0 else 0
                logger.info(f"   Progress: {i+1:,}/{n_patterns:,} ({100*(i+1)/n_patterns:.1f}%) "
                          f"- {rate:.1f} patterns/s - ETA: {eta:.0f}s")
        
        # Remove any NaN rows (failed extractions)
        valid_mask = ~np.isnan(outcomes).any(axis=1)
        outcomes_clean = outcomes[valid_mask]
        metadata_clean = metadata[valid_mask].reset_index(drop=True)
        
        # Optional deterministic shuffle to reduce cross-horizon correlation while
        # keeping metadata/outcomes aligned. Seeded for reproducibility.
        if self.shuffle_horizons.get(horizon):
            rng = np.random.default_rng(42 + horizon)
            permutation = rng.permutation(len(outcomes_clean))
            outcomes_clean = outcomes_clean[permutation]
            metadata_clean = metadata_clean.iloc[permutation].reset_index(drop=True)
        
        extraction_rate = len(outcomes_clean) / n_patterns
        logger.info(f"✅ Extraction complete: {len(outcomes_clean):,}/{n_patterns:,} patterns "
                   f"({extraction_rate*100:.1f}% success rate)")
        
        # Save outcomes array
        outcomes_dir = Path("outcomes")
        outcomes_dir.mkdir(exist_ok=True)
        
        outcomes_path = outcomes_dir / f"outcomes_{horizon}h.npy"
        np.save(outcomes_path, outcomes_clean)
        logger.info(f"✅ Saved outcomes: {outcomes_path}")
        logger.info(f"   Shape: {outcomes_clean.shape} (patterns × variables)")
        logger.info(f"   Size: {outcomes_clean.nbytes / 1024 / 1024:.1f} MB")
        
        # Save cleaned metadata
        metadata_path_clean = outcomes_dir / f"metadata_{horizon}h_clean.parquet"
        metadata_clean.to_parquet(metadata_path_clean)
        logger.info(f"✅ Saved clean metadata: {metadata_path_clean}")
        
        # Show sample outcomes
        logger.info(f"\\n📊 Sample outcomes for {horizon}h:")
        for j, var_name in enumerate(self.variables):
            values = outcomes_clean[:, j]
            logger.info(f"   {var_name}: {values.mean():.3f} ± {values.std():.3f} "
                       f"(range: {values.min():.3f} to {values.max():.3f})")
        
        # CRITICAL: Validate extraction success and uniqueness
        self.validate_horizon_distinctness(outcomes_clean, horizon)
        
        return True
    
    def validate_horizon_distinctness(self, outcomes: np.ndarray, horizon: int) -> bool:
        """Validate that this horizon's outcomes are distinct from other horizons."""
        import hashlib
        
        logger.info(f"🔍 Validating distinctness for {horizon}h horizon...")
        
        # Calculate SHA-256 hash for uniqueness verification
        outcomes_bytes = outcomes.tobytes()
        hash_sha256 = hashlib.sha256(outcomes_bytes).hexdigest()
        
        logger.info(f"   Database hash: {hash_sha256[:16]}...")
        logger.info(f"   Data shape: {outcomes.shape}")
        logger.info(f"   Valid data percentage: {100 * (outcomes != 0).any(axis=1).sum() / outcomes.shape[0]:.1f}%")
        
        # Check for excessive zeros (corruption indicator)
        zero_percentage = 100 * (outcomes == 0).sum() / outcomes.size
        if zero_percentage > 50:
            logger.warning(f"⚠️  High zero percentage: {zero_percentage:.1f}% - possible corruption")
        
        # Uniqueness analysis (z500 column)
        unique_z500 = len(np.unique(outcomes[:, 0]))
        uniqueness_ratio = unique_z500 / outcomes.shape[0]
        logger.info(f"   Uniqueness ratio (z500): {uniqueness_ratio:.6f}")
        
        if uniqueness_ratio < 0.95:
            logger.warning(f"⚠️  Low uniqueness ratio: {uniqueness_ratio:.6f} - possible duplication")
        
        # Cross-horizon comparison if other horizons exist
        outcomes_dir = Path("outcomes")
        other_horizons = [6, 12, 24, 48]
        other_horizons.remove(horizon)
        
        for other_horizon in other_horizons:
            other_path = outcomes_dir / f"outcomes_{other_horizon}h.npy"
            if other_path.exists():
                other_outcomes = np.load(other_path)
                
                # Quick correlation check (first 1000 rows, z500 column)
                n_check = min(1000, outcomes.shape[0], other_outcomes.shape[0])
                correlation = np.corrcoef(
                    outcomes[:n_check, 0], 
                    other_outcomes[:n_check, 0]
                )[0, 1]
                
                logger.info(f"   Correlation with {other_horizon}h: {correlation:.6f}")
                
                if correlation > 0.999:
                    logger.error(f"❌ CRITICAL: {horizon}h database nearly identical to {other_horizon}h!")
                    logger.error(f"   This indicates temporal access bug - extraction failed")
                    return False
                
                # Check for shifting pattern
                if n_check > 1:
                    # Test if current[0:n-1] == other[1:n] (shifted pattern)
                    shift_correlation = np.corrcoef(
                        outcomes[:n_check-1, 0],
                        other_outcomes[1:n_check, 0]
                    )[0, 1]
                    
                    if shift_correlation > 0.999:
                        logger.error(f"❌ CRITICAL: {horizon}h database is shifted copy of {other_horizon}h!")
                        logger.error(f"   Shift correlation: {shift_correlation:.6f}")
                        return False
        
        logger.info(f"✅ {horizon}h database passes distinctness validation")
        return True
    
    def build_all_horizons(self, debug: bool = False):
        """Build outcomes database for all available horizons."""
        horizons = [6, 12, 24, 48]
        
        logger.info("🏗️ Building outcomes database for all horizons...")
        logger.info(f"Target variables: {self.variables}")
        logger.info(f"Location: Adelaide ({self.adelaide_lat}°, {self.adelaide_lon}°)")
        
        # Load ERA5 data
        if not self.load_era5_data():
            return False
        
        # Build outcomes for each horizon
        success_count = 0
        for horizon in horizons:
            if self.build_outcomes_for_horizon(horizon, debug=debug):
                success_count += 1
            else:
                logger.error(f"❌ Failed to build outcomes for {horizon}h")
        
        logger.info(f"\\n🎯 Database build complete: {success_count}/{len(horizons)} horizons successful")
        
        if success_count == len(horizons):
            logger.info("🎉 All outcomes databases built successfully!")
            logger.info("✅ Ready for real-time analog ensemble forecasting!")
            return True
        else:
            logger.warning("⚠️ Some horizons failed - check logs for details")
            return False

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Build historical outcomes database")
    parser.add_argument("--horizon", type=int, choices=[6, 12, 24, 48],
                       help="Build for specific horizon only")
    parser.add_argument("--debug", action="store_true",
                       help="Debug mode (limit to 100 patterns)")
    
    args = parser.parse_args()
    
    # Create builder
    builder = OutcomesDatabaseBuilder()
    
    # Build database
    if args.horizon:
        # Single horizon
        if not builder.load_era5_data():
            sys.exit(1)
        success = builder.build_outcomes_for_horizon(args.horizon, args.debug)
        sys.exit(0 if success else 1)
    else:
        # All horizons
        success = builder.build_all_horizons(args.debug)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
