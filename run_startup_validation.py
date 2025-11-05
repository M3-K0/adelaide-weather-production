#!/usr/bin/env python3
"""
Expert Startup Validation Runner
================================

Runs the expert-validated startup validation system for the Adelaide Weather 
Forecasting System. This script implements Phase 3: System Hardening requirements
with zero tolerance for silent failures.

Usage:
    python run_startup_validation.py

Exit Codes:
    0: All validations passed
    1: Critical failures detected
    2: Expert threshold violations
    3: System crash

Author: QA-Optimization Specialist
Version: 3.0.0 - Expert Startup Validation
"""

import sys
import logging
import traceback
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.startup_validation_system import ExpertValidatedStartupSystem

def setup_logging():
    """Setup enhanced logging for startup validation."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(project_root / 'startup_validation.log')
        ]
    )
    
    # Suppress noisy libraries
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)

def main():
    """Main entry point for startup validation."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 ADELAIDE WEATHER FORECASTING SYSTEM")
    logger.info("📋 Expert-Validated Startup Validation v3.0.0")
    logger.info("🎯 Phase 3: System Hardening Implementation")
    logger.info("=" * 80)
    
    try:
        # Initialize expert validation system
        validator = ExpertValidatedStartupSystem(project_root=project_root)
        
        # Run comprehensive validation
        logger.info("Starting expert-validated startup validation...")
        success = validator.run_expert_startup_validation()
        
        if success:
            logger.info("\n🎉 STARTUP VALIDATION SUCCESSFUL")
            logger.info("✅ All expert thresholds met")
            logger.info("🚀 System certified for production operation")
            logger.info("📊 Validation report saved to: expert_startup_validation_report.json")
            return 0
        else:
            # Check for specific failure types
            critical_failures = [r for r in validator.validation_results if r.is_critical_failure()]
            expert_violations = [r for r in validator.validation_results if not r.expert_threshold_met]
            
            if critical_failures:
                logger.critical("\n🚨 CRITICAL STARTUP FAILURES DETECTED")
                logger.critical("❌ System startup blocked")
                logger.critical("🔧 Resolve critical issues before proceeding")
                return 1
            elif expert_violations:
                logger.error("\n⚠️ EXPERT THRESHOLD VIOLATIONS")
                logger.error("❌ System fails expert standards")
                logger.error("🎯 Deployment not recommended")
                return 2
            else:
                logger.error("\n❌ STARTUP VALIDATION FAILED")
                logger.error("🔍 Check validation logs for details")
                return 1
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Validation interrupted by user")
        return 3
        
    except Exception as e:
        logger.critical(f"\n💥 STARTUP VALIDATION CRASHED: {e}")
        logger.critical("📝 Full traceback:")
        traceback.print_exc()
        return 3

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)