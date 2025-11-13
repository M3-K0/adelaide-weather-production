#!/usr/bin/env python3
"""
TEST2: Comprehensive Integration and Performance Test Suite Executor

Executes all TEST2 requirements:
1. E2E integration tests for /api/analogs and /forecast endpoints
2. Performance benchmarks (API p95 < 150ms, FAISS p95 < 1ms)  
3. Frontend analog explorer component tests
4. Zero fallback validation and data source verification
5. Distance monotonicity and memory usage monitoring
6. Comprehensive load testing with concurrent users
7. Final test execution report with performance metrics

Author: Performance Specialist
Version: 1.0.0 - TEST2 Implementation
"""

import os
import sys
import json
import time
import subprocess
import threading
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test2_execution.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TEST2ExecutionManager:
    def __init__(self):
        self.start_time = time.time()
        self.project_root = Path(__file__).parent
        self.test_results = {
            'test_suite': 'TEST2_COMPREHENSIVE',
            'execution_id': f"test2_{int(time.time())}",
            'start_time': datetime.datetime.now().isoformat(),
            'status': 'RUNNING',
            'results': {},
            'performance_metrics': {},
            'violations': [],
            'summary': {}
        }
        
        # TEST2 requirements
        self.performance_requirements = {
            'api_p95_ms': 150,
            'faiss_p95_ms': 1.0,
            'fallback_count': 0,
            'error_rate_max': 0.001,
            'concurrent_users_target': 50
        }
        
        # Test configuration
        self.api_url = os.environ.get('API_URL', 'http://localhost:8000')
        self.frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        self.api_token = os.environ.get('API_TOKEN', 'test-token-12345')
        
        # Ensure output directories exist
        self.setup_output_directories()
        
    def setup_output_directories(self):
        """Create necessary output directories"""
        directories = [
            'tests/e2e/reports',
            'tests/performance/reports',
            'test2_results'
        ]
        
        for dir_path in directories:
            full_path = self.project_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            
    def validate_environment(self) -> bool:
        """Validate test environment prerequisites"""
        logger.info("🔍 Validating TEST2 environment prerequisites...")
        
        # Check API availability
        try:
            result = subprocess.run([
                'curl', '-s', '-o', '/dev/null', '-w', '%{http_code}',
                f'{self.api_url}/health'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0 or result.stdout.strip() != '200':
                logger.error(f"❌ API not available at {self.api_url}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"❌ API health check timeout at {self.api_url}")
            return False
            
        # Check FAISS health specifically
        try:
            result = subprocess.run([
                'curl', '-s', f'{self.api_url}/health/faiss',
                '-H', f'Authorization: Bearer {self.api_token}'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                health_data = json.loads(result.stdout)
                if health_data.get('status') != 'healthy':
                    logger.error("❌ FAISS indices not healthy")
                    return False
            else:
                logger.error("❌ FAISS health check failed")
                return False
                
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            logger.error("❌ FAISS health check error")
            return False
        
        # Check required tools
        required_tools = ['npx', 'playwright', 'artillery']
        for tool in required_tools:
            if subprocess.run(['which', tool], capture_output=True).returncode != 0:
                logger.error(f"❌ Required tool not found: {tool}")
                return False
                
        logger.info("✅ Environment validation passed")
        return True

    def run_api_integration_tests(self) -> Dict[str, Any]:
        """Execute E2E API integration tests"""
        logger.info("🧪 Running API integration tests...")
        
        test_command = [
            'npx', 'playwright', 'test',
            'tests/e2e/specs/integration/test2-comprehensive-api-integration.spec.ts',
            '--reporter=json'
        ]
        
        env = os.environ.copy()
        env.update({
            'BASE_URL': self.api_url,
            'API_TOKEN': self.api_token,
            'CI': 'true'
        })
        
        start_time = time.time()
        result = subprocess.run(
            test_command,
            cwd=self.project_root,
            capture_output=True,
            text=True,
            env=env
        )
        
        duration = time.time() - start_time
        
        test_result = {
            'name': 'API Integration Tests',
            'status': 'PASSED' if result.returncode == 0 else 'FAILED',
            'duration_seconds': duration,
            'exit_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
        
        # Parse Playwright results if available
        try:
            if result.stdout:
                # Try to find JSON in stdout
                lines = result.stdout.split('\n')
                for line in lines:
                    if line.strip().startswith('{') and 'tests' in line:
                        playwright_results = json.loads(line.strip())
                        test_result['playwright_results'] = playwright_results
                        break
        except json.JSONDecodeError:
            logger.warning("Could not parse Playwright JSON results")
        
        logger.info(f"✅ API integration tests completed: {test_result['status']}")
        return test_result
        
    def run_frontend_integration_tests(self) -> Dict[str, Any]:
        """Execute frontend analog explorer integration tests"""
        logger.info("🎨 Running frontend integration tests...")
        
        test_command = [
            'npx', 'playwright', 'test',
            'tests/e2e/specs/integration/test2-frontend-analog-explorer.spec.ts',
            '--reporter=json'
        ]
        
        env = os.environ.copy()
        env.update({
            'BASE_URL': self.frontend_url,
            'NEXT_PUBLIC_API_URL': self.api_url,
            'API_TOKEN': self.api_token,
            'CI': 'true'
        })
        
        start_time = time.time()
        result = subprocess.run(
            test_command,
            cwd=self.project_root,
            capture_output=True,
            text=True,
            env=env
        )
        
        duration = time.time() - start_time
        
        test_result = {
            'name': 'Frontend Integration Tests',
            'status': 'PASSED' if result.returncode == 0 else 'FAILED',
            'duration_seconds': duration,
            'exit_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
        
        logger.info(f"✅ Frontend integration tests completed: {test_result['status']}")
        return test_result
        
    def run_load_performance_tests(self) -> Dict[str, Any]:
        """Execute comprehensive load and performance tests"""
        logger.info("⚡ Running load and performance tests...")
        
        test_command = [
            'npx', 'artillery', 'run',
            'tests/performance/load-tests/test2-comprehensive-load-test.yml',
            '--output', 'tests/performance/reports/test2-load-results.json'
        ]
        
        env = os.environ.copy()
        env.update({
            'API_TOKEN': self.api_token,
            'TARGET_URL': self.api_url
        })
        
        start_time = time.time()
        result = subprocess.run(
            test_command,
            cwd=self.project_root,
            capture_output=True,
            text=True,
            env=env
        )
        
        duration = time.time() - start_time
        
        test_result = {
            'name': 'Load Performance Tests',
            'status': 'PASSED' if result.returncode == 0 else 'FAILED',
            'duration_seconds': duration,
            'exit_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
        
        # Load Artillery results
        artillery_results_path = self.project_root / 'tests/performance/reports/test2-load-results.json'
        if artillery_results_path.exists():
            try:
                with open(artillery_results_path) as f:
                    test_result['artillery_results'] = json.load(f)
            except json.JSONDecodeError:
                logger.warning("Could not parse Artillery JSON results")
        
        # Load custom performance metrics
        custom_metrics_path = self.project_root / 'tests/performance/reports/test2-performance-metrics.json'
        if custom_metrics_path.exists():
            try:
                with open(custom_metrics_path) as f:
                    test_result['custom_metrics'] = json.load(f)
            except json.JSONDecodeError:
                logger.warning("Could not parse custom performance metrics")
        
        logger.info(f"✅ Load performance tests completed: {test_result['status']}")
        return test_result
        
    def analyze_performance_metrics(self) -> Dict[str, Any]:
        """Analyze and validate performance metrics against TEST2 requirements"""
        logger.info("📊 Analyzing performance metrics...")
        
        analysis = {
            'requirements_met': {},
            'violations': [],
            'summary': {},
            'recommendations': []
        }
        
        # Collect all performance data
        performance_data = {}
        
        # Load custom performance metrics
        custom_metrics_path = self.project_root / 'tests/performance/reports/test2-performance-metrics.json'
        if custom_metrics_path.exists():
            with open(custom_metrics_path) as f:
                performance_data['custom'] = json.load(f)
        
        # Load Artillery results
        artillery_results_path = self.project_root / 'tests/performance/reports/test2-load-results.json'
        if artillery_results_path.exists():
            with open(artillery_results_path) as f:
                performance_data['artillery'] = json.load(f)
        
        # Load real-time metrics
        realtime_metrics_path = self.project_root / 'tests/performance/reports/test2-realtime-metrics.json'
        if realtime_metrics_path.exists():
            with open(realtime_metrics_path) as f:
                performance_data['realtime'] = json.load(f)
        
        # Analyze TEST2 requirements
        if 'custom' in performance_data:
            custom = performance_data['custom']
            sla_compliance = custom.get('sla_compliance', {})
            
            # API p95 < 150ms
            api_req = sla_compliance.get('api_p95_requirement', {})
            analysis['requirements_met']['api_p95_under_150ms'] = {
                'requirement': 'API p95 < 150ms',
                'met': api_req.get('compliant', False),
                'actual_value': api_req.get('actual_ms', 0),
                'threshold': api_req.get('threshold_ms', 150),
                'violations': api_req.get('violations', 0)
            }
            
            if not api_req.get('compliant', False):
                analysis['violations'].append(
                    f"API p95 requirement violated: {api_req.get('actual_ms', 0):.2f}ms > 150ms"
                )
            
            # FAISS p95 < 1ms
            faiss_req = sla_compliance.get('faiss_p95_requirement', {})
            analysis['requirements_met']['faiss_p95_under_1ms'] = {
                'requirement': 'FAISS p95 < 1ms',
                'met': faiss_req.get('compliant', False),
                'actual_value': faiss_req.get('actual_ms', 0),
                'threshold': faiss_req.get('threshold_ms', 1.0),
                'violations': faiss_req.get('violations', 0)
            }
            
            if not faiss_req.get('compliant', False):
                analysis['violations'].append(
                    f"FAISS p95 requirement violated: {faiss_req.get('actual_ms', 0):.3f}ms > 1ms"
                )
            
            # Zero fallback requirement
            fallback_req = sla_compliance.get('zero_fallback_requirement', {})
            analysis['requirements_met']['zero_fallback_usage'] = {
                'requirement': 'Zero fallback usage',
                'met': fallback_req.get('compliant', False),
                'actual_value': fallback_req.get('actual', 0),
                'threshold': fallback_req.get('threshold', 0),
                'violations': fallback_req.get('violations', 0)
            }
            
            if not fallback_req.get('compliant', False):
                analysis['violations'].append(
                    f"Zero fallback requirement violated: {fallback_req.get('actual', 0)} fallbacks detected"
                )
            
            # Error rate requirement
            error_req = sla_compliance.get('error_rate_requirement', {})
            analysis['requirements_met']['error_rate_under_threshold'] = {
                'requirement': 'Error rate < 0.1%',
                'met': error_req.get('compliant', False),
                'actual_value': error_req.get('actual', 0),
                'threshold': error_req.get('threshold', 0.001),
                'violations': error_req.get('violations', 0)
            }
            
            if not error_req.get('compliant', False):
                analysis['violations'].append(
                    f"Error rate requirement violated: {error_req.get('actual', 0):.4f} > 0.001"
                )
        
        # Generate summary
        total_requirements = len(analysis['requirements_met'])
        met_requirements = sum(1 for req in analysis['requirements_met'].values() if req['met'])
        
        analysis['summary'] = {
            'total_requirements': total_requirements,
            'met_requirements': met_requirements,
            'compliance_percentage': (met_requirements / total_requirements * 100) if total_requirements > 0 else 0,
            'all_requirements_met': len(analysis['violations']) == 0,
            'total_violations': len(analysis['violations'])
        }
        
        # Generate recommendations
        if analysis['violations']:
            analysis['recommendations'].append(
                "Address all performance violations before deploying to production"
            )
            
        if analysis['summary']['compliance_percentage'] < 100:
            analysis['recommendations'].append(
                "Review system configuration and optimize performance bottlenecks"
            )
            
        logger.info(f"📈 Performance analysis completed: {analysis['summary']['compliance_percentage']:.1f}% compliant")
        return analysis
        
    def generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive final test report"""
        logger.info("📋 Generating final TEST2 execution report...")
        
        end_time = time.time()
        total_duration = end_time - self.start_time
        
        # Update test results with final data
        self.test_results.update({
            'end_time': datetime.datetime.now().isoformat(),
            'total_duration_seconds': total_duration,
            'status': 'COMPLETED'
        })
        
        # Add performance analysis
        performance_analysis = self.analyze_performance_metrics()
        self.test_results['performance_analysis'] = performance_analysis
        
        # Determine overall test status
        all_tests_passed = all(
            result.get('status') == 'PASSED' 
            for result in self.test_results['results'].values()
        )
        
        all_requirements_met = performance_analysis['summary']['all_requirements_met']
        
        self.test_results['overall_status'] = (
            'SUCCESS' if all_tests_passed and all_requirements_met else 'FAILURE'
        )
        
        # Add executive summary
        self.test_results['executive_summary'] = {
            'test_suite': 'TEST2 Comprehensive Integration and Performance Tests',
            'execution_date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_duration': f"{total_duration:.1f}s",
            'overall_result': self.test_results['overall_status'],
            'tests_executed': len(self.test_results['results']),
            'tests_passed': sum(1 for r in self.test_results['results'].values() if r.get('status') == 'PASSED'),
            'performance_compliance': f"{performance_analysis['summary']['compliance_percentage']:.1f}%",
            'requirements_met': f"{performance_analysis['summary']['met_requirements']}/{performance_analysis['summary']['total_requirements']}",
            'violations_detected': len(performance_analysis['violations']),
            'recommendations_count': len(performance_analysis['recommendations'])
        }
        
        # Write final report to file
        report_file = self.project_root / 'test2_results' / f"TEST2_FINAL_REPORT_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
            
        logger.info(f"📄 Final report written to: {report_file}")
        return self.test_results
        
    def print_summary(self):
        """Print test execution summary to console"""
        summary = self.test_results['executive_summary']
        
        print("\n" + "="*80)
        print("🏁 TEST2: COMPREHENSIVE INTEGRATION AND PERFORMANCE TEST RESULTS")
        print("="*80)
        print(f"📅 Execution Date: {summary['execution_date']}")
        print(f"⏱️  Total Duration: {summary['total_duration']}")
        print(f"📊 Overall Result: {summary['overall_result']}")
        print(f"🧪 Tests Executed: {summary['tests_executed']}")
        print(f"✅ Tests Passed: {summary['tests_passed']}")
        print(f"📈 Performance Compliance: {summary['performance_compliance']}")
        print(f"✔️  Requirements Met: {summary['requirements_met']}")
        print(f"⚠️  Violations Detected: {summary['violations_detected']}")
        print(f"💡 Recommendations: {summary['recommendations_count']}")
        
        if self.test_results['performance_analysis']['violations']:
            print("\n🚨 PERFORMANCE VIOLATIONS:")
            for violation in self.test_results['performance_analysis']['violations']:
                print(f"   • {violation}")
                
        if self.test_results['performance_analysis']['recommendations']:
            print("\n💡 RECOMMENDATIONS:")
            for rec in self.test_results['performance_analysis']['recommendations']:
                print(f"   • {rec}")
        
        print("\n" + "="*80)
        
        if summary['overall_result'] == 'SUCCESS':
            print("🎉 ALL TEST2 REQUIREMENTS SUCCESSFULLY VALIDATED! 🎉")
        else:
            print("❌ TEST2 REQUIREMENTS NOT MET - REVIEW VIOLATIONS ABOVE")
            
        print("="*80)
        
    def execute_test_suite(self) -> bool:
        """Execute complete TEST2 test suite"""
        logger.info("🚀 Starting TEST2 Comprehensive Integration and Performance Test Suite")
        
        try:
            # Validate environment
            if not self.validate_environment():
                logger.error("❌ Environment validation failed")
                return False
            
            # Execute test phases
            test_phases = [
                ('api_integration', self.run_api_integration_tests),
                ('frontend_integration', self.run_frontend_integration_tests),
                ('load_performance', self.run_load_performance_tests)
            ]
            
            for phase_name, phase_function in test_phases:
                logger.info(f"🔄 Executing phase: {phase_name}")
                result = phase_function()
                self.test_results['results'][phase_name] = result
                
                if result['status'] == 'FAILED':
                    logger.warning(f"⚠️  Phase {phase_name} failed but continuing with remaining tests")
            
            # Generate final report
            self.generate_final_report()
            
            # Print summary
            self.print_summary()
            
            return self.test_results['overall_status'] == 'SUCCESS'
            
        except Exception as e:
            logger.error(f"❌ Test suite execution failed: {str(e)}")
            return False

def main():
    """Main execution function"""
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("""
TEST2: Comprehensive Integration and Performance Test Suite

Usage: python run_test2_comprehensive_suite.py [options]

Environment Variables:
  API_URL          - API endpoint URL (default: http://localhost:8000)
  FRONTEND_URL     - Frontend URL (default: http://localhost:3000)  
  API_TOKEN        - API authentication token (default: test-token-12345)

Requirements Validated:
  • API response time p95 < 150ms
  • FAISS search time p95 < 1ms
  • Zero fallback usage in CI runs
  • Distance monotonicity in search results
  • Memory usage within acceptable limits
  • All responses use data_source='faiss'
  • Frontend analog explorer component integration
  • Concurrent user handling (50+ users)

Exit Codes:
  0 - All tests passed and requirements met
  1 - Tests failed or requirements not met
        """)
        return
        
    # Set up environment
    os.environ.setdefault('NODE_ENV', 'test')
    os.environ.setdefault('CI', 'true')
    
    # Execute test suite
    executor = TEST2ExecutionManager()
    success = executor.execute_test_suite()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()