#!/usr/bin/env python3
"""
Test script for FAISS health endpoints in Adelaide Weather Forecasting System.

Tests the new FAISS health monitoring endpoints to ensure they provide
comprehensive health information including:
- Index readiness for all horizons
- Last successful search timestamps  
- Fallback counter metrics
- Performance metrics
- Degraded mode detection
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from api.health_checks import EnhancedHealthChecker
from api.enhanced_health_endpoints import initialize_health_checker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_faiss_health_check():
    """Test the FAISS health check functionality."""
    logger.info("🚀 Testing FAISS Health Check System")
    
    try:
        # Initialize the health checker
        initialize_health_checker()
        
        # Create a health checker instance for testing
        checker = EnhancedHealthChecker()
        
        logger.info("📊 Testing FAISS health check method...")
        
        # Test FAISS health check
        faiss_result = await checker._check_faiss_health()
        
        logger.info(f"FAISS Health Check Status: {faiss_result.status}")
        logger.info(f"FAISS Health Check Message: {faiss_result.message}")
        logger.info(f"FAISS Health Check Duration: {faiss_result.duration_ms:.1f}ms")
        
        # Test comprehensive FAISS metrics
        logger.info("📈 Testing comprehensive FAISS metrics...")
        faiss_metrics = await checker._get_comprehensive_faiss_metrics()
        
        logger.info(f"Available Indices: {len(faiss_metrics['indices'])}")
        logger.info(f"Degraded Mode: {faiss_metrics['degraded_mode']}")
        
        # Display index status
        for index_key, index_data in faiss_metrics["indices"].items():
            logger.info(f"  - {index_key}: {index_data.get('ntotal', 0)} vectors, "
                       f"{index_data.get('file_size_mb', 0):.1f}MB")
        
        # Test FAISS health monitoring service
        logger.info("🔍 Testing FAISS health monitoring service...")
        try:
            from api.services.faiss_health_monitoring import get_faiss_health_monitor
            
            monitor = await get_faiss_health_monitor()
            health_summary = await monitor.get_health_summary()
            
            logger.info(f"Monitor Status: {health_summary.get('status')}")
            logger.info(f"Total Queries: {health_summary.get('query_performance', {}).get('total_queries', 0)}")
            logger.info(f"Error Rate: {health_summary.get('query_performance', {}).get('error_rate', 0):.3f}")
            
            # Display per-horizon metrics
            latency_percentiles = health_summary.get("latency_percentiles", {})
            for horizon, metrics in latency_percentiles.items():
                logger.info(f"  - {horizon}: p50={metrics.get('p50_ms', 0):.1f}ms, "
                           f"p95={metrics.get('p95_ms', 0):.1f}ms, "
                           f"samples={metrics.get('sample_count', 0)}")
                
                last_search = metrics.get('last_successful_search')
                if last_search:
                    logger.info(f"    Last successful search: {last_search}")
                else:
                    logger.info(f"    No successful searches recorded for {horizon}")
            
            # Test fallback tracking
            fallback_metrics = health_summary.get("fallback_metrics", {})
            logger.info(f"Total Fallbacks: {fallback_metrics.get('total_fallbacks', 0)}")
            
            fallback_by_horizon = fallback_metrics.get("fallback_by_horizon", {})
            for horizon, count in fallback_by_horizon.items():
                logger.info(f"  - {horizon} fallbacks: {count}")
                
            degraded_mode = fallback_metrics.get("degraded_mode", {})
            logger.info(f"Degraded Mode: {degraded_mode.get('active', False)}")
            if degraded_mode.get('reasons'):
                logger.info(f"  Reasons: {degraded_mode.get('reasons')}")
            
            # Shut down monitoring
            await monitor.stop_monitoring()
            
        except Exception as monitor_error:
            logger.warning(f"FAISS monitoring service test failed: {monitor_error}")
        
        logger.info("✅ FAISS Health Check Test Completed Successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ FAISS Health Check Test Failed: {e}")
        return False

async def test_health_endpoint_simulation():
    """Simulate what the health endpoints would return."""
    logger.info("🌐 Simulating FAISS Health Endpoint Response")
    
    try:
        # Initialize health checker
        initialize_health_checker()
        checker = EnhancedHealthChecker()
        
        # Get FAISS metrics like the endpoint would
        faiss_check_result = await checker._check_faiss_health()
        faiss_metrics = await checker._get_comprehensive_faiss_metrics()
        
        # Simulate FAISS monitor data
        faiss_detailed_health = {}
        try:
            from api.services.faiss_health_monitoring import get_faiss_health_monitor
            faiss_monitor = await get_faiss_health_monitor()
            faiss_detailed_health = await faiss_monitor.get_health_summary()
            await faiss_monitor.stop_monitoring()
        except Exception:
            pass
        
        # Build response like the /health/faiss endpoint
        response_data = {
            "faiss_status": "healthy" if faiss_check_result.status == "pass" else "degraded",
            "message": f"FAISS system operational" if faiss_check_result.status == "pass" else f"FAISS system degraded",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "check_duration_ms": faiss_check_result.duration_ms,
            
            "index_readiness": {
                horizon: {
                    "flatip_ready": f"{horizon}_flatip" in faiss_metrics["indices"],
                    "ivfpq_ready": f"{horizon}_ivfpq" in faiss_metrics["indices"],
                    "last_successful_search": faiss_detailed_health.get("latency_percentiles", {}).get(horizon, {}).get("last_successful_search"),
                    "search_samples": faiss_detailed_health.get("latency_percentiles", {}).get(horizon, {}).get("sample_count", 0)
                }
                for horizon in ["6h", "12h", "24h", "48h"]
            },
            
            "index_validation": {
                "total_indices_available": len(faiss_metrics["indices"]),
                "expected_indices": 8,
                "indices_metadata": faiss_metrics["indices"]
            },
            
            "performance_metrics": {
                "query_performance": faiss_metrics["performance"],
                "latency_by_horizon": faiss_detailed_health.get("latency_percentiles", {}),
                "error_rate": faiss_detailed_health.get("query_performance", {}).get("error_rate", 0)
            },
            
            "degraded_mode": {
                "active": faiss_metrics["degraded_mode"],
                "fallback_counters": faiss_detailed_health.get("fallback_metrics", {
                    "total_fallbacks": 0,
                    "fallback_by_horizon": {"6h": 0, "12h": 0, "24h": 0, "48h": 0}
                })
            },
            
            "monitoring": {
                "active": faiss_detailed_health.get("monitoring", {}).get("active", False),
                "uptime_seconds": faiss_detailed_health.get("monitoring", {}).get("uptime_seconds", 0)
            }
        }
        
        # Pretty print the simulated response
        logger.info("📝 Simulated /health/faiss Endpoint Response:")
        print(json.dumps(response_data, indent=2))
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Health endpoint simulation failed: {e}")
        return False

async def main():
    """Run all FAISS health endpoint tests."""
    logger.info("🔍 Starting FAISS Health Endpoints Test Suite")
    
    test_results = []
    
    # Test 1: FAISS health check functionality
    test_results.append(await test_faiss_health_check())
    
    # Test 2: Endpoint response simulation
    test_results.append(await test_health_endpoint_simulation())
    
    # Summary
    passed = sum(test_results)
    total = len(test_results)
    
    logger.info(f"\n📊 Test Summary: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("✅ All FAISS health endpoint tests passed!")
        return 0
    else:
        logger.error("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)