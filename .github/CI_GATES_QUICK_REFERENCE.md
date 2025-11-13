# CI Gates Quick Reference

## 🚨 Critical Gates - DEPLOYMENT BLOCKING

### 1. Analog Fallback Gate
- **Threshold**: `analog_fallback_total` must equal **0**
- **Impact**: Pipeline FAILS if > 0
- **Check**: `curl http://localhost:8000/metrics | grep analog_fallback_total`

### 2. Security Drift Gate  
- **Threshold**: Critical security drift events must equal **0**
- **Impact**: Pipeline FAILS if > 0
- **Check**: `curl http://localhost:8000/health/security`

### 3. Test Coverage Gate
- **Threshold**: **90% minimum** coverage
- **Impact**: Pipeline FAILS if < 90%
- **Check**: `pytest --cov=api --cov=core --cov-report=term-missing`

## ⚡ Quick Fixes

### Format Code
```bash
black .                    # Format Python code
isort .                    # Sort Python imports  
cd frontend && npm run format  # Format TypeScript/React
```

### Run Quality Gates Locally
```bash
# All gates
./scripts/run_quality_gates.sh

# Quick check
./scripts/run_quality_gates.sh --fast

# Backend only
./scripts/run_quality_gates.sh --skip-frontend
```

### Check Monitoring Status
```bash
# Validate monitoring gates
python scripts/validate_monitoring_gates.py

# Check health endpoints
curl http://localhost:8000/health/faiss
curl http://localhost:8000/health/security
```

## 🔧 Quality Tools

### Python Tools
```bash
black --check .           # Check formatting
flake8 .                  # Lint code
mypy . --ignore-missing-imports  # Type check
bandit -r .               # Security scan
safety check              # Dependency scan
```

### Frontend Tools
```bash
cd frontend
npm run lint              # ESLint
npm run type-check        # TypeScript  
npm run format:check      # Prettier check
npm audit --audit-level=high  # Security audit
```

## 🚦 Pipeline Status

### Check Pipeline Status
- View workflow runs in GitHub Actions
- Check summary in PR comments
- Review artifact reports

### Emergency Override
```yaml
# Use only in emergency
workflow_dispatch:
  inputs:
    force_deploy: true
```

## 📊 Monitoring Integration

### Key Metrics
- `analog_fallback_total` - Must be 0
- `analog_real_total` - Real searches
- Security drift events - Critical must be 0
- FAISS health status

### Health Endpoints
- `/health/live` - Liveness probe
- `/health/ready` - Readiness probe  
- `/health/faiss` - FAISS status
- `/health/security` - Security drift

## ❌ Common Failures

| Error | Solution |
|-------|----------|
| Black formatting | Run `black .` |
| Import sorting | Run `isort .` |
| Coverage < 90% | Add tests |
| Security issues | Fix bandit/safety alerts |
| Fallbacks > 0 | Fix FAISS issues |
| Security drift | Review config changes |

## 🎯 Best Practices

1. **Run local validation** before pushing
2. **Fix quality issues** immediately  
3. **Monitor fallback counters** in development
4. **Review security drift** regularly
5. **Maintain test coverage** above 90%

## 🆘 Emergency Procedures

### Critical Pipeline Failure
1. Check monitoring gates status
2. Validate health endpoints
3. Review security drift events
4. Fix issues or use emergency override

### Analog Fallback Detection
1. Check FAISS health: `curl /health/faiss`
2. Validate indices status
3. Fix FAISS operational issues
4. Verify fallback counter reset

### Security Drift Detected
1. Check drift events: `curl /health/security`
2. Review configuration changes
3. Address critical security issues
4. Validate drift detector status

---

**Need Help?** Check the full implementation report: `CI_GATES_ENFORCEMENT_IMPLEMENTATION_REPORT.md`