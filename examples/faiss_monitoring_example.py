#!/usr/bin/env python3
"""
FAISS Health Monitoring Usage Example
====================================

Demonstrates how to use the FAISSHealthMonitor for real-time
FAISS performance monitoring in the Adelaide Weather Forecasting System.

This example shows:
1. Basic monitoring setup
2. Query tracking during FAISS operations
3. Health status monitoring
4. Prometheus metrics collection
5. Production usage patterns

Author: Monitoring & Observability Engineer
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from api.services.faiss_health_monitoring import FAISSHealthMonitor

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def basic_monitoring_example():
    """Example 1: Basic monitoring setup and usage."""
    logger.info("📊 Example 1: Basic FAISS Monitoring Setup")
    
    # Initialize and start monitoring
    monitor = FAISSHealthMonitor()
    await monitor.start_monitoring()
    
    try:
        # Simulate some FAISS queries
        for i in range(10):
            horizon = f"{[6, 12, 24, 48][i % 4]}h"
            
            # Track a FAISS query using async context manager
            async with monitor.track_query(
                horizon=horizon,
                k_neighbors=50,
                index_type="ivfpq"
            ) as query:
                # This is where your actual FAISS search would happen
                # For example: results = faiss_index.search(query_vector, k)
                await asyncio.sleep(0.002)  # Simulate 2ms search time
                
                logger.info(f"   Tracked {horizon} query (ID: {query.query_id})")
        
        # Get health summary
        health = await monitor.get_health_summary()
        logger.info(f"✅ Health Status: {health['status']}")
        logger.info(f"   Total Queries: {health['query_performance']['total_queries']}")
        logger.info(f"   Avg Latency: {health['query_performance']['avg_latency_ms']:.1f}ms")
        
    finally:
        await monitor.stop_monitoring()

async def production_integration_example():
    """Example 2: Production integration pattern."""
    logger.info("🏭 Example 2: Production Integration Pattern")
    
    # This simulates how the monitoring is integrated in main.py
    async with FAISSHealthMonitor() as monitor:
        
        def simulate_forecast_endpoint(horizon: str, variables: list):
            """Simulate the forecast endpoint logic."""
            return asyncio.create_task(_perform_forecast(monitor, horizon, variables))
        
        # Simulate multiple concurrent forecast requests
        tasks = [
            simulate_forecast_endpoint("24h", ["t2m", "u10", "v10"]),
            simulate_forecast_endpoint("12h", ["t2m", "msl"]),
            simulate_forecast_endpoint("48h", ["t2m", "u10", "v10", "q850"]),
        ]
        
        # Wait for all forecasts to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check monitoring results
        health = await monitor.get_health_summary()
        logger.info(f"✅ Processed {len(tasks)} concurrent forecasts")
        logger.info(f"   FAISS Status: {health['status']}")
        logger.info(f"   Total Queries: {health['query_performance']['total_queries']}")
        
        # Show per-horizon latencies
        for horizon, stats in health['latency_percentiles'].items():
            if stats['sample_count'] > 0:
                logger.info(f"   {horizon}: {stats['p50_ms']:.1f}ms (p50), {stats['p95_ms']:.1f}ms (p95)")

async def _perform_forecast(monitor: FAISSHealthMonitor, horizon: str, variables: list):
    """Simulate forecast computation with FAISS monitoring."""
    
    # Track the FAISS query that happens during forecast computation
    async with monitor.track_query(horizon, k_neighbors=50) as query:
        # Simulate the steps in analog forecasting:
        
        # 1. Generate embedding (this would be real in production)
        await asyncio.sleep(0.001)  # 1ms for embedding
        
        # 2. FAISS search (this is what we're monitoring)
        await asyncio.sleep(0.003)  # 3ms for FAISS search
        
        # 3. Outcome retrieval and ensemble generation
        await asyncio.sleep(0.002)  # 2ms for outcomes
        
        return {
            "horizon": horizon,
            "variables": {var: {"value": 25.0, "confidence": 0.8} for var in variables},
            "faiss_query_id": query.query_id
        }

async def monitoring_dashboard_example():
    """Example 3: Monitoring dashboard data collection."""
    logger.info("📈 Example 3: Monitoring Dashboard Data")
    
    monitor = FAISSHealthMonitor()
    await monitor.start_monitoring()
    
    try:
        # Generate some varied load to show different monitoring scenarios
        
        # Fast queries
        for i in range(5):
            async with monitor.track_query("6h", 20, "flatip"):
                await asyncio.sleep(0.001)  # 1ms - very fast
        
        # Normal queries  
        for i in range(10):
            async with monitor.track_query("24h", 50, "ivfpq"):
                await asyncio.sleep(0.005)  # 5ms - normal
        
        # Slow queries
        for i in range(3):
            async with monitor.track_query("48h", 100, "ivfpq"):
                await asyncio.sleep(0.020)  # 20ms - slower
        
        # Simulate an error
        try:
            async with monitor.track_query("24h", 50) as query:
                await asyncio.sleep(0.003)
                raise RuntimeError("Simulated FAISS error")
        except RuntimeError:
            pass  # Expected
        
        # Get comprehensive health data for dashboard
        health = await monitor.get_health_summary()
        
        logger.info("📊 Dashboard Metrics:")
        logger.info(f"   Overall Status: {health['status']}")
        logger.info(f"   Total Queries: {health['query_performance']['total_queries']}")
        logger.info(f"   Error Rate: {health['query_performance']['error_rate']:.1%}")
        logger.info(f"   System Memory: {health['system']['memory_usage_mb']:.1f} MB")
        
        # Show per-horizon performance
        logger.info("   Per-Horizon Performance:")
        for horizon, stats in health['latency_percentiles'].items():
            if stats['sample_count'] > 0:
                logger.info(f"     {horizon}: {stats['sample_count']} queries, "
                          f"{stats['p50_ms']:.1f}ms p50, {stats['p95_ms']:.1f}ms p95")
        
        # Show Prometheus metrics sample
        metrics = monitor.get_prometheus_metrics()
        logger.info(f"   Prometheus Metrics: {len(metrics)} characters")
        
        # Show sample metrics
        for line in metrics.split('\n'):
            if 'faiss_queries_total' in line and not line.startswith('#'):
                logger.info(f"     {line}")
                break
        
    finally:
        await monitor.stop_monitoring()

async def error_handling_example():
    """Example 4: Error handling and resilience."""
    logger.info("🛡️ Example 4: Error Handling and Resilience")
    
    monitor = FAISSHealthMonitor()
    await monitor.start_monitoring()
    
    try:
        # Test various error scenarios
        
        # 1. Normal successful query
        async with monitor.track_query("24h", 50) as query:
            await asyncio.sleep(0.005)
            logger.info(f"   ✅ Normal query: {query.query_id}")
        
        # 2. Query that fails
        try:
            async with monitor.track_query("24h", 50) as query:
                await asyncio.sleep(0.003)
                raise ConnectionError("FAISS index unavailable")
        except ConnectionError as e:
            logger.info(f"   ❌ Failed query handled: {e}")
        
        # 3. Query with timeout simulation
        try:
            async with monitor.track_query("48h", 100) as query:
                await asyncio.sleep(0.1)  # Very slow query
                raise TimeoutError("Query timeout")
        except TimeoutError as e:
            logger.info(f"   ⏱️ Timeout query handled: {e}")
        
        # Check that monitoring continues to work after errors
        health = await monitor.get_health_summary()
        perf = health['query_performance']
        
        logger.info(f"✅ Monitoring resilient to errors:")
        logger.info(f"   Total queries: {perf['total_queries']}")
        logger.info(f"   Error rate: {perf['error_rate']:.1%}")
        logger.info(f"   System status: {health['status']}")
        
    finally:
        await monitor.stop_monitoring()

async def main():
    """Run all monitoring examples."""
    logger.info("🚀 FAISS Health Monitoring Examples")
    logger.info("=" * 50)
    
    examples = [
        ("Basic Monitoring", basic_monitoring_example),
        ("Production Integration", production_integration_example), 
        ("Dashboard Data Collection", monitoring_dashboard_example),
        ("Error Handling", error_handling_example)
    ]
    
    for name, example_func in examples:
        logger.info(f"\n{name}")
        logger.info("-" * len(name))
        
        try:
            await example_func()
            logger.info(f"✅ {name} completed successfully")
        except Exception as e:
            logger.error(f"❌ {name} failed: {e}")
            import traceback
            traceback.print_exc()
    
    logger.info("\n" + "=" * 50)
    logger.info("🎉 FAISS Health Monitoring Examples Complete!")
    logger.info("\nTo use in production:")
    logger.info("1. Import: from api.services.faiss_health_monitoring import FAISSHealthMonitor")
    logger.info("2. Initialize: monitor = await get_faiss_health_monitor()")
    logger.info("3. Track queries: async with monitor.track_query(...) as query:")
    logger.info("4. Monitor health: health = await monitor.get_health_summary()")
    logger.info("5. Get metrics: metrics = monitor.get_prometheus_metrics()")

if __name__ == "__main__":
    asyncio.run(main())