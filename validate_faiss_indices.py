#!/usr/bin/env python3
"""
FAISS Index Validation Script
Task BL2: Confirm FAISS indices are readable and meet specifications.

Validates:
1. Each index has dimension d==256
2. Logs ntotal for each horizon
3. Verifies indices are readable and searchable
4. Logs warnings on size drift but doesn't hard fail
"""

import faiss
import numpy as np
import os
import logging
from typing import Dict, List, Tuple
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FAISSIndexValidator:
    """Validates FAISS indices for the Adelaide Weather Forecasting System."""
    
    def __init__(self, indices_dir: str = "indices"):
        self.indices_dir = Path(indices_dir)
        self.required_indices = [
            "faiss_6h_flatip.faiss",
            "faiss_12h_flatip.faiss", 
            "faiss_24h_flatip.faiss",
            "faiss_48h_flatip.faiss"
        ]
        self.expected_dimension = 256
        self.validation_results = {}
        
    def validate_all_indices(self) -> bool:
        """Validate all required FAISS indices."""
        logger.info("Starting FAISS index validation...")
        
        all_valid = True
        
        for index_file in self.required_indices:
            horizon = self._extract_horizon(index_file)
            try:
                is_valid = self._validate_single_index(index_file, horizon)
                if not is_valid:
                    all_valid = False
            except Exception as e:
                logger.error(f"Failed to validate {index_file}: {e}")
                all_valid = False
                self.validation_results[horizon] = {
                    'status': 'FAILED',
                    'error': str(e)
                }
        
        self._log_validation_summary()
        return all_valid
    
    def _validate_single_index(self, index_file: str, horizon: int) -> bool:
        """Validate a single FAISS index."""
        index_path = self.indices_dir / index_file
        
        if not index_path.exists():
            logger.error(f"Index file not found: {index_path}")
            return False
        
        try:
            # Load the FAISS index
            logger.info(f"Loading FAISS index: {index_file}")
            index = faiss.read_index(str(index_path))
            
            # Validate dimensions
            dimension_valid = self._validate_dimension(index, horizon)
            
            # Log ntotal
            ntotal = index.ntotal
            logger.info(f"Index {index_file}: ntotal={ntotal}")
            
            # Test searchability
            searchable = self._test_searchability(index, horizon)
            
            # Check for size drift (warning only)
            self._check_size_drift(index, horizon, ntotal)
            
            # Store validation results
            self.validation_results[horizon] = {
                'status': 'VALID' if dimension_valid and searchable else 'INVALID',
                'dimension': index.d,
                'ntotal': ntotal,
                'dimension_valid': dimension_valid,
                'searchable': searchable,
                'index_type': type(index).__name__,
                'file_path': str(index_path)
            }
            
            return dimension_valid and searchable
            
        except Exception as e:
            logger.error(f"Error validating {index_file}: {e}")
            return False
    
    def _validate_dimension(self, index, horizon: int) -> bool:
        """Validate that the index dimension equals expected value."""
        actual_dim = index.d
        if actual_dim != self.expected_dimension:
            logger.error(
                f"Horizon {horizon}h: Dimension mismatch! "
                f"Expected: {self.expected_dimension}, Got: {actual_dim}"
            )
            return False
        else:
            logger.info(f"Horizon {horizon}h: Dimension validation PASSED (d={actual_dim})")
            return True
    
    def _test_searchability(self, index, horizon: int) -> bool:
        """Test that the index is searchable with a dummy query."""
        try:
            # Create a dummy query vector with correct dimension
            query_vector = np.random.random((1, self.expected_dimension)).astype(np.float32)
            
            # Test search with k=min(5, ntotal) to avoid requesting more than available
            k = min(5, index.ntotal) if index.ntotal > 0 else 1
            
            if index.ntotal == 0:
                logger.warning(f"Horizon {horizon}h: Index is empty (ntotal=0)")
                return False
            
            # Perform search
            distances, indices = index.search(query_vector, k)
            
            logger.info(f"Horizon {horizon}h: Search test PASSED (retrieved {len(indices[0])} results)")
            return True
            
        except Exception as e:
            logger.error(f"Horizon {horizon}h: Search test FAILED: {e}")
            return False
    
    def _check_size_drift(self, index, horizon: int, ntotal: int):
        """Check for size drift and log warnings (non-failing)."""
        # Expected approximate sizes based on typical weather data
        # These are rough estimates - actual sizes may vary legitimately
        expected_sizes = {
            6: 50000,   # ~50k vectors for 6h horizon
            12: 45000,  # ~45k vectors for 12h horizon  
            24: 40000,  # ~40k vectors for 24h horizon
            48: 35000   # ~35k vectors for 48h horizon
        }
        
        expected = expected_sizes.get(horizon, 40000)
        drift_threshold = 0.3  # 30% drift threshold
        
        if ntotal == 0:
            logger.warning(f"Horizon {horizon}h: Index is empty (ntotal=0)")
            return
        
        drift_ratio = abs(ntotal - expected) / expected
        
        if drift_ratio > drift_threshold:
            logger.warning(
                f"Horizon {horizon}h: Size drift detected! "
                f"Expected ~{expected}, Got {ntotal} "
                f"(drift: {drift_ratio:.1%})"
            )
        else:
            logger.info(
                f"Horizon {horizon}h: Size within tolerance "
                f"(expected ~{expected}, got {ntotal}, drift: {drift_ratio:.1%})"
            )
    
    def _extract_horizon(self, index_file: str) -> int:
        """Extract horizon value from index filename."""
        # Extract number before 'h' in filename like "faiss_6h_flatip.faiss"
        import re
        match = re.search(r'(\d+)h', index_file)
        if match:
            return int(match.group(1))
        else:
            raise ValueError(f"Could not extract horizon from filename: {index_file}")
    
    def _log_validation_summary(self):
        """Log a summary of all validation results."""
        logger.info("=" * 60)
        logger.info("FAISS INDEX VALIDATION SUMMARY")
        logger.info("=" * 60)
        
        for horizon in sorted(self.validation_results.keys()):
            result = self.validation_results[horizon]
            status = result.get('status', 'UNKNOWN')
            
            if status == 'VALID':
                logger.info(f"Horizon {horizon}h: ✓ VALID (d={result['dimension']}, ntotal={result['ntotal']})")
            elif status == 'INVALID':
                logger.error(f"Horizon {horizon}h: ✗ INVALID (d={result.get('dimension', 'N/A')}, ntotal={result.get('ntotal', 'N/A')})")
            else:
                logger.error(f"Horizon {horizon}h: ✗ FAILED ({result.get('error', 'Unknown error')})")
        
        logger.info("=" * 60)
    
    def get_validation_report(self) -> Dict:
        """Get a structured validation report."""
        return {
            'validation_complete': True,
            'expected_dimension': self.expected_dimension,
            'indices_validated': len(self.validation_results),
            'results_by_horizon': self.validation_results,
            'all_valid': all(
                result.get('status') == 'VALID' 
                for result in self.validation_results.values()
            )
        }


def main():
    """Main validation function."""
    # Change to the correct working directory if needed
    if not os.path.exists('indices'):
        logger.error("'indices' directory not found in current directory")
        logger.info(f"Current directory: {os.getcwd()}")
        logger.info("Available directories: " + ", ".join([d for d in os.listdir('.') if os.path.isdir(d)]))
        sys.exit(1)
    
    validator = FAISSIndexValidator()
    
    logger.info("Starting FAISS index validation for Adelaide Weather Forecasting System")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Indices directory: {validator.indices_dir}")
    
    # Perform validation
    all_valid = validator.validate_all_indices()
    
    # Get structured report
    report = validator.get_validation_report()
    
    # Log final status
    if all_valid:
        logger.info("🎉 ALL FAISS INDICES VALIDATED SUCCESSFULLY!")
    else:
        logger.error("❌ SOME FAISS INDICES FAILED VALIDATION!")
    
    # Return appropriate exit code
    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()