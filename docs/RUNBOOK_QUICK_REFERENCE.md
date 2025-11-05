# Adelaide Weather API - Runbook Quick Reference

**Emergency Contact:** #incident-response Slack | PagerDuty: Adelaide Weather API  
**System:** Adelaide Weather Forecasting API  
**Last Updated:** 2025-11-05

---

## 🚨 Emergency Commands

### System Status Check
```bash
# Quick health check
curl -f "https://api.adelaide-weather.com/health"

# Service status
kubectl get pods -l app=api -n weather-forecast-prod

# Recent errors
kubectl logs -l app=api --tail=20 -n weather-forecast-prod | grep ERROR
```

### Performance Troubleshooting
```bash
# Response time test
time curl -H "Authorization: Bearer $API_TOKEN" \
  "https://api.adelaide-weather.com/forecast?horizon=24h&vars=t2m"

# Resource usage
kubectl top pods -l app=api -n weather-forecast-prod

# Scale up (if needed)
kubectl scale deployment api-deployment --replicas=5 -n weather-forecast-prod
```

---

## 🔧 Common Fixes

### FAISS Indices Missing
```bash
# 1. Check indices
ls -la /app/indices/faiss_*h_*.faiss

# 2. Restore from backup (fastest)
aws s3 sync s3://weather-forecast-indices-backup/$(date +%Y%m%d)/indices/ /tmp/faiss_recovery/
kubectl cp /tmp/faiss_recovery/ weather-forecast-prod/api-pod:/app/indices/

# 3. Restart API
kubectl rollout restart deployment/api-deployment -n weather-forecast-prod
```

### Emergency Token Rotation
```bash
# 1. Generate new token
NEW_TOKEN=$(openssl rand -hex 32)

# 2. Update secret
kubectl create secret generic api-secrets \
  --from-literal=API_TOKEN=$NEW_TOKEN \
  --dry-run=client -o yaml | kubectl apply -f -

# 3. Restart pods
kubectl delete pods -l app=api -n weather-forecast-prod

# 4. Test new token
curl -H "Authorization: Bearer $NEW_TOKEN" \
  "https://api.adelaide-weather.com/health"
```

### High Error Rate Response
```bash
# 1. Check error rate
for i in {1..10}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    "https://api.adelaide-weather.com/health"
done

# 2. Restart all pods
kubectl delete pods -l app=api -n weather-forecast-prod

# 3. Enable emergency mode (if needed)
kubectl set env deployment/api-deployment \
  EMERGENCY_MODE=true \
  SIMPLE_RESPONSES=true \
  -n weather-forecast-prod
```

### Memory Issues
```bash
# 1. Check memory usage
kubectl top pods -l app=api -n weather-forecast-prod

# 2. Restart high-memory pods
kubectl get pods -l app=api -n weather-forecast-prod | \
  awk 'NR>1 && $4 > 400 {print $1}' | \
  xargs kubectl delete pod -n weather-forecast-prod

# 3. Enable memory optimization
kubectl set env deployment/api-deployment \
  MEMORY_OPTIMIZATION=true \
  FAISS_LAZY_LOAD=true \
  -n weather-forecast-prod
```

---

## 📊 Monitoring Dashboards

### Primary Dashboards
- **Grafana:** http://grafana.adelaide-weather.com
- **CloudWatch:** AWS Console → CloudWatch → Dashboards
- **API Health:** https://api.adelaide-weather.com/health
- **FAISS Health:** https://api.adelaide-weather.com/health/faiss

### Key Metrics
- **SLA Target:** P95 < 150ms, Availability > 99.9%, Error Rate < 1%
- **FAISS Pattern Counts:** 6h/12h: 6,574 | 24h/48h: 13,148
- **Memory Limit:** ~500MB per pod
- **CPU Target:** <70% average

---

## 🔐 Security Incidents

### Authentication Failures
```bash
# Check for brute force
kubectl logs -l app=api --tail=500 -n weather-forecast-prod | \
  grep "authentication_attempt.*success.*false" | \
  grep -o '"client_ip":"[^"]*"' | sort | uniq -c | sort -nr

# Emergency IP blocking (manual WAF update required)
# aws wafv2 update-ip-set --addresses IP_ADDRESS/32
```

### Emergency Security Mode
```bash
# Enable strict security
kubectl set env deployment/api-deployment \
  SECURITY_MODE=strict \
  RATE_LIMIT_PER_MINUTE=10 \
  ENHANCED_AUTH_LOGGING=true \
  -n weather-forecast-prod
```

---

## 📞 Escalation Contacts

