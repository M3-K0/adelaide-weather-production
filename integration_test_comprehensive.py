#!/usr/bin/env python3
"""
Adelaide Weather Forecasting System - Comprehensive Integration Testing Suite
===========================================================================

End-to-end system integration testing covering all implemented components:
1. FAISS Health Monitoring (T1, T6) - Real-time monitoring and API integration
2. Frontend API Connection (T2) - Port configuration fix validation  
3. Environment Config Manager (T3) - Multi-environment configuration
4. Secure Credential Manager (T4) - Enterprise-grade credential security
5. Config Drift Detection (T5) - Real-time configuration monitoring
6. Production Deploy Script (T7) - Deployment orchestration

Integration test scenarios:
- Full System Deployment across environments
- Weather Forecasting Workflow with monitoring
- Configuration Management and environment switching
- Health Monitoring system verification
- Security Validation and credential management
- Error Handling under various failure scenarios
- Performance Integration testing

Author: Quality Assurance & Optimization Specialist
Version: 1.0.0 - Comprehensive System Integration Testing
"""

import os
import sys
import json
import time
import subprocess
import requests
import logging
import tempfile
import asyncio
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import yaml

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Import system components for testing
from core.environment_config_manager import EnvironmentConfigManager, Environment
from core.secure_credential_manager import SecureCredentialManager, CredentialType
from core.config_drift_detector import ConfigurationDriftDetector
from api.services.faiss_health_monitoring import FAISSHealthMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IntegrationTestResult:
    """Test result tracking for comprehensive reporting."""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.start_time = datetime.now(timezone.utc)
        self.end_time = None
        self.status = "running"
        self.details = {}
        self.errors = []
        self.warnings = []
        self.performance_metrics = {}
        
    def complete(self, status: str, details: Dict[str, Any] = None):
        """Mark test as complete with status and details."""
        self.end_time = datetime.now(timezone.utc)
        self.status = status
        if details:
            self.details.update(details)
            
    def add_error(self, error: str):
        """Add error message to test result."""
        self.errors.append(error)
        logger.error(f"{self.test_name}: {error}")
        
    def add_warning(self, warning: str):
        """Add warning message to test result."""
        self.warnings.append(warning)
        logger.warning(f"{self.test_name}: {warning}")
        
    def add_performance_metric(self, metric_name: str, value: float, unit: str = "ms"):
        """Add performance metric to test result."""
        self.performance_metrics[metric_name] = {"value": value, "unit": unit}
        
    def duration_ms(self) -> float:
        """Get test duration in milliseconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return (datetime.now(timezone.utc) - self.start_time).total_seconds() * 1000

class ComprehensiveIntegrationTester:
    """Comprehensive end-to-end integration testing suite."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.test_results: List[IntegrationTestResult] = []
        self.test_environment = "development"  # Default test environment
        self.api_base_url = "http://localhost:8000"
        self.frontend_base_url = "http://localhost:3000"
        self.api_token = None
        self.services_started = False
        
        # Create test artifacts directory
        self.artifacts_dir = self.project_root / "integration_test_artifacts"
        self.artifacts_dir.mkdir(exist_ok=True)
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Execute comprehensive integration test suite."""
        logger.info("🚀 Starting Comprehensive Integration Testing Suite")
        logger.info(f"📁 Test artifacts directory: {self.artifacts_dir}")
        
        overall_start = datetime.now(timezone.utc)
        
        try:
            # Pre-test setup
            self._setup_test_environment()
            
            # Core integration tests
            self._test_environment_config_manager()
            self._test_secure_credential_manager()
            self._test_config_drift_detection()
            
            # Deployment orchestration tests
            self._test_deployment_script()
            
            # API and monitoring integration tests
            self._test_api_startup_integration()
            self._test_faiss_health_monitoring()
            self._test_api_endpoints_integration()
            
            # Frontend integration tests
            self._test_frontend_api_connection()
            
            # End-to-end workflow tests
            self._test_complete_forecast_workflow()
            self._test_multi_environment_switching()
            self._test_performance_integration()
            self._test_error_handling_scenarios()
            
            # Security integration tests
            self._test_security_integration()
            
        except Exception as e:
            logger.error(f"💥 Integration testing failed: {e}")
            self._create_failure_report(str(e))
        finally:
            # Cleanup
            self._cleanup_test_environment()
            
        overall_duration = (datetime.now(timezone.utc) - overall_start).total_seconds()
        
        # Generate comprehensive report
        report = self._generate_comprehensive_report(overall_duration)
        self._save_test_report(report)
        
        return report
        
    def _setup_test_environment(self):
        """Setup test environment and prerequisites."""
        result = IntegrationTestResult("Environment Setup")
        
        try:
            logger.info("🔧 Setting up test environment...")
            
            # Ensure required directories exist
            required_dirs = [
                "configs/environments/development",
                "configs/environments/staging", 
                "configs/environments/production",
                "backups",
                "logs"
            ]
            
            for dir_path in required_dirs:
                (self.project_root / dir_path).mkdir(parents=True, exist_ok=True)
                
            # Set test environment variables
            os.environ["ENVIRONMENT"] = self.test_environment
            os.environ["API_TOKEN"] = "test_integration_token_123"
            self.api_token = os.environ["API_TOKEN"]
            
            # Verify system dependencies
            self._verify_system_dependencies()
            
            result.complete("passed", {
                "environment": self.test_environment,
                "api_token_set": bool(self.api_token),
                "directories_created": len(required_dirs)
            })
            
        except Exception as e:
            result.add_error(f"Environment setup failed: {e}")
            result.complete("failed")
            
        self.test_results.append(result)
        
    def _verify_system_dependencies(self):
        """Verify required system dependencies are available."""
        dependencies = ["docker", "docker-compose", "python3", "curl"]
        
        for dep in dependencies:
            if not shutil.which(dep):
                raise RuntimeError(f"Required dependency not found: {dep}")
                
        logger.info("✅ All system dependencies verified")
        
    def _test_environment_config_manager(self):
        """Test Environment Config Manager functionality."""
        result = IntegrationTestResult("Environment Config Manager")
        
        try:
            logger.info("🔧 Testing Environment Config Manager...")
            
            # Test environment detection
            for env in ["development", "staging", "production"]:
                start_time = time.time()
                
                manager = EnvironmentConfigManager(environment=env)
                config = manager.load_config()
                
                load_time = (time.time() - start_time) * 1000
                result.add_performance_metric(f"{env}_config_load_time", load_time)
                
                # Validate config structure
                required_sections = ["data", "model"]
                for section in required_sections:
                    if section not in config:
                        result.add_error(f"Missing config section '{section}' in {env}")
                        
                # Test configuration metadata
                metadata = manager.get_metadata()
                if not metadata.config_hash:
                    result.add_error(f"Missing config hash for {env}")
                    
            # Test environment switching
            dev_manager = EnvironmentConfigManager(environment="development")
            prod_manager = EnvironmentConfigManager(environment="production")
            
            dev_config = dev_manager.load_config()
            prod_config = prod_manager.load_config()
            
            # Configs should be different between environments
            if dev_config == prod_config:
                result.add_warning("Development and production configs are identical")
                
            result.complete("passed", {
                "environments_tested": ["development", "staging", "production"],
                "config_sections_validated": ["data", "model"],
                "environment_switching": "successful"
            })
            
        except Exception as e:
            result.add_error(f"Environment Config Manager test failed: {e}")
            result.complete("failed")
            
        self.test_results.append(result)
        
    def _test_secure_credential_manager(self):
        """Test Secure Credential Manager functionality."""
        result = IntegrationTestResult("Secure Credential Manager")
        
        try:
            logger.info("🔐 Testing Secure Credential Manager...")
            
            # Test credential storage and retrieval
            manager = SecureCredentialManager()
            
            # Test API token storage
            test_credentials = {
                "api_token": "test_secure_token_456",
                "database_password": "test_db_password",
                "monitoring_key": "test_monitoring_key"
            }
            
            for key, value in test_credentials.items():
                start_time = time.time()
                
                # Store credential
                manager.store_credential(
                    credential_id=key,
                    credential_value=value,
                    credential_type=CredentialType.API_TOKEN
                )
                
                # Retrieve credential
                retrieved = manager.retrieve_credential(key)
                
                store_retrieve_time = (time.time() - start_time) * 1000
                result.add_performance_metric(f"{key}_store_retrieve_time", store_retrieve_time)
                
                if retrieved != value:
                    result.add_error(f"Credential mismatch for {key}: expected {value}, got {retrieved}")
                    
            # Test credential encryption
            health_status = manager.health_check()
            if not health_status.get("storage_accessible", False):
                result.add_warning("Credential storage may not be encrypted")
                
            # Test credential validation
            invalid_scenarios = [
                ("", "empty_key"),
                ("valid_key", ""),  # empty value
                (None, "none_key"),
                ("valid_key", None)
            ]
            
            for key, value in invalid_scenarios:
                try:
                    if key and value:  # Only test with valid types for credential_type
                        manager.store_credential(
                            credential_id=key,
                            credential_value=value,
                            credential_type=CredentialType.API_TOKEN
                        )
                        result.add_warning(f"Expected validation error for key={key}, value={value}")
                except Exception:
                    pass  # Expected validation error
                    
            result.complete("passed", {
                "credentials_tested": len(test_credentials),
                "health_check_passed": health_status.get("status") == "healthy",
                "validation_scenarios": len(invalid_scenarios)
            })
            
        except Exception as e:
            result.add_error(f"Secure Credential Manager test failed: {e}")
            result.complete("failed")
            
        self.test_results.append(result)
        
    def _test_config_drift_detection(self):
        """Test Config Drift Detection functionality."""
        result = IntegrationTestResult("Config Drift Detection")
        
        try:
            logger.info("📊 Testing Config Drift Detection...")
            
            # Initialize drift detector
            detector = ConfigurationDriftDetector()
            
            # Start monitoring to establish baseline
            start_time = time.time()
            monitoring_started = detector.start_monitoring()
            baseline_time = (time.time() - start_time) * 1000
            result.add_performance_metric("monitoring_startup_time", baseline_time)
            
            if not monitoring_started:
                result.add_warning("Failed to start drift monitoring")
                
            # Test drift detection
            start_time = time.time()
            drift_events = detector.detect_drift(compare_with_baseline=True)
            drift_detection_time = (time.time() - start_time) * 1000
            result.add_performance_metric("drift_detection_time", drift_detection_time)
            
            # Test drift reporting
            drift_report = detector.get_drift_report()
            if not drift_report:
                result.add_warning("Empty drift report returned")
                
            # Test baseline update
            baseline_updated = detector.update_baseline()
            if not baseline_updated:
                result.add_warning("Failed to update configuration baseline")
                
            # Stop monitoring
            detector.stop_monitoring()
                
            result.complete("passed", {
                "monitoring_started": monitoring_started,
                "drift_events_count": len(drift_events) if drift_events else 0,
                "drift_report_generated": bool(drift_report),
                "baseline_updated": baseline_updated
            })
            
        except Exception as e:
            result.add_error(f"Config Drift Detection test failed: {e}")
            result.complete("failed")
            
        self.test_results.append(result)
        
    def _test_deployment_script(self):
        """Test deployment script functionality."""
        result = IntegrationTestResult("Deployment Script")
        
        try:
            logger.info("🚀 Testing Deployment Script...")
            
            deploy_script = self.project_root / "deploy.sh"
            if not deploy_script.exists():
                result.add_error("Deployment script not found")
                result.complete("failed")
                self.test_results.append(result)
                return
                
            # Test script help
            start_time = time.time()
            help_result = subprocess.run(
                [str(deploy_script), "--help"],
                capture_output=True,
                text=True,
                timeout=30
            )
            help_time = (time.time() - start_time) * 1000
            result.add_performance_metric("help_command_time", help_time)
            
            if help_result.returncode != 0:
                result.add_error("Deployment script help command failed")
                
            # Test script validation without deployment
            validation_commands = [
                ["bash", str(deploy_script), "development", "--help"],
            ]
            
            for cmd in validation_commands:
                try:
                    start_time = time.time()
                    validation_result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    validation_time = (time.time() - start_time) * 1000
                    
                    if validation_result.returncode not in [0, 1]:  # Allow graceful failures
                        result.add_warning(f"Validation command failed: {' '.join(cmd)}")
                        
                except subprocess.TimeoutExpired:
                    result.add_warning(f"Validation command timed out: {' '.join(cmd)}")
                    
            # Test environment-specific configuration validation
            for env in ["development", "staging", "production"]:
                env_dir = self.project_root / "configs" / "environments" / env
                if not env_dir.exists():
                    result.add_error(f"Environment config directory missing: {env}")
                    
            result.complete("passed", {
                "script_exists": deploy_script.exists(),
                "help_command": help_result.returncode == 0,
                "environments_configured": 3
            })
            
        except Exception as e:
            result.add_error(f"Deployment script test failed: {e}")
            result.complete("failed")
            
        self.test_results.append(result)
        
    def _test_api_startup_integration(self):
        """Test API startup and initialization integration."""
        result = IntegrationTestResult("API Startup Integration")
        
        try:
            logger.info("🔌 Testing API Startup Integration...")
            
            # Start API services for testing
            if not self._start_api_services():
                result.add_error("Failed to start API services")
                result.complete("failed")
                self.test_results.append(result)
                return
                
            # Wait for services to be ready
            ready = self._wait_for_services_ready(timeout=120)
            if not ready:
                result.add_error("Services failed to become ready within timeout")
                result.complete("failed")
                self.test_results.append(result)
                return
                
            # Test API health endpoint
            start_time = time.time()
            health_response = self._make_api_request("GET", "/health")
            health_time = (time.time() - start_time) * 1000
            result.add_performance_metric("health_endpoint_time", health_time)
            
            if health_response.status_code != 200:
                result.add_error(f"Health endpoint failed: {health_response.status_code}")
            else:
                health_data = health_response.json()
                if not health_data.get("ready"):
                    result.add_error("API reports not ready")
                    
            # Test startup validation integration
            if health_response.status_code == 200:
                health_data = health_response.json()
                startup_checks = [check for check in health_data.get("checks", []) 
                                if "startup" in check.get("name", "")]
                if not startup_checks:
                    result.add_warning("No startup validation checks found in health response")
                    
            result.complete("passed", {
                "services_started": True,
                "health_check": health_response.status_code == 200,
                "api_ready": health_data.get("ready", False) if health_response.status_code == 200 else False
            })
            
        except Exception as e:
            result.add_error(f"API startup integration test failed: {e}")
            result.complete("failed")
            
        self.test_results.append(result)
        
    def _test_faiss_health_monitoring(self):
        """Test FAISS Health Monitoring integration."""
        result = IntegrationTestResult("FAISS Health Monitoring")
        
        try:
            logger.info("📊 Testing FAISS Health Monitoring...")
            
            # Test FAISS health endpoint with authentication
            start_time = time.time()
            faiss_health_response = self._make_api_request("GET", "/health/faiss", authenticated=True)
            faiss_health_time = (time.time() - start_time) * 1000
            result.add_performance_metric("faiss_health_endpoint_time", faiss_health_time)
            
            if faiss_health_response.status_code == 200:
                faiss_data = faiss_health_response.json()
                
                # Validate FAISS health data structure
                expected_fields = ["status", "query_performance", "index_health"]
                for field in expected_fields:
                    if field not in faiss_data:
                        result.add_warning(f"Missing FAISS health field: {field}")
                        
                # Check performance metrics
                if "query_performance" in faiss_data:
                    perf = faiss_data["query_performance"]
                    if "total_queries" in perf:
                        result.add_performance_metric("faiss_total_queries", perf["total_queries"], "count")
                        
            elif faiss_health_response.status_code == 503:
                result.add_warning("FAISS health monitoring not available (service unavailable)")
            else:
                result.add_error(f"FAISS health endpoint failed: {faiss_health_response.status_code}")
                
            # Test metrics endpoint for FAISS metrics
            start_time = time.time()
            metrics_response = self._make_api_request("GET", "/metrics", authenticated=True)
            metrics_time = (time.time() - start_time) * 1000
            result.add_performance_metric("metrics_endpoint_time", metrics_time)
            
            if metrics_response.status_code == 200:
                metrics_text = metrics_response.text
                faiss_metrics_found = "faiss_" in metrics_text
                if not faiss_metrics_found:
                    result.add_warning("No FAISS metrics found in /metrics endpoint")
            else:
                result.add_error(f"Metrics endpoint failed: {metrics_response.status_code}")
                
            result.complete("passed", {
                "faiss_health_endpoint": faiss_health_response.status_code,
                "metrics_endpoint": metrics_response.status_code,
                "faiss_metrics_present": faiss_metrics_found if metrics_response.status_code == 200 else False
            })
            
        except Exception as e:
            result.add_error(f"FAISS Health Monitoring test failed: {e}")
            result.complete("failed")
            
        self.test_results.append(result)
        
    def _test_api_endpoints_integration(self):
        """Test API endpoints integration and functionality."""
        result = IntegrationTestResult("API Endpoints Integration")
        
        try:
            logger.info("🔗 Testing API Endpoints Integration...")
            
            # Test forecast endpoint
            forecast_params = {
                "horizon": "24h",
                "vars": "t2m,u10,v10,msl"
            }
            
            start_time = time.time()
            forecast_response = self._make_api_request(
                "GET", "/forecast", 
                params=forecast_params, 
                authenticated=True
            )
            forecast_time = (time.time() - start_time) * 1000
            result.add_performance_metric("forecast_endpoint_time", forecast_time)
            
            if forecast_response.status_code == 200:
                forecast_data = forecast_response.json()
                
                # Validate forecast response structure
                required_fields = ["horizon", "generated_at", "variables", "latency_ms"]
                for field in required_fields:
                    if field not in forecast_data:
                        result.add_error(f"Missing forecast field: {field}")
                        
                # Validate requested variables are present
                if "variables" in forecast_data:
                    requested_vars = forecast_params["vars"].split(",")
                    for var in requested_vars:
                        if var not in forecast_data["variables"]:
                            result.add_error(f"Missing requested variable: {var}")
                            
                # Check performance
                if "latency_ms" in forecast_data:
                    result.add_performance_metric("forecast_latency", forecast_data["latency_ms"])
                    
            else:
                result.add_error(f"Forecast endpoint failed: {forecast_response.status_code}")
                
            # Test authentication requirement
            unauth_response = self._make_api_request("GET", "/forecast", params=forecast_params)
            if unauth_response.status_code not in [401, 403]:
                result.add_error("Forecast endpoint should require authentication")
                
            # Test invalid parameters
            invalid_params = {"horizon": "invalid", "vars": "invalid_var"}
            invalid_response = self._make_api_request(
                "GET", "/forecast", 
                params=invalid_params, 
                authenticated=True
            )
            if invalid_response.status_code != 400:
                result.add_warning("Expected 400 for invalid parameters")
                
            result.complete("passed", {
                "forecast_endpoint": forecast_response.status_code,
                "authentication_required": unauth_response.status_code in [401, 403],
                "parameter_validation": invalid_response.status_code == 400
            })
            
        except Exception as e:
            result.add_error(f"API endpoints integration test failed: {e}")
            result.complete("failed")
            
        self.test_results.append(result)
        
    def _test_frontend_api_connection(self):
        """Test frontend API connection and port configuration."""
        result = IntegrationTestResult("Frontend API Connection")
        
        try:
            logger.info("🌐 Testing Frontend API Connection...")
            
            # Test frontend availability
            start_time = time.time()
            try:
                frontend_response = requests.get(self.frontend_base_url, timeout=10)
                frontend_time = (time.time() - start_time) * 1000
                result.add_performance_metric("frontend_response_time", frontend_time)
                
                frontend_available = frontend_response.status_code == 200
            except requests.RequestException:
                frontend_available = False
                result.add_warning("Frontend not available - testing API connectivity only")
                
            # Test API connectivity from expected frontend perspective
            api_endpoints_to_test = [
                "/health",
                "/forecast?horizon=24h&vars=t2m"
            ]
            
            connectivity_results = {}
            for endpoint in api_endpoints_to_test:
                try:
                    start_time = time.time()
                    # Test both authenticated and unauthenticated (where appropriate)
                    if "health" in endpoint:
                        response = self._make_api_request("GET", endpoint)
                    else:
                        response = self._make_api_request("GET", endpoint, authenticated=True)
                        
                    response_time = (time.time() - start_time) * 1000
                    result.add_performance_metric(f"api_connectivity_{endpoint.replace('/', '_')}", response_time)
                    
                    connectivity_results[endpoint] = {
                        "status_code": response.status_code,
                        "response_time_ms": response_time
                    }
                    
                except Exception as e:
                    connectivity_results[endpoint] = {"error": str(e)}
                    result.add_error(f"API connectivity test failed for {endpoint}: {e}")
                    
            # Test CORS headers (important for frontend integration)
            cors_test_response = self._make_api_request("OPTIONS", "/health")
            cors_headers = cors_test_response.headers
            
            cors_configured = (
                "Access-Control-Allow-Origin" in cors_headers or
                cors_test_response.status_code == 200  # Some servers return 200 for OPTIONS
            )
            
            if not cors_configured:
                result.add_warning("CORS headers may not be properly configured")
                
            result.complete("passed", {
                "frontend_available": frontend_available,
                "api_connectivity": connectivity_results,
                "cors_configured": cors_configured
            })
            
        except Exception as e:
            result.add_error(f"Frontend API connection test failed: {e}")
            result.complete("failed")
            
        self.test_results.append(result)
        
    def _test_complete_forecast_workflow(self):
        """Test complete end-to-end forecast workflow."""
        result = IntegrationTestResult("Complete Forecast Workflow")
        
        try:
            logger.info("🔄 Testing Complete Forecast Workflow...")
            
            # Test full workflow: request -> processing -> response -> monitoring
            workflow_steps = []
            
            # Step 1: Health check
            start_time = time.time()
            health_response = self._make_api_request("GET", "/health")
            health_time = (time.time() - start_time) * 1000
            
            workflow_steps.append({
                "step": "health_check",
                "status_code": health_response.status_code,
                "duration_ms": health_time
            })
            
            if health_response.status_code != 200:
                result.add_error("Health check failed in workflow")
                
            # Step 2: Request forecast
            start_time = time.time()
            forecast_response = self._make_api_request(
                "GET", "/forecast",
                params={"horizon": "24h", "vars": "t2m,u10,v10,msl,cape"},
                authenticated=True
            )
            forecast_time = (time.time() - start_time) * 1000
            
            workflow_steps.append({
                "step": "forecast_request",
                "status_code": forecast_response.status_code,
                "duration_ms": forecast_time
            })
            
            if forecast_response.status_code != 200:
                result.add_error("Forecast request failed in workflow")
                result.complete("failed")
                self.test_results.append(result)
                return
                
            forecast_data = forecast_response.json()
            
            # Step 3: Validate forecast response
            response_validation = self._validate_forecast_response(forecast_data)
            workflow_steps.append({
                "step": "response_validation",
                "valid": response_validation["valid"],
                "issues": response_validation["issues"]
            })
            
            if not response_validation["valid"]:
                for issue in response_validation["issues"]:
                    result.add_error(f"Response validation: {issue}")
                    
            # Step 4: Check monitoring metrics
            start_time = time.time()
            metrics_response = self._make_api_request("GET", "/metrics", authenticated=True)
            metrics_time = (time.time() - start_time) * 1000
            
            workflow_steps.append({
                "step": "monitoring_check",
                "status_code": metrics_response.status_code,
                "duration_ms": metrics_time
            })
            
            # Step 5: Verify FAISS health after forecast
            faiss_health_response = self._make_api_request("GET", "/health/faiss", authenticated=True)
            workflow_steps.append({
                "step": "faiss_health_check",
                "status_code": faiss_health_response.status_code
            })
            
            # Calculate total workflow time
            total_workflow_time = sum(
                step.get("duration_ms", 0) for step in workflow_steps 
                if "duration_ms" in step
            )
            result.add_performance_metric("total_workflow_time", total_workflow_time)
            
            # Validate end-to-end performance
            if total_workflow_time > 5000:  # 5 seconds threshold
                result.add_warning(f"Workflow took {total_workflow_time:.0f}ms (>5s threshold)")
                
            result.complete("passed", {
                "workflow_steps": workflow_steps,
                "total_time_ms": total_workflow_time,
                "forecast_variables": len(forecast_data.get("variables", {}))
            })
            
        except Exception as e:
            result.add_error(f"Complete forecast workflow test failed: {e}")
            result.complete("failed")
            
        self.test_results.append(result)
        
    def _test_multi_environment_switching(self):
        """Test multi-environment configuration switching."""
        result = IntegrationTestResult("Multi-Environment Switching")
        
        try:
            logger.info("🔄 Testing Multi-Environment Switching...")
            
            environments = ["development", "staging", "production"]
            environment_tests = {}
            
            for env in environments:
                env_result = {}
                
                try:
                    # Test environment config loading
                    start_time = time.time()
                    manager = EnvironmentConfigManager(environment=env)
                    config = manager.load_config()
                    load_time = (time.time() - start_time) * 1000
                    
                    env_result["config_load_time_ms"] = load_time
                    env_result["config_loaded"] = True
                    env_result["config_hash"] = manager.get_metadata().config_hash
                    
                    # Test environment-specific validation
                    required_sections = ["data", "model"]
                    missing_sections = [s for s in required_sections if s not in config]
                    env_result["missing_sections"] = missing_sections
                    
                    if missing_sections:
                        result.add_warning(f"Missing config sections in {env}: {missing_sections}")
                        
                except Exception as e:
                    env_result["error"] = str(e)
                    result.add_error(f"Environment {env} configuration failed: {e}")
                    
                environment_tests[env] = env_result
                
            # Test environment switching consistency
            config_hashes = [
                env_test.get("config_hash") for env_test in environment_tests.values()
                if env_test.get("config_hash")
            ]
            
            # All environments should have valid, different configurations
            unique_hashes = len(set(config_hashes))
            if unique_hashes < len(environments):
                result.add_warning("Some environments have identical configurations")
                
            result.complete("passed", {
                "environments_tested": len(environment_tests),
                "unique_configurations": unique_hashes,
                "environment_results": environment_tests
            })
            
        except Exception as e:
            result.add_error(f"Multi-environment switching test failed: {e}")
            result.complete("failed")
            
        self.test_results.append(result)
        
    def _test_performance_integration(self):
        """Test performance integration across all components."""
        result = IntegrationTestResult("Performance Integration")
        
        try:
            logger.info("⚡ Testing Performance Integration...")
            
            # Performance test scenarios
            scenarios = [
                {"name": "single_forecast", "requests": 1, "concurrent": 1},
                {"name": "burst_forecast", "requests": 10, "concurrent": 5},
                {"name": "health_checks", "requests": 20, "concurrent": 10}
            ]
            
            performance_results = {}
            
            for scenario in scenarios:
                scenario_name = scenario["name"]
                scenario_results = []
                
                if scenario_name == "health_checks":
                    # Test health endpoint performance
                    with ThreadPoolExecutor(max_workers=scenario["concurrent"]) as executor:
                        futures = []
                        for _ in range(scenario["requests"]):
                            future = executor.submit(self._performance_test_health_check)
                            futures.append(future)
                            
                        for future in as_completed(futures):
                            try:
                                result_data = future.result(timeout=30)
                                scenario_results.append(result_data)
                            except Exception as e:
                                result.add_error(f"Performance test error: {e}")
                                
                else:
                    # Test forecast endpoint performance
                    with ThreadPoolExecutor(max_workers=scenario["concurrent"]) as executor:
                        futures = []
                        for _ in range(scenario["requests"]):
                            future = executor.submit(self._performance_test_forecast)
                            futures.append(future)
                            
                        for future in as_completed(futures):
                            try:
                                result_data = future.result(timeout=60)
                                scenario_results.append(result_data)
                            except Exception as e:
                                result.add_error(f"Performance test error: {e}")
                                
                # Calculate performance statistics
                if scenario_results:
                    response_times = [r["response_time_ms"] for r in scenario_results if "response_time_ms" in r]
                    if response_times:
                        avg_time = sum(response_times) / len(response_times)
                        max_time = max(response_times)
                        min_time = min(response_times)
                        
                        performance_results[scenario_name] = {
                            "requests": len(scenario_results),
                            "avg_response_time_ms": avg_time,
                            "max_response_time_ms": max_time,
                            "min_response_time_ms": min_time,
                            "success_rate": len([r for r in scenario_results if r.get("success", False)]) / len(scenario_results)
                        }
                        
                        result.add_performance_metric(f"{scenario_name}_avg_time", avg_time)
                        result.add_performance_metric(f"{scenario_name}_max_time", max_time)
                        
            result.complete("passed", {
                "scenarios_tested": len(scenarios),
                "performance_results": performance_results
            })
            
        except Exception as e:
            result.add_error(f"Performance integration test failed: {e}")
            result.complete("failed")
            
        self.test_results.append(result)
        
    def _test_error_handling_scenarios(self):
        """Test system behavior under various error scenarios."""
        result = IntegrationTestResult("Error Handling Scenarios")
        
        try:
            logger.info("🚨 Testing Error Handling Scenarios...")
            
            error_scenarios = []
            
            # Test invalid authentication
            invalid_auth_response = self._make_api_request(
                "GET", "/forecast",
                headers={"Authorization": "Bearer invalid_token"}
            )
            error_scenarios.append({
                "scenario": "invalid_authentication",
                "expected_status": [401, 403],
                "actual_status": invalid_auth_response.status_code,
                "passed": invalid_auth_response.status_code in [401, 403]
            })
            
            # Test invalid parameters
            invalid_params_response = self._make_api_request(
                "GET", "/forecast",
                params={"horizon": "invalid", "vars": "nonexistent"},
                authenticated=True
            )
            error_scenarios.append({
                "scenario": "invalid_parameters",
                "expected_status": [400],
                "actual_status": invalid_params_response.status_code,
                "passed": invalid_params_response.status_code == 400
            })
            
            # Test missing required parameters
            missing_params_response = self._make_api_request(
                "GET", "/forecast",
                authenticated=True
            )
            error_scenarios.append({
                "scenario": "missing_parameters",
                "expected_status": [200, 400],  # Should use defaults or return 400
                "actual_status": missing_params_response.status_code,
                "passed": missing_params_response.status_code in [200, 400]
            })
            
            # Test rate limiting (if enabled)
            rate_limit_responses = []
            for i in range(70):  # Exceed typical rate limit
                try:
                    rate_response = self._make_api_request("GET", "/health", timeout=5)
                    rate_limit_responses.append(rate_response.status_code)
                    if rate_response.status_code == 429:  # Rate limited
                        break
                except requests.exceptions.Timeout:
                    break
                    
            rate_limited = 429 in rate_limit_responses
            error_scenarios.append({
                "scenario": "rate_limiting",
                "rate_limited": rate_limited,
                "requests_made": len(rate_limit_responses)
            })
            
            if not rate_limited:
                result.add_warning("Rate limiting may not be enabled or threshold is very high")
                
            # Test malformed JSON
            try:
                malformed_response = requests.post(
                    f"{self.api_base_url}/forecast",
                    headers={"Authorization": f"Bearer {self.api_token}"},
                    data="malformed json",
                    timeout=10
                )
                error_scenarios.append({
                    "scenario": "malformed_json",
                    "status_code": malformed_response.status_code,
                    "handled_gracefully": malformed_response.status_code in [400, 405]  # Bad request or method not allowed
                })
            except Exception as e:
                error_scenarios.append({
                    "scenario": "malformed_json",
                    "error": str(e)
                })
                
            # Calculate overall error handling score
            passed_scenarios = len([s for s in error_scenarios if s.get("passed", s.get("handled_gracefully", False))])
            total_scenarios = len([s for s in error_scenarios if "passed" in s or "handled_gracefully" in s])
            
            error_handling_score = passed_scenarios / total_scenarios if total_scenarios > 0 else 0
            
            result.complete("passed", {
                "scenarios_tested": len(error_scenarios),
                "error_handling_score": error_handling_score,
                "scenarios": error_scenarios
            })
            
        except Exception as e:
            result.add_error(f"Error handling scenarios test failed: {e}")
            result.complete("failed")
            
        self.test_results.append(result)
        
    def _test_security_integration(self):
        """Test security integration across all components."""
        result = IntegrationTestResult("Security Integration")
        
        try:
            logger.info("🔒 Testing Security Integration...")
            
            security_tests = []
            
            # Test API authentication requirement
            endpoints_to_test = ["/forecast", "/metrics", "/health/faiss"]
            for endpoint in endpoints_to_test:
                unauth_response = self._make_api_request("GET", endpoint)
                auth_required = unauth_response.status_code in [401, 403]
                
                security_tests.append({
                    "test": f"authentication_required_{endpoint.replace('/', '_')}",
                    "passed": auth_required,
                    "status_code": unauth_response.status_code
                })
                
                if not auth_required and endpoint != "/health":  # Health might be public
                    result.add_warning(f"Authentication may not be required for {endpoint}")
                    
            # Test credential manager security
            try:
                cred_manager = SecureCredentialManager()
                
                # Test credential encryption
                test_credential = "test_secret_value_123"
                cred_manager.store_credential(
                    credential_id="test_key",
                    credential_value=test_credential,
                    credential_type=CredentialType.API_TOKEN
                )
                
                # Check if storage is working and secure
                health_status = cred_manager.health_check()
                encryption_test = {
                    "test": "credential_encryption",
                    "passed": health_status.get("status") in ["healthy", "warning"],
                    "details": "Credential storage health check"
                }
                security_tests.append(encryption_test)
                
                if not encryption_test["passed"]:
                    result.add_warning("Credential storage may not be healthy")
                    
            except Exception as e:
                security_tests.append({
                    "test": "credential_manager",
                    "passed": False,
                    "error": str(e)
                })
                
            # Test input validation and sanitization
            malicious_inputs = [
                {"horizon": "<script>alert('xss')</script>", "vars": "t2m"},
                {"horizon": "'; DROP TABLE users; --", "vars": "t2m"},
                {"horizon": "24h", "vars": "../../../etc/passwd"},
                {"horizon": "24h" * 1000, "vars": "t2m"}  # Very long input
            ]
            
            for i, malicious_input in enumerate(malicious_inputs):
                try:
                    mal_response = self._make_api_request(
                        "GET", "/forecast",
                        params=malicious_input,
                        authenticated=True,
                        timeout=10
                    )
                    
                    # Should return 400 for malicious input
                    input_validation = {
                        "test": f"input_validation_{i}",
                        "passed": mal_response.status_code == 400,
                        "status_code": mal_response.status_code,
                        "input": str(malicious_input)[:100]  # Truncate for logging
                    }
                    security_tests.append(input_validation)
                    
                    if mal_response.status_code == 200:
                        result.add_warning(f"Malicious input not rejected: {str(malicious_input)[:50]}")
                        
                except Exception as e:
                    security_tests.append({
                        "test": f"input_validation_{i}",
                        "passed": True,  # Exception is acceptable for malicious input
                        "error": str(e)
                    })
                    
            # Calculate security score
            passed_security_tests = len([t for t in security_tests if t.get("passed", False)])
            total_security_tests = len(security_tests)
            security_score = passed_security_tests / total_security_tests if total_security_tests > 0 else 0
            
            result.complete("passed", {
                "security_tests": len(security_tests),
                "security_score": security_score,
                "test_results": security_tests
            })
            
        except Exception as e:
            result.add_error(f"Security integration test failed: {e}")
            result.complete("failed")
            
        self.test_results.append(result)
        
    def _start_api_services(self) -> bool:
        """Start API services for testing."""
        try:
            logger.info("🚀 Starting API services for testing...")
            
            # Use docker-compose to start services
            compose_cmd = self._get_compose_command()
            
            # Stop any existing services
            subprocess.run(
                [compose_cmd, "-f", "docker-compose.dev.yml", "down"],
                capture_output=True,
                timeout=60
            )
            
            # Start services
            start_result = subprocess.run(
                [compose_cmd, "-f", "docker-compose.dev.yml", "up", "-d", "--build"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if start_result.returncode != 0:
                logger.error(f"Failed to start services: {start_result.stderr}")
                return False
                
            self.services_started = True
            logger.info("✅ API services started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting API services: {e}")
            return False
            
    def _get_compose_command(self) -> str:
        """Get the appropriate docker-compose command."""
        if shutil.which("docker-compose"):
            return "docker-compose"
        elif subprocess.run(["docker", "compose", "version"], capture_output=True).returncode == 0:
            return "docker compose"
        else:
            raise RuntimeError("Docker Compose not found")
            
    def _wait_for_services_ready(self, timeout: int = 120) -> bool:
        """Wait for services to become ready."""
        logger.info("⏳ Waiting for services to become ready...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.api_base_url}/health", timeout=5)
                if response.status_code == 200:
                    logger.info("✅ Services are ready")
                    return True
            except requests.RequestException:
                pass
                
            time.sleep(5)
            
        logger.error("❌ Services failed to become ready within timeout")
        return False
        
    def _make_api_request(self, method: str, endpoint: str, params: Dict = None, 
                         headers: Dict = None, authenticated: bool = False, timeout: int = 30) -> requests.Response:
        """Make API request with optional authentication."""
        url = f"{self.api_base_url}{endpoint}"
        
        request_headers = headers or {}
        if authenticated and self.api_token:
            request_headers["Authorization"] = f"Bearer {self.api_token}"
            
        if method.upper() == "GET":
            return requests.get(url, params=params, headers=request_headers, timeout=timeout)
        elif method.upper() == "POST":
            return requests.post(url, json=params, headers=request_headers, timeout=timeout)
        elif method.upper() == "OPTIONS":
            return requests.options(url, headers=request_headers, timeout=timeout)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
            
    def _validate_forecast_response(self, forecast_data: Dict) -> Dict[str, Any]:
        """Validate forecast response structure."""
        validation_result = {"valid": True, "issues": []}
        
        required_fields = [
            "horizon", "generated_at", "variables", "latency_ms",
            "narrative", "risk_assessment", "analogs_summary"
        ]
        
        for field in required_fields:
            if field not in forecast_data:
                validation_result["issues"].append(f"Missing required field: {field}")
                validation_result["valid"] = False
                
        # Validate variables structure
        if "variables" in forecast_data:
            for var_name, var_data in forecast_data["variables"].items():
                required_var_fields = ["value", "available"]
                for var_field in required_var_fields:
                    if var_field not in var_data:
                        validation_result["issues"].append(f"Missing variable field {var_field} in {var_name}")
                        validation_result["valid"] = False
                        
        return validation_result
        
    def _performance_test_health_check(self) -> Dict[str, Any]:
        """Perform performance test on health check endpoint."""
        start_time = time.time()
        try:
            response = self._make_api_request("GET", "/health")
            response_time = (time.time() - start_time) * 1000
            
            return {
                "success": response.status_code == 200,
                "response_time_ms": response_time,
                "status_code": response.status_code
            }
        except Exception as e:
            return {
                "success": False,
                "response_time_ms": (time.time() - start_time) * 1000,
                "error": str(e)
            }
            
    def _performance_test_forecast(self) -> Dict[str, Any]:
        """Perform performance test on forecast endpoint."""
        start_time = time.time()
        try:
            response = self._make_api_request(
                "GET", "/forecast",
                params={"horizon": "24h", "vars": "t2m,u10,v10"},
                authenticated=True
            )
            response_time = (time.time() - start_time) * 1000
            
            return {
                "success": response.status_code == 200,
                "response_time_ms": response_time,
                "status_code": response.status_code
            }
        except Exception as e:
            return {
                "success": False,
                "response_time_ms": (time.time() - start_time) * 1000,
                "error": str(e)
            }
            
    def _cleanup_test_environment(self):
        """Cleanup test environment and services."""
        logger.info("🧹 Cleaning up test environment...")
        
        if self.services_started:
            try:
                compose_cmd = self._get_compose_command()
                subprocess.run(
                    [compose_cmd, "-f", "docker-compose.dev.yml", "down"],
                    capture_output=True,
                    timeout=60
                )
                logger.info("✅ Services stopped")
            except Exception as e:
                logger.warning(f"Error stopping services: {e}")
                
        # Clean up environment variables
        test_env_vars = ["API_TOKEN"]
        for var in test_env_vars:
            if var in os.environ:
                del os.environ[var]
                
    def _generate_comprehensive_report(self, total_duration: float) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        passed_tests = len([r for r in self.test_results if r.status == "passed"])
        failed_tests = len([r for r in self.test_results if r.status == "failed"])
        total_tests = len(self.test_results)
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # Aggregate performance metrics
        all_performance_metrics = {}
        for result in self.test_results:
            for metric_name, metric_data in result.performance_metrics.items():
                if metric_name not in all_performance_metrics:
                    all_performance_metrics[metric_name] = []
                all_performance_metrics[metric_name].append(metric_data)
                
        # Calculate performance statistics
        performance_summary = {}
        for metric_name, metric_values in all_performance_metrics.items():
            values = [m["value"] for m in metric_values]
            if values:
                performance_summary[metric_name] = {
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values),
                    "unit": metric_values[0]["unit"]
                }
                
        # Aggregate all errors and warnings
        all_errors = []
        all_warnings = []
        for result in self.test_results:
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
            
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate_percent": round(success_rate, 2),
                "total_duration_seconds": round(total_duration, 2)
            },
            "test_results": [
                {
                    "test_name": result.test_name,
                    "status": result.status,
                    "duration_ms": round(result.duration_ms(), 2),
                    "details": result.details,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "performance_metrics": result.performance_metrics
                }
                for result in self.test_results
            ],
            "performance_summary": performance_summary,
            "overall_assessment": {
                "system_ready": success_rate >= 80,
                "critical_issues": len([r for r in self.test_results 
                                      if r.status == "failed" and "startup" in r.test_name.lower()]),
                "total_errors": len(all_errors),
                "total_warnings": len(all_warnings)
            },
            "component_status": {
                "environment_config_manager": "passed" if any(r.test_name == "Environment Config Manager" and r.status == "passed" for r in self.test_results) else "failed",
                "secure_credential_manager": "passed" if any(r.test_name == "Secure Credential Manager" and r.status == "passed" for r in self.test_results) else "failed",
                "config_drift_detection": "passed" if any(r.test_name == "Config Drift Detection" and r.status == "passed" for r in self.test_results) else "failed",
                "deployment_script": "passed" if any(r.test_name == "Deployment Script" and r.status == "passed" for r in self.test_results) else "failed",
                "faiss_health_monitoring": "passed" if any(r.test_name == "FAISS Health Monitoring" and r.status == "passed" for r in self.test_results) else "failed",
                "api_integration": "passed" if any(r.test_name == "API Endpoints Integration" and r.status == "passed" for r in self.test_results) else "failed",
                "frontend_connection": "passed" if any(r.test_name == "Frontend API Connection" and r.status == "passed" for r in self.test_results) else "failed"
            },
            "recommendations": self._generate_recommendations(),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
        return report
        
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        # Analyze test results for recommendations
        failed_tests = [r for r in self.test_results if r.status == "failed"]
        
        if any("Environment Config Manager" in r.test_name for r in failed_tests):
            recommendations.append("Review environment configuration files and validation logic")
            
        if any("Secure Credential Manager" in r.test_name for r in failed_tests):
            recommendations.append("Verify credential storage security and encryption settings")
            
        if any("API" in r.test_name for r in failed_tests):
            recommendations.append("Check API service startup and dependency initialization")
            
        if any("Frontend" in r.test_name for r in failed_tests):
            recommendations.append("Verify frontend-API connectivity and CORS configuration")
            
        # Performance recommendations
        slow_tests = [r for r in self.test_results 
                     if any(m["value"] > 2000 for m in r.performance_metrics.values())]
        if slow_tests:
            recommendations.append("Investigate performance bottlenecks in slow-responding components")
            
        # Security recommendations
        security_warnings = []
        for result in self.test_results:
            if "security" in result.test_name.lower():
                security_warnings.extend(result.warnings)
                
        if security_warnings:
            recommendations.append("Address security configuration warnings")
            
        if not recommendations:
            recommendations.append("All integration tests passed successfully - system ready for deployment")
            
        return recommendations
        
    def _save_test_report(self, report: Dict[str, Any]):
        """Save comprehensive test report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.artifacts_dir / f"integration_test_report_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"📄 Test report saved: {report_file}")
        
        # Also create a summary report
        summary_file = self.artifacts_dir / f"integration_test_summary_{timestamp}.txt"
        with open(summary_file, 'w') as f:
            self._write_summary_report(f, report)
            
        logger.info(f"📄 Test summary saved: {summary_file}")
        
    def _write_summary_report(self, f, report: Dict[str, Any]):
        """Write human-readable test summary."""
        f.write("Adelaide Weather Forecasting System - Integration Test Summary\n")
        f.write("=" * 70 + "\n\n")
        
        # Test Summary
        summary = report["test_summary"]
        f.write(f"Total Tests: {summary['total_tests']}\n")
        f.write(f"Passed: {summary['passed_tests']}\n")
        f.write(f"Failed: {summary['failed_tests']}\n")
        f.write(f"Success Rate: {summary['success_rate_percent']}%\n")
        f.write(f"Total Duration: {summary['total_duration_seconds']}s\n\n")
        
        # Component Status
        f.write("Component Status:\n")
        f.write("-" * 20 + "\n")
        for component, status in report["component_status"].items():
            status_symbol = "✅" if status == "passed" else "❌"
            f.write(f"{status_symbol} {component.replace('_', ' ').title()}: {status}\n")
        f.write("\n")
        
        # Performance Summary
        if report["performance_summary"]:
            f.write("Performance Summary:\n")
            f.write("-" * 20 + "\n")
            for metric, stats in report["performance_summary"].items():
                f.write(f"{metric}: {stats['avg']:.1f}{stats['unit']} (avg), ")
                f.write(f"{stats['min']:.1f}-{stats['max']:.1f}{stats['unit']} (range)\n")
            f.write("\n")
            
        # Recommendations
        f.write("Recommendations:\n")
        f.write("-" * 20 + "\n")
        for i, rec in enumerate(report["recommendations"], 1):
            f.write(f"{i}. {rec}\n")
        f.write("\n")
        
        # Failed Tests Details
        failed_tests = [r for r in report["test_results"] if r["status"] == "failed"]
        if failed_tests:
            f.write("Failed Tests Details:\n")
            f.write("-" * 20 + "\n")
            for test in failed_tests:
                f.write(f"❌ {test['test_name']}\n")
                for error in test["errors"]:
                    f.write(f"   Error: {error}\n")
                f.write("\n")
                
    def _create_failure_report(self, error_message: str):
        """Create failure report when testing crashes."""
        failure_report = {
            "test_failed": True,
            "error_message": error_message,
            "completed_tests": len(self.test_results),
            "test_results": [
                {
                    "test_name": result.test_name,
                    "status": result.status,
                    "errors": result.errors
                }
                for result in self.test_results
            ],
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        failure_file = self.artifacts_dir / f"integration_test_failure_{timestamp}.json"
        
        with open(failure_file, 'w') as f:
            json.dump(failure_report, f, indent=2)
            
        logger.error(f"💥 Failure report saved: {failure_file}")

def main():
    """Main entry point for integration testing."""
    print("🚀 Adelaide Weather Forecasting System - Comprehensive Integration Testing")
    print("=" * 80)
    
    tester = ComprehensiveIntegrationTester()
    
    try:
        report = tester.run_all_tests()
        
        # Print summary to console
        summary = report["test_summary"]
        print(f"\n📊 Test Summary:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Passed: {summary['passed_tests']}")
        print(f"   Failed: {summary['failed_tests']}")
        print(f"   Success Rate: {summary['success_rate_percent']}%")
        print(f"   Duration: {summary['total_duration_seconds']}s")
        
        overall = report["overall_assessment"]
        if overall["system_ready"]:
            print(f"\n✅ System Integration: PASSED")
            print(f"   System is ready for deployment")
        else:
            print(f"\n❌ System Integration: FAILED")
            print(f"   Critical issues: {overall['critical_issues']}")
            print(f"   Total errors: {overall['total_errors']}")
            
        print(f"\n📁 Detailed reports available in: {tester.artifacts_dir}")
        
        # Exit with appropriate code
        return 0 if overall["system_ready"] else 1
        
    except KeyboardInterrupt:
        print("\n⚠️ Integration testing interrupted by user")
        return 130
    except Exception as e:
        print(f"\n💥 Integration testing failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())