# Configuration Drift Monitoring

## Overview

The Adelaide Weather Forecasting System includes comprehensive configuration drift monitoring that integrates with Prometheus alerts and optional webhook notifications for critical events. This system provides real-time visibility into configuration changes across the application stack.

## Features

### ✅ Prometheus Metrics Integration
- **Drift event counters** by type, severity, and source
- **Detection duration histograms** for performance monitoring
- **Unresolved events gauges** by severity level
- **File and environment variable monitoring counts**
- **Schema validation failure tracking**
- **Webhook notification status metrics**

### ✅ Multi-Level Alerting
- **CRITICAL**: Immediate action required for system stability
- **WARNING**: Changes requiring review and validation
- **INFO**: Operational insights and trends

### ✅ Webhook Notifications
- **Slack-compatible** webhook format for critical events
- **Configurable retry logic** with exponential backoff
- **Environment-controlled** enabling/disabling

### ✅ Comprehensive Monitoring Scope
- YAML/JSON configuration files
- Environment variables
- Docker configurations
- Kubernetes manifests
- Security configurations

## Quick Start

### 1. Environment Configuration

Copy the example configuration:
```bash
cp .env.config-drift-example .env.config-drift
```

Edit the configuration variables:
```bash
# Essential settings
CONFIG_DRIFT_METRICS_ENABLED=true
CONFIG_DRIFT_WEBHOOK_ENABLED=true
CONFIG_DRIFT_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
```

### 2. Integration with Main API

The drift detector is automatically initialized when the main API starts. Metrics are included in the `/metrics` endpoint alongside other application metrics.

### 3. Prometheus Configuration

Alert rules are automatically loaded when Prometheus starts:
```yaml
rule_files:
  - "alerts.yml"
  - "config_drift_alerts.yml"
  - "slo_alerts.yml"
```

## Alert Rules

### Critical Alerts
- **CriticalConfigurationDriftDetected**: Immediate response for critical config changes
- **SecurityRelatedConfigurationDrift**: Security-focused drift events
- **ConfigurationDriftMonitoringDown**: Monitoring system failure

### Warning Alerts
- **HighSeverityConfigurationDrift**: Multiple high-severity events
- **UnresolvedConfigurationDriftAccumulating**: Pending drift events
- **ConfigurationDriftDetectionSlow**: Performance degradation

### Informational Alerts
- **FrequentConfigurationDriftEvents**: Configuration instability patterns
- **ConfigurationDriftTrendIncreasing**: Trend analysis

## Metrics Reference

### Core Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `config_drift_events_total` | Counter | `drift_type`, `severity`, `source_type` | Total drift events detected |
| `config_drift_last_detection_timestamp` | Gauge | - | Last drift detection run timestamp |
| `config_drift_detection_duration_seconds` | Histogram | - | Drift detection execution time |
| `config_drift_unresolved_events` | Gauge | `severity` | Unresolved events by severity |
| `config_drift_files_monitored` | Gauge | - | Number of files being monitored |
| `config_drift_env_vars_monitored` | Gauge | - | Number of environment variables monitored |

### Operational Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `config_drift_snapshots_total` | Counter | `snapshot_type` | Configuration snapshots created |
| `config_drift_schema_validation_failures_total` | Counter | `config_path` | Schema validation failures |
| `config_drift_webhook_notifications_total` | Counter | `status`, `severity` | Webhook notification attempts |
| `config_drift_monitoring_active` | Gauge | - | Monitoring system status |

## Testing

Run the comprehensive test suite:
```bash
python3 monitoring/test_config_drift_monitoring.py
```

