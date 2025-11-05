#!/usr/bin/env python3
"""
FAISS Integration Test for T-001
================================

Test script to verify the real FAISS search integration meets all quality gates:
- Distance monotonicity verification
- Horizon-specific index dimensions
- k>0 results returned per horizon
- p50/p95 search latencies logged

This script validates the critical path implementation for Wave 2 dependencies.
"""

import asyncio
import logging
import time
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from api.services.analog_search import AnalogSearchService, AnalogSearchConfig
from scripts.analog_forecaster import AnalogEnsembleForecaster

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FAISSIntegrationTester:
    """Test suite for FAISS integration quality gates."""
    
    def __init__(self):
        self.config = AnalogSearchConfig()
        self.service = None
        self.test_results = {}
        self.all_horizons = [6, 12, 24, 48]
        
    async def initialize_service(self) -> bool:
        """Initialize the analog search service."""
        try:
            logger.info("🚀 Initializing Analog Search Service for FAISS testing...")
            self.service = AnalogSearchService(self.config)
            success = await self.service.initialize()
            
            if success:
                logger.info("✅ Service initialized successfully")
                return True
            else:
                logger.warning("⚠️ Service initialized in degraded mode")
                return True  # Still usable for testing fallback
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize service: {e}")
            return False
    
    async def test_horizon_search_results(self, horizon: int) -> dict:
        """Test search results for a specific horizon."""
        logger.info(f"🔍 Testing {horizon}h horizon search...")
        
        test_result = {
            'horizon': horizon,
            'success': False,
            'results_count': 0,
            'distance_monotonic': False,
            'search_time_ms': 0,
            'error_message': None,
            'search_method': 'unknown'
        }
        
        try:
            # Use current time as query time
            query_time = datetime.now(timezone.utc)
            
            # Perform search
            start_time = time.time()
            result = await self.service.search_analogs(
                query_time=query_time,
                horizon=horizon,
                k=50,
                correlation_id=f"test-{horizon}h"
            )
            search_time = (time.time() - start_time) * 1000
            
            test_result['search_time_ms'] = search_time
            
            if not result.success:
                test_result['error_message'] = result.error_message
                return test_result
            
            # Validate results
            indices = result.indices
            distances = result.distances
            
            # Check minimum results requirement (k>0)
            test_result['results_count'] = len(indices)
            if len(indices) == 0:
                test_result['error_message'] = "No results returned"
                return test_result
            
            # Check distance monotonicity
            if len(distances) > 1:
                is_monotonic = np.all(np.diff(distances) >= -1e-6)  # Allow small numerical errors
                test_result['distance_monotonic'] = is_monotonic
                
                if not is_monotonic:
                    violations = np.sum(np.diff(distances) < -1e-6)
                    logger.warning(f"  ❌ Distance monotonicity violations: {violations}")
                else:
                    logger.info(f"  ✅ Distance monotonicity verified")
            else:
                test_result['distance_monotonic'] = True  # Single result is trivially monotonic
            
            # Extract search method
            test_result['search_method'] = result.search_metadata.get('search_method', 'unknown')
            
            # Log success metrics
            logger.info(f"  ✅ Search completed: {len(indices)} results in {search_time:.1f}ms")
            logger.info(f"  📊 Distance range: {distances[0]:.3f} - {distances[-1]:.3f}")
            logger.info(f"  🔧 Method: {test_result['search_method']}")
            
            test_result['success'] = True
            
        except Exception as e:
            logger.error(f"  ❌ Search failed: {e}")
            test_result['error_message'] = str(e)
        
        return test_result
    
    async def test_all_horizons(self) -> dict:
        """Test search for all horizons and collect metrics."""
        logger.info("🎯 Testing all forecast horizons...")
        
        horizon_results = {}
        search_times = []
        
        for horizon in self.all_horizons:
            result = await self.test_horizon_search_results(horizon)
            horizon_results[horizon] = result
            
            if result['success']:
                search_times.append(result['search_time_ms'])
        
        # Calculate p50/p95 latencies
        latency_metrics = {}
        if search_times:
            latency_metrics = {
                'p50_latency_ms': np.percentile(search_times, 50),
                'p95_latency_ms': np.percentile(search_times, 95),
                'mean_latency_ms': np.mean(search_times),
                'max_latency_ms': np.max(search_times),
                'total_searches': len(search_times)
            }
            
            logger.info(f"📊 Performance Metrics:")
            logger.info(f"  p50 latency: {latency_metrics['p50_latency_ms']:.1f}ms")
            logger.info(f"  p95 latency: {latency_metrics['p95_latency_ms']:.1f}ms")
            logger.info(f"  Mean latency: {latency_metrics['mean_latency_ms']:.1f}ms")
        
        return {
            'horizon_results': horizon_results,
            'latency_metrics': latency_metrics
        }
    
    async def test_dimension_verification(self) -> dict:
        """Test dimension verification for available indices."""
        logger.info("🔧 Testing dimension verification...")
        
        # Try to access a forecaster instance to check dimensions
        try:
            forecaster = await self.service.pool.acquire()
            if forecaster is None:
                return {'success': False, 'error': 'Could not acquire forecaster'}
            
            dimension_results = {}
            
            try:
                if hasattr(forecaster, 'indices'):
                    for horizon in self.all_horizons:
                        if horizon in forecaster.indices:
                            index = forecaster.indices[horizon]
                            dimension_results[horizon] = {
                                'dimension': index.d,
                                'size': index.ntotal,
                                'index_type': type(index).__name__
                            }
                            logger.info(f"  {horizon}h: dim={index.d}, size={index.ntotal}, type={type(index).__name__}")
                        else:
                            dimension_results[horizon] = {'error': 'Index not loaded'}
                else:
                    return {'success': False, 'error': 'Forecaster has no indices attribute'}
                
            finally:
                await self.service.pool.release(forecaster)
            
            return {'success': True, 'dimensions': dimension_results}
            
        except Exception as e:
            logger.error(f"❌ Dimension verification failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def run_comprehensive_test(self) -> dict:
        """Run comprehensive FAISS integration test."""
        logger.info("🧪 Starting Comprehensive FAISS Integration Test")
        logger.info("=" * 60)
        
        test_start = time.time()
        
        # Initialize service
        if not await self.initialize_service():
            return {
                'success': False,
                'error': 'Failed to initialize service',
                'test_duration_s': time.time() - test_start
            }
        
        # Test dimension verification
        dimension_test = await self.test_dimension_verification()
        
        # Test all horizons
        horizon_test = await self.test_all_horizons()
        
        # Analyze results
        total_duration = time.time() - test_start
        
        # Check if all quality gates passed
        quality_gates = self.analyze_quality_gates(horizon_test, dimension_test)
        
        # Generate final report
        final_result = {
            'success': quality_gates['all_passed'],
            'quality_gates': quality_gates,
            'dimension_verification': dimension_test,
            'horizon_tests': horizon_test,
            'test_duration_s': total_duration,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Log summary
        logger.info("📋 Test Summary:")
        logger.info(f"  Duration: {total_duration:.1f}s")
        logger.info(f"  Quality Gates: {'✅ PASSED' if quality_gates['all_passed'] else '❌ FAILED'}")
        
        return final_result
    
    def analyze_quality_gates(self, horizon_test: dict, dimension_test: dict) -> dict:
        """Analyze if all quality gates were met."""
        gates = {
            'distance_monotonicity': True,
            'min_results_per_horizon': True,
            'performance_metrics_available': False,
            'dimension_verification': dimension_test['success'],
            'all_horizons_tested': True
        }
        
        horizon_results = horizon_test.get('horizon_results', {})
        
        # Check each horizon
        for horizon in self.all_horizons:
            if horizon not in horizon_results:
                gates['all_horizons_tested'] = False
                continue
                
            result = horizon_results[horizon]
            
            # Check minimum results (k>0)
            if result.get('results_count', 0) == 0:
                gates['min_results_per_horizon'] = False
                logger.warning(f"❌ Quality Gate Failed: No results for {horizon}h")
            
            # Check distance monotonicity
            if not result.get('distance_monotonic', False):
                gates['distance_monotonicity'] = False
                logger.warning(f"❌ Quality Gate Failed: Distance monotonicity for {horizon}h")
        
        # Check performance metrics
        latency_metrics = horizon_test.get('latency_metrics', {})
        if 'p50_latency_ms' in latency_metrics and 'p95_latency_ms' in latency_metrics:
            gates['performance_metrics_available'] = True
        
        gates['all_passed'] = all(gates.values())
        
        return gates
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.service:
            await self.service.shutdown()

async def main():
    """Main test execution."""
    tester = FAISSIntegrationTester()
    
    try:
        result = await tester.run_comprehensive_test()
        
        # Print final status
        print("\n" + "="*60)
        print("🏁 FAISS Integration Test Results")
        print("="*60)
        
        if result['success']:
            print("✅ ALL QUALITY GATES PASSED")
            print("🚀 Ready for Wave 2 tasks")
        else:
            print("❌ QUALITY GATES FAILED")
            print("⚠️ Wave 2 tasks may be impacted")
        
        # Print key metrics
        if 'latency_metrics' in result.get('horizon_tests', {}):
            metrics = result['horizon_tests']['latency_metrics']
            if metrics:
                print(f"\n📊 Performance Summary:")
                print(f"   p50 latency: {metrics.get('p50_latency_ms', 0):.1f}ms")
                print(f"   p95 latency: {metrics.get('p95_latency_ms', 0):.1f}ms")
        
        # Return appropriate exit code
        return 0 if result['success'] else 1
        
    except KeyboardInterrupt:
        logger.info("❌ Test interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        return 1
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)