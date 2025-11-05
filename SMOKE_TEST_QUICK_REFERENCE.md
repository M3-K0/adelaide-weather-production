# Adelaide Weather E2E Smoke Tests - Quick Reference

## 🚀 Quick Start

```bash
# Run all smoke tests with automatic setup
./run_smoke_tests.sh

# Run tests against existing services
./run_smoke_tests.sh --skip-setup

# Cleanup only
./run_smoke_tests.sh --cleanup-only
```

## 📋 Test Scenarios

| Test | Purpose | Endpoint | Expected |
|------|---------|----------|----------|
| 1 | Auth Rejection | `/forecast` (no token) | 401/403 |
| 2 | Health Check | `/health` (with token) | 200 + JSON |
| 3 | FAISS Forecast | `/forecast?horizon=24h` | 200 + analog data |
| 4 | Metrics Export | `/metrics` (with token) | 200 + Prometheus |
| 5 | Nginx Proxy | `/api/health` + CORS | 200 + headers |

## ⚡ Performance Thresholds

- Health: < 1000ms
- Forecast: < 2000ms  
- Metrics: < 1000ms
- Proxy: < 5000ms

## 🔧 Configuration

- **Test Token**: `test-e2e-smoke-token-12345`
- **Base URL**: `http://localhost`
- **API URL**: `http://localhost:8000`
- **Timeout**: 300s (configurable)

## 📊 Exit Codes

- `0` = All tests passed ✅
- `1` = Some tests failed ❌
- `2` = Infrastructure failure 🔧
- `130` = User interrupted ⚠️

## 🐛 Troubleshooting

```bash
# Check services
docker-compose ps
docker-compose logs api

# Test manually
curl -H "Authorization: Bearer test-e2e-smoke-token-12345" http://localhost:8000/health

# View detailed results
cat e2e_smoke_test_results.json | python3 -m json.tool
```

## 🔄 CI/CD Usage

```yaml
- name: E2E Smoke Tests
  run: ./run_smoke_tests.sh --timeout 600
  env:
    API_TOKEN: ${{ secrets.API_TOKEN }}
```

## 📁 Key Files

- `test_e2e_smoke.py` - Main test suite
- `run_smoke_tests.sh` - Test runner
- `e2e_smoke_test_results.json` - Results output
- `smoke_test_run.log` - Execution log