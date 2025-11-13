#!/usr/bin/env python3
"""
Test Execution Summary Generator
==============================

Creates comprehensive test execution summaries and CI-ready artifacts.
"""

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
import os

class TestExecutionSummary:
    """Generate comprehensive test execution summaries"""
    
    def __init__(self):
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.base_path = Path(__file__).parent
        
    def analyze_junit_xml(self, junit_file: str = "junit.xml") -> dict:
        """Analyze JUnit XML results"""
        print(f"📋 Analyzing JUnit XML: {junit_file}")
        
        if not os.path.exists(junit_file):
            return {
                "error": f"JUnit XML file not found: {junit_file}",
                "status": "missing"
            }
        
        try:
            tree = ET.parse(junit_file)
            root = tree.getroot()
            
            # Extract test statistics
            total_tests = int(root.get('tests', 0))
            failures = int(root.get('failures', 0))
            errors = int(root.get('errors', 0))
            skipped = int(root.get('skipped', 0))
            time_taken = float(root.get('time', 0))
            
            passed = total_tests - failures - errors - skipped
            
            # Analyze individual test cases
            test_cases = []
            for testcase in root.findall('.//testcase'):
                case_info = {
                    "name": testcase.get('name'),
                    "classname": testcase.get('classname'),
                    "time": float(testcase.get('time', 0)),
                    "status": "passed"
                }
                
                # Check for failures or errors
                if testcase.find('failure') is not None:
                    case_info["status"] = "failed"
                    case_info["failure_message"] = testcase.find('failure').text
                elif testcase.find('error') is not None:
                    case_info["status"] = "error"
                    case_info["error_message"] = testcase.find('error').text
                elif testcase.find('skipped') is not None:
                    case_info["status"] = "skipped"
                
                test_cases.append(case_info)
            
            return {
                "status": "success",
                "summary": {
                    "total": total_tests,
                    "passed": passed,
                    "failed": failures,
                    "errors": errors,
                    "skipped": skipped,
                    "success_rate": (passed / total_tests * 100) if total_tests > 0 else 0,
                    "total_time": time_taken
                },
                "test_cases": test_cases
            }
            
        except Exception as e:
            return {
                "error": f"Failed to parse JUnit XML: {str(e)}",
                "status": "parse_error"
            }
    
    def analyze_coverage_xml(self, coverage_file: str = "coverage.xml") -> dict:
        """Analyze coverage XML results"""
        print(f"📊 Analyzing Coverage XML: {coverage_file}")
        
        if not os.path.exists(coverage_file):
            return {
                "error": f"Coverage XML file not found: {coverage_file}",
                "status": "missing"
            }
        
        try:
            tree = ET.parse(coverage_file)
            root = tree.getroot()
            
            # Extract coverage statistics
            line_rate = float(root.get('line-rate', 0))
            branch_rate = float(root.get('branch-rate', 0))
            lines_covered = int(root.get('lines-covered', 0))
            lines_valid = int(root.get('lines-valid', 0))
            
            # Package-level coverage
            packages = []
            for package in root.findall('.//package'):
                pkg_info = {
                    "name": package.get('name'),
                    "line_rate": float(package.get('line-rate', 0)),
                    "branch_rate": float(package.get('branch-rate', 0)),
                    "classes": len(package.findall('.//class'))
                }
                packages.append(pkg_info)
            
            return {
                "status": "success",
                "summary": {
                    "line_coverage_percent": line_rate * 100,
                    "branch_coverage_percent": branch_rate * 100,
                    "lines_covered": lines_covered,
                    "lines_valid": lines_valid,
                    "coverage_threshold": 90,  # From pytest.ini
                    "threshold_met": line_rate * 100 >= 90
                },
                "packages": packages
            }
            
        except Exception as e:
            return {
                "error": f"Failed to parse coverage XML: {str(e)}",
                "status": "parse_error"
            }
    
    def analyze_performance_reports(self) -> dict:
        """Analyze performance benchmark reports"""
        print("⚡ Analyzing Performance Reports...")
        
        performance_files = [
            "performance_benchmark_report.json",
            "T006_REAL_PERFORMANCE_METRICS.json",
            "performance_metrics.json"
        ]
        
        reports = {}
        
        for file_name in performance_files:
            if os.path.exists(file_name):
                try:
                    with open(file_name, 'r') as f:
                        data = json.load(f)
                    reports[file_name] = {
                        "status": "success",
                        "data": data
                    }
                except Exception as e:
                    reports[file_name] = {
                        "status": "error",
                        "error": str(e)
                    }
            else:
                reports[file_name] = {
                    "status": "missing"
                }
        
        return reports
    
    def generate_ci_summary(self) -> dict:
        """Generate CI-ready summary"""
        print("🔄 Generating CI Integration Summary...")
        
        junit_analysis = self.analyze_junit_xml()
        coverage_analysis = self.analyze_coverage_xml()
        performance_analysis = self.analyze_performance_reports()
        
        # Determine overall status
        overall_status = "success"
        issues = []
        
        # Check test results
        if junit_analysis.get("status") != "success":
            overall_status = "failed"
            issues.append("Test execution failed or missing")
        elif junit_analysis.get("summary", {}).get("failed", 0) > 0:
            overall_status = "failed"
            issues.append(f"Tests failed: {junit_analysis['summary']['failed']}")
        elif junit_analysis.get("summary", {}).get("errors", 0) > 0:
            overall_status = "failed"
            issues.append(f"Test errors: {junit_analysis['summary']['errors']}")
        
        # Check coverage threshold
        if coverage_analysis.get("status") == "success":
            coverage_percent = coverage_analysis["summary"]["line_coverage_percent"]
            threshold_met = coverage_analysis["summary"]["threshold_met"]
            
            if not threshold_met:
                overall_status = "failed"
                issues.append(f"Coverage below threshold: {coverage_percent:.1f}% < 90%")
        else:
            overall_status = "failed"
            issues.append("Coverage analysis failed or missing")
        
        # Performance checks
        performance_status = "unknown"
        if any(report["status"] == "success" for report in performance_analysis.values()):
            performance_status = "available"
        
        return {
            "timestamp": self.timestamp,
            "overall_status": overall_status,
            "issues": issues,
            "test_results": junit_analysis,
            "coverage_results": coverage_analysis,
            "performance_results": performance_analysis,
            "performance_status": performance_status,
            "artifacts_generated": {
                "junit_xml": os.path.exists("junit.xml"),
                "coverage_xml": os.path.exists("coverage.xml"),
                "coverage_html": os.path.exists("htmlcov/index.html"),
                "performance_json": any(os.path.exists(f) for f in [
                    "performance_benchmark_report.json",
                    "T006_REAL_PERFORMANCE_METRICS.json"
                ])
            }
        }
    
    def save_summary(self, filename: str = "test_execution_summary.json"):
        """Save the test execution summary"""
        summary = self.generate_ci_summary()
        
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"📄 Test execution summary saved to {filename}")
        return summary
    
    def print_summary(self, summary: dict):
        """Print a formatted summary to console"""
        print("\n" + "="*60)
        print("🧪 TEST EXECUTION SUMMARY")
        print("="*60)
        
        print(f"📅 Timestamp: {summary['timestamp']}")
        print(f"🎯 Overall Status: {summary['overall_status'].upper()}")
        
        if summary['issues']:
            print(f"\n❌ Issues Found:")
            for i, issue in enumerate(summary['issues'], 1):
                print(f"  {i}. {issue}")
        else:
            print("\n✅ No issues found")
        
        # Test Results
        if summary['test_results']['status'] == 'success':
            test_summary = summary['test_results']['summary']
            print(f"\n📋 Test Results:")
            print(f"  • Total Tests: {test_summary['total']}")
            print(f"  • Passed: {test_summary['passed']}")
            print(f"  • Failed: {test_summary['failed']}")
            print(f"  • Errors: {test_summary['errors']}")
            print(f"  • Skipped: {test_summary['skipped']}")
            print(f"  • Success Rate: {test_summary['success_rate']:.1f}%")
            print(f"  • Total Time: {test_summary['total_time']:.2f}s")
        
        # Coverage Results
        if summary['coverage_results']['status'] == 'success':
            cov_summary = summary['coverage_results']['summary']
            print(f"\n📊 Coverage Results:")
            print(f"  • Line Coverage: {cov_summary['line_coverage_percent']:.1f}%")
            print(f"  • Branch Coverage: {cov_summary['branch_coverage_percent']:.1f}%")
            print(f"  • Lines Covered: {cov_summary['lines_covered']}")
            print(f"  • Total Lines: {cov_summary['lines_valid']}")
            print(f"  • Threshold (90%): {'✅ MET' if cov_summary['threshold_met'] else '❌ NOT MET'}")
        
        # Performance Status
        print(f"\n⚡ Performance Reports: {summary['performance_status'].upper()}")
        
        # Artifacts
        print(f"\n📁 Artifacts Generated:")
        for artifact, exists in summary['artifacts_generated'].items():
            status = "✅" if exists else "❌"
            print(f"  • {artifact}: {status}")
        
        print("="*60)

def main():
    """Main function to generate test execution summary"""
    print("🧪 Generating Test Execution Summary")
    print("="*50)
    
    summary_generator = TestExecutionSummary()
    
    # Generate and save summary
    summary = summary_generator.save_summary()
    
    # Print formatted summary
    summary_generator.print_summary(summary)
    
    # Also save with timestamp for historical tracking
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_generator.save_summary(f"test_execution_summary_{timestamp}.json")
    
    print(f"\n✅ Test execution summary completed!")
    
    # Return exit code based on overall status
    return 0 if summary['overall_status'] == 'success' else 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)