# Adelaide Weather Forecasting - Synthetic Monitoring & SLOs

This directory contains a comprehensive synthetic monitoring and Service Level Objective (SLO) tracking system for the Adelaide Weather Forecasting application.

## 🎯 Overview

The synthetic monitoring system provides:

- **Service Level Objectives (SLOs)** with error budget tracking
- **Geographic distribution monitoring** across Australian regions
- **Real-time synthetic checks** for all critical endpoints
- **Multi-layer alerting** with escalation policies
- **Comprehensive dashboards** for operational visibility
- **Error budget burn rate alerts** for proactive incident response

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Synthetic      │    │   Prometheus    │    │    Grafana      │
│  Monitor        │───▶│   (Metrics)     │───▶│  (Dashboards)   │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       ▼                       │
         │              ┌─────────────────┐              │
         └─────────────▶│  Alertmanager   │◀─────────────┘
                        │   (Alerting)    │
                        └─────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────────┐
                    │ Notification Channels       │
                    │ • Slack                     │
                    │ • PagerDuty                 │
                    │ • Email                     │
                    └─────────────────────────────┘
```

## 📊 Service Level Objectives

### API Availability SLO
- **Target**: 99.9% uptime (8.64 minutes downtime per month)
- **Measurement**: Success rate of synthetic checks
- **Error Budget**: 0.1% (43.2 minutes per month)

### API Latency SLO  
- **Target**: 95% of requests under 150ms
- **Measurement**: 95th percentile response time
- **Threshold**: 150ms for forecast endpoints

### Data Quality SLO
- **Target**: 98% of forecasts have valid data
- **Measurement**: Forecast validation success rate
- **Criteria**: All required variables present and valid

### Frontend Performance SLO
- **Target**: 90% of page loads under 2 seconds
- **Measurement**: Page load time from synthetic checks
- **Threshold**: 2000ms for initial page load

## 🔍 Synthetic Checks

### Endpoint Monitoring
- **Forecast API**: `/forecast` endpoint with parameter validation
- **Health Checks**: `/health`, `/health/live`, `/health/ready`
- **Frontend**: Page load and content validation
- **Metrics**: Prometheus metrics endpoints

### Geographic Distribution
- **Sydney**: Primary region (40% weight)
- **Melbourne**: Primary region (40% weight)  
- **Perth**: Secondary region (10% weight)
- **Singapore**: International check (10% weight)

### Check Types
- **Availability**: HTTP status code validation
- **Performance**: Response time measurement
- **Content**: JSON schema and content validation
- **Functionality**: End-to-end user journey testing

## 🚨 Alerting Strategy

### Error Budget Burn Rates
- **Fast burn (1h)**: >14.4x rate → Critical alert (immediate page)
- **Medium burn (6h)**: >6.0x rate → Warning alert (business hours page)
- **Slow burn (24h)**: >3.0x rate → Monitoring alert (email/Slack)

### Escalation Policies
1. **Critical alerts**: PagerDuty → Slack → Email (0m, 5m, 15m)
2. **Warning alerts**: Slack → Email (0m, 30m)
3. **Monitoring alerts**: Slack only

### Alert Categories
- **SLO Breaches**: Service level violations
- **Synthetic Failures**: Check failures by region/endpoint
- **Infrastructure**: System resource alerts
- **Data Quality**: Forecast accuracy issues

## 🚀 Deployment

### Prerequisites
- Docker and Docker Compose
- 4GB+ available memory
- Network access to target services

### Quick Start
```bash
# Deploy the complete monitoring stack
./deploy_synthetic_monitoring.sh deploy

# Check status
docker-compose -f docker-compose.monitoring.yml ps

# View logs
docker-compose -f docker-compose.monitoring.yml logs -f
```

### Configuration
Edit the `.env` file with your specific values:
```bash
# Required
API_TOKEN=your-secure-api-token-here

