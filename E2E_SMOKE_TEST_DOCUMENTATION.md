# Adelaide Weather E2E Smoke Test Suite
## T-009 E2E Smoke Test (Critical Path) - COMPLETE ✅

### Overview

This comprehensive smoke test suite validates the entire critical path of the Adelaide Weather Forecasting System, ensuring that all components work together correctly before deployment. The test suite covers authentication, proxy integration, FAISS search, metrics export, and performance validation.

### Test Architecture

```
Browser/Client → Nginx Proxy → FastAPI Backend → FAISS Search → Response
     ↓              ↓              ↓              ↓           ↓
   Test 5        Test 5         Test 2,3       Test 3      All Tests
```

### Quality Gate Requirements

✅ **All 5 smoke test scenarios pass including auth flow and proxy behavior**
✅ **Complete validation of request flow: Browser → Nginx → FastAPI → FAISS → Response**

### Test Scenarios

#### Test 1: Unauthorized Access (401 without token)
- **Purpose**: Verify security authentication is working
- **Method**: GET /forecast without Authorization header
- **Expected**: HTTP 401/403 status code
- **Validation**: Confirms that the API properly rejects unauthorized requests

#### Test 2: Authenticated Health Check (200 with token)
- **Purpose**: Verify authenticated endpoints work correctly
- **Method**: GET /health with valid Bearer token
- **Expected**: HTTP 200 with valid health response JSON
- **Validation**: Confirms authentication system and basic API functionality

#### Test 3: Forecast with FAISS Integration (200 with real data)
- **Purpose**: Verify complete forecast pipeline including FAISS search
- **Method**: GET /forecast?horizon=24h&vars=t2m,u10,v10,msl with token
- **Expected**: HTTP 200 with forecast data containing analog counts
- **Validation**: Confirms FAISS integration, forecast generation, and data pipeline

#### Test 4: Prometheus Metrics Export (200 for /metrics)
- **Purpose**: Verify monitoring and observability integration
- **Method**: GET /metrics with valid Bearer token
- **Expected**: HTTP 200 with Prometheus format metrics
- **Validation**: Confirms metrics collection and export for monitoring stack

#### Test 5: Nginx Proxy Integration (/api/* rewrite, CORS, gzip)
- **Purpose**: Verify complete proxy integration and web server functionality
- **Methods**: 
  - GET /api/health (proxy rewrite test)
  - GET /health (direct endpoint test)
  - OPTIONS /api/health (CORS preflight test)
- **Expected**: All routes work with proper CORS headers and compression
- **Validation**: Confirms nginx configuration, proxy behavior, and web integration

### File Structure

```
/home/micha/adelaide-weather-final/
├── test_e2e_smoke.py                    # Main Python test suite
├── run_smoke_tests.sh                   # Bash test runner script
├── E2E_SMOKE_TEST_DOCUMENTATION.md     # This documentation
├── ci_smoke_test_integration.yml        # CI/CD integration template
└── e2e_smoke_test_results.json         # Test results output (generated)
```

### Usage

#### Quick Start
```bash
# Run complete test suite with automatic setup
./run_smoke_tests.sh

# Run tests against existing services (skip docker-compose setup)
./run_smoke_tests.sh --skip-setup

# Verbose mode with custom timeout
./run_smoke_tests.sh --verbose --timeout 600

# Just cleanup existing services
./run_smoke_tests.sh --cleanup-only
```

#### Direct Python Execution
```bash
# Set API token and run directly
export API_TOKEN="test-e2e-smoke-token-12345"
python3 test_e2e_smoke.py
```

#### CI/CD Integration
```bash
# Use in CI/CD pipeline with structured output
./run_smoke_tests.sh --skip-setup > smoke_test_output.log 2>&1
echo $?  # 0 = all passed, 1 = some failed, 2 = infrastructure failure
```

### Performance Thresholds

| Endpoint | Max Response Time | Performance Tier |
|----------|------------------|------------------|
| /health | 1000ms | Critical |
| /forecast | 2000ms | Standard |
| /metrics | 1000ms | Standard |
| Proxy routes | 5000ms | Startup tolerance |

### Dependencies

#### Required Services
- **Docker & Docker Compose**: Container orchestration
- **Adelaide Weather API**: Main FastAPI backend
- **Nginx**: Reverse proxy and web server
- **FAISS Indices**: For analog search functionality

#### Required Python Packages
```python
requests>=2.28.0  # HTTP client for API testing
```

#### System Requirements
```bash
# Ubuntu/Debian
sudo apt-get install -y docker.io docker-compose python3 python3-pip curl
pip3 install requests

# Verify installation
docker --version
docker-compose --version
python3 --version
```

### Test Results Format

The test suite generates a comprehensive JSON results file:

```json
{
  "success": true,
  "critical_path_passing": true,
  "total_tests": 5,
  "passed_tests": 5,
  "failed_tests": 0,
  "success_rate": 100.0,
  "avg_response_time_ms": 150.5,
  "max_response_time_ms": 298.2,
  "test_results": [
    {
      "name": "Test 1: Unauthorized Access (401 without token)",
      "passed": true,
      "message": "Correctly rejected unauthorized access with status 401",
      "response_time_ms": 89.4,
      "details": {
        "status_code": 401,
        "endpoint": "/forecast"
      }
    }
    // ... additional test results
  ],
  "timestamp": "2025-11-05T12:00:00Z"
}
```

### Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | All tests passed | ✅ Proceed with deployment |
| 1 | Some tests failed | ❌ Fix issues before deployment |
| 2 | Infrastructure failure | 🔧 Check environment setup |
| 130 | User interrupted | ⚠️ Restart tests when ready |

### Troubleshooting

#### Common Issues

