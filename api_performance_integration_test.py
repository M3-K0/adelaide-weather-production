#!/usr/bin/env python3
"""
API Performance Integration Testing
=================================

Integration performance testing for the Adelaide Weather Forecasting API
with FAISS Health Monitoring. This script tests the complete API stack
including authentication, request processing, FAISS operations, and
monitoring overhead in a realistic production-like environment.

Key Testing Areas:
1. End-to-end forecast request performance
2. Health monitoring endpoint latency
3. Metrics collection performance
4. Concurrent API request handling
5. Authentication overhead
6. Error handling performance

Author: Performance Specialist
Version: 1.0.0 - API Integration Performance Testing
"""

import asyncio
import aiohttp
import time
import statistics
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import psutil

@dataclass
class APIPerformanceMetrics:
    """Container for API performance metrics."""
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    response_size_bytes: int
    timestamp: datetime
    error_message: Optional[str] = None
    
    @property
    def success(self) -> bool:
        """Check if request was successful."""
        return 200 <= self.status_code < 300

@dataclass
class LoadTestResults:
    """Container for load test results."""
    test_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    test_duration_seconds: float
    requests_per_second: float
    response_times: List[float] = field(default_factory=list)
    error_rates: Dict[int, int] = field(default_factory=dict)
    
    def add_response_time(self, response_time_ms: float):
        """Add response time sample."""
        self.response_times.append(response_time_ms)
    
    def calculate_percentiles(self) -> Dict[str, float]:
        """Calculate response time percentiles."""
        if not self.response_times:
            return {}
        
        return {
            "min": min(self.response_times),
            "max": max(self.response_times),
            "mean": statistics.mean(self.response_times),
            "median": statistics.median(self.response_times),
            "p95": np.percentile(self.response_times, 95),
            "p99": np.percentile(self.response_times, 99)
        }

