#!/usr/bin/env python3
"""
Comprehensive Temporal Verification System for Adelaide Weather Forecasting
===========================================================================

This system validates that all database horizons (6h, 12h, 24h, 48h) contain
truly distinct temporal patterns and that the ERA5 temporal alignment is correct.

Key validation checks:
1. Multi-horizon database distinctness verification
2. Temporal alignment validation (t+H alignment for all patterns)
3. Cross-horizon correlation analysis
4. Data shifting pattern detection
5. Database integrity verification

Author: Backend/Architecture Engineer
Target: <1% corruption, verified distinct patterns across all horizons
"""

import sys
import numpy as np
import pandas as pd
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TemporalVerificationSystem:
    """Comprehensive temporal verification for Adelaide Weather Forecasting System."""
    
    def __init__(self, base_dir: Path = Path(".")):
        self.base_dir = base_dir
        self.outcomes_dir = base_dir / "outcomes"
        self.embeddings_dir = base_dir / "embeddings"
        self.sidecars_dir = self.outcomes_dir / "sidecars"
        
        # Create sidecars directory
        self.sidecars_dir.mkdir(exist_ok=True)
        
        # Available horizons
        self.horizons = ['6h', '12h', '24h', '48h']
        self.horizon_hours = {'6h': 6, '12h': 12, '24h': 24, '48h': 48}
        
        # Variable names for analysis
        self.variables = [
            'z500', 't2m', 't850', 'q850', 
            'u10', 'v10', 'u850', 'v850', 'cape'
        ]
        
        # Validation thresholds
        self.thresholds = {
            'max_correlation': 0.95,  # Max acceptable cross-horizon correlation
            'min_valid_data_percentage': 99.0,  # Min % of valid data required
            'max_zero_percentage': 5.0,  # Max % of zeros acceptable
            'min_uniqueness_ratio': 0.95,  # Min ratio of unique patterns
            'max_shift_correlation': 0.999  # Max correlation for shift detection
        }
    
    def calculate_file_hash(self, filepath: Path) -> str:
        """Calculate SHA-256 hash of file."""
        hash_sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def load_horizon_data(self, horizon: str) -> Optional[Tuple[np.ndarray, pd.DataFrame]]:
        """Load outcomes and metadata for a horizon."""
        try:
            outcomes_path = self.outcomes_dir / f"outcomes_{horizon}.npy"
            metadata_path = self.outcomes_dir / f"metadata_{horizon}_clean.parquet"
            
            if not outcomes_path.exists() or not metadata_path.exists():
                logger.warning(f"Missing data files for {horizon}")
                return None
            
            outcomes = np.load(outcomes_path)
            metadata = pd.read_parquet(metadata_path)
            
            logger.debug(f"Loaded {horizon}: outcomes={outcomes.shape}, metadata={len(metadata)}")
            return outcomes, metadata
            
        except Exception as e:
            logger.error(f"Failed to load {horizon} data: {e}")
            return None
    
    def validate_temporal_alignment(self, horizon: str, metadata: pd.DataFrame) -> Dict[str, Any]:
        """Validate temporal alignment for a specific horizon."""
        logger.info(f"🕐 Validating temporal alignment for {horizon}...")
        
        expected_hours = self.horizon_hours[horizon]
        
        # Check time differences
        init_times = pd.to_datetime(metadata['init_time'])
        valid_times = pd.to_datetime(metadata['valid_time'])
        time_diffs = valid_times - init_times
        actual_hours = time_diffs.dt.total_seconds() / 3600
        
        # Analysis
        alignment_correct = np.all(actual_hours == expected_hours)
        alignment_errors = np.sum(actual_hours != expected_hours)
        unique_hours = sorted(set(actual_hours))
        
        result = {
            'horizon': horizon,
            'expected_hours': expected_hours,
            'unique_hours_found': unique_hours,
            'alignment_correct': alignment_correct,
            'alignment_errors': int(alignment_errors),
            'total_patterns': len(metadata),
            'alignment_error_rate': float(alignment_errors / len(metadata)),
            'temporal_range': {
                'init_time_min': str(metadata['init_time'].min()),
                'init_time_max': str(metadata['init_time'].max()),
                'valid_time_min': str(metadata['valid_time'].min()),
                'valid_time_max': str(metadata['valid_time'].max())
            }
        }
        
        if alignment_correct:
            logger.info(f"✅ {horizon} temporal alignment correct: all patterns at t+{expected_hours}h")
        else:
            logger.error(f"❌ {horizon} temporal alignment FAILED: {alignment_errors:,} errors")
            logger.error(f"   Expected: {expected_hours}h, Found: {unique_hours}")
        
        return result
    
    def analyze_data_quality(self, horizon: str, outcomes: np.ndarray) -> Dict[str, Any]:
        """Analyze data quality for a horizon."""
        logger.info(f"📊 Analyzing data quality for {horizon}...")
        
        # Basic statistics
        total_values = outcomes.size
        
        if total_values > 0:
            zero_count = np.sum(outcomes == 0)
            zero_percentage = 100 * zero_count / total_values
            
            # Row-level analysis
            completely_zero_rows = np.all(outcomes == 0, axis=1).sum()
            valid_rows = outcomes.shape[0] - completely_zero_rows
            valid_percentage = 100 * valid_rows / outcomes.shape[0]
        else:
            zero_count = 0
            zero_percentage = 100.0  # Empty database is 100% "zeros"
            completely_zero_rows = 0
            valid_rows = 0
            valid_percentage = 0.0
        
        # Uniqueness analysis (using z500 column)
        if outcomes.shape[0] > 0:
            unique_z500 = len(np.unique(outcomes[:, 0]))
            uniqueness_ratio = unique_z500 / outcomes.shape[0]
        else:
            unique_z500 = 0
            uniqueness_ratio = 0.0
        
        # Variable-level analysis
        variable_stats = {}
        for i, var in enumerate(self.variables):
            if outcomes.shape[0] > 0 and outcomes.shape[1] > i:
                col_data = outcomes[:, i]
                variable_stats[var] = {
                    'min': float(col_data.min()),
                    'max': float(col_data.max()),
                    'mean': float(col_data.mean()),
                    'std': float(col_data.std()),
                    'zeros': int(np.sum(col_data == 0)),
                    'zero_percentage': float(100 * np.sum(col_data == 0) / len(col_data))
                }
            else:
                # Empty database
                variable_stats[var] = {
                    'min': 0.0,
                    'max': 0.0,
                    'mean': 0.0,
                    'std': 0.0,
                    'zeros': 0,
                    'zero_percentage': 100.0
                }
        
        # Quality indicators
        quality_flags = {
            'excessive_zeros': zero_percentage > self.thresholds['max_zero_percentage'],
            'completely_zero_rows': completely_zero_rows > 0,
            'poor_uniqueness': uniqueness_ratio < self.thresholds['min_uniqueness_ratio'],
            'insufficient_valid_data': valid_percentage < self.thresholds['min_valid_data_percentage']
        }
        
        result = {
            'horizon': horizon,
            'shape': list(outcomes.shape),
            'dtype': str(outcomes.dtype),
            'total_values': total_values,
            'zero_count': zero_count,
            'zero_percentage': round(zero_percentage, 3),
            'completely_zero_rows': completely_zero_rows,
            'valid_rows': valid_rows,
            'valid_percentage': round(valid_percentage, 3),
            'uniqueness_ratio': round(uniqueness_ratio, 6),
            'variable_statistics': variable_stats,
            'quality_flags': quality_flags,
            'quality_score': self._calculate_quality_score(quality_flags, valid_percentage, uniqueness_ratio)
        }
        
        # Log quality assessment
        if any(quality_flags.values()):
            logger.warning(f"⚠️  {horizon} quality issues detected:")
            for flag, value in quality_flags.items():
                if value:
                    logger.warning(f"     - {flag}: {value}")
        else:
            logger.info(f"✅ {horizon} passes all quality checks")
        
        return result
    
    def _calculate_quality_score(self, quality_flags: Dict[str, bool], 
                                valid_percentage: float, uniqueness_ratio: float) -> float:
        """Calculate overall quality score (0-100)."""
        # Base score
        score = 100.0
        
        # Deduct for quality issues
        if quality_flags['excessive_zeros']:
            score -= 25
        if quality_flags['completely_zero_rows']:
            score -= 20
        if quality_flags['poor_uniqueness']:
            score -= 20
        if quality_flags['insufficient_valid_data']:
            score -= 35
        
        # Adjust for actual percentages
        score *= (valid_percentage / 100.0)
        score *= uniqueness_ratio
        
        return max(0.0, min(100.0, score))
    
    def detect_cross_horizon_duplication(self, all_outcomes: Dict[str, np.ndarray]) -> Dict[str, Any]:
        """Detect duplication and shifting patterns across horizons."""
        logger.info("🔍 Detecting cross-horizon duplication patterns...")
        
        # File hash analysis
        hashes = {}
        for horizon in self.horizons:
            if horizon in all_outcomes:
                outcomes_bytes = all_outcomes[horizon].tobytes()
                hashes[horizon] = hashlib.sha256(outcomes_bytes).hexdigest()
        
        # Group by hash to find identical files
        hash_groups = {}
        for horizon, hash_val in hashes.items():
            if hash_val not in hash_groups:
                hash_groups[hash_val] = []
            hash_groups[hash_val].append(horizon)
        
        identical_groups = [group for group in hash_groups.values() if len(group) > 1]
        
        # Correlation matrix
        correlation_matrix = {}
        shift_patterns = {}
        
        for i, h1 in enumerate(self.horizons):
            if h1 not in all_outcomes:
                continue
            
            correlation_matrix[h1] = {}
            shift_patterns[h1] = {}
            
            for j, h2 in enumerate(self.horizons):
                if h2 not in all_outcomes or i >= j:
                    continue
                
                # Direct correlation (z500 column, first 1000 rows)
                n_check = min(1000, all_outcomes[h1].shape[0], all_outcomes[h2].shape[0])
                direct_corr = np.corrcoef(
                    all_outcomes[h1][:n_check, 0], 
                    all_outcomes[h2][:n_check, 0]
                )[0, 1]
                
                correlation_matrix[h1][h2] = float(direct_corr)
                
                # Shift pattern detection
                if n_check > 1:
                    shift_corr = np.corrcoef(
                        all_outcomes[h1][:n_check-1, 0],
                        all_outcomes[h2][1:n_check, 0]
                    )[0, 1]
                    
                    shift_patterns[h1][h2] = {
                        'correlation': float(shift_corr),
                        'is_shifted': shift_corr > self.thresholds['max_shift_correlation']
                    }
        
        # Analysis results
        high_correlations = []
        shift_detections = []
        
        for h1, correlations in correlation_matrix.items():
            for h2, corr in correlations.items():
                if corr > self.thresholds['max_correlation']:
                    high_correlations.append({
                        'horizon1': h1,
                        'horizon2': h2,
                        'correlation': corr,
                        'severity': 'CRITICAL' if corr > 0.999 else 'HIGH'
                    })
        
        for h1, shifts in shift_patterns.items():
            for h2, shift_data in shifts.items():
                if shift_data['is_shifted']:
                    shift_detections.append({
                        'horizon1': h1,
                        'horizon2': h2,
                        'shift_correlation': shift_data['correlation'],
                        'pattern': f"{h1} appears to be shifted copy of {h2}"
                    })
        
        result = {
            'file_hashes': hashes,
            'identical_groups': identical_groups,
            'correlation_matrix': correlation_matrix,
            'shift_patterns': shift_patterns,
            'high_correlations': high_correlations,
            'shift_detections': shift_detections,
            'duplication_detected': len(identical_groups) > 0 or len(high_correlations) > 0,
            'shifting_detected': len(shift_detections) > 0
        }
        
        # Log findings
        if identical_groups:
            logger.error("❌ IDENTICAL FILES DETECTED:")
            for group in identical_groups:
                logger.error(f"   - Identical: {', '.join(group)}")
        
        if high_correlations:
            logger.error("❌ HIGH CORRELATIONS DETECTED:")
            for corr_data in high_correlations:
                logger.error(f"   - {corr_data['horizon1']} vs {corr_data['horizon2']}: "
                           f"{corr_data['correlation']:.6f} ({corr_data['severity']})")
        
        if shift_detections:
            logger.error("❌ SHIFT PATTERNS DETECTED:")
            for shift_data in shift_detections:
                logger.error(f"   - {shift_data['pattern']}: "
                           f"correlation={shift_data['shift_correlation']:.6f}")
        
        if not (identical_groups or high_correlations or shift_detections):
            logger.info("✅ No duplication or shifting patterns detected")
        
        return result
    
    def comprehensive_verification(self) -> Dict[str, Any]:
        """Run complete temporal verification suite."""
        logger.info("🚀 Starting comprehensive temporal verification...")
        
        # Load all available data
        all_outcomes = {}
        all_metadata = {}
        
        for horizon in self.horizons:
            data = self.load_horizon_data(horizon)
            if data:
                outcomes, metadata = data
                all_outcomes[horizon] = outcomes
                all_metadata[horizon] = metadata
        
        if not all_outcomes:
            logger.error("❌ No valid horizon data found!")
            return {'error': 'No data available for verification'}
        
        logger.info(f"✅ Loaded data for horizons: {list(all_outcomes.keys())}")
        
        # 1. Temporal alignment validation
        temporal_results = {}
        for horizon in all_outcomes.keys():
            temporal_results[horizon] = self.validate_temporal_alignment(
                horizon, all_metadata[horizon]
            )
        
        # 2. Data quality analysis
        quality_results = {}
        for horizon, outcomes in all_outcomes.items():
            quality_results[horizon] = self.analyze_data_quality(horizon, outcomes)
        
        # 3. Cross-horizon duplication detection
        duplication_results = self.detect_cross_horizon_duplication(all_outcomes)
        
        # 4. File integrity analysis
        file_integrity = {}
        for horizon in all_outcomes.keys():
            outcomes_path = self.outcomes_dir / f"outcomes_{horizon}.npy"
            metadata_path = self.outcomes_dir / f"metadata_{horizon}_clean.parquet"
            
            file_integrity[horizon] = {
                'outcomes_hash': self.calculate_file_hash(outcomes_path),
                'metadata_hash': self.calculate_file_hash(metadata_path),
                'outcomes_size_mb': round(outcomes_path.stat().st_size / 1024 / 1024, 3),
                'metadata_size_mb': round(metadata_path.stat().st_size / 1024 / 1024, 3)
            }
        
        # 5. Overall system assessment
        system_status = self._assess_system_status(
            temporal_results, quality_results, duplication_results
        )
        
        # Compile complete results
        verification_results = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'horizons_analyzed': list(all_outcomes.keys()),
            'temporal_alignment': temporal_results,
            'data_quality': quality_results,
            'cross_horizon_analysis': duplication_results,
            'file_integrity': file_integrity,
            'system_status': system_status,
            'validation_thresholds': self.thresholds
        }
        
        # Save results
        self._save_verification_results(verification_results)
        
        return verification_results
    
    def _assess_system_status(self, temporal_results: Dict, quality_results: Dict, 
                            duplication_results: Dict) -> Dict[str, Any]:
        """Assess overall system status based on verification results."""
        
        # Temporal alignment status
        temporal_ok = all(
            result['alignment_correct'] for result in temporal_results.values()
        )
        
        # Data quality status
        quality_ok = all(
            not any(result['quality_flags'].values()) for result in quality_results.values()
        )
        
        # Duplication status
        duplication_ok = not (
            duplication_results['duplication_detected'] or 
            duplication_results['shifting_detected']
        )
        
        # Overall status
        system_healthy = temporal_ok and quality_ok and duplication_ok
        
        # Calculate readiness score
        readiness_score = 0
        if temporal_ok:
            readiness_score += 40
        if quality_ok:
            readiness_score += 35  
        if duplication_ok:
            readiness_score += 25
        
        status = {
            'system_healthy': system_healthy,
            'readiness_score': readiness_score,
            'temporal_alignment_ok': temporal_ok,
            'data_quality_ok': quality_ok,
            'no_duplication': duplication_ok,
            'production_ready': system_healthy and readiness_score >= 95,
            'critical_issues': self._identify_critical_issues(
                temporal_results, quality_results, duplication_results
            ),
            'recommendations': self._generate_recommendations(
                temporal_ok, quality_ok, duplication_ok
            )
        }
        
        # Log overall status
        if system_healthy:
            logger.info(f"✅ SYSTEM HEALTHY - Readiness Score: {readiness_score}/100")
            logger.info("🎉 All temporal verification checks passed!")
        else:
            logger.error(f"❌ SYSTEM ISSUES DETECTED - Readiness Score: {readiness_score}/100")
            logger.error("⚠️  System requires fixes before production use")
        
        return status
    
    def _identify_critical_issues(self, temporal_results: Dict, quality_results: Dict, 
                                duplication_results: Dict) -> List[str]:
        """Identify critical issues requiring immediate attention."""
        issues = []
        
        # Temporal alignment issues
        for horizon, result in temporal_results.items():
            if not result['alignment_correct']:
                issues.append(f"Temporal misalignment in {horizon} database")
        
        # Data quality issues
        for horizon, result in quality_results.items():
            flags = result['quality_flags']
            if flags['insufficient_valid_data']:
                issues.append(f"Insufficient valid data in {horizon} database")
            if flags['excessive_zeros']:
                issues.append(f"Excessive zeros in {horizon} database")
            if flags['completely_zero_rows']:
                issues.append(f"Completely zero rows in {horizon} database")
        
        # Duplication issues
        if duplication_results['duplication_detected']:
            issues.append("Duplicate databases detected across horizons")
        if duplication_results['shifting_detected']:
            issues.append("Data shifting patterns detected between horizons")
        
        return issues
    
    def _generate_recommendations(self, temporal_ok: bool, quality_ok: bool, 
                                duplication_ok: bool) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if not temporal_ok:
            recommendations.append("Fix temporal alignment validation in metadata")
        
        if not quality_ok:
            recommendations.append("Investigate and fix data quality issues")
            recommendations.append("Remove debug mode limitations from extraction")
        
        if not duplication_ok:
            recommendations.append("Fix ERA5 temporal access logic in database builder")
            recommendations.append("Rebuild all horizon databases with fixed extraction")
        
        if temporal_ok and quality_ok and duplication_ok:
            recommendations.append("System ready for production use")
            recommendations.append("Consider implementing automated monitoring")
        
        return recommendations
    
    def _save_verification_results(self, results: Dict[str, Any]) -> None:
        """Save verification results to JSON files."""
        
        # Save master verification report
        master_path = self.sidecars_dir / "temporal_verification_report.json"
        with open(master_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"✅ Saved verification report: {master_path}")
        
        # Save individual horizon summaries
        for horizon in results['horizons_analyzed']:
            horizon_summary = {
                'horizon': horizon,
                'temporal_alignment': results['temporal_alignment'][horizon],
                'data_quality': results['data_quality'][horizon],
                'file_integrity': results['file_integrity'][horizon],
                'timestamp': results['timestamp']
            }
            
            horizon_path = self.sidecars_dir / f"verification_{horizon}_summary.json"
            with open(horizon_path, 'w') as f:
                json.dump(horizon_summary, f, indent=2, default=str)
        
        logger.info(f"✅ Saved individual horizon summaries in: {self.sidecars_dir}")

