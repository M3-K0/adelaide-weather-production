#!/usr/bin/env python3
"""
T-018 Quick Readiness Validator
===============================

Quick validation script to check if the system is ready for T-018 performance 
validation. This performs basic connectivity, authentication, and endpoint 
availability checks before running the full validation suite.

This script helps identify issues early and provides quick feedback on:
- API accessibility and authentication
- Endpoint availability (/forecast, /health, /metrics)
- T-005 compression middleware status
- T-011 FAISS monitoring status
- Basic performance baseline

Usage:
    python validate_t018_readiness.py

Environment Variables:
    API_BASE_URL: Base URL for API (default: http://localhost:8000)
    API_TOKEN: Authentication token (required)

Author: Performance Specialist
Version: 1.0.0 - Quick Readiness Check
"""

import os
import sys
import time
import json
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class Colors:
    """Terminal colors for better readability."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

class T018ReadinessChecker:
    """Quick readiness checker for T-018 validation prerequisites."""
    
    def __init__(self, api_url: str, api_token: str):
        """Initialize readiness checker.
        
        Args:
            api_url: Base URL for API
            api_token: Authentication token
        """
        self.api_url = api_url.rstrip('/')
        self.api_token = api_token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate"
        })
        self.session.timeout = 30
        
        self.checks = []
        
    def add_check(self, name: str, passed: bool, message: str, details: Dict = None):
        """Add a check result."""
        self.checks.append({
            "name": name,
            "passed": passed,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Print result
        status_color = Colors.GREEN if passed else Colors.RED
        status_text = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status_color}{status_text}{Colors.END} {name}: {message}")
        
    def check_api_connectivity(self) -> bool:
        """Check basic API connectivity."""
        print(f"\n{Colors.BOLD}🔌 Checking API Connectivity{Colors.END}")
        
        try:
            start_time = time.time()
            response = self.session.get(f"{self.api_url}/health")
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                health_data = response.json()
                ready = health_data.get('ready', False)
                
                self.add_check(
                    "API Connectivity",
                    True,
                    f"API responding in {response_time:.0f}ms",
                    {"response_time_ms": response_time, "ready": ready}
                )
                
                if ready:
                    self.add_check(
                        "System Ready",
                        True,
                        "System reports ready status",
                        {"health_data": health_data}
                    )
                else:
                    self.add_check(
                        "System Ready",
                        False,
                        "System not ready",
                        {"health_data": health_data}
                    )
                    
                return True
            else:
                self.add_check(
                    "API Connectivity",
                    False,
                    f"HTTP {response.status_code}: {response.text[:100]}",
                    {"status_code": response.status_code}
                )
                return False
                
        except Exception as e:
            self.add_check(
                "API Connectivity",
                False,
                f"Connection failed: {str(e)}",
                {"error": str(e)}
            )
            return False
            
    def check_authentication(self) -> bool:
        """Check API authentication."""
        print(f"\n{Colors.BOLD}🔐 Checking Authentication{Colors.END}")
        
        # Test without token
        try:
            session_no_auth = requests.Session()
            session_no_auth.timeout = 10
            response = session_no_auth.get(f"{self.api_url}/forecast?horizon=6h")
            
            if response.status_code == 401 or response.status_code == 403:
                self.add_check(
                    "Auth Required",
                    True,
                    "API correctly rejects unauthenticated requests",
                    {"status_code": response.status_code}
                )
            else:
                self.add_check(
                    "Auth Required",
                    False,
                    f"API allows unauthenticated access (status: {response.status_code})",
                    {"status_code": response.status_code}
                )
        except Exception as e:
            self.add_check(
                "Auth Required",
                False,
                f"Auth test failed: {str(e)}",
                {"error": str(e)}
            )
            
        # Test with token
        try:
            response = self.session.get(f"{self.api_url}/forecast?horizon=6h")
            
            if response.status_code == 200:
                self.add_check(
                    "Token Authentication",
                    True,
                    "Token authentication successful",
                    {"status_code": response.status_code}
                )
                return True
            else:
                self.add_check(
                    "Token Authentication",
                    False,
                    f"Token auth failed: HTTP {response.status_code}",
                    {"status_code": response.status_code, "response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.add_check(
                "Token Authentication",
                False,
                f"Token auth error: {str(e)}",
                {"error": str(e)}
            )
            return False
            
    def check_endpoint_availability(self) -> bool:
        """Check all required endpoints are available."""
        print(f"\n{Colors.BOLD}🌐 Checking Endpoint Availability{Colors.END}")
        
        endpoints = [
            ("/health", "Health endpoint"),
            ("/metrics", "Metrics endpoint"),
            ("/forecast?horizon=6h", "Forecast endpoint"),
            ("/health/faiss", "FAISS health endpoint")
        ]
        
        all_available = True
        
        for endpoint, description in endpoints:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.api_url}{endpoint}")
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    self.add_check(
                        description,
                        True,
                        f"Available ({response_time:.0f}ms)",
                        {"endpoint": endpoint, "response_time_ms": response_time}
                    )
                else:
                    self.add_check(
                        description,
                        False,
                        f"HTTP {response.status_code}",
                        {"endpoint": endpoint, "status_code": response.status_code}
                    )
                    all_available = False
                    
            except Exception as e:
                self.add_check(
                    description,
                    False,
                    f"Error: {str(e)}",
                    {"endpoint": endpoint, "error": str(e)}
                )
                all_available = False
                
        return all_available
        
    def check_t005_compression(self) -> bool:
        """Check T-005 compression middleware."""
        print(f"\n{Colors.BOLD}📦 Checking T-005 Compression Middleware{Colors.END}")
        
        try:
            # Request with compression support
            response = self.session.get(
                f"{self.api_url}/forecast?horizon=24h&vars=t2m,u10,v10,msl"
            )
            
            if response.status_code == 200:
                # Check for compression indicators
                compression_detected = 'content-encoding' in response.headers
                middleware_headers = 'x-response-time' in response.headers
                compression_ratio = response.headers.get('x-compression-ratio')
                
                if compression_detected:
                    self.add_check(
                        "Compression Active",
                        True,
                        f"Response compressed (ratio: {compression_ratio})",
                        {
                            "content_encoding": response.headers.get('content-encoding'),
                            "compression_ratio": compression_ratio,
                            "response_size": len(response.content)
                        }
                    )
                else:
                    self.add_check(
                        "Compression Active",
                        False,
                        "No compression detected in response",
                        {"response_headers": dict(response.headers)}
                    )
                    
                if middleware_headers:
                    self.add_check(
                        "Performance Middleware",
                        True,
                        f"Middleware active (response time: {response.headers.get('x-response-time')})",
                        {"middleware_headers": {k: v for k, v in response.headers.items() if k.startswith('x-')}}
                    )
                else:
                    self.add_check(
                        "Performance Middleware",
                        False,
                        "No middleware headers detected",
                        {}
                    )
                    
                return compression_detected or middleware_headers
            else:
                self.add_check(
                    "T-005 Compression",
                    False,
                    f"Cannot test compression (HTTP {response.status_code})",
                    {"status_code": response.status_code}
                )
                return False
                
        except Exception as e:
            self.add_check(
                "T-005 Compression",
                False,
                f"Compression test error: {str(e)}",
                {"error": str(e)}
            )
            return False
            
    def check_t011_faiss_monitoring(self) -> bool:
        """Check T-011 FAISS health monitoring."""
        print(f"\n{Colors.BOLD}🔍 Checking T-011 FAISS Health Monitoring{Colors.END}")
        
        try:
            response = self.session.get(f"{self.api_url}/health/faiss")
            
            if response.status_code == 200:
                faiss_health = response.json()
                status = faiss_health.get('status', 'unknown')
                
                monitoring_active = status in ['healthy', 'degraded']
                indices_count = len(faiss_health.get('indices', {}))
                query_metrics = 'query_performance' in faiss_health
                
                self.add_check(
                    "FAISS Health Endpoint",
                    True,
                    f"Status: {status}",
                    {"faiss_status": status, "indices_count": indices_count}
                )
                
                if monitoring_active:
                    self.add_check(
                        "FAISS Monitoring Active",
                        True,
                        f"Monitoring {indices_count} indices",
                        {"monitoring_details": faiss_health}
                    )
                else:
                    self.add_check(
                        "FAISS Monitoring Active",
                        False,
                        f"Monitoring not active (status: {status})",
                        {"faiss_status": status}
                    )
                    
                if query_metrics:
                    perf_data = faiss_health['query_performance']
                    self.add_check(
                        "FAISS Performance Metrics",
                        True,
                        f"Query metrics available ({perf_data.get('total_queries', 0)} queries tracked)",
                        {"performance_metrics": perf_data}
                    )
                else:
                    self.add_check(
                        "FAISS Performance Metrics",
                        False,
                        "No performance metrics available",
                        {}
                    )
                    
                return monitoring_active and query_metrics
            else:
                self.add_check(
                    "T-011 FAISS Monitoring",
                    False,
                    f"FAISS health endpoint failed (HTTP {response.status_code})",
                    {"status_code": response.status_code}
                )
                return False
                
        except Exception as e:
            self.add_check(
                "T-011 FAISS Monitoring",
                False,
                f"FAISS monitoring check error: {str(e)}",
                {"error": str(e)}
            )
            return False
            
    def check_performance_baseline(self) -> bool:
        """Check basic performance baseline."""
        print(f"\n{Colors.BOLD}⚡ Checking Performance Baseline{Colors.END}")
        
        try:
            # Test forecast endpoint performance
            start_time = time.time()
            response = self.session.get(f"{self.api_url}/forecast?horizon=6h&vars=t2m,u10,v10")
            forecast_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                # Check forecast response time (should be well under SLA)
                forecast_ok = forecast_time < 1000  # 1 second as baseline
                
                self.add_check(
                    "Forecast Performance",
                    forecast_ok,
                    f"Response time: {forecast_time:.0f}ms",
                    {"response_time_ms": forecast_time, "threshold_ms": 1000}
                )
                
                # Test health endpoint performance
                start_time = time.time()
                health_response = self.session.get(f"{self.api_url}/health")
                health_time = (time.time() - start_time) * 1000
                
                health_ok = health_time < 500  # 500ms as baseline
                
                self.add_check(
                    "Health Performance",
                    health_ok,
                    f"Response time: {health_time:.0f}ms",
                    {"response_time_ms": health_time, "threshold_ms": 500}
                )
                
                return forecast_ok and health_ok
            else:
                self.add_check(
                    "Performance Baseline",
                    False,
                    f"Cannot test performance (HTTP {response.status_code})",
                    {"status_code": response.status_code}
                )
                return False
                
        except Exception as e:
            self.add_check(
                "Performance Baseline",
                False,
                f"Performance test error: {str(e)}",
                {"error": str(e)}
            )
            return False
            
    def run_all_checks(self) -> bool:
        """Run all readiness checks."""
        print(f"{Colors.BOLD}{Colors.CYAN}🎯 T-018 Performance Validation Readiness Check{Colors.END}")
        print(f"{Colors.CYAN}API URL: {self.api_url}{Colors.END}")
        print(f"{Colors.CYAN}Timestamp: {datetime.now(timezone.utc).isoformat()}{Colors.END}")
        
        # Run all checks
        connectivity_ok = self.check_api_connectivity()
        auth_ok = self.check_authentication() if connectivity_ok else False
        endpoints_ok = self.check_endpoint_availability() if auth_ok else False
        compression_ok = self.check_t005_compression() if endpoints_ok else False
        monitoring_ok = self.check_t011_faiss_monitoring() if endpoints_ok else False
        performance_ok = self.check_performance_baseline() if endpoints_ok else False
        
        # Calculate overall readiness
        critical_checks = [connectivity_ok, auth_ok, endpoints_ok, performance_ok]
        enhancement_checks = [compression_ok, monitoring_ok]
        
        critical_passed = all(critical_checks)
        enhancements_passed = all(enhancement_checks)
        overall_ready = critical_passed
        
        return overall_ready, critical_passed, enhancements_passed
        
    def print_summary(self, overall_ready: bool, critical_passed: bool, enhancements_passed: bool):
        """Print readiness summary."""
        print(f"\n{Colors.BOLD}📊 READINESS SUMMARY{Colors.END}")
        print("=" * 60)
        
        # Overall status
        if overall_ready:
            print(f"{Colors.GREEN}✅ READY FOR T-018 VALIDATION{Colors.END}")
        else:
            print(f"{Colors.RED}❌ NOT READY FOR T-018 VALIDATION{Colors.END}")
            
        # Detailed status
        print(f"\n{Colors.BOLD}Critical Requirements:{Colors.END}")
        print(f"   {'✅' if critical_passed else '❌'} Basic system functionality")
        
        print(f"\n{Colors.BOLD}Enhancement Validation:{Colors.END}")
        print(f"   {'✅' if enhancements_passed else '⚠️'} T-005 & T-011 integrations")
        
        # Check results summary
        passed_checks = len([c for c in self.checks if c['passed']])
        total_checks = len(self.checks)
        
        print(f"\n{Colors.BOLD}Checks Summary:{Colors.END}")
        print(f"   Passed: {passed_checks}/{total_checks}")
        print(f"   Success Rate: {passed_checks/total_checks*100:.1f}%")
        
        # Next steps
        print(f"\n{Colors.BOLD}Next Steps:{Colors.END}")
        if overall_ready:
            print(f"   {Colors.GREEN}➤ Run full T-018 validation: python run_t018_validation.py{Colors.END}")
        else:
            print(f"   {Colors.RED}➤ Address failed checks before running full validation{Colors.END}")
            print(f"   {Colors.YELLOW}➤ Check API logs and configuration{Colors.END}")
            
    def save_results(self):
        """Save check results to file."""
        results = {
            "readiness_check": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "api_url": self.api_url,
                "checks": self.checks,
                "summary": {
                    "total_checks": len(self.checks),
                    "passed_checks": len([c for c in self.checks if c['passed']]),
                    "success_rate": len([c for c in self.checks if c['passed']]) / len(self.checks) * 100
                }
            }
        }
        
        output_file = "t018_readiness_check_results.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
            
        print(f"\n💾 Results saved to: {output_file}")

def main():
    """Main readiness check workflow."""
    # Get configuration
    api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    api_token = os.getenv("API_TOKEN")
    
    if not api_token:
        print(f"{Colors.RED}❌ Error: API_TOKEN environment variable is required{Colors.END}")
        print("Please set API_TOKEN and try again.")
        sys.exit(1)
    
    # Run readiness check
    checker = T018ReadinessChecker(api_url, api_token)
    
    try:
        overall_ready, critical_passed, enhancements_passed = checker.run_all_checks()
        checker.print_summary(overall_ready, critical_passed, enhancements_passed)
        checker.save_results()
        
        # Exit with appropriate code
        sys.exit(0 if overall_ready else 1)
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⏹️ Readiness check interrupted{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}💥 Readiness check failed: {e}{Colors.END}")
        sys.exit(1)

if __name__ == "__main__":
    main()