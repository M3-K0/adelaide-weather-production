# Adelaide Weather Forecast - Operations Runbook

## Emergency Contacts & Escalation

### Primary Contacts
- **On-Call Engineer**: +1-XXX-XXX-XXXX
- **DevOps Lead**: devops@yourcompany.com
- **Development Lead**: dev@yourcompany.com
- **Product Owner**: product@yourcompany.com

### Escalation Matrix
1. **P1 (Critical)**: Service completely down
   - Response: 15 minutes
   - Contact: On-call engineer immediately
   - Escalate to: DevOps Lead after 30 minutes

2. **P2 (High)**: Significant service degradation
   - Response: 1 hour
   - Contact: On-call engineer
   - Escalate to: DevOps Lead after 2 hours

3. **P3 (Medium)**: Minor issues, some features affected
   - Response: 4 hours
   - Contact: Development team
   - Escalate to: DevOps Lead next business day

## Service Overview

### Application Components
- **Frontend**: Next.js application serving weather forecast UI
- **API**: FastAPI backend providing forecast data
- **Load Balancer**: AWS ALB distributing traffic
- **Container Platform**: ECS Fargate with auto-scaling
- **Monitoring**: CloudWatch metrics and alarms

### Key URLs
- **Production**: https://weather-forecast.dev
- **Staging**: https://staging.weather-forecast.dev
- **API**: https://api.weather-forecast.dev
- **Health Checks**: https://api.weather-forecast.dev/health

## Common Incident Response Procedures

### 1. Service Completely Down (P1)

#### Symptoms
- Health check endpoints returning 5XX errors
- Users unable to access the application
- All monitoring alerts firing

#### Immediate Actions
1. **Verify the issue**:
   ```bash
   curl -I https://weather-forecast.dev
   curl -I https://api.weather-forecast.dev/health
   ```

2. **Check AWS Service Health**:
   - Visit AWS Service Health Dashboard
   - Check for regional outages

3. **Check ECS Service Status**:
   ```bash
   aws ecs describe-services \
     --cluster weather-forecast-prod-cluster \
     --services weather-forecast-prod-api weather-forecast-prod-frontend
   ```

4. **Check Target Group Health**:
   ```bash
   aws elbv2 describe-target-health \
     --target-group-arn arn:aws:elasticloadbalancing:us-east-1:ACCOUNT:targetgroup/weather-forecast-prod-api-tg/XXXXXXXXX
   ```

#### Investigation Steps
1. **Check Recent Deployments**:
   - Review GitHub Actions for recent deployments
   - Check if any infrastructure changes were made

2. **Review Logs**:
   ```bash
   aws logs filter-log-events \
     --log-group-name /ecs/weather-forecast-prod/api \
     --start-time $(date -d '1 hour ago' +%s)000
   ```

3. **Check Resource Utilization**:
   - CPU and memory usage in CloudWatch
   - Auto-scaling activities

#### Resolution Steps
1. **If recent deployment caused issue**:
   ```bash
   # Rollback to previous task definition
   aws ecs update-service \
     --cluster weather-forecast-prod-cluster \
     --service weather-forecast-prod-api \
     --task-definition weather-forecast-prod-api:PREVIOUS_REVISION
   ```

2. **If infrastructure issue**:
   ```bash
   # Force new deployment
   aws ecs update-service \
     --cluster weather-forecast-prod-cluster \
     --service weather-forecast-prod-api \
     --force-new-deployment
   ```

3. **If auto-scaling issue**:
   ```bash
   # Manually scale up
   aws ecs update-service \
     --cluster weather-forecast-prod-cluster \
     --service weather-forecast-prod-api \
     --desired-count 5
   ```

### 2. High Response Times (P2)

#### Symptoms
- Response times > 5 seconds
- User complaints about slow performance
- CloudWatch alarms for high latency

#### Investigation Steps
1. **Check Current Response Times**:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/ApplicationELB \
     --metric-name TargetResponseTime \
     --start-time $(date -d '1 hour ago' --iso-8601) \
     --end-time $(date --iso-8601) \
     --period 300 \
     --statistics Average
   ```

2. **Check Resource Utilization**:
   - CPU and memory usage patterns
   - Database performance (if applicable)
   - Network throughput

3. **Review Recent Traffic Patterns**:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/ApplicationELB \
     --metric-name RequestCount \
     --start-time $(date -d '4 hours ago' --iso-8601) \
     --end-time $(date --iso-8601) \
     --period 300 \
     --statistics Sum
   ```

#### Resolution Steps
1. **Scale up services**:
   ```bash
   aws ecs update-service \
     --cluster weather-forecast-prod-cluster \
     --service weather-forecast-prod-api \
     --desired-count 6
   ```

2. **Check for resource contention**:
   - Review container resource limits
   - Check for memory leaks or CPU spikes

