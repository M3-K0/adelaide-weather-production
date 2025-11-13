#!/usr/bin/env python3
"""
Monitoring Gates Validation Script
==================================

Validates critical monitoring gates for CI/CD pipeline enforcement:
1. analog_fallback_total metrics validation
2. Security drift critical events detection
3. FAISS health operational status
4. Prometheus metrics availability

This script is used by the CI/CD pipeline to enforce quality gates.

Author: Design Systems Architect & Monitoring Engineer
Version: 1.0.0 - CI1 Implementation
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

import requests
from prometheus_client import CollectorRegistry, generate_latest


class MonitoringGateValidator:
    """Validates monitoring gates for CI/CD pipeline."""
    
    def __init__(self, 
                 api_base_url: str = "http://localhost:8000",
                 prometheus_url: str = "http://localhost:9090"):
        self.api_base_url = api_base_url
        self.prometheus_url = prometheus_url
        self.validation_results: Dict = {}
        self.critical_failures: List[str] = []
        
    async def validate_all_gates(self) -> bool:
        """Validate all monitoring gates. Returns True if all pass."""
        print("🚦 Starting monitoring gates validation...")
        print(f"API Base URL: {self.api_base_url}")
        print(f"Prometheus URL: {self.prometheus_url}")
        print("-" * 60)
        
        # Run all validations
        gates = [
            ("analog_fallback", self.validate_analog_fallback_metrics),
            ("security_drift", self.validate_security_drift),
            ("faiss_health", self.validate_faiss_health),
            ("prometheus_metrics", self.validate_prometheus_metrics)
        ]
        
        all_passed = True
        for gate_name, validator in gates:
            try:
                print(f"\n🔍 Validating {gate_name}...")
                result = await validator()
                self.validation_results[gate_name] = result
                
                if not result["passed"]:
                    all_passed = False
                    if result.get("critical", False):
                        self.critical_failures.append(gate_name)
                        
                self._print_gate_result(gate_name, result)
                
            except Exception as e:
                print(f"❌ {gate_name} validation failed with exception: {e}")
                self.validation_results[gate_name] = {
                    "passed": False,
                    "critical": True,
                    "error": str(e),
                    "message": f"Validation error: {e}"
                }
                self.critical_failures.append(gate_name)
                all_passed = False
        
        # Print summary
        self._print_summary()
        
        return all_passed and len(self.critical_failures) == 0
    
    async def validate_analog_fallback_metrics(self) -> Dict:
        """Validate analog fallback metrics - CRITICAL GATE."""
        try:
            # Try to import and check analog metrics
            sys.path.append('.')
            from api.analog_metrics import analog_fallback_total
            
            # Get current fallback count
            current_fallbacks = analog_fallback_total._value._value
            
            if current_fallbacks > 0:
                return {
                    "passed": False,
                    "critical": True,
                    "fallback_count": current_fallbacks,
                    "message": f"CRITICAL: analog_fallback_total = {current_fallbacks} > 0",
                    "details": {
                        "metric_name": "analog_fallback_total",
                        "current_value": current_fallbacks,
                        "threshold": 0,
                        "severity": "CRITICAL"
                    }
                }
            else:
                return {
                    "passed": True,
                    "critical": False,
                    "fallback_count": current_fallbacks,
                    "message": f"✅ analog_fallback_total = {current_fallbacks}",
                    "details": {
                        "metric_name": "analog_fallback_total",
                        "current_value": current_fallbacks,
                        "threshold": 0
                    }
                }
                
        except Exception as e:
            return {
                "passed": False,
                "critical": True,
                "error": str(e),
                "message": f"Failed to check analog fallback metrics: {e}"
            }
    
    async def validate_security_drift(self) -> Dict:
        """Validate security drift detection - CRITICAL GATE."""
        try:
            # Check via health endpoint
            response = requests.get(
                f"{self.api_base_url}/health/security",
                timeout=30
            )
            
            if response.status_code == 503:
                # Service unavailable due to critical security issues
                data = response.json()
                return {
                    "passed": False,
                    "critical": True,
                    "status_code": response.status_code,
                    "message": f"CRITICAL: Security drift critical events detected",
                    "details": data
                }
            elif response.status_code == 200:
                data = response.json()
                security_status = data.get("security_status", "unknown")
                config_drift = data.get("configuration_drift", {})
                critical_events = config_drift.get("events_by_severity", {}).get("critical", 0)
                
                if security_status == "critical" or critical_events > 0:
                    return {
                        "passed": False,
                        "critical": True,
                        "security_status": security_status,
                        "critical_events": critical_events,
                        "message": f"CRITICAL: Security drift critical events = {critical_events}",
                        "details": data
                    }
                else:
                    return {
                        "passed": True,
                        "critical": False,
                        "security_status": security_status,
                        "critical_events": critical_events,
                        "message": f"✅ Security drift status: {security_status}, critical events: {critical_events}",
                        "details": {
                            "security_status": security_status,
                            "total_events": config_drift.get("total_events", 0),
                            "events_by_severity": config_drift.get("events_by_severity", {})
                        }
                    }
            else:
                return {
                    "passed": False,
                    "critical": True,
                    "status_code": response.status_code,
                    "message": f"Security drift endpoint returned {response.status_code}",
                    "details": {"response_text": response.text}
                }
                
        except Exception as e:
            return {
                "passed": False,
                "critical": True,
                "error": str(e),
                "message": f"Failed to check security drift: {e}"
            }
    
    async def validate_faiss_health(self) -> Dict:
        """Validate FAISS health status."""
        try:
            # Check FAISS health endpoint
            response = requests.get(
                f"{self.api_base_url}/health/faiss",
                timeout=30
            )
            
            if response.status_code == 503:
                # FAISS unhealthy
                data = response.json()
                return {
                    "passed": False,
                    "critical": False,  # FAISS issues are serious but not deployment-blocking
                    "status_code": response.status_code,
                    "faiss_status": data.get("faiss_status", "unhealthy"),
                    "message": f"FAISS system unhealthy: {data.get('message', 'Unknown')}",
                    "details": data
                }
            elif response.status_code == 200:
                data = response.json()
                faiss_status = data.get("faiss_status", "unknown")
                index_readiness = data.get("index_readiness", {})
                degraded_mode = data.get("degraded_mode", {}).get("active", False)
                
                # Count ready indices
                ready_indices = 0
                total_expected = 8  # 4 horizons × 2 index types
                
                for horizon in ["6h", "12h", "24h", "48h"]:
                    horizon_data = index_readiness.get(horizon, {})
                    if horizon_data.get("flatip_ready", False):
                        ready_indices += 1
                    if horizon_data.get("ivfpq_ready", False):
                        ready_indices += 1
                
                if faiss_status == "unhealthy":
                    return {
                        "passed": False,
                        "critical": False,
                        "faiss_status": faiss_status,
                        "ready_indices": ready_indices,
                        "total_expected": total_expected,
                        "degraded_mode": degraded_mode,
                        "message": f"FAISS unhealthy: {ready_indices}/{total_expected} indices ready",
                        "details": data
                    }
                else:
                    return {
                        "passed": True,
                        "critical": False,
                        "faiss_status": faiss_status,
                        "ready_indices": ready_indices,
                        "total_expected": total_expected,
                        "degraded_mode": degraded_mode,
                        "message": f"✅ FAISS {faiss_status}: {ready_indices}/{total_expected} indices ready",
                        "details": {
                            "faiss_status": faiss_status,
                            "index_readiness_summary": f"{ready_indices}/{total_expected}",
                            "degraded_mode": degraded_mode
                        }
                    }
            else:
                return {
                    "passed": False,
                    "critical": False,
                    "status_code": response.status_code,
                    "message": f"FAISS health endpoint returned {response.status_code}",
                    "details": {"response_text": response.text}
                }
                
        except Exception as e:
            return {
                "passed": False,
                "critical": False,
                "error": str(e),
                "message": f"Failed to check FAISS health: {e}"
            }
    
    async def validate_prometheus_metrics(self) -> Dict:
        """Validate Prometheus metrics availability."""
        try:
            # Check if Prometheus is reachable
            response = requests.get(f"{self.prometheus_url}/-/ready", timeout=10)
            if response.status_code != 200:
                return {
                    "passed": False,
                    "critical": False,
                    "status_code": response.status_code,
                    "message": f"Prometheus not ready: {response.status_code}",
                    "details": {"prometheus_url": self.prometheus_url}
                }
            
            # Query analog fallback metrics
            metrics_response = requests.get(
                f"{self.prometheus_url}/api/v1/query?query=analog_fallback_total",
                timeout=15
            )
            
            if metrics_response.status_code != 200:
                return {
                    "passed": False,
                    "critical": False,
                    "status_code": metrics_response.status_code,
                    "message": "Failed to query Prometheus metrics",
                    "details": {"query": "analog_fallback_total"}
                }
            
            data = metrics_response.json()
            if data.get("status") != "success":
                return {
                    "passed": False,
                    "critical": False,
                    "prometheus_status": data.get("status"),
                    "message": f"Prometheus query failed: {data.get('error', 'Unknown')}",
                    "details": data
                }
            
            # Check metric values
            result = data.get("data", {}).get("result", [])
            if not result:
                # No metrics found - could be OK if no fallbacks have occurred
                return {
                    "passed": True,
                    "critical": False,
                    "metrics_found": False,
                    "message": "✅ Prometheus reachable, no fallback metrics (expected for clean system)",
                    "details": {
                        "prometheus_status": "ready",
                        "analog_fallback_total": 0,
                        "metrics_available": False
                    }
                }
            else:
                # Metrics found, check values
                fallback_value = float(result[0]["value"][1])
                return {
                    "passed": fallback_value == 0,
                    "critical": fallback_value > 0,
                    "metrics_found": True,
                    "fallback_value": fallback_value,
                    "message": f"✅ Prometheus confirms analog_fallback_total = {fallback_value}",
                    "details": {
                        "prometheus_status": "ready",
                        "analog_fallback_total": fallback_value,
                        "metrics_available": True,
                        "query_result": result[0]
                    }
                }
                
        except Exception as e:
            return {
                "passed": False,
                "critical": False,
                "error": str(e),
                "message": f"Failed to validate Prometheus metrics: {e}"
            }
    
    def _print_gate_result(self, gate_name: str, result: Dict):
        """Print formatted gate result."""
        status = "✅ PASSED" if result["passed"] else "❌ FAILED"
        critical = "🚨 CRITICAL" if result.get("critical", False) else ""
        print(f"  {status} {critical}")
        print(f"  Message: {result['message']}")
        
        if "details" in result:
            print(f"  Details: {json.dumps(result['details'], indent=2)}")
        
        if "error" in result:
            print(f"  Error: {result['error']}")
    
    def _print_summary(self):
        """Print validation summary."""
        print("\n" + "="*60)
        print("📊 MONITORING GATES VALIDATION SUMMARY")
        print("="*60)
        
        passed_count = sum(1 for r in self.validation_results.values() if r["passed"])
        total_count = len(self.validation_results)
        critical_count = len(self.critical_failures)
        
        print(f"Total Gates: {total_count}")
        print(f"Passed: {passed_count}")
        print(f"Failed: {total_count - passed_count}")
        print(f"Critical Failures: {critical_count}")
        
        if self.critical_failures:
            print(f"\n🚨 CRITICAL FAILURES:")
            for failure in self.critical_failures:
                result = self.validation_results[failure]
                print(f"  - {failure}: {result['message']}")
        
        # Overall status
        if critical_count > 0:
            print(f"\n❌ VALIDATION RESULT: CRITICAL FAILURES DETECTED")
            print(f"🚫 PIPELINE MUST FAIL")
        elif passed_count == total_count:
            print(f"\n✅ VALIDATION RESULT: ALL GATES PASSED")
            print(f"🎉 READY FOR DEPLOYMENT")
        else:
            print(f"\n⚠️ VALIDATION RESULT: NON-CRITICAL FAILURES")
            print(f"📋 REVIEW WARNINGS BUT PROCEED")
    
    def export_results(self, output_file: str = "monitoring_gates_results.json"):
        """Export validation results to JSON file."""
        results_data = {
            "timestamp": datetime.now().isoformat(),
            "validation_results": self.validation_results,
            "critical_failures": self.critical_failures,
            "summary": {
                "total_gates": len(self.validation_results),
                "passed_gates": sum(1 for r in self.validation_results.values() if r["passed"]),
                "critical_failures": len(self.critical_failures),
                "overall_status": "FAIL" if self.critical_failures else "PASS"
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(results_data, f, indent=2, default=str)
        
        print(f"\n📄 Results exported to: {output_file}")


async def main():
    """Main validation entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate monitoring gates for CI/CD pipeline")
    parser.add_argument("--api-url", default="http://localhost:8000", 
                       help="API base URL")
    parser.add_argument("--prometheus-url", default="http://localhost:9090",
                       help="Prometheus URL") 
    parser.add_argument("--output", default="monitoring_gates_results.json",
                       help="Output file for results")
    parser.add_argument("--fail-on-warnings", action="store_true",
                       help="Fail pipeline on non-critical warnings")
    
    args = parser.parse_args()
    
    # Initialize validator
    validator = MonitoringGateValidator(
        api_base_url=args.api_url,
        prometheus_url=args.prometheus_url
    )
    
    # Run validation
    all_passed = await validator.validate_all_gates()
    
    # Export results
    validator.export_results(args.output)
    
    # Determine exit code
    if validator.critical_failures:
        print(f"\n🚫 CRITICAL FAILURES DETECTED - EXITING WITH CODE 1")
        sys.exit(1)
    elif not all_passed and args.fail_on_warnings:
        print(f"\n⚠️ NON-CRITICAL FAILURES WITH --fail-on-warnings - EXITING WITH CODE 1")
        sys.exit(1)
    elif not all_passed:
        print(f"\n⚠️ NON-CRITICAL FAILURES DETECTED - EXITING WITH CODE 0")
        sys.exit(0)
    else:
        print(f"\n✅ ALL GATES PASSED - EXITING WITH CODE 0")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())