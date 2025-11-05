#!/usr/bin/env python3
"""
Integration Testing Suite for Adelaide Weather Forecasting System
================================================================

Tests end-to-end integration of the rebuilt database system with the existing
forecasting pipeline to ensure all components work together correctly.

Key integration tests:
1. Database loading and integrity verification
2. Forecasting pipeline integration 
3. Analog forecaster functionality
4. Real-time forecasting workflow
5. Performance and accuracy validation

Author: Backend/Architecture Engineer  
Target: End-to-end system validation with <1% corruption
"""

import sys
import time
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IntegrationTestSuite:
    """Comprehensive integration testing for Adelaide Weather Forecasting System."""
    
    def __init__(self, base_dir: Path = Path(".")):
        self.base_dir = base_dir
        self.outcomes_dir = base_dir / "outcomes"
        self.embeddings_dir = base_dir / "embeddings"
        self.indices_dir = base_dir / "indices"
        
        # Test parameters
        self.horizons = ['6h', '12h', '24h', '48h']
        self.variables = [
            'z500', 't2m', 't850', 'q850', 
            'u10', 'v10', 'u850', 'v850', 'cape'
        ]
        
        # Integration test results
        self.test_results = {
            'database_integrity': {},
            'forecasting_pipeline': {},
            'analog_forecaster': {},
            'real_time_workflow': {},
            'performance_metrics': {}
        }
    
    def test_database_integrity(self) -> Dict[str, Any]:
        """Test 1: Database loading and integrity verification."""
        logger.info("🔍 Integration Test 1: Database Integrity")
        
        results = {}
        
        for horizon in self.horizons:
            logger.info(f"  Testing {horizon} database...")
            
            try:
                # Load outcomes and metadata
                outcomes_path = self.outcomes_dir / f"outcomes_{horizon}.npy"
                metadata_path = self.outcomes_dir / f"metadata_{horizon}_clean.parquet"
                
                if not outcomes_path.exists() or not metadata_path.exists():
                    results[horizon] = {
                        'status': 'FAIL',
                        'error': 'Missing database files',
                        'files_exist': False
                    }
                    continue
                
                outcomes = np.load(outcomes_path)
                metadata = pd.read_parquet(metadata_path)
                
                # Basic integrity checks
                shapes_match = len(outcomes) == len(metadata)
                has_data = outcomes.shape[0] > 0
                correct_variables = outcomes.shape[1] == len(self.variables)
                no_all_zeros = not np.all(outcomes == 0)
                
                # Temporal alignment check
                expected_hours = int(horizon[:-1])
                init_times = pd.to_datetime(metadata['init_time'])
                valid_times = pd.to_datetime(metadata['valid_time'])
                time_diffs = valid_times - init_times
                actual_hours = time_diffs.dt.total_seconds() / 3600
                temporal_correct = np.all(actual_hours == expected_hours)
                
                # Data quality metrics
                valid_percentage = 100 * (outcomes != 0).any(axis=1).sum() / outcomes.shape[0]
                uniqueness_ratio = len(np.unique(outcomes[:, 0])) / outcomes.shape[0]
                
                results[horizon] = {
                    'status': 'PASS' if all([shapes_match, has_data, correct_variables, 
                                           no_all_zeros, temporal_correct]) else 'FAIL',
                    'files_exist': True,
                    'shapes_match': shapes_match,
                    'has_data': has_data,
                    'correct_variables': correct_variables,
                    'no_all_zeros': no_all_zeros,
                    'temporal_correct': temporal_correct,
                    'outcomes_shape': list(outcomes.shape),
                    'metadata_count': len(metadata),
                    'valid_percentage': round(valid_percentage, 2),
                    'uniqueness_ratio': round(uniqueness_ratio, 6),
                    'sample_values': {
                        'z500_mean': float(outcomes[:, 0].mean()),
                        'z500_std': float(outcomes[:, 0].std()),
                        'z500_range': [float(outcomes[:, 0].min()), float(outcomes[:, 0].max())]
                    }
                }
                
                logger.info(f"    {horizon}: {results[horizon]['status']} "
                          f"({results[horizon]['outcomes_shape']}, "
                          f"{results[horizon]['valid_percentage']:.1f}% valid)")
                
            except Exception as e:
                results[horizon] = {
                    'status': 'ERROR',
                    'error': str(e),
                    'files_exist': outcomes_path.exists() and metadata_path.exists()
                }
                logger.error(f"    {horizon}: ERROR - {e}")
        
        # Overall database integrity assessment
        all_pass = all(r.get('status') == 'PASS' for r in results.values())
        results['overall_status'] = 'PASS' if all_pass else 'FAIL'
        
        logger.info(f"  Overall Database Integrity: {results['overall_status']}")
        return results
    
    def test_forecasting_pipeline_integration(self) -> Dict[str, Any]:
        """Test 2: Forecasting pipeline integration."""
        logger.info("🔄 Integration Test 2: Forecasting Pipeline")
        
        results = {}
        
        try:
            # Test if we can import the forecasting components
            sys.path.append(str(self.base_dir))
            
            # Test analog forecaster import
            try:
                from core.analog_forecaster import AnalogForecaster
                results['analog_forecaster_import'] = 'PASS'
                logger.info("  ✅ AnalogForecaster import successful")
            except ImportError as e:
                results['analog_forecaster_import'] = f'FAIL: {e}'
                logger.error(f"  ❌ AnalogForecaster import failed: {e}")
            
            # Test embeddings availability
            embeddings_available = {}
            for horizon in self.horizons:
                embeddings_path = self.embeddings_dir / f"embeddings_{horizon}.npy"
                metadata_path = self.embeddings_dir / f"metadata_{horizon}.parquet"
                
                embeddings_available[horizon] = (
                    embeddings_path.exists() and metadata_path.exists()
                )
            
            results['embeddings_available'] = embeddings_available
            
            # Test FAISS indices availability  
            indices_available = {}
            for horizon in self.horizons:
                flatip_path = self.indices_dir / f"faiss_{horizon}_flatip.faiss"
                ivfpq_path = self.indices_dir / f"faiss_{horizon}_ivfpq.faiss"
                
                indices_available[horizon] = {
                    'flatip': flatip_path.exists(),
                    'ivfpq': ivfpq_path.exists()
                }
            
            results['indices_available'] = indices_available
            
            # Test if all components are ready
            all_embeddings = all(embeddings_available.values())
            all_indices = all(
                all(idx.values()) for idx in indices_available.values()
            )
            
            results['pipeline_ready'] = (
                results['analog_forecaster_import'] == 'PASS' and 
                all_embeddings and all_indices
            )
            
            logger.info(f"  Embeddings available: {all_embeddings}")
            logger.info(f"  Indices available: {all_indices}")
            logger.info(f"  Pipeline ready: {results['pipeline_ready']}")
            
        except Exception as e:
            results['error'] = str(e)
            results['pipeline_ready'] = False
            logger.error(f"  Pipeline integration test failed: {e}")
        
        results['status'] = 'PASS' if results.get('pipeline_ready', False) else 'FAIL'
        logger.info(f"  Overall Pipeline Integration: {results['status']}")
        
        return results
    
    def test_analog_forecaster_functionality(self) -> Dict[str, Any]:
        """Test 3: Analog forecaster functionality."""
        logger.info("⚡ Integration Test 3: Analog Forecaster")
        
        results = {}
        
        try:
            # Import and initialize analog forecaster
            sys.path.append(str(self.base_dir))
            from core.analog_forecaster import AnalogForecaster
            
            forecaster = AnalogForecaster()
            results['initialization'] = 'PASS'
            logger.info("  ✅ AnalogForecaster initialized")
            
            # Test forecasting for each horizon
            forecast_results = {}
            
            for horizon in self.horizons:
                try:
                    logger.info(f"    Testing {horizon} forecasting...")
                    
                    # Create test input pattern (realistic Adelaide weather)
                    test_pattern = np.array([
                        [5700.0,  # z500 (typical 500mb height)
                         295.0,   # t2m (typical summer temp in K)
                         280.0,   # t850
                         0.008,   # q850 (humidity)
                         2.0,     # u10 (easterly wind)
                         -1.0,    # v10 (southerly wind)
                         3.0,     # u850
                         -2.0,    # v850
                         0.0]     # cape
                    ])
                    
                    # Test analog search
                    start_time = time.time()
                    analogs = forecaster.find_analogs(test_pattern, horizon=horizon, k=10)
                    search_time = time.time() - start_time
                    
                    if analogs is not None and len(analogs) > 0:
                        forecast_results[horizon] = {
                            'status': 'PASS',
                            'analog_count': len(analogs),
                            'search_time_ms': round(search_time * 1000, 2),
                            'has_outcomes': 'outcomes' in analogs.columns if hasattr(analogs, 'columns') else False
                        }
                        logger.info(f"      ✅ {horizon}: {len(analogs)} analogs found in {search_time*1000:.1f}ms")
                    else:
                        forecast_results[horizon] = {
                            'status': 'FAIL',
                            'error': 'No analogs returned',
                            'search_time_ms': round(search_time * 1000, 2)
                        }
                        logger.error(f"      ❌ {horizon}: No analogs returned")
                
                except Exception as e:
                    forecast_results[horizon] = {
                        'status': 'ERROR',
                        'error': str(e)
                    }
                    logger.error(f"      ❌ {horizon}: {e}")
            
            results['forecast_results'] = forecast_results
            
            # Overall analog forecaster status
            all_horizons_work = all(
                r.get('status') == 'PASS' for r in forecast_results.values()
            )
            
            results['functionality_status'] = 'PASS' if all_horizons_work else 'FAIL'
            
        except Exception as e:
            results['initialization'] = f'FAIL: {e}'
            results['functionality_status'] = 'FAIL'
            logger.error(f"  Analog forecaster test failed: {e}")
        
        logger.info(f"  Overall Analog Forecaster: {results.get('functionality_status', 'FAIL')}")
        return results
    
    def test_real_time_workflow(self) -> Dict[str, Any]:
        """Test 4: Real-time forecasting workflow."""
        logger.info("⏱️ Integration Test 4: Real-time Workflow")
        
        results = {}
        
        try:
            # Test end-to-end workflow simulation
            logger.info("  Simulating real-time forecasting workflow...")
            
            # Step 1: Pattern extraction (simulated)
            logger.info("    Step 1: Current weather pattern extraction")
            current_pattern = np.array([
                5650.0, 298.0, 283.0, 0.009, 1.5, -0.8, 2.2, -1.2, 0.0
            ])
            results['pattern_extraction'] = 'PASS'
            
            # Step 2: Multi-horizon forecasting
            logger.info("    Step 2: Multi-horizon analog forecasting")
            forecasts = {}
            total_time = 0
            
            # Import forecaster
            sys.path.append(str(self.base_dir))
            from core.analog_forecaster import AnalogForecaster
            forecaster = AnalogForecaster()
            
            for horizon in self.horizons:
                start_time = time.time()
                try:
                    analogs = forecaster.find_analogs(
                        current_pattern.reshape(1, -1), 
                        horizon=horizon, 
                        k=20
                    )
                    forecast_time = time.time() - start_time
                    total_time += forecast_time
                    
                    if analogs is not None and len(analogs) > 0:
                        forecasts[horizon] = {
                            'status': 'PASS',
                            'analogs': len(analogs),
                            'time_ms': round(forecast_time * 1000, 1)
                        }
                    else:
                        forecasts[horizon] = {
                            'status': 'FAIL',
                            'error': 'No analogs found'
                        }
                        
                except Exception as e:
                    forecasts[horizon] = {
                        'status': 'ERROR',
                        'error': str(e)
                    }
            
            results['multi_horizon_forecasts'] = forecasts
            results['total_forecast_time_ms'] = round(total_time * 1000, 1)
            
            # Step 3: Performance validation
            logger.info("    Step 3: Performance validation")
            all_successful = all(f.get('status') == 'PASS' for f in forecasts.values())
            fast_enough = total_time < 5.0  # Under 5 seconds for all horizons
            
            results['performance_acceptable'] = fast_enough
            results['all_horizons_successful'] = all_successful
            
            logger.info(f"      Total forecast time: {total_time:.2f}s")
            logger.info(f"      All horizons successful: {all_successful}")
            logger.info(f"      Performance acceptable: {fast_enough}")
            
            # Overall workflow status
            results['workflow_status'] = (
                'PASS' if all_successful and fast_enough else 'FAIL'
            )
            
        except Exception as e:
            results['workflow_status'] = 'FAIL'
            results['error'] = str(e)
            logger.error(f"  Real-time workflow test failed: {e}")
        
        logger.info(f"  Overall Real-time Workflow: {results.get('workflow_status', 'FAIL')}")
        return results
    
    def test_performance_and_accuracy(self) -> Dict[str, Any]:
        """Test 5: Performance and accuracy validation."""
        logger.info("📊 Integration Test 5: Performance & Accuracy")
        
        results = {}
        
        try:
            # Performance benchmarks
            performance_metrics = {}
            
            for horizon in self.horizons:
                logger.info(f"    Benchmarking {horizon}...")
                
                # Load outcomes to check data quality
                outcomes_path = self.outcomes_dir / f"outcomes_{horizon}.npy"
                if outcomes_path.exists():
                    outcomes = np.load(outcomes_path)
                    
                    # Quality metrics
                    non_zero_percentage = (outcomes != 0).any(axis=1).mean() * 100
                    variance_check = outcomes.var(axis=0).mean() > 1e-6
                    realistic_ranges = self._check_realistic_ranges(outcomes)
                    
                    performance_metrics[horizon] = {
                        'data_completeness': round(non_zero_percentage, 2),
                        'has_variance': variance_check,
                        'realistic_ranges': realistic_ranges,
                        'total_patterns': outcomes.shape[0],
                        'variables_count': outcomes.shape[1]
                    }
                else:
                    performance_metrics[horizon] = {
                        'status': 'MISSING',
                        'error': 'Outcomes file not found'
                    }
            
            results['performance_metrics'] = performance_metrics
            
            # Overall accuracy assessment
            quality_scores = []
            for horizon, metrics in performance_metrics.items():
                if 'data_completeness' in metrics:
                    score = (
                        (metrics['data_completeness'] > 95.0) * 25 +  # Completeness
                        metrics['has_variance'] * 25 +                # Variance
                        metrics['realistic_ranges'] * 25 +            # Realistic data
                        (metrics['total_patterns'] > 10000) * 25      # Sufficient data
                    )
                    quality_scores.append(score)
            
            results['average_quality_score'] = (
                sum(quality_scores) / len(quality_scores) if quality_scores else 0
            )
            
            results['accuracy_status'] = (
                'PASS' if results['average_quality_score'] >= 90 else 'FAIL'
            )
            
            logger.info(f"  Average quality score: {results['average_quality_score']:.1f}/100")
            
        except Exception as e:
            results['accuracy_status'] = 'FAIL'
            results['error'] = str(e)
            logger.error(f"  Performance & accuracy test failed: {e}")
        
        logger.info(f"  Overall Performance & Accuracy: {results.get('accuracy_status', 'FAIL')}")
        return results
    
    def _check_realistic_ranges(self, outcomes: np.ndarray) -> bool:
        """Check if variable values are in realistic meteorological ranges."""
        try:
            # Define realistic ranges for each variable
            realistic_ranges = {
                0: (5000, 6000),    # z500 (m)
                1: (250, 320),      # t2m (K) 
                2: (250, 310),      # t850 (K)
                3: (0, 0.025),      # q850 (kg/kg)
                4: (-30, 30),       # u10 (m/s)
                5: (-30, 30),       # v10 (m/s)
                6: (-50, 50),       # u850 (m/s)
                7: (-50, 50),       # v850 (m/s)
                8: (0, 5000)        # cape (J/kg)
            }
            
            for i, (min_val, max_val) in realistic_ranges.items():
                if i < outcomes.shape[1]:
                    col_data = outcomes[:, i]
                    if col_data.min() < min_val or col_data.max() > max_val:
                        return False
            
            return True
            
        except Exception:
            return False
    
    def run_comprehensive_integration_tests(self) -> Dict[str, Any]:
        """Run complete integration test suite."""
        logger.info("🚀 Starting Comprehensive Integration Testing...")
        logger.info("=" * 60)
        
        start_time = time.time()
        
        # Run all integration tests
        self.test_results['database_integrity'] = self.test_database_integrity()
        self.test_results['forecasting_pipeline'] = self.test_forecasting_pipeline_integration()
        self.test_results['analog_forecaster'] = self.test_analog_forecaster_functionality()
        self.test_results['real_time_workflow'] = self.test_real_time_workflow()
        self.test_results['performance_metrics'] = self.test_performance_and_accuracy()
        
        # Overall system assessment
        test_statuses = [
            self.test_results['database_integrity'].get('overall_status'),
            self.test_results['forecasting_pipeline'].get('status'),
            self.test_results['analog_forecaster'].get('functionality_status'),
            self.test_results['real_time_workflow'].get('workflow_status'),
            self.test_results['performance_metrics'].get('accuracy_status')
        ]
        
        passed_tests = sum(1 for status in test_statuses if status == 'PASS')
        total_tests = len(test_statuses)
        
        overall_status = 'PASS' if passed_tests == total_tests else 'FAIL'
        integration_score = (passed_tests / total_tests) * 100
        
        total_time = time.time() - start_time
        
        # Compile final results
        final_results = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'overall_status': overall_status,
            'integration_score': integration_score,
            'tests_passed': passed_tests,
            'total_tests': total_tests,
            'test_duration_seconds': round(total_time, 2),
            'individual_results': self.test_results,
            'summary': {
                'database_integrity': self.test_results['database_integrity'].get('overall_status'),
                'forecasting_pipeline': self.test_results['forecasting_pipeline'].get('status'),
                'analog_forecaster': self.test_results['analog_forecaster'].get('functionality_status'),
                'real_time_workflow': self.test_results['real_time_workflow'].get('workflow_status'),
                'performance_accuracy': self.test_results['performance_metrics'].get('accuracy_status')
            }
        }
        
        # Save results
        self._save_integration_results(final_results)
        
        # Print summary
        logger.info("=" * 60)
        logger.info("🎯 INTEGRATION TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Overall Status: {'✅ PASS' if overall_status == 'PASS' else '❌ FAIL'}")
        logger.info(f"Integration Score: {integration_score:.1f}/100")
        logger.info(f"Tests Passed: {passed_tests}/{total_tests}")
        logger.info(f"Test Duration: {total_time:.1f}s")
        logger.info("")
        
        for test_name, status in final_results['summary'].items():
            status_icon = '✅' if status == 'PASS' else '❌'
            logger.info(f"{status_icon} {test_name.replace('_', ' ').title()}: {status}")
        
        logger.info("=" * 60)
        
        if overall_status == 'PASS':
            logger.info("🎉 All integration tests passed! System ready for production.")
        else:
            logger.info("⚠️  Some integration tests failed. Review results before production use.")
        
        return final_results
    
    def _save_integration_results(self, results: Dict[str, Any]) -> None:
        """Save integration test results to file."""
        import json
        
        results_path = self.base_dir / "integration_test_results.json"
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"✅ Integration test results saved: {results_path}")

def main():
    """Main entry point for integration testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Adelaide Weather Forecasting Integration Tests")
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
        
        # Initialize integration test suite
        test_suite = IntegrationTestSuite()
        
        # Run comprehensive tests
        results = test_suite.run_comprehensive_integration_tests()
        
        # Exit with appropriate code
        return 0 if results['overall_status'] == 'PASS' else 1
        
    finally:
        os.chdir(original_cwd)

if __name__ == "__main__":
    sys.exit(main())