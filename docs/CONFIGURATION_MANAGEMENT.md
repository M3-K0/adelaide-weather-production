# Adelaide Weather Forecasting - Configuration Management Guide

## Overview

The Adelaide Weather Forecasting System uses a sophisticated configuration management approach that supports multiple environments, secure credential storage, and real-time drift detection. This guide covers all aspects of configuration management in the system.

## 🏗️ Architecture Overview

### Configuration Components

1. **Environment Configuration Manager** - Multi-environment configuration with validation
2. **Secure Credential Manager** - Enterprise-grade credential storage
3. **Configuration Drift Detector** - Real-time change monitoring
4. **Environment Detection** - Automatic environment identification

### Configuration Hierarchy

```
Base Configuration (configs/)
├── data.yaml              # Data processing configuration
├── model.yaml             # ML model configuration
├── training.yaml          # Training parameters
└── environments/
    ├── development/        # Development overrides
    │   ├── data.yaml
    │   └── model.yaml
    ├── staging/           # Staging overrides
    │   └── model.yaml
    └── production/        # Production overrides
        ├── data.yaml
        └── model.yaml
```

## 🌍 Environment Management

### Environment Detection

The system automatically detects environments using these variables (in order of precedence):

1. `ENVIRONMENT`
2. `ENV`
3. `STAGE`
4. `NODE_ENV`

```bash
# Set environment explicitly
export ENVIRONMENT="production"

# Alternative environment variables
export ENV="staging"
export STAGE="development"
export NODE_ENV="production"
```

### Environment-Specific Configuration

#### Development Environment
- **Purpose**: Rapid development and testing
- **Characteristics**: Reduced resource requirements, simplified configurations
- **Validation**: Relaxed validation for faster iteration

```yaml
# configs/environments/development/model.yaml
encoder:
  embedding_dim: 128        # Reduced for faster training
  batch_size: 32           # Smaller batches for memory efficiency

training:
  epochs: 10               # Fewer epochs for quick iteration
  device: "cpu"            # CPU-only for accessibility
```

#### Staging Environment
- **Purpose**: Production-like testing and integration validation
- **Characteristics**: Production settings with test data
- **Validation**: Full production validation

```yaml
# configs/environments/staging/model.yaml
encoder:
  embedding_dim: 256       # Production dimensions
  batch_size: 64          # Production batch sizes

training:
  device: "cuda"          # GPU acceleration enabled
  validation_split: 0.2   # Comprehensive validation
```

#### Production Environment
- **Purpose**: Live production deployment
- **Characteristics**: Optimized for performance and reliability
- **Validation**: Strict validation and security requirements

```yaml
# configs/environments/production/model.yaml
encoder:
  embedding_dim: 256       # Full production dimensions
  batch_size: 128         # Optimized batch sizes

training:
  device: "cuda"          # GPU required
  experiment_tracking: true # Full monitoring enabled
```

### Environment Configuration Usage

```python
from core import EnvironmentConfigManager, Environment

# Automatic environment detection
manager = EnvironmentConfigManager()
config = manager.load_config()

# Manual environment specification
manager = EnvironmentConfigManager(environment=Environment.PRODUCTION)
config = manager.load_config()

# Access configuration values
adelaide_lat = manager.get('adelaide.lat')
embedding_dim = manager.get('encoder.embedding_dim', 256)

# Environment checks
if manager.is_production():
    print("Running in production mode")
elif manager.is_development():
    print("Running in development mode")
```

## 🔒 Secure Credential Management

### Credential Types

The system supports multiple credential types with different security levels:

```python
from core.secure_credential_manager import CredentialType, SecurityLevel

class CredentialType(Enum):
    API_KEY = "api_key"
    DATABASE_PASSWORD = "database_password"
    SERVICE_TOKEN = "service_token"
    ENCRYPTION_KEY = "encryption_key"
    OAUTH_CLIENT_SECRET = "oauth_client_secret"
    CERTIFICATE = "certificate"
    PRIVATE_KEY = "private_key"
    WEBHOOK_SECRET = "webhook_secret"
    SESSION_SECRET = "session_secret"
    JWT_SECRET = "jwt_secret"
```

