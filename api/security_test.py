#!/usr/bin/env python3
"""
Adelaide Weather Forecasting API - Security Validation Tests
===========================================================

Comprehensive security testing script to validate:
- Input validation and sanitization
- XSS protection
- SQL injection protection
- Request size limits
- Error message sanitization
- Authentication security

Author: Security Testing
Version: 1.0.0 - Production Security Validation
"""

import requests
import json
import time
from typing import Dict, List, Any, Optional

class SecurityTester:
    """Comprehensive security testing for the Weather API."""
    
    def __init__(self, base_url: str = "http://localhost:8000", token: str = "dev-token-change-in-production"):
        self.base_url = base_url
        self.token = token
        self.session = requests.Session()
        self.test_results = []
    
    def test_authentication_security(self):
        """Test authentication security measures."""
        print("🔐 Testing Authentication Security...")
        
        # Test 1: Missing token
        try:
            response = self.session.get(f"{self.base_url}/forecast")
            self.record_test("Missing Token", response.status_code == 401, 
                           f"Expected 401, got {response.status_code}")
        except Exception as e:
            self.record_test("Missing Token", False, str(e))
        
        # Test 2: Invalid token format
        try:
            headers = {"Authorization": "Bearer invalid<script>alert('xss')</script>"}
            response = self.session.get(f"{self.base_url}/forecast", headers=headers)
            self.record_test("Invalid Token Format", response.status_code == 401,
                           f"Expected 401, got {response.status_code}")
        except Exception as e:
            self.record_test("Invalid Token Format", False, str(e))
        
        # Test 3: Wrong token
        try:
            headers = {"Authorization": "Bearer wrong-token-12345"}
            response = self.session.get(f"{self.base_url}/forecast", headers=headers)
            self.record_test("Wrong Token", response.status_code == 401,
                           f"Expected 401, got {response.status_code}")
        except Exception as e:
            self.record_test("Wrong Token", False, str(e))
        
        # Test 4: Valid token
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.get(f"{self.base_url}/forecast", headers=headers)
            self.record_test("Valid Token", response.status_code == 200,
                           f"Expected 200, got {response.status_code}")
        except Exception as e:
            self.record_test("Valid Token", False, str(e))
    
    def test_input_validation(self):
        """Test input validation and sanitization."""
        print("🛡️ Testing Input Validation...")
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Test 1: Invalid horizon
        try:
            response = self.session.get(f"{self.base_url}/forecast?horizon=invalid", headers=headers)
            self.record_test("Invalid Horizon", response.status_code == 400,
                           f"Expected 400, got {response.status_code}")
        except Exception as e:
            self.record_test("Invalid Horizon", False, str(e))
        
        # Test 2: XSS in horizon
        try:
            xss_horizon = "<script>alert('xss')</script>"
            response = self.session.get(f"{self.base_url}/forecast?horizon={xss_horizon}", headers=headers)
            self.record_test("XSS in Horizon", response.status_code == 400,
                           f"Expected 400, got {response.status_code}")
        except Exception as e:
            self.record_test("XSS in Horizon", False, str(e))
        
        # Test 3: SQL injection in variables
        try:
            sql_vars = "t2m'; DROP TABLE users; --"
            response = self.session.get(f"{self.base_url}/forecast?vars={sql_vars}", headers=headers)
            self.record_test("SQL Injection in Variables", response.status_code == 400,
                           f"Expected 400, got {response.status_code}")
        except Exception as e:
            self.record_test("SQL Injection in Variables", False, str(e))
        
        # Test 4: Too many variables
        try:
            many_vars = ",".join([f"var{i}" for i in range(25)])
            response = self.session.get(f"{self.base_url}/forecast?vars={many_vars}", headers=headers)
            self.record_test("Too Many Variables", response.status_code == 400,
                           f"Expected 400, got {response.status_code}")
        except Exception as e:
            self.record_test("Too Many Variables", False, str(e))
        
        # Test 5: Valid inputs
        try:
            response = self.session.get(f"{self.base_url}/forecast?horizon=24h&vars=t2m,u10,v10", headers=headers)
            self.record_test("Valid Inputs", response.status_code == 200,
                           f"Expected 200, got {response.status_code}")
        except Exception as e:
            self.record_test("Valid Inputs", False, str(e))
    
    def test_xss_protection(self):
        """Test XSS protection mechanisms."""
        print("🔍 Testing XSS Protection...")
        headers = {"Authorization": f"Bearer {self.token}"}
        
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<iframe src='javascript:alert(\"xss\")'></iframe>",
            "onmouseover=alert('xss')",
            "%3Cscript%3Ealert('xss')%3C/script%3E"
        ]
        
        for i, payload in enumerate(xss_payloads):
            try:
                response = self.session.get(f"{self.base_url}/forecast?vars={payload}", headers=headers)
                success = response.status_code == 400
                if success and response.text:
                    # Check that the payload is not reflected unescaped
                    success = success and "<script>" not in response.text and "javascript:" not in response.text.lower()
                
                self.record_test(f"XSS Payload {i+1}", success,
                               f"Payload: {payload[:30]}...")
            except Exception as e:
                self.record_test(f"XSS Payload {i+1}", False, str(e))
    
    def test_sql_injection_protection(self):
        """Test SQL injection protection mechanisms."""
        print("💉 Testing SQL Injection Protection...")
        headers = {"Authorization": f"Bearer {self.token}"}
        
        sql_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "admin'--",
            "'; INSERT INTO users VALUES ('hacker'); --",
            "' OR 1=1 --",
            "\\'; exec master..xp_cmdshell 'ping 10.10.1.1'; --"
        ]
        
        for i, payload in enumerate(sql_payloads):
            try:
                response = self.session.get(f"{self.base_url}/forecast?vars=t2m{payload}", headers=headers)
                self.record_test(f"SQL Injection {i+1}", response.status_code == 400,
                               f"Payload: {payload[:30]}...")
            except Exception as e:
                self.record_test(f"SQL Injection {i+1}", False, str(e))
    
    def test_request_size_limits(self):
        """Test request size and parameter limits."""
        print("📏 Testing Request Size Limits...")
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Test 1: Very long parameter value
        try:
            long_value = "A" * 2000
            response = self.session.get(f"{self.base_url}/forecast?vars={long_value}", headers=headers)
            self.record_test("Long Parameter Value", response.status_code == 400,
                           f"Expected 400, got {response.status_code}")
        except Exception as e:
            self.record_test("Long Parameter Value", False, str(e))
        
        # Test 2: Many parameters
        try:
            many_params = "&".join([f"param{i}=value{i}" for i in range(100)])
            response = self.session.get(f"{self.base_url}/forecast?{many_params}", headers=headers)
            # This should either work or be rejected gracefully
            success = response.status_code in [200, 400, 413]
            self.record_test("Many Parameters", success,
                           f"Expected 200/400/413, got {response.status_code}")
        except Exception as e:
            self.record_test("Many Parameters", False, str(e))
    
    def test_error_message_sanitization(self):
        """Test that error messages don't leak sensitive information."""
        print("🚫 Testing Error Message Sanitization...")
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Test various invalid inputs and check error messages
        test_cases = [
            ("invalid_horizon", f"{self.base_url}/forecast?horizon=invalid"),
            ("malicious_vars", f"{self.base_url}/forecast?vars=<script>alert('xss')</script>"),
            ("nonexistent_endpoint", f"{self.base_url}/nonexistent_endpoint")
        ]
        
        for test_name, url in test_cases:
            try:
                response = self.session.get(url, headers=headers)
                if response.status_code >= 400:
                    error_text = response.text.lower()
                    # Check that common sensitive information is not leaked
                    sensitive_terms = ['traceback', 'stack trace', 'file not found', 
                                     'database', 'sql', 'internal error', 'exception']
                    
                    # Error message should not contain raw sensitive terms
                    leaked_info = any(term in error_text for term in sensitive_terms)
                    self.record_test(f"Error Sanitization - {test_name}", 
                                   not leaked_info or 'redacted' in error_text,
                                   f"Potential information leakage in error message")
            except Exception as e:
                self.record_test(f"Error Sanitization - {test_name}", False, str(e))
    
    def test_security_headers(self):
        """Test that security headers are present."""
        print("🛡️ Testing Security Headers...")
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            response = self.session.get(f"{self.base_url}/forecast", headers=headers)
            
            expected_headers = [
                'x-content-type-options',
                'x-frame-options', 
                'x-xss-protection',
                'content-security-policy'
            ]
            
            for header in expected_headers:
                present = header in [h.lower() for h in response.headers.keys()]
                self.record_test(f"Security Header - {header}", present,
                               f"Header {header} missing")
                
        except Exception as e:
            self.record_test("Security Headers", False, str(e))
    
    def test_health_endpoint_security(self):
        """Test health endpoint doesn't leak sensitive information."""
        print("❤️ Testing Health Endpoint Security...")
        
        try:
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code == 200:
                health_data = response.json()
                # Health endpoint should not expose sensitive details in production
                sensitive_fields = ['database_connection_string', 'api_keys', 'secrets']
                exposed = any(field in str(health_data).lower() for field in sensitive_fields)
                self.record_test("Health Info Exposure", not exposed,
                               "Health endpoint may expose sensitive information")
            else:
                self.record_test("Health Endpoint Access", response.status_code == 200,
                               f"Expected 200, got {response.status_code}")
        except Exception as e:
            self.record_test("Health Endpoint Security", False, str(e))
    
    def record_test(self, test_name: str, passed: bool, details: str = ""):
        """Record test result."""
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": time.time()
        })
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} {test_name}: {details}")
    
    def run_all_tests(self):
        """Run all security tests."""
        print("🚀 Starting Comprehensive Security Testing...")
        print("=" * 60)
        
        self.test_authentication_security()
        print()
        self.test_input_validation()
        print()
        self.test_xss_protection()
        print()
        self.test_sql_injection_protection()
        print()
        self.test_request_size_limits()
        print()
        self.test_error_message_sanitization()
        print()
        self.test_security_headers()
        print()
        self.test_health_endpoint_security()
        
        # Summary
        print("\n" + "=" * 60)
        print("🏁 SECURITY TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["passed"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: ✅ {passed_tests}")
        print(f"Failed: ❌ {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n🚨 FAILED TESTS:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"  ❌ {result['test']}: {result['details']}")
        
        return failed_tests == 0

if __name__ == "__main__":
    # Test against the running test API
    tester = SecurityTester("http://localhost:8000")
    
    print("Adelaide Weather Forecasting API - Security Test Suite")
    print("=====================================================")
    print("Testing comprehensive input validation and security measures...")
    print()
    
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 ALL SECURITY TESTS PASSED!")
        print("The API demonstrates robust security measures.")
    else:
        print("\n⚠️  SOME SECURITY TESTS FAILED!")
        print("Review the failed tests and strengthen security measures.")
    
    exit(0 if success else 1)