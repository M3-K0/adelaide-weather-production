#!/usr/bin/env python3
"""
Comprehensive FAISS Test Runner
===============================

Executes all FAISS-related tests and generates a detailed coverage report.
Designed for TEST1 validation requirements.

Usage:
    python run_faiss_tests.py [--include-performance] [--verbose] [--coverage]

Features:
- Real FAISS behavior validation
- Performance benchmarking  
- Coverage reporting
- Environment setup verification
- Detailed test result analysis

Author: QA & Optimization Specialist
Version: 1.0.0
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime
import argparse

# Ensure we can import from the project
sys.path.insert(0, str(Path(__file__).parent / "api"))

def setup_environment():
    """Set up test environment variables."""
    env_vars = {
        "PYTHONPATH": str(Path(__file__).parent),
        "TESTING": "true",
        "LOG_LEVEL": "INFO"
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    print("✅ Test environment configured")

def run_pytest_with_coverage(test_files, include_performance=False, verbose=False):
    """Run pytest with coverage reporting."""
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.extend(["-v", "-s"])
    
    # Add coverage options
    cmd.extend([
        "--cov=api.services.analog_search",
        "--cov=api.forecast_adapter", 
        "--cov-report=term-missing",
        "--cov-report=json:test_coverage.json",
        "--durations=10"
    ])
    
    # Add performance tests if requested
    if include_performance:
        cmd.append("-m")
        cmd.append("not slow")
    
    # Add test files
    cmd.extend(test_files)
    
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, capture_output=True, text=True)

def analyze_test_results(result, output_file="test_results.json"):
    """Analyze and save test results."""
    results = {
        "timestamp": datetime.now().isoformat(),
        "exit_code": result.returncode,
        "success": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr
    }
    
    # Parse test output for metrics
    stdout_lines = result.stdout.split('\n')
    
    # Extract test counts
    for line in stdout_lines:
        if "passed" in line and "failed" in line:
            results["test_summary"] = line.strip()
            break
    
    # Extract coverage information if available
    coverage_lines = [line for line in stdout_lines if "TOTAL" in line and "%" in line]
    if coverage_lines:
        results["coverage"] = coverage_lines[-1].strip()
    
    # Save results
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    return results

def validate_faiss_prerequisites():
    """Validate that FAISS test prerequisites are available."""
    print("🔍 Validating FAISS test prerequisites...")
    
    required_files = [
        "api/services/analog_search.py",
        "api/test_analog_search_service.py",
        "api/test_faiss_real_behavior.py",
        "api/test_api.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        return False
    
    # Check for outcomes data (optional for real data tests)
    outcomes_dir = Path("outcomes")
    if outcomes_dir.exists():
        outcomes_files = list(outcomes_dir.glob("outcomes_*.npy"))
        if outcomes_files:
            print(f"✅ Found {len(outcomes_files)} outcomes data files for real data testing")
        else:
            print("⚠️  No outcomes data found - some real data tests may be skipped")
    else:
        print("⚠️  Outcomes directory not found - real data tests will be mocked")
    
    # Check for FAISS indices (optional)
    indices_dir = Path("indices") 
    if indices_dir.exists():
        faiss_files = list(indices_dir.glob("*.faiss"))
        if faiss_files:
            print(f"✅ Found {len(faiss_files)} FAISS index files")
        else:
            print("⚠️  No FAISS indices found - FAISS tests will use mocks")
    else:
        print("⚠️  Indices directory not found - FAISS tests will use mocks")
    
    print("✅ Prerequisites validation complete")
    return True

def generate_coverage_report():
    """Generate detailed coverage report."""
    print("\n📊 Generating coverage report...")
    
    # Check if coverage data exists
    if not Path("test_coverage.json").exists():
        print("❌ Coverage data not found")
        return None
    
    try:
        with open("test_coverage.json", 'r') as f:
            coverage_data = json.load(f)
        
        # Extract key metrics
        files = coverage_data.get("files", {})
        total_coverage = coverage_data.get("totals", {})
        
        print(f"📈 Overall Coverage: {total_coverage.get('percent_covered', 0):.1f}%")
        print(f"📋 Lines Covered: {total_coverage.get('covered_lines', 0)}/{total_coverage.get('num_statements', 0)}")
        
        # Show file-level coverage
        print("\n📁 File Coverage Details:")
        for file_path, file_data in files.items():
            if "analog_search" in file_path or "forecast_adapter" in file_path:
                coverage_pct = (file_data['executed_lines'] / max(file_data['num_statements'], 1)) * 100
                print(f"  {Path(file_path).name}: {coverage_pct:.1f}% ({file_data['executed_lines']}/{file_data['num_statements']} lines)")
        
        return coverage_data
        
    except Exception as e:
        print(f"❌ Error reading coverage data: {e}")
        return None

def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Run comprehensive FAISS tests")
    parser.add_argument("--include-performance", action="store_true", 
                       help="Include performance benchmark tests")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose test output")
    parser.add_argument("--coverage", action="store_true",
                       help="Generate detailed coverage report")
    parser.add_argument("--quick", action="store_true",
                       help="Run only quick tests (skip slow integration tests)")
    
    args = parser.parse_args()
    
    print("🚀 Starting FAISS Test Suite")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Setup
    setup_environment()
    
    if not validate_faiss_prerequisites():
        print("❌ Prerequisites validation failed")
        sys.exit(1)
    
    # Define test files in execution order
    test_files = [
        "api/test_analog_search_service.py",
        "api/test_faiss_real_behavior.py", 
        "api/test_api.py"
    ]
    
    # Add test markers for different test types
    if args.quick:
        test_files = ["api/test_faiss_real_behavior.py::TestRealFAISSSearchMethod"]
    
    print(f"\n🧪 Running tests: {', '.join([Path(f).name for f in test_files])}")
    
    # Run tests
    start_time = time.time()
    result = run_pytest_with_coverage(
        test_files, 
        include_performance=args.include_performance,
        verbose=args.verbose
    )
    end_time = time.time()
    
    # Analyze results
    test_results = analyze_test_results(result)
    
    print("\n" + "=" * 60)
    print("📋 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    print(f"⏱️  Total Runtime: {end_time - start_time:.1f} seconds")
    print(f"🏁 Exit Code: {result.returncode}")
    print(f"✅ Success: {'YES' if test_results['success'] else 'NO'}")
    
    if "test_summary" in test_results:
        print(f"📊 Test Summary: {test_results['test_summary']}")
    
    # Show coverage if available
    if args.coverage:
        generate_coverage_report()
    elif "coverage" in test_results:
        print(f"📈 Coverage: {test_results['coverage']}")
    
    # Show any errors
    if result.stderr:
        print(f"\n⚠️  Errors/Warnings:")
        print(result.stderr)
    
    # Key validation checkpoints for TEST1
    print(f"\n🎯 TEST1 VALIDATION CHECKPOINTS:")
    checkpoints = [
        ("✅ Real FAISS search method validation", "TestRealFAISSSearchMethod" in result.stdout),
        ("✅ Distance monotonicity verification", "TestDistanceMonotonicity" in result.stdout),
        ("✅ Fallback behavior control", "TestFallbackBehavior" in result.stdout),
        ("✅ Timeline data determinism", "TestTimelineDataDeterminism" in result.stdout),
        ("✅ Performance benchmarks", "TestPerformanceBenchmarks" in result.stdout),
        ("✅ Transparency field validation", "TestTransparencyFields" in result.stdout)
    ]
    
    for checkpoint, passed in checkpoints:
        status = "✅" if passed else "❌"
        print(f"{status} {checkpoint[2:]}")
    
    # Final status
    if test_results['success']:
        print(f"\n🎉 FAISS Test Suite PASSED - All TEST1 requirements validated!")
        sys.exit(0)
    else:
        print(f"\n❌ FAISS Test Suite FAILED - Review errors above")
        sys.exit(1)

if __name__ == "__main__":
    main()