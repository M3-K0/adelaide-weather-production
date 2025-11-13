#!/usr/bin/env python3
"""
FAISS Readiness Test for Adelaide Weather Forecasting System
Task BL2: Test FAISS indices integration and searchability.

Validates FAISS indices can be loaded and used by the analog forecaster.
"""

import sys
import os
import logging
import numpy as np
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_faiss_integration():
    """Test FAISS indices integration with the analog forecaster."""
    logger.info("Starting FAISS integration test...")
    
    try:
        # Import the analog ensemble forecaster
        from scripts.analog_forecaster import AnalogEnsembleForecaster
        
        logger.info("Initializing AnalogEnsembleForecaster...")
        # Initialize with minimal required paths
        model_path = "models/best_model.pt" 
        config_path = "configs/model.yaml"
        embeddings_dir = "embeddings"
        indices_dir = "indices"
        
        forecaster = AnalogEnsembleForecaster(
            model_path=model_path,
            config_path=config_path,
            embeddings_dir=embeddings_dir,
            indices_dir=indices_dir,
            use_optimized_index=False  # Use FlatIP indices
        )
        
        # Test each horizon
        horizons = [6, 12, 24, 48]
        test_results = {}
        
        for horizon in horizons:
            logger.info(f"Testing horizon {horizon}h...")
            try:
                # Check if index exists for this horizon
                if horizon in forecaster.indices:
                    index = forecaster.indices[horizon]
                    
                    # Basic checks
                    dimension = index.d
                    ntotal = index.ntotal
                    
                    logger.info(f"Horizon {horizon}h: d={dimension}, ntotal={ntotal}")
                    
                    # Verify dimension
                    if dimension != 256:
                        logger.error(f"Horizon {horizon}h: Wrong dimension! Expected 256, got {dimension}")
                        test_results[horizon] = {'status': 'FAILED', 'reason': 'Wrong dimension'}
                        continue
                    
                    # Test search capability with dummy vector
                    if ntotal > 0:
                        dummy_vector = np.random.random((1, 256)).astype(np.float32)
                        k = min(5, ntotal)
                        distances, indices = index.search(dummy_vector, k)
                        
                        if len(distances[0]) > 0:
                            logger.info(f"Horizon {horizon}h: Search test PASSED (found {len(distances[0])} results)")
                            test_results[horizon] = {'status': 'PASSED', 'ntotal': ntotal, 'dimension': dimension}
                        else:
                            logger.error(f"Horizon {horizon}h: Search returned no results")
                            test_results[horizon] = {'status': 'FAILED', 'reason': 'No search results'}
                    else:
                        logger.warning(f"Horizon {horizon}h: Index is empty (ntotal=0)")
                        test_results[horizon] = {'status': 'WARNING', 'reason': 'Empty index'}
                        
                else:
                    logger.error(f"Horizon {horizon}h: Index not found in forecaster")
                    test_results[horizon] = {'status': 'FAILED', 'reason': 'Index not loaded'}
                    
            except Exception as e:
                logger.error(f"Horizon {horizon}h: Test failed with error: {e}")
                test_results[horizon] = {'status': 'ERROR', 'reason': str(e)}
        
        # Log summary
        logger.info("=" * 60)
        logger.info("FAISS INTEGRATION TEST SUMMARY")
        logger.info("=" * 60)
        
        all_passed = True
        for horizon in horizons:
            result = test_results.get(horizon, {'status': 'UNKNOWN'})
            status = result['status']
            
            if status == 'PASSED':
                logger.info(f"Horizon {horizon}h: ✓ PASSED (ntotal={result['ntotal']}, d={result['dimension']})")
            elif status == 'WARNING':
                logger.warning(f"Horizon {horizon}h: ⚠ WARNING ({result['reason']})")
                # Warnings don't fail the test as per requirements
            else:
                logger.error(f"Horizon {horizon}h: ✗ {status} ({result.get('reason', 'Unknown')})")
                all_passed = False
        
        logger.info("=" * 60)
        
        if all_passed:
            logger.info("🎉 FAISS INTEGRATION TEST COMPLETED SUCCESSFULLY!")
            return True
        else:
            logger.error("❌ SOME FAISS INTEGRATION TESTS FAILED!")
            return False
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        logger.info("This might indicate the forecaster is not properly set up")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during FAISS integration test: {e}")
        return False

def test_indices_files():
    """Test that all required FAISS index files exist."""
    logger.info("Checking FAISS index files...")
    
    indices_dir = Path("indices")
    required_files = [
        "faiss_6h_flatip.faiss",
        "faiss_12h_flatip.faiss", 
        "faiss_24h_flatip.faiss",
        "faiss_48h_flatip.faiss"
    ]
    
    all_exist = True
    for file_name in required_files:
        file_path = indices_dir / file_name
        if file_path.exists():
            size_mb = file_path.stat().st_size / (1024 * 1024)
            logger.info(f"✓ {file_name}: {size_mb:.1f} MB")
        else:
            logger.error(f"✗ {file_name}: NOT FOUND")
            all_exist = False
    
    return all_exist

def main():
    """Main test function."""
    logger.info("Starting FAISS readiness validation...")
    logger.info(f"Working directory: {os.getcwd()}")
    
    # Test 1: Check index files exist
    files_ok = test_indices_files()
    
    # Test 2: Test FAISS integration
    integration_ok = test_faiss_integration()
    
    # Final result
    if files_ok and integration_ok:
        logger.info("🎉 ALL FAISS READINESS TESTS PASSED!")
        return True
    else:
        logger.error("❌ FAISS READINESS TESTS FAILED!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)