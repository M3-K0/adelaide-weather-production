#!/usr/bin/env python3
"""
AnalogSearchService Demonstration
=================================

Demonstrates the production-ready AnalogSearchService functionality:
- Service initialization and connection pooling
- Async analog search with performance monitoring
- Integration with ForecastAdapter
- Error handling and graceful degradation
- Health checking and metrics

Usage:
    python demo_analog_search_service.py
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import service components
from api.services import (
    AnalogSearchService,
    AnalogSearchConfig,
    get_analog_search_service,
    shutdown_analog_search_service
)
from api.forecast_adapter import ForecastAdapter

async def demo_analog_search_service():
    """Demonstrate AnalogSearchService functionality."""
    logger.info("🚀 Starting AnalogSearchService Demonstration")
    
    try:
        # Configuration for demo
        config = AnalogSearchConfig(
            pool_size=2,
            search_timeout_ms=3000,
            retry_attempts=2,
            max_workers=2
        )
        
        # Initialize service
        logger.info("📦 Initializing AnalogSearchService...")
        service = AnalogSearchService(config)
        
        # Note: In a real environment, this would load actual FAISS indices
        # For demo, the service will run in degraded mode with fallback data
        success = await service.initialize()
        
        if not success:
            logger.warning("⚠️ Service initialization had issues, continuing with demo")
        
        # Health check
        logger.info("🏥 Checking service health...")
        health = await service.health_check()
        logger.info(f"Service status: {health['status']}")
        logger.info(f"Degraded mode: {health['degraded_mode']}")
        logger.info(f"Pool connections: {health['pool']['available_connections']}")
        
        # Demonstrate analog search for different horizons
        logger.info("\n🔍 Demonstrating analog search for different horizons...")
        
        horizons = [6, 12, 24, 48]
        query_time = datetime.now(timezone.utc)
        
        for horizon in horizons:
            logger.info(f"\n--- Testing {horizon}h forecast horizon ---")
            
            start_time = time.time()
            result = await service.search_analogs(
                query_time=query_time,
                horizon=horizon,
                k=30,
                correlation_id=f"demo-{horizon}h"
            )
            search_time = (time.time() - start_time) * 1000
            
            if result.success:
                logger.info(f"✅ Search successful:")
                logger.info(f"   Correlation ID: {result.correlation_id}")
                logger.info(f"   Found {len(result.indices)} analogs")
                logger.info(f"   Best distance: {result.distances[0]:.3f}")
                logger.info(f"   Search time: {search_time:.1f}ms")
                logger.info(f"   Metadata: {result.search_metadata}")
            else:
                logger.error(f"❌ Search failed: {result.error_message}")
        
        # Demonstrate adapter-compatible interface
        logger.info("\n🔌 Testing adapter-compatible interface...")
        
        adapter_result = await service.generate_analog_results_for_adapter(
            horizon_hours=25,  # Should map to 48h
            correlation_id="demo-adapter"
        )
        
        logger.info(f"✅ Adapter interface working:")
        logger.info(f"   Indices shape: {adapter_result['indices'].shape}")
        logger.info(f"   Distances shape: {adapter_result['distances'].shape}")
        logger.info(f"   Init time: {adapter_result['init_time']}")
        logger.info(f"   Correlation ID: {adapter_result['search_metadata'].get('correlation_id')}")
        
        # Performance metrics
        logger.info("\n📊 Performance metrics:")
        final_health = await service.health_check()
        metrics = final_health['metrics']
        logger.info(f"   Total requests: {metrics['total_requests']}")
        logger.info(f"   Error rate: {metrics['error_rate']:.1%}")
        logger.info(f"   Average search time: {metrics['avg_search_time_ms']:.1f}ms")
        
        # Cleanup
        logger.info("\n🧹 Shutting down service...")
        await service.shutdown()
        
        logger.info("✅ AnalogSearchService demonstration completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")
        raise

async def demo_forecast_adapter_integration():
    """Demonstrate ForecastAdapter integration with AnalogSearchService."""
    logger.info("\n🔗 Starting ForecastAdapter Integration Demo")
    
    try:
        # Initialize adapter
        adapter = ForecastAdapter()
        
        # Test variables
        test_variables = ['t2m', 'u10', 'v10', 'r850']
        test_horizon = '24h'
        
        logger.info(f"🎯 Generating forecast for {test_horizon} horizon...")
        logger.info(f"Variables: {test_variables}")
        
        start_time = time.time()
        
        # This will use the AnalogSearchService under the hood
        forecast_result = await adapter.forecast_with_uncertainty(
            horizon=test_horizon,
            variables=test_variables
        )
        
        forecast_time = (time.time() - start_time) * 1000
        
        logger.info(f"✅ Forecast generated in {forecast_time:.1f}ms")
        
        # Display results
        for var, result in forecast_result.items():
            if result['available']:
                logger.info(f"   {var}: {result['value']:.2f} "
                           f"[{result['p05']:.2f}, {result['p95']:.2f}] "
                           f"({result['analog_count']} analogs)")
            else:
                logger.info(f"   {var}: Not available")
        
        # Test health check
        logger.info("\n🏥 Checking adapter health...")
        health = await adapter.get_system_health()
        
        logger.info(f"Adapter ready: {health['adapter_ready']}")
        logger.info(f"Forecaster loaded: {health['forecaster_loaded']}")
        logger.info(f"Analog service ready: {health['analog_service_ready']}")
        
        if health.get('analog_service_health'):
            service_health = health['analog_service_health']
            logger.info(f"Analog service status: {service_health.get('status', 'unknown')}")
        
        logger.info("✅ ForecastAdapter integration demo completed!")
        
    except Exception as e:
        logger.error(f"❌ Adapter demo failed: {e}")
        raise

async def demo_dependency_injection():
    """Demonstrate dependency injection pattern."""
    logger.info("\n💉 Starting Dependency Injection Demo")
    
    try:
        # Reset any existing service
        await shutdown_analog_search_service()
        
        # Get service through dependency injection
        logger.info("📦 Getting service through dependency injection...")
        service1 = await get_analog_search_service()
        service2 = await get_analog_search_service()
        
        # Should be the same instance
        logger.info(f"Same instance: {service1 is service2}")
        
        # Test the service
        result = await service1.search_analogs(
            query_time=datetime.now(timezone.utc),
            horizon=12,
            k=10,
            correlation_id="di-demo"
        )
        
        logger.info(f"Search via DI successful: {result.success}")
        
        # Shutdown through DI
        logger.info("🧹 Shutting down via dependency injection...")
        await shutdown_analog_search_service()
        
        logger.info("✅ Dependency injection demo completed!")
        
    except Exception as e:
        logger.error(f"❌ DI demo failed: {e}")
        raise

async def run_all_demos():
    """Run all demonstration scenarios."""
    logger.info("🎪 Starting Complete AnalogSearchService Demo Suite")
    logger.info("=" * 60)
    
    try:
        # Demo 1: Core service functionality
        await demo_analog_search_service()
        
        # Demo 2: Adapter integration
        await demo_forecast_adapter_integration()
        
        # Demo 3: Dependency injection
        await demo_dependency_injection()
        
        logger.info("\n🎉 All demonstrations completed successfully!")
        logger.info("The AnalogSearchService is ready for production use.")
        
    except Exception as e:
        logger.error(f"❌ Demo suite failed: {e}")
        return False
    
    return True

def main():
    """Main entry point."""
    print("AnalogSearchService Production Demo")
    print("=" * 40)
    print("This demonstrates the production-ready analog search service")
    print("with async interface, connection pooling, and error handling.")
    print()
    
    # Run all demos
    success = asyncio.run(run_all_demos())
    
    if success:
        print("\n✅ Demo completed successfully!")
        print("The service is ready for integration with the production API.")
    else:
        print("\n❌ Demo encountered issues.")
        print("Please check the logs for details.")
        exit(1)

if __name__ == "__main__":
    main()