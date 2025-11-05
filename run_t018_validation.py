#!/usr/bin/env python3
"""
T-018 Performance Validation Orchestrator
==========================================

Master orchestrator for T-018 performance validation that integrates with
existing testing infrastructure and validates all components together.

This script coordinates:
1. System startup and readiness validation
2. T-005 compression middleware validation  
3. T-011 FAISS health monitoring validation
4. T-018 SLA target validation
5. Load testing and resource monitoring
6. Comprehensive reporting and production readiness assessment

Integration Points:
- Uses existing run_comprehensive_performance_tests.py orchestrator
- Integrates new performance_validation_suite.py SLA validation
- Validates api_performance_integration_test.py results
- Monitors FAISS health during testing via T-011
- Analyzes T-005 compression impact on performance

Author: Performance Specialist  
Version: 1.0.0 - T-018 Master Validation
"""

import asyncio
import subprocess
import sys
import os
import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class T018ValidationOrchestrator:
    """Master orchestrator for comprehensive T-018 performance validation."""
    
    def __init__(self, api_url: str = "http://localhost:8000", api_token: str = None):
        """Initialize T-018 validation orchestrator.
        
        Args:
            api_url: Base URL for API testing
            api_token: Authentication token for API requests
        """
        self.api_url = api_url
        self.api_token = api_token or os.getenv("API_TOKEN")
        self.start_time = datetime.now(timezone.utc)
        
        # Validation results storage
        self.validation_results = {
            "orchestrator_info": {
                "start_time": self.start_time.isoformat(),
                "api_url": api_url,
                "validation_version": "1.0.0"
            },
            "prerequisites": {},
            "t005_compression_validation": {},
            "t011_faiss_monitoring_validation": {},
            "t018_sla_validation": {},
            "integration_validation": {},
            "production_readiness": {}
        }
        
        # Output directory for all results
        self.output_dir = Path("t018_validation_results")
        self.output_dir.mkdir(exist_ok=True)
        
        logger.info("🎯 T-018 Performance Validation Orchestrator initialized")
        logger.info(f"   API URL: {api_url}")
        logger.info(f"   Token configured: {'Yes' if self.api_token else 'No'}")
        logger.info(f"   Output directory: {self.output_dir}")
        
    def check_prerequisites(self) -> bool:
        """Check all prerequisites for T-018 validation."""
        logger.info("🔍 Checking T-018 validation prerequisites...")
        
        prerequisites = {
            "python_version": sys.version_info >= (3, 8),
            "api_token_configured": bool(self.api_token),
            "required_scripts_exist": True,
            "system_resources": True,
            "api_accessibility": False
        }
        
        # Check required validation scripts
        required_scripts = [
            "performance_validation_suite.py",
            "run_comprehensive_performance_tests.py", 
            "api_performance_integration_test.py"
        ]
        
        for script in required_scripts:
            if not Path(script).exists():
                logger.error(f"❌ Missing required script: {script}")
                prerequisites["required_scripts_exist"] = False
        
        # Check system resources
        memory_gb = psutil.virtual_memory().total / (1024**3)
        if memory_gb < 4:
            logger.warning(f"⚠️ Low system memory: {memory_gb:.1f}GB (recommended: ≥4GB)")
            prerequisites["system_resources"] = False
        
        # Check API accessibility
        try:
            import requests
            response = requests.get(f"{self.api_url}/health", timeout=10, 
                                    headers={"Authorization": f"Bearer {self.api_token}"})
            if response.status_code == 200:
                prerequisites["api_accessibility"] = True
                logger.info("✅ API is accessible and responding")
            else:
                logger.warning(f"⚠️ API returned status {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️ API accessibility check failed: {e}")
        
        self.validation_results["prerequisites"] = prerequisites
        
        # Summary
        essential_checks = ["python_version", "api_token_configured", "required_scripts_exist"]
        essential_passed = all(prerequisites[check] for check in essential_checks)
        
        if essential_passed:
            logger.info("✅ Essential prerequisites met")
            return True
        else:
            logger.error("❌ Essential prerequisites not met")
            return False
            
    async def validate_t005_compression_integration(self) -> bool:
        """Validate T-005 compression middleware integration and performance."""
        logger.info("📦 Validating T-005 compression middleware integration...")
        
        validation_result = {
            "test_start_time": datetime.now(timezone.utc).isoformat(),
            "compression_detected": False,
            "compression_ratio": None,
            "performance_impact": {},
            "middleware_active": False
        }
        
        try:
            # Test compression by making requests and checking headers
            import aiohttp
            
            async with aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Accept-Encoding": "gzip, deflate"
                }
            ) as session:
                
                # Test forecast endpoint with compression
                start_time = time.time()
                async with session.get(
                    f"{self.api_url}/forecast",
                    params={"horizon": "24h", "vars": "t2m,u10,v10,msl"}
                ) as response:
                    response_time = (time.time() - start_time) * 1000
                    response_text = await response.text()
                    
                    # Check for compression headers
                    compression_detected = 'content-encoding' in response.headers
                    compression_ratio = None
                    
                    if 'x-compression-ratio' in response.headers:
                        try:
                            compression_ratio = float(response.headers['x-compression-ratio'])
                        except ValueError:
                            pass
                    
                    validation_result.update({
                        "compression_detected": compression_detected,
                        "compression_ratio": compression_ratio,
                        "response_time_ms": response_time,
                        "response_size_bytes": len(response_text.encode()),
                        "middleware_active": response.headers.get('x-response-time') is not None
                    })
                    
                    if compression_detected:
                        logger.info(f"✅ Compression detected: ratio={compression_ratio}")
                        logger.info(f"   Response time: {response_time:.1f}ms")
                        logger.info(f"   Response size: {len(response_text)} chars")
                    else:
                        logger.warning("⚠️ No compression detected in response")
        
        except Exception as e:
            logger.error(f"❌ T-005 compression validation failed: {e}")
            validation_result["error"] = str(e)
            
        self.validation_results["t005_compression_validation"] = validation_result
        return validation_result.get("compression_detected", False)
        
    async def validate_t011_faiss_monitoring_integration(self) -> bool:
        """Validate T-011 FAISS health monitoring integration."""
        logger.info("🔍 Validating T-011 FAISS health monitoring integration...")
        
        validation_result = {
            "test_start_time": datetime.now(timezone.utc).isoformat(),
            "faiss_health_endpoint_accessible": False,
            "monitoring_active": False,
            "performance_metrics_available": False
        }
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.api_token}"}
            ) as session:
                
                # Test FAISS health endpoint
                async with session.get(f"{self.api_url}/health/faiss") as response:
                    if response.status == 200:
                        health_data = await response.json()
                        
                        validation_result.update({
                            "faiss_health_endpoint_accessible": True,
                            "monitoring_active": health_data.get("status") in ["healthy", "degraded"],
                            "performance_metrics_available": "query_performance" in health_data,
                            "faiss_status": health_data.get("status"),
                            "indices_monitored": len(health_data.get("indices", {}))
                        })
                        
                        logger.info(f"✅ FAISS health monitoring active")
                        logger.info(f"   Status: {health_data.get('status')}")
                        logger.info(f"   Indices monitored: {len(health_data.get('indices', {}))}")
                    else:
                        logger.warning(f"⚠️ FAISS health endpoint returned {response.status}")
                        
        except Exception as e:
            logger.error(f"❌ T-011 FAISS monitoring validation failed: {e}")
            validation_result["error"] = str(e)
            
        self.validation_results["t011_faiss_monitoring_validation"] = validation_result
        return validation_result.get("monitoring_active", False)
        
    async def run_t018_sla_validation(self) -> bool:
        """Run comprehensive T-018 SLA validation using the dedicated suite."""
        logger.info("🎯 Running T-018 SLA validation suite...")
        
        try:
            # Set environment variables for the validation suite
            env = os.environ.copy()
            env["API_BASE_URL"] = self.api_url
            env["API_TOKEN"] = self.api_token
            
            # Run the T-018 validation suite
            start_time = time.time()
            
            process = await asyncio.create_subprocess_exec(
                sys.executable, "performance_validation_suite.py",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env
            )
            
            stdout, _ = await process.communicate()
            end_time = time.time()
            
            # Parse output
            output_text = stdout.decode('utf-8')
            
            # Save raw output
            with open(self.output_dir / "t018_sla_validation_output.log", "w") as f:
                f.write(output_text)
            
            # Try to load JSON report if generated
            sla_report = {}
            report_file = Path("t018_performance_validation_report.json")
            if report_file.exists():
                with open(report_file, "r") as f:
                    sla_report = json.load(f)
                
                # Move to output directory
                report_file.rename(self.output_dir / "t018_performance_validation_report.json")
            
            # Store results
            validation_result = {
                "success": process.returncode == 0,
                "duration_seconds": end_time - start_time,
                "output_lines": len(output_text.split('\n')),
                "report_data": sla_report,
                "production_ready": process.returncode == 0
            }
            
            if process.returncode == 0:
                logger.info(f"✅ T-018 SLA validation PASSED in {end_time - start_time:.1f}s")
            else:
                logger.error(f"❌ T-018 SLA validation FAILED (exit code: {process.returncode})")
            
            self.validation_results["t018_sla_validation"] = validation_result
            return validation_result["success"]
            
        except Exception as e:
            logger.error(f"❌ Failed to run T-018 SLA validation: {e}")
            self.validation_results["t018_sla_validation"] = {
                "success": False,
                "error": str(e)
            }
            return False
            
    async def run_integration_validation(self) -> bool:
        """Run existing integration tests to validate overall system integration."""
        logger.info("🔗 Running integration validation tests...")
        
        try:
            # Set environment variables
            env = os.environ.copy()
            env["API_BASE_URL"] = self.api_url
            env["API_TOKEN"] = self.api_token
            
            # Run the existing comprehensive performance tests
            start_time = time.time()
            
            process = await asyncio.create_subprocess_exec(
                sys.executable, "run_comprehensive_performance_tests.py",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env
            )
            
            stdout, _ = await process.communicate()
            end_time = time.time()
            
            # Parse output
            output_text = stdout.decode('utf-8')
            
            # Save raw output
            with open(self.output_dir / "integration_validation_output.log", "w") as f:
                f.write(output_text)
            
            # Store results
            validation_result = {
                "success": process.returncode == 0,
                "duration_seconds": end_time - start_time,
                "output_lines": len(output_text.split('\n')),
                "comprehensive_tests_passed": process.returncode == 0
            }
            
            if process.returncode == 0:
                logger.info(f"✅ Integration validation PASSED in {end_time - start_time:.1f}s")
            else:
                logger.warning(f"⚠️ Integration validation issues (exit code: {process.returncode})")
            
            self.validation_results["integration_validation"] = validation_result
            return validation_result["success"]
            
        except Exception as e:
            logger.error(f"❌ Failed to run integration validation: {e}")
            self.validation_results["integration_validation"] = {
                "success": False,
                "error": str(e)
            }
            return False
            
    def assess_production_readiness(self) -> Dict[str, Any]:
        """Assess overall production readiness based on all validation results."""
        logger.info("🚀 Assessing production readiness...")
        
        # Gather validation results
        prerequisites_ok = all(self.validation_results["prerequisites"].values())
        t005_compression_ok = self.validation_results["t005_compression_validation"].get("compression_detected", False)
        t011_monitoring_ok = self.validation_results["t011_faiss_monitoring_validation"].get("monitoring_active", False)
        t018_sla_ok = self.validation_results["t018_sla_validation"].get("success", False)
        integration_ok = self.validation_results["integration_validation"].get("success", False)
        
        # Calculate overall readiness
        critical_requirements = [t018_sla_ok, integration_ok]
        optional_enhancements = [t005_compression_ok, t011_monitoring_ok]
        
        critical_passed = all(critical_requirements)
        enhancements_passed = all(optional_enhancements)
        
        # Determine readiness level
        if critical_passed and enhancements_passed:
            readiness_level = "FULLY_READY"
            readiness_description = "All critical requirements and enhancements validated"
        elif critical_passed:
            readiness_level = "READY_WITH_WARNINGS"
            readiness_description = "Critical requirements met, some enhancements not validated"
        else:
            readiness_level = "NOT_READY"
            readiness_description = "Critical requirements not met"
        
        assessment = {
            "readiness_level": readiness_level,
            "description": readiness_description,
            "production_ready": critical_passed,
            "critical_requirements": {
                "t018_sla_targets": t018_sla_ok,
                "system_integration": integration_ok
            },
            "enhancements_validated": {
                "t005_compression": t005_compression_ok,
                "t011_faiss_monitoring": t011_monitoring_ok
            },
            "prerequisites_met": prerequisites_ok,
            "validation_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        self.validation_results["production_readiness"] = assessment
        
        # Log assessment
        logger.info(f"🚀 Production Readiness: {readiness_level}")
        logger.info(f"   {readiness_description}")
        logger.info(f"   Critical requirements: {'✅' if critical_passed else '❌'}")
        logger.info(f"   Enhancements validated: {'✅' if enhancements_passed else '⚠️'}")
        
        return assessment
        
    def generate_executive_summary(self) -> Dict[str, Any]:
        """Generate executive summary of T-018 validation."""
        total_duration = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        
        summary = {
            "t018_validation_executive_summary": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_duration_minutes": total_duration / 60,
                "validation_scope": [
                    "T-005 Performance Middleware Compression",
                    "T-011 FAISS Health Monitoring", 
                    "T-018 SLA Target Validation",
                    "System Integration Testing",
                    "Production Readiness Assessment"
                ],
                "production_readiness": self.validation_results["production_readiness"],
                "key_findings": [],
                "recommendations": []
            }
        }
        
        # Generate key findings
        findings = []
        readiness = self.validation_results["production_readiness"]
        
        if readiness["production_ready"]:
            findings.append("All critical performance requirements validated successfully")
        else:
            findings.append("Critical performance requirements not fully met")
            
        if readiness["enhancements_validated"]["t005_compression"]:
            findings.append("T-005 compression middleware active and performing well")
        else:
            findings.append("T-005 compression middleware needs investigation")
            
        if readiness["enhancements_validated"]["t011_faiss_monitoring"]:
            findings.append("T-011 FAISS health monitoring operational")
        else:
            findings.append("T-011 FAISS health monitoring needs attention")
        
        # Generate recommendations
        recommendations = []
        if readiness["production_ready"]:
            recommendations.append("System approved for production deployment")
            recommendations.append("Monitor performance metrics post-deployment")
        else:
            recommendations.append("Address critical SLA validation failures before deployment")
            recommendations.append("Review failed test results and optimize accordingly")
            
        if not readiness["enhancements_validated"]["t005_compression"]:
            recommendations.append("Investigate T-005 compression middleware configuration")
            
        if not readiness["enhancements_validated"]["t011_faiss_monitoring"]:
            recommendations.append("Verify T-011 FAISS monitoring service status")
        
        summary["t018_validation_executive_summary"]["key_findings"] = findings
        summary["t018_validation_executive_summary"]["recommendations"] = recommendations
        
        return summary
        
    def print_validation_dashboard(self):
        """Print comprehensive T-018 validation dashboard."""
        print("\n" + "="*100)
        print("🎯 T-018 PERFORMANCE VALIDATION DASHBOARD") 
        print("="*100)
        
        readiness = self.validation_results["production_readiness"]
        
        # Overall Status
        status_icon = "✅" if readiness["production_ready"] else "❌"
        print(f"\n{status_icon} OVERALL STATUS: {readiness['readiness_level']}")
        print(f"   {readiness['description']}")
        
        # Critical Requirements
        print(f"\n🔥 CRITICAL REQUIREMENTS:")
        critical = readiness["critical_requirements"]
        for req, passed in critical.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {status} {req}")
        
        # Enhancement Validation
        print(f"\n⚡ ENHANCEMENT VALIDATION:")
        enhancements = readiness["enhancements_validated"]
        for enhancement, validated in enhancements.items():
            status = "✅ VALIDATED" if validated else "⚠️ NOT VALIDATED"
            print(f"   {status} {enhancement}")
        
        # Test Results Summary
        print(f"\n📊 VALIDATION RESULTS:")
        
        # Prerequisites
        prereq_passed = all(self.validation_results["prerequisites"].values())
        print(f"   {'✅' if prereq_passed else '❌'} Prerequisites: {'PASSED' if prereq_passed else 'FAILED'}")
        
        # T-005 Compression
        compression_ok = self.validation_results["t005_compression_validation"].get("compression_detected", False)
        print(f"   {'✅' if compression_ok else '⚠️'} T-005 Compression: {'ACTIVE' if compression_ok else 'NOT DETECTED'}")
        
        # T-011 Monitoring
        monitoring_ok = self.validation_results["t011_faiss_monitoring_validation"].get("monitoring_active", False)
        print(f"   {'✅' if monitoring_ok else '⚠️'} T-011 FAISS Monitoring: {'ACTIVE' if monitoring_ok else 'NOT ACTIVE'}")
        
        # T-018 SLA
        sla_ok = self.validation_results["t018_sla_validation"].get("success", False)
        print(f"   {'✅' if sla_ok else '❌'} T-018 SLA Validation: {'PASSED' if sla_ok else 'FAILED'}")
        
        # Integration
        integration_ok = self.validation_results["integration_validation"].get("success", False)
        print(f"   {'✅' if integration_ok else '❌'} Integration Tests: {'PASSED' if integration_ok else 'FAILED'}")
        
        # Final Recommendation
        print(f"\n🚀 DEPLOYMENT RECOMMENDATION:")
        if readiness["production_ready"]:
            print("   ✅ APPROVED FOR PRODUCTION DEPLOYMENT")
            print("   ✅ All critical performance requirements validated")
        else:
            print("   ❌ NOT APPROVED FOR PRODUCTION DEPLOYMENT") 
            print("   ❌ Critical requirements must be addressed first")
        
        print(f"\n📁 Detailed results available in: {self.output_dir}")
        print("="*100)
        
    def save_comprehensive_report(self):
        """Save comprehensive validation report."""
        logger.info("💾 Saving comprehensive T-018 validation report...")
        
        # Generate executive summary
        executive_summary = self.generate_executive_summary()
        
        # Combine all results
        comprehensive_report = {
            **self.validation_results,
            **executive_summary
        }
        
        # Save main report
        report_path = self.output_dir / "t018_comprehensive_validation_report.json"
        with open(report_path, "w") as f:
            json.dump(comprehensive_report, f, indent=2, default=str)
        
        # Save executive summary separately
        summary_path = self.output_dir / "t018_executive_summary.json"
        with open(summary_path, "w") as f:
            json.dump(executive_summary, f, indent=2, default=str)
        
        logger.info(f"✅ Comprehensive report saved: {report_path}")
        logger.info(f"📄 Executive summary saved: {summary_path}")

