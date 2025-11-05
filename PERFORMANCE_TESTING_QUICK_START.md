# FAISS Health Monitoring Performance Testing - Quick Start Guide

## 🚀 Quick Start (5 Minutes)

### Step 1: Validate Setup
```bash
# Check if everything is ready
python3 validate_performance_test_setup.py
```

### Step 2: Run Comprehensive Tests
```bash
# Run the full performance test suite
python3 run_comprehensive_performance_tests.py
```

### Step 3: View Results
```bash
# Check test results
ls performance_test_results/
cat performance_test_results/performance_test_summary.txt
```

## 📋 Prerequisites Checklist

- [ ] Python 3.8+ installed
- [ ] Required packages: `numpy pandas fastapi prometheus_client`
- [ ] Optional packages: `psutil aiohttp memory-profiler` (for full testing)
- [ ] Adelaide Weather API running (for API tests)
- [ ] Minimum 2GB RAM, 1GB disk space

## 🧪 Individual Test Components

### FAISS Monitoring Performance Only
```bash
python3 test_faiss_monitoring_performance.py
```

### API Integration Performance Only
```bash
export API_TOKEN="your-token"
export API_BASE_URL="http://localhost:8000"
python3 api_performance_integration_test.py
```

### Demo/Example
```bash
python3 examples/run_performance_tests_demo.py
```

## 📊 Expected Results

✅ **Pass Criteria:**
- Monitoring overhead: <0.1ms per query
- Health endpoint: <50ms response time
- Concurrent queries: >100 successful
- Memory stable: <10MB growth
- Background CPU: <5% usage

## 🔧 Troubleshooting

### Missing Dependencies
```bash
# Install with pip (if allowed)
pip install psutil aiohttp memory-profiler

# Or use system packages
sudo apt-get install python3-psutil python3-aiohttp
```

### API Not Running
```bash
# Start the Adelaide Weather API
cd api/
python3 main.py
```

### Permission Issues
```bash
# Run with appropriate permissions
sudo python3 run_comprehensive_performance_tests.py
```

## 📈 Performance Requirements

| Metric | Requirement | Test |
|--------|-------------|------|
| Monitoring overhead | <0.1ms | Latency comparison |
| Health endpoint latency | <50ms | Endpoint testing |
| Concurrent queries | >100 | Concurrency testing |
| Memory stability | No leaks | Extended monitoring |
| Background CPU | <5% | Resource monitoring |
| API success rate | >95% | Integration testing |

## 📁 Output Files

After running tests, check these files:

```
performance_test_results/
├── comprehensive_performance_report.json    # Detailed technical results
├── performance_test_summary.txt            # Human-readable summary
├── faiss_monitoring_performance_report.json # FAISS-specific metrics
├── api_performance_integration_report.json  # API-specific metrics
├── monitoring_tests_output.log             # Raw test output
└── api_tests_output.log                    # API test output
```

## 🎯 Quick Commands Reference

```bash
# Full validation and testing (recommended)
python3 validate_performance_test_setup.py && python3 run_comprehensive_performance_tests.py

# Monitor-only testing
python3 test_faiss_monitoring_performance.py

# API-only testing (requires running API)
API_TOKEN=test python3 api_performance_integration_test.py

# View latest results
cat performance_test_results/performance_test_summary.txt

# Check if setup is ready
python3 validate_performance_test_setup.py | grep "Overall Status"
```

## ⚡ Performance Testing in CI/CD

```yaml
# GitHub Actions example
- name: Validate Performance Setup
  run: python3 validate_performance_test_setup.py

- name: Run Performance Tests
  run: python3 run_comprehensive_performance_tests.py
  
- name: Check Results
  run: |
    if grep -q "ALL CRITICAL PERFORMANCE REQUIREMENTS MET" performance_test_results/performance_test_summary.txt; then
      echo "✅ Performance tests passed"
    else
      echo "❌ Performance tests failed"
      exit 1
    fi
```

## 🔍 Test Customization

```python
# Customize test parameters in scripts
test_suite = PerformanceTestSuite(
    test_duration_seconds=120,      # Longer testing
    max_concurrent_requests=200,    # Higher concurrency
    api_base_url="https://your-api.com",
    output_dir="custom_results"
)
```

## 📞 Getting Help

### Common Issues

| Problem | Solution |
|---------|----------|
| `python: command not found` | Use `python3` instead |
| Missing packages | Install with pip or system package manager |
| API connection failed | Check API is running on localhost:8000 |
| Permission denied | Use sudo or check file permissions |
| Out of memory | Ensure 2GB+ RAM available |

### Debug Mode
```bash
# Run with verbose output
python3 -v run_comprehensive_performance_tests.py

# Check individual component
python3 -c "from api.services.faiss_health_monitoring import FAISSHealthMonitor; print('OK')"
```

## 🎉 Success Indicators

When tests complete successfully, you should see:
- ✅ All 9 core performance tests pass
- ✅ "ALL CRITICAL PERFORMANCE REQUIREMENTS MET"
- ✅ Performance report files generated
- ✅ No critical errors in output logs

Ready for production deployment! 🚀