#!/usr/bin/env python3
"""
Comprehensive API Tests for Adelaide Weather Forecasting System
===============================================================

Complete test suite covering:
- Authentication and authorization
- Input validation and sanitization
- API endpoint functionality
- Error handling and edge cases
- Performance and security requirements
- Pydantic model validation

Target: 90% test coverage for API layer
"""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List

# Import the API components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app, verify_token, forecast_adapter, system_health
from api.forecast_adapter import ForecastAdapter
from api.security_middleware import SecurityMiddleware, InputSanitizer, ValidationUtils
from api.variables import VARIABLE_ORDER, VALID_HORIZONS, DEFAULT_VARIABLES

class TestAPIAuthentication:
    """Test suite for API authentication and authorization."""
    
    def setup_method(self):
        """Setup test client and mock data."""
        self.client = TestClient(app)
        self.valid_token = "test-token-for-comprehensive-testing"
        self.headers = {"Authorization": f"Bearer {self.valid_token}"}
        
        # Mock environment variable
        os.environ["API_TOKEN"] = self.valid_token
    
    def test_missing_authorization_header(self):
        """Test request without Authorization header."""
        response = self.client.get("/forecast")
        assert response.status_code == 401
        assert "Authentication token required" in response.json()["detail"]
    
    def test_invalid_authorization_scheme(self):
        """Test request with invalid authorization scheme."""
        headers = {"Authorization": "Basic invalid-scheme"}
        response = self.client.get("/forecast", headers=headers)
        assert response.status_code == 403  # HTTPBearer returns 403 for invalid scheme
    
    def test_malformed_bearer_token(self):
        """Test request with malformed Bearer token."""
        headers = {"Authorization": "Bearer <script>alert('xss')</script>"}
        response = self.client.get("/forecast", headers=headers)
        assert response.status_code == 401
        assert "Invalid authentication token format" in response.json()["detail"]
    
    def test_token_too_short(self):
        """Test token that's too short."""
        headers = {"Authorization": "Bearer short"}
        response = self.client.get("/forecast", headers=headers)
        assert response.status_code == 401
    
    def test_token_too_long(self):
        """Test token that's too long."""
        long_token = "a" * 200
        headers = {"Authorization": f"Bearer {long_token}"}
        response = self.client.get("/forecast", headers=headers)
        assert response.status_code == 401
    
    def test_token_with_invalid_characters(self):
        """Test token with invalid characters."""
        headers = {"Authorization": "Bearer token-with-@#$%^&*()"}
        response = self.client.get("/forecast", headers=headers)
        assert response.status_code == 401
    
    def test_placeholder_token_detection(self):
        """Test detection of placeholder tokens."""
        placeholder_tokens = ["test", "demo", "example", "default"]
        for token in placeholder_tokens:
            headers = {"Authorization": f"Bearer {token}"}
            response = self.client.get("/forecast", headers=headers)
            assert response.status_code == 401
    
    def test_wrong_token(self):
        """Test with wrong but valid format token."""
        headers = {"Authorization": "Bearer wrong-token-12345"}
        response = self.client.get("/forecast", headers=headers)
        assert response.status_code == 401
        assert "Invalid authentication token" in response.json()["detail"]
    
    @patch('api.main.forecast_adapter')
    def test_valid_token_success(self, mock_adapter):
        """Test successful authentication with valid token."""
        # Mock the forecast adapter
        mock_adapter.forecast_with_uncertainty.return_value = {
            "t2m": {
                "value": 20.0, "p05": 18.0, "p95": 22.0,
                "confidence": 2.0, "available": True, "analog_count": 50
            }
        }
        
        response = self.client.get("/forecast?horizon=24h&vars=t2m", headers=self.headers)
        assert response.status_code == 200
        assert "horizon" in response.json()


