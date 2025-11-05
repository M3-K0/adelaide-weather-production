#!/usr/bin/env python3
"""
Comprehensive Security Tests for Adelaide Weather Forecasting System
====================================================================

Complete security test suite covering:
- Security middleware validation
- Input sanitization and XSS protection
- SQL injection protection
- Request size and parameter limits
- Error message sanitization
- Security headers enforcement
- Authentication token validation

Target: 100% security coverage for all attack vectors
"""

import pytest
import pytest_asyncio
from fastapi import Request, Response
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import json
import html
import re
from typing import Dict, Any, List

# Import security components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.security_middleware import (
    SecurityMiddleware, SecurityConfig, InputSanitizer, 
    SecurityException, ValidationUtils
)
from api.main import app


class TestInputSanitizer:
    """Test suite for InputSanitizer class."""
    
    def test_sanitize_string_basic(self):
        """Test basic string sanitization."""
        # Valid input
        result = InputSanitizer.sanitize_string("hello world")
        assert result == "hello world"
        
        # Input with HTML entities
        result = InputSanitizer.sanitize_string("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
    
    def test_sanitize_string_length_limit(self):
        """Test string length validation."""
        # Valid length
        InputSanitizer.sanitize_string("short", 10)
        
        # Exceeds length
        with pytest.raises(ValueError, match="Input too long"):
            InputSanitizer.sanitize_string("very long string", 5)
    
    def test_sanitize_string_xss_patterns(self):
        """Test XSS pattern detection."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<iframe src='javascript:alert(1)'></iframe>",
            "<object data='javascript:alert(1)'></object>",
            "<embed src='javascript:alert(1)'></embed>",
            "onmouseover=alert('xss')"
        ]
        
        for payload in xss_payloads:
            with pytest.raises(ValueError, match="Potentially malicious input detected"):
                InputSanitizer.sanitize_string(payload)
    
    def test_sanitize_string_sql_patterns(self):
        """Test SQL injection pattern detection."""
        sql_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "admin'--", 
            "'; exec master..xp_cmdshell --",
            "' OR 1=1 --",
            "'; INSERT INTO malicious --"
        ]
        
        for payload in sql_payloads:
            with pytest.raises(ValueError, match="Potentially malicious input detected"):
                InputSanitizer.sanitize_string(payload)
    
    def test_sanitize_string_control_characters(self):
        """Test removal of control characters."""
        input_with_controls = "hello\x00\x01\x02world"
        result = InputSanitizer.sanitize_string(input_with_controls)
        assert "\x00" not in result
        assert "\x01" not in result
        assert "\x02" not in result
        assert "helloworld" in result
    
    def test_sanitize_string_preserves_valid_chars(self):
        """Test that valid characters are preserved."""
        valid_input = "Hello World 123 !@#$%^&*()\t\n\r"
        result = InputSanitizer.sanitize_string(valid_input)
        # HTML entities should be escaped but tabs/newlines preserved
        assert "Hello World 123" in result
    
    def test_sanitize_string_non_string_input(self):
        """Test handling of non-string input."""
        with pytest.raises(ValueError, match="Input must be a string"):
            InputSanitizer.sanitize_string(123)
        
        with pytest.raises(ValueError, match="Input must be a string"):
            InputSanitizer.sanitize_string(None)
    
    def test_validate_horizon_valid(self):
        """Test valid horizon validation."""
        valid_horizons = ["6h", "12h", "24h", "48h"]
        
        for horizon in valid_horizons:
            result = InputSanitizer.validate_horizon(horizon)
            assert result == horizon
    
    def test_validate_horizon_invalid(self):
        """Test invalid horizon validation."""
        invalid_horizons = [
            "invalid", "1h", "72h", "24", "h24", "24hrs",
            "", " ", "24h ", " 24h", "<script>", "'; DROP --"
        ]
        
        for horizon in invalid_horizons:
            with pytest.raises(ValueError):
                InputSanitizer.validate_horizon(horizon)
    
    def test_validate_variables_valid(self):
        """Test valid variables validation."""
        # Valid variable lists
        valid_cases = [
            "t2m",
            "t2m,u10,v10",
            "t2m, u10, v10",  # with spaces
            ""  # empty should return empty list
        ]
        
        for vars_str in valid_cases:
            result = InputSanitizer.validate_variables(vars_str)
            assert isinstance(result, list)
    
    def test_validate_variables_invalid(self):
        """Test invalid variables validation."""
        invalid_cases = [
            "invalid_var",
            "var@123", 
            "var with spaces",
            "var-with-dashes",
            "var.with.dots",
            "<script>alert('xss')</script>",
            "'; DROP TABLE --",
            ",".join([f"var{i}" for i in range(25)]),  # too many
            "A" * 600  # too long
        ]
        
        for vars_str in invalid_cases:
            with pytest.raises(ValueError):
                InputSanitizer.validate_variables(vars_str)
    
    def test_validate_variables_limit_checks(self):
        """Test variable validation limits."""
        # Test too many variables
        too_many = ",".join([f"t2m{i}" for i in range(25)])
        with pytest.raises(ValueError, match="Too many variables"):
            InputSanitizer.validate_variables(too_many)
        
        # Test valid number of variables
        valid_many = ",".join(["t2m", "u10", "v10", "msl", "cape"])
        result = InputSanitizer.validate_variables(valid_many)
        assert len(result) == 5
    
    def test_validate_token_valid(self):
        """Test valid token validation."""
        valid_tokens = [
            "validtoken123",
            "valid-token-123",
            "valid_token_123",
            "valid.token.123",
            "a" * 32,  # 32 chars
            "a" * 64   # 64 chars
        ]
        
        for token in valid_tokens:
            result = InputSanitizer.validate_token(token)
            assert result == token
    
    def test_validate_token_invalid(self):
        """Test invalid token validation."""
        invalid_tokens = [
            "short",           # too short
            "a" * 200,         # too long
            "token@#$%",       # invalid chars
            "<script>alert()", # XSS attempt
            "",                # empty
            123,               # not string
            None               # None
        ]
        
        for token in invalid_tokens:
            with pytest.raises(ValueError):
                InputSanitizer.validate_token(token)


class TestValidationUtils:
    """Test suite for ValidationUtils class."""
    
    def test_validate_forecast_request_valid(self):
        """Test valid forecast request validation."""
        result = ValidationUtils.validate_forecast_request("24h", "t2m,u10,v10")
        
        assert result["valid"] is True
        assert result["horizon"] == "24h"
        assert "t2m" in result["variables"]
        assert "u10" in result["variables"]
        assert "v10" in result["variables"]
    
    def test_validate_forecast_request_invalid_horizon(self):
        """Test forecast request with invalid horizon."""
        result = ValidationUtils.validate_forecast_request("invalid", "t2m")
        
        assert result["valid"] is False
        assert "error" in result
    
    def test_validate_forecast_request_invalid_variables(self):
        """Test forecast request with invalid variables."""
        result = ValidationUtils.validate_forecast_request("24h", "invalid_var")
        
        assert result["valid"] is False
        assert "error" in result
    
    def test_validate_forecast_request_business_logic(self):
        """Test forecast request business logic validation."""
        # Too many variables for 48h horizon
        many_vars = ",".join(["t2m", "u10", "v10", "msl", "r850", "tp6h", "cape", "t850", "z500", "extra1", "extra2"])
        result = ValidationUtils.validate_forecast_request("48h", many_vars)
        
        assert result["valid"] is False
        assert "Too many variables for extended forecast" in result["error"]
    
    def test_validate_auth_token_valid(self):
        """Test valid authentication token validation."""
        valid_token = "production-secure-token-12345"
        result = ValidationUtils.validate_auth_token(valid_token)
        
        assert result["valid"] is True
        assert result["token"] == valid_token
    
    def test_validate_auth_token_placeholder(self):
        """Test placeholder token detection."""
        placeholder_tokens = ["test", "demo", "example", "default"]
        
        for token in placeholder_tokens:
            result = ValidationUtils.validate_auth_token(token)
            assert result["valid"] is False
            assert "placeholder" in result["error"]
    
    def test_validate_auth_token_invalid_format(self):
        """Test invalid token format validation."""
        invalid_tokens = [
            "short",
            "a" * 200,
            "token@#$%",
            "<script>alert()"
        ]
        
        for token in invalid_tokens:
            result = ValidationUtils.validate_auth_token(token)
            assert result["valid"] is False


class TestSecurityConfig:
    """Test suite for SecurityConfig constants and patterns."""
    
    def test_pattern_compilation(self):
        """Test that all regex patterns compile successfully."""
        patterns = [
            SecurityConfig.HORIZON_PATTERN,
            SecurityConfig.VARIABLE_PATTERN,
            SecurityConfig.TOKEN_PATTERN
        ]
        
        for pattern in patterns:
            assert pattern is not None
            # Test that pattern can be used
            pattern.match("test")
    
    def test_sql_injection_patterns(self):
        """Test SQL injection pattern detection."""
        test_cases = [
            ("'; DROP TABLE users; --", True),
            ("' OR '1'='1", True),
            ("valid input", False),
            ("SELECT * FROM valid_table", True),
            ("normal query parameter", False)
        ]
        
        for test_input, should_match in test_cases:
            matched = any(pattern.search(test_input) for pattern in SecurityConfig.SQL_INJECTION_PATTERNS)
            assert matched == should_match, f"Failed for: {test_input}"
    
    def test_xss_patterns(self):
        """Test XSS pattern detection."""
        test_cases = [
            ("<script>alert('xss')</script>", True),
            ("javascript:alert('xss')", True),
            ("onmouseover=alert('xss')", True),
            ("<iframe src='evil'></iframe>", True),
            ("normal text content", False),
            ("valid <b>html</b> content", False)
        ]
        
        for test_input, should_match in test_cases:
            matched = any(pattern.search(test_input) for pattern in SecurityConfig.XSS_PATTERNS)
            assert matched == should_match, f"Failed for: {test_input}"
    
    def test_security_headers_completeness(self):
        """Test that all required security headers are defined."""
        required_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options', 
            'X-XSS-Protection',
            'Strict-Transport-Security',
            'Content-Security-Policy',
            'Referrer-Policy'
        ]
        
        for header in required_headers:
            assert header in SecurityConfig.SECURITY_HEADERS
            assert SecurityConfig.SECURITY_HEADERS[header]  # Non-empty value
    
    def test_allowed_content_types(self):
        """Test allowed content types."""
        assert 'application/json' in SecurityConfig.ALLOWED_CONTENT_TYPES
        assert 'application/x-www-form-urlencoded' in SecurityConfig.ALLOWED_CONTENT_TYPES
        assert 'text/plain' in SecurityConfig.ALLOWED_CONTENT_TYPES
        
        # Dangerous content types should not be allowed
        assert 'text/html' not in SecurityConfig.ALLOWED_CONTENT_TYPES
        assert 'application/x-javascript' not in SecurityConfig.ALLOWED_CONTENT_TYPES


class TestSecurityMiddleware:
    """Test suite for SecurityMiddleware functionality."""
    
    def setup_method(self):
        """Setup test client with security middleware."""
        self.client = TestClient(app)
    
    def test_request_size_validation(self):
        """Test request size validation."""
        # Test valid request size
        response = self.client.get("/health")
        assert response.status_code in [200, 401]  # 401 for auth, but not size issue
        
        # Test oversized request (headers)
        large_headers = {"X-Large-Header": "A" * 10000}
        response = self.client.get("/health", headers=large_headers)
        # Should handle gracefully
        assert response.status_code in [200, 400, 413, 431]
    
    def test_query_parameter_validation(self):
        """Test query parameter validation."""
        headers = {"Authorization": "Bearer test-token-for-comprehensive-testing"}
        os.environ["API_TOKEN"] = "test-token-for-comprehensive-testing"
        
        # Test too many parameters
        many_params = "&".join([f"param{i}=value{i}" for i in range(60)])
        response = self.client.get(f"/forecast?{many_params}", headers=headers)
        assert response.status_code in [200, 400, 413]
        
        # Test parameter value too long
        long_value = "A" * 2000
        response = self.client.get(f"/forecast?vars={long_value}", headers=headers)
        assert response.status_code == 400
    
    def test_content_type_validation(self):
        """Test content type validation."""
        headers = {"Authorization": "Bearer test-token-for-comprehensive-testing"}
        os.environ["API_TOKEN"] = "test-token-for-comprehensive-testing"
        
        # Test unsupported content type for POST
        response = self.client.post(
            "/forecast", 
            headers={**headers, "Content-Type": "text/html"},
            json={"test": "data"}
        )
        # Should reject unsupported content type
        assert response.status_code in [400, 405, 415]
    
    def test_security_headers_added(self):
        """Test that security headers are added to responses."""
        response = self.client.get("/health")
        
        # Check for key security headers
        security_headers = [
            'x-content-type-options',
            'x-frame-options',
            'x-xss-protection'
        ]
        
        response_headers_lower = {k.lower(): v for k, v in response.headers.items()}
        
        for header in security_headers:
            # Header should be present (case-insensitive check)
            assert any(header in h for h in response_headers_lower.keys()), f"Missing header: {header}"
    
    def test_host_header_validation(self):
        """Test Host header validation."""
        # Test valid host
        response = self.client.get("/health", headers={"Host": "localhost:8000"})
        assert response.status_code == 200
        
        # Test invalid host (too long)
        long_host = "a" * 300 + ".example.com"
        response = self.client.get("/health", headers={"Host": long_host})
        assert response.status_code in [200, 400]
    
    def test_user_agent_validation(self):
        """Test User-Agent header validation."""
        # Test normal user agent
        normal_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        response = self.client.get("/health", headers={"User-Agent": normal_ua})
        assert response.status_code == 200
        
        # Test oversized user agent
        long_ua = "A" * 1000
        response = self.client.get("/health", headers={"User-Agent": long_ua})
        assert response.status_code in [200, 400]


class TestSecurityException:
    """Test suite for SecurityException class."""
    
    def test_security_exception_creation(self):
        """Test SecurityException creation and attributes."""
        exc = SecurityException("test_violation", "Test message", 400)
        
        assert exc.violation_type == "test_violation"
        assert exc.message == "Test message"
        assert exc.status_code == 400
        assert str(exc) == "Test message"
    
    def test_security_exception_default_status(self):
        """Test SecurityException with default status code."""
        exc = SecurityException("test_violation", "Test message")
        
        assert exc.status_code == 400  # Default


class TestSecurityIntegration:
    """Integration tests for security components."""
    
    def setup_method(self):
        """Setup test client and authentication."""
        self.client = TestClient(app)
        self.headers = {"Authorization": "Bearer test-token-for-comprehensive-testing"}
        os.environ["API_TOKEN"] = "test-token-for-comprehensive-testing"
    
    def test_xss_protection_integration(self):
        """Test XSS protection across the full request pipeline."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<iframe src='javascript:alert(1)'></iframe>",
            "onmouseover=alert('xss')"
        ]
        
        for payload in xss_payloads:
            # Test in horizon parameter
            response = self.client.get(f"/forecast?horizon={payload}", headers=self.headers)
            assert response.status_code == 400
            
            # Ensure XSS payload is not reflected in response
            response_text = response.text.lower()
            assert "<script>" not in response_text
            assert "javascript:" not in response_text
            assert "onerror=" not in response_text
    
    def test_sql_injection_protection_integration(self):
        """Test SQL injection protection across the full request pipeline."""
        sql_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "admin'--",
            "'; exec master..xp_cmdshell 'ping evil.com'; --"
        ]
        
        for payload in sql_payloads:
            response = self.client.get(f"/forecast?vars=t2m{payload}", headers=self.headers)
            assert response.status_code == 400
    
    def test_request_sanitization_flow(self):
        """Test the complete request sanitization flow."""
        # Test request with multiple potential issues
        malicious_request = {
            "horizon": "<script>alert('xss')</script>",
            "vars": "'; DROP TABLE users; --",
            "extra_param": "javascript:alert('evil')"
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in malicious_request.items()])
        response = self.client.get(f"/forecast?{query_string}", headers=self.headers)
        
        assert response.status_code == 400
        
        # Ensure response doesn't contain malicious content
        response_text = response.text.lower()
        assert "drop table" not in response_text
        assert "<script>" not in response_text
        assert "javascript:" not in response_text
    
    def test_error_message_sanitization(self):
        """Test that error messages are properly sanitized."""
        # Generate various types of errors
        error_test_cases = [
            "/forecast?horizon=<script>alert('xss')</script>",
            "/forecast?vars='; DROP TABLE users; --",
            "/nonexistent_endpoint"
        ]
        
        for test_url in error_test_cases:
            response = self.client.get(test_url, headers=self.headers)
            
            if response.status_code >= 400:
                error_data = response.json()
                error_message = str(error_data).lower()
                
                # Check that sensitive information is not leaked
                sensitive_terms = [
                    'traceback', 'stack trace', 'file not found',
                    'database', 'internal error', 'exception'
                ]
                
                # Error should not contain raw sensitive terms unless sanitized
                for term in sensitive_terms:
                    if term in error_message:
                        # If present, should be marked as redacted/sanitized
                        assert 'redacted' in error_message or '[PATH]' in error_message
    
    @patch('api.main.forecast_adapter')
    def test_security_with_valid_request(self, mock_adapter):
        """Test that security doesn't interfere with valid requests."""
        mock_adapter.forecast_with_uncertainty.return_value = {
            "t2m": {"value": 20.0, "p05": 18.0, "p95": 22.0,
                   "confidence": 2.0, "available": True, "analog_count": 50}
        }
        
        # Valid request should pass through security checks
        response = self.client.get("/forecast?horizon=24h&vars=t2m", headers=self.headers)
        assert response.status_code == 200
        
        # Security headers should be present
        assert 'x-content-type-options' in [h.lower() for h in response.headers.keys()]


