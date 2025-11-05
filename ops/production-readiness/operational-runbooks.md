# Operational Runbooks - Production Ready Operations Guide

**System:** Adelaide Weather Forecast Application  
**Document Date:** 2025-10-29  
**Document Type:** Operational Procedures and Incident Response  
**Scope:** Production Environment Operations  

---

## Table of Contents

1. [Emergency Response Procedures](#1-emergency-response-procedures)
2. [System Health Monitoring](#2-system-health-monitoring)
3. [Application Deployment Procedures](#3-application-deployment-procedures)
4. [Infrastructure Scaling Operations](#4-infrastructure-scaling-operations)
5. [Security Incident Response](#5-security-incident-response)
6. [Data Backup and Recovery Operations](#6-data-backup-and-recovery-operations)
7. [Performance Issue Troubleshooting](#7-performance-issue-troubleshooting)
8. [Third-Party Service Dependencies](#8-third-party-service-dependencies)
9. [Maintenance Windows and Updates](#9-maintenance-windows-and-updates)
10. [Contact Information and Escalation](#10-contact-information-and-escalation)

---

## 1. Emergency Response Procedures

### 1.1 Critical System Outage Response

**Severity:** Critical  
**Response Time:** Immediate (< 5 minutes)  
**Escalation:** PagerDuty → On-call Engineer → Team Lead → Engineering Manager  

**Symptoms:**
- API health check failures
- 500 error rates > 5%
- Complete service unavailability
- Load balancer health check failures

**Immediate Actions:**
```bash
# 1. Check system health status
curl -f https://api.adelaide-weather.com/health
curl -f https://adelaide-weather.com

# 2. Check ECS service status
aws ecs describe-services --cluster weather-forecast-prod --services api frontend

# 3. Check ALB target health
aws elbv2 describe-target-health --target-group-arn <TARGET_GROUP_ARN>

# 4. Check CloudWatch logs for errors
aws logs tail --log-group-name "/ecs/weather-forecast-prod/api" --since 10m

# 5. Check auto-scaling events
aws application-autoscaling describe-scaling-activities --service-namespace ecs
```

**Recovery Steps:**
1. **Assess Impact:**
   - Determine affected services (API, Frontend, Both)
   - Check user impact via monitoring dashboards
   - Identify potential root cause from logs

2. **Immediate Mitigation:**
   ```bash
   # Force service restart if needed
   aws ecs update-service --cluster weather-forecast-prod --service api --force-new-deployment
   
   # Scale up if capacity issue
   aws ecs update-service --cluster weather-forecast-prod --service api --desired-count 5
   ```

3. **Communication:**
   - Post in #incident-response Slack channel
   - Update status page if customer-facing
   - Notify stakeholders via incident communication plan

4. **Resolution Verification:**
   ```bash
   # Verify service recovery
   curl -f https://api.adelaide-weather.com/health
   curl -f "https://api.adelaide-weather.com/forecast?horizon=24h&vars=t2m"
   
   # Check performance metrics
   # Verify error rates return to normal (<1%)
   # Confirm response times meet SLA (<150ms)
   ```

### 1.2 Performance Degradation Response

**Severity:** High  
**Response Time:** 15 minutes  
**Triggers:** API latency P95 > 150ms, Error rate > 1%  

**Investigation Steps:**
```bash
# 1. Check current performance metrics
aws cloudwatch get-metric-statistics --namespace AWS/ECS \
  --metric-name CPUUtilization --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) --period 300 --statistics Average

# 2. Check FAISS index health
curl -s "https://api.adelaide-weather.com/health" | jq '.checks'

# 3. Analyze request patterns
aws logs insights start-query --log-group-name "/ecs/weather-forecast-prod/api" \
  --start-time $(date -d '1 hour ago' +%s) --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc'
```

**Mitigation Actions:**
```bash
# 1. Scale up if resource constrained
aws ecs update-service --cluster weather-forecast-prod --service api --desired-count 5

# 2. Check for memory leaks
aws ecs describe-tasks --cluster weather-forecast-prod --tasks $(aws ecs list-tasks --cluster weather-forecast-prod --service-name api --query 'taskArns[0]' --output text)

# 3. Restart problematic containers if identified
aws ecs stop-task --cluster weather-forecast-prod --task <TASK_ARN>
```

### 1.3 Security Incident Response

**Severity:** Critical/High  
**Response Time:** Immediate  
**Triggers:** Security violations, Authentication failures spike, Suspicious patterns  

**Immediate Response:**
```bash
# 1. Check security logs
aws logs insights start-query --log-group-name "/ecs/weather-forecast-prod/api" \
  --start-time $(date -d '1 hour ago' +%s) --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /security_violation/ | sort @timestamp desc'

# 2. Check authentication failure rates
aws cloudwatch get-metric-statistics --namespace WeatherForecast \
  --metric-name AuthenticationFailures --start-time $(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) --period 300 --statistics Sum

# 3. Review access patterns
aws logs insights start-query --log-group-name "/ecs/weather-forecast-prod/api" \
  --start-time $(date -d '1 hour ago' +%s) --end-time $(date +%s) \
  --query-string 'fields @timestamp, client_ip, user_agent | filter @message like /authentication_attempt/ | stats count() by client_ip | sort count desc'
```

**Containment Actions:**
```bash
# 1. Block suspicious IPs if identified
# Update security group to deny specific IP ranges
aws ec2 authorize-security-group-ingress --group-id <SG_ID> --protocol tcp --port 443 --source-group <DENY_IP>/32

# 2. Rotate API tokens if compromised
# Generate new tokens and update environment variables
kubectl create secret generic api-secrets --from-literal=API_TOKEN=<NEW_TOKEN>

# 3. Enable enhanced monitoring
# Increase log verbosity and monitoring frequency
```

---

## 2. System Health Monitoring

### 2.1 Health Check Procedures

**Daily Health Verification:**
```bash
#!/bin/bash
# Daily system health check script

echo "=== Adelaide Weather Forecast Daily Health Check ==="
echo "Date: $(date)"
echo

# 1. API Health Check
echo "1. API Health Status:"
API_HEALTH=$(curl -s https://api.adelaide-weather.com/health)
if echo "$API_HEALTH" | jq -e '.status == "healthy"' > /dev/null; then
    echo "   ✅ API is healthy"
else
    echo "   ❌ API health check failed"
    echo "   Response: $API_HEALTH"
fi

# 2. Frontend Health Check
echo "2. Frontend Status:"
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://adelaide-weather.com)
if [ "$FRONTEND_STATUS" = "200" ]; then
    echo "   ✅ Frontend is accessible"
else
    echo "   ❌ Frontend returned status: $FRONTEND_STATUS"
fi

# 3. Core Functionality Test
echo "3. Core Functionality:"
FORECAST_TEST=$(curl -s "https://api.adelaide-weather.com/forecast?horizon=24h&vars=t2m" -H "Authorization: Bearer $API_TOKEN")
if echo "$FORECAST_TEST" | jq -e '.forecast' > /dev/null; then
    echo "   ✅ Forecast generation working"
else
    echo "   ❌ Forecast generation failed"
fi

# 4. Performance Check
echo "4. Performance Metrics:"
RESPONSE_TIME=$(curl -o /dev/null -s -w "%{time_total}" "https://api.adelaide-weather.com/health")
if (( $(echo "$RESPONSE_TIME < 0.15" | bc -l) )); then
    echo "   ✅ Response time: ${RESPONSE_TIME}s (within SLA)"
else
    echo "   ⚠️  Response time: ${RESPONSE_TIME}s (exceeds SLA)"
fi

# 5. Resource Utilization
echo "5. Resource Utilization:"
# Check ECS service CPU/Memory
aws ecs describe-services --cluster weather-forecast-prod --services api frontend --query 'services[*].[serviceName,runningCount,desiredCount]' --output table

echo
echo "=== Health Check Complete ==="
```

### 2.2 Monitoring Dashboard Access

**Primary Dashboards:**
- **Grafana:** http://grafana.adelaide-weather.com
  - Username: admin
  - Password: Check AWS Secrets Manager `/weather-forecast/grafana/admin-password`
  - Key Dashboards:
    - Adelaide Weather API Performance
    - Infrastructure Overview
    - SLO Dashboard

**CloudWatch Dashboards:**
```bash
# View CloudWatch dashboard
aws cloudwatch list-dashboards --dashboard-name-prefix "WeatherForecast"

# Get dashboard URL
echo "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=WeatherForecast-Production"
```

### 2.3 Key Performance Indicators (KPIs)

**Critical Metrics to Monitor:**
```yaml
primary_slis:
  api_availability:
    target: "> 99.9%"
    measurement: "uptime over 24h"
    alert_threshold: "< 99.5%"
    
  api_latency:
    target: "P95 < 150ms"
    measurement: "95th percentile response time"
    alert_threshold: "> 100ms"
    
  error_rate:
    target: "< 1%"
    measurement: "5xx errors / total requests"
    alert_threshold: "> 0.5%"
    
  forecast_success_rate:
    target: "> 99%"
    measurement: "successful forecast generations"
    alert_threshold: "< 98%"

infrastructure_metrics:
  cpu_utilization:
    normal_range: "10-30%"
    warning_threshold: "> 70%"
    critical_threshold: "> 90%"
    
  memory_utilization:
    normal_range: "100-300MB"
    warning_threshold: "> 400MB"
    critical_threshold: "> 500MB"
    
  container_restart_rate:
    target: "< 1 restart/day"
    alert_threshold: "> 3 restarts/hour"
```

---

## 3. Application Deployment Procedures

### 3.1 Production Deployment Process

**Pre-Deployment Checklist:**
- [ ] Code reviewed and approved by at least 2 engineers
- [ ] All tests passing (unit, integration, e2e)
- [ ] Security scans completed (SAST, DAST, dependency)
- [ ] Performance tests executed and within SLA
- [ ] Database migrations tested (if applicable)
- [ ] Rollback plan documented and tested
- [ ] Deployment window scheduled and communicated
- [ ] Monitoring alerts configured for new deployment

**Deployment Steps:**
```bash
# 1. Pre-deployment health check
./scripts/health-check.sh production

# 2. Deploy to staging first
git checkout release/v1.x.x
./deploy.sh staging

# 3. Validate staging deployment
./scripts/validate-deployment.sh staging

# 4. Deploy to production (blue-green deployment)
./deploy.sh production

# 5. Monitor deployment progress
kubectl rollout status deployment/api-deployment -n weather-forecast-prod
kubectl rollout status deployment/frontend-deployment -n weather-forecast-prod

# 6. Run smoke tests
./scripts/smoke-tests.sh production

# 7. Monitor metrics for 30 minutes
# Watch for error rates, response times, resource utilization
```

**Post-Deployment Verification:**
```bash
# Verify deployment success
kubectl get deployments -n weather-forecast-prod
kubectl get pods -n weather-forecast-prod

# Check application logs
kubectl logs -f deployment/api-deployment -n weather-forecast-prod

# Verify health endpoints
curl -f https://api.adelaide-weather.com/health
curl -f https://adelaide-weather.com

# Test core functionality
curl -H "Authorization: Bearer $API_TOKEN" \
  "https://api.adelaide-weather.com/forecast?horizon=24h&vars=t2m,cape"

# Monitor performance metrics
# Error rate should be < 1%
# Response time should be < 150ms P95
# No increase in container restarts
```

### 3.2 Rollback Procedures

**Automatic Rollback Triggers:**
- Error rate > 5% for 5 minutes
- Response time P95 > 300ms for 5 minutes
- Health check failures > 50% for 2 minutes

**Manual Rollback Process:**
```bash
# 1. Identify last known good version
kubectl rollout history deployment/api-deployment -n weather-forecast-prod

# 2. Rollback to previous version
kubectl rollout undo deployment/api-deployment -n weather-forecast-prod
kubectl rollout undo deployment/frontend-deployment -n weather-forecast-prod

# 3. Verify rollback success
kubectl rollout status deployment/api-deployment -n weather-forecast-prod
kubectl get pods -n weather-forecast-prod

# 4. Test functionality
curl -f https://api.adelaide-weather.com/health
./scripts/smoke-tests.sh production

# 5. Document rollback reason
# Create incident report
# Update deployment notes
# Schedule post-mortem if needed
```

### 3.3 Emergency Hotfix Deployment

**Hotfix Process:**
```bash
# 1. Create hotfix branch from production
git checkout production
git checkout -b hotfix/critical-security-fix

# 2. Implement minimal fix
# Make necessary changes
git add .
git commit -m "hotfix: address critical security vulnerability"

# 3. Emergency review process
# Get security team approval
# Fast-track peer review

# 4. Deploy directly to production
git push origin hotfix/critical-security-fix
# Trigger emergency deployment pipeline

# 5. Monitor closely
# Watch for any adverse effects
# Verify fix addresses the issue

# 6. Backport to main branch
git checkout main
git merge hotfix/critical-security-fix
git push origin main
```

---

## 4. Infrastructure Scaling Operations

### 4.1 Manual Scaling Procedures

**API Service Scaling:**
```bash
# Check current capacity
aws ecs describe-services --cluster weather-forecast-prod --service api \
  --query 'services[0].[runningCount,desiredCount]'

# Scale up for high traffic
aws ecs update-service --cluster weather-forecast-prod --service api --desired-count 8

# Scale down during low traffic
aws ecs update-service --cluster weather-forecast-prod --service api --desired-count 3

# Monitor scaling events
aws ecs describe-services --cluster weather-forecast-prod --service api \
  --query 'services[0].events[0:5]'
```

**Auto-scaling Configuration:**
```bash
# Check auto-scaling policies
aws application-autoscaling describe-scaling-policies --service-namespace ecs

# Update scaling policy if needed
aws application-autoscaling put-scaling-policy \
  --policy-name api-cpu-scaling \
  --policy-type TargetTrackingScaling \
  --service-namespace ecs \
  --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/weather-forecast-prod/api \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 70.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
    }
  }'
```

### 4.2 Load Testing and Capacity Planning

**Pre-event Scaling (Weather Emergency):**
```bash
# Prepare for high traffic event
# Scale up infrastructure
aws ecs update-service --cluster weather-forecast-prod --service api --desired-count 10
aws ecs update-service --cluster weather-forecast-prod --service frontend --desired-count 5

# Pre-warm FAISS indices
curl -H "Authorization: Bearer $API_TOKEN" \
  "https://api.adelaide-weather.com/forecast?horizon=6h&vars=t2m,cape,u,v"
curl -H "Authorization: Bearer $API_TOKEN" \
  "https://api.adelaide-weather.com/forecast?horizon=24h&vars=t2m,cape,u,v"

# Monitor resource utilization
watch -n 5 'aws ecs describe-services --cluster weather-forecast-prod --services api frontend'
```

**Load Testing Execution:**
```bash
# Run load test
cd tests/load
./run-load-tests.sh --environment production --duration 10m --users 1000

# Monitor during load test
# Watch CloudWatch metrics
# Check application logs
# Verify auto-scaling triggers

# Analyze results
cat load-test-results.json | jq '.summary'
```

---

## 5. Security Incident Response

### 5.1 Security Alert Investigation

**Authentication Failure Investigation:**
```bash
# Check authentication failure patterns
aws logs insights start-query \
  --log-group-name "/ecs/weather-forecast-prod/api" \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string '
    fields @timestamp, client_ip, user_agent, token_hint
    | filter @message like /authentication_attempt/
    | filter success = false
    | stats count() by client_ip
    | sort count desc
    | limit 20
  '

# Analyze suspicious IPs
aws logs insights start-query \
  --log-group-name "/ecs/weather-forecast-prod/api" \
  --start-time $(date -d '24 hours ago' +%s) \
  --end-time $(date +%s) \
  --query-string '
    fields @timestamp, client_ip, user_agent, method, endpoint
    | filter client_ip = "SUSPICIOUS_IP"
    | sort @timestamp desc
  '
```

**Security Violation Response:**
```bash
# Check for injection attempts
aws logs insights start-query \
  --log-group-name "/ecs/weather-forecast-prod/api" \
  --start-time $(date -d '2 hours ago' +%s) \
  --end-time $(date +%s) \
  --query-string '
    fields @timestamp, @message
    | filter @message like /security_violation/
    | filter violation_type = "injection_attempt"
    | sort @timestamp desc
  '

# Block malicious IPs
aws ec2 create-security-group --group-name emergency-block --description "Emergency IP blocking"
aws ec2 authorize-security-group-egress --group-id sg-xxxxxxxx --protocol tcp --port 443 --source-group MALICIOUS_IP/32

# Review and update WAF rules if applicable
# Document incident for security team review
```

### 5.2 Token Management and Rotation

**Emergency Token Rotation:**
```bash
# Generate new API token
NEW_TOKEN=$(openssl rand -hex 32)

# Update Kubernetes secret
kubectl create secret generic api-secrets \
  --from-literal=API_TOKEN=$NEW_TOKEN \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart services to pick up new token
kubectl rollout restart deployment/api-deployment -n weather-forecast-prod

# Verify new token works
curl -H "Authorization: Bearer $NEW_TOKEN" \
  "https://api.adelaide-weather.com/health"

# Notify API users of token change
# Update documentation with new token
```

---

## 6. Data Backup and Recovery Operations

### 6.1 Backup Verification Procedures

**Daily Backup Verification:**
```bash
#!/bin/bash
# Verify backup integrity

echo "=== Backup Verification $(date) ==="

# 1. Check FAISS indices backup
echo "1. FAISS Indices Backup:"
aws s3 ls s3://weather-forecast-indices-backup/$(date +%Y%m%d)/ --human-readable

# 2. Check outcomes data backup  
echo "2. Outcomes Data Backup:"
aws s3 ls s3://weather-forecast-outcomes-backup/$(date +%Y%m%d)/ --human-readable

# 3. Check weather data backup
echo "3. Weather Data Backup:"
aws s3 ls s3://weather-forecast-data-backup/$(date +%Y%m%d)/ --human-readable

# 4. Verify backup completeness
EXPECTED_FILES=(
  "outcomes/outcomes_6h.npy"
  "outcomes/outcomes_12h.npy"
  "outcomes/outcomes_24h.npy"
  "outcomes/outcomes_48h.npy"
  "indices/faiss_6h_flatip.faiss"
  "indices/faiss_12h_flatip.faiss"
  "indices/faiss_24h_flatip.faiss"
  "indices/faiss_48h_flatip.faiss"
)

for file in "${EXPECTED_FILES[@]}"; do
  if aws s3api head-object --bucket weather-forecast-data-backup --key "$(date +%Y%m%d)/$file" &>/dev/null; then
    echo "   ✅ $file"
  else
    echo "   ❌ $file - MISSING"
  fi
done
```

### 6.2 Data Recovery Procedures

**Application Data Recovery:**
```bash
# 1. Identify recovery point
RECOVERY_DATE="20241029"  # Format: YYYYMMDD

# 2. Download backup data
mkdir -p /tmp/recovery/$RECOVERY_DATE
aws s3 sync s3://weather-forecast-data-backup/$RECOVERY_DATE/ /tmp/recovery/$RECOVERY_DATE/

# 3. Verify backup integrity
cd /tmp/recovery/$RECOVERY_DATE
for file in outcomes/*.npy; do
  if python -c "import numpy as np; np.load('$file')"; then
    echo "✅ $file integrity verified"
  else
    echo "❌ $file corrupted"
  fi
done

# 4. Stop application services
kubectl scale deployment api-deployment --replicas=0 -n weather-forecast-prod

# 5. Replace data files
kubectl cp /tmp/recovery/$RECOVERY_DATE/outcomes/ weather-forecast-prod/api-pod:/app/outcomes/
kubectl cp /tmp/recovery/$RECOVERY_DATE/indices/ weather-forecast-prod/api-pod:/app/indices/

# 6. Restart services
kubectl scale deployment api-deployment --replicas=3 -n weather-forecast-prod

# 7. Verify recovery
curl -f https://api.adelaide-weather.com/health
curl -H "Authorization: Bearer $API_TOKEN" \
  "https://api.adelaide-weather.com/forecast?horizon=24h&vars=t2m"
```

**Infrastructure Recovery (Complete Rebuild):**
```bash
# 1. Clone infrastructure repository
git clone https://github.com/organization/weather-forecast-infrastructure.git
cd weather-forecast-infrastructure

# 2. Initialize Terraform
terraform init

# 3. Plan infrastructure recreation
terraform plan -var-file="environments/prod/terraform.tfvars"

# 4. Apply infrastructure (with approval)
terraform apply -var-file="environments/prod/terraform.tfvars"

# 5. Deploy application
./deploy.sh production

# 6. Restore data from backups
./scripts/restore-data.sh --date $RECOVERY_DATE

# 7. Verify complete system functionality
./scripts/validate-deployment.sh production
```

---

## 7. Performance Issue Troubleshooting

### 7.1 High Latency Investigation

**Latency Troubleshooting Steps:**
```bash
# 1. Check current response times
curl -w "Response Time: %{time_total}s\n" -o /dev/null -s \
  "https://api.adelaide-weather.com/forecast?horizon=24h&vars=t2m"

# 2. Analyze response time distribution
aws logs insights start-query \
  --log-group-name "/ecs/weather-forecast-prod/api" \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string '
    fields @timestamp, response_time_ms
    | filter @message like /api_request_completed/
    | stats avg(response_time_ms), min(response_time_ms), max(response_time_ms), count() by bin(5m)
  '

# 3. Check for resource constraints
aws ecs describe-services --cluster weather-forecast-prod --service api
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=api Name=ClusterName,Value=weather-forecast-prod \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 --statistics Average,Maximum

# 4. Analyze FAISS index performance
curl -s https://api.adelaide-weather.com/health | jq '.checks.performance'
```

**Performance Optimization Actions:**
```bash
# 1. Scale up if resource constrained
aws ecs update-service --cluster weather-forecast-prod --service api --desired-count 6

# 2. Check for memory leaks
kubectl top pods -n weather-forecast-prod
kubectl describe pod <pod-name> -n weather-forecast-prod

# 3. Restart containers if memory leak detected
kubectl delete pod <pod-name> -n weather-forecast-prod

# 4. Enable detailed monitoring temporarily
kubectl set env deployment/api-deployment LOG_LEVEL=DEBUG -n weather-forecast-prod
```

### 7.2 High Error Rate Investigation

**Error Analysis Process:**
```bash
# 1. Check error rate by endpoint
aws logs insights start-query \
  --log-group-name "/ecs/weather-forecast-prod/api" \
  --start-time $(date -d '30 minutes ago' +%s) \
  --end-time $(date +%s) \
  --query-string '
    fields @timestamp, method, endpoint, status_code
    | filter status_code >= 400
    | stats count() by endpoint, status_code
    | sort count desc
  '

# 2. Analyze specific error patterns
aws logs insights start-query \
  --log-group-name "/ecs/weather-forecast-prod/api" \
  --start-time $(date -d '30 minutes ago' +%s) \
  --end-time $(date +%s) \
  --query-string '
    fields @timestamp, @message
    | filter @message like /ERROR/
    | sort @timestamp desc
    | limit 50
  '

# 3. Check for dependency failures
curl -s https://api.adelaide-weather.com/health | jq '.checks'

# 4. Verify data integrity
curl -H "Authorization: Bearer $API_TOKEN" \
  "https://api.adelaide-weather.com/forecast?horizon=6h&vars=t2m" | jq '.error // "No error"'
```

---

## 8. Third-Party Service Dependencies

### 8.1 External Dependencies

**Primary Dependencies:**
- **AWS Services:** ECS, ALB, CloudWatch, S3, IAM
- **Container Registry:** GitHub Container Registry (ghcr.io)
- **Monitoring:** Prometheus, Grafana
- **DNS:** Route53 or CloudFlare
- **SSL Certificates:** AWS Certificate Manager

**Dependency Health Checks:**
```bash
# 1. Check AWS service status
aws sts get-caller-identity
aws ecs describe-clusters --clusters weather-forecast-prod

# 2. Check container registry access
docker login ghcr.io
docker pull ghcr.io/organization/weather-forecast-api:latest

# 3. Check monitoring services
curl -f http://prometheus.adelaide-weather.com/-/healthy
curl -f http://grafana.adelaide-weather.com/api/health

# 4. Check DNS resolution
nslookup adelaide-weather.com
nslookup api.adelaide-weather.com
```

### 8.2 Dependency Failure Response

**AWS Service Outage:**
```bash
# Check AWS status page
curl -s https://status.aws.amazon.com/

# Implement emergency procedures:
# 1. Switch to backup region if configured
# 2. Use static fallback responses if possible
# 3. Communicate service degradation to users
# 4. Monitor AWS status for restoration updates
```

**Container Registry Outage:**
```bash
# Use cached container images
docker images | grep weather-forecast

# Deploy from local registry if available
docker tag ghcr.io/organization/weather-forecast-api:latest localhost:5000/weather-forecast-api:latest
docker push localhost:5000/weather-forecast-api:latest

# Update Kubernetes deployment to use local registry temporarily
kubectl set image deployment/api-deployment api=localhost:5000/weather-forecast-api:latest -n weather-forecast-prod
```

---

## 9. Maintenance Windows and Updates

### 9.1 Scheduled Maintenance Procedures

**Monthly Maintenance Window:**
- **Schedule:** First Sunday of each month, 2:00 AM - 4:00 AM UTC
- **Duration:** 2 hours maximum
- **Communication:** 48-hour advance notice via email and status page

**Maintenance Tasks:**
```bash
# 1. System updates and patches
# Update container base images
# Apply security patches
# Update dependencies

# 2. Infrastructure maintenance
# Review and optimize auto-scaling policies
# Clean up old logs and metrics
# Verify backup integrity

# 3. Performance optimization
# Analyze and optimize FAISS indices
# Review and tune resource allocations
# Clean up temporary files

# 4. Security updates
# Rotate access tokens if needed
# Review and update security groups
# Update SSL certificates if needed
```

**Pre-Maintenance Checklist:**
- [ ] Backup current system state
- [ ] Test rollback procedures
- [ ] Communicate maintenance window to stakeholders
- [ ] Prepare rollback plan
- [ ] Schedule maintenance window in monitoring systems
- [ ] Verify emergency contact availability

**Post-Maintenance Verification:**
```bash
# 1. Complete system health check
./scripts/health-check.sh production

# 2. Performance verification
./scripts/performance-test.sh production

# 3. Security validation
./scripts/security-scan.sh production

# 4. Update documentation
# Document any changes made
# Update operational procedures if needed
```

### 9.2 Emergency Maintenance

**Security Patch Deployment:**
```bash
# 1. Assess severity and impact
# Review security advisory
# Determine if emergency deployment needed

# 2. Prepare emergency patch
git checkout -b emergency/security-patch-CVE-2024-XXXX
# Apply security patch
git commit -m "emergency: apply security patch for CVE-2024-XXXX"

# 3. Fast-track deployment
# Skip normal testing for critical security patches
./deploy.sh production --emergency

# 4. Monitor post-deployment
# Watch for any adverse effects
# Verify patch effectiveness
```

---

## 10. Contact Information and Escalation

### 10.1 Emergency Contacts

**Primary On-Call Rotation:**
- **DevOps Engineer:** Available 24/7 via PagerDuty
- **Lead Engineer:** Escalation after 15 minutes
- **Engineering Manager:** Escalation after 30 minutes
- **CTO:** Escalation for critical business impact

**Communication Channels:**
- **Slack:** #incident-response (immediate)
- **PagerDuty:** Critical alerts (immediate)
- **Email:** team-devops@company.com (non-urgent)
- **Status Page:** https://status.adelaide-weather.com

### 10.2 Escalation Matrix

**Incident Severity Levels:**

**Critical (Severity 1):**
- Complete service outage
- Security breach
- Data loss or corruption
- **Response Time:** Immediate (< 5 minutes)
- **Escalation:** PagerDuty → On-call → Lead → Manager → CTO

**High (Severity 2):**
- Significant performance degradation
- Partial service outage
- Security vulnerability
- **Response Time:** 15 minutes
- **Escalation:** Slack → On-call → Lead → Manager

**Medium (Severity 3):**
- Minor performance issues
- Non-critical feature failures
- **Response Time:** 2 hours
- **Escalation:** Slack → Team discussion

**Low (Severity 4):**
- Cosmetic issues
- Enhancement requests
- **Response Time:** Next business day
- **Escalation:** Email → Product backlog

### 10.3 External Vendor Contacts

**AWS Support:**
- **Support Level:** Business Support
- **Contact:** AWS Support Console
- **Phone:** 1-800-AWS-SUPPORT
- **Emergency:** Open critical support case

**Domain/DNS Provider:**
- **Provider:** CloudFlare/Route53
- **Contact:** Support portal
- **Emergency:** Phone support line

**Monitoring Services:**
- **PagerDuty:** support@pagerduty.com
- **Status Page:** Support portal

---

## Appendix

### A. Command Reference Quick Sheet

```bash
# Health Checks
curl -f https://api.adelaide-weather.com/health
curl -f https://adelaide-weather.com

# Service Status
aws ecs describe-services --cluster weather-forecast-prod --services api frontend
kubectl get pods -n weather-forecast-prod

# Scaling
aws ecs update-service --cluster weather-forecast-prod --service api --desired-count <N>
kubectl scale deployment api-deployment --replicas=<N> -n weather-forecast-prod

# Logs
aws logs tail --log-group-name "/ecs/weather-forecast-prod/api" --since 10m
kubectl logs -f deployment/api-deployment -n weather-forecast-prod

# Metrics
aws cloudwatch get-metric-statistics --namespace AWS/ECS --metric-name CPUUtilization
```

### B. Troubleshooting Checklist

**Service Down:**
- [ ] Check health endpoints
- [ ] Verify ECS service status
- [ ] Check load balancer health
- [ ] Review application logs
- [ ] Check resource utilization
- [ ] Verify network connectivity

**Performance Issues:**
- [ ] Check response times
- [ ] Review CPU/memory usage
- [ ] Analyze request patterns
- [ ] Check FAISS index health
- [ ] Review auto-scaling events
- [ ] Verify cache performance

**Deployment Issues:**
- [ ] Check deployment status
- [ ] Review rollout progress
- [ ] Verify container health
- [ ] Check environment variables
- [ ] Review image availability
- [ ] Verify network policies

---

**Document Maintained By:** DevOps Infrastructure Team  
**Last Updated:** 2025-10-29  
**Review Schedule:** Monthly  
**Next Review Date:** 2025-11-29  
**Document Version:** 1.0.0