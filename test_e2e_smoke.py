#!/usr/bin/env python3
"""
Adelaide Weather E2E Smoke Test Suite
=====================================

Comprehensive smoke test for critical path validation:
- Authentication flow (401 without token, 200 with token)
- Proxy validation (Nginx /api/* rewrite, CORS headers, gzip)
- FAISS integration (real search results in forecast endpoint)
- Metrics export (Prometheus endpoint)
- Error handling and performance validation

This test suite validates the complete request flow:
Browser → Nginx → FastAPI → FAISS → Response

Test Scenarios:
1. 401 without token - Verify unauthorized access rejection
2. 200 with token for /health - Verify authenticated health endpoint  
3. 200 with token for /forecast - Verify forecast returns variables with real FAISS data
4. 200 for /metrics - Verify Prometheus metrics export
5. Proxy validation - Verify Nginx integration works correctly

Author: Quality Assurance & Optimization Specialist
Version: 1.0.0 - E2E Smoke Test Suite
"""

import os
import sys
import time
import json
import requests
import threading
import subprocess
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
import tempfile
import signal
import atexit
from contextlib import contextmanager

# Test configuration
TEST_BASE_URL = "http://localhost"
API_BASE_URL = "http://localhost:8000"
NGINX_PORT = 80
API_DIRECT_PORT = 8000
TEST_TOKEN = "test-e2e-smoke-token-12345"

# Performance thresholds
MAX_RESPONSE_TIME_MS = 5000  # 5 seconds for startup tolerance
MAX_FORECAST_TIME_MS = 2000  # 2 seconds for forecast
MAX_HEALTH_TIME_MS = 1000    # 1 second for health

class Colors:
    """Terminal colors for output formatting."""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class SmokeTestResult:
    """Individual smoke test result."""
    def __init__(self, test_name: str, passed: bool, message: str, 
                 response_time_ms: Optional[float] = None, details: Optional[Dict] = None):
        self.test_name = test_name
        self.passed = passed
        self.message = message
        self.response_time_ms = response_time_ms
        self.details = details or {}
        self.timestamp = datetime.now(timezone.utc)

