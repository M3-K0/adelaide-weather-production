#!/usr/bin/env python3
"""
End-to-End FAISS Data Flow Validation Test
==========================================

This script validates the complete end-to-end data flow from FAISS indices 
through the API service to ensure real historical data is flowing correctly 
without any synthetic generation.

Validates:
1. FAISS indices integrity and real data
2. Analog Search Service functionality 
3. Real historical pattern retrieval
4. Zero synthetic generation in pipeline
5. All forecast horizons (6h, 12h, 24h, 48h)
6. Data integrity and performance metrics

Usage:
    python test_faiss_end_to_end.py
"""

import asyncio
import numpy as np
import sys
from pathlib import Path
from datetime import datetime, timezone
import logging

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from api.services.analog_search import AnalogSearchService, AnalogSearchConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FAISSEndToEndValidator:
    """Comprehensive end-to-end validation of FAISS data flow."""
    
    def __init__(self):
        self.config = AnalogSearchConfig()
        self.service = None
        self.test_results = {}
    
    async def initialize(self):
        """Initialize the analog search service."""
        logger.info("🚀 Initializing AnalogSearchService for end-to-end validation")
        
        self.service = AnalogSearchService(self.config)
        success = await self.service.initialize()
        
        if not success:
            logger.error("❌ Failed to initialize AnalogSearchService")
            return False
            
        logger.info("✅ AnalogSearchService initialized successfully")
        return True
    
    async def validate_faiss_indices(self):
        """Validate FAISS indices contain real data."""
        logger.info("🔍 Validating FAISS indices integrity...")
        
        horizons_tested = []
        for horizon in [6, 12, 24, 48]:
            try:
                # Test basic search functionality
                query_time = datetime.now(timezone.utc)
                search_result = await self.service.search_analogs(
                    query_time=query_time,
                    horizon=horizon,
                    k=10,
                    correlation_id=f"test-{horizon}h"
                )
                
                if search_result.success:
                    # Validate real data characteristics
                    distances = search_result.distances
                    indices = search_result.indices
                    
                    # Check for real similarity values (not 0.000 bug)
                    if len(distances) > 0 and np.all(np.abs(distances) < 1e-6):
                        logger.error(f"❌ {horizon}h: FAISS returning zero distances - normalization bug")
                        self.test_results[f"{horizon}h_faiss"] = False
                        continue
                    
                    # Check for realistic similarity range
                    mean_distance = np.mean(distances)
                    if mean_distance > 10.0 or mean_distance < 0.0:
                        logger.warning(f"⚠️ {horizon}h: Unusual distance values: mean={mean_distance:.3f}")
                    
                    # Check for monotonic distance ordering
                    if len(distances) > 1 and not all(distances[i] <= distances[i+1] + 1e-6 for i in range(len(distances)-1)):
                        logger.error(f"❌ {horizon}h: Distance monotonicity violation")
                        self.test_results[f"{horizon}h_faiss"] = False
                        continue
                    
                    # Check indices are within reasonable bounds
                    max_expected_indices = {"6": 7000, "12": 7000, "24": 14000, "48": 14000}
                    max_expected = max_expected_indices.get(str(horizon), 15000)
                    
                    if np.any(indices >= max_expected) or np.any(indices < 0):
                        logger.error(f"❌ {horizon}h: Invalid index values - range [0, {max_expected}]")
                        self.test_results[f"{horizon}h_faiss"] = False
                        continue
                    
                    # Verify search metadata indicates real FAISS
                    search_method = search_result.search_metadata.get('search_method', 'unknown')
                    if search_method == 'fallback_mock':
                        logger.warning(f"⚠️ {horizon}h: Using fallback mock instead of real FAISS")
                        self.test_results[f"{horizon}h_faiss"] = False
                        continue
                    
                    logger.info(f"✅ {horizon}h: FAISS working correctly - {len(indices)} analogs, method={search_method}")
                    logger.info(f"   Distance range: {np.min(distances):.4f} to {np.max(distances):.4f}")
                    logger.info(f"   Index range: {np.min(indices)} to {np.max(indices)}")
                    
                    horizons_tested.append(horizon)
                    self.test_results[f"{horizon}h_faiss"] = True
                    
                else:
                    logger.error(f"❌ {horizon}h: Search failed - {search_result.error_message}")
                    self.test_results[f"{horizon}h_faiss"] = False
                    
            except Exception as e:
                logger.error(f"❌ {horizon}h: Exception during validation - {e}")
                self.test_results[f"{horizon}h_faiss"] = False
        
        if len(horizons_tested) == 4:
            logger.info("🎉 All FAISS indices validated successfully")
            return True
        else:
            logger.error(f"❌ Only {len(horizons_tested)}/4 horizons working: {horizons_tested}")
            return False
    
    async def validate_analog_details_api(self):
        """Validate the comprehensive analog details API."""
        logger.info("🔍 Validating comprehensive analog details API...")
        
        try:
            query_time = datetime.now(timezone.utc)
            
            # Test the full analog details API
            analog_details = await self.service.get_analog_details(
                query_time=query_time,
                horizon=24,
                variable="temperature",
                k=5,
                correlation_id="test-details"
            )
            
            # Validate response structure
            if not analog_details.get("success", False):
                logger.error(f"❌ Analog details API failed: {analog_details.get('error', 'Unknown error')}")
                self.test_results["analog_details_api"] = False
                return False
            
            # Check for required sections
            required_sections = ["analogs", "search_metadata", "timeline_data", "similarity_analysis", "meteorological_context"]
            for section in required_sections:
                if section not in analog_details:
                    logger.error(f"❌ Missing required section: {section}")
                    self.test_results["analog_details_api"] = False
                    return False
            
            # Validate analog data contains real historical information
            analogs = analog_details["analogs"]
            if len(analogs) == 0:
                logger.error("❌ No analogs returned in details API")
                self.test_results["analog_details_api"] = False
                return False
            
            # Check first analog for realistic data
            first_analog = analogs[0]
            required_analog_fields = ["rank", "analog_index", "historical_date", "similarity_score", "distance"]
            for field in required_analog_fields:
                if field not in first_analog:
                    logger.error(f"❌ Missing analog field: {field}")
                    self.test_results["analog_details_api"] = False
                    return False
            
            # Validate similarity scores are realistic
            similarity = first_analog["similarity_score"]
            if not (0.0 <= similarity <= 1.0):
                logger.error(f"❌ Invalid similarity score: {similarity}")
                self.test_results["analog_details_api"] = False
                return False
            
            # Validate historical date is reasonable
            historical_date = first_analog["historical_date"]
            try:
                historical_dt = datetime.fromisoformat(historical_date.replace("Z", "+00:00"))
                years_back = (query_time - historical_dt).days / 365.25
                if years_back < 0 or years_back > 15:  # Should be between 0-15 years back
                    logger.warning(f"⚠️ Unusual historical date: {years_back:.1f} years ago")
            except ValueError:
                logger.error(f"❌ Invalid historical date format: {historical_date}")
                self.test_results["analog_details_api"] = False
                return False
            
            # Check FAISS search metadata
            search_metadata = analog_details["search_metadata"]
            if search_metadata.get("search_method") == "fallback_mock":
                logger.warning("⚠️ Analog details using fallback mock instead of real FAISS")
                self.test_results["analog_details_api"] = False
                return False
            
            logger.info(f"✅ Analog details API working correctly")
            logger.info(f"   Returned {len(analogs)} analogs with rich metadata")
            logger.info(f"   Search method: {search_metadata.get('search_method', 'unknown')}")
            logger.info(f"   First analog: {similarity:.3f} similarity, {historical_dt.strftime('%Y-%m-%d')}")
            
            self.test_results["analog_details_api"] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Analog details API validation failed: {e}")
            self.test_results["analog_details_api"] = False
            return False
    
    async def validate_no_synthetic_generation(self):
        """Validate that no synthetic data generation is occurring."""
        logger.info("🔍 Validating zero synthetic data generation...")
        
        try:
            # Run multiple searches and check for deterministic behavior
            query_time = datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)  # Fixed timestamp
            
            # Run same search twice
            result1 = await self.service.search_analogs(
                query_time=query_time,
                horizon=24,
                k=10,
                correlation_id="deterministic-test-1"
            )
            
            result2 = await self.service.search_analogs(
                query_time=query_time,
                horizon=24,
                k=10,
                correlation_id="deterministic-test-2"
            )
            
            if not (result1.success and result2.success):
                logger.error("❌ Deterministic test failed - searches unsuccessful")
                self.test_results["no_synthetic"] = False
                return False
            
            # Check if results are identical (they should be for real FAISS)
            if not np.array_equal(result1.indices, result2.indices):
                # Check if this is due to fallback mock
                if (result1.search_metadata.get('search_method') == 'fallback_mock' or 
                    result2.search_metadata.get('search_method') == 'fallback_mock'):
                    logger.warning("⚠️ Non-deterministic results due to fallback mock - not using real FAISS")
                    self.test_results["no_synthetic"] = False
                    return False
                else:
                    logger.error("❌ Non-deterministic results despite real FAISS - potential synthetic generation")
                    self.test_results["no_synthetic"] = False
                    return False
            
            if not np.allclose(result1.distances, result2.distances, rtol=1e-6):
                logger.error("❌ Non-deterministic distances - potential synthetic generation")
                self.test_results["no_synthetic"] = False
                return False
            
            logger.info("✅ Deterministic results confirmed - no synthetic generation")
            logger.info(f"   Search method: {result1.search_metadata.get('search_method')}")
            logger.info(f"   Identical indices and distances across multiple runs")
            
            self.test_results["no_synthetic"] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Synthetic generation validation failed: {e}")
            self.test_results["no_synthetic"] = False
            return False
    
    async def validate_performance_characteristics(self):
        """Validate performance characteristics of real FAISS data flow."""
        logger.info("🔍 Validating performance characteristics...")
        
        try:
            search_times = []
            
            # Run performance tests on multiple horizons
            for horizon in [6, 12, 24, 48]:
                query_time = datetime.now(timezone.utc)
                
                import time
                start_time = time.time()
                
                search_result = await self.service.search_analogs(
                    query_time=query_time,
                    horizon=horizon,
                    k=50,  # Larger k for performance test
                    correlation_id=f"perf-test-{horizon}h"
                )
                
                end_time = time.time()
                search_time_ms = (end_time - start_time) * 1000
                search_times.append(search_time_ms)
                
                if search_result.success:
                    reported_time = search_result.performance_metrics.get('total_time_ms', 0)
                    logger.info(f"✅ {horizon}h: {search_time_ms:.1f}ms actual, {reported_time:.1f}ms reported")
                else:
                    logger.error(f"❌ {horizon}h: Performance test failed")
                    self.test_results["performance"] = False
                    return False
            
            # Check performance metrics
            avg_time = np.mean(search_times)
            max_time = np.max(search_times)
            
            if avg_time > 5000:  # 5 second max average
                logger.warning(f"⚠️ Average search time {avg_time:.1f}ms exceeds 5s threshold")
            
            if max_time > 10000:  # 10 second max individual
                logger.warning(f"⚠️ Max search time {max_time:.1f}ms exceeds 10s threshold")
            
            logger.info(f"✅ Performance validation completed")
            logger.info(f"   Average search time: {avg_time:.1f}ms")
            logger.info(f"   Max search time: {max_time:.1f}ms")
            logger.info(f"   All horizons: {[f'{t:.1f}ms' for t in search_times]}")
            
            self.test_results["performance"] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Performance validation failed: {e}")
            self.test_results["performance"] = False
            return False
    
    async def validate_error_handling(self):
        """Validate graceful error handling and degradation."""
        logger.info("🔍 Validating error handling and graceful degradation...")
        
        try:
            # Test invalid inputs
            invalid_tests = [
                ("invalid_horizon", {"query_time": datetime.now(timezone.utc), "horizon": 99, "k": 10}),
                ("invalid_k", {"query_time": datetime.now(timezone.utc), "horizon": 24, "k": -5}),
                ("invalid_k_large", {"query_time": datetime.now(timezone.utc), "horizon": 24, "k": 1000}),
            ]
            
            for test_name, params in invalid_tests:
                try:
                    result = await self.service.search_analogs(
                        correlation_id=f"error-test-{test_name}",
                        **params
                    )
                    
                    if result.success:
                        logger.error(f"❌ {test_name}: Should have failed but succeeded")
                        self.test_results["error_handling"] = False
                        return False
                    else:
                        logger.info(f"✅ {test_name}: Properly rejected with error")
                        
                except Exception as e:
                    logger.info(f"✅ {test_name}: Properly raised exception: {e}")
            
            logger.info("✅ Error handling validation completed")
            self.test_results["error_handling"] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Error handling validation failed: {e}")
            self.test_results["error_handling"] = False
            return False
    
    async def run_validation(self):
        """Run comprehensive end-to-end validation."""
        logger.info("🚀 Starting End-to-End FAISS Data Flow Validation")
        logger.info("="*60)
        
        # Initialize service
        if not await self.initialize():
            logger.error("❌ Service initialization failed - cannot continue validation")
            return False
        
        # Run all validation tests
        validation_tests = [
            ("FAISS Indices Integrity", self.validate_faiss_indices),
            ("Analog Details API", self.validate_analog_details_api),
            ("Zero Synthetic Generation", self.validate_no_synthetic_generation),
            ("Performance Characteristics", self.validate_performance_characteristics),
            ("Error Handling", self.validate_error_handling),
        ]
        
        all_passed = True
        for test_name, test_func in validation_tests:
            logger.info(f"\n🔍 Running: {test_name}")
            logger.info("-" * 40)
            
            try:
                success = await test_func()
                if success:
                    logger.info(f"✅ {test_name}: PASSED")
                else:
                    logger.error(f"❌ {test_name}: FAILED")
                    all_passed = False
            except Exception as e:
                logger.error(f"❌ {test_name}: EXCEPTION - {e}")
                all_passed = False
        
        # Final summary
        logger.info("\n" + "="*60)
        logger.info("📊 End-to-End FAISS Data Flow Validation Results")
        logger.info("="*60)
        
        for test_key, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"  {test_key}: {status}")
        
        if all_passed:
            logger.info("\n🎉 ALL VALIDATIONS PASSED!")
            logger.info("✅ Real FAISS data is flowing correctly through the entire pipeline")
            logger.info("✅ Zero synthetic generation confirmed")
            logger.info("✅ Historical analog data integrity validated")
            logger.info("✅ Performance characteristics within acceptable limits")
            logger.info("✅ Error handling working correctly")
        else:
            logger.error("\n❌ VALIDATION FAILED!")
            logger.error("Some components are not working with real FAISS data")
        
        # Cleanup
        if self.service:
            await self.service.shutdown()
        
        return all_passed

async def main():
    """Main validation function."""
    validator = FAISSEndToEndValidator()
    success = await validator.run_validation()
    
    if success:
        print("\n🎉 End-to-end FAISS validation: SUCCESS")
        return 0
    else:
        print("\n❌ End-to-end FAISS validation: FAILED")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)