def main():
    """Main entry point for temporal verification."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Adelaide Weather Forecasting Temporal Verification")
    parser.add_argument("--base-dir", type=Path, default=Path("."),
                       help="Base directory containing weather-forecast-final system")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Change to the specified directory
    original_cwd = Path.cwd()
    try:
        import os
        os.chdir(args.base_dir)
        
        # Initialize verification system
        verifier = TemporalVerificationSystem()
        
        # Run comprehensive verification
        results = verifier.comprehensive_verification()
        
        # Print summary
        if 'system_status' in results:
            status = results['system_status']
            print(f"\\n=== VERIFICATION SUMMARY ===")
            print(f"System Health: {'✅ HEALTHY' if status['system_healthy'] else '❌ ISSUES DETECTED'}")
            print(f"Readiness Score: {status['readiness_score']}/100")
            print(f"Production Ready: {'✅ YES' if status['production_ready'] else '❌ NO'}")
            
            if status['critical_issues']:
                print(f"\\nCritical Issues:")
                for issue in status['critical_issues']:
                    print(f"  - {issue}")
            
            print(f"\\nRecommendations:")
            for rec in status['recommendations']:
                print(f"  - {rec}")
        
        return 0 if results.get('system_status', {}).get('system_healthy', False) else 1
        
    finally:
        os.chdir(original_cwd)

if __name__ == "__main__":
    sys.exit(main())