### Security Levels

```python
class SecurityLevel(Enum):
    STANDARD = auto()      # Basic encryption, standard audit trail
    HIGH = auto()          # Enhanced encryption (2x iterations)
    CRITICAL = auto()      # Maximum security (5x iterations)
    EPHEMERAL = auto()     # Memory-only storage, no persistence
```

### Credential Management Operations

#### Storing Credentials

```python
from core.secure_credential_manager import SecureCredentialManager

# Initialize credential manager
credential_manager = SecureCredentialManager(
    environment="production",
    master_key_env="ADELAIDE_WEATHER_MASTER_KEY"
)

# Store API key
credential_manager.store_credential(
    credential_id="openweather_api_key",
    credential_value="your-secret-api-key",
    credential_type=CredentialType.API_KEY,
    security_level=SecurityLevel.STANDARD,
    tags={"service": "openweather", "environment": "production"}
)

# Store database password with high security
credential_manager.store_credential(
    credential_id="postgres_password",
    credential_value="secure-database-password",
    credential_type=CredentialType.DATABASE_PASSWORD,
    security_level=SecurityLevel.HIGH,
    metadata={"host": "localhost", "database": "weather_data"}
)
```

#### Retrieving Credentials

```python
# Secure context manager (recommended)
with credential_manager.secure_context("openweather_api_key") as api_key:
    # Use the credential
    response = make_api_request(api_key)
    # Credential automatically cleared after this block

# Manual retrieval (less secure)
api_key = credential_manager.retrieve_credential("openweather_api_key")
try:
    response = make_api_request(api_key)
finally:
    # Manual cleanup required
    del api_key
```

#### Credential Rotation

```python
# Rotate credential with backup
old_credential = credential_manager.rotate_credential(
    credential_id="api_key",
    new_credential_value="new-secure-key",
    create_backup=True
)

# List credentials for management
credentials = credential_manager.list_credentials(
    credential_type=CredentialType.API_KEY,
    environment="production"
)
```

### Environment Variable Overrides

Override configuration values using the `ADELAIDE_` prefix:

```bash
# Override Adelaide coordinates
export ADELAIDE_LAT="-34.9285"
export ADELAIDE_LON="138.6007"

# Override model parameters
export ADELAIDE_ENCODER_EMBEDDING_DIM="512"
export ADELAIDE_TRAINING_BATCH_SIZE="256"

# Set master encryption key
export ADELAIDE_WEATHER_MASTER_KEY="your-secure-master-key"
```

## 🔍 Configuration Drift Detection

### Real-time Monitoring

The Configuration Drift Detector monitors changes to configuration files and environment variables:

```python
from core.config_drift_detector import ConfigurationDriftDetector, DriftSeverity

# Initialize detector
detector = ConfigurationDriftDetector(
    project_root=Path("/home/micha/adelaide-weather-final"),
    enable_real_time=True,
    check_interval_seconds=60
)

# Start monitoring
detector.start_monitoring()

# Detect drift
events = detector.detect_drift()

# Filter by severity
critical_events = [e for e in events if e.severity == DriftSeverity.CRITICAL]
```

### Monitored Files and Patterns

#### Included Files
- Configuration files: `*.yaml`, `*.yml`, `*.json`
- Environment files: `.env*`
- Infrastructure files: `docker-compose*.yml`, `Dockerfile*`
- Kubernetes configs: `k8s/*.yaml`
- Monitoring configs: `prometheus*.yml`, `alertmanager*.yml`

#### Excluded Patterns
- Build artifacts: `node_modules/`, `.next/`, `build/`, `dist/`
- Version control: `.git/`
- Python artifacts: `__pycache__/`, `*.pyc`
- Temporary files: `*.log`, `*.tmp`

