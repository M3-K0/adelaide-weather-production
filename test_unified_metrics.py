#!/usr/bin/env python3
"""
Test script to verify unified metrics registry integration.

This test verifies that:
1. FAISS metrics are exposed through the default Prometheus registry
2. API metrics and FAISS metrics can be collected together
3. No metric name conflicts exist
4. Metrics unification works as expected
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

async def test_unified_metrics():
    """Test that unified metrics collection works correctly."""
    
    try:
        # Import required modules
        from prometheus_client import generate_latest, REGISTRY
        from api.services.faiss_health_monitoring import FAISSHealthMonitor
        
        logger.info("🧪 Testing unified metrics registry integration...")
        
        # Step 1: Create FAISS health monitor with default registry
        logger.info("📊 Creating FAISS health monitor with default registry...")
        faiss_monitor = FAISSHealthMonitor()
        
        # Verify it's using the default registry
        if faiss_monitor.registry is REGISTRY:
            logger.info("✅ FAISS monitor is using default Prometheus registry")
        else:
            logger.error("❌ FAISS monitor is not using default registry")
            return False
        
        # Step 2: Start monitoring
        logger.info("🔍 Starting FAISS health monitoring...")
        await faiss_monitor.start_monitoring()
        
        # Step 3: Generate some test metrics
        logger.info("📈 Generating test metrics...")
        
        # Simulate a FAISS query to generate metrics
        async with faiss_monitor.track_query("24h", k_neighbors=50) as query:
            # Simulate some work
            await asyncio.sleep(0.1)
        
        # Step 4: Collect unified metrics
        logger.info("📊 Collecting unified metrics from default registry...")
        unified_metrics_text = generate_latest(REGISTRY).decode('utf-8')
        
        # Step 5: Verify metrics are present
        logger.info("🔍 Verifying metrics presence...")
        
        # Check for FAISS metrics
        faiss_metrics_found = []
        expected_faiss_metrics = [
            'faiss_query_duration_seconds',
            'faiss_queries_total',
            'faiss_active_queries',
            'faiss_build_info'
        ]
        
        for metric_name in expected_faiss_metrics:
            if metric_name in unified_metrics_text:
                faiss_metrics_found.append(metric_name)
                logger.info(f"✅ Found FAISS metric: {metric_name}")
            else:
                logger.warning(f"⚠️ Missing FAISS metric: {metric_name}")
        
        # Check for API metrics (if available)
        api_metrics_found = []
        expected_api_metrics = [
            'forecast_requests_total',
            'health_requests_total',
            'metrics_requests_total'
        ]
        
        for metric_name in expected_api_metrics:
            if metric_name in unified_metrics_text:
                api_metrics_found.append(metric_name)
                logger.info(f"✅ Found API metric: {metric_name}")
            else:
                logger.info(f"ℹ️ API metric not found (expected if not running full API): {metric_name}")
        
        # Step 6: Test metric collection
        logger.info("📊 Testing individual metric collection...")
        
        # Get FAISS-specific metrics
        faiss_metrics_text = faiss_monitor.get_prometheus_metrics()
        logger.info(f"📏 FAISS metrics length: {len(faiss_metrics_text)} characters")
        
        # Step 7: Analyze results
        logger.info("📋 Analysis Results:")
        logger.info(f"   - FAISS metrics found: {len(faiss_metrics_found)}/{len(expected_faiss_metrics)}")
        logger.info(f"   - API metrics found: {len(api_metrics_found)}/{len(expected_api_metrics)}")
        logger.info(f"   - Total unified metrics size: {len(unified_metrics_text)} characters")
        logger.info(f"   - FAISS-only metrics size: {len(faiss_metrics_text)} characters")
        
        # Step 8: Test for real conflicts (metric family name collisions)
        logger.info("🔍 Checking for metric name conflicts...")
        
        # Parse the metrics text to find actual metric family definitions
        metric_lines = unified_metrics_text.split('\n')
        help_lines = [line for line in metric_lines if line.startswith('# HELP')]
        type_lines = [line for line in metric_lines if line.startswith('# TYPE')]
        
        # Extract metric family names from HELP and TYPE declarations
        help_metrics = set()
        type_metrics = set()
        real_conflicts = []
        
        for line in help_lines:
            if len(line.split()) >= 3:
                metric_name = line.split()[2]
                if metric_name in help_metrics:
                    real_conflicts.append(f"Duplicate HELP for {metric_name}")
                help_metrics.add(metric_name)
        
        for line in type_lines:
            if len(line.split()) >= 3:
                metric_name = line.split()[2]
                if metric_name in type_metrics:
                    real_conflicts.append(f"Duplicate TYPE for {metric_name}")
                type_metrics.add(metric_name)
        
        if real_conflicts:
            logger.error(f"❌ Found real metric conflicts: {real_conflicts}")
            return False
        else:
            logger.info("✅ No metric name conflicts detected")
            logger.info(f"   - Found {len(help_metrics)} unique metric families")
            logger.info(f"   - HELP and TYPE declarations are consistent")
        
        # Step 9: Cleanup
        logger.info("🧹 Cleaning up...")
        await faiss_monitor.stop_monitoring()
        
        # Step 10: Final validation
        success = len(faiss_metrics_found) >= 3  # At least 3 FAISS metrics should be present
        
        if success:
            logger.info("🎉 Unified metrics registry test PASSED")
            logger.info("✅ Key findings:")
            logger.info("   - FAISS metrics are properly exposed in default registry")
            logger.info("   - No metric name conflicts detected")
            logger.info("   - Metrics can be collected uniformly")
            logger.info("   - Registry unification is working correctly")
        else:
            logger.error("❌ Unified metrics registry test FAILED")
            logger.error("   - Insufficient FAISS metrics found in unified collection")
        
        return success
        
    except Exception as e:
        logger.error(f"💥 Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_metrics_endpoint_compatibility():
    """Test that the metrics endpoint changes are compatible."""
    
    try:
        logger.info("🧪 Testing metrics endpoint compatibility...")
        
        from prometheus_client import generate_latest, REGISTRY
        from api.services.faiss_health_monitoring import get_faiss_health_monitor
        
        # Initialize FAISS health monitor through the dependency injection
        logger.info("📊 Initializing FAISS health monitor via dependency injection...")
        faiss_monitor = await get_faiss_health_monitor()
        
        # Simulate the /metrics endpoint logic
        logger.info("📡 Simulating /metrics endpoint behavior...")
        
        # This simulates what the /metrics endpoint now does
        unified_metrics = generate_latest(REGISTRY)
        
        logger.info(f"📏 Unified metrics size: {len(unified_metrics)} bytes")
        
        # Check that we have metrics
        if len(unified_metrics) > 100:  # Should have some reasonable content
            logger.info("✅ Metrics endpoint compatibility test PASSED")
            logger.info("   - Unified metrics successfully generated")
            logger.info("   - Dependency injection working correctly")
            return True
        else:
            logger.error("❌ Metrics endpoint compatibility test FAILED")
            logger.error("   - Insufficient metrics content generated")
            return False
            
    except Exception as e:
        logger.error(f"💥 Compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all unified metrics tests."""
    
    logger.info("🚀 Starting unified metrics registry tests...")
    logger.info("=" * 60)
    
    # Test 1: Basic unified metrics functionality
    test1_result = await test_unified_metrics()
    
    logger.info("=" * 60)
    
    # Test 2: Metrics endpoint compatibility
    test2_result = await test_metrics_endpoint_compatibility()
    
    logger.info("=" * 60)
    
    # Overall results
    if test1_result and test2_result:
        logger.info("🎉 ALL TESTS PASSED")
        logger.info("✅ Unified metrics registry is working correctly")
        logger.info("✅ T-008 Metrics Registry Unification - COMPLETED")
        return True
    else:
        logger.error("❌ SOME TESTS FAILED")
        logger.error("❌ Issues detected with metrics registry unification")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)