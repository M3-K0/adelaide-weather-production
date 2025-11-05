#!/usr/bin/env python3
"""
Adelaide Weather Forecasting System - Component Validation Test
==============================================================

Focused integration testing that validates individual components
without relying on Docker service orchestration. This provides
immediate validation of component functionality and integration points.

Author: Quality Assurance & Optimization Specialist
Version: 1.0.0 - Component Validation Testing
"""

import os
import sys
import time
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime, timezone
import json

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def test_environment_config_manager():
    """Test Environment Configuration Manager in isolation."""
    print("🔧 Testing Environment Configuration Manager...")
    
    try:
        from core.environment_config_manager import EnvironmentConfigManager, Environment
        
        # Test all environments
        results = {}
        for env_name in ["development", "staging", "production"]:
            start_time = time.time()
            
            manager = EnvironmentConfigManager(environment=env_name)
            config = manager.load_config()
            metadata = manager.get_metadata()
            
            load_time = (time.time() - start_time) * 1000
            
            results[env_name] = {
                "config_loaded": bool(config),
                "has_data_section": "data" in config,
                "has_model_section": "model" in config,
                "config_hash": metadata.config_hash,
                "load_time_ms": round(load_time, 2)
            }
            
        print("✅ Environment Configuration Manager: PASSED")
        return True, results
        
    except Exception as e:
        print(f"❌ Environment Configuration Manager: FAILED - {e}")
        return False, {"error": str(e)}

def test_secure_credential_manager():
    """Test Secure Credential Manager with proper environment setup."""
    print("🔐 Testing Secure Credential Manager...")
    
    # Set up master key for testing
    os.environ["CREDENTIAL_MASTER_KEY"] = f"test_master_key_{int(time.time())}"
    
    try:
        from core.secure_credential_manager import SecureCredentialManager
        
        manager = SecureCredentialManager()
        
        # Test credential operations
        test_credentials = {
            "api_token": "test_token_123",
            "db_password": "test_password_456"
        }
        
        results = {"credentials_tested": 0, "operations_successful": 0}
        
        for key, value in test_credentials.items():
            # Store credential
            manager.store_credential(key, value)
            
            # Retrieve credential
            retrieved = manager.get_credential(key)
            
            if retrieved == value:
                results["operations_successful"] += 1
            results["credentials_tested"] += 1
            
        results["encryption_available"] = manager._is_encrypted_storage()
        results["success_rate"] = results["operations_successful"] / results["credentials_tested"]
        
        success = results["success_rate"] == 1.0
        
        if success:
            print("✅ Secure Credential Manager: PASSED")
        else:
            print("❌ Secure Credential Manager: FAILED")
            
        return success, results
        
    except Exception as e:
        print(f"❌ Secure Credential Manager: FAILED - {e}")
        return False, {"error": str(e)}

def test_config_drift_detector():
    """Test Configuration Drift Detector functionality."""
    print("📊 Testing Configuration Drift Detector...")
    
    try:
        from core.config_drift_detector import ConfigurationDriftDetector
        
        detector = ConfigurationDriftDetector()
        
        results = {}
        
        # Test monitoring startup
        start_time = time.time()
        monitoring_started = detector.start_monitoring()
        startup_time = (time.time() - start_time) * 1000
        
        results["monitoring_started"] = monitoring_started
        results["startup_time_ms"] = round(startup_time, 2)
        
        # Test drift detection
        start_time = time.time()
        drift_events = detector.detect_drift(compare_with_baseline=True)
        detection_time = (time.time() - start_time) * 1000
        
        results["drift_detection_time_ms"] = round(detection_time, 2)
        results["drift_events_detected"] = len(drift_events) if drift_events else 0
        
        # Test reporting
        drift_report = detector.get_drift_report()
        results["report_generated"] = bool(drift_report)
        
        # Test baseline update
        baseline_updated = detector.update_baseline()
        results["baseline_updated"] = baseline_updated
        
        # Clean up
        detector.stop_monitoring()
        results["monitoring_stopped"] = True
        
        print("✅ Configuration Drift Detector: PASSED")
        return True, results
        
    except Exception as e:
        print(f"❌ Configuration Drift Detector: FAILED - {e}")
        return False, {"error": str(e)}

