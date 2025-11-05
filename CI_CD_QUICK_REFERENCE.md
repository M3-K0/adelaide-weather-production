# CI/CD Pipeline Quick Reference

## 🚀 Quick Start

### Trigger Deployments
```bash
# Staging deployment
git push origin develop

# Production deployment  
git push origin main

# Manual deployment
gh workflow run comprehensive-ci-cd.yml -f environment=staging
```

### Monitor Pipeline
```bash
# Check pipeline health
python scripts/pipeline-health-monitor.py --days 7

# View latest runs
gh run list --workflow=comprehensive-ci-cd.yml --limit 10
```

### Emergency Rollback
```bash
gh workflow run rollback-automation.yml \
  -f environment=production \
  -f rollback_target=previous \
  -f reason="Critical issue description"
```

## 📋 Pipeline Stages

| Stage | Purpose | Duration | Quality Gates |
|-------|---------|----------|---------------|
| **Build** | Docker image creation | 3-5 min | Multi-stage builds, caching |
| **Test** | Unit & integration tests | 5-8 min | Unit tests, Pact verification |
| **Security** | Vulnerability scanning | 2-3 min | Trivy scans, dependency audit |
| **Smoke** | E2E validation | 3-5 min | T-009 smoke tests |
| **Artifact** | Image tagging & push | 1-2 min | Registry management |
| **Deploy** | Environment deployment | 2-4 min | Health checks, validation |

## 🔧 Configuration

### Environment Variables
```bash
# Required for GitHub Actions
GITHUB_TOKEN=ghp_xxx        # GitHub registry access
API_TOKEN=xxx               # Application auth token

# Optional
PACT_BROKER_BASE_URL=xxx    # Pact broker integration
SLACK_WEBHOOK_URL=xxx       # Notifications
```

### Quality Gate Thresholds
```yaml
success_rate_min: 85%       # Pipeline success rate
avg_duration_max: 15min     # Average build time
security_critical: 0        # Critical vulnerabilities
test_coverage_min: 80%      # Code coverage
```

## 🐛 Troubleshooting

### Common Issues

**Build Failures**:
```bash
# Check build logs
gh run view <run-id> --log

# Rebuild with clean cache
gh workflow run comprehensive-ci-cd.yml -f clean_cache=true
```

**Test Failures**:
```bash
# Run tests locally
docker-compose up -d
python test_e2e_smoke.py

# Check Pact verification
cd api && python -m pytest pact/provider/test_provider.py -v
```

**Security Scan Failures**:
```bash
# Local security scan
trivy fs . --severity HIGH,CRITICAL
npm audit --audit-level moderate
```

**Deployment Issues**:
```bash
# Check service health
curl -f http://localhost/health
docker-compose logs api

# Manual rollback
gh workflow run rollback-automation.yml \
  -f environment=staging \
  -f rollback_target=previous \
  -f reason="Manual rollback for testing"
```

## 📊 Monitoring

### Key Metrics
- **Success Rate**: Target >95%
- **Build Duration**: Target <15min avg
- **Deployment Frequency**: Target >1/day
- **MTTR**: Target <1hr

### Alert Conditions
- Success rate drops below 85%
- Average duration exceeds 20min
- Critical security vulnerabilities
- Smoke test failures

### Health Check URLs
```bash
# API health
curl http://localhost:8000/health

# Frontend health  
curl http://localhost:3000/api/health

# Nginx proxy
curl http://localhost/health
```

## 🔄 Rollback Procedures

### Automatic Rollback Triggers
- Smoke test failures
- Health check failures
- Critical security vulnerabilities
- Manual trigger via GitHub Actions

### Rollback Types
1. **Previous**: Roll back to last successful deployment
2. **Specific**: Roll back to specific commit SHA
3. **Emergency**: Skip validation for critical issues

### Rollback Validation
- Pre-rollback health checks
- Target image verification
- Post-rollback smoke tests
- Monitoring setup

## 🛠️ Maintenance

### Weekly Tasks
```bash
# Check pipeline health
python scripts/pipeline-health-monitor.py --days 7

# Review failed runs
gh run list --status failure --limit 20

# Clean up old artifacts
gh api repos/:owner/:repo/actions/artifacts --paginate | \
  jq '.artifacts[] | select(.created_at < "2024-01-01") | .id'
```

### Monthly Tasks
- Review and update dependencies
- Analyze performance trends
- Update security thresholds
- Review rollback procedures

## 📞 Support Contacts

- **CI/CD Issues**: DevOps Team
- **Test Failures**: QA Team  
- **Security Issues**: Security Team
- **Deployment Issues**: Platform Team

## 🔗 Related Documentation

- [Full Implementation Guide](./CI_CD_COMPREHENSIVE_IMPLEMENTATION.md)
- [E2E Smoke Tests](./T009_E2E_SMOKE_TEST_COMPLETION_REPORT.md)
- [Contract Testing](./CONTRACT_TESTING_STRATEGY.md)
- [Security Baseline](./SECURITY_BASELINE_SCANNING.md)