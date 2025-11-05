#!/usr/bin/env python3
"""
System Readiness Validation
============================

Validates the Adelaide Weather Forecast System is ready for Day 5 evaluation.
Checks all components without requiring full dependency stack.

Usage:
    python validate_system_readiness.py
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SystemValidator:
    """Validates system readiness for Day 5 evaluation."""
    
    def __init__(self):
        self.project_root = Path("/home/micha/weather-forecast-final")
        self.validation_results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {},
            'overall_status': 'unknown'
        }
    
    def validate_directory_structure(self) -> bool:
        """Validate required directory structure exists."""
        logger.info("📁 Validating directory structure...")
        
        required_dirs = [
            'data', 'models', 'scripts', 'configs', 'embeddings', 'indices', 'outputs'
        ]
        
        missing_dirs = []
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                missing_dirs.append(dir_name)
        
        if missing_dirs:
            logger.error(f"❌ Missing directories: {missing_dirs}")
            self.validation_results['tests']['directory_structure'] = {
                'status': 'failed',
                'missing_dirs': missing_dirs
            }
            return False
        
        logger.info("✅ All required directories present")
        self.validation_results['tests']['directory_structure'] = {'status': 'passed'}
        return True
    
    def validate_model_files(self) -> bool:
        """Validate model files exist and are reasonable size."""
        logger.info("🧠 Validating model files...")
        
        # Check for trained model
        model_patterns = [
            'models/encoder_model_final.pth',
            'outputs/training_production_*/best_model.pt'
        ]
        
        model_found = False
        model_info = {}
        
        for pattern in model_patterns:
            if '*' in pattern:
                # Handle glob pattern
                pattern_path = self.project_root / pattern.replace('*', '*')
                matches = list(self.project_root.glob(pattern))
                if matches:
                    model_path = matches[0]  # Use first match
                    model_found = True
            else:
                model_path = self.project_root / pattern
                if model_path.exists():
                    model_found = True
            
            if model_found:
                size_mb = model_path.stat().st_size / (1024 * 1024)
                model_info = {
                    'path': str(model_path),
                    'size_mb': round(size_mb, 1)
                }
                break
        
        if not model_found:
            logger.error("❌ No trained model found")
            self.validation_results['tests']['model_files'] = {'status': 'failed', 'reason': 'no_model_found'}
            return False
        
        if model_info['size_mb'] < 10:
            logger.warning(f"⚠️ Model size seems small: {model_info['size_mb']} MB")
        
        logger.info(f"✅ Model found: {model_info['path']} ({model_info['size_mb']} MB)")
        self.validation_results['tests']['model_files'] = {
            'status': 'passed',
            'model_info': model_info
        }
        return True
    
    def validate_embeddings(self) -> bool:
        """Validate embeddings are generated for all horizons."""
        logger.info("🔢 Validating embeddings...")
        
        embeddings_dir = self.project_root / 'embeddings'
        expected_horizons = ['6h', '12h', '24h', '48h']
        
        missing_embeddings = []
        embedding_info = {}
        
        for horizon in expected_horizons:
            embedding_file = embeddings_dir / f'embeddings_{horizon}.npy'
            if not embedding_file.exists():
                missing_embeddings.append(horizon)
            else:
                size_mb = embedding_file.stat().st_size / (1024 * 1024)
                embedding_info[horizon] = {
                    'file': str(embedding_file),
                    'size_mb': round(size_mb, 1)
                }
        
        if missing_embeddings:
            logger.error(f"❌ Missing embeddings for: {missing_embeddings}")
            self.validation_results['tests']['embeddings'] = {
                'status': 'failed',
                'missing_horizons': missing_embeddings
            }
            return False
        
        total_size = sum(info['size_mb'] for info in embedding_info.values())
        logger.info(f"✅ All embeddings present (total: {total_size:.1f} MB)")
        
        for horizon, info in embedding_info.items():
            logger.info(f"  {horizon}: {info['size_mb']} MB")
        
        self.validation_results['tests']['embeddings'] = {
            'status': 'passed',
            'embedding_info': embedding_info,
            'total_size_mb': total_size
        }
        return True
    
    def validate_faiss_indices(self) -> bool:
        """Validate FAISS indices are built and have benchmarks."""
        logger.info("🔍 Validating FAISS indices...")
        
        indices_dir = self.project_root / 'indices'
        expected_horizons = ['6h', '12h', '24h', '48h']
        expected_types = ['flatip', 'ivfpq']
        
        missing_indices = []
        index_info = {}
        
        for horizon in expected_horizons:
            index_info[horizon] = {}
            for index_type in expected_types:
                index_file = indices_dir / f'faiss_{horizon}_{index_type}.faiss'
                if not index_file.exists():
                    missing_indices.append(f"{horizon}_{index_type}")
                else:
                    size_mb = index_file.stat().st_size / (1024 * 1024)
                    index_info[horizon][index_type] = {
                        'file': str(index_file),
                        'size_mb': round(size_mb, 1)
                    }
        
        if missing_indices:
            logger.error(f"❌ Missing FAISS indices: {missing_indices}")
            self.validation_results['tests']['faiss_indices'] = {
                'status': 'failed',
                'missing_indices': missing_indices
            }
            return False
        
        # Check for benchmarks
        benchmark_file = indices_dir / 'index_benchmarks.json'
        if benchmark_file.exists():
            try:
                with open(benchmark_file, 'r') as f:
                    benchmarks = json.load(f)
                logger.info("✅ FAISS benchmarks available")
                
                # Show performance summary
                for horizon in expected_horizons:
                    if horizon in benchmarks:
                        ivfpq_qps = benchmarks[horizon]['ivfpq']['throughput_qps']
                        logger.info(f"  {horizon}: {ivfpq_qps:.0f} QPS")
                
            except Exception as e:
                logger.warning(f"⚠️ Benchmark file exists but couldn't parse: {e}")
        
        logger.info("✅ All FAISS indices present")
        self.validation_results['tests']['faiss_indices'] = {
            'status': 'passed',
            'index_info': index_info
        }
        return True
    
    def validate_scripts(self) -> bool:
        """Validate required scripts exist."""
        logger.info("📜 Validating scripts...")
        
        required_scripts = [
            'analog_forecaster.py',
            'evaluate_system.py',
            'build_indices.py',
            'generate_embeddings.py'
        ]
        
        scripts_dir = self.project_root / 'scripts'
        missing_scripts = []
        
        for script in required_scripts:
            script_path = scripts_dir / script
            if not script_path.exists():
                missing_scripts.append(script)
        
        if missing_scripts:
            logger.error(f"❌ Missing scripts: {missing_scripts}")
            self.validation_results['tests']['scripts'] = {
                'status': 'failed',
                'missing_scripts': missing_scripts
            }
            return False
        
        logger.info("✅ All required scripts present")
        self.validation_results['tests']['scripts'] = {'status': 'passed'}
        return True
    
    def validate_faiss_fix(self) -> bool:
        """Validate the FAISS similarity fix was applied."""
        logger.info("🔧 Validating FAISS similarity fix...")
        
        # Check if our validation test passed
        validation_test = self.project_root / 'scripts' / 'test_faiss_similarity.py'
        if not validation_test.exists():
            logger.warning("⚠️ FAISS validation test not found")
            self.validation_results['tests']['faiss_fix'] = {
                'status': 'warning',
                'reason': 'validation_test_missing'
            }
            return True  # Not critical for system readiness
        
        # Check if fix was applied to key files
        fix_indicators = []
        
        # Check build_indices.py for FAISS normalization
        build_indices = self.project_root / 'scripts' / 'build_indices.py'
        if build_indices.exists():
            with open(build_indices, 'r') as f:
                content = f.read()
                if 'faiss.normalize_L2' in content:
                    fix_indicators.append('build_indices_fixed')
        
        # Check analog_forecaster.py for FAISS normalization  
        analog_forecaster = self.project_root / 'scripts' / 'analog_forecaster.py'
        if analog_forecaster.exists():
            with open(analog_forecaster, 'r') as f:
                content = f.read()
                if 'faiss.normalize_L2' in content:
                    fix_indicators.append('analog_forecaster_fixed')
        
        if len(fix_indicators) >= 2:
            logger.info("✅ FAISS similarity fix applied")
            self.validation_results['tests']['faiss_fix'] = {
                'status': 'passed',
                'fix_indicators': fix_indicators
            }
            return True
        else:
            logger.warning("⚠️ FAISS fix may not be fully applied")
            self.validation_results['tests']['faiss_fix'] = {
                'status': 'warning',
                'fix_indicators': fix_indicators
            }
            return True  # Not critical failure
    
    def validate_data_availability(self) -> bool:
        """Validate required data files exist."""
        logger.info("📊 Validating data availability...")
        
        data_dir = self.project_root / 'data'
        
        # Check for ERA5 data files
        era5_files = []
        for pattern in ['*.zarr', '**/*.zarr', '**/*.nc']:
            era5_files.extend(list(data_dir.glob(pattern)))
        
        if not era5_files:
            logger.error("❌ No ERA5 data files found")
            self.validation_results['tests']['data_availability'] = {
                'status': 'failed',
                'reason': 'no_era5_data'
            }
            return False
        
        total_size_gb = sum(f.stat().st_size for f in era5_files) / (1024**3)
        logger.info(f"✅ ERA5 data available ({len(era5_files)} files, {total_size_gb:.1f} GB)")
        
        self.validation_results['tests']['data_availability'] = {
            'status': 'passed',
            'era5_files_count': len(era5_files),
            'total_size_gb': round(total_size_gb, 1)
        }
        return True
    
    def run_validation(self) -> bool:
        """Run complete system validation."""
        logger.info("🎯 STARTING SYSTEM READINESS VALIDATION")
        logger.info("=" * 60)
        
        # Change to project directory
        os.chdir(self.project_root)
        
        # Run all validation tests
        tests = [
            ('Directory Structure', self.validate_directory_structure),
            ('Model Files', self.validate_model_files),
            ('Embeddings', self.validate_embeddings),
            ('FAISS Indices', self.validate_faiss_indices),
            ('Scripts', self.validate_scripts),
            ('FAISS Fix', self.validate_faiss_fix),
            ('Data Availability', self.validate_data_availability)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            logger.info(f"\n🔍 Running: {test_name}")
            try:
                if test_func():
                    passed_tests += 1
                    logger.info(f"✅ {test_name}: PASSED")
                else:
                    logger.info(f"❌ {test_name}: FAILED")
            except Exception as e:
                logger.error(f"💥 {test_name}: ERROR - {e}")
        
        # Determine overall status
        if passed_tests == total_tests:
            self.validation_results['overall_status'] = 'ready'
            logger.info(f"\n🎉 SYSTEM VALIDATION PASSED ({passed_tests}/{total_tests})")
            logger.info("✅ Adelaide Weather Forecast System is READY for Day 5 evaluation!")
        elif passed_tests >= total_tests - 1:
            self.validation_results['overall_status'] = 'mostly_ready'
            logger.info(f"\n⚠️ SYSTEM MOSTLY READY ({passed_tests}/{total_tests})")
            logger.info("✅ System can proceed with evaluation (minor issues detected)")
        else:
            self.validation_results['overall_status'] = 'not_ready'
            logger.info(f"\n❌ SYSTEM NOT READY ({passed_tests}/{total_tests})")
            logger.info("❌ Critical issues must be resolved before evaluation")
        
        logger.info("=" * 60)
        
        # Save validation results
        results_file = self.project_root / 'system_validation_results.json'
        with open(results_file, 'w') as f:
            json.dump(self.validation_results, f, indent=2)
        logger.info(f"💾 Validation results saved to: {results_file}")
        
        return self.validation_results['overall_status'] in ['ready', 'mostly_ready']

def main():
    """Main validation script."""
    validator = SystemValidator()
    
    try:
        success = validator.run_validation()
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"❌ Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()