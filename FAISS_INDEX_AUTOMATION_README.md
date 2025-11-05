# FAISS Index Automation System

Comprehensive automated FAISS index rebuilding system with validation, atomic deployment, and monitoring capabilities for the Adelaide Weather Forecasting project.

## Overview

The FAISS Index Automation System provides production-ready automated lifecycle management for FAISS indices, ensuring fresh, validated indices while maintaining system availability through zero-downtime deployments.

## Key Features

### 🔧 **Automated Index Rebuilding**
- Scheduled rebuilds with configurable timing (cron-style)
- Manual trigger capability via CLI/API
- Support for all forecast horizons (6h, 12h, 24h, 48h)
- Parallel processing for multiple index types

### 🔍 **Comprehensive Validation**
- Structural validation (dimensions, size, type)
- Search functionality testing
- Performance benchmarking
- Recall validation for approximate indices
- Integration with existing startup validation

### ⚡ **Atomic Deployment**
- Zero-downtime index replacement
- Automatic rollback on validation failure
- Backup creation before deployment
- Staged deployment with verification

### 📊 **Monitoring & Alerting**
- Prometheus metrics export
- Grafana dashboard integration
- Health check endpoints
- Alert rules for common failure patterns
- Resource usage monitoring

### 🔒 **Production Safety**
- File locks to prevent concurrent rebuilds
- Timeout protection for long-running operations
- Resource usage limits and monitoring
- Comprehensive error handling and logging

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Scheduler     │    │   Rebuilder     │    │   Validator     │
│                 │    │                 │    │                 │
│ - Cron-style    │───▶│ - Build indices │───▶│ - Quality gates │
│ - Manual trigger│    │ - Staging       │    │ - Performance   │
│ - Health checks │    │ - Atomic deploy │    │ - Recall tests  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Monitor      │    │ Backup Manager  │    │   Notification  │
│                 │    │                 │    │                 │
│ - Prometheus    │    │ - Versioning    │    │ - Slack/Email   │
│ - Health status │    │ - Compression   │    │ - Webhooks      │
│ - Alert rules   │    │ - Restoration   │    │ - Log alerts    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Installation

### 1. System Dependencies

```bash
# Install required Python packages
pip install -r requirements.txt
pip install prometheus-client schedule psutil filelock

# Optional: Install systemd service
sudo python scripts/faiss_rebuild_service.py install
```

### 2. Configuration

Create configuration file at `/etc/faiss-rebuild/config.json`:

```json
{
  "scheduler": {
    "rebuild_schedule": "0 2 * * 0",
    "timezone": "UTC",
    "max_rebuild_duration_hours": 4,
    "enable_notifications": true,
    "notification_channels": ["log", "email"],
    "log_level": "INFO"
  },
  "monitoring": {
    "enable_prometheus": true,
    "metrics_port": 9100,
    "health_check_port": 8080,
    "integrate_with_existing_monitoring": true
  }
}
```

### 3. Service Setup

```bash
# Install and start systemd service
sudo systemctl start faiss-rebuild
sudo systemctl enable faiss-rebuild

# Check status
sudo systemctl status faiss-rebuild
sudo journalctl -u faiss-rebuild -f
```

## Usage

### Command Line Interface

The system provides a comprehensive CLI for all operations:

```bash
# Manual rebuild
python scripts/faiss_rebuild_cli.py rebuild

# System status
python scripts/faiss_rebuild_cli.py status

# Backup management
python scripts/faiss_rebuild_cli.py backup list
python scripts/faiss_rebuild_cli.py backup create
python scripts/faiss_rebuild_cli.py backup restore --backup-id 20241105_143000

# Monitoring
python scripts/faiss_rebuild_cli.py monitor --health
python scripts/faiss_rebuild_cli.py monitor --metrics
python scripts/faiss_rebuild_cli.py monitor --alerts

# Maintenance
python scripts/faiss_rebuild_cli.py maintenance cleanup
python scripts/faiss_rebuild_cli.py maintenance validate
python scripts/faiss_rebuild_cli.py maintenance disk-usage
```

### Programmatic Usage

```python
from core.faiss_index_rebuilder import FAISSIndexRebuilder, RebuildConfig
from core.faiss_rebuild_scheduler import FAISSRebuildScheduler

# Manual rebuild
config = RebuildConfig(validation_enabled=True)
rebuilder = FAISSIndexRebuilder(config)
result = rebuilder.rebuild_all_indices()

# Scheduled operation
scheduler = FAISSRebuildScheduler()
scheduler.start()
```