### Incident Severity
- **Critical (< 5 min):** PagerDuty → On-call Engineer → Lead → Manager
- **High (< 15 min):** Slack #weather-alerts → On-call Engineer → Lead  
- **Medium (< 2 hours):** Slack #weather-alerts → Team discussion
- **Low (next business day):** Email → Product backlog

### Emergency Webhooks
```bash
# Critical alerts
curl -X POST $PAGERDUTY_WEBHOOK_URL -d '{"routing_key":"'$PAGERDUTY_ROUTING_KEY'","event_action":"trigger","payload":{"summary":"Critical Adelaide Weather API Issue","severity":"critical"}}'

# Team notifications  
curl -X POST $SLACK_WEBHOOK_URL -d '{"text":"🚨 Adelaide Weather API Emergency - Manual intervention required","channel":"#weather-critical"}'
```

---

## 🔍 Validation Commands

### Full System Validation
```bash
# Health endpoints
curl -f "https://api.adelaide-weather.com/health"
curl -f "https://api.adelaide-weather.com/health/detailed"
curl -f "https://api.adelaide-weather.com/health/faiss"

# Core functionality
curl -H "Authorization: Bearer $API_TOKEN" \
  "https://api.adelaide-weather.com/forecast?horizon=24h&vars=t2m" | \
  jq '.variables.t2m.available'

# Performance test
for i in {1..5}; do
  time curl -s -H "Authorization: Bearer $API_TOKEN" \
    "https://api.adelaide-weather.com/forecast?horizon=6h&vars=t2m" > /dev/null
done
```

### FAISS Validation
```bash
# Check all required indices
for horizon in 6 12 24 48; do
  for type in flatip ivfpq; do
    file="/app/indices/faiss_${horizon}h_${type}.faiss"
    if [ -f "$file" ]; then
      echo "✓ $file exists"
    else
      echo "✗ Missing: $file"
    fi
  done
done
```

---

## ⚡ Performance Optimization

### Quick Performance Fixes
```bash
# Scale up
kubectl scale deployment api-deployment --replicas=5 -n weather-forecast-prod

# Enable performance mode
kubectl set env deployment/api-deployment \
  PERFORMANCE_MODE=true \
  FAISS_LAZY_LOAD=true \
  RESPONSE_CACHING=true \
  -n weather-forecast-prod

# CPU optimization
kubectl set env deployment/api-deployment \
  TORCH_NUM_THREADS=2 \
  OMP_NUM_THREADS=2 \
  -n weather-forecast-prod
```

### Emergency Fallback Mode
```bash
# Simple search mode
kubectl set env deployment/api-deployment \
  ANALOG_SEARCH_MODE=simplified \
  ANALOG_MAX_NEIGHBORS=20 \
  FAISS_SIMPLE_SEARCH=true \
  -n weather-forecast-prod
```

---

## 📋 Backup & Recovery

### Backup Locations
- **FAISS Indices:** `s3://weather-forecast-indices-backup/YYYYMMDD/`
- **Outcomes Data:** `s3://weather-forecast-outcomes-backup/YYYYMMDD/`
- **Configuration:** `s3://weather-forecast-config-backup/YYYYMMDD/`

### Quick Recovery
```bash
# Restore indices from backup
BACKUP_DATE=$(date +%Y%m%d)
aws s3 sync s3://weather-forecast-indices-backup/$BACKUP_DATE/indices/ /tmp/recovery/
kubectl cp /tmp/recovery/ weather-forecast-prod/api-pod:/app/indices/
kubectl rollout restart deployment/api-deployment -n weather-forecast-prod
```

---

## 🚨 Emergency Checklist

### System Down Response
- [ ] Check health endpoints
- [ ] Verify pod status  
- [ ] Check recent logs for errors
- [ ] Restart deployment if needed
- [ ] Verify recovery with test requests
- [ ] Update status page if customer-facing
- [ ] Document incident for post-mortem

### Performance Issues
- [ ] Measure current response times
- [ ] Check resource utilization
- [ ] Scale up if resource constrained
- [ ] Restart high-memory pods
- [ ] Enable performance optimizations
- [ ] Monitor improvement
- [ ] Validate SLA compliance

### Security Incidents
- [ ] Identify attack patterns
- [ ] Block suspicious IPs
- [ ] Rotate API tokens
- [ ] Enable enhanced monitoring
- [ ] Document security event
- [ ] Notify security team
- [ ] Conduct security review

---

**For detailed procedures, see:** [OPERATIONAL_RUNBOOKS.md](./OPERATIONAL_RUNBOOKS.md)

**Emergency Contact:** Slack #incident-response | PagerDuty: Adelaide Weather API