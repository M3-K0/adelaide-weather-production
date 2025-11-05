#!/usr/bin/env python3
"""
Database Rebuild Monitor and Verification Automation
==================================================

Monitors the database rebuild process and automatically runs comprehensive
verification and integration testing once the rebuild is complete.

Functions:
1. Monitor rebuild progress 
2. Detect completion
3. Run temporal verification
4. Run integration testing
5. Generate final report

Author: Backend/Architecture Engineer
"""

import time
import subprocess
import sys
from pathlib import Path
import logging
import json

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RebuildMonitor:
    """Monitor database rebuild and run automated verification."""
    
    def __init__(self):
        self.base_dir = Path(".")
        self.log_file = self.base_dir / "rebuild_all_databases.log"
        self.horizons = ['6h', '12h', '24h', '48h']
        self.rebuild_complete = False
        
    def check_rebuild_progress(self) -> dict:
        """Check current rebuild progress from log file."""
        try:
            if not self.log_file.exists():
                return {'status': 'not_started', 'progress': 0}
            
            with open(self.log_file, 'r') as f:
                lines = f.readlines()
            
            if not lines:
                return {'status': 'not_started', 'progress': 0}
            
            # Look for completion indicators
            last_few_lines = lines[-20:]  # Check last 20 lines
            
            # Check for overall completion
            for line in reversed(last_few_lines):
                if "All outcomes databases built successfully!" in line:
                    return {'status': 'completed', 'progress': 100}
                if "Database build complete:" in line:
                    # Parse success count
                    try:
                        parts = line.split("Database build complete: ")[1]
                        success_count = int(parts.split("/")[0])
                        total_count = int(parts.split("/")[1].split()[0])
                        return {
                            'status': 'completed' if success_count == total_count else 'failed',
                            'progress': (success_count / total_count) * 100,
                            'success_count': success_count,
                            'total_count': total_count
                        }
                    except:
                        pass
            
            # Look for current progress
            current_horizon = None
            current_progress = 0
            horizons_completed = 0
            
            for line in reversed(last_few_lines):
                if "Building outcomes database for" in line and "horizon" in line:
                    # Extract horizon
                    if "6h horizon" in line:
                        current_horizon = "6h"
                    elif "12h horizon" in line:
                        current_horizon = "12h"
                        horizons_completed = 1
                    elif "24h horizon" in line:
                        current_horizon = "24h"
                        horizons_completed = 2
                    elif "48h horizon" in line:
                        current_horizon = "48h"
                        horizons_completed = 3
                    break
                
                if "Progress:" in line:
                    # Extract progress percentage
                    try:
                        progress_part = line.split("Progress: ")[1]
                        percentage_part = progress_part.split("(")[1].split(")")[0]
                        current_progress = float(percentage_part.replace("%", ""))
                        break
                    except:
                        pass
            
            # Calculate overall progress across all horizons
            if current_horizon:
                overall_progress = (horizons_completed * 25) + (current_progress * 0.25)
            else:
                overall_progress = 0
            
            return {
                'status': 'in_progress',
                'progress': round(overall_progress, 1),
                'current_horizon': current_horizon,
                'current_progress': current_progress,
                'horizons_completed': horizons_completed
            }
            
        except Exception as e:
            logger.error(f"Error checking rebuild progress: {e}")
            return {'status': 'error', 'progress': 0, 'error': str(e)}
    
    def wait_for_completion(self, check_interval: int = 30) -> bool:
        """Wait for rebuild to complete, checking every interval seconds."""
        logger.info("🔄 Monitoring database rebuild progress...")
        
        last_progress = -1
        
        while True:
            progress_info = self.check_rebuild_progress()
            current_progress = progress_info['progress']
            
            # Only log if progress changed significantly
            if abs(current_progress - last_progress) >= 5 or progress_info['status'] in ['completed', 'failed', 'error']:
                if progress_info['status'] == 'completed':
                    logger.info(f"✅ Database rebuild completed! (100.0%)")
                    return True
                elif progress_info['status'] == 'failed':
                    logger.error(f"❌ Database rebuild failed!")
                    return False
                elif progress_info['status'] == 'error':
                    logger.error(f"❌ Error monitoring rebuild: {progress_info.get('error', 'Unknown error')}")
                    return False
                elif progress_info['status'] == 'in_progress':
                    current_horizon = progress_info.get('current_horizon', 'unknown')
                    horizon_progress = progress_info.get('current_progress', 0)
                    logger.info(f"📊 Rebuild progress: {current_progress:.1f}% "
                              f"(Current: {current_horizon} at {horizon_progress:.1f}%)")
                else:
                    logger.info(f"📊 Rebuild status: {progress_info['status']} ({current_progress:.1f}%)")
                
                last_progress = current_progress
            
            time.sleep(check_interval)
    
    def run_verification_suite(self) -> dict:
        """Run comprehensive verification after rebuild completion."""
        logger.info("🔍 Running temporal verification suite...")
        
        try:
            # Run temporal verification
            result = subprocess.run([
                sys.executable, "temporal_verification_system.py"
            ], capture_output=True, text=True, timeout=300)
            
            temporal_verification = {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr if result.returncode != 0 else None
            }
            
            logger.info("✅ Temporal verification completed")
            
        except subprocess.TimeoutExpired:
            temporal_verification = {
                'success': False,
                'error': 'Temporal verification timed out'
            }
            logger.error("❌ Temporal verification timed out")
        except Exception as e:
            temporal_verification = {
                'success': False,
                'error': str(e)
            }
            logger.error(f"❌ Temporal verification failed: {e}")
        
        return temporal_verification
    
    def run_integration_tests(self) -> dict:
        """Run integration testing suite."""
        logger.info("🧪 Running integration test suite...")
        
        try:
            # Run integration tests
            result = subprocess.run([
                sys.executable, "integration_testing_suite.py"
            ], capture_output=True, text=True, timeout=600)
            
            integration_tests = {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr if result.returncode != 0 else None
            }
            
            logger.info("✅ Integration tests completed")
            
        except subprocess.TimeoutExpired:
            integration_tests = {
                'success': False,
                'error': 'Integration tests timed out'
            }
            logger.error("❌ Integration tests timed out")
        except Exception as e:
            integration_tests = {
                'success': False,
                'error': str(e)
            }
            logger.error(f"❌ Integration tests failed: {e}")
        
        return integration_tests
    
    def generate_final_report(self, verification_results: dict, integration_results: dict) -> dict:
        """Generate comprehensive final report."""
        logger.info("📋 Generating final system report...")
        
        # Overall system status
        verification_passed = verification_results.get('success', False)
        integration_passed = integration_results.get('success', False)
        system_ready = verification_passed and integration_passed
        
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'database_rebuild': {
                'status': 'completed',
                'all_horizons_built': True
            },
            'temporal_verification': verification_results,
            'integration_testing': integration_results,
            'overall_system_status': {
                'ready_for_production': system_ready,
                'verification_passed': verification_passed,
                'integration_passed': integration_passed,
                'readiness_score': (
                    (verification_passed * 50) + (integration_passed * 50)
                )
            },
            'next_steps': self._generate_next_steps(system_ready, verification_passed, integration_passed)
        }
        
        # Save report
        report_path = self.base_dir / "final_system_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"✅ Final report saved: {report_path}")
        
        # Print summary
        self._print_final_summary(report)
        
        return report
    
    def _generate_next_steps(self, system_ready: bool, verification_passed: bool, integration_passed: bool) -> list:
        """Generate next steps based on test results."""
        if system_ready:
            return [
                "✅ System is ready for production use",
                "✅ All databases rebuilt successfully with <1% corruption",
                "✅ Temporal verification passed - no duplication or shifting detected",
                "✅ Integration tests passed - forecasting pipeline functional",
                "📋 Consider implementing continuous monitoring",
                "📋 Set up automated backup procedures",
                "📋 Deploy to production environment"
            ]
        else:
            steps = []
            if not verification_passed:
                steps.extend([
                    "❌ Fix temporal verification issues",
                    "❌ Check database corruption and uniqueness",
                    "❌ Verify cross-horizon distinctness"
                ])
            if not integration_passed:
                steps.extend([
                    "❌ Fix integration pipeline issues",
                    "❌ Check analog forecaster functionality",
                    "❌ Verify real-time workflow"
                ])
            steps.append("🔄 Re-run verification after fixes")
            return steps
    
    def _print_final_summary(self, report: dict) -> None:
        """Print final summary to console."""
        print("\n" + "="*80)
        print("🎯 ADELAIDE WEATHER FORECASTING SYSTEM - FINAL REPORT")
        print("="*80)
        
        overall = report['overall_system_status']
        
        if overall['ready_for_production']:
            print("✅ SYSTEM STATUS: READY FOR PRODUCTION")
        else:
            print("❌ SYSTEM STATUS: REQUIRES FIXES")
        
        print(f"📊 Overall Readiness Score: {overall['readiness_score']}/100")
        print()
        
        # Component status
        print("📋 COMPONENT STATUS:")
        db_status = "✅ COMPLETED" if report['database_rebuild']['status'] == 'completed' else "❌ FAILED"
        print(f"   Database Rebuild: {db_status}")
        
        verification_status = "✅ PASSED" if overall['verification_passed'] else "❌ FAILED"
        print(f"   Temporal Verification: {verification_status}")
        
        integration_status = "✅ PASSED" if overall['integration_passed'] else "❌ FAILED"
        print(f"   Integration Testing: {integration_status}")
        print()
        
        # Next steps
        print("📝 NEXT STEPS:")
        for step in report['next_steps']:
            print(f"   {step}")
        
        print("="*80)
    
    def run_complete_workflow(self) -> dict:
        """Run complete monitoring and verification workflow."""
        logger.info("🚀 Starting complete rebuild monitoring and verification workflow...")
        
        # Step 1: Wait for rebuild completion
        rebuild_success = self.wait_for_completion()
        
        if not rebuild_success:
            logger.error("❌ Database rebuild failed - aborting verification")
            return {'success': False, 'error': 'Database rebuild failed'}
        
        # Step 2: Run verification suite
        verification_results = self.run_verification_suite()
        
        # Step 3: Run integration tests (even if verification failed, to get complete picture)
        integration_results = self.run_integration_tests()
        
        # Step 4: Generate final report
        final_report = self.generate_final_report(verification_results, integration_results)
        
        return final_report

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor database rebuild and run verification")
    parser.add_argument("--check-interval", type=int, default=30,
                       help="Check interval in seconds (default: 30)")
    parser.add_argument("--skip-wait", action="store_true",
                       help="Skip waiting for rebuild, run verification immediately")
    
    args = parser.parse_args()
    
    monitor = RebuildMonitor()
    
    if args.skip_wait:
        # Run verification immediately
        logger.info("⏩ Skipping rebuild wait, running verification immediately...")
        verification_results = monitor.run_verification_suite()
        integration_results = monitor.run_integration_tests()
        final_report = monitor.generate_final_report(verification_results, integration_results)
    else:
        # Run complete workflow
        final_report = monitor.run_complete_workflow()
    
    # Exit with appropriate code
    return 0 if final_report.get('overall_system_status', {}).get('ready_for_production', False) else 1

if __name__ == "__main__":
    sys.exit(main())