## Configuration Reference

### Rebuild Configuration

```python
@dataclass
class RebuildConfig:
    embeddings_dir: str = "embeddings"
    indices_dir: str = "indices"
    backup_dir: str = "indices/backups"
    staging_dir: str = "indices/staging"
    
    # Rebuild parameters
    horizons: List[int] = [6, 12, 24, 48]
    index_types: List[str] = ['flatip', 'ivfpq']
    
    # Validation settings
    validation_enabled: bool = True
    min_recall_threshold: float = 0.95
    max_latency_threshold_ms: float = 100.0
    
    # Safety settings
    require_validation_pass: bool = True
    enable_rollback: bool = True
    max_rebuild_time_minutes: int = 60
```

### Scheduler Configuration

```python
@dataclass
class SchedulerConfig:
    rebuild_schedule: str = "0 2 * * 0"  # Weekly Sunday 2 AM
    timezone: str = "UTC"
    max_rebuild_duration_hours: int = 4
    
    # Failure handling
    max_consecutive_failures: int = 3
    failure_cooldown_hours: int = 24
    
    # Notifications
    enable_notifications: bool = True
    notification_channels: List[str] = ['log', 'email']
```

### Monitoring Configuration

```python
@dataclass
class MonitoringConfig:
    enable_prometheus: bool = True
    metrics_port: int = 9100
    health_check_port: int = 8080
    
    # Alert thresholds
    max_rebuild_duration_minutes: float = 240.0
    max_failure_rate: float = 0.2
    min_success_rate_24h: float = 0.8
```

## Monitoring

### Prometheus Metrics

The system exports comprehensive metrics for monitoring:

```
# Rebuild metrics
faiss_rebuild_total{status="success|failure", trigger_type="scheduled|manual"}
faiss_rebuild_duration_seconds{status="success|failure"}
faiss_rebuild_consecutive_failures
faiss_rebuild_last_success_timestamp

# Index quality metrics
faiss_index_size_total{horizon="6h|12h|24h|48h", index_type="flatip|ivfpq"}
faiss_index_search_latency_ms{horizon, index_type}
faiss_index_recall_score{horizon, index_type}

# Resource metrics
faiss_rebuild_memory_peak_bytes
faiss_rebuild_cpu_avg_percent
```

### Health Checks

Health endpoint available at `http://localhost:8080/health`:

```json
{
  "status": "healthy|warning|critical",
  "timestamp": "2024-11-05T14:30:00Z",
  "component": "faiss_rebuild_system",
  "active_alerts": [],
  "alert_counts": {
    "critical": 0,
    "warning": 0,
    "total": 0
  }
}
```

### Alert Rules

Pre-configured alert rules for common issues:

- **FAISSRebuildHighDuration**: Rebuild taking too long (>4h)
- **FAISSRebuildConsecutiveFailures**: Too many consecutive failures (≥3)
- **FAISSRebuildLowSuccessRate**: Success rate too low (<80% in 24h)
- **FAISSRebuildStale**: No successful rebuild in 7 days
- **FAISSIndexLowRecall**: Index recall score too low (<90%)

## Operational Procedures

### Daily Operations

1. **Health Check**
   ```bash
   python scripts/faiss_rebuild_cli.py monitor --health
   ```

2. **Status Review**
   ```bash
   python scripts/faiss_rebuild_cli.py status
   ```

3. **Log Review**
   ```bash
   sudo journalctl -u faiss-rebuild --since "24 hours ago"
   ```

### Weekly Maintenance

1. **Backup Cleanup**
   ```bash
   python scripts/faiss_rebuild_cli.py maintenance cleanup
   ```

2. **Disk Usage Review**
   ```bash
   python scripts/faiss_rebuild_cli.py maintenance disk-usage
   ```

3. **Index Validation**
   ```bash
   python scripts/faiss_rebuild_cli.py maintenance validate
   ```

### Incident Response

#### Rebuild Failure

1. **Check Status**
   ```bash
   python scripts/faiss_rebuild_cli.py status
   python scripts/faiss_rebuild_cli.py monitor --alerts
   ```

2. **Review Logs**
   ```bash
   sudo journalctl -u faiss-rebuild -n 100
   ```