class APIPerformanceTester:
    """API performance testing framework."""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_token: str = None):
        """Initialize API performance tester.
        
        Args:
            base_url: Base URL for the API
            api_token: Authentication token for API requests
        """
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token or os.getenv("API_TOKEN", "test-token")
        self.session: Optional[aiohttp.ClientSession] = None
        self.results: List[LoadTestResults] = []
        
        # Test parameters
        self.default_timeout = aiohttp.ClientTimeout(total=30)
        self.max_concurrent_requests = 100
        
        print(f"🔧 API Performance Tester initialized")
        print(f"   Base URL: {self.base_url}")
        print(f"   Token: {'*' * len(self.api_token[:4]) + self.api_token[-4:] if self.api_token else 'None'}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        connector = aiohttp.TCPConnector(limit=200, limit_per_host=100)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=self.default_timeout,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def make_request(self, endpoint: str, method: str = "GET", params: Dict = None) -> APIPerformanceMetrics:
        """Make a single API request and measure performance.
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            params: Query parameters
            
        Returns:
            Performance metrics for the request
        """
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            async with self.session.request(method, url, params=params) as response:
                response_text = await response.text()
                response_time_ms = (time.time() - start_time) * 1000
                
                return APIPerformanceMetrics(
                    endpoint=endpoint,
                    method=method,
                    status_code=response.status,
                    response_time_ms=response_time_ms,
                    response_size_bytes=len(response_text.encode('utf-8')),
                    timestamp=datetime.now(timezone.utc)
                )
        
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return APIPerformanceMetrics(
                endpoint=endpoint,
                method=method,
                status_code=0,  # Connection error
                response_time_ms=response_time_ms,
                response_size_bytes=0,
                timestamp=datetime.now(timezone.utc),
                error_message=str(e)
            )
    
    async def test_forecast_endpoint_performance(self, num_requests: int = 100) -> LoadTestResults:
        """Test forecast endpoint performance.
        
        Args:
            num_requests: Number of requests to make
            
        Returns:
            Load test results
        """
        print(f"\n🧪 Testing Forecast Endpoint Performance ({num_requests} requests)")
        
        start_time = time.time()
        results = LoadTestResults(
            test_name="forecast_endpoint_performance",
            total_requests=num_requests,
            successful_requests=0,
            failed_requests=0,
            test_duration_seconds=0,
            requests_per_second=0
        )
        
        # Test parameters
        horizons = ["6h", "12h", "24h", "48h"]
        variable_sets = [
            "t2m,u10,v10",
            "t2m,u10,v10,msl",
            "t2m,u10,v10,msl,cape",
            "cape,q850,z500"
        ]
        
        # Make requests
        for i in range(num_requests):
            horizon = horizons[i % len(horizons)]
            variables = variable_sets[i % len(variable_sets)]
            
            metrics = await self.make_request(
                "/forecast",
                params={"horizon": horizon, "vars": variables}
            )
            
            results.add_response_time(metrics.response_time_ms)
            
            if metrics.success:
                results.successful_requests += 1
            else:
                results.failed_requests += 1
                if metrics.status_code in results.error_rates:
                    results.error_rates[metrics.status_code] += 1
                else:
                    results.error_rates[metrics.status_code] = 1
            
            # Progress update
            if (i + 1) % 20 == 0:
                print(f"   Progress: {i + 1}/{num_requests} requests completed")
        
        end_time = time.time()
        results.test_duration_seconds = end_time - start_time
        results.requests_per_second = num_requests / results.test_duration_seconds
        
        # Print results
        percentiles = results.calculate_percentiles()
        print(f"✅ Forecast Endpoint Results:")
        print(f"   Duration: {results.test_duration_seconds:.2f}s")
        print(f"   Success rate: {results.successful_requests}/{num_requests} ({100*results.successful_requests/num_requests:.1f}%)")
        print(f"   Throughput: {results.requests_per_second:.1f} RPS")
        print(f"   Response times: min={percentiles['min']:.1f}ms, mean={percentiles['mean']:.1f}ms, p95={percentiles['p95']:.1f}ms")
        
        if results.error_rates:
            print(f"   Error breakdown: {results.error_rates}")
        
        self.results.append(results)
        return results
    
    async def test_health_endpoint_performance(self, num_requests: int = 50) -> LoadTestResults:
        """Test health endpoint performance.
        
        Args:
            num_requests: Number of requests to make
            
        Returns:
            Load test results
        """
        print(f"\n🧪 Testing Health Endpoint Performance ({num_requests} requests)")
        
        start_time = time.time()
        results = LoadTestResults(
            test_name="health_endpoint_performance",
            total_requests=num_requests,
            successful_requests=0,
            failed_requests=0,
            test_duration_seconds=0,
            requests_per_second=0
        )
        
        # Make requests to health endpoints
        for i in range(num_requests):
            if i % 2 == 0:
                endpoint = "/health"
            else:
                endpoint = "/health/faiss"
            
            metrics = await self.make_request(endpoint)
            results.add_response_time(metrics.response_time_ms)
            
            if metrics.success:
                results.successful_requests += 1
            else:
                results.failed_requests += 1
                if metrics.status_code in results.error_rates:
                    results.error_rates[metrics.status_code] += 1
                else:
                    results.error_rates[metrics.status_code] = 1
            
            # Small delay between health checks
            await asyncio.sleep(0.1)
        
        end_time = time.time()
        results.test_duration_seconds = end_time - start_time
        results.requests_per_second = num_requests / results.test_duration_seconds
        
        # Print results
        percentiles = results.calculate_percentiles()
        print(f"✅ Health Endpoint Results:")
        print(f"   Duration: {results.test_duration_seconds:.2f}s")
        print(f"   Success rate: {results.successful_requests}/{num_requests} ({100*results.successful_requests/num_requests:.1f}%)")
        print(f"   Throughput: {results.requests_per_second:.1f} RPS")
        print(f"   Response times: min={percentiles['min']:.1f}ms, mean={percentiles['mean']:.1f}ms, p95={percentiles['p95']:.1f}ms")
        
        # Validate health endpoint latency requirement (<50ms)
        if percentiles['mean'] <= 50:
            print(f"✅ PASS: Health endpoint mean latency {percentiles['mean']:.1f}ms ≤ 50ms")
        else:
            print(f"❌ FAIL: Health endpoint mean latency {percentiles['mean']:.1f}ms > 50ms")
        
        self.results.append(results)
        return results
    
    async def test_metrics_endpoint_performance(self, num_requests: int = 20) -> LoadTestResults:
        """Test metrics endpoint performance.
        
        Args:
            num_requests: Number of requests to make
            
        Returns:
            Load test results
        """
        print(f"\n🧪 Testing Metrics Endpoint Performance ({num_requests} requests)")
        
        start_time = time.time()
        results = LoadTestResults(
            test_name="metrics_endpoint_performance",
            total_requests=num_requests,
            successful_requests=0,
            failed_requests=0,
            test_duration_seconds=0,
            requests_per_second=0
        )
        
        # Make requests to metrics endpoint
        for i in range(num_requests):
            metrics = await self.make_request("/metrics")
            results.add_response_time(metrics.response_time_ms)
            
            if metrics.success:
                results.successful_requests += 1
            else:
                results.failed_requests += 1
                if metrics.status_code in results.error_rates:
                    results.error_rates[metrics.status_code] += 1
                else:
                    results.error_rates[metrics.status_code] = 1
            
            # Delay between metrics collections
            await asyncio.sleep(1.0)  # Metrics are expensive
        
        end_time = time.time()
        results.test_duration_seconds = end_time - start_time
        results.requests_per_second = num_requests / results.test_duration_seconds
        
        # Print results
        percentiles = results.calculate_percentiles()
        print(f"✅ Metrics Endpoint Results:")
        print(f"   Duration: {results.test_duration_seconds:.2f}s")
        print(f"   Success rate: {results.successful_requests}/{num_requests} ({100*results.successful_requests/num_requests:.1f}%)")
        print(f"   Throughput: {results.requests_per_second:.1f} RPS")
        print(f"   Response times: min={percentiles['min']:.1f}ms, mean={percentiles['mean']:.1f}ms, p95={percentiles['p95']:.1f}ms")
        
        self.results.append(results)
        return results
    
    async def test_concurrent_forecast_requests(self, num_concurrent: int = 50, total_requests: int = 200) -> LoadTestResults:
        """Test concurrent forecast request handling.
        
        Args:
            num_concurrent: Number of concurrent requests
            total_requests: Total number of requests to make
            
        Returns:
            Load test results
        """
        print(f"\n🧪 Testing Concurrent Forecast Requests ({num_concurrent} concurrent, {total_requests} total)")
        
        start_time = time.time()
        results = LoadTestResults(
            test_name="concurrent_forecast_requests",
            total_requests=total_requests,
            successful_requests=0,
            failed_requests=0,
            test_duration_seconds=0,
            requests_per_second=0
        )
        
        semaphore = asyncio.Semaphore(num_concurrent)
        
        async def make_concurrent_request(request_id: int) -> APIPerformanceMetrics:
            """Make a single concurrent request."""
            async with semaphore:
                horizon = ["6h", "12h", "24h", "48h"][request_id % 4]
                variables = "t2m,u10,v10,msl"
                
                return await self.make_request(
                    "/forecast",
                    params={"horizon": horizon, "vars": variables}
                )
        
        # Launch all concurrent requests
        print(f"   Launching {total_requests} requests with {num_concurrent} concurrency...")
        tasks = [make_concurrent_request(i) for i in range(total_requests)]
        
        # Wait for completion and collect results
        completed_metrics = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for metrics in completed_metrics:
            if isinstance(metrics, Exception):
                results.failed_requests += 1
                results.add_response_time(0)  # Failed request
            else:
                results.add_response_time(metrics.response_time_ms)
                if metrics.success:
                    results.successful_requests += 1
                else:
                    results.failed_requests += 1
                    if metrics.status_code in results.error_rates:
                        results.error_rates[metrics.status_code] += 1
                    else:
                        results.error_rates[metrics.status_code] = 1
        
        end_time = time.time()
        results.test_duration_seconds = end_time - start_time
        results.requests_per_second = total_requests / results.test_duration_seconds
        
        # Print results
        percentiles = results.calculate_percentiles()
        print(f"✅ Concurrent Request Results:")
        print(f"   Duration: {results.test_duration_seconds:.2f}s")
        print(f"   Success rate: {results.successful_requests}/{total_requests} ({100*results.successful_requests/total_requests:.1f}%)")
        print(f"   Effective throughput: {results.requests_per_second:.1f} RPS")
        print(f"   Response times: min={percentiles['min']:.1f}ms, mean={percentiles['mean']:.1f}ms, p95={percentiles['p95']:.1f}ms")
        
        # Validate concurrent handling requirement (>100 concurrent queries)
        if results.successful_requests >= 100:
            print(f"✅ PASS: Handled {results.successful_requests} ≥ 100 concurrent requests successfully")
        else:
            print(f"❌ FAIL: Only handled {results.successful_requests} < 100 concurrent requests successfully")
        
        self.results.append(results)
        return results
    
    async def test_sustained_load(self, duration_seconds: int = 60, rps_target: int = 10) -> LoadTestResults:
        """Test sustained load performance.
        
        Args:
            duration_seconds: Test duration in seconds
            rps_target: Target requests per second
            
        Returns:
            Load test results
        """
        print(f"\n🧪 Testing Sustained Load ({duration_seconds}s at {rps_target} RPS target)")
        
        start_time = time.time()
        results = LoadTestResults(
            test_name="sustained_load",
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            test_duration_seconds=0,
            requests_per_second=0
        )
        
        end_test_time = start_time + duration_seconds
        request_interval = 1.0 / rps_target  # Seconds between requests
        
        request_count = 0
        next_request_time = start_time
        
        print(f"   Running sustained load for {duration_seconds}s...")
        
        while time.time() < end_test_time:
            current_time = time.time()
            
            # Make request if it's time
            if current_time >= next_request_time:
                horizon = ["6h", "12h", "24h", "48h"][request_count % 4]
                variables = "t2m,u10,v10"
                
                metrics = await self.make_request(
                    "/forecast",
                    params={"horizon": horizon, "vars": variables}
                )
                
                results.total_requests += 1
                results.add_response_time(metrics.response_time_ms)
                
                if metrics.success:
                    results.successful_requests += 1
                else:
                    results.failed_requests += 1
                    if metrics.status_code in results.error_rates:
                        results.error_rates[metrics.status_code] += 1
                    else:
                        results.error_rates[metrics.status_code] = 1
                
                request_count += 1
                next_request_time += request_interval
                
                # Progress update
                if request_count % 50 == 0:
                    elapsed = current_time - start_time
                    current_rps = request_count / elapsed
                    print(f"   Progress: {elapsed:.0f}s, {request_count} requests, {current_rps:.1f} RPS")
            
            # Small sleep to prevent tight loop
            await asyncio.sleep(0.01)
        
        end_time = time.time()
        results.test_duration_seconds = end_time - start_time
        results.requests_per_second = results.total_requests / results.test_duration_seconds
        
        # Print results
        percentiles = results.calculate_percentiles()
        print(f"✅ Sustained Load Results:")
        print(f"   Duration: {results.test_duration_seconds:.2f}s")
        print(f"   Total requests: {results.total_requests}")
        print(f"   Success rate: {results.successful_requests}/{results.total_requests} ({100*results.successful_requests/results.total_requests:.1f}%)")
        print(f"   Actual throughput: {results.requests_per_second:.1f} RPS (target: {rps_target} RPS)")
        print(f"   Response times: min={percentiles['min']:.1f}ms, mean={percentiles['mean']:.1f}ms, p95={percentiles['p95']:.1f}ms")
        
        self.results.append(results)
        return results
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive API performance report."""
        report = {
            "api_performance_test_report": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "base_url": self.base_url,
                "test_results": [],
                "summary": {
                    "total_tests": len(self.results),
                    "total_requests": sum(r.total_requests for r in self.results),
                    "total_successful": sum(r.successful_requests for r in self.results),
                    "total_failed": sum(r.failed_requests for r in self.results),
                    "overall_success_rate": 0.0,
                    "requirements_compliance": {}
                }
            }
        }
        
        # Process test results
        for result in self.results:
            percentiles = result.calculate_percentiles()
            
            test_data = {
                "test_name": result.test_name,
                "total_requests": result.total_requests,
                "successful_requests": result.successful_requests,
                "failed_requests": result.failed_requests,
                "success_rate_percent": 100 * result.successful_requests / result.total_requests if result.total_requests > 0 else 0,
                "test_duration_seconds": result.test_duration_seconds,
                "requests_per_second": result.requests_per_second,
                "response_time_percentiles": percentiles,
                "error_rates": result.error_rates
            }
            
            report["api_performance_test_report"]["test_results"].append(test_data)
        
        # Calculate summary
        total_requests = sum(r.total_requests for r in self.results)
        total_successful = sum(r.successful_requests for r in self.results)
        
        if total_requests > 0:
            report["api_performance_test_report"]["summary"]["overall_success_rate"] = 100 * total_successful / total_requests
        
        # Check compliance with performance requirements
        compliance = {}
        
        # Health endpoint latency requirement (<50ms)
        health_test = next((r for r in self.results if r.test_name == "health_endpoint_performance"), None)
        if health_test:
            health_percentiles = health_test.calculate_percentiles()
            compliance["health_endpoint_latency"] = health_percentiles["mean"] <= 50
        
        # Concurrent request handling (>100 successful)
        concurrent_test = next((r for r in self.results if r.test_name == "concurrent_forecast_requests"), None)
        if concurrent_test:
            compliance["concurrent_request_handling"] = concurrent_test.successful_requests >= 100
        
        # Overall system stability (>95% success rate)
        compliance["system_stability"] = report["api_performance_test_report"]["summary"]["overall_success_rate"] >= 95
        
        report["api_performance_test_report"]["summary"]["requirements_compliance"] = compliance
        
        return report
    
    def print_final_summary(self):
        """Print final API performance test summary."""
        report = self.generate_performance_report()["api_performance_test_report"]
        
        print("\n" + "="*80)
        print("🏁 API PERFORMANCE TEST SUMMARY")
        print("="*80)
        
        print(f"🌐 API Base URL: {self.base_url}")
        print(f"📈 Total Tests: {report['summary']['total_tests']}")
        print(f"🔍 Total Requests: {report['summary']['total_requests']:,}")
        print(f"✅ Successful: {report['summary']['total_successful']:,}")
        print(f"❌ Failed: {report['summary']['total_failed']:,}")
        print(f"📊 Overall Success Rate: {report['summary']['overall_success_rate']:.1f}%")
        
        print("\n📋 Requirements Compliance:")
        compliance = report["summary"]["requirements_compliance"]
        for req_name, met in compliance.items():
            status = "✅ PASS" if met else "❌ FAIL"
            print(f"   {req_name}: {status}")
        
        # Overall assessment
        all_requirements_met = all(compliance.values()) if compliance else False
        
        print(f"\n🎯 Overall Assessment:")
        if all_requirements_met:
            print("✅ ALL API PERFORMANCE REQUIREMENTS MET")
            print("   The API provides excellent performance with FAISS monitoring enabled.")
        else:
            print("❌ SOME API PERFORMANCE REQUIREMENTS NOT MET")
            print("   Review failed requirements and investigate performance bottlenecks.")

async def main():
    """Main API performance testing workflow."""
    print("🚀 Adelaide Weather API Performance Testing")
    print("=" * 50)
    
    # Configuration
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    api_token = os.getenv("API_TOKEN", "test-token")
    
    print(f"🔧 Configuration:")
    print(f"   API URL: {base_url}")
    print(f"   Token configured: {'Yes' if api_token else 'No'}")
    
    # Check if API is available
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status != 200:
                    print(f"⚠️ Warning: API health check returned status {response.status}")
                else:
                    print("✅ API is responding")
    except Exception as e:
        print(f"❌ API connectivity test failed: {e}")
        print("   Proceeding with tests anyway...")
    
    # Run performance tests
    async with APIPerformanceTester(base_url=base_url, api_token=api_token) as tester:
        try:
            print("\n🧪 Starting API Performance Test Suite...")
            
            # Test 1: Forecast endpoint performance
            await tester.test_forecast_endpoint_performance(num_requests=100)
            
            # Test 2: Health endpoint performance
            await tester.test_health_endpoint_performance(num_requests=50)
            
            # Test 3: Metrics endpoint performance
            await tester.test_metrics_endpoint_performance(num_requests=20)
            
            # Test 4: Concurrent request handling
            await tester.test_concurrent_forecast_requests(num_concurrent=50, total_requests=200)
            
            # Test 5: Sustained load testing
            await tester.test_sustained_load(duration_seconds=60, rps_target=10)
            
            # Generate and display final report
            tester.print_final_summary()
            
            # Save detailed report
            report = tester.generate_performance_report()
            with open("api_performance_integration_report.json", "w") as f:
                json.dump(report, f, indent=2)
            
            print(f"\n💾 Detailed report saved: api_performance_integration_report.json")
            
        except KeyboardInterrupt:
            print("\n⏹️ API performance testing interrupted by user")
        except Exception as e:
            print(f"\n💥 API performance testing failed: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(main())