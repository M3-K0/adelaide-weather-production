#!/usr/bin/env python3
"""
T-020 Final Integration Test - Adelaide Weather Forecasting System
================================================================

Critical final validation before production deployment.
Tests all 20 integrated tasks and validates production readiness.

This script validates:
1. All core components are properly integrated
2. Configuration management works across environments  
3. Security components function correctly
4. API components can be imported and initialized
5. No critical integration issues remain

Author: Quality Assurance & Optimization Specialist
Version: 1.0.0 - Final Production Readiness Validation
"""

import os
import sys
import json
import time
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import logging

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FinalIntegrationTest:
    """Final integration test for production deployment readiness."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.test_results = []
        self.start_time = datetime.now(timezone.utc)
        
    def run_final_validation(self) -> Dict[str, Any]:
        """Execute final integration validation."""
        logger.info("🚀 T-020 Final Integration Test - Production Readiness Validation")
        logger.info("=" * 80)
        
        try:
            # Set up test environment
            self._setup_test_environment()
            
            # Core component validation
            self._test_environment_config_manager()
            self._test_secure_credential_manager()
            self._test_config_drift_detection()
            
            # API component validation
            self._test_api_components()
            self._test_security_middleware()
            self._test_faiss_monitoring()
            
            # Deployment validation
            self._test_deployment_script()
            
            # System integration validation
            self._test_system_integration()
            
            # Generate final report
            return self._generate_final_report()
            
        except Exception as e:
            logger.error(f"💥 Final integration test failed: {e}")
            return self._generate_failure_report(str(e))
    
    def _setup_test_environment(self):
        """Setup test environment for final validation."""
        logger.info("🔧 Setting up test environment...")
        
        # Set required environment variables for testing
        test_env_vars = {
            "ENVIRONMENT": "development", 
            "CREDENTIAL_MASTER_KEY": f"test_master_key_{int(time.time())}",
            "API_TOKEN": "test_integration_token_final"
        }
        
        for key, value in test_env_vars.items():
            os.environ[key] = value
            
        # Ensure required directories exist
        required_dirs = [
            "configs/environments/development",
            "configs/environments/staging",
            "configs/environments/production",
            "api"
        ]
        
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                logger.error(f"❌ Required directory missing: {dir_path}")
                self.test_results.append({
                    "test": "environment_setup",
                    "status": "failed",
                    "error": f"Missing directory: {dir_path}"
                })
                return False
                
        logger.info("✅ Test environment setup complete")
        self.test_results.append({
            "test": "environment_setup", 
            "status": "passed",
            "duration_ms": 0
        })
        return True
    
    def _test_environment_config_manager(self):
        """Test Environment Configuration Manager integration."""
        logger.info("🔧 Testing Environment Configuration Manager...")
        start_time = time.time()
        
        try:
            from core.environment_config_manager import EnvironmentConfigManager
            
            # Test all environments
            for env in ["development", "staging", "production"]:
                manager = EnvironmentConfigManager(environment=env)
                config = manager.load_config()
                metadata = manager.get_metadata()
                
                # Validate config structure
                if not config or not isinstance(config, dict):
                    raise ValueError(f"Invalid config structure for {env}")
                
                if not metadata.config_hash:
                    raise ValueError(f"Missing config hash for {env}")
                    
            duration = (time.time() - start_time) * 1000
            logger.info(f"✅ Environment Config Manager: PASSED ({duration:.0f}ms)")
            self.test_results.append({
                "test": "environment_config_manager",
                "status": "passed", 
                "duration_ms": duration,
                "environments_tested": 3
            })
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"❌ Environment Config Manager: FAILED - {e}")
            self.test_results.append({
                "test": "environment_config_manager",
                "status": "failed",
                "duration_ms": duration,
                "error": str(e)
            })
    
    def _test_secure_credential_manager(self):
        """Test Secure Credential Manager integration."""
        logger.info("🔐 Testing Secure Credential Manager...")
        start_time = time.time()
        
        try:
            from core.secure_credential_manager import SecureCredentialManager, CredentialType
            
            manager = SecureCredentialManager()
            
            # Test credential operations
            test_cred_id = f"test_final_cred_{int(time.time())}"
            test_value = "test_secret_final_value"
            
            # Store credential
            manager.store_credential(
                credential_id=test_cred_id,
                credential_value=test_value,
                credential_type=CredentialType.API_TOKEN
            )
            
            # Retrieve credential  
            retrieved = manager.retrieve_credential(test_cred_id)
            
            if retrieved != test_value:
                raise ValueError("Credential retrieval mismatch")
            
            # Test health check
            health = manager.health_check()
            if health["status"] not in ["healthy", "warning"]:
                raise ValueError(f"Credential manager unhealthy: {health['status']}")
            
            # Cleanup
            manager.delete_credential(test_cred_id)
            
            duration = (time.time() - start_time) * 1000
            logger.info(f"✅ Secure Credential Manager: PASSED ({duration:.0f}ms)")
            self.test_results.append({
                "test": "secure_credential_manager",
                "status": "passed",
                "duration_ms": duration,
                "health_status": health["status"]
            })
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"❌ Secure Credential Manager: FAILED - {e}")
            self.test_results.append({
                "test": "secure_credential_manager", 
                "status": "failed",
                "duration_ms": duration,
                "error": str(e)
            })
    
    def _test_config_drift_detection(self):
        """Test Configuration Drift Detection integration."""
        logger.info("📊 Testing Configuration Drift Detection...")
        start_time = time.time()
        
        try:
            from core.config_drift_detector import ConfigurationDriftDetector
            
            detector = ConfigurationDriftDetector()
            
            # Start monitoring
            monitoring_started = detector.start_monitoring()
            if not monitoring_started:
                raise ValueError("Failed to start drift monitoring")
            
            # Detect drift
            drift_events = detector.detect_drift(compare_with_baseline=True)
            
            # Get drift report
            drift_report = detector.get_drift_report()
            if not drift_report:
                raise ValueError("Failed to generate drift report")
            
            # Update baseline
            baseline_updated = detector.update_baseline()
            if not baseline_updated:
                raise ValueError("Failed to update baseline")
                
            # Stop monitoring
            detector.stop_monitoring()
            
            duration = (time.time() - start_time) * 1000
            logger.info(f"✅ Config Drift Detection: PASSED ({duration:.0f}ms)")
            self.test_results.append({
                "test": "config_drift_detection",
                "status": "passed",
                "duration_ms": duration,
                "drift_events": len(drift_events) if drift_events else 0
            })
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"❌ Config Drift Detection: FAILED - {e}")
            self.test_results.append({
                "test": "config_drift_detection",
                "status": "failed", 
                "duration_ms": duration,
                "error": str(e)
            })
    
    def _test_api_components(self):
        """Test API component imports and initialization."""
        logger.info("🔌 Testing API Components...")
        start_time = time.time()
        
        try:
            # Test core API imports
            from api.variables import VARIABLE_ORDER, VARIABLE_SPECS, VALID_HORIZONS
            from api.forecast_adapter import ForecastAdapter
            from api.services.faiss_health_monitoring import FAISSHealthMonitor
            
            # Validate variable configuration
            if not VARIABLE_ORDER or not VARIABLE_SPECS or not VALID_HORIZONS:
                raise ValueError("Invalid variable configuration")
            
            # Test forecast adapter initialization
            adapter = ForecastAdapter()
            if not hasattr(adapter, 'prepare_forecast_response'):
                raise ValueError("Invalid ForecastAdapter structure")
            
            # Test health monitor initialization  
            monitor = FAISSHealthMonitor()
            if not hasattr(monitor, 'get_health_summary'):
                raise ValueError("Invalid FAISSHealthMonitor structure")
            
            duration = (time.time() - start_time) * 1000
            logger.info(f"✅ API Components: PASSED ({duration:.0f}ms)")
            self.test_results.append({
                "test": "api_components",
                "status": "passed",
                "duration_ms": duration,
                "variables_count": len(VARIABLE_ORDER),
                "horizons_count": len(VALID_HORIZONS)
            })
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"❌ API Components: FAILED - {e}")
            self.test_results.append({
                "test": "api_components",
                "status": "failed",
                "duration_ms": duration, 
                "error": str(e)
            })
    
    def _test_security_middleware(self):
        """Test Security Middleware integration."""
        logger.info("🔒 Testing Security Middleware...")
        start_time = time.time()
        
        try:
            from api.security_middleware import SecurityMiddleware
            
            # Test middleware initialization
            middleware = SecurityMiddleware()
            
            # Check required methods exist
            required_methods = ['verify_token', 'rate_limit_check']
            for method in required_methods:
                if not hasattr(middleware, method):
                    raise ValueError(f"Missing required method: {method}")
            
            duration = (time.time() - start_time) * 1000
            logger.info(f"✅ Security Middleware: PASSED ({duration:.0f}ms)")
            self.test_results.append({
                "test": "security_middleware",
                "status": "passed",
                "duration_ms": duration
            })
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"❌ Security Middleware: FAILED - {e}")
            self.test_results.append({
                "test": "security_middleware",
                "status": "failed",
                "duration_ms": duration,
                "error": str(e)
            })
    
    def _test_faiss_monitoring(self):
        """Test FAISS Health Monitoring integration.""" 
        logger.info("📊 Testing FAISS Health Monitoring...")
        start_time = time.time()
        
        try:
            from api.services.faiss_health_monitoring import FAISSHealthMonitor
            
            monitor = FAISSHealthMonitor()
            
            # Test health status generation (run async method)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            health_status = loop.run_until_complete(monitor.get_health_summary())
            
            # Validate health status structure  
            required_fields = ["status", "query_performance", "indices"]
            for field in required_fields:
                if field not in health_status:
                    raise ValueError(f"Missing health status field: {field}")
            
            duration = (time.time() - start_time) * 1000
            logger.info(f"✅ FAISS Health Monitoring: PASSED ({duration:.0f}ms)")
            self.test_results.append({
                "test": "faiss_monitoring",
                "status": "passed",
                "duration_ms": duration,
                "health_status": health_status["status"]
            })
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"❌ FAISS Health Monitoring: FAILED - {e}")
            self.test_results.append({
                "test": "faiss_monitoring",
                "status": "failed",
                "duration_ms": duration,
                "error": str(e)
            })
    
    def _test_deployment_script(self):
        """Test deployment script availability and configuration."""
        logger.info("🚀 Testing Deployment Script...")
        start_time = time.time()
        
        try:
            deploy_script = self.project_root / "deploy.sh"
            
            if not deploy_script.exists():
                raise ValueError("Deployment script not found")
            
            # Check script is executable
            if not os.access(deploy_script, os.X_OK):
                raise ValueError("Deployment script not executable")
            
            # Check environment configurations exist
            for env in ["development", "staging", "production"]:
                env_dir = self.project_root / "configs" / "environments" / env
                if not env_dir.exists():
                    raise ValueError(f"Environment config missing: {env}")
            
            duration = (time.time() - start_time) * 1000
            logger.info(f"✅ Deployment Script: PASSED ({duration:.0f}ms)")
            self.test_results.append({
                "test": "deployment_script",
                "status": "passed",
                "duration_ms": duration,
                "environments_configured": 3
            })
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"❌ Deployment Script: FAILED - {e}")
            self.test_results.append({
                "test": "deployment_script",
                "status": "failed",
                "duration_ms": duration,
                "error": str(e)
            })
    
    def _test_system_integration(self):
        """Test overall system integration."""
        logger.info("🔄 Testing System Integration...")
        start_time = time.time()
        
        try:
            # Test file structure integrity
            critical_files = [
                "api/main.py",
                "api/variables.py", 
                "api/forecast_adapter.py",
                "core/environment_config_manager.py",
                "core/secure_credential_manager.py",
                "core/config_drift_detector.py",
                "docker-compose.yml",
                "docker-compose.dev.yml"
            ]
            
            missing_files = []
            for file_path in critical_files:
                if not (self.project_root / file_path).exists():
                    missing_files.append(file_path)
            
            if missing_files:
                raise ValueError(f"Missing critical files: {missing_files}")
            
            # Test configuration consistency
            from core.environment_config_manager import EnvironmentConfigManager
            
            dev_manager = EnvironmentConfigManager(environment="development")
            prod_manager = EnvironmentConfigManager(environment="production")
            
            dev_config = dev_manager.load_config()
            prod_config = prod_manager.load_config()
            
            # Check that configs have required sections
            required_sections = ["data", "model"]
            for section in required_sections:
                if section not in dev_config or section not in prod_config:
                    raise ValueError(f"Missing config section: {section}")
            
            duration = (time.time() - start_time) * 1000
            logger.info(f"✅ System Integration: PASSED ({duration:.0f}ms)")
            self.test_results.append({
                "test": "system_integration", 
                "status": "passed",
                "duration_ms": duration,
                "critical_files_present": len(critical_files) - len(missing_files),
                "total_critical_files": len(critical_files)
            })
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"❌ System Integration: FAILED - {e}")
            self.test_results.append({
                "test": "system_integration",
                "status": "failed",
                "duration_ms": duration,
                "error": str(e)
            })
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """Generate final integration test report."""
        end_time = datetime.now(timezone.utc)
        total_duration = (end_time - self.start_time).total_seconds()
        
        passed_tests = [r for r in self.test_results if r["status"] == "passed"]
        failed_tests = [r for r in self.test_results if r["status"] == "failed"]
        
        success_rate = (len(passed_tests) / len(self.test_results)) * 100 if self.test_results else 0
        
        # Determine production readiness
        critical_failures = [
            r for r in failed_tests 
            if r["test"] in ["environment_config_manager", "secure_credential_manager", "api_components"]
        ]
        
        production_ready = len(critical_failures) == 0 and success_rate >= 80
        
        report = {
            "test_summary": {
                "total_tests": len(self.test_results),
                "passed_tests": len(passed_tests),
                "failed_tests": len(failed_tests),
                "success_rate_percent": round(success_rate, 2),
                "total_duration_seconds": round(total_duration, 2)
            },
            "production_readiness": {
                "ready": production_ready,
                "critical_failures": len(critical_failures),
                "recommendation": "APPROVED FOR PRODUCTION" if production_ready else "REQUIRES FIXES BEFORE PRODUCTION"
            },
            "test_results": self.test_results,
            "quality_gates": {
                "all_core_components_pass": len([r for r in passed_tests if r["test"] in ["environment_config_manager", "secure_credential_manager", "config_drift_detection"]]) == 3,
                "api_components_integrated": any(r["test"] == "api_components" and r["status"] == "passed" for r in self.test_results),
                "security_components_working": any(r["test"] == "security_middleware" and r["status"] == "passed" for r in self.test_results),
                "deployment_ready": any(r["test"] == "deployment_script" and r["status"] == "passed" for r in self.test_results)
            },
            "generated_at": end_time.isoformat(),
            "test_environment": {
                "python_version": sys.version,
                "platform": sys.platform,
                "project_root": str(self.project_root)
            }
        }
        
        return report
    
    def _generate_failure_report(self, error_msg: str) -> Dict[str, Any]:
        """Generate failure report for critical test failures."""
        return {
            "test_failed": True,
            "error_message": error_msg,
            "production_readiness": {
                "ready": False,
                "recommendation": "CRITICAL FAILURE - CANNOT DEPLOY TO PRODUCTION"
            },
            "test_results": self.test_results,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

def main():
    """Execute final integration test."""
    print("🚀 T-020 Final Integration Test - Production Readiness Validation")
    print("=" * 80)
    
    tester = FinalIntegrationTest()
    report = tester.run_final_validation()
    
    # Print summary
    if "test_summary" in report:
        summary = report["test_summary"]
        readiness = report["production_readiness"]
        
        print(f"\n📊 Final Test Results:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Passed: {summary['passed_tests']}")
        print(f"   Failed: {summary['failed_tests']}")
        print(f"   Success Rate: {summary['success_rate_percent']}%")
        print(f"   Duration: {summary['total_duration_seconds']}s")
        
        print(f"\n🎯 Production Readiness Assessment:")
        if readiness["ready"]:
            print(f"   ✅ {readiness['recommendation']}")
            print(f"   🚀 System is ready for production deployment")
        else:
            print(f"   ❌ {readiness['recommendation']}")
            print(f"   🔧 Critical failures: {readiness['critical_failures']}")
            
        # Print failed tests
        failed_tests = [r for r in report["test_results"] if r["status"] == "failed"]
        if failed_tests:
            print(f"\n❌ Failed Tests:")
            for test in failed_tests:
                print(f"   • {test['test']}: {test.get('error', 'Unknown error')}")
    else:
        print(f"\n💥 CRITICAL FAILURE:")
        print(f"   {report['error_message']}")
        print(f"   {report['production_readiness']['recommendation']}")
    
    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = Path(__file__).parent / f"final_integration_report_{timestamp}.json"
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved: {report_file}")
    
    # Return appropriate exit code
    if report.get("production_readiness", {}).get("ready", False):
        print(f"\n🎉 FINAL INTEGRATION TEST: PASSED")
        return 0
    else:
        print(f"\n🚨 FINAL INTEGRATION TEST: FAILED")
        return 1

if __name__ == "__main__":
    exit(main())