# Optional (for alerting)
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
PAGERDUTY_SERVICE_KEY=your-pagerduty-key
SMTP_SERVER=smtp.your-org.com
```

### Access Points
- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093
- **Synthetic Monitor**: http://localhost:8080/metrics

## 📁 Directory Structure

```
monitoring/
├── synthetic/
│   ├── config.yml              # Synthetic monitoring configuration
│   ├── synthetic_monitor.py    # Main monitoring application
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile             # Container definition
│   └── schemas/               # JSON validation schemas
├── grafana/
│   └── dashboards/
│       └── slo-dashboard.json # SLO monitoring dashboard
├── alertmanager/
│   └── alertmanager.yml       # Alert routing configuration
├── blackbox/
│   └── blackbox.yml           # Endpoint monitoring config
├── prometheus.enhanced.yml     # Enhanced Prometheus config
├── slo_alerts.yml             # SLO alerting rules
├── docker-compose.monitoring.yml # Complete stack definition
└── deploy_synthetic_monitoring.sh # Deployment script
```

## 🔧 Configuration Files

### Synthetic Monitor Config (`synthetic/config.yml`)
- Endpoint definitions and check parameters
- SLO targets and error budget thresholds
- Geographic region configuration
- Alerting channel setup

### Prometheus Config (`prometheus.enhanced.yml`)
- Service discovery and scraping configuration
- Recording rules for SLO calculations
- Integration with alerting system

### Alertmanager Config (`alertmanager/alertmanager.yml`)
- Alert routing and escalation rules
- Notification channel configuration
- Inhibition rules to prevent alert spam

## 📈 Monitoring and Operations

### Key Metrics
- `slo_availability_ratio`: Current availability ratio by SLO
- `slo_error_budget_remaining_ratio`: Remaining error budget (0-1)
- `slo_burn_rate`: Current error budget burn rate by time window
- `synthetic_check_success_total`: Successful synthetic checks
- `synthetic_check_duration_seconds`: Check response times

### Dashboard Usage
1. **SLO Overview**: High-level SLO status and trends
2. **Error Budget**: Current budget and burn rate analysis
3. **Geographic View**: Performance by monitoring region
4. **Alert History**: Recent alerts and escalations

### Operational Procedures

#### SLO Breach Response
1. **Immediate**: Check alert details and runbook
2. **Assess**: Determine scope and user impact
3. **Mitigate**: Apply immediate fixes if possible
4. **Investigate**: Root cause analysis
5. **Follow-up**: Post-incident review and improvements

#### Error Budget Management
- **Monthly review**: Analyze budget consumption patterns
- **Trend analysis**: Identify recurring issues
- **Capacity planning**: Adjust SLO targets if needed
- **Process improvement**: Update monitoring based on incidents

## 🧪 Testing

### Validation Tests
```bash
# Test synthetic monitoring functionality
./deploy_synthetic_monitoring.sh test

# Check individual components
curl http://localhost:8080/metrics
curl http://localhost:9090/-/healthy
curl http://localhost:3001/api/health
```

### Load Testing
The synthetic monitor includes configurable check intervals and can simulate load patterns for SLO validation.

## 🔒 Security Considerations

- **API tokens**: Securely stored and rotated regularly
- **Network isolation**: Monitoring network separated from production
- **Access control**: Role-based access to monitoring tools
- **Alert security**: Sensitive data filtered from notifications

## 🔗 Integration

### Existing Systems
- **T-007 Prometheus Metrics**: Leverages existing application metrics
- **API Security**: Uses existing authentication mechanisms
- **Frontend Monitoring**: Integrates with React application metrics

### External Services
- **Slack**: Real-time alert notifications
- **PagerDuty**: Critical incident escalation
- **Email**: Alert notifications and reports

## 📚 References

- [SLO Implementation Guide](https://sre.google/sre-book/service-level-objectives/)
- [Error Budget Policies](https://sre.google/workbook/error-budget-policy/)
- [Prometheus Alerting](https://prometheus.io/docs/alerting/latest/)
- [Grafana Dashboards](https://grafana.com/docs/grafana/latest/dashboards/)

## 🆘 Troubleshooting

### Common Issues

#### Synthetic Monitor Not Starting
```bash
# Check logs
docker-compose -f docker-compose.monitoring.yml logs synthetic-monitor

# Verify configuration
cat synthetic/config.yml

# Check API connectivity
curl -H "Authorization: Bearer $API_TOKEN" http://api:8000/health
```

#### Missing Metrics
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Verify service discovery
docker-compose -f docker-compose.monitoring.yml ps
```

#### Alert Not Firing
```bash
# Check Prometheus rules
curl http://localhost:9090/api/v1/rules

# Verify Alertmanager config
curl http://localhost:9093/api/v1/status
```

### Support
For issues or questions:
1. Check the logs for error messages
2. Verify configuration files
3. Test individual components
4. Review alert routing rules
5. Consult the troubleshooting guide above