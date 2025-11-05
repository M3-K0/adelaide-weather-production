#!/usr/bin/env python3
"""
Integration Tests for AnalogSearchService with ForecastAdapter
=============================================================

Comprehensive integration test suite verifying that:
- AnalogSearchService integrates correctly with ForecastAdapter
- Async interfaces work end-to-end
- Error handling and graceful degradation work properly
- Performance meets SLA requirements (<50ms for analog search)
- Service lifecycle management works correctly
"""

import pytest
import asyncio
import time
import numpy as np
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Import components under test
from api.services import (
    AnalogSearchService,
    AnalogSearchConfig,
    get_analog_search_service,
    shutdown_analog_search_service
)
from api.forecast_adapter import ForecastAdapter

@pytest.mark.asyncio
class TestAnalogSearchServiceIntegration:
    """Integration tests for AnalogSearchService with production components."""
    
    @pytest.fixture
    def integration_config(self):
        """Configuration for integration testing."""
        return AnalogSearchConfig(
            pool_size=1,  # Small pool for testing
            search_timeout_ms=2000,  # 2 second timeout
            retry_attempts=1,  # Single retry for fast tests
            max_workers=1
        )
    
    @pytest.fixture
    async def service(self, integration_config):
        """Integration service instance."""
        service = AnalogSearchService(integration_config)
        
        # Mock the forecaster creation to avoid loading actual models
        with patch.object(service.pool, '_create_forecaster_instance') as mock_create:
            mock_forecaster = Mock()
            mock_forecaster.forecast.return_value = {
                'confidence': 0.85,
                'ensemble_mean': 18.5,
                'query_time': datetime.now(timezone.utc),
                'valid_time': datetime.now(timezone.utc)
            }
            mock_create.return_value = mock_forecaster
            
            await service.initialize()
            yield service
            await service.shutdown()
    
    async def test_service_initialization(self, service):
        """Test that service initializes properly."""
        health = await service.health_check()
        
        assert health['service'] == 'AnalogSearchService'
        assert health['status'] in ['healthy', 'degraded']
        assert health['pool']['initialized'] is True
    
    async def test_analog_search_basic_functionality(self, service):
        """Test basic analog search functionality."""
        query_time = datetime.now(timezone.utc)
        
        result = await service.search_analogs(
            query_time=query_time,
            horizon=24,
            k=10
        )
        
        assert result.success is True
        assert result.horizon == 24
        assert len(result.indices) > 0
        assert len(result.distances) > 0
        assert result.correlation_id is not None
        assert 'search_time_ms' in result.performance_metrics
    
    async def test_analog_search_performance_sla(self, service):
        """Test that analog search meets <50ms SLA."""
        start_time = time.time()
        
        result = await service.search_analogs(
            query_time=datetime.now(timezone.utc),
            horizon=12,
            k=25
        )
        
        total_time_ms = (time.time() - start_time) * 1000
        
        assert result.success is True
        assert total_time_ms < 50.0, f"Search took {total_time_ms:.1f}ms, exceeds 50ms SLA"
        assert result.performance_metrics['total_time_ms'] < 50.0
    
    async def test_analog_search_all_horizons(self, service):
        """Test analog search for all supported horizons."""
        horizons = [6, 12, 24, 48]
        
        for horizon in horizons:
            result = await service.search_analogs(
                query_time=datetime.now(timezone.utc),
                horizon=horizon,
                k=20
            )
            
            assert result.success is True, f"Search failed for horizon {horizon}h"
            assert result.horizon == horizon
            assert len(result.indices) > 0
    
    async def test_adapter_compatible_interface(self, service):
        """Test that service provides adapter-compatible interface."""
        result = await service.generate_analog_results_for_adapter(
            horizon_hours=25,  # Should map to 48h horizon
            correlation_id="test-adapter-compat"
        )
        
        # Verify adapter-expected format
        assert 'indices' in result
        assert 'distances' in result
        assert 'init_time' in result
        assert 'search_metadata' in result
        
        # Verify correlation ID is passed through
        assert result['search_metadata']['correlation_id'] == "test-adapter-compat"
        
        # Verify arrays are numpy arrays (forecaster expects this)
        assert isinstance(result['indices'], np.ndarray)
        assert isinstance(result['distances'], np.ndarray)
        assert isinstance(result['init_time'], datetime)
    
    async def test_degraded_mode_functionality(self, service):
        """Test service functionality in degraded mode."""
        # Force degraded mode
        service.degraded_mode = True
        
        result = await service.search_analogs(
            query_time=datetime.now(timezone.utc),
            horizon=24,
            k=30
        )
        
        assert result.success is True
        assert result.search_metadata.get('fallback_mode') is True
        assert len(result.indices) > 0
        assert len(result.distances) > 0
        
        # Performance should still be good in degraded mode
        assert result.performance_metrics['total_time_ms'] < 50.0
    
    async def test_error_handling_and_recovery(self, service):
        """Test error handling and retry logic."""
        # Mock pool to simulate temporary failure
        original_acquire = service.pool.acquire
        
        call_count = 0
        async def failing_acquire():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None  # First call fails
            return await original_acquire()  # Second call succeeds
        
        service.pool.acquire = failing_acquire
        
        result = await service.search_analogs(
            query_time=datetime.now(timezone.utc),
            horizon=12,
            k=15
        )
        
        # Should eventually succeed due to retry logic
        assert result.success is True
        assert call_count >= 2  # Verify retry occurred

