#!/usr/bin/env python3
"""
Performance Validation Report - Adelaide Weather Forecasting System
===================================================================

Validates that all integrated components meet performance SLA targets.

Author: Quality Assurance & Optimization Specialist  
Version: 1.0.0 - Performance Integration Validation
"""

import time
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceValidator:
    """Validates performance integration across all components."""
    
    def __init__(self):
        self.results = []
        
    def validate_all_components(self) -> Dict[str, Any]:
        """Validate performance across all integrated components."""
        logger.info("🚀 Performance Integration Validation")
        logger.info("=" * 60)
        
        # Environment Configuration Performance
        self._validate_config_performance()
        
        # Credential Manager Performance
        self._validate_credential_performance()
        
        # Config Drift Detection Performance
        self._validate_drift_detection_performance()
        
        # API Component Performance
        self._validate_api_performance()
        
        return self._generate_performance_report()
    
    def _validate_config_performance(self):
        """Validate Environment Configuration Manager performance."""
        logger.info("🔧 Validating Config Manager Performance...")
        
        from core.environment_config_manager import EnvironmentConfigManager
        
        # Test configuration loading speed
        times = []
        for _ in range(5):
            start = time.time()
            manager = EnvironmentConfigManager(environment="production")
            config = manager.load_config()
            end = time.time()
            times.append((end - start) * 1000)
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # SLA: Config loading should be < 100ms average, < 200ms max
        sla_met = avg_time < 100 and max_time < 200
        
        self.results.append({
            "component": "Environment Config Manager",
            "metric": "Config Loading Time",
            "average_ms": round(avg_time, 2),
            "max_ms": round(max_time, 2),
            "sla_target": "< 100ms avg, < 200ms max",
            "sla_met": sla_met,
            "status": "PASS" if sla_met else "FAIL"
        })
        
        logger.info(f"   Average: {avg_time:.2f}ms, Max: {max_time:.2f}ms - {'PASS' if sla_met else 'FAIL'}")
    
    def _validate_credential_performance(self):
        """Validate Secure Credential Manager performance.""" 
        logger.info("🔐 Validating Credential Manager Performance...")
        
        import os
        os.environ["CREDENTIAL_MASTER_KEY"] = f"perf_test_{int(time.time())}"
        
        from core.secure_credential_manager import SecureCredentialManager, CredentialType
        
        manager = SecureCredentialManager()
        
        # Test credential operations speed
        store_times = []
        retrieve_times = []
        
        for i in range(10):
            cred_id = f"perf_test_{i}"
            cred_value = f"test_value_{i}_" + "x" * 100  # 100+ char value
            
            # Store performance
            start = time.time()
            manager.store_credential(
                credential_id=cred_id,
                credential_value=cred_value,
                credential_type=CredentialType.API_TOKEN
            )
            store_times.append((time.time() - start) * 1000)
            
            # Retrieve performance
            start = time.time()
            retrieved = manager.retrieve_credential(cred_id)
            retrieve_times.append((time.time() - start) * 1000)
            
            # Cleanup
            manager.delete_credential(cred_id)
        
        avg_store = sum(store_times) / len(store_times)
        avg_retrieve = sum(retrieve_times) / len(retrieve_times)
        
        # SLA: Credential ops should be < 50ms average
        store_sla = avg_store < 50
        retrieve_sla = avg_retrieve < 50
        
        self.results.extend([
            {
                "component": "Secure Credential Manager",
                "metric": "Store Operation Time",
                "average_ms": round(avg_store, 2),
                "sla_target": "< 50ms avg",
                "sla_met": store_sla,
                "status": "PASS" if store_sla else "FAIL"
            },
            {
                "component": "Secure Credential Manager", 
                "metric": "Retrieve Operation Time",
                "average_ms": round(avg_retrieve, 2),
                "sla_target": "< 50ms avg",
                "sla_met": retrieve_sla,
                "status": "PASS" if retrieve_sla else "FAIL"
            }
        ])
        
        logger.info(f"   Store: {avg_store:.2f}ms - {'PASS' if store_sla else 'FAIL'}")
        logger.info(f"   Retrieve: {avg_retrieve:.2f}ms - {'PASS' if retrieve_sla else 'FAIL'}")
    
    def _validate_drift_detection_performance(self):
        """Validate Config Drift Detection performance."""
        logger.info("📊 Validating Drift Detection Performance...")
        
        from core.config_drift_detector import ConfigurationDriftDetector
        
        detector = ConfigurationDriftDetector()
        
        # Test monitoring startup time
        start = time.time()
        monitoring_started = detector.start_monitoring()
        startup_time = (time.time() - start) * 1000
        
        # Test drift detection time
        start = time.time()
        drift_events = detector.detect_drift(compare_with_baseline=True)
        detection_time = (time.time() - start) * 1000
        
        detector.stop_monitoring()
        
        # SLA: Startup < 1000ms, Detection < 500ms
        startup_sla = startup_time < 1000
        detection_sla = detection_time < 500
        
        self.results.extend([
            {
                "component": "Config Drift Detector",
                "metric": "Monitoring Startup Time", 
                "time_ms": round(startup_time, 2),
                "sla_target": "< 1000ms",
                "sla_met": startup_sla,
                "status": "PASS" if startup_sla else "FAIL"
            },
            {
                "component": "Config Drift Detector",
                "metric": "Drift Detection Time",
                "time_ms": round(detection_time, 2), 
                "sla_target": "< 500ms",
                "sla_met": detection_sla,
                "status": "PASS" if detection_sla else "FAIL"
            }
        ])
        
        logger.info(f"   Startup: {startup_time:.2f}ms - {'PASS' if startup_sla else 'FAIL'}")
        logger.info(f"   Detection: {detection_time:.2f}ms - {'PASS' if detection_sla else 'FAIL'}")
    
    def _validate_api_performance(self):
        """Validate API component performance."""
        logger.info("🔌 Validating API Component Performance...")
        
        # Test ForecastAdapter performance
        from api.forecast_adapter import ForecastAdapter
        
        adapter = ForecastAdapter()
        
        # Test forecast preparation time
        times = []
        for _ in range(5):
            start = time.time()
            response = adapter.prepare_forecast_response(
                horizon="24h",
                variables=["temperature", "humidity", "wind_speed"],
                forecast_data={
                    "variables": {
                        "temperature": {"value": 20.5, "unit": "°C"},
                        "humidity": {"value": 65.0, "unit": "%"},
                        "wind_speed": {"value": 5.2, "unit": "m/s"}
                    },
                    "latency_ms": 50
                }
            )
            times.append((time.time() - start) * 1000)
        
        avg_time = sum(times) / len(times)
        
        # SLA: Response preparation < 10ms
        sla_met = avg_time < 10
        
        self.results.append({
            "component": "Forecast Adapter",
            "metric": "Response Preparation Time",
            "average_ms": round(avg_time, 2),
            "sla_target": "< 10ms avg",
            "sla_met": sla_met,
            "status": "PASS" if sla_met else "FAIL"
        })
        
        logger.info(f"   Response Prep: {avg_time:.2f}ms - {'PASS' if sla_met else 'FAIL'}")
        
        # Test SecurityMiddleware performance
        from api.security_middleware import SecurityMiddleware
        
        middleware = SecurityMiddleware()
        
        # Test token verification performance
        times = []
        test_token = "test_integration_token_final"
        
        for _ in range(100):
            start = time.time()
            result = middleware.verify_token(test_token)
            times.append((time.time() - start) * 1000)
        
        avg_time = sum(times) / len(times)
        
        # SLA: Token verification < 1ms
        sla_met = avg_time < 1
        
        self.results.append({
            "component": "Security Middleware",
            "metric": "Token Verification Time",
            "average_ms": round(avg_time, 4),
            "sla_target": "< 1ms avg",
            "sla_met": sla_met,
            "status": "PASS" if sla_met else "FAIL"
        })
        
        logger.info(f"   Token Verification: {avg_time:.4f}ms - {'PASS' if sla_met else 'FAIL'}")
    
    def _generate_performance_report(self) -> Dict[str, Any]:
        """Generate final performance validation report."""
        passed_tests = [r for r in self.results if r["status"] == "PASS"]
        failed_tests = [r for r in self.results if r["status"] == "FAIL"]
        
        performance_sla_met = len(failed_tests) == 0
        
        report = {
            "performance_validation": {
                "overall_status": "PASS" if performance_sla_met else "FAIL",
                "total_tests": len(self.results),
                "passed_tests": len(passed_tests),
                "failed_tests": len(failed_tests),
                "success_rate_percent": round((len(passed_tests) / len(self.results)) * 100, 2)
            },
            "sla_compliance": {
                "all_slas_met": performance_sla_met,
                "critical_failures": len([r for r in failed_tests if "Critical" in r.get("component", "")]),
                "performance_ready": performance_sla_met
            },
            "detailed_results": self.results,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
        return report

def main():
    """Execute performance validation."""
    validator = PerformanceValidator()
    report = validator.validate_all_components()
    
    # Print summary
    perf = report["performance_validation"]
    sla = report["sla_compliance"]
    
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Overall Status: {'✅ PASS' if perf['overall_status'] == 'PASS' else '❌ FAIL'}")
    print(f"Tests Passed: {perf['passed_tests']}/{perf['total_tests']} ({perf['success_rate_percent']}%)")
    print(f"SLA Compliance: {'✅ ALL SLAs MET' if sla['all_slas_met'] else '❌ SLA VIOLATIONS'}")
    print(f"Production Ready: {'✅ YES' if sla['performance_ready'] else '❌ NO'}")
    
    if report["detailed_results"]:
        print(f"\n📈 Component Performance Results:")
        for result in report["detailed_results"]:
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            print(f"   {status_icon} {result['component']}: {result['metric']}")
            if "average_ms" in result:
                print(f"      Time: {result['average_ms']}ms (Target: {result['sla_target']})")
            elif "time_ms" in result:
                print(f"      Time: {result['time_ms']}ms (Target: {result['sla_target']})")
    
    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = Path(__file__).parent / f"performance_validation_report_{timestamp}.json"
    
    import json
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved: {report_file}")
    
    return 0 if sla["performance_ready"] else 1

if __name__ == "__main__":
    exit(main())