def test_deployment_script():
    """Test deployment script functionality."""
    print("🚀 Testing Deployment Script...")
    
    try:
        deploy_script = Path(__file__).parent / "deploy.sh"
        
        if not deploy_script.exists():
            raise FileNotFoundError("Deployment script not found")
            
        results = {}
        
        # Test help command
        start_time = time.time()
        help_result = subprocess.run(
            ["bash", str(deploy_script), "--help"],
            capture_output=True,
            text=True,
            timeout=30
        )
        help_time = (time.time() - start_time) * 1000
        
        results["help_command_works"] = help_result.returncode == 0
        results["help_response_time_ms"] = round(help_time, 2)
        results["help_output_length"] = len(help_result.stdout)
        
        # Check environment directories
        env_dirs = ["development", "staging", "production"]
        env_configs = []
        
        for env in env_dirs:
            env_dir = Path(__file__).parent / "configs" / "environments" / env
            env_configs.append(env_dir.exists())
            
        results["environment_configs"] = {
            "total": len(env_dirs),
            "available": sum(env_configs),
            "environments": dict(zip(env_dirs, env_configs))
        }
        
        success = results["help_command_works"] and results["environment_configs"]["available"] == 3
        
        if success:
            print("✅ Deployment Script: PASSED")
        else:
            print("❌ Deployment Script: FAILED")
            
        return success, results
        
    except Exception as e:
        print(f"❌ Deployment Script: FAILED - {e}")
        return False, {"error": str(e)}

def test_api_components():
    """Test API components without requiring service startup."""
    print("🔌 Testing API Components...")
    
    try:
        # Test API imports and basic initialization
        sys.path.append(str(Path(__file__).parent / "api"))
        
        results = {}
        
        # Test variable definitions
        try:
            from api.variables import VARIABLE_ORDER, VARIABLE_SPECS, VALID_HORIZONS
            results["variables_module"] = {
                "variable_count": len(VARIABLE_ORDER),
                "variable_specs": len(VARIABLE_SPECS),
                "horizons": len(VALID_HORIZONS)
            }
        except ImportError as e:
            results["variables_module"] = {"error": str(e)}
            
        # Test forecast adapter
        try:
            from api.forecast_adapter import ForecastAdapter
            # Don't initialize - just check import
            results["forecast_adapter"] = {"import_successful": True}
        except ImportError as e:
            results["forecast_adapter"] = {"error": str(e)}
            
        # Test FAISS health monitoring
        try:
            from api.services.faiss_health_monitoring import FAISSHealthMonitor
            results["faiss_monitoring"] = {"import_successful": True}
        except ImportError as e:
            results["faiss_monitoring"] = {"error": str(e)}
            
        # Test security middleware
        try:
            from api.security_middleware import SecurityMiddleware
            results["security_middleware"] = {"import_successful": True}
        except ImportError as e:
            results["security_middleware"] = {"error": str(e)}
            
        # Count successful imports
        successful_imports = sum(1 for module in results.values() 
                               if isinstance(module, dict) and module.get("import_successful"))
        total_imports = len(results)
        
        success = successful_imports >= total_imports * 0.8  # 80% import success rate
        
        if success:
            print("✅ API Components: PASSED")
        else:
            print("❌ API Components: FAILED")
            
        return success, results
        
    except Exception as e:
        print(f"❌ API Components: FAILED - {e}")
        return False, {"error": str(e)}