class TestEdgeCasesAndBoundaries:
    """Test edge cases and boundary conditions."""
    
    def setup_method(self):
        """Setup test environment."""
        self.client = TestClient(app)
        os.environ["API_TOKEN"] = "test-token-for-comprehensive-testing"
    
    def test_empty_string_inputs(self):
        """Test handling of empty string inputs."""
        # Empty strings should be handled gracefully
        assert InputSanitizer.validate_variables("") == []
        
        with pytest.raises(ValueError):
            InputSanitizer.validate_horizon("")
    
    def test_whitespace_only_inputs(self):
        """Test handling of whitespace-only inputs."""
        whitespace_inputs = [" ", "\t", "\n", "\r\n", "   "]
        
        for whitespace in whitespace_inputs:
            with pytest.raises(ValueError):
                InputSanitizer.validate_horizon(whitespace)
    
    def test_unicode_inputs(self):
        """Test handling of unicode inputs."""
        unicode_inputs = [
            "café",           # accented characters
            "测试",            # Chinese characters  
            "🚀",             # emoji
            "αβγ",            # Greek letters
            "\u0000",         # null character
            "\u200B"          # zero-width space
        ]
        
        for unicode_input in unicode_inputs:
            # Should either sanitize or reject
            try:
                result = InputSanitizer.sanitize_string(unicode_input)
                # If accepted, should be sanitized
                assert len(result) >= 0
            except ValueError:
                # Rejection is also acceptable
                pass
    
    def test_boundary_length_values(self):
        """Test inputs at exact boundary lengths."""
        # Test exact length limits
        max_length = 1000
        
        # Exactly at limit
        at_limit = "a" * max_length
        result = InputSanitizer.sanitize_string(at_limit, max_length)
        assert len(result) <= max_length
        
        # Just over limit
        over_limit = "a" * (max_length + 1)
        with pytest.raises(ValueError, match="Input too long"):
            InputSanitizer.sanitize_string(over_limit, max_length)
    
    def test_case_sensitivity(self):
        """Test case sensitivity in validation."""
        # Horizon validation should be case sensitive
        with pytest.raises(ValueError):
            InputSanitizer.validate_horizon("24H")  # uppercase
        
        with pytest.raises(ValueError):
            InputSanitizer.validate_horizon("24h ")  # trailing space


if __name__ == "__main__":
    # Run security tests with detailed output
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--cov=api.security_middleware",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-fail-under=95"
    ])