### Test Coverage
- ✅ Critical configuration file changes
- ✅ Schema validation failures
- ✅ Security-related drift detection
- ✅ Prometheus metrics generation
- ✅ Alert rule syntax validation
- ✅ Webhook notification functionality

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CONFIG_DRIFT_METRICS_ENABLED` | `true` | Enable metrics collection |
| `CONFIG_DRIFT_REALTIME_ENABLED` | `true` | Enable real-time file monitoring |
| `CONFIG_DRIFT_WEBHOOK_ENABLED` | `false` | Enable webhook notifications |
| `CONFIG_DRIFT_WEBHOOK_URL` | - | Webhook endpoint URL |
| `CONFIG_DRIFT_WEBHOOK_TIMEOUT` | `10` | Webhook timeout (seconds) |
| `CONFIG_DRIFT_WEBHOOK_RETRIES` | `3` | Webhook retry attempts |
| `CONFIG_DRIFT_CHECK_INTERVAL` | `60` | Detection interval (seconds) |
| `CONFIG_DRIFT_RETENTION_DAYS` | `30` | Snapshot retention period |

## Webhook Integration

### Slack Configuration
```bash
CONFIG_DRIFT_WEBHOOK_URL=https://hooks.slack.com/services/YOUR_SLACK_WEBHOOK_HERE
```

### Microsoft Teams Configuration
```bash
CONFIG_DRIFT_WEBHOOK_URL=https://outlook.office.com/webhook/YOUR-TEAMS-WEBHOOK-URL
```

### Discord Configuration
```bash
CONFIG_DRIFT_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR-DISCORD-WEBHOOK
```

## Monitoring Patterns

### File Types Monitored
- `**/*.yaml`, `**/*.yml` - YAML configurations
- `**/*.json` - JSON configurations
- `**/Dockerfile*` - Docker configurations
- `**/docker-compose*.yml` - Docker Compose files
- `**/.env*` - Environment files
- `**/kubernetes/*.yaml` - Kubernetes manifests
- `**/terraform/*.tf` - Terraform configurations

### Environment Variables Monitored
- `API_TOKEN`, `SECRET_KEY` - Authentication
- `DATABASE_URL` - Database configuration
- `LOG_LEVEL`, `DEBUG` - Application settings
- `CORS_ORIGINS` - Security settings
- `MODEL_PATH`, `DATA_PATH` - Application paths

## Severity Determination

### Critical Severity
- Docker/Kubernetes configuration changes
- Security configuration modifications
- Production environment files
- Authentication/authorization settings

### High Severity
- Model and data configuration changes
- Prometheus/monitoring configurations
- Application-specific settings

### Medium Severity
- General configuration files
- Environment variable changes
- Development settings

### Low Severity
- Non-critical file changes
- Documentation updates
- Test configurations

## Grafana Dashboard Integration

Metrics can be visualized in Grafana using queries like:
```promql
# Drift events by severity over time
rate(config_drift_events_total[5m])

# Unresolved critical events
config_drift_unresolved_events{severity="critical"}

# Detection performance
histogram_quantile(0.95, rate(config_drift_detection_duration_seconds_bucket[5m]))
```

## Troubleshooting

### Common Issues

1. **No metrics appearing**
   - Check `CONFIG_DRIFT_METRICS_ENABLED=true`
   - Verify API is running and `/metrics` endpoint accessible

2. **Webhook notifications not working**
   - Verify `CONFIG_DRIFT_WEBHOOK_ENABLED=true`
   - Check webhook URL is accessible
   - Review webhook timeout settings

3. **Real-time monitoring disabled**
   - Install watchdog: `pip install watchdog`
   - Check file system permissions

4. **Alert rules not firing**
   - Verify Prometheus is scraping metrics
   - Check alert rule syntax with `promtool`
   - Confirm AlertManager configuration

### Debug Commands

Check drift detector status:
```bash
# View metrics endpoint
curl -H "Authorization: Bearer $API_TOKEN" http://localhost:8000/metrics | grep config_drift

# Test webhook connectivity
curl -X POST $CONFIG_DRIFT_WEBHOOK_URL -H "Content-Type: application/json" -d '{"text": "test"}'

# Validate alert rules
promtool check rules monitoring/config_drift_alerts.yml
```

## Security Considerations

- Webhook URLs may contain sensitive tokens
- Environment variables with sensitive data are masked in logs
- Critical drift events trigger immediate security review
- Configuration changes in production require validation

## Performance Impact

- **CPU**: Minimal overhead (~1-2% during detection runs)
- **Memory**: ~10MB for baseline snapshots and event history
- **Disk**: Minimal (configuration snapshots are compressed)
- **Network**: Webhook notifications only for critical events

## Deployment Notes

### Docker
```yaml
environment:
  - CONFIG_DRIFT_METRICS_ENABLED=true
  - CONFIG_DRIFT_WEBHOOK_URL=${SLACK_WEBHOOK_URL}
```

### Kubernetes
```yaml
env:
- name: CONFIG_DRIFT_WEBHOOK_URL
  valueFrom:
    secretKeyRef:
      name: monitoring-secrets
      key: webhook-url
```

## Contributing

When adding new configuration patterns:
1. Update `monitored_patterns` in `ConfigurationDriftDetector`
2. Add appropriate severity classification
3. Include test scenarios
4. Update alert rules if needed
5. Document in this README

## Support

For issues or questions:
- Check test results: `config_drift_test_report.json`
- Review logs for drift detection events
- Monitor Prometheus alerts dashboard
- Contact infrastructure team for webhook setup

---

**Status**: ✅ Production Ready  
**Last Updated**: 2025-11-05  
**Version**: 1.0.0