**1. Services Not Starting**
```bash
# Check Docker daemon
sudo systemctl status docker
sudo systemctl start docker

# Check port conflicts
netstat -tlnp | grep :80
netstat -tlnp | grep :8000

# View service logs
docker-compose logs api
docker-compose logs nginx
```

**2. Authentication Failures**
```bash
# Verify API token is set
echo $API_TOKEN

# Check token in docker-compose
docker-compose exec api env | grep API_TOKEN

# Test token manually
curl -H "Authorization: Bearer test-e2e-smoke-token-12345" http://localhost:8000/health
```

**3. FAISS Integration Issues**
```bash
# Check FAISS indices exist
ls -la /home/micha/adelaide-weather-final/indices/

# Verify mounting in container
docker-compose exec api ls -la /app/indices/

# Check startup validation logs
docker-compose logs api | grep -i faiss
```

**4. Nginx Proxy Problems**
```bash
# Test direct API access
curl http://localhost:8000/health

# Test nginx proxy
curl http://localhost/api/health

# Check nginx configuration
docker-compose exec nginx nginx -t
```

#### Debug Mode

For detailed debugging, run with maximum verbosity:

```bash
# Enable verbose logging
./run_smoke_tests.sh --verbose

# Check generated log files
cat smoke_test_run.log
cat e2e_smoke_test_results.json | python3 -m json.tool

# Manual service testing
curl -v -H "Authorization: Bearer test-e2e-smoke-token-12345" http://localhost/api/health
```

### Integration with T-013 CI/CD Pipeline

This smoke test suite is designed to integrate with T-013 CI/CD Pipeline:

#### Pipeline Integration Points
1. **Pre-deployment validation**: Run smoke tests before any deployment
2. **Environment promotion gates**: Tests must pass to promote between environments
3. **Rollback triggers**: Failed tests can trigger automatic rollbacks
4. **Performance monitoring**: Track response times across deployments

#### CI/CD Template Integration
```yaml
# Example GitHub Actions integration
smoke_tests:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v3
    - name: Run E2E Smoke Tests
      run: |
        cd /path/to/adelaide-weather-final
        ./run_smoke_tests.sh --timeout 600
      env:
        API_TOKEN: ${{ secrets.API_TOKEN }}
    - name: Upload Test Results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: smoke-test-results
        path: e2e_smoke_test_results.json
```

### Security Considerations

#### Test Token Management
- **Test Token**: Uses a dedicated test token that's different from production
- **Scope**: Limited to smoke test scenarios only
- **Rotation**: Should be rotated regularly in CI/CD environments
- **Isolation**: Does not use production credentials

#### Network Security
- **Local Testing**: Tests run against localhost to avoid external dependencies
- **Container Isolation**: Uses Docker networking for service isolation
- **Port Binding**: Only exposes necessary ports during testing

### Performance Monitoring

The smoke test suite tracks key performance metrics:

#### Response Time Monitoring
- **Individual Test Timing**: Each test measures its own response time
- **Aggregate Metrics**: Average, min, max response times calculated
- **Threshold Validation**: Tests fail if they exceed performance thresholds
- **Trend Analysis**: Results can be tracked over time for performance regression detection

#### Resource Usage
- **Memory Usage**: Can be extended to monitor container memory consumption
- **CPU Usage**: Docker stats integration available for resource monitoring
- **Network I/O**: Network performance can be monitored during proxy tests

### Maintenance and Updates

#### Regular Maintenance Tasks
1. **Update Dependencies**: Keep Python packages and Docker images updated
2. **Review Thresholds**: Adjust performance thresholds based on production data
3. **Extend Scenarios**: Add new test scenarios as features are developed
4. **Log Rotation**: Manage test log files to prevent disk space issues

#### Version Compatibility
- **API Versioning**: Tests should be updated when API contracts change
- **Docker Images**: Ensure test environment matches target deployment images
- **FAISS Indices**: Update test expectations when FAISS indices are regenerated

### Success Criteria Validation

✅ **All 5 test scenarios pass automatically**
- Unauthorized access properly rejected (Test 1)
- Authenticated health endpoint works (Test 2)
- Forecast returns real FAISS data (Test 3)
- Metrics endpoint exports Prometheus data (Test 4)
- Nginx proxy integration functions correctly (Test 5)

✅ **Auth flow properly rejects/accepts requests**
- Test 1 validates rejection of unauthorized requests
- Tests 2-4 validate acceptance of valid tokens
- Comprehensive token validation including format checks

✅ **Proxy correctly routes and transforms requests**
- Test 5 validates /api/* → /* URL rewriting
- CORS headers properly set for cross-origin requests
- Compression and performance optimization working

✅ **FAISS search returns real results in forecast endpoint**
- Test 3 validates forecast endpoint returns analog_count > 0
- Actual FAISS integration confirmed through response metadata
- Real search results included in forecast variables

✅ **Performance meets basic latency requirements**
- All tests measure and validate response times
- Configurable thresholds for different endpoint types
- Performance regression detection through metrics tracking

✅ **Test suite can be run in CI/CD pipeline**
- Fully automated with no manual intervention required
- Structured JSON output for machine processing
- Appropriate exit codes for pipeline decision making
- Docker-based execution for consistency across environments

### Conclusion

This comprehensive E2E smoke test suite provides robust validation of the Adelaide Weather system's critical path functionality. It ensures that all components work together correctly and that the system is ready for production deployment.

The test suite is designed to be:
- **Comprehensive**: Covers all critical functionality
- **Automated**: Runs without manual intervention
- **Fast**: Completes in under 5 minutes typically
- **Reliable**: Provides consistent results across environments
- **Integrated**: Ready for CI/CD pipeline integration

With this test suite in place, T-013 CI/CD Pipeline can proceed with confidence that the quality gates are properly implemented and the system is ready for automated deployment workflows.