async def main():
    """Main T-018 validation orchestration workflow."""
    print("🚀 T-018 Performance Validation Orchestrator")
    print("=" * 80)
    
    # Configuration
    api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    api_token = os.getenv("API_TOKEN")
    
    if not api_token:
        logger.error("❌ API_TOKEN environment variable is required")
        print("Please set API_TOKEN environment variable and try again.")
        sys.exit(1)
    
    # Initialize orchestrator
    orchestrator = T018ValidationOrchestrator(api_url=api_url, api_token=api_token)
    
    try:
        # Step 1: Check prerequisites
        prerequisites_ok = orchestrator.check_prerequisites()
        if not prerequisites_ok:
            logger.warning("⚠️ Some prerequisites not met - proceeding with validation...")
        
        # Step 2: Validate T-005 compression integration
        await orchestrator.validate_t005_compression_integration()
        
        # Step 3: Validate T-011 FAISS monitoring integration
        await orchestrator.validate_t011_faiss_monitoring_integration()
        
        # Step 4: Run comprehensive T-018 SLA validation
        await orchestrator.run_t018_sla_validation()
        
        # Step 5: Run integration validation
        await orchestrator.run_integration_validation()
        
        # Step 6: Assess production readiness
        readiness = orchestrator.assess_production_readiness()
        
        # Step 7: Generate reports
        orchestrator.save_comprehensive_report()
        
        # Step 8: Display final dashboard
        orchestrator.print_validation_dashboard()
        
        # Exit with appropriate code
        if readiness["production_ready"]:
            print("\n🎉 T-018 Performance Validation COMPLETED SUCCESSFULLY!")
            print("🚀 System is ready for production deployment.")
            sys.exit(0)
        else:
            print("\n⚠️ T-018 Performance Validation COMPLETED WITH ISSUES.")
            print("🔧 Address critical requirements before production deployment.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\n⏹️ T-018 validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n💥 T-018 validation orchestration failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())