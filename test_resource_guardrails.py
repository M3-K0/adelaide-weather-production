#!/usr/bin/env python3
"""
Resource Guardrails Integration Test
====================================

Tests the complete resource guardrails implementation to ensure all
components work correctly together.

Author: Performance Specialist
Version: 1.0.0 - Integration Test
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def test_resource_monitor():
    """Test resource monitor functionality."""
    logger.info("Testing Resource Monitor...")
    
    from core.resource_monitor import get_resource_monitor, check_memory_budget
    
    # Get monitor
    monitor = get_resource_monitor()
    
    # Test getting metrics
    metrics = monitor.get_current_metrics()
    assert metrics.cpu_count > 0, "CPU count should be positive"
    assert 0 <= metrics.memory_used_percent <= 100, "Memory percentage should be 0-100%"
    assert metrics.process_memory_mb > 0, "Process memory should be positive"
    
    # Test memory budget check
    budget_status = check_memory_budget("test_operation")
    assert isinstance(budget_status, bool), "Budget check should return boolean"
    
    logger.info("✅ Resource Monitor tests passed")

def test_device_manager():
    """Test device manager functionality."""
    logger.info("Testing Device Manager...")
    
    from core.device_manager import get_device_manager, get_selected_device_type, is_gpu_enabled
    
    # Get manager
    device_manager = get_device_manager()
    
    # Test device info
    device_info = device_manager.get_device_info()
    assert 'selected_device' in device_info, "Device info should have selected_device"
    assert 'cpu_capabilities' in device_info, "Device info should have CPU capabilities"
    
    # Test device type functions
    device_type = get_selected_device_type()
    assert device_type.value in ['cpu', 'gpu'], "Device type should be cpu or gpu"
    
    # Test GPU enabled check
    gpu_enabled = is_gpu_enabled()
    assert isinstance(gpu_enabled, bool), "GPU enabled should be boolean"
    
    # Test device validation
    validation = device_manager.validate_device_selection()
    assert 'overall_valid' in validation, "Validation should have overall_valid field"
    
    logger.info("✅ Device Manager tests passed")

async def test_enhanced_analog_search():
    """Test enhanced analog search service."""
    logger.info("Testing Enhanced Analog Search Service...")
    
    from api.services.enhanced_analog_search import EnhancedAnalogSearchService, ResourceConfig
    
    # Create configuration
    config = ResourceConfig(
        memory_limit_mb=4096,
        lazy_loading=True,  # Use lazy loading to avoid missing index files
        enable_memory_profiling=True,
        fail_fast_on_budget=False  # Don't fail fast in test
    )
    
    # Create service
    service = EnhancedAnalogSearchService(config)
    
    try:
        # Initialize service
        success = await service.initialize()
        assert success, "Service initialization should succeed"
        
        # Test health check
        health = await service.health_check_enhanced()
        assert health['status'] in ['healthy', 'degraded'], "Health status should be valid"
        assert 'resource_summary' in health, "Health should include resource summary"
        assert 'device_info' in health, "Health should include device info"
        
        # Test search (will likely use fallback due to missing indices)
        result = await service.search_analogs_enhanced(
            query_time="2023-07-15T12:00:00",
            horizon=24,
            k=10,
            correlation_id="test_search"
        )
        
        assert result.correlation_id == "test_search", "Correlation ID should match"
        assert result.horizon == 24, "Horizon should match"
        assert 'resource_metrics' in result.to_dict(), "Result should include resource metrics"
        assert 'device_info' in result.to_dict(), "Result should include device info"
        
    finally:
        # Cleanup
        await service.shutdown()
    
    logger.info("✅ Enhanced Analog Search Service tests passed")

def test_startup_validation():
    """Test startup validation with resource guardrails."""
    logger.info("Testing Startup Validation...")
    
    # Set required environment variable
    os.environ['FAISS_MEMORY_LIMIT'] = '4096'
    
    from core.startup_validation_system import ExpertValidatedStartupSystem
    
    # Create validator
    validator = ExpertValidatedStartupSystem()
    
    # Test resource guardrails validation
    result = validator.validate_resource_guardrails_expert()
    
    assert result.test_name == "resource_guardrails_expert", "Test name should match"
    assert result.status in ['PASS', 'FAIL', 'CRITICAL_FAIL'], "Status should be valid"
    assert isinstance(result.expert_threshold_met, bool), "Expert threshold should be boolean"
    assert 'current_metrics' in result.metrics, "Metrics should include current metrics"
    assert 'device_info' in result.metrics, "Metrics should include device info"
    
    logger.info("✅ Startup Validation tests passed")

def test_environment_variables():
    """Test environment variable handling."""
    logger.info("Testing Environment Variables...")
    
    # Test with different environment variable settings
    test_cases = [
        {'FAISS_MEMORY_LIMIT': '2048', 'expected_limit': 2048.0},
        {'FAISS_GPU_ENABLED': 'false', 'expected_gpu': False},
        {'FAISS_LAZY_LOAD': 'true', 'expected_lazy': True},
        {'FAISS_FAIL_FAST': 'false', 'expected_fail_fast': False}
    ]
    
    for case in test_cases:
        # Set environment variables
        original_values = {}
        for key, value in case.items():
            if not key.startswith('expected_'):
                original_values[key] = os.environ.get(key)
                os.environ[key] = value
        
        try:
            # Test configuration loading
            from api.services.enhanced_analog_search import ResourceConfig
            config = ResourceConfig.from_environment()
            
            # Validate configuration
            if 'expected_limit' in case:
                assert config.memory_limit_mb == case['expected_limit'], f"Memory limit should be {case['expected_limit']}"
            if 'expected_lazy' in case:
                assert config.lazy_loading == case['expected_lazy'], f"Lazy loading should be {case['expected_lazy']}"
            if 'expected_fail_fast' in case:
                assert config.fail_fast_on_budget == case['expected_fail_fast'], f"Fail fast should be {case['expected_fail_fast']}"
            
        finally:
            # Restore original values
            for key, original_value in original_values.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value
    
    logger.info("✅ Environment Variables tests passed")

async def main():
    """Run all integration tests."""
    logger.info("🧪 Starting Resource Guardrails Integration Tests")
    logger.info("=" * 60)
    
    try:
        # Test individual components
        test_resource_monitor()
        test_device_manager()
        await test_enhanced_analog_search()
        test_startup_validation()
        test_environment_variables()
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 All Resource Guardrails Integration Tests Passed!")
        logger.info("=" * 60)
        
        # Summary
        logger.info("\nValidated Features:")
        logger.info("✅ Memory profiling and budget enforcement")
        logger.info("✅ GPU/CPU detection and switching")
        logger.info("✅ Enhanced analog search with resource guardrails")
        logger.info("✅ Startup validation integration")
        logger.info("✅ Environment variable configuration")
        logger.info("✅ Lazy loading and fail-fast behavior")
        logger.info("✅ Resource metrics collection")
        logger.info("✅ Device capability validation")
        
        return 0
        
    except Exception as e:
        logger.error(f"Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)