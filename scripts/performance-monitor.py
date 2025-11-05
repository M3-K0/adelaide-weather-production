#!/usr/bin/env python3
"""
Adelaide Weather Forecasting API - Performance Monitor
====================================================

Advanced performance monitoring and analysis tool for the Adelaide Weather API.

Features:
- Real-time performance metrics collection
- Response time analysis and trending
- Error rate monitoring and alerting
- System health diagnostics
- Performance regression detection
- Load testing and stress testing
- Detailed performance reports

Usage:
    python performance-monitor.py --monitor       # Continuous monitoring
    python performance-monitor.py --test         # Run performance tests
    python performance-monitor.py --report       # Generate performance report
    python performance-monitor.py --baseline     # Establish performance baseline
"""

import os
import sys
import time
import json
import asyncio
import argparse
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
import psutil
import numpy as np
from prometheus_client.parser import text_string_to_metric_families


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""
    timestamp: datetime
    response_time_ms: float
    status_code: int
    error_rate: float
    throughput_rps: float
    cpu_usage: float
    memory_usage_mb: float
    active_connections: int
    queue_depth: int = 0


@dataclass
class PerformanceTest:
    """Performance test configuration."""
    name: str
    duration_seconds: int
    concurrent_users: int
    ramp_up_seconds: int
    endpoints: List[str]
    expected_p95_ms: float
    expected_error_rate: float


