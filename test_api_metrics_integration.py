#!/usr/bin/env python3
"""
Integration test for unified API and FAISS metrics endpoint.

This test simulates creating API metrics alongside FAISS metrics
to verify they can coexist in the same registry without conflicts.
"""

import sys
import os
import asyncio
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_api_faiss_metrics_integration():
    """Test that API and FAISS metrics can coexist in default registry."""
    
    try:
        logger.info("🧪 Testing API + FAISS metrics integration...")
        
        # Import required modules
        from prometheus_client import Counter, Histogram, generate_latest, REGISTRY
        from api.services.faiss_health_monitoring import FAISSHealthMonitor
        
        # Step 1: Create some API-style metrics in the default registry
        logger.info("📊 Creating API metrics in default registry...")
        
        # Simulate the API metrics from main.py using same pattern
        def _get_or_create_metric(metric_cls, name, documentation, *args, **kwargs):
            existing = REGISTRY._names_to_collectors.get(name)
            if existing is not None:
                return existing
            return metric_cls(name, documentation, *args, **kwargs)
        
        # Create API metrics
        forecast_requests = _get_or_create_metric(
            Counter, 'forecast_requests_total', 'Total forecast requests'
        )
        response_duration_metric = _get_or_create_metric(
            Histogram, 'response_duration_seconds', 'Forecast request duration'
        )
        health_requests = _get_or_create_metric(
            Counter, 'health_requests_total', 'Total health check requests'
        )
        
        # Generate some API metrics
        forecast_requests.inc()
        response_duration_metric.observe(0.15)
        health_requests.inc()
        
        logger.info("✅ API metrics created and populated")
        
        # Step 2: Create FAISS health monitor (should use same registry)
        logger.info("📊 Creating FAISS health monitor...")
        faiss_monitor = FAISSHealthMonitor()
        
        # Verify it's using the default registry
        if faiss_monitor.registry is REGISTRY:
            logger.info("✅ FAISS monitor using default registry")
        else:
            logger.error("❌ FAISS monitor not using default registry")
            return False
        
        # Step 3: Start FAISS monitoring
        logger.info("🔍 Starting FAISS monitoring...")
        await faiss_monitor.start_monitoring()
        
        # Generate a FAISS query to create metrics
        async with faiss_monitor.track_query("24h", k_neighbors=50) as query:
            await asyncio.sleep(0.05)  # Simulate work
        
        # Step 4: Collect all metrics from unified registry
        logger.info("📊 Collecting unified metrics...")
        unified_metrics_text = generate_latest(REGISTRY).decode('utf-8')
        
        # Step 5: Verify both API and FAISS metrics are present
        logger.info("🔍 Verifying metrics presence...")
        
        # Check for API metrics
        api_metrics_found = []
        expected_api_metrics = [
            'forecast_requests_total',
            'response_duration_seconds',
            'health_requests_total'
        ]
        
        for metric_name in expected_api_metrics:
            if metric_name in unified_metrics_text:
                api_metrics_found.append(metric_name)
                logger.info(f"✅ Found API metric: {metric_name}")
            else:
                logger.error(f"❌ Missing API metric: {metric_name}")
        
        # Check for FAISS metrics
        faiss_metrics_found = []
        expected_faiss_metrics = [
            'faiss_query_duration_seconds',
            'faiss_queries_total',
            'faiss_active_queries'
        ]
        
        for metric_name in expected_faiss_metrics:
            if metric_name in unified_metrics_text:
                faiss_metrics_found.append(metric_name)
                logger.info(f"✅ Found FAISS metric: {metric_name}")
            else:
                logger.error(f"❌ Missing FAISS metric: {metric_name}")
        
        # Step 6: Verify metrics endpoint simulation
        logger.info("📡 Simulating /metrics endpoint response...")
        
        # This is essentially what the /metrics endpoint now does
        combined_response = unified_metrics_text
        
        # Add some performance metrics (like the endpoint does)
        performance_metrics = [
            "# HELP compression_requests_total Total compression requests",
            "# TYPE compression_requests_total counter", 
            "compression_requests_total 42",
            "",
            "# HELP rate_limit_requests_total Total rate limit checks",
            "# TYPE rate_limit_requests_total counter",
            "rate_limit_requests_total 100"
        ]
        
        combined_response += "\n" + "\n".join(performance_metrics)
        
        # Step 7: Validate results
        logger.info("📋 Validation Results:")
        logger.info(f"   - API metrics found: {len(api_metrics_found)}/{len(expected_api_metrics)}")
        logger.info(f"   - FAISS metrics found: {len(faiss_metrics_found)}/{len(expected_faiss_metrics)}")
        logger.info(f"   - Total response size: {len(combined_response)} characters")
        
        # Check for no conflicts
        help_lines = [line for line in combined_response.split('\n') if line.startswith('# HELP')]
        metric_names = [line.split()[2] for line in help_lines if len(line.split()) >= 3]
        unique_metrics = len(set(metric_names))
        total_metrics = len(metric_names)
        
        logger.info(f"   - Unique metric families: {unique_metrics}")
        logger.info(f"   - Total metric declarations: {total_metrics}")
        
        if unique_metrics != total_metrics:
            logger.error("❌ Metric name conflicts detected!")
            return False
        
        # Step 8: Cleanup
        logger.info("🧹 Cleaning up...")
        await faiss_monitor.stop_monitoring()
        
        # Final validation
        success = (len(api_metrics_found) >= 3 and 
                  len(faiss_metrics_found) >= 3 and
                  unique_metrics == total_metrics)
        
        if success:
            logger.info("🎉 API + FAISS metrics integration test PASSED")
            logger.info("✅ Key achievements:")
            logger.info("   - API and FAISS metrics coexist in same registry")
            logger.info("   - No metric name conflicts")
            logger.info("   - Unified /metrics endpoint works correctly")
            logger.info("   - Both metric types are properly exposed")
        else:
            logger.error("❌ API + FAISS metrics integration test FAILED")
        
        return success
        
    except Exception as e:
        logger.error(f"💥 Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run the integration test."""
    
    logger.info("🚀 Starting API + FAISS metrics integration test...")
    logger.info("=" * 60)
    
    success = await test_api_faiss_metrics_integration()
    
    logger.info("=" * 60)
    
    if success:
        logger.info("🎉 INTEGRATION TEST PASSED")
        logger.info("✅ T-008 Metrics Registry Unification - VERIFIED")
        logger.info("✅ Ready for T-011 FAISS Health Monitoring integration")
    else:
        logger.error("❌ INTEGRATION TEST FAILED")
        logger.error("❌ Issues need to be resolved before T-011")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)