@pytest.mark.asyncio 
class TestForecastAdapterIntegration:
    """Integration tests for ForecastAdapter with AnalogSearchService."""
    
    @pytest.fixture
    async def adapter(self):
        """ForecastAdapter instance for testing."""
        adapter = ForecastAdapter()
        
        # Mock the analog service to avoid actual model loading
        mock_service = Mock()
        mock_service.generate_analog_results_for_adapter = AsyncMock()
        mock_service.generate_analog_results_for_adapter.return_value = {
            'indices': np.array([1, 2, 3, 4, 5]),
            'distances': np.array([0.1, 0.2, 0.3, 0.4, 0.5]),
            'init_time': datetime.now(timezone.utc),
            'search_metadata': {
                'k_neighbors': 5,
                'search_time_ms': 25.0,
                'correlation_id': 'test-integration'
            }
        }
        mock_service.health_check = AsyncMock()
        mock_service.health_check.return_value = {
            'status': 'healthy',
            'service': 'AnalogSearchService'
        }
        
        adapter.analog_service = mock_service
        
        return adapter
    
    async def test_adapter_async_forecast_generation(self, adapter):
        """Test that adapter can generate forecasts asynchronously."""
        variables = ['t2m', 'u10', 'v10']
        
        # Mock the core forecaster to return a result
        with patch.object(adapter.forecaster, 'generate_forecast') as mock_forecast:
            # Create a mock forecast result
            mock_result = Mock()
            mock_result.variables = {
                't2m': 295.15,  # 22°C in Kelvin
                'u10': 5.2,
                'v10': -2.1
            }
            mock_result.confidence_intervals = {
                't2m': (290.15, 300.15),
                'u10': (2.0, 8.0),
                'v10': (-5.0, 1.0)
            }
            mock_result.ensemble_size = 25
            mock_forecast.return_value = mock_result
            
            result = await adapter.forecast_with_uncertainty(
                horizon='24h',
                variables=variables
            )
            
            assert len(result) == len(variables)
            for var in variables:
                assert var in result
                assert result[var]['available'] is True
                assert result[var]['value'] is not None
                assert result[var]['analog_count'] == 25
    
    async def test_adapter_service_integration(self, adapter):
        """Test that adapter properly integrates with AnalogSearchService."""
        # Verify that the adapter calls the service correctly
        result = await adapter._generate_analog_results(24)
        
        assert 'indices' in result
        assert 'distances' in result
        assert 'search_metadata' in result
        
        # Verify service was called with correct parameters
        adapter.analog_service.generate_analog_results_for_adapter.assert_called_once()
        call_args = adapter.analog_service.generate_analog_results_for_adapter.call_args
        assert call_args[1]['horizon_hours'] == 24
        assert 'correlation_id' in call_args[1]
    
    async def test_adapter_graceful_degradation(self, adapter):
        """Test adapter graceful degradation when service fails."""
        # Make service fail
        adapter.analog_service.generate_analog_results_for_adapter.side_effect = Exception("Service unavailable")
        
        result = await adapter._generate_analog_results(12)
        
        # Should fall back to mock results
        assert 'indices' in result
        assert 'distances' in result
        assert result['search_metadata'].get('fallback_mode') is True
    
    async def test_adapter_health_check_integration(self, adapter):
        """Test that adapter health check includes service status."""
        health = await adapter.get_system_health()
        
        assert 'adapter_ready' in health
        assert 'analog_service_ready' in health
        assert 'analog_service_health' in health
        
        # Verify service health check was called
        adapter.analog_service.health_check.assert_called_once()

@pytest.mark.asyncio
class TestEndToEndIntegration:
    """End-to-end integration tests."""
    
    async def test_dependency_injection_lifecycle(self):
        """Test complete service lifecycle through dependency injection."""
        # Reset global service
        await shutdown_analog_search_service()
        
        with patch('api.services.analog_search.AnalogSearchService') as MockService:
            mock_instance = Mock()
            mock_instance.initialize = AsyncMock(return_value=True)
            mock_instance.shutdown = AsyncMock()
            MockService.return_value = mock_instance
            
            # Get service instance (should initialize)
            service1 = await get_analog_search_service()
            service2 = await get_analog_search_service()
            
            # Should return same instance
            assert service1 is service2
            
            # Should have called initialize
            mock_instance.initialize.assert_called_once()
            
            # Shutdown
            await shutdown_analog_search_service()
            mock_instance.shutdown.assert_called_once()
    
    async def test_full_forecast_pipeline(self):
        """Test complete forecast pipeline from API call to result."""
        adapter = ForecastAdapter()
        
        # Mock both the analog service and core forecaster
        with patch('api.services.get_analog_search_service') as mock_get_service:
            # Mock analog service
            mock_service = Mock()
            mock_service.generate_analog_results_for_adapter = AsyncMock()
            mock_service.generate_analog_results_for_adapter.return_value = {
                'indices': np.array([100, 200, 300]),
                'distances': np.array([0.15, 0.25, 0.35]),
                'init_time': datetime.now(timezone.utc),
                'search_metadata': {'k_neighbors': 3, 'search_time_ms': 15.0}
            }
            mock_get_service.return_value = mock_service
            
            # Mock core forecaster
            with patch.object(adapter.forecaster, 'generate_forecast') as mock_forecast:
                mock_result = Mock()
                mock_result.variables = {'t2m': 298.15}
                mock_result.confidence_intervals = {'t2m': (295.15, 301.15)}
                mock_result.ensemble_size = 3
                mock_forecast.return_value = mock_result
                
                # Execute full pipeline
                result = await adapter.forecast_with_uncertainty(
                    horizon='12h',
                    variables=['t2m']
                )
                
                # Verify end-to-end result
                assert 't2m' in result
                assert result['t2m']['available'] is True
                assert result['t2m']['analog_count'] == 3
                
                # Verify the pipeline was executed
                mock_service.generate_analog_results_for_adapter.assert_called_once()
                mock_forecast.assert_called_once()

if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short"])