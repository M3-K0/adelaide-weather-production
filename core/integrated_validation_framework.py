#!/usr/bin/env python3
"""
Integrated Validation Framework
===============================

Phase 3: System Hardening - Unified validation framework that combines:
1. Expert-validated startup validation system
2. Production health validator
3. Runtime monitoring and validation

This framework provides a single entry point for all validation activities
with expert-validated thresholds and zero tolerance for silent failures.

Author: QA-Optimization Specialist  
Version: 3.0.0 - Integrated System Hardening
"""

import sys
import time
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict

from .startup_validation_system import ExpertValidatedStartupSystem, StartupValidationResult
from .system_health_validator import ProductionHealthValidator, ValidationResult

logger = logging.getLogger(__name__)

@dataclass
class IntegratedValidationReport:
    """Comprehensive validation report combining all validation systems."""
    validation_framework: str
    validation_timestamp: str
    startup_validation_results: Dict[str, Any]
    health_validation_results: Dict[str, Any]
    overall_status: str  # 'PASS', 'FAIL', 'CRITICAL_FAIL'
    expert_standards_met: bool
    total_validation_time_seconds: float
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class IntegratedValidationFramework:
    """Unified validation framework with expert standards and production monitoring."""
    
    def __init__(self, project_root: Path = None):
        """Initialize integrated validation framework."""
        self.project_root = project_root or Path("/home/micha/weather-forecast-final")
        self.startup_time = time.time()
        
        # Initialize sub-validators
        self.expert_validator = ExpertValidatedStartupSystem(self.project_root)
        self.health_validator = ProductionHealthValidator(self.project_root)
        
        logger.info(f"🎯 Integrated Validation Framework v3.0.0 Initialized")
        logger.info(f"   Project Root: {self.project_root}")
        logger.info(f"   Expert Standards: ENABLED")
        logger.info(f"   Production Health: ENABLED")
    
    def run_complete_validation(self, include_performance: bool = True) -> Tuple[bool, IntegratedValidationReport]:
        """Run complete validation with both expert and production standards.
        
        Args:
            include_performance: Whether to include performance profiling
            
        Returns:
            Tuple of (success, comprehensive_report)
        """
        logger.info("🚀 STARTING COMPLETE INTEGRATED VALIDATION")
        logger.info("=" * 100)
        logger.info("COMPONENTS: Expert Startup Validation + Production Health Monitoring")
        logger.info("STANDARDS: Expert Thresholds + Production Performance Gates")
        logger.info("=" * 100)
        
        validation_start = time.time()
        recommendations = []
        
        # Phase 1: Expert Startup Validation (Critical)
        logger.info("\n📋 PHASE 1: Expert Startup Validation")
        logger.info("-" * 50)
        
        expert_success = self.expert_validator.run_expert_startup_validation()
        startup_results = {
            "validation_passed": expert_success,
            "results": [asdict(r) for r in self.expert_validator.validation_results],
            "system_state": self.expert_validator.system_state.to_dict() if self.expert_validator.system_state else {},
            "expert_thresholds_met": all(r.expert_threshold_met for r in self.expert_validator.validation_results if r.is_passing())
        }
        
        if not expert_success:
            # Critical failure - stop here
            total_time = time.time() - validation_start
            
            report = IntegratedValidationReport(
                validation_framework="Integrated Validation Framework v3.0.0",
                validation_timestamp=datetime.now().isoformat(),
                startup_validation_results=startup_results,
                health_validation_results={"skipped": "Expert validation failed"},
                overall_status="CRITICAL_FAIL",
                expert_standards_met=False,
                total_validation_time_seconds=total_time,
                recommendations=["CRITICAL: Resolve expert startup validation failures before proceeding"]
            )
            
            logger.critical("🚨 EXPERT VALIDATION FAILED - ABORTING FURTHER VALIDATION")
            return False, report
        
        # Phase 2: Production Health Validation (if expert validation passed)
        logger.info("\n🏥 PHASE 2: Production Health Validation")
        logger.info("-" * 50)
        
        health_success = True
        health_results = {"validation_passed": True, "results": [], "performance_metrics": {}}
        
        try:
            # Run production health checks
            health_tests = [
                ("System Versions", self.health_validator.validate_system_versions),
                ("Model Integrity", self.health_validator.validate_model_integrity),
                ("Database Integrity", self.health_validator.validate_database_integrity),
                ("FAISS Indices", self.health_validator.validate_faiss_indices)
            ]
            
            if include_performance:
                health_tests.append(("Performance Profile", self.health_validator.validate_performance_profile))
            
            health_passed = 0
            health_warnings = []
            
            for test_name, test_func in health_tests:
                try:
                    result = test_func()
                    if result.is_passing():
                        health_passed += 1
                    elif result.status == "WARNING":
                        health_warnings.append(f"{test_name}: {result.message}")
                    else:
                        health_success = False
                        logger.warning(f"⚠️ Health validation issue: {test_name} - {result.message}")
                        
                except Exception as e:
                    logger.error(f"❌ Health test {test_name} crashed: {e}")
                    health_success = False
            
            health_results = {
                "validation_passed": health_success,
                "results": [asdict(r) for r in self.health_validator.validation_results],
                "performance_metrics": self.health_validator.performance_metrics,
                "passed_tests": health_passed,
                "total_tests": len(health_tests),
                "warnings": health_warnings
            }
            
            if health_warnings:
                recommendations.extend([f"Monitor: {w}" for w in health_warnings])
                
        except Exception as e:
            logger.error(f"💥 Production health validation crashed: {e}")
            health_success = False
            health_results = {"validation_passed": False, "error": str(e)}
            recommendations.append("URGENT: Investigate production health validation crash")
        
        # Overall Assessment
        total_time = time.time() - validation_start
        overall_success = expert_success and health_success
        expert_standards_met = startup_results.get("expert_thresholds_met", False)
        
        # Determine overall status
        if not expert_success:
            overall_status = "CRITICAL_FAIL"
        elif not expert_standards_met:
            overall_status = "FAIL"
        elif not health_success:
            overall_status = "FAIL"
        else:
            overall_status = "PASS"
        
        # Generate recommendations
        if overall_success and expert_standards_met:
            recommendations.append("✅ System certified for production operation")
            recommendations.append("🎯 All expert thresholds and production standards met")
        elif expert_success but not health_success:
            recommendations.append("⚠️ Expert validation passed but production health issues detected")
            recommendations.append("🔧 Address production health warnings before deployment")
        
        # Create comprehensive report
        report = IntegratedValidationReport(
            validation_framework="Integrated Validation Framework v3.0.0",
            validation_timestamp=datetime.now().isoformat(),
            startup_validation_results=startup_results,
            health_validation_results=health_results,
            overall_status=overall_status,
            expert_standards_met=expert_standards_met,
            total_validation_time_seconds=total_time,
            recommendations=recommendations
        )
        
        # Log final results
        logger.info("\n" + "=" * 100)
        logger.info("INTEGRATED VALIDATION RESULTS")
        logger.info("=" * 100)
        
        if overall_success:
            logger.info(f"✅ INTEGRATED VALIDATION PASSED")
            logger.info(f"🎯 Expert Standards: {'✅ MET' if expert_standards_met else '❌ NOT MET'}")
            logger.info(f"🏥 Production Health: {'✅ PASSED' if health_success else '❌ FAILED'}")
            logger.info(f"⚡ Total Validation Time: {total_time:.1f}s")
            logger.info(f"🚀 SYSTEM READY FOR PRODUCTION")
        else:
            logger.error(f"❌ INTEGRATED VALIDATION FAILED")
            logger.error(f"🎯 Expert Standards: {'✅ MET' if expert_standards_met else '❌ NOT MET'}")
            logger.error(f"🏥 Production Health: {'✅ PASSED' if health_success else '❌ FAILED'}")
            logger.error(f"🚫 SYSTEM NOT READY FOR PRODUCTION")
        
        # Save comprehensive report
        self._save_integrated_report(report)
        
        return overall_success, report
    
    def run_quick_validation(self) -> bool:
        """Run quick validation checks for rapid startup verification."""
        logger.info("⚡ Running Quick Validation...")
        
        try:
            # Use expert validator's quick health check
            return self.expert_validator.startup_health_check()
            
        except Exception as e:
            logger.error(f"Quick validation failed: {e}")
            return False
    
    def run_expert_validation_only(self) -> bool:
        """Run only expert validation (for critical startup verification)."""
        logger.info("🎯 Running Expert Validation Only...")
        return self.expert_validator.run_expert_startup_validation()
    
    def run_production_health_only(self) -> bool:
        """Run only production health validation (for monitoring)."""
        logger.info("🏥 Running Production Health Validation Only...")
        return self.health_validator.run_startup_validation()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status without running full validation."""
        try:
            status = {
                "timestamp": datetime.now().isoformat(),
                "model_available": False,
                "database_available": False,
                "indices_available": False,
                "quick_health": False
            }
            
            # Quick checks
            try:
                from core.model_loader import load_model_safe
                model = load_model_safe(device='cpu', require_exact_match=False)
                status["model_available"] = model is not None
            except:
                pass
            
            # Database check
            outcomes_dir = self.project_root / "outcomes"
            status["database_available"] = all(
                (outcomes_dir / f"outcomes_{h}h.npy").exists() 
                for h in [6, 12, 24, 48]
            )
            
            # Indices check
            indices_dir = self.project_root / "indices"
            status["indices_available"] = all(
                (indices_dir / f"faiss_{h}h_ivfpq.faiss").exists() 
                for h in [6, 12, 24, 48]
            )
            
            # Quick health
            status["quick_health"] = self.run_quick_validation()
            
            return status
            
        except Exception as e:
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def _save_integrated_report(self, report: IntegratedValidationReport):
        """Save comprehensive integrated validation report."""
        report_path = self.project_root / "integrated_validation_report.json"
        
        with open(report_path, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        
        logger.info(f"💾 Integrated validation report saved: {report_path}")

def main():
    """Main entry point for integrated validation."""
    framework = IntegratedValidationFramework()
    
    try:
        success, report = framework.run_complete_validation()
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.critical(f"💥 Integrated validation framework crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()