### Severity Assessment

#### CRITICAL 🚨
- Docker/Kubernetes configurations
- Security credentials and tokens
- Production environment files (`.env.production`)

#### HIGH ⚠️
- ML model configurations (`model.yaml`, `training.yaml`)
- Data processing configs (`data.yaml`)
- Monitoring configurations (`prometheus.yml`)

#### MEDIUM 📋
- Environment variables (`.env` files)
- General configurations (`config*.yaml`)
- Application settings (`settings*.json`)

#### LOW ℹ️
- Documentation (`README.md`, `*.txt`)
- Package configurations (`package.json`)
- Non-critical application files

### Drift Reporting

```python
# Generate comprehensive report
report = detector.get_drift_report()

# Filter by severity and time
critical_report = detector.get_drift_report(
    severity_filter=DriftSeverity.CRITICAL,
    hours_back=24
)

# Resolve drift events
detector.resolve_drift_event(
    event_id="drift_event_123",
    resolution_notes="Configuration change approved via CR-2023-045"
)
```

## 🚀 Deployment Configuration

### Environment Setup

#### Development Deployment
```bash
export ENVIRONMENT="development"
export API_TOKEN="dev-token-change-in-production"

# Deploy development environment
./deploy.sh development
```

#### Staging Deployment
```bash
export ENVIRONMENT="staging"
export API_TOKEN="staging-secure-token"

# Deploy staging environment
./deploy.sh staging --monitoring
```

#### Production Deployment
```bash
export ENVIRONMENT="production"
export API_TOKEN="production-secure-token"
export ADELAIDE_WEATHER_MASTER_KEY="production-master-key"

# Deploy production environment
./deploy.sh production --monitoring --force
```

### Configuration Validation

The deployment script validates configuration at multiple levels:

1. **System Requirements**: Docker, memory, disk space
2. **Environment Configuration**: YAML validation and schema compliance
3. **Credential Validation**: Required credentials and security levels
4. **Docker Compose**: Service configuration and dependency validation

```bash
# Manual validation
python3 -c "
from core.environment_config_manager import EnvironmentConfigManager
manager = EnvironmentConfigManager(environment='production')
config = manager.load_config()
print('✅ Configuration validation passed')
"
```

## 📊 Configuration Monitoring

### Health Endpoints

Monitor configuration health through dedicated endpoints:

```bash
# Check system health
curl http://localhost:8000/health

# Detailed configuration health
curl http://localhost:8000/health/detailed

# Dependency status
curl http://localhost:8000/health/dependencies
```

### Prometheus Metrics

Configuration-related metrics are exported to Prometheus:

```promql
# Configuration drift events
config_drift_events_total{severity="critical"}

# Credential access patterns
credential_access_total{credential_type="api_key"}

# Environment configuration status
environment_config_validation_status
```

### Grafana Dashboards

Monitor configuration health through Grafana dashboards:

- **Configuration Overview**: Environment status, validation results
- **Drift Detection**: Real-time configuration changes and trends
- **Credential Management**: Access patterns and security metrics
- **System Health**: Overall configuration and system status

## 🛡️ Security Best Practices

### Credential Security

1. **Use Environment Variables**: Never commit credentials to version control
2. **Rotate Regularly**: Implement credential rotation policies
3. **Least Privilege**: Grant minimal required access
4. **Audit Trails**: Monitor all credential access

### Configuration Security

1. **Validate Inputs**: Use schema validation for all configuration
2. **Environment Isolation**: Separate configurations per environment
3. **Access Control**: Restrict configuration file access
4. **Change Monitoring**: Monitor all configuration changes

### Deployment Security

1. **Secure Deployment**: Use encrypted communication
2. **Backup Strategy**: Maintain secure configuration backups
3. **Rollback Capability**: Ensure quick rollback for security issues
4. **Health Monitoring**: Continuous security posture monitoring