def test_docker_configuration():
    """Test Docker configuration without starting services."""
    print("🐳 Testing Docker Configuration...")
    
    try:
        results = {}
        
        # Check Docker compose files
        compose_files = [
            "docker-compose.yml",
            "docker-compose.dev.yml", 
            "docker-compose.staging.yml",
            "docker-compose.production.yml"
        ]
        
        compose_status = {}
        for compose_file in compose_files:
            file_path = Path(__file__).parent / compose_file
            compose_status[compose_file] = file_path.exists()
            
        results["compose_files"] = compose_status
        
        # Check Dockerfiles
        dockerfiles = [
            "api/Dockerfile",
            "api/Dockerfile.simple",
            "api/Dockerfile.production",
            "frontend/Dockerfile"
        ]
        
        dockerfile_status = {}
        for dockerfile in dockerfiles:
            file_path = Path(__file__).parent / dockerfile
            dockerfile_status[dockerfile] = file_path.exists()
            
        results["dockerfiles"] = dockerfile_status
        
        # Test docker-compose syntax validation
        compose_validation = {}
        for compose_file in ["docker-compose.yml", "docker-compose.dev.yml"]:
            file_path = Path(__file__).parent / compose_file
            if file_path.exists():
                try:
                    # Use docker compose config to validate syntax
                    validation_result = subprocess.run(
                        ["docker", "compose", "-f", str(file_path), "config"],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    compose_validation[compose_file] = validation_result.returncode == 0
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    compose_validation[compose_file] = False
            else:
                compose_validation[compose_file] = False
                
        results["compose_validation"] = compose_validation
        
        # Calculate success metrics
        files_present = sum(compose_status.values()) + sum(dockerfile_status.values())
        total_files = len(compose_status) + len(dockerfile_status)
        valid_compose_files = sum(compose_validation.values())
        
        results["summary"] = {
            "files_present": files_present,
            "total_files": total_files,
            "file_availability": files_present / total_files,
            "valid_compose_files": valid_compose_files
        }
        
        success = (files_present >= total_files * 0.8 and valid_compose_files >= 1)
        
        if success:
            print("✅ Docker Configuration: PASSED")
        else:
            print("❌ Docker Configuration: FAILED")
            
        return success, results
        
    except Exception as e:
        print(f"❌ Docker Configuration: FAILED - {e}")
        return False, {"error": str(e)}

def main():
    """Execute component validation tests."""
    print("🚀 Adelaide Weather Forecasting System - Component Validation")
    print("=" * 70)
    
    overall_start = time.time()
    
    # Test suite
    tests = [
        ("Environment Config Manager", test_environment_config_manager),
        ("Secure Credential Manager", test_secure_credential_manager),
        ("Config Drift Detector", test_config_drift_detector),
        ("Deployment Script", test_deployment_script),
        ("API Components", test_api_components),
        ("Docker Configuration", test_docker_configuration)
    ]
    
    results = {}
    passed_tests = 0
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            success, result_data = test_func()
            results[test_name] = {
                "status": "passed" if success else "failed",
                "data": result_data
            }
            if success:
                passed_tests += 1
        except Exception as e:
            print(f"❌ {test_name}: CRASHED - {e}")
            results[test_name] = {
                "status": "crashed",
                "error": str(e)
            }
            
    total_duration = time.time() - overall_start
    
    # Generate summary
    print("\n" + "=" * 70)
    print("📊 COMPONENT VALIDATION SUMMARY")
    print("=" * 70)
    
    print(f"Total Tests: {len(tests)}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(tests) - passed_tests}")
    print(f"Success Rate: {(passed_tests / len(tests)) * 100:.1f}%")
    print(f"Duration: {total_duration:.2f}s")
    
    # Component status
    print(f"\nComponent Status:")
    for test_name, result in results.items():
        status_icon = "✅" if result["status"] == "passed" else "❌"
        print(f"{status_icon} {test_name}: {result['status'].upper()}")
        
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = Path(__file__).parent / f"component_validation_report_{timestamp}.json"
    
    detailed_report = {
        "test_summary": {
            "total_tests": len(tests),
            "passed_tests": passed_tests,
            "failed_tests": len(tests) - passed_tests,
            "success_rate_percent": round((passed_tests / len(tests)) * 100, 2),
            "total_duration_seconds": round(total_duration, 2)
        },
        "test_results": results,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
    
    with open(report_file, 'w') as f:
        json.dump(detailed_report, f, indent=2)
        
    print(f"\n📄 Detailed report saved: {report_file}")
    
    # Overall assessment
    success_rate = (passed_tests / len(tests)) * 100
    
    if success_rate >= 90:
        print("\n🎉 EXCELLENT: System components are well integrated")
        return 0
    elif success_rate >= 80:
        print("\n✅ GOOD: Most components working, minor issues to address")
        return 0
    elif success_rate >= 60:
        print("\n⚠️ PARTIAL: Significant issues need attention")
        return 1
    else:
        print("\n❌ CRITICAL: Major integration problems")
        return 1

if __name__ == "__main__":
    exit(main())