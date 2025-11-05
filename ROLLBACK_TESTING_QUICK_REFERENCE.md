# Adelaide Weather - Rollback Testing Quick Reference

## 🚀 Quick Commands

### Validate Rollback Capabilities
```bash
./scripts/rollback_automation.sh validate
```

### Test Specific Rollback Scenarios
```bash
# Test deployment failure rollback
./scripts/rollback_automation.sh test deployment_failure development

# Test security emergency rollback  
./scripts/rollback_automation.sh test security_issue production

# Test performance degradation rollback
./scripts/rollback_automation.sh test performance_degradation staging

# Test FAISS corruption rollback
./scripts/rollback_automation.sh test faiss_corruption development
```

### Execute Production Rollback
```bash
# Manual production rollback
./scripts/rollback_automation.sh execute production

# Using deploy script
./deploy.sh --rollback production

# Enhanced deployment with rollback testing
./deploy_with_rollback_testing.sh production --test-rollback --rto-monitoring
```

### Comprehensive Testing
```bash
# Run all rollback scenarios
python3 test_rollback_comprehensive.py --environment development

# Test with specific environment
python3 test_rollback_comprehensive.py --environment staging
```

## 📊 RTO Targets

| Scenario | RTO Target | Use Case |
|----------|------------|----------|
| Deployment Failure | 300s (5 min) | Failed deployment recovery |
| Performance Degradation | 180s (3 min) | Performance issue recovery |
| Security Issue | 120s (2 min) | Emergency security recovery |
| FAISS Corruption | 240s (4 min) | Search functionality recovery |
| Configuration Error | 150s (2.5 min) | Config rollback |
| DB Migration Failure | 360s (6 min) | Database recovery |
| Health Check Failure | 240s (4 min) | Service health recovery |

## 🔍 Monitoring Commands

### Check System Status
```bash
# Current deployment status
docker compose ps

# Health endpoint check
curl http://localhost:8000/health

# FAISS health check
curl http://localhost:8000/health/faiss
```

### Review Rollback Reports
```bash
# List recent rollback reports
ls -la rollback_report_*.json

# View latest report
cat $(ls -t rollback_report_*.json | head -1) | jq .

# Check RTO compliance
grep -r "RTO compliance" rollback_report_*.json
```

## 🛠️ Troubleshooting

### Common Issues

**Rollback Validation Failed**
```bash
# Check prerequisites
./scripts/rollback_automation.sh validate

# Verify backup exists
ls -la .last_backup_*

# Check system requirements
docker --version
docker compose version
```

**RTO Target Exceeded**
```bash
# Review rollback timing
cat .rollback_duration_* .rollback_rto_target_*

# Check system performance
docker stats

# Review logs for bottlenecks
tail -f logs/rollback-*.log
```

**Post-Rollback Validation Failed**
```bash
# Manual health check
curl -v http://localhost:8000/health

# Check service logs
docker compose logs api

# Verify service containers
docker compose ps
```

## 📋 Testing Checklist

### Pre-Testing
- [ ] Validate rollback capabilities
- [ ] Verify backup functionality
- [ ] Check system resources
- [ ] Review current deployment state

### During Testing
- [ ] Monitor RTO compliance
- [ ] Track rollback execution
- [ ] Validate failure simulation
- [ ] Monitor system recovery

### Post-Testing
- [ ] Verify functionality restoration
- [ ] Check performance metrics
- [ ] Review rollback reports
- [ ] Update procedures if needed

## 🎯 Best Practices

### Regular Testing
- Run `rollback_automation.sh validate` weekly
- Execute scenario tests monthly
- Perform comprehensive testing quarterly
- Review and update RTO targets annually

### Production Rollbacks
- Always validate capabilities before rollback
- Use `--rto-monitoring` for timing measurement
- Verify post-rollback functionality
- Document lessons learned

### Emergency Procedures
- Use CI/CD rollback automation when possible
- Have manual rollback commands ready
- Maintain communication during rollback
- Escalate if RTO targets are exceeded

## 📞 Emergency Contacts

### Rollback Escalation
1. **Operations Team**: For rollback execution assistance
2. **Development Team**: For application-specific issues
3. **Infrastructure Team**: For system-level problems
4. **Security Team**: For security-related rollbacks

### Key Files Reference
- **Main Testing**: `test_rollback_comprehensive.py`
- **Automation Script**: `scripts/rollback_automation.sh`
- **Deploy Script**: `deploy.sh` (with `--rollback` option)
- **Enhanced Deploy**: `deploy_with_rollback_testing.sh`
- **CI/CD Workflow**: `.github/workflows/rollback-automation.yml`
- **Emergency Recovery**: `scripts/emergency_recovery.sh`

---

*Quick Reference for T-016 Rollback Testing Implementation*  
*Adelaide Weather Forecasting System*