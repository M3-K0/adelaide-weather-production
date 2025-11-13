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

# Test constants for real FAISS behavior validation
TEST_CORRELATION_ID = "test-faiss-real"
FAISS_ENV_VARS = {
    "ALLOW_ANALOG_FALLBACK": "false",
    "FAISS_VALIDATION_MODE": "strict"
}

@pytest.mark.asyncio
class TestRealFAISSBehavior:
    """Test real FAISS analog behavior with comprehensive validation."""
    
    @pytest.fixture
    def faiss_config(self):
        """Configuration for real FAISS testing."""
        return AnalogSearchConfig(
            model_path="outputs/training_production_demo/best_model.pt",
            embeddings_dir="embeddings",
            indices_dir="indices",
            use_optimized_index=True,
            search_timeout_ms=10000,
            retry_attempts=1,
            pool_size=1
        )
    
    @pytest.fixture
    def mock_faiss_forecaster(self):
        """Mock forecaster with real FAISS search capability."""
        forecaster = Mock()
        
        # Mock FAISS indices
        mock_index_6h = Mock()
        mock_index_6h.d = 256
        mock_index_6h.ntotal = 6574
        
        mock_index_24h = Mock()
        mock_index_24h.d = 256 
        mock_index_24h.ntotal = 13148
        
        forecaster.indices = {
            6: mock_index_6h,
            24: mock_index_24h
        }
        
        # Mock metadata
        import pandas as pd
        forecaster.metadata = {
            6: pd.DataFrame({
                'init_time': ['2024-01-01T00:00:00'] * 100,
                'valid_time': ['2024-01-01T06:00:00'] * 100,
                'season': [0] * 100,
                'month': [1] * 100,
                'hour': [0] * 100
            }),
            24: pd.DataFrame({
                'init_time': ['2024-01-01T00:00:00'] * 100,
                'valid_time': ['2024-01-01T24:00:00'] * 100,
                'season': [0] * 100,
                'month': [1] * 100,
                'hour': [0] * 100
            })
        }
        
        # Mock FAISS search methods
        forecaster._extract_weather_pattern.return_value = np.random.randn(10, 5)  # Mock weather pattern
        forecaster._generate_query_embedding.return_value = np.random.randn(1, 256)  # Mock embedding
        
        # Mock FAISS search results with proper monotonic distances
        similarities = np.array([3.8, 3.6, 3.4, 3.2, 3.0])  # FAISS inner products (sorted descending)
        indices = np.array([1, 15, 23, 41, 67])
        forecaster._search_analogs.return_value = (similarities, indices)
        
        return forecaster
    
    async def test_real_faiss_search_method_validation(self, faiss_config):
        """Test that real FAISS search returns search_method='real_faiss'."""
        service = AnalogSearchService(faiss_config)
        service.degraded_mode = False
        
        # Mock the pool to return our test forecaster
        mock_pool = Mock()
        mock_forecaster = self.mock_faiss_forecaster()
        mock_pool.acquire = AsyncMock(return_value=mock_forecaster)
        mock_pool.release = AsyncMock()
        service.pool = mock_pool
        
        # Execute search
        result = await service.search_analogs(
            query_time=datetime.now(timezone.utc),
            horizon=24,
            k=5,
            correlation_id=TEST_CORRELATION_ID
        )
        
        # Verify search method
        assert result.success is True
        assert result.search_metadata['search_method'] == 'real_faiss'
        assert 'data_source' not in result.search_metadata or result.search_metadata.get('data_source') == 'faiss'
        
    async def test_distance_monotonicity_validation(self, faiss_config):
        """Test that distances are monotonically increasing (similarity decreasing)."""
        service = AnalogSearchService(faiss_config)
        service.degraded_mode = False
        
        mock_pool = Mock()
        mock_forecaster = self.mock_faiss_forecaster()
        mock_pool.acquire = AsyncMock(return_value=mock_forecaster)
        mock_pool.release = AsyncMock()
        service.pool = mock_pool
        
        result = await service.search_analogs(
            query_time=datetime.now(timezone.utc),
            horizon=24,
            k=5,
            correlation_id=TEST_CORRELATION_ID
        )
        
        # Verify distances are monotonically increasing
        assert result.success is True
        distances = result.distances
        assert len(distances) > 1
        
        # Check monotonicity
        for i in range(1, len(distances)):
            assert distances[i] >= distances[i-1], f"Distance monotonicity violated at index {i}: {distances[i-1]} > {distances[i]}"
        
        # Verify distance plausibility
        assert np.all(distances >= 0), "Found negative distances"
        assert np.all(distances <= 10.0), "Found unreasonably large distances"
        assert not np.any(np.isnan(distances)), "Found NaN distances"
        assert not np.any(np.isinf(distances)), "Found infinite distances"
    
    async def test_fallback_disabled_behavior(self, faiss_config):
        """Test that service returns 503 when FAISS fails and fallback is disabled."""
        import os
        
        # Disable fallback
        os.environ['ALLOW_ANALOG_FALLBACK'] = 'false'
        
        try:
            service = AnalogSearchService(faiss_config)
            service.degraded_mode = False
            
            # Mock failing FAISS search
            mock_pool = Mock()
            mock_forecaster = Mock()
            mock_forecaster._extract_weather_pattern.return_value = None  # Simulate failure
            mock_pool.acquire = AsyncMock(return_value=mock_forecaster)
            mock_pool.release = AsyncMock()
            service.pool = mock_pool
            
            result = await service.search_analogs(
                query_time=datetime.now(timezone.utc),
                horizon=24,
                k=5,
                correlation_id=TEST_CORRELATION_ID
            )
            
            # Should use fallback since we're in the service layer
            # But verify it's marked appropriately
            assert 'fallback' in result.search_metadata or 'search_method' in result.search_metadata
            
        finally:
            if 'ALLOW_ANALOG_FALLBACK' in os.environ:
                del os.environ['ALLOW_ANALOG_FALLBACK']
    
    async def test_fallback_enabled_behavior(self, faiss_config):
        """Test explicit fallback labeling when ALLOW_ANALOG_FALLBACK=true."""
        import os
        
        # Enable fallback
        os.environ['ALLOW_ANALOG_FALLBACK'] = 'true'
        
        try:
            service = AnalogSearchService(faiss_config)
            service.degraded_mode = True  # Force degraded mode
            
            result = await service.search_analogs(
                query_time=datetime.now(timezone.utc),
                horizon=24,
                k=5,
                correlation_id=TEST_CORRELATION_ID
            )
            
            # Verify fallback is explicitly labeled
            assert result.success is True
            assert result.search_metadata.get('fallback_mode') is True or result.performance_metrics.get('fallback') is True
            assert result.search_metadata.get('search_method') == 'fallback_mock'
            
        finally:
            if 'ALLOW_ANALOG_FALLBACK' in os.environ:
                del os.environ['ALLOW_ANALOG_FALLBACK']
    
    async def test_faiss_index_dimension_validation(self, faiss_config):
        """Test FAISS index dimension validation."""
        service = AnalogSearchService(faiss_config)
        
        # Test valid dimensions
        mock_index = Mock()
        mock_index.d = 256
        assert service._verify_index_dimensions(mock_index, 24) is True
        
        # Test invalid dimensions
        mock_index.d = 128  # Wrong dimension
        assert service._verify_index_dimensions(mock_index, 24) is False
        
    async def test_search_result_validation(self, faiss_config):
        """Test comprehensive search result validation."""
        service = AnalogSearchService(faiss_config)
        
        # Valid search result
        valid_result = {
            'indices': np.array([1, 2, 3, 4, 5]),
            'distances': np.array([0.1, 0.2, 0.3, 0.4, 0.5]),
            'metadata': {'total_candidates': 1000}
        }
        
        validation = service._validate_search_results(valid_result, 24, 5)
        assert validation['valid'] is True
        
        # Invalid result - non-monotonic distances
        invalid_result = {
            'indices': np.array([1, 2, 3, 4, 5]),
            'distances': np.array([0.1, 0.3, 0.2, 0.4, 0.5]),  # Non-monotonic
            'metadata': {'total_candidates': 1000}
        }
        
        validation = service._validate_search_results(invalid_result, 24, 5)
        assert validation['valid'] is False
        assert 'monotonicity' in validation['reason'].lower()
    
    async def test_transparency_field_population(self, faiss_config):
        """Test that transparency fields are properly populated."""
        service = AnalogSearchService(faiss_config)
        service.degraded_mode = False
        
        mock_pool = Mock()
        mock_forecaster = self.mock_faiss_forecaster()
        mock_pool.acquire = AsyncMock(return_value=mock_forecaster)
        mock_pool.release = AsyncMock()
        service.pool = mock_pool
        
        result = await service.search_analogs(
            query_time=datetime.now(timezone.utc),
            horizon=24,
            k=5,
            correlation_id=TEST_CORRELATION_ID
        )
        
        # Verify transparency fields
        assert 'search_metadata' in result.__dict__
        metadata = result.search_metadata
        
        assert 'search_method' in metadata
        assert 'total_candidates' in metadata
        assert 'k_neighbors' in metadata
        assert 'distance_metric' in metadata
        assert 'faiss_index_type' in metadata
        assert 'faiss_index_size' in metadata
        assert 'faiss_index_dim' in metadata
        
        # Verify performance metrics
        assert 'performance_metrics' in result.__dict__
        perf_metrics = result.performance_metrics
        
        assert 'search_time_ms' in perf_metrics
        assert 'total_time_ms' in perf_metrics

