# Configuration Drift Detection & Monitoring

## Overview

The Configuration Drift Detection system monitors critical configuration files for unauthorized changes, ensuring system integrity and security compliance. This system provides real-time monitoring, alerting, and comprehensive audit logging.

## Features

- **Real-time Monitoring**: Continuous monitoring of critical configuration files
- **Security Validation**: Detection of insecure configuration values
- **Multi-format Support**: YAML, JSON, Docker Compose, and text files
- **Flexible Alerting**: Slack, email, and custom webhook notifications
- **Comprehensive Logging**: Detailed audit trails with correlation IDs
- **Performance Optimized**: Efficient file watching with configurable thresholds

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install watchdog pyyaml requests
   ```

2. **Configure Environment**:
   ```bash
   cp .env.config-drift-example .env.config-drift
   # Edit .env.config-drift with your settings
   ```

3. **Run the Monitor**:
   ```bash
   python demo_config_drift_detector.py
   ```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CONFIG_DRIFT_ENABLED` | Enable/disable monitoring | `true` |
| `CONFIG_DRIFT_CHECK_INTERVAL` | Check interval in seconds | `300` |
| `CONFIG_DRIFT_WATCH_PATHS` | Comma-separated file paths | `api/main.py,core/model_loader.py` |
| `CONFIG_DRIFT_WEBHOOK_URL` | Slack webhook URL | Required for alerts |
| `CONFIG_DRIFT_LOG_LEVEL` | Logging level | `INFO` |

### Monitored Files

The system monitors these critical files by default:
- `api/main.py` - Main API configuration
- `core/model_loader.py` - Model loading configuration  
- `nginx/nginx.conf` - Reverse proxy configuration
- `docker-compose.yml` - Container orchestration
- `.env*` - Environment configuration files

### Alert Configuration

Configure alerts in your `.env.config-drift` file:

```bash
# Slack Integration (replace with your webhook)
CONFIG_DRIFT_WEBHOOK_URL=https://hooks.slack.com/services/YOUR_SLACK_WEBHOOK_HERE

# Email Alerts
CONFIG_DRIFT_EMAIL_ENABLED=true
CONFIG_DRIFT_EMAIL_TO=alerts@yourcompany.com

# Alert Thresholds
CONFIG_DRIFT_NOTIFICATION_THRESHOLD=3
CONFIG_DRIFT_ALERT_SEVERITY=warning
```

## Security Features

### Insecure Value Detection

The system automatically detects potentially insecure configurations:

- Hardcoded passwords or API keys
- Insecure protocol usage (HTTP vs HTTPS)
- Weak encryption settings
- Debug mode enabled in production
- Default credentials

### Permission Monitoring

Tracks file permission and ownership changes:
- File permission modifications
- Ownership changes
- ACL modifications
- Symbolic link changes

## API Integration

### Health Check Endpoint

```bash
GET /health/config-drift
```

Response:
```json
{
  "status": "healthy",
  "last_check": "2024-11-05T10:30:00Z",
  "files_monitored": 12,
  "alerts_today": 0,
  "drift_detected": false
}
```

### Configuration Status

```bash
GET /api/config/status
```

Response:
```json
{
  "monitoring_enabled": true,
  "files_watched": [
    "api/main.py",
    "core/model_loader.py",
    "nginx/nginx.conf"
  ],
  "last_drift_event": null,
  "total_files": 12
}
```

## Monitoring Integration

### Prometheus Metrics

The system exposes metrics for monitoring:

```
# HELP config_drift_files_monitored Number of files being monitored
# TYPE config_drift_files_monitored gauge
config_drift_files_monitored 12

# HELP config_drift_violations_total Total configuration drift violations detected
# TYPE config_drift_violations_total counter
config_drift_violations_total{severity="warning"} 5
config_drift_violations_total{severity="critical"} 1

# HELP config_drift_last_check_timestamp Timestamp of last configuration check
# TYPE config_drift_last_check_timestamp gauge
config_drift_last_check_timestamp 1699185000
```

### Grafana Dashboard

Import the provided dashboard (`monitoring/grafana/dashboards/config-drift-dashboard.json`) for visualization:

- Real-time drift detection status
- File modification timeline
- Alert frequency analysis
- Security violation trends

## Testing

### Basic Functionality Test

```bash
python simple_test_config_drift.py
```

### Integration Test

```bash
python test_config_drift_detector.py
```

### Performance Test

```bash
python monitoring/test_config_drift_monitoring.py
```

## Troubleshooting

### Common Issues

1. **File Permission Errors**:
   - Ensure the monitoring user has read access to watched files
   - Check file system permissions and ACLs

2. **High CPU Usage**:
   - Reduce `CONFIG_DRIFT_CHECK_INTERVAL` value
   - Limit `CONFIG_DRIFT_WATCH_PATHS` to essential files only

3. **Missing Alerts**:
   - Verify webhook URL configuration
   - Check network connectivity to alert endpoints
   - Review log files for error messages

### Log Analysis

```bash
# View recent drift events
tail -f logs/config_drift.log | grep "DRIFT_DETECTED"

# Check for errors
grep "ERROR" logs/config_drift.log

# Monitor performance
grep "performance" logs/config_drift.log
```

## Production Deployment

### Docker Integration

The drift detector runs as a sidecar container:

```yaml
services:
  config-drift-monitor:
    image: adelaide-weather/config-drift:latest
    volumes:
      - ./configs:/app/configs:ro
      - ./logs:/app/logs
    environment:
      - CONFIG_DRIFT_ENABLED=true
      - CONFIG_DRIFT_WEBHOOK_URL=${SLACK_WEBHOOK_URL}
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: config-drift-monitor
spec:
  selector:
    matchLabels:
      app: config-drift-monitor
  template:
    spec:
      containers:
      - name: monitor
        image: adelaide-weather/config-drift:latest
        env:
        - name: CONFIG_DRIFT_WEBHOOK_URL
          valueFrom:
            secretKeyRef:
              name: slack-webhook
              key: url
```

## Best Practices

1. **File Selection**: Monitor only critical configuration files to reduce noise
2. **Alert Tuning**: Set appropriate thresholds to avoid alert fatigue
3. **Regular Testing**: Periodically test the monitoring system
4. **Backup Strategy**: Maintain configuration backups for quick restoration
5. **Access Control**: Limit who can modify monitored configuration files

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

This configuration drift detection system is part of the Adelaide Weather Forecasting System and follows the same licensing terms.