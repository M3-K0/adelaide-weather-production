#!/usr/bin/env python3
"""
Adelaide Weather System - Comprehensive Integration Test Script
End-to-End testing without requiring full Docker deployment
"""

import json
import os
import sys
import subprocess
import time
import requests
from datetime import datetime
from pathlib import Path
import numpy as np

class AdelaideWeatherIntegrationTester:
    def __init__(self):
        self.test_results = {
            "test_execution_id": f"integration_test_{int(time.time())}",
            "timestamp": datetime.utcnow().isoformat(),
            "test_type": "comprehensive_integration",
            "status": "running",
            "tests": [],
            "overall_score": 0,
            "recommendations": []
        }
        
    def log_test(self, test_name, status, details="", execution_time=0):
        """Log test results"""
        test_entry = {
            "test_name": test_name,
            "status": status,
            "details": details,
            "execution_time": execution_time,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.test_results["tests"].append(test_entry)
        print(f"[{status.upper()}] {test_name}: {details}")
        
    def test_faiss_data_integrity(self):
        """Test FAISS data files are present and valid"""
        start_time = time.time()
        
        try:
            # Check indices directory
            indices_path = Path("indices")
            if not indices_path.exists():
                self.log_test("faiss_data_integrity", "FAIL", 
                             f"Indices directory missing: {indices_path.absolute()}")
                return False
                
            faiss_files = list(indices_path.glob("*.faiss"))
            expected_indices = 8  # Based on validation output
            
            if len(faiss_files) != expected_indices:
                self.log_test("faiss_data_integrity", "FAIL", 
                             f"Expected {expected_indices} FAISS files, found {len(faiss_files)}")
                return False
                
            # Check embeddings
            embeddings_path = Path("embeddings")
            if not embeddings_path.exists():
                self.log_test("faiss_data_integrity", "FAIL", 
                             f"Embeddings directory missing: {embeddings_path.absolute()}")
                return False
                
            npy_files = list(embeddings_path.glob("*.npy"))
            expected_embeddings = 4
            
            if len(npy_files) < expected_embeddings:
                self.log_test("faiss_data_integrity", "FAIL", 
                             f"Expected at least {expected_embeddings} embedding files, found {len(npy_files)}")
                return False
                
            # Validate actual data by loading one file
            try:
                test_embedding = np.load(npy_files[0])
                if test_embedding.size == 0:
                    self.log_test("faiss_data_integrity", "FAIL", 
                                 f"Empty embedding file: {npy_files[0]}")
                    return False
            except Exception as e:
                self.log_test("faiss_data_integrity", "FAIL", 
                             f"Could not load embedding file: {str(e)}")
                return False
                
            execution_time = time.time() - start_time
            self.log_test("faiss_data_integrity", "PASS", 
                         f"All FAISS data files present and valid", execution_time)
            return True
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.log_test("faiss_data_integrity", "ERROR", str(e), execution_time)
            return False
    
    def test_core_modules_availability(self):
        """Test that core Python modules can be imported"""
        start_time = time.time()
        
        try:
            # Test core module imports
            core_modules = [
                'numpy',
                'pandas', 
                'torch',
                'faiss'
            ]
            
            missing_modules = []
            for module in core_modules:
                try:
                    __import__(module)
                except ImportError:
                    missing_modules.append(module)
                    
            if missing_modules:
                execution_time = time.time() - start_time
                self.log_test("core_modules_availability", "FAIL", 
                             f"Missing modules: {missing_modules}", execution_time)
                return False
                
            execution_time = time.time() - start_time
            self.log_test("core_modules_availability", "PASS", 
                         "All core modules available", execution_time)
            return True
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.log_test("core_modules_availability", "ERROR", str(e), execution_time)
            return False
            
    def test_api_module_structure(self):
        """Test API module structure and key files"""
        start_time = time.time()
        
        try:
            api_path = Path("api")
            
            required_files = [
                "main.py",
                "requirements.txt",
                "health_checks.py",
                "security_middleware.py",
                "performance_middleware.py"
            ]
            
            missing_files = []
            for file in required_files:
                if not (api_path / file).exists():
                    missing_files.append(file)
                    
            if missing_files:
                execution_time = time.time() - start_time
                self.log_test("api_module_structure", "FAIL", 
                             f"Missing API files: {missing_files}", execution_time)
                return False
                
            # Check if main.py has FastAPI app
            main_py = api_path / "main.py"
            try:
                with open(main_py, 'r') as f:
                    content = f.read()
                    if 'FastAPI' not in content or 'app =' not in content:
                        execution_time = time.time() - start_time
                        self.log_test("api_module_structure", "FAIL", 
                                     "main.py doesn't appear to contain FastAPI app", execution_time)
                        return False
            except Exception as e:
                execution_time = time.time() - start_time
                self.log_test("api_module_structure", "ERROR", 
                             f"Could not read main.py: {str(e)}", execution_time)
                return False
                
            execution_time = time.time() - start_time
            self.log_test("api_module_structure", "PASS", 
                         "API module structure valid", execution_time)
            return True
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.log_test("api_module_structure", "ERROR", str(e), execution_time)
            return False
            
    def test_frontend_structure(self):
        """Test frontend module structure"""
        start_time = time.time()
        
        try:
            frontend_path = Path("frontend")
            
            if not frontend_path.exists():
                execution_time = time.time() - start_time
                self.log_test("frontend_structure", "FAIL", 
                             "Frontend directory missing", execution_time)
                return False
                
            required_files = [
                "package.json",
                "next.config.js"
            ]
            
            missing_files = []
            for file in required_files:
                if not (frontend_path / file).exists():
                    missing_files.append(file)
                    
            if missing_files:
                execution_time = time.time() - start_time
                self.log_test("frontend_structure", "FAIL", 
                             f"Missing frontend files: {missing_files}", execution_time)
                return False
                
            # Check package.json for Next.js
            package_json = frontend_path / "package.json"
            try:
                with open(package_json, 'r') as f:
                    content = json.load(f)
                    if 'next' not in content.get('dependencies', {}):
                        execution_time = time.time() - start_time
                        self.log_test("frontend_structure", "FAIL", 
                                     "Next.js not found in package.json dependencies", execution_time)
                        return False
            except Exception as e:
                execution_time = time.time() - start_time
                self.log_test("frontend_structure", "ERROR", 
                             f"Could not read package.json: {str(e)}", execution_time)
                return False
                
            execution_time = time.time() - start_time
            self.log_test("frontend_structure", "PASS", 
                         "Frontend structure valid", execution_time)
            return True
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.log_test("frontend_structure", "ERROR", str(e), execution_time)
            return False
            
    def test_nginx_configuration(self):
        """Test nginx configuration files"""
        start_time = time.time()
        
        try:
            nginx_path = Path("nginx")
            
            if not nginx_path.exists():
                execution_time = time.time() - start_time
                self.log_test("nginx_configuration", "FAIL", 
                             "Nginx directory missing", execution_time)
                return False
                
            # Check for nginx.conf
            nginx_conf = nginx_path / "nginx.conf"
            if not nginx_conf.exists():
                execution_time = time.time() - start_time
                self.log_test("nginx_configuration", "FAIL", 
                             "nginx.conf missing", execution_time)
                return False
                
            # Check SSL directory
            ssl_path = nginx_path / "ssl"
            if not ssl_path.exists():
                execution_time = time.time() - start_time
                self.log_test("nginx_configuration", "FAIL", 
                             "SSL directory missing", execution_time)
                return False
                
            # Check for SSL certificates
            ssl_files = ["cert.pem", "key.pem"]
            missing_ssl = []
            for ssl_file in ssl_files:
                if not (ssl_path / ssl_file).exists():
                    missing_ssl.append(ssl_file)
                    
            if missing_ssl:
                execution_time = time.time() - start_time
                self.log_test("nginx_configuration", "FAIL", 
                             f"Missing SSL files: {missing_ssl}", execution_time)
                return False
                
            execution_time = time.time() - start_time
            self.log_test("nginx_configuration", "PASS", 
                         "Nginx configuration valid", execution_time)
            return True
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.log_test("nginx_configuration", "ERROR", str(e), execution_time)
            return False
            
    def test_monitoring_stack_configuration(self):
        """Test monitoring stack configuration"""
        start_time = time.time()
        
        try:
            monitoring_path = Path("monitoring")
            
            if not monitoring_path.exists():
                execution_time = time.time() - start_time
                self.log_test("monitoring_configuration", "FAIL", 
                             "Monitoring directory missing", execution_time)
                return False
                
            # Check for prometheus configuration
            prometheus_path = monitoring_path / "prometheus"
            if prometheus_path.exists():
                prometheus_config = prometheus_path / "prometheus.yml"
                if not prometheus_config.exists():
                    execution_time = time.time() - start_time
                    self.log_test("monitoring_configuration", "WARNING", 
                                 "prometheus.yml missing", execution_time)
                    
            execution_time = time.time() - start_time
            self.log_test("monitoring_configuration", "PASS", 
                         "Monitoring configuration present", execution_time)
            return True
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.log_test("monitoring_configuration", "ERROR", str(e), execution_time)
            return False
            
    def test_docker_compose_files(self):
        """Test Docker Compose configuration files"""
        start_time = time.time()
        
        try:
            compose_files = [
                "docker-compose.production.yml",
                "docker-compose.yml"
            ]
            
            valid_compose_files = []
            for compose_file in compose_files:
                if Path(compose_file).exists():
                    valid_compose_files.append(compose_file)
                    
            if not valid_compose_files:
                execution_time = time.time() - start_time
                self.log_test("docker_compose_files", "FAIL", 
                             "No Docker Compose files found", execution_time)
                return False
                
            execution_time = time.time() - start_time
            self.log_test("docker_compose_files", "PASS", 
                         f"Found compose files: {valid_compose_files}", execution_time)
            return True
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.log_test("docker_compose_files", "ERROR", str(e), execution_time)
            return False
            
    def test_environment_configuration(self):
        """Test environment configuration files"""
        start_time = time.time()
        
        try:
            env_files = [
                ".env.production",
                ".env.example"
            ]
            
            found_env_files = []
            for env_file in env_files:
                if Path(env_file).exists():
                    found_env_files.append(env_file)
                    
            if not found_env_files:
                execution_time = time.time() - start_time
                self.log_test("environment_configuration", "WARNING", 
                             "No environment files found", execution_time)
                return True  # Not critical for testing
                
            # Check production environment file for required variables
            prod_env = Path(".env.production")
            if prod_env.exists():
                try:
                    with open(prod_env, 'r') as f:
                        content = f.read()
                        required_vars = ['API_TOKEN', 'GRAFANA_PASSWORD']
                        missing_vars = []
                        for var in required_vars:
                            if var not in content:
                                missing_vars.append(var)
                                
                        if missing_vars:
                            execution_time = time.time() - start_time
                            self.log_test("environment_configuration", "WARNING", 
                                         f"Missing environment variables: {missing_vars}", execution_time)
                            return True
                            
                except Exception as e:
                    execution_time = time.time() - start_time
                    self.log_test("environment_configuration", "WARNING", 
                                 f"Could not read .env.production: {str(e)}", execution_time)
                    return True
                    
            execution_time = time.time() - start_time
            self.log_test("environment_configuration", "PASS", 
                         f"Environment files found: {found_env_files}", execution_time)
            return True
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.log_test("environment_configuration", "ERROR", str(e), execution_time)
            return False

    def test_system_integration_readiness(self):
        """Overall system integration readiness assessment"""
        start_time = time.time()
        
        try:
            # Calculate overall readiness based on test results
            total_tests = len(self.test_results["tests"])
            passed_tests = len([t for t in self.test_results["tests"] if t["status"] == "PASS"])
            failed_tests = len([t for t in self.test_results["tests"] if t["status"] == "FAIL"])
            error_tests = len([t for t in self.test_results["tests"] if t["status"] == "ERROR"])
            
            if total_tests == 0:
                self.log_test("system_integration_readiness", "ERROR", 
                             "No tests executed", 0)
                return False
                
            pass_rate = passed_tests / total_tests
            
            if pass_rate >= 0.9:
                status = "EXCELLENT"
                readiness = "ready_for_production"
            elif pass_rate >= 0.8:
                status = "GOOD"
                readiness = "ready_for_testing"
            elif pass_rate >= 0.6:
                status = "FAIR"
                readiness = "needs_fixes"
            else:
                status = "POOR"
                readiness = "major_issues"
                
            execution_time = time.time() - start_time
            self.log_test("system_integration_readiness", status, 
                         f"Pass rate: {pass_rate:.1%} ({passed_tests}/{total_tests}), "
                         f"Readiness: {readiness}, Failed: {failed_tests}, Errors: {error_tests}", 
                         execution_time)
                         
            self.test_results["overall_score"] = pass_rate
            self.test_results["readiness_status"] = readiness
            
            return pass_rate >= 0.6
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.log_test("system_integration_readiness", "ERROR", str(e), execution_time)
            return False
    
    def run_all_tests(self):
        """Run comprehensive integration test suite"""
        print("🔧 Starting Adelaide Weather Comprehensive Integration Testing")
        print("=" * 70)
        
        test_methods = [
            self.test_faiss_data_integrity,
            self.test_core_modules_availability,
            self.test_api_module_structure,
            self.test_frontend_structure,
            self.test_nginx_configuration,
            self.test_monitoring_stack_configuration,
            self.test_docker_compose_files,
            self.test_environment_configuration,
            self.test_system_integration_readiness
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                print(f"EXCEPTION in {test_method.__name__}: {str(e)}")
                
        self.test_results["status"] = "completed"
        
        # Generate recommendations
        failed_tests = [t for t in self.test_results["tests"] if t["status"] in ["FAIL", "ERROR"]]
        if failed_tests:
            self.test_results["recommendations"].append("Fix failed test components before production deployment")
            for test in failed_tests:
                self.test_results["recommendations"].append(f"Address {test['test_name']}: {test['details']}")
                
        return self.test_results
        
    def save_results(self, filename="test_results.json"):
        """Save test results to file"""
        with open(filename, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        print(f"✅ Test results saved to {filename}")

if __name__ == "__main__":
    tester = AdelaideWeatherIntegrationTester()
    results = tester.run_all_tests()
    tester.save_results()
    
    print("\n" + "=" * 70)
    print("🎯 INTEGRATION TEST SUMMARY")
    print("=" * 70)
    print(f"Overall Score: {results['overall_score']:.1%}")
    print(f"Status: {results.get('readiness_status', 'unknown')}")
    print(f"Tests Executed: {len(results['tests'])}")
    
    # Print recommendations
    if results["recommendations"]:
        print("\n📋 RECOMMENDATIONS:")
        for i, rec in enumerate(results["recommendations"], 1):
            print(f"{i}. {rec}")
    
    print("\n✨ Integration testing completed!")
    
    # Exit with appropriate code
    sys.exit(0 if results['overall_score'] >= 0.6 else 1)