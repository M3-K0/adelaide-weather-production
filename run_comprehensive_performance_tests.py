#!/usr/bin/env python3
"""
Comprehensive FAISS Health Monitoring Performance Test Runner
============================================================

Master test runner that orchestrates comprehensive performance testing
of the FAISS Health Monitoring system integrated with the Adelaide
Weather Forecasting API. This script coordinates both unit-level
monitoring tests and integration-level API tests.

Test Execution Strategy:
1. System Prerequisites Check
2. Baseline Performance Measurement  
3. FAISS Monitoring Performance Tests
4. API Integration Performance Tests
5. Comparative Analysis & Reporting
6. Performance Requirements Validation

Performance Requirements Validation:
- Monitoring overhead: <0.1ms per query
- Memory usage stability: no leaks
- Background monitoring: <5% CPU
- Concurrent queries: >100 simultaneous
- Health endpoint: <50ms response time
- API overall: >95% success rate

Author: Performance Specialist
Version: 1.0.0 - Comprehensive Performance Testing
"""

import asyncio
import subprocess
import sys
import os
import json
import time
import psutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import shutil

class PerformanceTestOrchestrator:
    """Orchestrates comprehensive performance testing of FAISS monitoring system."""
    
    def __init__(self, output_dir: str = "performance_test_results"):
        """Initialize test orchestrator.
        
        Args:
            output_dir: Directory to store test results and reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Test configuration
        self.api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        self.api_token = os.getenv("API_TOKEN")
        
        # Test results
        self.test_results = {
            "orchestrator_info": {
                "start_time": datetime.now(timezone.utc).isoformat(),
                "api_base_url": self.api_base_url,
                "test_output_dir": str(self.output_dir),
                "system_info": self._get_system_info()
            },
            "prerequisites": {},
            "monitoring_tests": {},
            "api_tests": {},
            "comparative_analysis": {},
            "requirements_validation": {},
            "summary": {}
        }
        
        print("🎯 FAISS Health Monitoring Comprehensive Performance Testing")
        print("=" * 65)
        print(f"📁 Output directory: {self.output_dir}")
        print(f"🌐 API URL: {self.api_base_url}")
        print(f"🔑 API Token: {'Configured' if self.api_token else 'Not configured'}")
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for test context."""
        try:
            return {
                "platform": sys.platform,
                "python_version": sys.version,
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": psutil.virtual_memory().total / (1024**3),
                "disk_free_gb": shutil.disk_usage('.').free / (1024**3)
            }
        except Exception as e:
            return {"error": f"Failed to get system info: {e}"}
    
    async def check_prerequisites(self) -> bool:
        """Check system prerequisites for performance testing.
        
        Returns:
            True if all prerequisites are met
        """
        print("\n🔍 Checking Performance Test Prerequisites...")
        
        prerequisites = {
            "python_version": False,
            "required_packages": False,
            "test_files_exist": False,
            "system_resources": False,
            "api_accessibility": False
        }
        
        # Check Python version
        if sys.version_info >= (3, 8):
            prerequisites["python_version"] = True
            print("✅ Python version >= 3.8")
        else:
            print(f"❌ Python version {sys.version} < 3.8")
        
        # Check required packages
        required_packages = [
            "numpy", "pandas", "psutil", "aiohttp", 
            "fastapi", "prometheus_client", "memory_profiler"
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        if not missing_packages:
            prerequisites["required_packages"] = True
            print("✅ All required packages available")
        else:
            print(f"❌ Missing packages: {missing_packages}")
        
        # Check test files exist
        test_files = [
            "test_faiss_monitoring_performance.py",
            "api_performance_integration_test.py"
        ]
        
        all_files_exist = True
        for test_file in test_files:
            if not Path(test_file).exists():
                print(f"❌ Missing test file: {test_file}")
                all_files_exist = False
        
        if all_files_exist:
            prerequisites["test_files_exist"] = True
            print("✅ All test files available")
        
        # Check system resources
        memory_gb = psutil.virtual_memory().total / (1024**3)
        disk_free_gb = shutil.disk_usage('.').free / (1024**3)
        
        if memory_gb >= 4 and disk_free_gb >= 1:
            prerequisites["system_resources"] = True
            print(f"✅ Sufficient resources: {memory_gb:.1f}GB RAM, {disk_free_gb:.1f}GB disk")
        else:
            print(f"❌ Insufficient resources: {memory_gb:.1f}GB RAM, {disk_free_gb:.1f}GB disk")
        
        # Check API accessibility (optional)
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        prerequisites["api_accessibility"] = True
                        print("✅ API is accessible")
                    else:
                        print(f"⚠️ API returned status {response.status}")
        except Exception as e:
            print(f"⚠️ API accessibility check failed: {e}")
            print("   (API tests may be skipped)")
        
        # Store results
        self.test_results["prerequisites"] = prerequisites
        
        # Overall prerequisite status
        essential_prerequisites = ["python_version", "required_packages", "test_files_exist", "system_resources"]
        all_essential_met = all(prerequisites[key] for key in essential_prerequisites)
        
        if all_essential_met:
            print("✅ All essential prerequisites met - proceeding with tests")
            return True
        else:
            print("❌ Some essential prerequisites not met - tests may fail")
            return False
    
    async def run_monitoring_performance_tests(self) -> bool:
        """Run FAISS monitoring performance tests.
        
        Returns:
            True if tests completed successfully
        """
        print("\n🧪 Running FAISS Monitoring Performance Tests...")
        
        try:
            # Run the monitoring performance test script
            start_time = time.time()
            
            process = await asyncio.create_subprocess_exec(
                sys.executable, "test_faiss_monitoring_performance.py",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd="."
            )
            
            stdout, _ = await process.communicate()
            end_time = time.time()
            
            # Parse output
            output_text = stdout.decode('utf-8')
            
            # Save raw output
            with open(self.output_dir / "monitoring_tests_output.log", "w") as f:
                f.write(output_text)
            
            # Try to load JSON report if generated
            monitoring_report = {}
            report_file = Path("faiss_monitoring_performance_report.json")
            if report_file.exists():
                with open(report_file, "r") as f:
                    monitoring_report = json.load(f)
                
                # Move to output directory
                shutil.move(str(report_file), str(self.output_dir / "faiss_monitoring_performance_report.json"))
            
            # Store results
            self.test_results["monitoring_tests"] = {
                "success": process.returncode == 0,
                "duration_seconds": end_time - start_time,
                "output_lines": len(output_text.split('\n')),
                "report_data": monitoring_report
            }
            
            if process.returncode == 0:
                print(f"✅ Monitoring performance tests completed in {end_time - start_time:.1f}s")
                return True
            else:
                print(f"❌ Monitoring performance tests failed (exit code: {process.returncode})")
                return False
                
        except Exception as e:
            print(f"❌ Failed to run monitoring performance tests: {e}")
            self.test_results["monitoring_tests"] = {
                "success": False,
                "error": str(e)
            }
            return False
    
    async def run_api_performance_tests(self) -> bool:
        """Run API integration performance tests.
        
        Returns:
            True if tests completed successfully
        """
        print("\n🌐 Running API Integration Performance Tests...")
        
        if not self.test_results["prerequisites"].get("api_accessibility", False):
            print("⚠️ Skipping API tests - API not accessible")
            self.test_results["api_tests"] = {"skipped": True, "reason": "API not accessible"}
            return True
        
        try:
            # Set environment variables for API tests
            env = os.environ.copy()
            env["API_BASE_URL"] = self.api_base_url
            if self.api_token:
                env["API_TOKEN"] = self.api_token
            
            # Run the API performance test script
            start_time = time.time()
            
            process = await asyncio.create_subprocess_exec(
                sys.executable, "api_performance_integration_test.py",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
                cwd="."
            )
            
            stdout, _ = await process.communicate()
            end_time = time.time()
            
            # Parse output
            output_text = stdout.decode('utf-8')
            
            # Save raw output
            with open(self.output_dir / "api_tests_output.log", "w") as f:
                f.write(output_text)
            
            # Try to load JSON report if generated
            api_report = {}
            report_file = Path("api_performance_integration_report.json")
            if report_file.exists():
                with open(report_file, "r") as f:
                    api_report = json.load(f)
                
                # Move to output directory
                shutil.move(str(report_file), str(self.output_dir / "api_performance_integration_report.json"))
            
            # Store results
            self.test_results["api_tests"] = {
                "success": process.returncode == 0,
                "duration_seconds": end_time - start_time,
                "output_lines": len(output_text.split('\n')),
                "report_data": api_report
            }
            
            if process.returncode == 0:
                print(f"✅ API performance tests completed in {end_time - start_time:.1f}s")
                return True
            else:
                print(f"❌ API performance tests failed (exit code: {process.returncode})")
                return False
                
        except Exception as e:
            print(f"❌ Failed to run API performance tests: {e}")
            self.test_results["api_tests"] = {
                "success": False,
                "error": str(e)
            }
            return False
    
    def analyze_comparative_performance(self):
        """Analyze comparative performance between monitoring and API tests."""
        print("\n📊 Performing Comparative Performance Analysis...")
        
        analysis = {
            "monitoring_vs_api_consistency": False,
            "performance_correlation": {},
            "recommendations": []
        }
        
        try:
            # Extract key metrics from both test suites
            monitoring_data = self.test_results.get("monitoring_tests", {}).get("report_data", {})
            api_data = self.test_results.get("api_tests", {}).get("report_data", {})
            
            if monitoring_data and api_data:
                # Compare response times
                if "test_results" in monitoring_data:
                    monitoring_latencies = []
                    for test in monitoring_data["test_results"]:
                        if test.get("latency_statistics", {}).get("mean_ms"):
                            monitoring_latencies.append(test["latency_statistics"]["mean_ms"])
                
                if "api_performance_test_report" in api_data and "test_results" in api_data["api_performance_test_report"]:
                    api_latencies = []
                    for test in api_data["api_performance_test_report"]["test_results"]:
                        if test.get("response_time_percentiles", {}).get("mean"):
                            api_latencies.append(test["response_time_percentiles"]["mean"])
                
                # Basic consistency check
                if monitoring_latencies and api_latencies:
                    analysis["performance_correlation"] = {
                        "monitoring_mean_latency": sum(monitoring_latencies) / len(monitoring_latencies),
                        "api_mean_latency": sum(api_latencies) / len(api_latencies),
                        "latency_samples": {
                            "monitoring_count": len(monitoring_latencies),
                            "api_count": len(api_latencies)
                        }
                    }
                    
                    # Check if results are reasonably consistent
                    monitoring_avg = analysis["performance_correlation"]["monitoring_mean_latency"]
                    api_avg = analysis["performance_correlation"]["api_mean_latency"]
                    
                    # API latency should be higher (includes HTTP overhead)
                    if api_avg > monitoring_avg:
                        analysis["monitoring_vs_api_consistency"] = True
                        print("✅ Performance correlation looks reasonable (API > monitoring latency)")
                    else:
                        print("⚠️ Unexpected performance correlation (API latency lower than monitoring)")
            
            # Generate recommendations
            if monitoring_data.get("performance_requirements"):
                requirements = monitoring_data["performance_requirements"]
                
                recommendations = []
                
                # Check overhead requirement
                if requirements.get("max_monitoring_overhead_ms", 0) > 0.05:
                    recommendations.append("Consider optimizing monitoring overhead - target is <0.1ms")
                
                # Check memory requirements
                if "memory_leak_threshold_mb" in requirements:
                    recommendations.append("Monitor memory usage in production for leak detection")
                
                # Check CPU requirements
                if requirements.get("max_background_cpu_percent", 0) > 3:
                    recommendations.append("Background monitoring CPU usage could be optimized")
                
                analysis["recommendations"] = recommendations
            
            self.test_results["comparative_analysis"] = analysis
            
            print(f"📈 Comparative analysis completed")
            if analysis["recommendations"]:
                print("💡 Recommendations:")
                for rec in analysis["recommendations"]:
                    print(f"   - {rec}")
            
        except Exception as e:
            print(f"⚠️ Comparative analysis failed: {e}")
            self.test_results["comparative_analysis"] = {"error": str(e)}
    
    def validate_performance_requirements(self) -> Dict[str, bool]:
        """Validate all performance requirements across test suites.
        
        Returns:
            Dictionary of requirement validation results
        """
        print("\n🎯 Validating Performance Requirements...")
        
        validation_results = {
            "monitoring_overhead_ms": False,
            "memory_stability": False,
            "background_cpu_percent": False,
            "concurrent_queries": False,
            "health_endpoint_latency_ms": False,
            "api_success_rate": False,
            "overall_system_performance": False
        }
        
        try:
            # Extract data from test results
            monitoring_data = self.test_results.get("monitoring_tests", {}).get("report_data", {})
            api_data = self.test_results.get("api_tests", {}).get("report_data", {})
            
            # Validate monitoring requirements
            if monitoring_data.get("summary", {}).get("requirements_met"):
                monitoring_reqs = monitoring_data["summary"]["requirements_met"]
                
                validation_results["monitoring_overhead_ms"] = monitoring_reqs.get("monitoring_overhead", False)
                validation_results["memory_stability"] = monitoring_reqs.get("memory_stability", False)
                validation_results["background_cpu_percent"] = monitoring_reqs.get("background_cpu_usage", False)
                validation_results["concurrent_queries"] = monitoring_reqs.get("concurrent_queries", False)
                validation_results["health_endpoint_latency_ms"] = monitoring_reqs.get("health_endpoint_latency", False)
            
            # Validate API requirements
            if api_data.get("api_performance_test_report", {}).get("summary", {}).get("requirements_compliance"):
                api_reqs = api_data["api_performance_test_report"]["summary"]["requirements_compliance"]
                
                validation_results["api_success_rate"] = api_reqs.get("system_stability", False)
                if not validation_results["health_endpoint_latency_ms"]:  # Override if not set from monitoring
                    validation_results["health_endpoint_latency_ms"] = api_reqs.get("health_endpoint_latency", False)
                if not validation_results["concurrent_queries"]:  # Override if not set from monitoring
                    validation_results["concurrent_queries"] = api_reqs.get("concurrent_request_handling", False)
            
            # Overall system performance (all critical requirements met)
            critical_requirements = [
                "monitoring_overhead_ms",
                "health_endpoint_latency_ms", 
                "concurrent_queries",
                "api_success_rate"
            ]
            
            validation_results["overall_system_performance"] = all(
                validation_results[req] for req in critical_requirements
            )
            
            # Print validation results
            print("📋 Performance Requirements Validation:")
            for requirement, passed in validation_results.items():
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"   {requirement}: {status}")
            
            # Overall assessment
            if validation_results["overall_system_performance"]:
                print("\n🎉 ALL CRITICAL PERFORMANCE REQUIREMENTS MET!")
                print("   The FAISS Health Monitoring system is ready for production deployment.")
            else:
                print("\n⚠️ Some performance requirements not met.")
                print("   Review failed requirements before production deployment.")
            
            self.test_results["requirements_validation"] = validation_results
            return validation_results
            
        except Exception as e:
            print(f"❌ Performance requirements validation failed: {e}")
            self.test_results["requirements_validation"] = {"error": str(e)}
            return validation_results
    
    def generate_executive_summary(self):
        """Generate executive summary of all performance testing."""
        print("\n📄 Generating Executive Summary...")
        
        summary = {
            "test_execution": {
                "start_time": self.test_results["orchestrator_info"]["start_time"],
                "end_time": datetime.now(timezone.utc).isoformat(),
                "total_duration_minutes": 0,
                "tests_executed": []
            },
            "performance_assessment": {
                "overall_grade": "Unknown",
                "critical_requirements_met": False,
                "monitoring_overhead_acceptable": False,
                "api_performance_acceptable": False,
                "system_ready_for_production": False
            },
            "key_findings": [],
            "recommendations": []
        }
        
        try:
            # Calculate test duration
            start_time = datetime.fromisoformat(self.test_results["orchestrator_info"]["start_time"].replace('Z', '+00:00'))
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds() / 60
            summary["test_execution"]["total_duration_minutes"] = round(duration, 1)
            
            # Track executed tests
            if self.test_results.get("monitoring_tests", {}).get("success"):
                summary["test_execution"]["tests_executed"].append("FAISS Monitoring Performance Tests")
            
            if self.test_results.get("api_tests", {}).get("success"):
                summary["test_execution"]["tests_executed"].append("API Integration Performance Tests")
            elif not self.test_results.get("api_tests", {}).get("skipped"):
                summary["test_execution"]["tests_executed"].append("API Tests (Failed)")
            
            # Assess performance
            validation_results = self.test_results.get("requirements_validation", {})
            
            if validation_results.get("overall_system_performance"):
                summary["performance_assessment"]["overall_grade"] = "A - Excellent"
                summary["performance_assessment"]["system_ready_for_production"] = True
                summary["key_findings"].append("All critical performance requirements met")
            elif validation_results.get("monitoring_overhead_ms") and validation_results.get("health_endpoint_latency_ms"):
                summary["performance_assessment"]["overall_grade"] = "B - Good"
                summary["key_findings"].append("Core performance requirements met, some optimizations possible")
            else:
                summary["performance_assessment"]["overall_grade"] = "C - Needs Improvement"
                summary["key_findings"].append("Performance requirements not fully met")
            
            summary["performance_assessment"]["critical_requirements_met"] = validation_results.get("overall_system_performance", False)
            summary["performance_assessment"]["monitoring_overhead_acceptable"] = validation_results.get("monitoring_overhead_ms", False)
            summary["performance_assessment"]["api_performance_acceptable"] = validation_results.get("api_success_rate", False)
            
            # Generate recommendations
            recommendations = []
            
            if not validation_results.get("monitoring_overhead_ms"):
                recommendations.append("Optimize FAISS monitoring overhead to meet <0.1ms requirement")
            
            if not validation_results.get("health_endpoint_latency_ms"):
                recommendations.append("Optimize health endpoint response time to meet <50ms requirement")
            
            if not validation_results.get("concurrent_queries"):
                recommendations.append("Improve concurrent query handling capacity")
            
            if not validation_results.get("api_success_rate"):
                recommendations.append("Investigate API stability issues affecting success rate")
            
            if not recommendations:
                recommendations.append("System performance is excellent - monitor in production")
                recommendations.append("Consider implementing automated performance regression testing")
            
            summary["recommendations"] = recommendations
            
            # Store in results
            self.test_results["summary"] = summary
            
            print("✅ Executive summary generated")
            
        except Exception as e:
            print(f"⚠️ Executive summary generation failed: {e}")
            self.test_results["summary"] = {"error": str(e)}
    
    def save_comprehensive_report(self):
        """Save comprehensive performance test report to file."""
        print("\n💾 Saving Comprehensive Performance Report...")
        
        try:
            # Generate final report
            report_path = self.output_dir / "comprehensive_performance_report.json"
            
            with open(report_path, "w") as f:
                json.dump(self.test_results, f, indent=2, default=str)
            
            # Generate human-readable summary
            summary_path = self.output_dir / "performance_test_summary.txt"
            
            with open(summary_path, "w") as f:
                f.write("FAISS Health Monitoring Performance Test Summary\n")
                f.write("=" * 50 + "\n\n")
                
                summary = self.test_results.get("summary", {})
                
                f.write(f"Test Duration: {summary.get('test_execution', {}).get('total_duration_minutes', 0):.1f} minutes\n")
                f.write(f"Overall Grade: {summary.get('performance_assessment', {}).get('overall_grade', 'Unknown')}\n")
                f.write(f"Production Ready: {summary.get('performance_assessment', {}).get('system_ready_for_production', False)}\n\n")
                
                f.write("Requirements Validation:\n")
                validation = self.test_results.get("requirements_validation", {})
                for req, passed in validation.items():
                    if isinstance(passed, bool):
                        status = "PASS" if passed else "FAIL"
                        f.write(f"  - {req}: {status}\n")
                
                f.write("\nKey Findings:\n")
                for finding in summary.get("key_findings", []):
                    f.write(f"  - {finding}\n")
                
                f.write("\nRecommendations:\n")
                for rec in summary.get("recommendations", []):
                    f.write(f"  - {rec}\n")
            
            print(f"✅ Comprehensive report saved to: {report_path}")
            print(f"📄 Human-readable summary saved to: {summary_path}")
            
        except Exception as e:
            print(f"❌ Failed to save comprehensive report: {e}")
    
    def print_final_dashboard(self):
        """Print final performance test dashboard."""
        print("\n" + "="*80)
        print("🏁 FAISS HEALTH MONITORING PERFORMANCE TEST DASHBOARD")
        print("="*80)
        
        summary = self.test_results.get("summary", {})
        validation = self.test_results.get("requirements_validation", {})
        
        # Test execution info
        exec_info = summary.get("test_execution", {})
        print(f"⏱️ Total Test Duration: {exec_info.get('total_duration_minutes', 0):.1f} minutes")
        print(f"🧪 Tests Executed: {', '.join(exec_info.get('tests_executed', []))}")
        
        # Performance assessment
        perf_assessment = summary.get("performance_assessment", {})
        print(f"\n🎯 Overall Performance Grade: {perf_assessment.get('overall_grade', 'Unknown')}")
        
        # Requirements summary
        print(f"\n📋 Critical Requirements Status:")
        critical_reqs = [
            ("Monitoring Overhead", validation.get("monitoring_overhead_ms", False)),
            ("Health Endpoint Latency", validation.get("health_endpoint_latency_ms", False)),
            ("Concurrent Query Handling", validation.get("concurrent_queries", False)),
            ("API Success Rate", validation.get("api_success_rate", False))
        ]
        
        for req_name, passed in critical_reqs:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {req_name}: {status}")
        
        # Production readiness
        ready = perf_assessment.get("system_ready_for_production", False)
        readiness_status = "✅ READY" if ready else "⚠️ NEEDS WORK"
        print(f"\n🚀 Production Readiness: {readiness_status}")
        
        # Key insights
        findings = summary.get("key_findings", [])
        if findings:
            print(f"\n💡 Key Findings:")
            for finding in findings[:3]:  # Show top 3
                print(f"   • {finding}")
        
        # Recommendations
        recommendations = summary.get("recommendations", [])
        if recommendations:
            print(f"\n🔧 Top Recommendations:")
            for rec in recommendations[:3]:  # Show top 3
                print(f"   • {rec}")
        
        # Output files
        print(f"\n📁 Results Location: {self.output_dir}")
        print(f"   📊 Comprehensive Report: comprehensive_performance_report.json")
        print(f"   📄 Executive Summary: performance_test_summary.txt")
        
        print("\n" + "="*80)

async def main():
    """Main performance testing orchestration workflow."""
    orchestrator = PerformanceTestOrchestrator()
    
    try:
        # Step 1: Check prerequisites
        prerequisites_ok = await orchestrator.check_prerequisites()
        if not prerequisites_ok:
            print("⚠️ Some prerequisites not met - proceeding anyway...")
        
        # Step 2: Run monitoring performance tests
        monitoring_success = await orchestrator.run_monitoring_performance_tests()
        
        # Step 3: Run API integration tests
        api_success = await orchestrator.run_api_performance_tests()
        
        # Step 4: Comparative analysis
        orchestrator.analyze_comparative_performance()
        
        # Step 5: Validate requirements
        orchestrator.validate_performance_requirements()
        
        # Step 6: Generate executive summary
        orchestrator.generate_executive_summary()
        
        # Step 7: Save comprehensive report
        orchestrator.save_comprehensive_report()
        
        # Step 8: Display final dashboard
        orchestrator.print_final_dashboard()
        
        print("\n🎉 Comprehensive performance testing completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Performance testing interrupted by user")
    except Exception as e:
        print(f"\n💥 Performance testing orchestration failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())