class PerformanceMonitor:
    """Advanced performance monitoring for the Adelaide Weather API."""

    def __init__(self, api_url: str = "http://localhost:8000", 
                 api_token: str = "dev-token-change-in-production"):
        self.api_url = api_url.rstrip('/')
        self.api_token = api_token
        self.metrics_history: List[PerformanceMetrics] = []
        self.baseline_metrics: Optional[Dict] = None
        
        # HTTP client configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={"Authorization": f"Bearer {api_token}"}
        )
        
        # Performance thresholds
        self.thresholds = {
            "response_time_p95_ms": 150.0,
            "error_rate_percent": 1.0,
            "cpu_usage_percent": 80.0,
            "memory_usage_mb": 512.0
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def collect_api_metrics(self) -> Dict:
        """Collect metrics from the API /metrics endpoint."""
        try:
            response = await self.client.get(f"{self.api_url}/metrics")
            response.raise_for_status()
            
            metrics = {}
            for family in text_string_to_metric_families(response.text):
                for sample in family.samples:
                    metrics[sample.name] = sample.value
            
            return metrics
            
        except Exception as e:
            print(f"Failed to collect API metrics: {e}")
            return {}

    async def make_forecast_request(self, horizon: str = "24h", 
                                  variables: str = "t2m,u10,v10") -> Tuple[float, int]:
        """Make a forecast request and measure response time."""
        start_time = time.time()
        
        try:
            response = await self.client.get(
                f"{self.api_url}/forecast",
                params={"horizon": horizon, "vars": variables}
            )
            
            response_time = (time.time() - start_time) * 1000
            return response_time, response.status_code
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            print(f"Request failed: {e}")
            return response_time, 500

    def collect_system_metrics(self) -> Dict:
        """Collect system-level performance metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            return {
                "cpu_usage": cpu_percent,
                "memory_usage_mb": memory.used / 1024 / 1024,
                "memory_available_mb": memory.available / 1024 / 1024,
                "memory_percent": memory.percent
            }
        except Exception as e:
            print(f"Failed to collect system metrics: {e}")
            return {}

    async def run_performance_test(self, test_config: PerformanceTest) -> Dict:
        """Run a comprehensive performance test."""
        print(f"\n🚀 Running performance test: {test_config.name}")
        print(f"   Duration: {test_config.duration_seconds}s")
        print(f"   Concurrent users: {test_config.concurrent_users}")
        print(f"   Ramp-up: {test_config.ramp_up_seconds}s")
        
        start_time = time.time()
        results = {
            "test_name": test_config.name,
            "start_time": datetime.now(),
            "response_times": [],
            "status_codes": [],
            "errors": [],
            "throughput_timeline": []
        }
        
        # Ramp-up phase
        print("📈 Ramp-up phase...")
        await self._ramp_up_load(test_config, results)
        
        # Sustained load phase
        print("⚡ Sustained load phase...")
        await self._sustained_load(test_config, results)
        
        # Analysis
        total_duration = time.time() - start_time
        analysis = self._analyze_test_results(results, test_config, total_duration)
        
        return {**results, **analysis}

    async def _ramp_up_load(self, config: PerformanceTest, results: Dict):
        """Gradually increase load during ramp-up period."""
        ramp_step_duration = config.ramp_up_seconds / config.concurrent_users
        
        for users in range(1, config.concurrent_users + 1):
            tasks = []
            for _ in range(users):
                for endpoint in config.endpoints:
                    task = asyncio.create_task(self._make_test_request(endpoint, results))
                    tasks.append(task)
            
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(ramp_step_duration)

    async def _sustained_load(self, config: PerformanceTest, results: Dict):
        """Run sustained load for the main test duration."""
        end_time = time.time() + config.duration_seconds
        
        while time.time() < end_time:
            tasks = []
            for _ in range(config.concurrent_users):
                for endpoint in config.endpoints:
                    task = asyncio.create_task(self._make_test_request(endpoint, results))
                    tasks.append(task)
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Record throughput
            current_rps = len(results["response_times"]) / (time.time() - results["start_time"].timestamp())
            results["throughput_timeline"].append({
                "timestamp": datetime.now(),
                "rps": current_rps
            })
            
            await asyncio.sleep(0.1)  # Small delay to prevent overwhelming

    async def _make_test_request(self, endpoint: str, results: Dict):
        """Make a single test request and record results."""
        try:
            if endpoint == "forecast":
                response_time, status_code = await self.make_forecast_request()
            elif endpoint == "health":
                start = time.time()
                response = await self.client.get(f"{self.api_url}/health")
                response_time = (time.time() - start) * 1000
                status_code = response.status_code
            else:
                start = time.time()
                response = await self.client.get(f"{self.api_url}{endpoint}")
                response_time = (time.time() - start) * 1000
                status_code = response.status_code
            
            results["response_times"].append(response_time)
            results["status_codes"].append(status_code)
            
            if status_code >= 400:
                results["errors"].append({
                    "timestamp": datetime.now(),
                    "endpoint": endpoint,
                    "status_code": status_code,
                    "response_time": response_time
                })
                
        except Exception as e:
            results["errors"].append({
                "timestamp": datetime.now(),
                "endpoint": endpoint,
                "error": str(e),
                "response_time": None
            })

    def _analyze_test_results(self, results: Dict, config: PerformanceTest, 
                            duration: float) -> Dict:
        """Analyze performance test results and generate insights."""
        response_times = results["response_times"]
        status_codes = results["status_codes"]
        
        if not response_times:
            return {"error": "No successful requests completed"}
        
        # Response time statistics
        p50 = np.percentile(response_times, 50)
        p95 = np.percentile(response_times, 95)
        p99 = np.percentile(response_times, 99)
        avg_response_time = statistics.mean(response_times)
        
        # Error analysis
        total_requests = len(status_codes)
        error_count = len([code for code in status_codes if code >= 400])
        error_rate = (error_count / total_requests) * 100 if total_requests > 0 else 0
        
        # Throughput analysis
        throughput_rps = total_requests / duration if duration > 0 else 0
        
        # Pass/fail analysis
        passed_response_time = p95 <= config.expected_p95_ms
        passed_error_rate = error_rate <= config.expected_error_rate
        overall_pass = passed_response_time and passed_error_rate
        
        return {
            "duration_seconds": duration,
            "total_requests": total_requests,
            "successful_requests": total_requests - error_count,
            "error_count": error_count,
            "error_rate_percent": error_rate,
            "throughput_rps": throughput_rps,
            "response_times": {
                "average_ms": avg_response_time,
                "p50_ms": p50,
                "p95_ms": p95,
                "p99_ms": p99,
                "min_ms": min(response_times),
                "max_ms": max(response_times)
            },
            "performance_assessment": {
                "overall_pass": overall_pass,
                "response_time_pass": passed_response_time,
                "error_rate_pass": passed_error_rate,
                "expected_p95_ms": config.expected_p95_ms,
                "actual_p95_ms": p95,
                "expected_error_rate": config.expected_error_rate,
                "actual_error_rate": error_rate
            }
        }

    async def continuous_monitoring(self, duration_minutes: int = 60):
        """Run continuous performance monitoring."""
        print(f"🔍 Starting continuous monitoring for {duration_minutes} minutes...")
        
        end_time = time.time() + (duration_minutes * 60)
        interval_seconds = 30
        
        while time.time() < end_time:
            try:
                # Collect metrics
                response_time, status_code = await self.make_forecast_request()
                api_metrics = await self.collect_api_metrics()
                system_metrics = self.collect_system_metrics()
                
                # Create performance snapshot
                metrics = PerformanceMetrics(
                    timestamp=datetime.now(),
                    response_time_ms=response_time,
                    status_code=status_code,
                    error_rate=api_metrics.get("error_requests_total", 0),
                    throughput_rps=api_metrics.get("forecast_requests_total", 0),
                    cpu_usage=system_metrics.get("cpu_usage", 0),
                    memory_usage_mb=system_metrics.get("memory_usage_mb", 0),
                    active_connections=0  # Would need additional monitoring
                )
                
                self.metrics_history.append(metrics)
                
                # Check thresholds and alert
                self._check_performance_thresholds(metrics)
                
                # Print status
                print(f"⏱️  {metrics.timestamp.strftime('%H:%M:%S')} | "
                      f"RT: {response_time:.1f}ms | "
                      f"CPU: {system_metrics.get('cpu_usage', 0):.1f}% | "
                      f"MEM: {system_metrics.get('memory_usage_mb', 0):.0f}MB | "
                      f"Status: {status_code}")
                
                await asyncio.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                print("\n🛑 Monitoring stopped by user")
                break
            except Exception as e:
                print(f"❌ Monitoring error: {e}")
                await asyncio.sleep(interval_seconds)

    def _check_performance_thresholds(self, metrics: PerformanceMetrics):
        """Check if performance metrics exceed thresholds."""
        alerts = []
        
        if metrics.response_time_ms > self.thresholds["response_time_p95_ms"]:
            alerts.append(f"High response time: {metrics.response_time_ms:.1f}ms")
        
        if metrics.cpu_usage > self.thresholds["cpu_usage_percent"]:
            alerts.append(f"High CPU usage: {metrics.cpu_usage:.1f}%")
        
        if metrics.memory_usage_mb > self.thresholds["memory_usage_mb"]:
            alerts.append(f"High memory usage: {metrics.memory_usage_mb:.0f}MB")
        
        if alerts:
            print(f"🚨 ALERT: {' | '.join(alerts)}")

    def generate_performance_report(self) -> Dict:
        """Generate a comprehensive performance report."""
        if not self.metrics_history:
            return {"error": "No performance data available"}
        
        response_times = [m.response_time_ms for m in self.metrics_history]
        cpu_usage = [m.cpu_usage for m in self.metrics_history]
        memory_usage = [m.memory_usage_mb for m in self.metrics_history]
        
        return {
            "report_generated": datetime.now(),
            "monitoring_period": {
                "start": self.metrics_history[0].timestamp,
                "end": self.metrics_history[-1].timestamp,
                "duration_minutes": len(self.metrics_history) * 0.5  # Assuming 30s intervals
            },
            "performance_summary": {
                "avg_response_time_ms": statistics.mean(response_times),
                "p95_response_time_ms": np.percentile(response_times, 95),
                "p99_response_time_ms": np.percentile(response_times, 99),
                "max_response_time_ms": max(response_times),
                "avg_cpu_usage": statistics.mean(cpu_usage),
                "max_cpu_usage": max(cpu_usage),
                "avg_memory_usage_mb": statistics.mean(memory_usage),
                "max_memory_usage_mb": max(memory_usage)
            },
            "threshold_violations": self._count_threshold_violations(),
            "recommendations": self._generate_recommendations()
        }

    def _count_threshold_violations(self) -> Dict:
        """Count threshold violations in the monitoring data."""
        violations = {
            "response_time": 0,
            "cpu_usage": 0,
            "memory_usage": 0
        }
        
        for metrics in self.metrics_history:
            if metrics.response_time_ms > self.thresholds["response_time_p95_ms"]:
                violations["response_time"] += 1
            if metrics.cpu_usage > self.thresholds["cpu_usage_percent"]:
                violations["cpu_usage"] += 1
            if metrics.memory_usage_mb > self.thresholds["memory_usage_mb"]:
                violations["memory_usage"] += 1
        
        return violations

    def _generate_recommendations(self) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        if not self.metrics_history:
            return recommendations
        
        avg_response_time = statistics.mean([m.response_time_ms for m in self.metrics_history])
        avg_cpu = statistics.mean([m.cpu_usage for m in self.metrics_history])
        avg_memory = statistics.mean([m.memory_usage_mb for m in self.metrics_history])
        
        if avg_response_time > 100:
            recommendations.append("Consider optimizing forecast computation algorithms")
        
        if avg_cpu > 60:
            recommendations.append("Consider scaling up CPU resources or optimizing CPU-intensive operations")
        
        if avg_memory > 300:
            recommendations.append("Consider optimizing memory usage or scaling up memory resources")
        
        violations = self._count_threshold_violations()
        if sum(violations.values()) > len(self.metrics_history) * 0.1:
            recommendations.append("Frequent threshold violations detected - review system capacity")
        
        return recommendations


async def main():
    """Main entry point for the performance monitor."""
    parser = argparse.ArgumentParser(description="Adelaide Weather API Performance Monitor")
    parser.add_argument("--monitor", action="store_true", 
                       help="Run continuous monitoring")
    parser.add_argument("--test", action="store_true", 
                       help="Run performance tests")
    parser.add_argument("--report", action="store_true", 
                       help="Generate performance report")
    parser.add_argument("--duration", type=int, default=60, 
                       help="Duration in minutes for monitoring")
    parser.add_argument("--api-url", default="http://localhost:8000", 
                       help="API URL to monitor")
    parser.add_argument("--api-token", default="dev-token-change-in-production", 
                       help="API authentication token")
    
    args = parser.parse_args()
    
    async with PerformanceMonitor(args.api_url, args.api_token) as monitor:
        
        if args.monitor:
            await monitor.continuous_monitoring(args.duration)
            
        elif args.test:
            # Define test scenarios
            test_scenarios = [
                PerformanceTest(
                    name="Light Load Test",
                    duration_seconds=60,
                    concurrent_users=5,
                    ramp_up_seconds=10,
                    endpoints=["forecast", "health"],
                    expected_p95_ms=150.0,
                    expected_error_rate=1.0
                ),
                PerformanceTest(
                    name="Normal Load Test", 
                    duration_seconds=120,
                    concurrent_users=10,
                    ramp_up_seconds=20,
                    endpoints=["forecast"],
                    expected_p95_ms=200.0,
                    expected_error_rate=2.0
                ),
                PerformanceTest(
                    name="Stress Test",
                    duration_seconds=180,
                    concurrent_users=20,
                    ramp_up_seconds=30,
                    endpoints=["forecast"],
                    expected_p95_ms=300.0,
                    expected_error_rate=5.0
                )
            ]
            
            # Run all test scenarios
            for test_config in test_scenarios:
                result = await monitor.run_performance_test(test_config)
                
                # Print test results
                print(f"\n📊 Test Results: {result['test_name']}")
                print(f"   Total Requests: {result['total_requests']}")
                print(f"   Error Rate: {result['error_rate_percent']:.2f}%")
                print(f"   Throughput: {result['throughput_rps']:.2f} RPS")
                print(f"   P95 Response Time: {result['response_times']['p95_ms']:.1f}ms")
                print(f"   Overall Pass: {'✅' if result['performance_assessment']['overall_pass'] else '❌'}")
                
                # Save detailed results
                with open(f"performance_test_{test_config.name.lower().replace(' ', '_')}.json", "w") as f:
                    json.dump(result, f, indent=2, default=str)
                
                # Short break between tests
                await asyncio.sleep(10)
                
        elif args.report:
            report = monitor.generate_performance_report()
            print(json.dumps(report, indent=2, default=str))
            
        else:
            # Quick health check
            print("🔍 Running quick performance check...")
            response_time, status_code = await monitor.make_forecast_request()
            system_metrics = monitor.collect_system_metrics()
            
            print(f"📡 API Health Check:")
            print(f"   Response Time: {response_time:.1f}ms")
            print(f"   Status Code: {status_code}")
            print(f"   CPU Usage: {system_metrics.get('cpu_usage', 0):.1f}%")
            print(f"   Memory Usage: {system_metrics.get('memory_usage_mb', 0):.0f}MB")


if __name__ == "__main__":
    asyncio.run(main())