## 🔧 Troubleshooting

### Common Issues

#### Configuration Validation Failures
```bash
# Check configuration syntax
python3 -c "
from core.environment_config_manager import EnvironmentConfigManager
try:
    manager = EnvironmentConfigManager()
    config = manager.load_config()
    print('✅ Configuration valid')
except Exception as e:
    print(f'❌ Configuration error: {e}')
"
```

#### Credential Access Issues
```bash
# Test credential manager
python3 demo_credential_manager.py

# Check master key
echo "Master key set: ${ADELAIDE_WEATHER_MASTER_KEY:+YES}"
```

#### Environment Detection Problems
```bash
# Check environment variables
env | grep -E "(ENVIRONMENT|ENV|STAGE|NODE_ENV)"

# Test environment detection
python3 -c "
from core.environment_config_manager import EnvironmentConfigManager
manager = EnvironmentConfigManager()
print(f'Detected environment: {manager.get_environment().value}')
"
```

#### Configuration Drift Issues
```bash
# Check drift detection
python3 demo_config_drift_detector.py

# Manual drift check
python3 -c "
from core.config_drift_detector import ConfigurationDriftDetector
detector = ConfigurationDriftDetector()
events = detector.detect_drift()
print(f'Drift events: {len(events)}')
"
```

### Recovery Procedures

#### Restore from Backup
```bash
# Find latest backup
ls -la backups/production/

# Restore configuration
tar -xzf backups/production/backup-YYYYMMDD-HHMMSS.tar.gz

# Redeploy
./deploy.sh production --force
```

#### Reset Credentials
```bash
# Set new master key
export ADELAIDE_WEATHER_MASTER_KEY="new-secure-master-key"

# Reinitialize credential manager
python3 -c "
from core.secure_credential_manager import SecureCredentialManager
manager = SecureCredentialManager(environment='production')
# Re-store all credentials
"
```

## 📋 Configuration Checklist

### Pre-Deployment Checklist

- [ ] Environment variables configured
- [ ] Master encryption key set
- [ ] Configuration validation passes
- [ ] Credentials stored securely
- [ ] Drift detection enabled
- [ ] Backup strategy implemented
- [ ] Monitoring configured

### Production Readiness Checklist

- [ ] Production environment configured
- [ ] Security credentials rotated
- [ ] Configuration drift monitoring active
- [ ] Health endpoints responding
- [ ] Metrics collection enabled
- [ ] Backup and rollback tested
- [ ] Documentation updated

### Security Checklist

- [ ] No credentials in version control
- [ ] Master key securely stored
- [ ] Access logging enabled
- [ ] Configuration change monitoring active
- [ ] Regular security audits scheduled
- [ ] Incident response procedures documented

## 📚 Reference

### Configuration Files

| File | Purpose | Environment |
|------|---------|-------------|
| `configs/data.yaml` | Base data configuration | All |
| `configs/model.yaml` | Base model configuration | All |
| `configs/training.yaml` | Base training configuration | All |
| `configs/environments/{env}/` | Environment-specific overrides | Specific |

### Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `ENVIRONMENT` | Environment specification | Recommended |
| `ADELAIDE_WEATHER_MASTER_KEY` | Credential encryption key | Production |
| `API_TOKEN` | API authentication token | All |
| `ADELAIDE_*` | Configuration overrides | Optional |

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| Environment Config Manager | `core/environment_config_manager.py` | Multi-environment configuration |
| Secure Credential Manager | `core/secure_credential_manager.py` | Credential storage and encryption |
| Configuration Drift Detector | `core/config_drift_detector.py` | Change monitoring and alerting |
| Deployment Script | `deploy.sh` | Automated deployment with validation |

---

**Adelaide Weather Forecasting System - Configuration Management Guide**  
*Comprehensive configuration management for reliable weather predictions*