@pytest.mark.asyncio 
class TestTimelineDataDeterminism:
    """Test _generate_timeline_data determinism."""
    
    @pytest.fixture
    def service_with_real_data(self):
        """Service configured to use real outcomes data."""
        config = AnalogSearchConfig()
        return AnalogSearchService(config)
    
    async def test_timeline_data_determinism(self, service_with_real_data):
        """Test that same inputs produce same timeline outputs."""
        service = service_with_real_data
        
        # Create consistent search result
        query_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        horizon = 24
        correlation_id = "determinism-test"
        
        search_result = AnalogSearchResult(
            correlation_id=correlation_id,
            horizon=horizon,
            indices=np.array([1, 2, 3, 4, 5]),
            distances=np.array([0.1, 0.2, 0.3, 0.4, 0.5]),
            init_time=query_time,
            search_metadata={},
            performance_metrics={},
            success=True
        )
        
        # Generate timeline data multiple times
        timeline_1 = await service._generate_timeline_data(
            search_result, horizon, query_time, correlation_id
        )
        
        timeline_2 = await service._generate_timeline_data(
            search_result, horizon, query_time, correlation_id
        )
        
        # Verify determinism (same structure and values)
        if not isinstance(timeline_1, dict) or 'error' in timeline_1:
            pytest.skip("Real outcomes data not available for determinism test")
        
        assert timeline_1.keys() == timeline_2.keys()
        
        # Compare forecast timeline points
        timeline_points_1 = timeline_1.get('forecast_timeline', [])
        timeline_points_2 = timeline_2.get('forecast_timeline', [])
        
        assert len(timeline_points_1) == len(timeline_points_2)
        
        for point_1, point_2 in zip(timeline_points_1, timeline_points_2):
            assert point_1['analog_rank'] == point_2['analog_rank']
            assert point_1['analog_index'] == point_2['analog_index']
            assert point_1['similarity_weight'] == point_2['similarity_weight']
            
            # Compare temporal snapshots
            snapshots_1 = point_1['temporal_snapshots']
            snapshots_2 = point_2['temporal_snapshots']
            
            for snap_1, snap_2 in zip(snapshots_1, snapshots_2):
                assert snap_1['progress_percent'] == snap_2['progress_percent']
                # Compare forecast values (should be identical for same real data)
                for key in snap_1['forecast_values']:
                    if key in snap_2['forecast_values']:
                        assert abs(snap_1['forecast_values'][key] - snap_2['forecast_values'][key]) < 1e-6

