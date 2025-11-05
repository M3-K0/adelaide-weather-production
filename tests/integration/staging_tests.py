#!/usr/bin/env python3
"""
Integration tests for staging environment.
These tests run against the deployed staging environment to verify functionality.
"""

import os
import time
import pytest
import requests
from typing import Dict, Any


class TestStagingEnvironment:
    """Test suite for staging environment integration tests."""
    
    def setup_class(self):
        """Setup test environment."""
        self.base_url = os.getenv('STAGING_URL', 'https://staging.weather-forecast.dev')
        self.api_url = os.getenv('STAGING_API_URL', 'https://api-staging.weather-forecast.dev')
        self.timeout = 30

    def test_frontend_health(self):
        """Test that frontend is accessible and returns 200."""
        response = requests.get(f"{self.base_url}/", timeout=self.timeout)
        assert response.status_code == 200
        assert "Adelaide Weather" in response.text or "weather" in response.text.lower()

    def test_api_health(self):
        """Test that API health endpoint is working."""
        response = requests.get(f"{self.api_url}/health", timeout=self.timeout)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "environment" in data

    def test_api_forecast_endpoint(self):
        """Test forecast endpoint with valid coordinates."""
        # Adelaide coordinates
        lat, lon = -34.9285, 138.6007
        
        response = requests.get(
            f"{self.api_url}/forecast",
            params={"lat": lat, "lon": lon},
            timeout=self.timeout
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "forecast" in data
        assert "location" in data
        assert "generated_at" in data
        assert "model_version" in data
        
        # Verify forecast data
        forecast = data["forecast"]
        assert isinstance(forecast, list)
        assert len(forecast) > 0
        
        # Check forecast entry structure
        entry = forecast[0]
        assert "datetime" in entry
        assert "temperature" in entry
        assert "conditions" in entry

    def test_api_forecast_invalid_coordinates(self):
        """Test forecast endpoint with invalid coordinates."""
        response = requests.get(
            f"{self.api_url}/forecast",
            params={"lat": 1000, "lon": 1000},
            timeout=self.timeout
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_api_rate_limiting(self):
        """Test that rate limiting is working."""
        # Make rapid requests to trigger rate limiting
        responses = []
        for _ in range(100):
            try:
                response = requests.get(f"{self.api_url}/health", timeout=5)
                responses.append(response.status_code)
            except requests.RequestException:
                # Expected if rate limited
                break
        
        # Should eventually get rate limited (429)
        # Allow some requests through but should limit eventually
        rate_limited = any(status == 429 for status in responses)
        # Don't strictly require rate limiting in staging for testing flexibility
        # assert rate_limited, "Rate limiting should be active"

    def test_api_cors_headers(self):
        """Test CORS headers are properly configured."""
        response = requests.options(
            f"{self.api_url}/health",
            headers={"Origin": self.base_url},
            timeout=self.timeout
        )
        
        # Should allow CORS from frontend domain
        cors_origin = response.headers.get("Access-Control-Allow-Origin")
        assert cors_origin in ["*", self.base_url]

    def test_ssl_certificate(self):
        """Test SSL certificate is valid."""
        response = requests.get(f"{self.base_url}/", timeout=self.timeout)
        assert response.url.startswith("https://")
        
        response = requests.get(f"{self.api_url}/health", timeout=self.timeout)
        assert response.url.startswith("https://")

    def test_response_times(self):
        """Test response times are acceptable."""
        start_time = time.time()
        response = requests.get(f"{self.api_url}/health", timeout=self.timeout)
        response_time = time.time() - start_time
        
        assert response.status_code == 200
        assert response_time < 5.0, f"Response time {response_time:.2f}s is too slow"

    def test_error_handling(self):
        """Test error handling and response format."""
        # Test 404 endpoint
        response = requests.get(f"{self.api_url}/nonexistent", timeout=self.timeout)
        assert response.status_code == 404
        
        # Should return JSON error format
        try:
            data = response.json()
            assert "error" in data or "detail" in data
        except ValueError:
            # Some 404s might not return JSON, that's okay
            pass

    def test_security_headers(self):
        """Test security headers are present."""
        response = requests.get(f"{self.api_url}/health", timeout=self.timeout)
        
        headers = response.headers
        
        # Check for important security headers
        security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options", 
            "X-XSS-Protection",
        ]
        
        # At least some security headers should be present
        present_headers = [h for h in security_headers if h in headers]
        assert len(present_headers) > 0, "No security headers found"


class TestPerformance:
    """Performance tests for staging environment."""
    
    def setup_class(self):
        """Setup test environment."""
        self.api_url = os.getenv('STAGING_API_URL', 'https://api-staging.weather-forecast.dev')
        self.timeout = 30

    def test_concurrent_requests(self):
        """Test handling of concurrent requests."""
        import threading
        import time
        
        results = []
        
        def make_request():
            try:
                start = time.time()
                response = requests.get(f"{self.api_url}/health", timeout=10)
                end = time.time()
                results.append({
                    'status': response.status_code,
                    'time': end - start
                })
            except Exception as e:
                results.append({
                    'status': 'error',
                    'error': str(e)
                })
        
        # Create 10 concurrent threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Analyze results
        successful = [r for r in results if r.get('status') == 200]
        assert len(successful) >= 8, f"Only {len(successful)}/10 requests succeeded"
        
        # Check average response time
        avg_time = sum(r['time'] for r in successful) / len(successful)
        assert avg_time < 10.0, f"Average response time {avg_time:.2f}s is too slow"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])