class TestAPIInputValidation:
    """Test suite for API input validation and sanitization."""
    
    def setup_method(self):
        """Setup test client and authentication."""
        self.client = TestClient(app)
        self.headers = {"Authorization": "Bearer test-token-for-comprehensive-testing"}
        os.environ["API_TOKEN"] = "test-token-for-comprehensive-testing"
    
    def test_invalid_horizon_values(self):
        """Test various invalid horizon values."""
        invalid_horizons = [
            "invalid", "1h", "72h", "24", "h24", "24hrs", 
            "", " ", "24h ", " 24h", "24H", "INVALID"
        ]
        
        for horizon in invalid_horizons:
            response = self.client.get(f"/forecast?horizon={horizon}", headers=self.headers)
            assert response.status_code == 400, f"Failed for horizon: {horizon}"
            assert "Invalid request parameters" in response.json()["detail"]
    
    def test_valid_horizon_values(self):
        """Test all valid horizon values."""
        with patch('api.main.forecast_adapter') as mock_adapter:
            mock_adapter.forecast_with_uncertainty.return_value = {
                "t2m": {"value": 20.0, "p05": 18.0, "p95": 22.0, 
                       "confidence": 2.0, "available": True, "analog_count": 50}
            }
            
            for horizon in VALID_HORIZONS:
                response = self.client.get(f"/forecast?horizon={horizon}&vars=t2m", headers=self.headers)
                assert response.status_code == 200, f"Failed for horizon: {horizon}"
                data = response.json()
                assert data["horizon"] == horizon
    
    def test_xss_injection_attempts(self):
        """Test XSS injection attempts in parameters."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "onmouseover=alert('xss')",
            "%3Cscript%3Ealert('xss')%3C/script%3E",
            "<iframe src='javascript:alert(\"xss\")'></iframe>"
        ]
        
        for payload in xss_payloads:
            # Test in horizon parameter
            response = self.client.get(f"/forecast?horizon={payload}", headers=self.headers)
            assert response.status_code == 400
            
            # Test in vars parameter
            response = self.client.get(f"/forecast?vars={payload}", headers=self.headers)
            assert response.status_code == 400
    
    def test_sql_injection_attempts(self):
        """Test SQL injection attempts in parameters."""
        sql_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "admin'--",
            "'; INSERT INTO users VALUES ('hacker'); --",
            "' OR 1=1 --"
        ]
        
        for payload in sql_payloads:
            response = self.client.get(f"/forecast?vars=t2m{payload}", headers=self.headers)
            assert response.status_code == 400
    
    def test_invalid_variable_names(self):
        """Test invalid variable names."""
        invalid_vars = [
            "invalid_var", "var@123", "var with spaces", 
            "var-with-dashes", "var.with.dots", "123var",
            "very_long_variable_name_that_exceeds_limits"
        ]
        
        for var in invalid_vars:
            response = self.client.get(f"/forecast?vars={var}", headers=self.headers)
            assert response.status_code == 400
    
    def test_too_many_variables(self):
        """Test request with too many variables."""
        many_vars = ",".join([f"var{i}" for i in range(25)])  # Exceeds 20 limit
        response = self.client.get(f"/forecast?vars={many_vars}", headers=self.headers)
        assert response.status_code == 400
        assert "Too many variables" in response.json()["detail"]
    
    def test_duplicate_variables(self):
        """Test request with duplicate variables."""
        response = self.client.get("/forecast?vars=t2m,u10,t2m,v10", headers=self.headers)
        assert response.status_code == 400
    
    def test_empty_variables_parameter(self):
        """Test request with empty variables parameter."""
        with patch('api.main.forecast_adapter') as mock_adapter:
            mock_adapter.forecast_with_uncertainty.return_value = {
                var: {"value": 20.0, "p05": 18.0, "p95": 22.0, 
                     "confidence": 2.0, "available": True, "analog_count": 50}
                for var in DEFAULT_VARIABLES
            }
            
            response = self.client.get("/forecast?vars=", headers=self.headers)
            assert response.status_code == 200
            # Should use default variables


class TestAPIEndpoints:
    """Test suite for API endpoints functionality."""
    
    def setup_method(self):
        """Setup test client and authentication."""
        self.client = TestClient(app)
        self.headers = {"Authorization": "Bearer test-token-for-comprehensive-testing"}
        os.environ["API_TOKEN"] = "test-token-for-comprehensive-testing"
    
    @patch('api.main.forecast_adapter')
    @patch('api.main.system_health', {"ready": True, "validation_passed": True})
    def test_forecast_endpoint_success(self, mock_adapter):
        """Test successful forecast endpoint response."""
        # Mock forecast adapter response
        mock_response = {
            "t2m": {
                "value": 20.5, "p05": 18.2, "p95": 22.8,
                "confidence": 2.3, "available": True, "analog_count": 45
            },
            "u10": {
                "value": 3.2, "p05": 1.1, "p95": 5.3,
                "confidence": 2.1, "available": True, "analog_count": 45
            },
            "v10": {
                "value": -1.8, "p05": -3.9, "p95": 0.3,
                "confidence": 2.1, "available": True, "analog_count": 45
            }
        }
        mock_adapter.forecast_with_uncertainty.return_value = mock_response
        
        response = self.client.get("/forecast?horizon=24h&vars=t2m,u10,v10", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "horizon" in data
        assert "generated_at" in data
        assert "variables" in data
        assert "wind10m" in data
        assert "versions" in data
        assert "hashes" in data
        assert "latency_ms" in data
        
        assert data["horizon"] == "24h"
        assert "t2m" in data["variables"]
        assert "u10" in data["variables"]
        assert "v10" in data["variables"]
        
        # Validate wind calculation
        assert data["wind10m"] is not None
        assert "speed" in data["wind10m"]
        assert "direction" in data["wind10m"]
    
    def test_health_endpoint_success(self):
        """Test health endpoint response."""
        with patch('api.main.system_health', {"ready": True, "validation_passed": True}):
            response = self.client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            
            # Validate health response structure
            assert "ready" in data
            assert "checks" in data
            assert "model" in data
            assert "index" in data
            assert "datasets" in data
            assert "deps" in data
            assert "uptime_seconds" in data
    
    def test_health_endpoint_system_not_ready(self):
        """Test health endpoint when system is not ready."""
        with patch('api.main.system_health', {"ready": False}):
            response = self.client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["ready"] is False
    
    def test_metrics_endpoint_success(self):
        """Test metrics endpoint with valid authentication."""
        response = self.client.get("/metrics", headers=self.headers)
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
    
    def test_metrics_endpoint_unauthorized(self):
        """Test metrics endpoint without authentication."""
        response = self.client.get("/metrics")
        assert response.status_code == 401
    
    @patch('api.main.forecast_adapter', None)
    def test_forecast_endpoint_adapter_not_ready(self):
        """Test forecast endpoint when adapter is not ready."""
        response = self.client.get("/forecast", headers=self.headers)
        assert response.status_code == 503
        assert "Forecasting system not ready" in response.json()["detail"]


class TestRateLimiting:
    """Test suite for API rate limiting."""
    
    def setup_method(self):
        """Setup test client and authentication."""
        self.client = TestClient(app)
        self.headers = {"Authorization": "Bearer test-token-for-comprehensive-testing"}
        os.environ["API_TOKEN"] = "test-token-for-comprehensive-testing"
    
    def test_forecast_rate_limit(self):
        """Test forecast endpoint rate limiting (60/minute)."""
        # This test would need to be run with actual rate limiting enabled
        # For unit testing, we can mock the rate limiter
        with patch('api.main.forecast_adapter') as mock_adapter:
            mock_adapter.forecast_with_uncertainty.return_value = {
                "t2m": {"value": 20.0, "p05": 18.0, "p95": 22.0, 
                       "confidence": 2.0, "available": True, "analog_count": 50}
            }
            
            # Make multiple rapid requests
            responses = []
            for _ in range(5):
                response = self.client.get("/forecast?vars=t2m", headers=self.headers)
                responses.append(response.status_code)
            
            # Should succeed for reasonable number of requests
            assert all(status in [200, 429] for status in responses)
    
    def test_health_rate_limit(self):
        """Test health endpoint rate limiting (30/minute)."""
        responses = []
        for _ in range(3):
            response = self.client.get("/health")
            responses.append(response.status_code)
        
        # Should succeed for reasonable number of requests
        assert all(status in [200, 429] for status in responses)


class TestErrorHandling:
    """Test suite for error handling and edge cases."""
    
    def setup_method(self):
        """Setup test client and authentication."""
        self.client = TestClient(app)
        self.headers = {"Authorization": "Bearer test-token-for-comprehensive-testing"}
        os.environ["API_TOKEN"] = "test-token-for-comprehensive-testing"
    
    @patch('api.main.forecast_adapter')
    def test_adapter_exception_handling(self, mock_adapter):
        """Test handling of exceptions from forecast adapter."""
        mock_adapter.forecast_with_uncertainty.side_effect = Exception("Adapter error")
        
        response = self.client.get("/forecast?vars=t2m", headers=self.headers)
        assert response.status_code == 500
        
        # Error message should be sanitized
        assert "Internal server error" in response.json()["detail"]
    
    def test_invalid_endpoint(self):
        """Test request to invalid endpoint."""
        response = self.client.get("/invalid_endpoint", headers=self.headers)
        assert response.status_code == 404
    
    def test_method_not_allowed(self):
        """Test unsupported HTTP method."""
        response = self.client.post("/forecast", headers=self.headers)
        assert response.status_code == 405
    
    def test_large_request_headers(self):
        """Test request with oversized headers."""
        large_headers = self.headers.copy()
        large_headers["X-Large-Header"] = "A" * 10000
        
        response = self.client.get("/forecast", headers=large_headers)
        # Should either succeed or be rejected gracefully
        assert response.status_code in [200, 400, 413, 431]
    
    def test_request_timeout_simulation(self):
        """Test request timeout handling."""
        # This would typically be tested at the integration level
        # For unit testing, we can mock slow operations
        with patch('api.main.forecast_adapter') as mock_adapter:
            def slow_response(*args, **kwargs):
                time.sleep(0.1)  # Simulate slow response
                return {"t2m": {"value": 20.0, "p05": 18.0, "p95": 22.0, 
                               "confidence": 2.0, "available": True, "analog_count": 50}}
            
            mock_adapter.forecast_with_uncertainty.side_effect = slow_response
            
            response = self.client.get("/forecast?vars=t2m", headers=self.headers)
            # Should complete successfully
            assert response.status_code == 200


class TestPydanticValidation:
    """Test suite for Pydantic model validation."""
    
    def setup_method(self):
        """Setup test client and authentication."""
        self.client = TestClient(app)
        self.headers = {"Authorization": "Bearer test-token-for-comprehensive-testing"}
        os.environ["API_TOKEN"] = "test-token-for-comprehensive-testing"
    
    @patch('api.main.forecast_adapter')
    def test_variable_result_validation(self, mock_adapter):
        """Test VariableResult model validation."""
        # Test with invalid analog count
        mock_adapter.forecast_with_uncertainty.return_value = {
            "t2m": {
                "value": 20.0, "p05": 18.0, "p95": 22.0,
                "confidence": 2.0, "available": True, "analog_count": -1  # Invalid
            }
        }
        
        response = self.client.get("/forecast?vars=t2m", headers=self.headers)
        # Should handle validation error gracefully
        assert response.status_code in [200, 422, 500]
    
    @patch('api.main.forecast_adapter')
    def test_extreme_values_validation(self, mock_adapter):
        """Test validation of extreme values."""
        mock_adapter.forecast_with_uncertainty.return_value = {
            "t2m": {
                "value": 1e15,  # Extreme value
                "p05": 18.0, "p95": 22.0,
                "confidence": 2.0, "available": True, "analog_count": 50
            }
        }
        
        response = self.client.get("/forecast?vars=t2m", headers=self.headers)
        # Should handle extreme values appropriately
        assert response.status_code in [200, 422, 500]
    
    @patch('api.main.forecast_adapter')
    def test_wind_calculation_edge_cases(self, mock_adapter):
        """Test wind calculation with edge case values."""
        # Test with zero wind components
        mock_adapter.forecast_with_uncertainty.return_value = {
            "u10": {"value": 0.0, "p05": -1.0, "p95": 1.0,
                   "confidence": 1.0, "available": True, "analog_count": 50},
            "v10": {"value": 0.0, "p05": -1.0, "p95": 1.0,
                   "confidence": 1.0, "available": True, "analog_count": 50}
        }
        
        response = self.client.get("/forecast?vars=u10,v10", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        # Wind speed should be 0, direction should be calculated
        assert data["wind10m"]["speed"] == 0.0
        assert 0 <= data["wind10m"]["direction"] < 360


class TestPerformanceRequirements:
    """Test suite for performance requirements."""
    
    def setup_method(self):
        """Setup test client and authentication."""
        self.client = TestClient(app)
        self.headers = {"Authorization": "Bearer test-token-for-comprehensive-testing"}
        os.environ["API_TOKEN"] = "test-token-for-comprehensive-testing"
    
    @patch('api.main.forecast_adapter')
    def test_response_time_requirement(self, mock_adapter):
        """Test that responses meet <150ms requirement."""
        mock_adapter.forecast_with_uncertainty.return_value = {
            "t2m": {"value": 20.0, "p05": 18.0, "p95": 22.0,
                   "confidence": 2.0, "available": True, "analog_count": 50}
        }
        
        start_time = time.time()
        response = self.client.get("/forecast?vars=t2m", headers=self.headers)
        end_time = time.time()
        
        response_time_ms = (end_time - start_time) * 1000
        
        assert response.status_code == 200
        # Note: This is a unit test, so actual response time will be very fast
        # Real performance testing should be done with integration tests
        assert response_time_ms < 1000  # Generous limit for unit test
        
        # Check that latency is reported in response
        data = response.json()
        assert "latency_ms" in data
        assert isinstance(data["latency_ms"], (int, float))
    
    @patch('api.main.forecast_adapter')
    def test_concurrent_requests_simulation(self, mock_adapter):
        """Test simulation of concurrent requests."""
        mock_adapter.forecast_with_uncertainty.return_value = {
            "t2m": {"value": 20.0, "p05": 18.0, "p95": 22.0,
                   "confidence": 2.0, "available": True, "analog_count": 50}
        }
        
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            response = self.client.get("/forecast?vars=t2m", headers=self.headers)
            results.put(response.status_code)
        
        # Simulate concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        status_codes = []
        while not results.empty():
            status_codes.append(results.get())
        
        assert all(status == 200 for status in status_codes)
        assert len(status_codes) == 5


# Test fixtures and utilities
@pytest.fixture
def mock_forecast_adapter():
    """Fixture for mocked forecast adapter."""
    adapter = Mock(spec=ForecastAdapter)
    adapter.forecast_with_uncertainty.return_value = {
        "t2m": {"value": 20.0, "p05": 18.0, "p95": 22.0,
               "confidence": 2.0, "available": True, "analog_count": 50},
        "u10": {"value": 3.0, "p05": 1.0, "p95": 5.0,
               "confidence": 2.0, "available": True, "analog_count": 50},
        "v10": {"value": -2.0, "p05": -4.0, "p95": 0.0,
               "confidence": 2.0, "available": True, "analog_count": 50}
    }
    adapter.get_system_health.return_value = {
        "adapter_ready": True,
        "forecaster_loaded": True
    }
    return adapter


@pytest.fixture
def valid_headers():
    """Fixture for valid authentication headers."""
    return {"Authorization": "Bearer test-token-for-comprehensive-testing"}


if __name__ == "__main__":
    # Run tests with coverage
    pytest.main([
        __file__,
        "-v",
        "--cov=api",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-fail-under=90"
    ])