# Adelaide Weather Forecast - Deployment Runbook

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Pre-Deployment Checklist](#pre-deployment-checklist)
4. [Deployment Procedures](#deployment-procedures)
5. [Monitoring and Validation](#monitoring-and-validation)
6. [Rollback Procedures](#rollback-procedures)
7. [Troubleshooting](#troubleshooting)
8. [Emergency Procedures](#emergency-procedures)
9. [Post-Deployment Tasks](#post-deployment-tasks)
10. [Contact Information](#contact-information)

## Overview

This runbook provides comprehensive procedures for deploying the Adelaide Weather Forecast application across all environments. The application uses a microservices architecture with blue-green deployment strategy for production deployments.

### Application Components
- **API Service**: FastAPI backend providing weather forecast endpoints
- **Frontend Service**: Next.js web application
- **Redis Cache**: In-memory caching for performance optimization
- **PostgreSQL Database**: Persistent data storage
- **Monitoring Stack**: Prometheus, Grafana, AlertManager

### Environments
- **Development**: Feature branch deployments and testing
- **Staging**: Pre-production validation and integration testing
- **Production**: Live production environment with high availability

## Architecture

### Deployment Strategy
- **Development/Staging**: Rolling deployments with minimal downtime
- **Production**: Blue-Green deployments with zero downtime
- **Emergency**: Fast rollback capability with automated health checks

### Infrastructure
- **Kubernetes**: Container orchestration (EKS on AWS)
- **Helm**: Package management and templating
- **Terraform**: Infrastructure as Code
- **GitHub Actions**: CI/CD automation

## Pre-Deployment Checklist

### 🔍 Staging Validation
- [ ] Staging deployment completed successfully
- [ ] All integration tests passing
- [ ] Performance tests within acceptable limits
- [ ] Security scans completed with no critical issues
- [ ] Load testing results acceptable

### 🛡️ Security Checks
- [ ] Container images scanned for vulnerabilities
- [ ] No critical security issues in dependencies
- [ ] Secrets properly configured and rotated if needed
- [ ] Access controls reviewed and updated

### 📊 Monitoring Readiness
- [ ] Monitoring dashboards updated
- [ ] Alert rules configured and tested
- [ ] On-call schedule confirmed
- [ ] Runbook procedures reviewed

### 🧪 Testing Verification
- [ ] Unit tests: 95%+ coverage
- [ ] Integration tests: All passing
- [ ] End-to-end tests: All critical paths validated
- [ ] Performance tests: Within SLA requirements

### 📋 Change Management
- [ ] Change request approved (if required)
- [ ] Deployment window scheduled
- [ ] Stakeholders notified
- [ ] Rollback plan confirmed

## Deployment Procedures

### 1. Automated CI/CD Pipeline Deployment

The primary deployment method is through GitHub Actions workflows:

#### For Staging Deployments
```bash
# Triggered automatically on develop branch
git checkout develop
git pull origin develop
git push origin develop
```

#### For Production Deployments
```bash
# Manual trigger via GitHub Actions UI
# Go to: Actions → Production Deployment → Run workflow
# Select parameters:
# - deployment_strategy: blue-green
# - image_tag: [validated tag from staging]
# - approval_required: true
# - rollback_timeout: 30
```

### 2. Manual Blue-Green Deployment

For manual deployments or emergency situations:

```bash
# Navigate to deployment scripts
cd ops/deployment

# Execute blue-green deployment
./blue-green-deployment.sh \
  --image-tag v1.2.3 \
  --environment production \
  --cleanup

# For dry-run testing
./blue-green-deployment.sh \
  --image-tag v1.2.3 \
  --environment production \
  --dry-run
```

### 3. Staging Deployment

```bash
# Deploy to staging
./blue-green-deployment.sh \
  --image-tag v1.2.3 \
  --environment staging \
  --namespace adelaide-weather-staging
```

### 4. Database Migrations

Database migrations are handled automatically during application startup, but for manual execution:

```bash
# Connect to database pod
kubectl exec -it deployment/adelaide-weather-api -n adelaide-weather-production -- bash

# Run migrations manually (if needed)
python -m alembic upgrade head

# Check migration status
python -m alembic current
```

## Monitoring and Validation

### 1. Deployment Health Validation

Use the automated validation script:

```bash
# Full validation suite
./deployment-validation.sh full \
  --environment production \
  --load-test \
  --report-file validation-report.json

# Quick smoke test
./deployment-validation.sh smoke \
  --environment production

# Performance validation
./deployment-validation.sh performance \
  --environment production \
  --url https://adelaide-weather.com
```

### 2. Manual Health Checks

#### API Health Check
```bash
curl -f https://adelaide-weather.com/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-10-29T12:00:00Z",
  "version": "v1.2.3",
  "database": "healthy",
  "redis": "healthy"
}
```

#### Frontend Health Check
```bash
curl -f https://adelaide-weather.com/
```

Should return HTTP 200 with the application homepage.

#### Database Connectivity
```bash
curl -f https://adelaide-weather.com/api/health/database
```

#### Redis Connectivity
```bash
curl -f https://adelaide-weather.com/api/health/redis
```

### 3. Monitoring Dashboards

- **Application Metrics**: https://grafana.adelaide-weather.com/d/app-metrics
- **Infrastructure Metrics**: https://grafana.adelaide-weather.com/d/infra-metrics
- **SLO Dashboard**: https://grafana.adelaide-weather.com/d/slo-metrics

### 4. Key Metrics to Monitor

#### Application Metrics
- Response time (p95 < 500ms)
- Error rate (< 1%)
- Throughput (requests/second)
- Active users

#### Infrastructure Metrics
- CPU utilization (< 70%)
- Memory utilization (< 80%)
- Disk utilization (< 85%)
- Network latency

#### Business Metrics
- Forecast accuracy
- User engagement
- API usage patterns

## Rollback Procedures

### 1. Automated Rollback

For blue-green deployments, rollback is automatic if health checks fail. Manual rollback can be triggered:

```bash
# Emergency rollback (fastest)
./rollback-procedures.sh emergency \
  --reason "Critical production issue"

# Application rollback
./rollback-procedures.sh application \
  --target-version v1.2.2 \
  --notify

# Traffic rollback only
./rollback-procedures.sh traffic \
  --force
```

### 2. Helm Rollback

```bash
# List release history
helm history adelaide-weather -n adelaide-weather-production

# Rollback to previous version
helm rollback adelaide-weather 1 -n adelaide-weather-production

# Rollback to specific version
helm rollback adelaide-weather 3 -n adelaide-weather-production
```

### 3. Database Rollback

⚠️ **WARNING**: Database rollbacks are destructive and should only be performed in extreme circumstances.

```bash
# Create database backup first
kubectl exec -it statefulset/postgresql-primary -n adelaide-weather-production -- \
  pg_dump -U admin adelaide_weather > backup-$(date +%Y%m%d-%H%M%S).sql

# Database rollback (manual process)
./rollback-procedures.sh database \
  --target-version v1.2.2 \
  --force
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Pod Stuck in Pending State

**Symptoms:**
```bash
kubectl get pods -n adelaide-weather-production
# NAME                               READY   STATUS    RESTARTS   AGE
# adelaide-weather-api-xxx-xxx       0/1     Pending   0          5m
```

**Diagnosis:**
```bash
kubectl describe pod adelaide-weather-api-xxx-xxx -n adelaide-weather-production
```

**Common Causes:**
- Insufficient cluster resources
- Node affinity/anti-affinity constraints
- Pod security policy violations

**Resolution:**
```bash
# Check cluster capacity
kubectl top nodes

# Scale cluster if needed (via Terraform or AWS Console)
# Restart deployment
kubectl rollout restart deployment/adelaide-weather-api -n adelaide-weather-production
```

#### 2. High Error Rate

**Symptoms:**
- HTTP 5xx errors in monitoring
- Application logs showing exceptions

**Diagnosis:**
```bash
# Check application logs
kubectl logs deployment/adelaide-weather-api -n adelaide-weather-production --tail=100

# Check resource utilization
kubectl top pods -n adelaide-weather-production
```

**Resolution:**
```bash
# Scale up if resource constrained
kubectl scale deployment adelaide-weather-api --replicas=5 -n adelaide-weather-production

# Restart if application error
kubectl rollout restart deployment/adelaide-weather-api -n adelaide-weather-production
```

#### 3. Database Connection Issues

**Symptoms:**
- Database health check failing
- Connection timeout errors

**Diagnosis:**
```bash
# Check database connectivity
kubectl exec -it deployment/adelaide-weather-api -n adelaide-weather-production -- \
  curl database-endpoint:5432

# Check database status
aws rds describe-db-instances --db-instance-identifier adelaide-weather-production-db
```

**Resolution:**
```bash
# Restart database if needed (via AWS Console)
# Update database credentials if expired
kubectl create secret generic db-credentials \
  --from-literal=username=admin \
  --from-literal=password=new-password \
  -n adelaide-weather-production
```

#### 4. Ingress/Load Balancer Issues

**Symptoms:**
- External access failing
- DNS resolution issues

**Diagnosis:**
```bash
# Check ingress status
kubectl get ingress -n adelaide-weather-production
kubectl describe ingress adelaide-weather-ingress -n adelaide-weather-production

# Check ALB status
aws elbv2 describe-load-balancers
```

**Resolution:**
```bash
# Restart ingress controller
kubectl rollout restart deployment/aws-load-balancer-controller -n kube-system

# Update DNS if needed
# Verify SSL certificate validity
```

## Emergency Procedures

### 🚨 Critical Production Issues

#### Immediate Response (0-5 minutes)
1. **Assess Impact**: Check monitoring dashboards and error rates
2. **Notify Team**: Alert on-call engineer and escalate if needed
3. **Emergency Rollback**: If recent deployment, immediately rollback
4. **Traffic Diversion**: Consider diverting traffic if multi-region

#### Emergency Rollback
```bash
# Fastest rollback - bypass all checks
./rollback-procedures.sh emergency \
  --reason "P0 production incident" \
  --notify

# Verify rollback success
./deployment-validation.sh smoke --environment production
```

#### Service Degradation Response
1. **Scale Resources**: Increase replica count for affected services
2. **Rate Limiting**: Enable aggressive rate limiting to protect backend
3. **Cache Warming**: Pre-warm caches to reduce database load
4. **Feature Flags**: Disable non-critical features

```bash
# Emergency scaling
kubectl scale deployment adelaide-weather-api --replicas=10 -n adelaide-weather-production
kubectl scale deployment adelaide-weather-frontend --replicas=8 -n adelaide-weather-production
```

### 🔧 Maintenance Windows

#### Planned Maintenance Process
1. **Pre-Maintenance**: 
   - Notify users via status page
   - Scale up resources for faster recovery
   - Create fresh backups

2. **During Maintenance**:
   - Monitor all systems continuously
   - Have rollback plan ready
   - Test functionality after each change

3. **Post-Maintenance**:
   - Validate all services
   - Monitor for 30 minutes minimum
   - Update status page

## Post-Deployment Tasks

### ✅ Immediate Post-Deployment (0-30 minutes)
- [ ] Verify all health checks pass
- [ ] Monitor error rates and response times
- [ ] Check critical user journeys
- [ ] Validate monitoring and alerting
- [ ] Update deployment tracking

### 📊 Extended Monitoring (30 minutes - 2 hours)
- [ ] Monitor business metrics
- [ ] Check performance trends
- [ ] Validate database performance
- [ ] Review security logs
- [ ] Monitor user feedback

### 📝 Documentation Updates
- [ ] Update deployment logs
- [ ] Document any issues encountered
- [ ] Update runbook if needed
- [ ] Share lessons learned with team
- [ ] Update monitoring dashboards

## Contact Information

### On-Call Escalation
1. **Primary On-Call**: Check PagerDuty schedule
2. **Secondary On-Call**: Check PagerDuty schedule
3. **Engineering Manager**: [Contact info]
4. **DevOps Lead**: [Contact info]

### Notification Channels
- **Slack**: #production-alerts, #deployments
- **Email**: prod-alerts@company.com
- **PagerDuty**: Adelaide Weather Forecast Service
- **Status Page**: https://status.adelaide-weather.com

### External Dependencies
- **AWS Support**: [Support case portal]
- **DNS Provider**: [Contact info]
- **CDN Provider**: [Contact info]
- **Monitoring SaaS**: [Contact info]

### Vendor Escalation
- **Database Issues**: AWS RDS Support
- **Kubernetes Issues**: AWS EKS Support
- **Load Balancer Issues**: AWS ALB Support
- **DNS Issues**: Route53 Support

---

## Appendix

### A. Useful Commands

#### Kubernetes Operations
```bash
# Get all resources
kubectl get all -n adelaide-weather-production

# Check pod logs
kubectl logs -f deployment/adelaide-weather-api -n adelaide-weather-production

# Port forward for debugging
kubectl port-forward svc/adelaide-weather-api 8080:8000 -n adelaide-weather-production

# Execute into pod
kubectl exec -it deployment/adelaide-weather-api -n adelaide-weather-production -- bash

# Check resource usage
kubectl top pods -n adelaide-weather-production
kubectl top nodes
```

#### Helm Operations
```bash
# List releases
helm list -n adelaide-weather-production

# Get release status
helm status adelaide-weather -n adelaide-weather-production

# Get release values
helm get values adelaide-weather -n adelaide-weather-production

# Upgrade release
helm upgrade adelaide-weather ./helm/adelaide-weather-forecast \
  --namespace adelaide-weather-production \
  --values production-values.yaml
```

#### Terraform Operations
```bash
# Plan infrastructure changes
cd terraform/environments/production
terraform plan

# Apply infrastructure changes
terraform apply

# Check infrastructure state
terraform show
terraform state list
```

### B. Configuration Templates

#### Emergency Scaling Configuration
```yaml
# emergency-scale.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: adelaide-weather-api
spec:
  replicas: 10
  template:
    spec:
      containers:
      - name: api
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
```

#### Rate Limiting Configuration
```yaml
# rate-limit-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: rate-limit-config
data:
  rate-limit.conf: |
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
```

### C. Monitoring Queries

#### Prometheus Queries
```promql
# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# Response time 95th percentile
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Pod memory usage
container_memory_usage_bytes{pod=~"adelaide-weather-.*"} / container_spec_memory_limit_bytes * 100

# Database connections
pg_stat_database_numbackends{datname="adelaide_weather"}
```

### D. Security Procedures

#### Credential Rotation
```bash
# Database password rotation
aws rds modify-db-instance \
  --db-instance-identifier adelaide-weather-production-db \
  --master-user-password NewSecurePassword123

# API key rotation
kubectl create secret generic api-secrets \
  --from-literal=api-key=new-api-key \
  --dry-run=client -o yaml | kubectl apply -f -
```

#### Certificate Management
```bash
# Check certificate expiry
openssl x509 -in cert.pem -text -noout | grep "Not After"

# Request new certificate via ACM
aws acm request-certificate \
  --domain-name adelaide-weather.com \
  --validation-method DNS
```

---

**Document Version**: 1.0  
**Last Updated**: 2024-10-29  
**Next Review**: 2024-11-29  
**Owner**: DevOps Team  
**Approved By**: Engineering Manager