#!/usr/bin/env python3
"""
Resource Guardrails Demonstration
==================================

Demonstrates the resource guardrails system including memory profiling,
GPU/CPU switching, lazy loading, and fail-fast behavior.

Run this script to see the resource management capabilities in action.

Usage:
    python demo_resource_guardrails.py
    
Environment Variables (optional):
    FAISS_MEMORY_LIMIT=2048          # Memory limit in MB
    FAISS_GPU_ENABLED=auto           # GPU enablement (true/false/auto)
    FAISS_LAZY_LOAD=true             # Enable lazy loading
    FAISS_FAIL_FAST=true             # Enable fail-fast behavior
    FAISS_MEMORY_PROFILING=true      # Enable memory profiling
"""

import os
import asyncio
import logging
import sys
import time
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.append(str(Path(__file__).parent))

async def demo_resource_monitor():
    """Demonstrate resource monitoring capabilities."""
    logger.info("🔍 Demonstrating Resource Monitor")
    logger.info("=" * 50)
    
    from core.resource_monitor import get_resource_monitor, profile_memory
    
    # Get resource monitor
    monitor = get_resource_monitor()
    
    # Show current resource metrics
    metrics = monitor.get_current_metrics()
    logger.info(f"Current CPU usage: {metrics.cpu_percent:.1f}%")
    logger.info(f"Memory usage: {metrics.memory_used_percent:.1f}% ({metrics.process_memory_mb:.1f}MB process)")
    logger.info(f"GPU available: {metrics.gpu_available}")
    if metrics.gpu_memory_mb:
        logger.info(f"GPU memory: {metrics.gpu_memory_mb:.0f}MB")
    
    # Demonstrate memory profiling
    logger.info("\n📊 Memory Profiling Demonstration")
    
    with profile_memory("demo_memory_allocation") as profiler:
        logger.info("Allocating memory for demonstration...")
        
        # Simulate memory allocation
        data = []
        for i in range(5):
            # Allocate 10MB chunks
            chunk = [0] * (10 * 1024 * 1024 // 8)  # 10MB of integers
            data.append(chunk)
            logger.info(f"Allocated chunk {i+1}/5 (~10MB)")
            await asyncio.sleep(0.5)
        
        logger.info("Peak memory usage during allocation...")
        
        # Clean up
        del data
        logger.info("Memory cleaned up")
    
    # Show profiling results
    peak_usage = profiler.get_peak_usage()
    growth_rate = profiler.get_memory_growth_rate()
    
    if peak_usage:
        logger.info(f"Peak memory usage: {peak_usage.process_rss_mb:.1f}MB")
    logger.info(f"Memory growth rate: {growth_rate:.2f}MB/s")
    
    # Check memory budget
    budget_check = monitor.check_memory_budget()
    logger.info(f"Memory budget status: {budget_check.get('severity', 'normal')}")
    
    return True

async def demo_device_manager():
    """Demonstrate device detection and switching."""
    logger.info("\n🖥️ Demonstrating Device Manager")
    logger.info("=" * 50)
    
    from core.device_manager import get_device_manager
    
    # Get device manager
    device_manager = get_device_manager()
    
    # Show device information
    device_info = device_manager.get_device_info()
    
    logger.info("Device Detection Results:")
    selected_device = device_info['selected_device']
    if selected_device:
        logger.info(f"Selected device: {selected_device['device_type']}")
        logger.info(f"Selection reason: {selected_device['selection_reason']}")
        logger.info(f"Fallback applied: {selected_device['fallback_applied']}")
    
    # Show GPU capabilities if any
    gpu_caps = device_info['gpu_capabilities']
    if gpu_caps:
        logger.info(f"\nGPU Capabilities:")
        for i, gpu in enumerate(gpu_caps):
            logger.info(f"  GPU {i}: {gpu['memory_mb']:.0f}MB, CC {gpu['compute_capability']}")
    else:
        logger.info("No GPU devices detected")
    
    # Show CPU capabilities
    cpu_caps = device_info['cpu_capabilities']
    if cpu_caps:
        logger.info(f"\nCPU Capabilities:")
        logger.info(f"  Cores: {cpu_caps['device_count']}")
        logger.info(f"  Performance score: {cpu_caps['performance_score']:.1f}")
    
    # Show FAISS GPU availability
    logger.info(f"\nFAISS GPU support: {device_info['faiss_gpu_available']}")
    
    # Show environment configuration
    env_config = device_info['environment_config']
    logger.info(f"\nEnvironment Configuration:")
    for key, value in env_config.items():
        logger.info(f"  {key}: {value}")
    
    # Validate device selection
    validation = device_manager.validate_device_selection()
    logger.info(f"\nDevice Validation:")
    logger.info(f"  Overall valid: {validation['overall_valid']}")
    if validation['issues']:
        logger.info(f"  Issues: {validation['issues']}")
    
    return True

async def demo_enhanced_analog_search():
    """Demonstrate enhanced analog search with resource guardrails."""
    logger.info("\n🔎 Demonstrating Enhanced Analog Search")
    logger.info("=" * 50)
    
    from api.services.enhanced_analog_search import EnhancedAnalogSearchService, ResourceConfig
    
    # Create configuration from environment
    config = ResourceConfig.from_environment()
    
    logger.info("Resource Configuration:")
    logger.info(f"  Memory limit: {config.memory_limit_mb}MB")
    logger.info(f"  Process limit: {config.process_memory_limit_mb}MB")
    logger.info(f"  Lazy loading: {config.lazy_loading}")
    logger.info(f"  GPU enabled: {config.gpu_enabled}")
    logger.info(f"  Fail fast: {config.fail_fast_on_budget}")
    logger.info(f"  Memory profiling: {config.enable_memory_profiling}")
    
    # Initialize service
    service = EnhancedAnalogSearchService(config)
    
    try:
        # Initialize service
        logger.info("\nInitializing Enhanced Analog Search Service...")
        success = await service.initialize()
        
        if not success:
            logger.error("Service initialization failed")
            return False
        
        # Perform test search
        logger.info("\nPerforming test analog search...")
        
        result = await service.search_analogs_enhanced(
            query_time="2023-07-15T12:00:00",
            horizon=24,
            k=50,
            correlation_id="demo_search",
            enable_profiling=True
        )
        
        if result.success:
            logger.info(f"Search successful:")
            logger.info(f"  Found {len(result.indices)} analogs")
            logger.info(f"  Search time: {result.performance_metrics.get('total_time_ms', 0):.1f}ms")
            logger.info(f"  Method: {result.performance_metrics.get('method', 'unknown')}")
            logger.info(f"  Device: {result.performance_metrics.get('device_type', 'unknown')}")
            
            # Show resource metrics
            resource_metrics = result.resource_metrics
            logger.info(f"  Memory usage: {resource_metrics.get('memory_used_percent', 0):.1f}%")
            logger.info(f"  Process memory: {resource_metrics.get('process_memory_mb', 0):.1f}MB")
            
            if result.resource_metrics.get('profiling_enabled'):
                logger.info(f"  Peak memory: {result.resource_metrics.get('peak_memory_mb', 0):.1f}MB")
                logger.info(f"  Growth rate: {result.resource_metrics.get('memory_growth_rate_mb_s', 0):.2f}MB/s")
        else:
            logger.error(f"Search failed: {result.error_message}")
        
        # Health check
        logger.info("\nPerforming health check...")
        health = await service.health_check_enhanced()
        
        logger.info(f"Service status: {health['status']}")
        logger.info(f"Total requests: {health['performance_metrics']['total_requests']}")
        logger.info(f"Error rate: {health['performance_metrics']['error_rate']:.1%}")
        
        # Show cache stats
        cache_stats = health['cache_stats']
        logger.info(f"Index cache: {cache_stats['cache_size']}/{cache_stats['max_cache_size']}")
        
        return True
        
    finally:
        # Shutdown service
        await service.shutdown()

async def demo_startup_validation():
    """Demonstrate startup validation with resource guardrails."""
    logger.info("\n✅ Demonstrating Startup Validation")
    logger.info("=" * 50)
    
    from core.startup_validation_system import ExpertValidatedStartupSystem
    
    # Create startup validator
    validator = ExpertValidatedStartupSystem()
    
    # Run only the resource guardrails validation
    logger.info("Running resource guardrails validation...")
    
    result = validator.validate_resource_guardrails_expert()
    
    logger.info(f"Validation result: {result.status}")
    logger.info(f"Message: {result.message}")
    logger.info(f"Expert threshold met: {result.expert_threshold_met}")
    
    # Show key metrics from validation
    metrics = result.metrics
    if 'device_info' in metrics:
        device_info = metrics['device_info']
        selected_device = device_info.get('selected_device', {})
        logger.info(f"Selected device: {selected_device.get('device_type', 'unknown')}")
    
    if 'current_metrics' in metrics:
        current_metrics = metrics['current_metrics']
        logger.info(f"Available memory: {current_metrics.get('memory_available_gb', 0):.1f}GB")
        logger.info(f"GPU available: {current_metrics.get('gpu_available', False)}")
    
    if 'environment_config' in metrics:
        env_config = metrics['environment_config']
        logger.info("Environment variables checked:")
        for key, value in env_config.items():
            logger.info(f"  {key}: {value}")
    
    return result.is_passing()

def demo_environment_setup():
    """Show environment variable setup for resource guardrails."""
    logger.info("\n⚙️ Environment Variable Configuration")
    logger.info("=" * 50)
    
    env_vars = {
        'FAISS_MEMORY_LIMIT': 'Memory limit in MB (default: 4096)',
        'FAISS_PROCESS_MEMORY_LIMIT': 'Process memory limit in MB (default: 2048)',
        'FAISS_GPU_ENABLED': 'Enable GPU usage (true/false/auto, default: auto)',
        'FAISS_FORCE_CPU': 'Force CPU usage (true/false, default: false)',
        'FAISS_GPU_DEVICE': 'Specific GPU device ID (default: auto)',
        'FAISS_GPU_MEMORY_FRACTION': 'GPU memory fraction to use (default: 0.8)',
        'FAISS_LAZY_LOAD': 'Enable lazy loading (true/false, default: false)',
        'FAISS_FAIL_FAST': 'Enable fail-fast behavior (true/false, default: true)',
        'FAISS_MEMORY_PROFILING': 'Enable memory profiling (true/false, default: true)',
        'FAISS_MAX_CONCURRENT': 'Max concurrent searches (default: 4)',
        'FAISS_INDEX_CACHE_SIZE': 'Index cache size (default: 2)'
    }
    
    logger.info("Available environment variables:")
    for var, description in env_vars.items():
        current_value = os.getenv(var, 'not set')
        logger.info(f"  {var}={current_value}")
        logger.info(f"    {description}")
    
    logger.info("\nExample configuration:")
    logger.info("export FAISS_MEMORY_LIMIT=2048")
    logger.info("export FAISS_GPU_ENABLED=auto")
    logger.info("export FAISS_LAZY_LOAD=true")
    logger.info("export FAISS_FAIL_FAST=true")

async def main():
    """Main demonstration function."""
    logger.info("🚀 Resource Guardrails Demonstration")
    logger.info("=" * 60)
    
    try:
        # Show environment setup
        demo_environment_setup()
        
        # Demonstrate resource monitoring
        success = await demo_resource_monitor()
        if not success:
            logger.error("Resource monitor demo failed")
            return 1
        
        # Demonstrate device management
        success = await demo_device_manager()
        if not success:
            logger.error("Device manager demo failed")
            return 1
        
        # Demonstrate startup validation
        success = await demo_startup_validation()
        if not success:
            logger.warning("Startup validation had issues but continuing...")
        
        # Demonstrate enhanced analog search
        try:
            success = await demo_enhanced_analog_search()
            if not success:
                logger.error("Enhanced analog search demo failed")
        except Exception as e:
            logger.warning(f"Enhanced analog search demo failed: {e}")
            logger.warning("This is expected if FAISS indices are not available")
        
        logger.info("\n🎉 Resource Guardrails Demonstration Complete!")
        logger.info("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)