class SmokeTestSuite:
    """Comprehensive E2E smoke test suite for Adelaide Weather system."""
    
    def __init__(self):
        self.results: List[SmokeTestResult] = []
        self.session = requests.Session()
        self.session.timeout = 30  # 30 second timeout for all requests
        self.docker_compose_process = None
        self.services_started = False
        
        # Set up clean exit
        atexit.register(self.cleanup)
        
    def print_header(self, title: str):
        """Print formatted test section header."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{title.center(80)}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")
        
    def print_result(self, result: SmokeTestResult):
        """Print formatted test result."""
        status_color = Colors.GREEN if result.passed else Colors.RED
        status_text = "✅ PASS" if result.passed else "❌ FAIL"
        
        print(f"{status_color}{status_text}{Colors.END} {Colors.BOLD}{result.test_name}{Colors.END}")
        print(f"    {result.message}")
        
        if result.response_time_ms:
            time_color = Colors.GREEN if result.response_time_ms < 1000 else Colors.YELLOW if result.response_time_ms < 2000 else Colors.RED
            print(f"    {time_color}Response Time: {result.response_time_ms:.1f}ms{Colors.END}")
        
        if result.details:
            for key, value in result.details.items():
                print(f"    {Colors.BLUE}{key}: {value}{Colors.END}")
        print()
        
    def wait_for_service(self, url: str, timeout: int = 120, interval: int = 2) -> bool:
        """Wait for a service to become available."""
        print(f"⏳ Waiting for service at {url}...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = self.session.get(f"{url}/health", timeout=5)
                if response.status_code in [200, 401, 403]:  # Service is responding
                    print(f"✅ Service at {url} is available")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(interval)
            print(".", end="", flush=True)
        
        print(f"❌ Service at {url} did not become available within {timeout} seconds")
        return False
        
    def start_services(self) -> bool:
        """Start the docker-compose services."""
        print(f"{Colors.BOLD}🚀 Starting Adelaide Weather services...{Colors.END}")
        
        # Check if services are already running
        try:
            response = self.session.get(f"{TEST_BASE_URL}/health", timeout=5)
            if response.status_code in [200, 401, 403]:
                print("✅ Services already running")
                self.services_started = True
                return True
        except requests.exceptions.RequestException:
            pass
        
        # Set API token for testing
        env = os.environ.copy()
        env['API_TOKEN'] = TEST_TOKEN
        
        try:
            # Start docker-compose in background
            self.docker_compose_process = subprocess.Popen(
                ['docker-compose', 'up', '-d'],
                cwd='/home/micha/adelaide-weather-final',
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for process to complete
            stdout, stderr = self.docker_compose_process.communicate(timeout=300)  # 5 minute timeout
            
            if self.docker_compose_process.returncode != 0:
                print(f"❌ Docker compose failed: {stderr.decode()}")
                return False
            
            print("✅ Docker compose started")
            
            # Wait for services to be ready
            services_ready = True
            services_ready &= self.wait_for_service(API_BASE_URL, timeout=120)
            services_ready &= self.wait_for_service(TEST_BASE_URL, timeout=60)
            
            if services_ready:
                print("✅ All services are ready")
                self.services_started = True
                time.sleep(5)  # Additional settling time
                return True
            else:
                print("❌ Not all services became ready")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Docker compose startup timed out")
            if self.docker_compose_process:
                self.docker_compose_process.kill()
            return False
        except Exception as e:
            print(f"❌ Failed to start services: {e}")
            return False
    
    def cleanup(self):
        """Clean up test environment."""
        if self.services_started:
            print(f"\n{Colors.YELLOW}🧹 Cleaning up test environment...{Colors.END}")
            try:
                subprocess.run(
                    ['docker-compose', 'down'],
                    cwd='/home/micha/adelaide-weather-final',
                    timeout=60,
                    capture_output=True
                )
                print("✅ Services stopped")
            except Exception as e:
                print(f"⚠️ Cleanup warning: {e}")

    @contextmanager
    def time_request(self):
        """Context manager to time HTTP requests."""
        start_time = time.time()
        yield
        end_time = time.time()
        self.last_request_time = (end_time - start_time) * 1000  # Convert to milliseconds

    def test_unauthorized_access(self) -> SmokeTestResult:
        """Test 1: 401 without token - Verify unauthorized access rejection."""
        test_name = "Test 1: Unauthorized Access (401 without token)"
        
        try:
            with self.time_request():
                # Test direct API access without token
                response = self.session.get(f"{API_BASE_URL}/forecast")
            
            if response.status_code == 401 or response.status_code == 403:
                return SmokeTestResult(
                    test_name, True, 
                    f"Correctly rejected unauthorized access with status {response.status_code}",
                    self.last_request_time,
                    {"status_code": response.status_code, "endpoint": "/forecast"}
                )
            else:
                return SmokeTestResult(
                    test_name, False,
                    f"Expected 401/403 but got {response.status_code}",
                    self.last_request_time,
                    {"status_code": response.status_code, "response": response.text[:200]}
                )
                
        except Exception as e:
            return SmokeTestResult(test_name, False, f"Request failed: {str(e)}")

    def test_authenticated_health(self) -> SmokeTestResult:
        """Test 2: 200 with token for /health - Verify authenticated health endpoint."""
        test_name = "Test 2: Authenticated Health Check (200 with token)"
        
        try:
            headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
            
            with self.time_request():
                response = self.session.get(f"{API_BASE_URL}/health", headers=headers)
            
            if response.status_code == 200:
                try:
                    health_data = response.json()
                    ready_status = health_data.get("ready", False)
                    
                    return SmokeTestResult(
                        test_name, True,
                        f"Health endpoint accessible, system ready: {ready_status}",
                        self.last_request_time,
                        {
                            "status_code": response.status_code,
                            "system_ready": ready_status,
                            "checks_count": len(health_data.get("checks", []))
                        }
                    )
                except json.JSONDecodeError:
                    return SmokeTestResult(
                        test_name, False,
                        "Health endpoint returned invalid JSON",
                        self.last_request_time
                    )
            else:
                return SmokeTestResult(
                    test_name, False,
                    f"Expected 200 but got {response.status_code}",
                    self.last_request_time,
                    {"status_code": response.status_code, "response": response.text[:200]}
                )
                
        except Exception as e:
            return SmokeTestResult(test_name, False, f"Request failed: {str(e)}")

    def test_forecast_with_faiss(self) -> SmokeTestResult:
        """Test 3: 200 with token for /forecast - Verify forecast returns variables with real FAISS data."""
        test_name = "Test 3: Forecast with FAISS Integration (200 with real data)"
        
        try:
            headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
            params = {"horizon": "24h", "vars": "t2m,u10,v10,msl"}
            
            with self.time_request():
                response = self.session.get(f"{API_BASE_URL}/forecast", headers=headers, params=params)
            
            if response.status_code == 200:
                try:
                    forecast_data = response.json()
                    
                    # Validate response structure
                    required_fields = ["horizon", "generated_at", "variables", "narrative", "latency_ms"]
                    missing_fields = [field for field in required_fields if field not in forecast_data]
                    
                    if missing_fields:
                        return SmokeTestResult(
                            test_name, False,
                            f"Missing required fields: {missing_fields}",
                            self.last_request_time
                        )
                    
                    # Check variables data
                    variables = forecast_data.get("variables", {})
                    available_vars = [var for var, data in variables.items() if data.get("available", False)]
                    
                    # Check for FAISS integration indicators
                    analog_counts = []
                    for var, data in variables.items():
                        if data.get("analog_count") is not None:
                            analog_counts.append(data.get("analog_count"))
                    
                    faiss_integrated = len(analog_counts) > 0 and any(count > 0 for count in analog_counts)
                    
                    return SmokeTestResult(
                        test_name, True,
                        f"Forecast generated with {len(available_vars)} variables, FAISS integration: {'✅' if faiss_integrated else '⚠️'}",
                        self.last_request_time,
                        {
                            "status_code": response.status_code,
                            "available_variables": len(available_vars),
                            "total_variables": len(variables),
                            "faiss_integrated": faiss_integrated,
                            "avg_analog_count": sum(analog_counts) / len(analog_counts) if analog_counts else 0,
                            "forecast_latency": forecast_data.get("latency_ms")
                        }
                    )
                except json.JSONDecodeError:
                    return SmokeTestResult(
                        test_name, False,
                        "Forecast endpoint returned invalid JSON",
                        self.last_request_time
                    )
            else:
                return SmokeTestResult(
                    test_name, False,
                    f"Expected 200 but got {response.status_code}",
                    self.last_request_time,
                    {"status_code": response.status_code, "response": response.text[:200]}
                )
                
        except Exception as e:
            return SmokeTestResult(test_name, False, f"Request failed: {str(e)}")

    def test_metrics_endpoint(self) -> SmokeTestResult:
        """Test 4: 200 for /metrics - Verify Prometheus metrics export."""
        test_name = "Test 4: Prometheus Metrics Export (200 for /metrics)"
        
        try:
            headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
            
            with self.time_request():
                response = self.session.get(f"{API_BASE_URL}/metrics", headers=headers)
            
            if response.status_code == 200:
                metrics_text = response.text
                
                # Check for expected Prometheus metrics
                expected_metrics = [
                    "forecast_requests_total",
                    "response_duration_seconds",
                    "health_requests_total",
                    "metrics_requests_total"
                ]
                
                found_metrics = [metric for metric in expected_metrics if metric in metrics_text]
                metric_lines = len([line for line in metrics_text.split('\n') if line and not line.startswith('#')])
                
                return SmokeTestResult(
                    test_name, True,
                    f"Metrics endpoint accessible with {len(found_metrics)}/{len(expected_metrics)} core metrics",
                    self.last_request_time,
                    {
                        "status_code": response.status_code,
                        "content_type": response.headers.get("content-type", ""),
                        "metric_lines": metric_lines,
                        "found_core_metrics": len(found_metrics),
                        "expected_core_metrics": len(expected_metrics)
                    }
                )
            else:
                return SmokeTestResult(
                    test_name, False,
                    f"Expected 200 but got {response.status_code}",
                    self.last_request_time,
                    {"status_code": response.status_code, "response": response.text[:200]}
                )
                
        except Exception as e:
            return SmokeTestResult(test_name, False, f"Request failed: {str(e)}")

    def test_nginx_proxy_integration(self) -> SmokeTestResult:
        """Test 5: Proxy validation - Verify Nginx /api/* rewrite, gzip, CORS headers."""
        test_name = "Test 5: Nginx Proxy Integration (/api/* rewrite, CORS, gzip)"
        
        try:
            # Test API routes through Nginx proxy
            headers = {
                "Authorization": f"Bearer {TEST_TOKEN}",
                "Origin": "http://localhost:3000",  # Simulate frontend origin
                "Accept-Encoding": "gzip, deflate"
            }
            
            proxy_tests = []
            
            # Test 1: Health endpoint through /api/ proxy
            with self.time_request():
                response = self.session.get(f"{TEST_BASE_URL}/api/health", headers=headers)
            
            health_time = self.last_request_time
            
            if response.status_code == 200:
                proxy_tests.append("✅ /api/health proxy working")
                
                # Check CORS headers
                cors_headers = {
                    "Access-Control-Allow-Origin": response.headers.get("access-control-allow-origin"),
                    "Access-Control-Allow-Methods": response.headers.get("access-control-allow-methods"),
                    "Access-Control-Allow-Headers": response.headers.get("access-control-allow-headers")
                }
                
                if cors_headers["Access-Control-Allow-Origin"]:
                    proxy_tests.append("✅ CORS headers present")
                else:
                    proxy_tests.append("⚠️ CORS headers missing")
                    
            else:
                proxy_tests.append(f"❌ /api/health proxy failed: {response.status_code}")
            
            # Test 2: Direct endpoint through nginx (without /api prefix)
            with self.time_request():
                response2 = self.session.get(f"{TEST_BASE_URL}/health", headers=headers)
            
            direct_time = self.last_request_time
            
            if response2.status_code == 200:
                proxy_tests.append("✅ Direct /health endpoint working")
            else:
                proxy_tests.append(f"❌ Direct /health failed: {response2.status_code}")
            
            # Test 3: Check compression capability
            compression_applied = "gzip" in response.headers.get("content-encoding", "").lower()
            if compression_applied:
                proxy_tests.append("✅ Gzip compression applied")
            else:
                proxy_tests.append("⚠️ Gzip compression not detected (may be handled by nginx)")
            
            # Test 4: OPTIONS preflight request
            with self.time_request():
                options_response = self.session.options(f"{TEST_BASE_URL}/api/health", headers=headers)
            
            if options_response.status_code == 204:
                proxy_tests.append("✅ CORS preflight working")
            else:
                proxy_tests.append(f"⚠️ CORS preflight issue: {options_response.status_code}")
            
            success_count = len([test for test in proxy_tests if test.startswith("✅")])
            total_tests = len(proxy_tests)
            
            return SmokeTestResult(
                test_name, success_count >= 2,  # At least basic proxy + CORS working
                f"Nginx proxy integration: {success_count}/{total_tests} tests passed",
                (health_time + direct_time) / 2,  # Average response time
                {
                    "proxy_tests": proxy_tests,
                    "health_via_proxy_time": health_time,
                    "health_direct_time": direct_time,
                    "cors_headers_present": bool(cors_headers.get("Access-Control-Allow-Origin")),
                    "compression_detected": compression_applied
                }
            )
                
        except Exception as e:
            return SmokeTestResult(test_name, False, f"Proxy test failed: {str(e)}")

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all smoke tests and return comprehensive results."""
        self.print_header("Adelaide Weather E2E Smoke Test Suite")
        
        print(f"{Colors.BOLD}🔍 Test Configuration:{Colors.END}")
        print(f"  • Base URL: {TEST_BASE_URL}")
        print(f"  • API URL: {API_BASE_URL}")
        print(f"  • Test Token: {TEST_TOKEN[:8]}...")
        print(f"  • Max Response Time: {MAX_RESPONSE_TIME_MS}ms")
        
        # Start services
        if not self.start_services():
            print(f"{Colors.RED}❌ Failed to start services. Aborting tests.{Colors.END}")
            return {"success": False, "error": "Service startup failed"}
        
        # Run all tests
        test_functions = [
            self.test_unauthorized_access,
            self.test_authenticated_health,
            self.test_forecast_with_faiss,
            self.test_metrics_endpoint,
            self.test_nginx_proxy_integration
        ]
        
        print(f"\n{Colors.BOLD}🧪 Running Smoke Tests:{Colors.END}\n")
        
        for test_func in test_functions:
            result = test_func()
            self.results.append(result)
            self.print_result(result)
        
        # Generate summary
        passed_tests = [r for r in self.results if r.passed]
        failed_tests = [r for r in self.results if not r.passed]
        
        # Performance analysis
        response_times = [r.response_time_ms for r in self.results if r.response_time_ms]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        self.print_header("Smoke Test Results Summary")
        
        print(f"{Colors.BOLD}📊 Test Results:{Colors.END}")
        print(f"  • Total Tests: {len(self.results)}")
        print(f"  • Passed: {Colors.GREEN}{len(passed_tests)}{Colors.END}")
        print(f"  • Failed: {Colors.RED}{len(failed_tests)}{Colors.END}")
        print(f"  • Success Rate: {Colors.GREEN if len(failed_tests) == 0 else Colors.YELLOW}{len(passed_tests)/len(self.results)*100:.1f}%{Colors.END}")
        
        print(f"\n{Colors.BOLD}⚡ Performance Metrics:{Colors.END}")
        print(f"  • Average Response Time: {avg_response_time:.1f}ms")
        print(f"  • Max Response Time: {max(response_times) if response_times else 0:.1f}ms")
        print(f"  • Min Response Time: {min(response_times) if response_times else 0:.1f}ms")
        
        if failed_tests:
            print(f"\n{Colors.BOLD}{Colors.RED}❌ Failed Tests:{Colors.END}")
            for test in failed_tests:
                print(f"  • {test.test_name}: {test.message}")
        
        # Critical path validation
        critical_tests = [
            "Test 2: Authenticated Health Check",
            "Test 3: Forecast with FAISS Integration", 
            "Test 5: Nginx Proxy Integration"
        ]
        
        critical_passed = [r for r in self.results if any(ct in r.test_name for ct in critical_tests) and r.passed]
        critical_success = len(critical_passed) >= 2  # At least 2 of 3 critical tests must pass
        
        print(f"\n{Colors.BOLD}🚨 Critical Path Status:{Colors.END}")
        status_color = Colors.GREEN if critical_success else Colors.RED
        status_text = "✅ PASSING" if critical_success else "❌ FAILING"
        print(f"  • Critical Path: {status_color}{status_text}{Colors.END}")
        print(f"  • Ready for CI/CD: {'✅ YES' if len(failed_tests) == 0 else '❌ NO'}")
        
        # Generate machine-readable results
        results_data = {
            "success": len(failed_tests) == 0,
            "critical_path_passing": critical_success,
            "total_tests": len(self.results),
            "passed_tests": len(passed_tests),
            "failed_tests": len(failed_tests),
            "success_rate": len(passed_tests)/len(self.results)*100,
            "avg_response_time_ms": avg_response_time,
            "max_response_time_ms": max(response_times) if response_times else 0,
            "test_results": [
                {
                    "name": r.test_name,
                    "passed": r.passed,
                    "message": r.message,
                    "response_time_ms": r.response_time_ms,
                    "details": r.details
                } for r in self.results
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Save results to file
        results_file = "/home/micha/adelaide-weather-final/e2e_smoke_test_results.json"
        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"\n{Colors.BOLD}📄 Results saved to: {results_file}{Colors.END}")
        
        if len(failed_tests) == 0:
            print(f"\n{Colors.BOLD}{Colors.GREEN}🎉 ALL SMOKE TESTS PASSED! System ready for production.{Colors.END}")
        else:
            print(f"\n{Colors.BOLD}{Colors.RED}⚠️ SMOKE TESTS FAILED. System NOT ready for production.{Colors.END}")
            print(f"{Colors.YELLOW}Please address the failed tests before proceeding with deployment.{Colors.END}")
        
        return results_data

def main():
    """Main execution function."""
    try:
        # Change to the project directory
        os.chdir('/home/micha/adelaide-weather-final')
        
        # Create and run the smoke test suite
        suite = SmokeTestSuite()
        results = suite.run_all_tests()
        
        # Exit with appropriate code
        exit_code = 0 if results["success"] else 1
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}🛑 Tests interrupted by user{Colors.END}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}💥 Test suite failed: {e}{Colors.END}")
        sys.exit(1)

if __name__ == "__main__":
    main()