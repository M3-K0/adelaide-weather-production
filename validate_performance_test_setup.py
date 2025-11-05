#!/usr/bin/env python3
"""
Performance Test Setup Validator
===============================

Validates that the FAISS Health Monitoring performance testing framework
is properly configured and ready for execution. This script checks all
prerequisites and performs basic functionality tests.

Author: Performance Specialist
Version: 1.0.0 - Setup Validation
"""

import sys
import os
import asyncio
import importlib
from pathlib import Path
from typing import Dict, List, Tuple

class PerformanceTestValidator:
    """Validates performance testing setup and configuration."""
    
    def __init__(self):
        self.validation_results = {}
        self.passed_checks = 0
        self.failed_checks = 0
        
    def check_python_version(self) -> bool:
        """Check Python version compatibility."""
        print("🐍 Checking Python version...")
        
        if sys.version_info >= (3, 8):
            print(f"   ✅ Python {sys.version.split()[0]} (>= 3.8 required)")
            return True
        else:
            print(f"   ❌ Python {sys.version.split()[0]} (>= 3.8 required)")
            return False
    
    def check_required_packages(self) -> Dict[str, bool]:
        """Check if all required packages are available."""
        print("\n📦 Checking required packages...")
        
        required_packages = {
            'numpy': False,
            'pandas': False,
            'psutil': False,
            'aiohttp': False,
            'fastapi': False,
            'prometheus_client': False,
            'asyncio': False  # Built-in, should always be available
        }
        
        for package in required_packages:
            try:
                importlib.import_module(package)
                required_packages[package] = True
                print(f"   ✅ {package}")
            except ImportError:
                print(f"   ❌ {package} (not installed)")
        
        return required_packages
    
    def check_test_files(self) -> Dict[str, bool]:
        """Check if all test files exist."""
        print("\n📁 Checking test files...")
        
        test_files = {
            'test_faiss_monitoring_performance.py': False,
            'api_performance_integration_test.py': False,
            'run_comprehensive_performance_tests.py': False,
            'api/services/faiss_health_monitoring.py': False,
            'examples/run_performance_tests_demo.py': False
        }
        
        for file_path in test_files:
            if Path(file_path).exists():
                test_files[file_path] = True
                print(f"   ✅ {file_path}")
            else:
                print(f"   ❌ {file_path} (missing)")
        
        return test_files
    
    def check_system_resources(self) -> Dict[str, bool]:
        """Check available system resources."""
        print("\n💻 Checking system resources...")
        
        resources = {
            'memory': False,
            'disk_space': False,
            'cpu_cores': False
        }
        
        try:
            import psutil
            
            # Check memory (minimum 2GB)
            memory_gb = psutil.virtual_memory().total / (1024**3)
            if memory_gb >= 2:
                resources['memory'] = True
                print(f"   ✅ Memory: {memory_gb:.1f} GB (>= 2GB required)")
            else:
                print(f"   ❌ Memory: {memory_gb:.1f} GB (>= 2GB required)")
            
            # Check disk space (minimum 1GB free)
            import shutil
            disk_free_gb = shutil.disk_usage('.').free / (1024**3)
            if disk_free_gb >= 1:
                resources['disk_space'] = True
                print(f"   ✅ Disk space: {disk_free_gb:.1f} GB free (>= 1GB required)")
            else:
                print(f"   ❌ Disk space: {disk_free_gb:.1f} GB free (>= 1GB required)")
            
            # Check CPU cores (minimum 2)
            cpu_count = psutil.cpu_count()
            if cpu_count >= 2:
                resources['cpu_cores'] = True
                print(f"   ✅ CPU cores: {cpu_count} (>= 2 required)")
            else:
                print(f"   ❌ CPU cores: {cpu_count} (>= 2 required)")
                
        except ImportError:
            print("   ⚠️ psutil not available - cannot check system resources")
        
        return resources
    
    async def test_basic_monitoring_functionality(self) -> bool:
        """Test basic FAISS health monitoring functionality."""
        print("\n🔍 Testing basic monitoring functionality...")
        
        try:
            # Try to import the monitoring system
            from api.services.faiss_health_monitoring import FAISSHealthMonitor
            from prometheus_client import CollectorRegistry
            
            print("   ✅ FAISS health monitoring module imported")
            
            # Initialize monitor
            registry = CollectorRegistry()
            monitor = FAISSHealthMonitor(registry=registry)
            print("   ✅ Health monitor initialized")
            
            # Start monitoring
            await monitor.start_monitoring()
            print("   ✅ Monitoring started")
            
            # Test query tracking
            async with monitor.track_query("24h", k_neighbors=10) as query:
                await asyncio.sleep(0.001)  # Simulate 1ms work
            print("   ✅ Query tracking functional")
            
            # Get health summary
            health = await monitor.get_health_summary()
            print(f"   ✅ Health summary generated (status: {health['status']})")
            
            # Stop monitoring
            await monitor.stop_monitoring()
            print("   ✅ Monitoring stopped gracefully")
            
            return True
            
        except ImportError as e:
            print(f"   ❌ Import failed: {e}")
            return False
        except Exception as e:
            print(f"   ❌ Functionality test failed: {e}")
            return False
    
    def check_optional_components(self) -> Dict[str, bool]:
        """Check optional components for enhanced testing."""
        print("\n🔧 Checking optional components...")
        
        optional = {
            'pytest': False,
            'memory_profiler': False,
            'matplotlib': False,
            'api_server': False
        }
        
        # Check optional packages
        for package in ['pytest', 'memory_profiler', 'matplotlib']:
            try:
                importlib.import_module(package)
                optional[package] = True
                print(f"   ✅ {package} (optional)")
            except ImportError:
                print(f"   ⚠️ {package} (optional - not installed)")
        
        # Check if API server is running
        try:
            import aiohttp
            import asyncio
            
            async def check_api():
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get("http://localhost:8000/health", timeout=aiohttp.ClientTimeout(total=2)) as response:
                            return response.status == 200
                except:
                    return False
            
            api_available = asyncio.run(check_api())
            optional['api_server'] = api_available
            
            if api_available:
                print("   ✅ API server running on localhost:8000")
            else:
                print("   ⚠️ API server not running on localhost:8000 (API tests will be skipped)")
                
        except:
            print("   ⚠️ Cannot check API server status")
        
        return optional
    
    def generate_setup_report(self) -> Dict:
        """Generate comprehensive setup validation report."""
        print("\n📊 Generating setup validation report...")
        
        report = {
            "validation_timestamp": "2024-11-02T12:00:00Z",
            "overall_status": "unknown",
            "python_version": self.validation_results.get("python_version", False),
            "required_packages": self.validation_results.get("required_packages", {}),
            "test_files": self.validation_results.get("test_files", {}),
            "system_resources": self.validation_results.get("system_resources", {}),
            "monitoring_functionality": self.validation_results.get("monitoring_functionality", False),
            "optional_components": self.validation_results.get("optional_components", {}),
            "recommendations": []
        }
        
        # Calculate overall status
        essential_checks = [
            report["python_version"],
            all(report["required_packages"].values()),
            all(report["test_files"].values()),
            all(report["system_resources"].values()),
            report["monitoring_functionality"]
        ]
        
        if all(essential_checks):
            report["overall_status"] = "ready"
        elif sum(essential_checks) >= 3:
            report["overall_status"] = "mostly_ready"
        else:
            report["overall_status"] = "not_ready"
        
        # Generate recommendations
        recommendations = []
        
        if not report["python_version"]:
            recommendations.append("Upgrade Python to version 3.8 or higher")
        
        missing_packages = [pkg for pkg, available in report["required_packages"].items() if not available]
        if missing_packages:
            recommendations.append(f"Install missing packages: {', '.join(missing_packages)}")
        
        missing_files = [file for file, exists in report["test_files"].items() if not exists]
        if missing_files:
            recommendations.append(f"Create missing test files: {', '.join(missing_files)}")
        
        if not all(report["system_resources"].values()):
            recommendations.append("Ensure sufficient system resources (2GB RAM, 1GB disk, 2 CPU cores)")
        
        if not report["monitoring_functionality"]:
            recommendations.append("Fix FAISS health monitoring functionality issues")
        
        if not report["optional_components"].get("api_server", False):
            recommendations.append("Start API server on localhost:8000 for complete testing")
        
        report["recommendations"] = recommendations
        
        return report
    
    async def run_comprehensive_validation(self) -> Dict:
        """Run comprehensive validation of performance test setup."""
        print("🎯 FAISS Performance Test Setup Validation")
        print("=" * 50)
        
        # Run all validation checks
        self.validation_results["python_version"] = self.check_python_version()
        self.validation_results["required_packages"] = self.check_required_packages()
        self.validation_results["test_files"] = self.check_test_files()
        self.validation_results["system_resources"] = self.check_system_resources()
        self.validation_results["monitoring_functionality"] = await self.test_basic_monitoring_functionality()
        self.validation_results["optional_components"] = self.check_optional_components()
        
        # Generate report
        report = self.generate_setup_report()
        
        # Print summary
        print("\n" + "="*50)
        print("📋 VALIDATION SUMMARY")
        print("="*50)
        
        status_emoji = {
            "ready": "✅",
            "mostly_ready": "⚠️",
            "not_ready": "❌"
        }
        
        emoji = status_emoji.get(report["overall_status"], "❓")
        print(f"{emoji} Overall Status: {report['overall_status'].upper()}")
        
        if report["recommendations"]:
            print("\n🔧 Recommendations:")
            for rec in report["recommendations"]:
                print(f"   • {rec}")
        
        if report["overall_status"] == "ready":
            print("\n🚀 System is ready for performance testing!")
            print("   Run: python run_comprehensive_performance_tests.py")
        elif report["overall_status"] == "mostly_ready":
            print("\n⚠️ System is mostly ready - some tests may be skipped")
            print("   You can proceed with limited testing")
        else:
            print("\n❌ System is not ready for performance testing")
            print("   Please address the recommendations above")
        
        return report

async def main():
    """Main validation workflow."""
    validator = PerformanceTestValidator()
    
    try:
        report = await validator.run_comprehensive_validation()
        
        # Save validation report
        import json
        with open("performance_test_validation_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Validation report saved: performance_test_validation_report.json")
        
        # Exit with appropriate code
        if report["overall_status"] == "ready":
            sys.exit(0)
        elif report["overall_status"] == "mostly_ready":
            sys.exit(1)
        else:
            sys.exit(2)
            
    except KeyboardInterrupt:
        print("\n⏹️ Validation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Validation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())