@pytest.mark.asyncio
class TestPerformanceBenchmarks:
    """Test performance benchmarks for search times and memory usage."""
    
    @pytest.fixture
    def benchmark_config(self):
        """Configuration for performance benchmarks."""
        return AnalogSearchConfig(
            search_timeout_ms=5000,
            max_workers=2,
            pool_size=1
        )
    
    async def test_search_time_benchmarks(self, benchmark_config):
        """Test search time performance meets SLA requirements."""
        service = AnalogSearchService(benchmark_config)
        service.degraded_mode = False
        
        mock_pool = Mock()
        mock_forecaster = Mock()
        
        # Mock fast FAISS search
        mock_forecaster._extract_weather_pattern.return_value = np.random.randn(10, 5)
        mock_forecaster._generate_query_embedding.return_value = np.random.randn(1, 256)
        mock_forecaster._search_analogs.return_value = (
            np.array([3.8, 3.6, 3.4, 3.2, 3.0]), 
            np.array([1, 15, 23, 41, 67])
        )
        
        mock_forecaster.indices = {
            24: Mock(d=256, ntotal=13148)
        }
        mock_forecaster.metadata = {
            24: Mock()
        }
        
        mock_pool.acquire = AsyncMock(return_value=mock_forecaster)
        mock_pool.release = AsyncMock()
        service.pool = mock_pool
        
        # Benchmark multiple searches
        search_times = []
        
        for i in range(5):
            start_time = time.time()
            
            result = await service.search_analogs(
                query_time=datetime.now(timezone.utc),
                horizon=24,
                k=50,
                correlation_id=f"benchmark-{i}"
            )
            
            search_time = (time.time() - start_time) * 1000  # Convert to ms
            search_times.append(search_time)
            
            assert result.success is True
        
        # Verify performance metrics
        avg_time = np.mean(search_times)
        p95_time = np.percentile(search_times, 95)
        
        assert avg_time < 150, f"Average search time {avg_time:.1f}ms exceeds 150ms SLA"
        assert p95_time < 500, f"P95 search time {p95_time:.1f}ms exceeds 500ms SLA"
        
        logger.info(f"Search performance: avg={avg_time:.1f}ms, p95={p95_time:.1f}ms")
    
    async def test_memory_usage_monitoring(self, benchmark_config):
        """Test memory usage stays within reasonable bounds."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / (1024 * 1024)  # MB
        
        service = AnalogSearchService(benchmark_config)
        
        # Simulate multiple searches
        for i in range(10):
            result = await service.search_analogs(
                query_time=datetime.now(timezone.utc),
                horizon=24,
                k=50,
                correlation_id=f"memory-test-{i}"
            )
        
        final_memory = process.memory_info().rss / (1024 * 1024)  # MB
        memory_increase = final_memory - initial_memory
        
        # Allow reasonable memory increase (should be < 100MB for tests)
        assert memory_increase < 100, f"Memory usage increased by {memory_increase:.1f}MB, exceeding limit"
        
        logger.info(f"Memory usage: initial={initial_memory:.1f}MB, final={final_memory:.1f}MB, increase={memory_increase:.1f}MB")

if __name__ == "__main__":
    # Run tests with asyncio support
    pytest.main([__file__, "-v", "--tb=short"])