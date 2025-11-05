#!/usr/bin/env python3
"""
FAISS Health Monitor Integration Test
====================================

Test script to verify the FAISS health monitoring system integration
with the Adelaide Weather Forecasting API.

This script tests:
1. FAISSHealthMonitor initialization
2. Query tracking with context manager
3. Health summary generation
4. Prometheus metrics collection
5. Integration with main API endpoints

Usage:
    python test_faiss_monitoring_integration.py
"""

import asyncio
import logging
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from api.services.faiss_health_monitoring import (
    FAISSHealthMonitor, 
    get_faiss_health_monitor
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_faiss_health_monitor():
    """Test the FAISS health monitoring system."""
    logger.info("🧪 Starting FAISS Health Monitor Integration Test")
    
    try:
        # Test 1: Initialize monitor
        logger.info("1️⃣ Testing monitor initialization...")
        monitor = FAISSHealthMonitor()
        
        # Start monitoring
        start_success = await monitor.start_monitoring()
        assert start_success, "Monitor failed to start"
        logger.info("✅ Monitor started successfully")
        
        # Test 2: Query tracking
        logger.info("2️⃣ Testing query tracking...")
        
        # Simulate FAISS queries
        for i in range(5):
            horizon = f"{[6, 12, 24, 48][i % 4]}h"
            
            async with monitor.track_query(
                horizon=horizon, 
                k_neighbors=50,
                index_type="test"
            ) as query:
                # Simulate FAISS operation
                await asyncio.sleep(0.01)  # 10ms operation
                logger.info(f"   Query {i+1}: {horizon} horizon tracked")
        
        logger.info("✅ Query tracking working correctly")
        
        # Test 3: Health summary
        logger.info("3️⃣ Testing health summary...")
        health_summary = await monitor.get_health_summary()
        
        # Verify health summary structure
        required_keys = ["status", "timestamp", "monitoring", "query_performance", "system"]
        for key in required_keys:
            assert key in health_summary, f"Missing key in health summary: {key}"
        
        # Check query performance metrics
        perf = health_summary["query_performance"]
        assert perf["total_queries"] == 5, f"Expected 5 queries, got {perf['total_queries']}"
        assert perf["error_rate"] == 0.0, f"Unexpected error rate: {perf['error_rate']}"
        
        logger.info("✅ Health summary structure valid")
        logger.info(f"   Status: {health_summary['status']}")
        logger.info(f"   Total queries: {perf['total_queries']}")
        logger.info(f"   Avg latency: {perf['avg_latency_ms']:.1f}ms")
        
        # Test 4: Prometheus metrics
        logger.info("4️⃣ Testing Prometheus metrics...")
        metrics_text = monitor.get_prometheus_metrics()
        
        # Verify key metrics are present
        expected_metrics = [
            "faiss_queries_total",
            "faiss_query_duration_seconds",
            "faiss_active_queries",
            "faiss_build_info"
        ]
        
        for metric in expected_metrics:
            assert metric in metrics_text, f"Missing Prometheus metric: {metric}"
        
        logger.info("✅ Prometheus metrics generated correctly")
        logger.info(f"   Metrics size: {len(metrics_text)} characters")
        
        # Test 5: Error handling
        logger.info("5️⃣ Testing error handling...")
        
        try:
            async with monitor.track_query("24h", 50) as query:
                # Simulate an error
                raise ValueError("Test error")
        except ValueError:
            pass  # Expected
        
        # Check that error was recorded
        updated_health = await monitor.get_health_summary()
        perf = updated_health["query_performance"]
        assert perf["total_queries"] == 6, "Error query not counted"
        
        logger.info("✅ Error handling working correctly")
        
        # Test 6: Global instance
        logger.info("6️⃣ Testing global instance...")
        global_monitor = await get_faiss_health_monitor()
        assert global_monitor is not None, "Global monitor not available"
        
        global_health = await global_monitor.get_health_summary()
        assert "status" in global_health, "Global monitor not working"
        
        logger.info("✅ Global instance working correctly")
        
        # Test 7: Async context manager
        logger.info("7️⃣ Testing async context manager...")
        
        async with FAISSHealthMonitor() as ctx_monitor:
            # Monitor should start automatically
            ctx_health = await ctx_monitor.get_health_summary()
            assert ctx_health["monitoring"]["active"], "Context monitor not active"
        
        # Monitor should stop automatically after context exit
        logger.info("✅ Async context manager working correctly")
        
        # Cleanup
        await monitor.stop_monitoring()
        
        logger.info("🎉 All tests passed! FAISS Health Monitor integration successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_api_integration():
    """Test integration with API endpoints (mock)."""
    logger.info("🌐 Testing API integration patterns...")
    
    try:
        # Simulate the main.py startup pattern
        monitor = await get_faiss_health_monitor()
        
        # Simulate forecast endpoint usage
        horizon = "24h"
        async with monitor.track_query(horizon, k_neighbors=50, index_type="ivfpq") as query:
            # This is where the actual FAISS search would happen
            await asyncio.sleep(0.005)  # 5ms simulated search
        
        # Simulate health endpoint
        health_response = await monitor.get_health_summary()
        
        # Simulate metrics endpoint  
        metrics_response = monitor.get_prometheus_metrics()
        
        logger.info("✅ API integration patterns working correctly")
        logger.info(f"   Health status: {health_response['status']}")
        logger.info(f"   Metrics available: {len(metrics_response)} chars")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ API integration test failed: {e}")
        return False

async def main():
    """Run all integration tests."""
    logger.info("🚀 Starting FAISS Health Monitor Integration Tests")
    
    tests = [
        ("Core Monitor Test", test_faiss_health_monitor),
        ("API Integration Test", test_api_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*50}")
        
        start_time = time.time()
        success = await test_func()
        duration = time.time() - start_time
        
        results.append((test_name, success, duration))
        
        if success:
            logger.info(f"✅ {test_name} PASSED ({duration:.2f}s)")
        else:
            logger.error(f"❌ {test_name} FAILED ({duration:.2f}s)")
    
    # Final summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, duration in results:
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} {test_name} ({duration:.2f}s)")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED - FAISS Health Monitoring Ready for Production!")
        return 0
    else:
        logger.error("💥 SOME TESTS FAILED - Check implementation before deployment")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)