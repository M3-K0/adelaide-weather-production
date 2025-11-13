#!/usr/bin/env python3
"""
Data Artifacts Validation Script
================================

Validates alignment between outcomes, metadata, and FAISS indices for all horizons.
Task BL1: Validate data artifacts shape and counts.

Checks:
1. All outcome arrays have shape (n_samples, len(VARIABLE_ORDER))
2. Metadata parquet files have matching row counts  
3. FAISS indices ntotal matches the data counts
4. Report any misalignments or missing files
"""

import numpy as np
import pandas as pd
import faiss
from pathlib import Path
import logging
import json
from typing import Dict, List, Tuple, Any

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Variable order from analog_forecaster.py
VARIABLE_ORDER = [
    'z500',    # geopotential 500mb (m)
    't2m',     # 2m temperature (K)
    't850',    # temperature 850mb (K) 
    'q850',    # specific humidity 850mb (kg/kg)
    'u10',     # u-wind 10m (m/s)
    'v10',     # v-wind 10m (m/s)
    'u850',    # u-wind 850mb (m/s)
    'v850',    # v-wind 850mb (m/s)
    'cape'     # CAPE (J/kg)
]

HORIZONS = [6, 12, 24, 48]

class DataArtifactsValidator:
    """Validates data artifacts alignment across all horizons."""
    
    def __init__(self, base_dir: Path = Path(".")):
        self.base_dir = base_dir
        self.outcomes_dir = base_dir / "outcomes"
        self.indices_dir = base_dir / "indices"
        self.validation_results = {}
        
    def check_file_exists(self, file_path: Path) -> bool:
        """Check if file exists and log result."""
        exists = file_path.exists()
        if not exists:
            logger.error(f"❌ Missing file: {file_path}")
        return exists
    
    def validate_outcomes_file(self, horizon: int) -> Dict[str, Any]:
        """Validate outcomes file for given horizon."""
        outcomes_file = self.outcomes_dir / f"outcomes_{horizon}h.npy"
        
        result = {
            'horizon': horizon,
            'file_exists': self.check_file_exists(outcomes_file),
            'file_path': str(outcomes_file),
            'shape': None,
            'expected_variables': len(VARIABLE_ORDER),
            'actual_variables': None,
            'n_samples': None,
            'shape_valid': False,
            'dtype': None,
            'file_size_mb': None,
            'errors': []
        }
        
        if not result['file_exists']:
            result['errors'].append(f"File not found: {outcomes_file}")
            return result
            
        try:
            # Load array to check shape
            outcomes = np.load(outcomes_file)
            result['shape'] = outcomes.shape
            result['dtype'] = str(outcomes.dtype)
            result['file_size_mb'] = round(outcomes_file.stat().st_size / 1024 / 1024, 2)
            
            # Validate shape
            if len(outcomes.shape) != 2:
                result['errors'].append(f"Expected 2D array, got {len(outcomes.shape)}D")
            else:
                result['n_samples'] = outcomes.shape[0]
                result['actual_variables'] = outcomes.shape[1]
                
                if outcomes.shape[1] == len(VARIABLE_ORDER):
                    result['shape_valid'] = True
                    logger.info(f"✅ {horizon}h outcomes: {outcomes.shape} - VALID")
                else:
                    result['shape_valid'] = False
                    result['errors'].append(
                        f"Variable count mismatch: expected {len(VARIABLE_ORDER)}, got {outcomes.shape[1]}"
                    )
                    logger.error(f"❌ {horizon}h outcomes: {outcomes.shape} - INVALID variable count")
            
        except Exception as e:
            result['errors'].append(f"Error loading outcomes: {str(e)}")
            logger.error(f"❌ Error loading {outcomes_file}: {e}")
            
        return result
    
    def validate_metadata_file(self, horizon: int, expected_rows: int = None) -> Dict[str, Any]:
        """Validate metadata file for given horizon."""
        metadata_file = self.outcomes_dir / f"metadata_{horizon}h_clean.parquet"
        
        result = {
            'horizon': horizon,
            'file_exists': self.check_file_exists(metadata_file),
            'file_path': str(metadata_file),
            'n_rows': None,
            'n_columns': None,
            'expected_rows': expected_rows,
            'rows_match': False,
            'file_size_mb': None,
            'columns': None,
            'errors': []
        }
        
        if not result['file_exists']:
            result['errors'].append(f"File not found: {metadata_file}")
            return result
            
        try:
            # Load metadata to check shape
            metadata = pd.read_parquet(metadata_file)
            result['n_rows'] = len(metadata)
            result['n_columns'] = len(metadata.columns)
            result['columns'] = list(metadata.columns)
            result['file_size_mb'] = round(metadata_file.stat().st_size / 1024 / 1024, 2)
            
            if expected_rows is not None:
                if result['n_rows'] == expected_rows:
                    result['rows_match'] = True
                    logger.info(f"✅ {horizon}h metadata: {result['n_rows']} rows - MATCHES outcomes")
                else:
                    result['rows_match'] = False
                    result['errors'].append(
                        f"Row count mismatch: expected {expected_rows}, got {result['n_rows']}"
                    )
                    logger.error(f"❌ {horizon}h metadata: {result['n_rows']} rows - MISMATCH with outcomes ({expected_rows})")
            else:
                logger.info(f"📊 {horizon}h metadata: {result['n_rows']} rows, {result['n_columns']} columns")
            
        except Exception as e:
            result['errors'].append(f"Error loading metadata: {str(e)}")
            logger.error(f"❌ Error loading {metadata_file}: {e}")
            
        return result
    
    def validate_faiss_index(self, horizon: int, expected_count: int = None) -> Dict[str, Any]:
        """Validate FAISS index for given horizon."""
        faiss_file = self.indices_dir / f"faiss_{horizon}h_flatip.faiss"
        
        result = {
            'horizon': horizon,
            'file_exists': self.check_file_exists(faiss_file),
            'file_path': str(faiss_file),
            'ntotal': None,
            'dimension': None,
            'expected_count': expected_count,
            'count_matches': False,
            'index_type': None,
            'file_size_mb': None,
            'errors': []
        }
        
        if not result['file_exists']:
            result['errors'].append(f"File not found: {faiss_file}")
            return result
            
        try:
            # Load FAISS index
            index = faiss.read_index(str(faiss_file))
            result['ntotal'] = index.ntotal
            result['dimension'] = index.d
            result['index_type'] = type(index).__name__
            result['file_size_mb'] = round(faiss_file.stat().st_size / 1024 / 1024, 2)
            
            if expected_count is not None:
                if result['ntotal'] == expected_count:
                    result['count_matches'] = True
                    logger.info(f"✅ {horizon}h FAISS: {result['ntotal']} vectors - MATCHES outcomes")
                else:
                    result['count_matches'] = False
                    result['errors'].append(
                        f"Vector count mismatch: expected {expected_count}, got {result['ntotal']}"
                    )
                    logger.error(f"❌ {horizon}h FAISS: {result['ntotal']} vectors - MISMATCH with outcomes ({expected_count})")
            else:
                logger.info(f"📊 {horizon}h FAISS: {result['ntotal']} vectors, {result['dimension']}D")
            
        except Exception as e:
            result['errors'].append(f"Error loading FAISS index: {str(e)}")
            logger.error(f"❌ Error loading {faiss_file}: {e}")
            
        return result
    
    def validate_horizon(self, horizon: int) -> Dict[str, Any]:
        """Validate all artifacts for a single horizon."""
        logger.info(f"\n🔍 Validating {horizon}h horizon artifacts...")
        
        # Validate outcomes first to get expected row count
        outcomes_result = self.validate_outcomes_file(horizon)
        expected_rows = outcomes_result.get('n_samples')
        
        # Validate metadata with expected row count
        metadata_result = self.validate_metadata_file(horizon, expected_rows)
        
        # Validate FAISS index with expected count
        faiss_result = self.validate_faiss_index(horizon, expected_rows)
        
        # Summary for this horizon
        horizon_result = {
            'horizon': horizon,
            'outcomes': outcomes_result,
            'metadata': metadata_result,
            'faiss': faiss_result,
            'all_valid': (
                outcomes_result.get('shape_valid', False) and
                metadata_result.get('rows_match', False) and
                faiss_result.get('count_matches', False)
            ),
            'all_files_exist': (
                outcomes_result.get('file_exists', False) and
                metadata_result.get('file_exists', False) and
                faiss_result.get('file_exists', False)
            )
        }
        
        if horizon_result['all_valid'] and horizon_result['all_files_exist']:
            logger.info(f"✅ {horizon}h horizon: ALL ARTIFACTS VALID")
        else:
            logger.error(f"❌ {horizon}h horizon: VALIDATION FAILED")
            
        return horizon_result
    
    def validate_all_horizons(self) -> Dict[str, Any]:
        """Validate artifacts for all horizons."""
        logger.info("🚀 Starting data artifacts validation...")
        logger.info(f"📂 Base directory: {self.base_dir.absolute()}")
        logger.info(f"📊 Expected variable count: {len(VARIABLE_ORDER)}")
        logger.info(f"🎯 Horizons to validate: {HORIZONS}")
        
        results = {
            'validation_summary': {
                'timestamp': pd.Timestamp.now().isoformat(),
                'base_directory': str(self.base_dir.absolute()),
                'variable_order': VARIABLE_ORDER,
                'expected_variable_count': len(VARIABLE_ORDER),
                'horizons_tested': HORIZONS,
                'total_horizons': len(HORIZONS),
                'valid_horizons': 0,
                'invalid_horizons': 0,
                'missing_files': 0
            },
            'horizon_results': {},
            'errors': [],
            'warnings': []
        }
        
        for horizon in HORIZONS:
            try:
                horizon_result = self.validate_horizon(horizon)
                results['horizon_results'][horizon] = horizon_result
                
                if horizon_result['all_valid'] and horizon_result['all_files_exist']:
                    results['validation_summary']['valid_horizons'] += 1
                else:
                    results['validation_summary']['invalid_horizons'] += 1
                    
                # Count missing files
                if not horizon_result['all_files_exist']:
                    missing_count = sum([
                        not horizon_result['outcomes']['file_exists'],
                        not horizon_result['metadata']['file_exists'], 
                        not horizon_result['faiss']['file_exists']
                    ])
                    results['validation_summary']['missing_files'] += missing_count
                    
            except Exception as e:
                error_msg = f"Failed to validate {horizon}h horizon: {str(e)}"
                results['errors'].append(error_msg)
                logger.error(f"❌ {error_msg}")
                results['validation_summary']['invalid_horizons'] += 1
        
        return results
    
    def print_summary(self, results: Dict[str, Any]) -> None:
        """Print validation summary."""
        summary = results['validation_summary']
        
        print("\n" + "="*60)
        print("🎯 DATA ARTIFACTS VALIDATION SUMMARY")
        print("="*60)
        
        print(f"📊 Total horizons tested: {summary['total_horizons']}")
        print(f"✅ Valid horizons: {summary['valid_horizons']}")
        print(f"❌ Invalid horizons: {summary['invalid_horizons']}")
        print(f"📁 Missing files: {summary['missing_files']}")
        
        if summary['valid_horizons'] == summary['total_horizons']:
            print("\n🎉 ALL HORIZONS VALIDATED SUCCESSFULLY!")
        else:
            print(f"\n⚠️  {summary['invalid_horizons']} horizons failed validation")
            
        # Show detailed issues
        print(f"\n📋 Detailed Results:")
        for horizon, horizon_result in results['horizon_results'].items():
            status = "✅ VALID" if horizon_result['all_valid'] and horizon_result['all_files_exist'] else "❌ INVALID"
            print(f"  {horizon}h: {status}")
            
            if not horizon_result['all_files_exist']:
                print(f"    📁 Missing files:")
                if not horizon_result['outcomes']['file_exists']:
                    print(f"      - outcomes_{horizon}h.npy")
                if not horizon_result['metadata']['file_exists']:
                    print(f"      - metadata_{horizon}h_clean.parquet")
                if not horizon_result['faiss']['file_exists']:
                    print(f"      - faiss_{horizon}h_flatip.faiss")
            
            # Show counts if available
            outcomes = horizon_result['outcomes']
            metadata = horizon_result['metadata']  
            faiss_res = horizon_result['faiss']
            
            if outcomes.get('n_samples') is not None:
                print(f"    📊 Outcomes: {outcomes['n_samples']} samples × {outcomes['actual_variables']} vars")
            if metadata.get('n_rows') is not None:
                print(f"    📋 Metadata: {metadata['n_rows']} rows")
            if faiss_res.get('ntotal') is not None:
                print(f"    🔍 FAISS: {faiss_res['ntotal']} vectors")
                
        print("="*60)

def main():
    """Run data artifacts validation."""
    validator = DataArtifactsValidator()
    results = validator.validate_all_horizons()
    
    # Print summary
    validator.print_summary(results)
    
    # Save detailed results
    results_file = Path("data_artifacts_validation_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"💾 Detailed results saved to: {results_file}")
    
    # Return exit code based on validation success
    summary = results['validation_summary']
    if summary['valid_horizons'] == summary['total_horizons'] and summary['missing_files'] == 0:
        logger.info("🎉 All validations passed!")
        return 0
    else:
        logger.error("❌ Validation failures detected!")
        return 1

if __name__ == "__main__":
    exit(main())