3. **Enable additional monitoring**:
   ```bash
   python scripts/setup_deployment_monitoring.py --environment prod --duration 1h
   ```

### 3. High Error Rates (P2)

#### Symptoms
- Increased 4XX or 5XX error rates
- Application errors in logs
- User-reported functionality issues

#### Investigation Steps
1. **Check Error Rates**:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/ApplicationELB \
     --metric-name HTTPCode_Target_5XX_Count \
     --start-time $(date -d '1 hour ago' --iso-8601) \
     --end-time $(date --iso-8601) \
     --period 300 \
     --statistics Sum
   ```

2. **Review Application Logs**:
   ```bash
   aws logs filter-log-events \
     --log-group-name /ecs/weather-forecast-prod/api \
     --filter-pattern "ERROR" \
     --start-time $(date -d '1 hour ago' +%s)000
   ```

3. **Check Specific Error Patterns**:
   ```bash
   aws logs filter-log-events \
     --log-group-name /ecs/weather-forecast-prod/api \
     --filter-pattern '"status_code": 500' \
     --start-time $(date -d '1 hour ago' +%s)000
   ```

#### Resolution Steps
1. **If configuration error**:
   - Review environment variables
   - Check service configuration

2. **If dependency failure**:
   - Check external API availability
   - Review database connectivity

3. **If code error**:
   - Review recent code changes
   - Consider rollback if necessary

### 4. Auto-Scaling Issues (P3)

#### Symptoms
- Services not scaling up during high load
- Unexpected scaling down during peak hours
- Resource utilization not matching scale

#### Investigation Steps
1. **Check Auto-Scaling Configuration**:
   ```bash
   aws application-autoscaling describe-scaling-policies \
     --service-namespace ecs \
     --resource-id service/weather-forecast-prod-cluster/weather-forecast-prod-api
   ```

2. **Review Scaling Activities**:
   ```bash
   aws application-autoscaling describe-scaling-activities \
     --service-namespace ecs \
     --resource-id service/weather-forecast-prod-cluster/weather-forecast-prod-api
   ```

3. **Check Metrics**:
   - CPU utilization trends
   - Memory utilization trends
   - Request count patterns

#### Resolution Steps
1. **Adjust scaling policies**:
   ```bash
   aws application-autoscaling put-scaling-policy \
     --policy-name weather-forecast-prod-api-cpu-scaling \
     --service-namespace ecs \
     --resource-id service/weather-forecast-prod-cluster/weather-forecast-prod-api \
     --scalable-dimension ecs:service:DesiredCount \
     --policy-type TargetTrackingScaling \
     --target-tracking-scaling-policy-configuration file://scaling-policy.json
   ```

2. **Manual intervention**:
   ```bash
   # Temporarily scale up
   aws ecs update-service \
     --cluster weather-forecast-prod-cluster \
     --service weather-forecast-prod-api \
     --desired-count 4
   ```

## Monitoring & Alerting

### Key Metrics to Monitor

#### Application Performance
- **Response Time**: Target < 2 seconds (95th percentile)
- **Error Rate**: Target < 1% 5XX errors
- **Throughput**: Requests per minute
- **Availability**: Target > 99.9% uptime

#### Infrastructure Health
- **CPU Utilization**: Target < 70% average
- **Memory Utilization**: Target < 80% average
- **Disk I/O**: Monitor for bottlenecks
- **Network**: Monitor for bandwidth limits

#### Business Metrics
- **Forecast Accuracy**: Model performance metrics
- **User Engagement**: API usage patterns
- **Feature Usage**: Frontend interaction metrics

### Alert Thresholds

#### Critical Alerts (P1)
- **Service Down**: 0 healthy targets for 2 minutes
- **Error Spike**: > 20 5XX errors in 5 minutes
- **Complete Outage**: No successful requests for 5 minutes

#### Warning Alerts (P2)
- **High Latency**: > 5 seconds average for 10 minutes
- **High Error Rate**: > 5% error rate for 10 minutes
- **Resource Exhaustion**: > 85% CPU/Memory for 15 minutes

#### Info Alerts (P3)
- **Scaling Events**: Service scaled up/down
- **Deployment Events**: New version deployed
- **Performance Degradation**: > 3 seconds response time

### Dashboard URLs
- **CloudWatch**: https://console.aws.amazon.com/cloudwatch/home#dashboards:name=weather-forecast-prod
- **ECS Console**: https://console.aws.amazon.com/ecs/home#/clusters/weather-forecast-prod-cluster
- **ALB Console**: https://console.aws.amazon.com/ec2/v2/home#LoadBalancers:

## Maintenance Procedures

### Regular Maintenance Tasks

#### Daily
- [ ] Check service health via automated monitoring
- [ ] Review error logs for any unusual patterns
- [ ] Verify auto-scaling is functioning correctly

#### Weekly
- [ ] Review performance metrics and trends
- [ ] Check for security updates and patches
- [ ] Validate backup and recovery procedures
- [ ] Review resource utilization and costs

#### Monthly
- [ ] Update container images with latest security patches
- [ ] Review and update monitoring thresholds
- [ ] Test disaster recovery procedures
- [ ] Review access logs for security issues

#### Quarterly
- [ ] Comprehensive security review
- [ ] Performance testing and optimization
- [ ] Disaster recovery full test
- [ ] Documentation review and updates

### Planned Maintenance

#### Pre-Maintenance Checklist
1. [ ] Schedule maintenance window during low-traffic period
2. [ ] Notify stakeholders 24 hours in advance
3. [ ] Prepare rollback plan
4. [ ] Verify backup status
5. [ ] Test changes in staging environment

#### During Maintenance
1. [ ] Monitor service health continuously
2. [ ] Execute changes in planned order
3. [ ] Verify each step before proceeding
4. [ ] Document any deviations from plan

#### Post-Maintenance
1. [ ] Verify all services are healthy
2. [ ] Run smoke tests
3. [ ] Monitor for 2 hours post-maintenance
4. [ ] Document lessons learned
5. [ ] Update runbooks if needed

## Security Incident Response

### Types of Security Incidents
1. **Unauthorized Access**: Suspicious login attempts or access patterns
2. **Data Breach**: Unauthorized access to sensitive data
3. **DDoS Attack**: Unusual traffic patterns or service degradation
4. **Malware/Compromise**: Indicators of system compromise

### Immediate Response
1. **Contain**: Isolate affected systems
2. **Assess**: Determine scope and impact
3. **Eradicate**: Remove threats and vulnerabilities
4. **Recover**: Restore services safely
5. **Document**: Record all actions taken

### Escalation Contacts
- **Security Team**: security@yourcompany.com
- **Legal**: legal@yourcompany.com
- **Compliance**: compliance@yourcompany.com
- **External**: security-vendor@company.com

## Backup & Recovery

### Backup Strategy
- **Infrastructure**: Terraform state in S3 with versioning
- **Container Images**: Multi-region registry replication
- **Configuration**: GitOps with version control
- **Monitoring Data**: CloudWatch logs retention

### Recovery Procedures

#### Complete Environment Recovery
1. **Infrastructure Recreation**:
   ```bash
   cd infrastructure/environments/prod
   terraform init
   terraform plan
   terraform apply
   ```

2. **Application Deployment**:
   ```bash
   # Trigger deployment via GitHub Actions
   # Or manually update ECS services
   ```

3. **Verification**:
   ```bash
   # Test all endpoints
   curl https://weather-forecast.dev/health
   curl https://api.weather-forecast.dev/health
   ```

#### Partial Recovery
1. **Single Service Recovery**:
   ```bash
   aws ecs update-service \
     --cluster weather-forecast-prod-cluster \
     --service weather-forecast-prod-api \
     --force-new-deployment
   ```

2. **Database Recovery**: (If applicable)
   ```bash
   # Restore from snapshot
   aws rds restore-db-instance-from-db-snapshot \
     --db-instance-identifier weather-forecast-prod-restored \
     --db-snapshot-identifier weather-forecast-prod-snapshot-latest
   ```

## Performance Optimization

### Regular Optimization Tasks
1. **Container Right-Sizing**: Review CPU/memory allocation monthly
2. **Auto-Scaling Tuning**: Adjust thresholds based on traffic patterns
3. **Cache Optimization**: Review cache hit rates and strategies
4. **Database Optimization**: Query performance and indexing

### Performance Testing
```bash
# Load testing with artillery
artillery quick --count 100 --num 10 https://api.weather-forecast.dev/health

# API endpoint testing
curl -w "time_total: %{time_total}\n" https://api.weather-forecast.dev/forecast?lat=-34.9285&lon=138.6007
```

## Troubleshooting Tools

### AWS CLI Commands
```bash
# Service status
aws ecs describe-services --cluster CLUSTER --services SERVICE

# Task logs
aws logs get-log-events --log-group-name LOG_GROUP --log-stream-name STREAM

# Metrics
aws cloudwatch get-metric-statistics --namespace NAMESPACE --metric-name METRIC

# Target health
aws elbv2 describe-target-health --target-group-arn ARN
```

### Useful Queries
```bash
# Find failed tasks
aws logs filter-log-events \
  --log-group-name /ecs/weather-forecast-prod/api \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s)000

# Check response times
aws logs filter-log-events \
  --log-group-name /ecs/weather-forecast-prod/api \
  --filter-pattern "[timestamp, request_id, level, duration > 5000]"
```

---

**Last Updated**: 2024-10-29  
**Version**: 1.0  
**Review Schedule**: Monthly