3. **Manual Recovery**
   ```bash
   # If needed, restore from backup
   python scripts/faiss_rebuild_cli.py backup list
   python scripts/faiss_rebuild_cli.py backup restore --backup-id BACKUP_ID
   
   # Or trigger manual rebuild
   python scripts/faiss_rebuild_cli.py rebuild --force
   ```

#### Service Issues

1. **Service Status**
   ```bash
   sudo systemctl status faiss-rebuild
   ```

2. **Restart Service**
   ```bash
   sudo systemctl restart faiss-rebuild
   ```

3. **Configuration Reload**
   ```bash
   sudo systemctl reload faiss-rebuild
   ```

## Troubleshooting

### Common Issues

#### 1. Rebuild Timeouts
**Symptoms**: Rebuilds taking longer than expected
**Solutions**:
- Increase `max_rebuild_duration_hours` in config
- Check system resources and load
- Review embeddings data size and complexity

#### 2. Validation Failures
**Symptoms**: New indices failing validation
**Solutions**:
- Check embeddings data quality
- Verify dimension consistency
- Review validation thresholds
- Check disk space in staging area

#### 3. Memory Issues
**Symptoms**: Out of memory errors during rebuild
**Solutions**:
- Increase system memory
- Adjust `max_memory_gb` in config
- Enable staging cleanup
- Process horizons sequentially

#### 4. Permission Errors
**Symptoms**: Cannot write to directories
**Solutions**:
- Check file permissions on directories
- Verify service user has correct permissions
- Check SELinux/AppArmor policies

### Log Analysis

Important log patterns to monitor:

```bash
# Successful rebuild
grep "Rebuild completed successfully" /var/log/faiss-rebuild/service.log

# Validation failures
grep "Validation failed" /var/log/faiss-rebuild/service.log

# Resource issues
grep -E "(memory|CPU|disk)" /var/log/faiss-rebuild/service.log

# Backup operations
grep -E "(backup|restore)" /var/log/faiss-rebuild/service.log
```

## Performance Tuning

### Rebuild Performance

1. **Parallel Processing**
   - Adjust `max_workers` in rebuild config
   - Balance CPU cores vs memory usage

2. **Validation Optimization**
   - Reduce `validation_sample_size` for faster validation
   - Adjust recall thresholds based on requirements

3. **Storage Optimization**
   - Use SSD storage for staging directory
   - Ensure sufficient disk space (3x index size)

### Resource Management

1. **Memory Management**
   - Monitor peak memory usage during rebuilds
   - Adjust system limits based on data size
   - Use memory mapping for large datasets

2. **CPU Optimization**
   - Schedule rebuilds during low-traffic periods
   - Balance rebuild frequency vs system load

## Security Considerations

### File Permissions

```bash
# Service user setup
sudo useradd -r -s /bin/false faiss-rebuild
sudo chown -R faiss-rebuild:faiss-rebuild /var/lib/faiss-rebuild
sudo chmod 750 /var/lib/faiss-rebuild
```

### Network Security

- Health check endpoint should be internal-only
- Metrics endpoint should be secured with authentication
- Use HTTPS for webhook notifications

### Data Protection

- Encrypt backups for sensitive deployments
- Implement audit logging for rebuild operations
- Secure configuration files with appropriate permissions

## Integration

### Existing FAISS Infrastructure

The system integrates seamlessly with existing FAISS components:

- **Analog Search Service**: Uses rebuilt indices automatically
- **Health Monitoring**: Extends existing monitoring with rebuild metrics
- **Startup Validation**: Uses same validation framework

### CI/CD Integration

```yaml
# Example GitHub Actions workflow
name: FAISS Index Validation
on:
  push:
    paths: ['embeddings/**', 'indices/**']

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Validate Indices
        run: python scripts/faiss_rebuild_cli.py maintenance validate
```

### Grafana Dashboard

Import the provided dashboard configuration:

```bash
python scripts/faiss_rebuild_cli.py monitor --dashboard > faiss-rebuild-dashboard.json
```

## License

This system is part of the Adelaide Weather Forecasting project and follows the same licensing terms.

## Support

For issues and support:

1. Check this documentation and troubleshooting guide
2. Review system logs and monitoring dashboards
3. Use the CLI tools for diagnosis and recovery
4. Consult the existing FAISS infrastructure documentation

---

*Last updated: November 2024*
*Version: 1.0.0 - T-015 FAISS Index Automation*