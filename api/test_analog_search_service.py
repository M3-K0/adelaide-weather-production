#!/usr/bin/env python3
"""
Unit Tests for AnalogSearchService
=================================

Comprehensive test suite for the AnalogSearchService class covering:
- Async interface functionality
- Connection pooling behavior 
- Error handling and graceful degradation
- Performance monitoring
- Service lifecycle management
"""

import pytest
import asyncio
import numpy as np
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

# Import the service under test
from api.services.analog_search import (
    AnalogSearchService,
    AnalogSearchConfig,
    AnalogSearchResult,
    AnalogSearchPool,
    get_analog_search_service,
    shutdown_analog_search_service
)

class TestAnalogSearchConfig:
    """Test AnalogSearchConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = AnalogSearchConfig()
        
        assert config.model_path == "outputs/training_production_demo/best_model.pt"
        assert config.config_path == "configs/model.yaml"
        assert config.embeddings_dir == "embeddings"
        assert config.indices_dir == "indices"
        assert config.use_optimized_index is True
        assert config.max_workers == 4
        assert config.search_timeout_ms == 5000
        assert config.retry_attempts == 2
        assert config.pool_size == 2
        assert config.pool_timeout_ms == 1000
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = AnalogSearchConfig(
            model_path="/custom/model.pt",
            max_workers=8,
            search_timeout_ms=10000,
            pool_size=4
        )
        
        assert config.model_path == "/custom/model.pt"
        assert config.max_workers == 8
        assert config.search_timeout_ms == 10000
        assert config.pool_size == 4

class TestAnalogSearchResult:
    """Test AnalogSearchResult dataclass."""
    
    def test_successful_result(self):
        """Test successful search result creation."""
        indices = np.array([1, 2, 3, 4, 5])
        distances = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        
        result = AnalogSearchResult(
            correlation_id="test-123",
            horizon=24,
            indices=indices,
            distances=distances,
            init_time=datetime.now(timezone.utc),
            search_metadata={"k": 5},
            performance_metrics={"time_ms": 100},
            success=True
        )
        
        assert result.correlation_id == "test-123"
        assert result.horizon == 24
        assert np.array_equal(result.indices, indices)
        assert np.array_equal(result.distances, distances)
        assert result.success is True
        assert result.error_message is None
    
    def test_failed_result(self):
        """Test failed search result creation."""
        result = AnalogSearchResult(
            correlation_id="test-456",
            horizon=12,
            indices=np.array([]),
            distances=np.array([]),
            init_time=datetime.now(timezone.utc),
            search_metadata={},
            performance_metrics={},
            success=False,
            error_message="Search failed"
        )
        
        assert result.success is False
        assert result.error_message == "Search failed"
        assert len(result.indices) == 0
        assert len(result.distances) == 0

@pytest.mark.asyncio
class TestAnalogSearchPool:
    """Test AnalogSearchPool connection pooling."""
    
    @pytest.fixture
    def config(self):
        """Test configuration with small pool size."""
        return AnalogSearchConfig(
            pool_size=2,
            pool_timeout_ms=100,
            max_workers=2
        )
    
    @pytest.fixture
    def mock_forecaster(self):
        """Mock forecaster instance."""
        mock = Mock()
        mock.forecast.return_value = {
            'confidence': 0.8,
            'ensemble_mean': 15.0
        }
        return mock
    
    async def test_pool_initialization_success(self, config):
        """Test successful pool initialization."""
        pool = AnalogSearchPool(config)
        
        # Mock the forecaster creation
        with patch.object(pool, '_create_forecaster_instance') as mock_create:
            mock_create.return_value = Mock()
            
            success = await pool.initialize()
            
            assert success is True
            assert pool._initialized is True
            assert len(pool.pool) == config.pool_size
            assert mock_create.call_count == config.pool_size
    
    async def test_pool_initialization_failure(self, config):
        """Test pool initialization with failures."""
        pool = AnalogSearchPool(config)
        
        # Mock the forecaster creation to fail
        with patch.object(pool, '_create_forecaster_instance') as mock_create:
            mock_create.side_effect = Exception("Creation failed")
            
            success = await pool.initialize()
            
            assert success is False
            assert pool._initialized is False
            assert len(pool.pool) == 0
    
    async def test_acquire_and_release(self, config, mock_forecaster):
        """Test acquiring and releasing forecasters."""
        pool = AnalogSearchPool(config)
        
        with patch.object(pool, '_create_forecaster_instance') as mock_create:
            mock_create.return_value = mock_forecaster
            
            await pool.initialize()
            
            # Acquire forecaster
            forecaster = await pool.acquire()
            assert forecaster is mock_forecaster
            
            # Release forecaster
            await pool.release(forecaster)
            
            # Should be able to acquire again
            forecaster2 = await pool.acquire()
            assert forecaster2 is mock_forecaster
    
    async def test_acquire_timeout(self, config, mock_forecaster):
        """Test acquire timeout when pool is exhausted."""
        config.pool_timeout_ms = 50  # Very short timeout
        pool = AnalogSearchPool(config)
        
        with patch.object(pool, '_create_forecaster_instance') as mock_create:
            mock_create.return_value = mock_forecaster
            
            await pool.initialize()
            
            # Acquire all forecasters
            forecasters = []
            for _ in range(config.pool_size):
                f = await pool.acquire()
                forecasters.append(f)
            
            # Next acquire should timeout
            forecaster = await pool.acquire()
            assert forecaster is None
    
    async def test_shutdown(self, config, mock_forecaster):
        """Test pool shutdown."""
        pool = AnalogSearchPool(config)
        
        with patch.object(pool, '_create_forecaster_instance') as mock_create:
            mock_create.return_value = mock_forecaster
            
            await pool.initialize()
            assert pool._initialized is True
            
            await pool.shutdown()
            assert pool._initialized is False
            assert len(pool.pool) == 0

@pytest.mark.asyncio 
class TestAnalogSearchService:
    """Test AnalogSearchService main functionality."""
    
    @pytest.fixture
    def config(self):
        """Test configuration."""
        return AnalogSearchConfig(
            pool_size=1,
            search_timeout_ms=1000,
            retry_attempts=2,
            max_workers=1
        )
    
    @pytest.fixture
    def service(self, config):
        """Service instance for testing."""
        return AnalogSearchService(config)
    
    @pytest.fixture
    def mock_pool(self):
        """Mock connection pool."""
        pool = Mock()
        pool.initialize = AsyncMock(return_value=True)
        pool.acquire = AsyncMock()
        pool.release = AsyncMock()
        pool.shutdown = AsyncMock()
        return pool
    
    async def test_service_initialization_success(self, service, mock_pool):
        """Test successful service initialization."""
        service.pool = mock_pool
        
        success = await service.initialize()
        
        assert success is True
        assert service.degraded_mode is False
        mock_pool.initialize.assert_called_once()
    
    async def test_service_initialization_degraded(self, service, mock_pool):
        """Test service initialization with pool failure."""
        service.pool = mock_pool
        mock_pool.initialize.return_value = False
        
        success = await service.initialize()
        
        assert success is True  # Service still initializes
        assert service.degraded_mode is True  # But in degraded mode
    
    async def test_search_analogs_input_validation(self, service):
        """Test input validation for search_analogs."""
        # Test invalid horizon
        result = await service.search_analogs(
            query_time=datetime.now(timezone.utc),
            horizon=99,  # Invalid horizon
            k=50
        )
        
        assert result.success is False
        assert "Invalid horizon" in result.error_message
        
        # Test invalid k
        result = await service.search_analogs(
            query_time=datetime.now(timezone.utc),
            horizon=24,
            k=0  # Invalid k
        )
        
        assert result.success is False
        assert "Invalid k" in result.error_message
    
    async def test_search_analogs_degraded_mode(self, service):
        """Test analog search in degraded mode."""
        service.degraded_mode = True
        
        result = await service.search_analogs(
            query_time=datetime.now(timezone.utc),
            horizon=24,
            k=50
        )
        
        assert result.success is True
        assert result.search_metadata.get('fallback_mode') is True
        assert len(result.indices) > 0
        assert len(result.distances) > 0
    
    async def test_search_analogs_successful(self, service, mock_pool):
        """Test successful analog search."""
        service.pool = mock_pool
        service.degraded_mode = False
        
        # Mock forecaster
        mock_forecaster = Mock()
        mock_forecaster.forecast.return_value = {
            'confidence': 0.8,
            'ensemble_mean': 15.0
        }
        mock_pool.acquire.return_value = mock_forecaster
        
        with patch.object(service, '_execute_analog_search') as mock_execute:
            mock_execute.return_value = {
                'indices': np.array([1, 2, 3]),
                'distances': np.array([0.1, 0.2, 0.3]),
                'metadata': {'k': 3},
                'search_time_ms': 50.0
            }
            
            result = await service.search_analogs(
                query_time=datetime.now(timezone.utc),
                horizon=24,
                k=3
            )
            
            assert result.success is True
            assert len(result.indices) == 3
            assert len(result.distances) == 3
            assert result.horizon == 24
            mock_pool.acquire.assert_called_once()
            mock_pool.release.assert_called_once()
    
    async def test_search_analogs_with_retry(self, service, mock_pool):
        """Test analog search with retry logic."""
        service.pool = mock_pool
        service.degraded_mode = False
        service.config.retry_attempts = 2
        
        # Mock forecaster
        mock_forecaster = Mock()
        mock_pool.acquire.return_value = mock_forecaster
        
        with patch.object(service, '_execute_analog_search') as mock_execute:
            # First call fails, second succeeds
            mock_execute.side_effect = [
                None,  # First attempt fails
                {      # Second attempt succeeds
                    'indices': np.array([1, 2]),
                    'distances': np.array([0.1, 0.2]),
                    'metadata': {'k': 2},
                    'search_time_ms': 75.0
                }
            ]
            
            result = await service.search_analogs(
                query_time=datetime.now(timezone.utc),
                horizon=12,
                k=2
            )
            
            assert result.success is True
            assert result.performance_metrics['attempt'] == 2
            assert mock_execute.call_count == 2
    
    async def test_generate_analog_results_for_adapter(self, service):
        """Test adapter-compatible result generation."""
        service.degraded_mode = True  # Use fallback for predictable results
        
        result = await service.generate_analog_results_for_adapter(
            horizon_hours=25,  # Should map to 48h horizon
            correlation_id="test-adapter"
        )
        
        assert 'indices' in result
        assert 'distances' in result
        assert 'init_time' in result
        assert 'search_metadata' in result
        assert result['search_metadata']['correlation_id'] == "test-adapter"
    
    async def test_health_check(self, service):
        """Test service health check."""
        service.request_count = 100
        service.error_count = 5
        service.total_search_time = 10.0
        
        health = await service.health_check()
        
        assert health['service'] == 'AnalogSearchService'
        assert health['status'] in ['healthy', 'degraded', 'unhealthy']
        assert health['metrics']['total_requests'] == 100
        assert health['metrics']['error_count'] == 5
        assert health['metrics']['error_rate'] == 0.05
        assert 'pool' in health
        assert 'config' in health
    
    async def test_shutdown(self, service, mock_pool):
        """Test service shutdown."""
        service.pool = mock_pool
        
        with patch.object(service.executor, 'shutdown') as mock_executor_shutdown:
            await service.shutdown()
            
            mock_pool.shutdown.assert_called_once()
            mock_executor_shutdown.assert_called_once_with(wait=True)

@pytest.mark.asyncio
class TestDependencyInjection:
    """Test dependency injection functions."""
    
    async def test_get_analog_search_service(self):
        """Test getting the global service instance."""
        # Reset global instance
        import api.services.analog_search as service_module
        service_module._analog_search_service = None
        
        with patch.object(AnalogSearchService, 'initialize') as mock_init:
            mock_init.return_value = True
            
            service1 = await get_analog_search_service()
            service2 = await get_analog_search_service()
            
            # Should return the same instance
            assert service1 is service2
            assert isinstance(service1, AnalogSearchService)
            mock_init.assert_called_once()
    
    async def test_shutdown_analog_search_service(self):
        """Test shutting down the global service instance."""
        import api.services.analog_search as service_module
        
        # Create a mock service instance
        mock_service = Mock()
        mock_service.shutdown = AsyncMock()
        service_module._analog_search_service = mock_service
        
        await shutdown_analog_search_service()
        
        mock_service.shutdown.assert_called_once()
        assert service_module._analog_search_service is None

class TestPerformanceMetrics:
    """Test performance monitoring functionality."""
    
    def test_performance_tracking(self):
        """Test that performance metrics are tracked correctly."""
        service = AnalogSearchService()
        
        # Initial state
        assert service.request_count == 0
        assert service.error_count == 0
        assert service.total_search_time == 0.0
        
        # Simulate some activity
        service.request_count = 50
        service.error_count = 2
        service.total_search_time = 5.0
        
        # Check calculations
        error_rate = service.error_count / service.request_count
        avg_time = service.total_search_time / (service.request_count - service.error_count)
        
        assert error_rate == 0.04  # 4% error rate
        assert avg_time == 5.0 / 48  # Average successful request time

if __name__ == "__main__":
    # Run tests with asyncio support
    pytest.main([__file__, "-v"])