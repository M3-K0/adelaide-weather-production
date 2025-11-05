# Adelaide Weather Forecasting System - Deployment Guide

## Overview

The Adelaide Weather Forecasting System uses a sophisticated deployment script (`deploy.sh`) that handles real deployment scenarios across multiple environments with comprehensive validation, health checks, and rollback capabilities.

## Supported Environments

### Development
- **Purpose**: Local development with hot reload and debug features
- **Configuration**: docker-compose.yml + docker-compose.dev.yml
- **Resources**: Minimal resource allocation, suitable for development
- **Features**: Hot reload, debug logging, relaxed validation

### Staging
- **Purpose**: Production-like environment for integration testing
- **Configuration**: docker-compose.staging.yml
- **Resources**: Moderate resource allocation for realistic testing
- **Features**: Production-like configuration, monitoring available

### Production
- **Purpose**: Full production deployment with monitoring and security
- **Configuration**: docker-compose.production.yml
- **Resources**: Full resource allocation with limits and reservations
- **Features**: Nginx reverse proxy, Redis caching, comprehensive monitoring

## Quick Start

### 1. Prerequisites

```bash
# Ensure Docker and Docker Compose are installed
docker --version
docker-compose --version  # or docker compose version

# Ensure Python dependencies are available
python3 -c "import yaml; print('Python dependencies OK')"
```

### 2. Environment Setup

```bash
# Copy appropriate environment template
cp .env.development.sample .env     # For development
cp .env.staging.sample .env         # For staging  
cp .env.production.sample .env      # For production

# Edit .env file with your configuration
nano .env
```

### 3. Deploy

```bash
# Development deployment
./deploy.sh development

# Staging deployment with monitoring
./deploy.sh staging --monitoring

# Production deployment (requires confirmation)
./deploy.sh production

# Force deployment without confirmation
./deploy.sh production --force
```

## Deployment Script Features

### Advanced Functionality

- **Multi-Environment Support**: Handles development, staging, and production
- **Environment Variables**: Automatic environment variable setup per environment
- **Docker Compose Orchestration**: Manages complex multi-container deployments
- **Health Checks**: Comprehensive health verification before declaring success
- **Error Handling**: Robust error handling with automatic rollback options
- **Configuration Validation**: Validates configurations using Environment Config Manager
- **Backup & Rollback**: Creates backups and supports rollback functionality
- **Monitoring Integration**: Optional monitoring stack deployment
- **Logging**: Comprehensive deployment logging with timestamps

### Command Line Options

```bash
Usage: ./deploy.sh [environment] [options]

Environments:
  development  - Local development with hot reload and debug features
  staging      - Production-like environment for integration testing  
  production   - Full production deployment with monitoring

Options:
  --force            Force deployment without confirmation prompts
  --no-health-check  Skip post-deployment health verification
  --rollback         Rollback to previous deployment
  --monitoring       Enable monitoring stack (Prometheus/Grafana)
  -h, --help         Show this help message
```

### Example Commands

```bash
# Basic deployments
./deploy.sh development              # Deploy to development
./deploy.sh staging                  # Deploy to staging
./deploy.sh production               # Deploy to production

# Advanced deployments
./deploy.sh staging --monitoring     # Deploy staging with monitoring
./deploy.sh production --force       # Force production deployment
./deploy.sh development --no-health-check  # Skip health checks

# Rollback operations
./deploy.sh --rollback production    # Rollback production deployment
./deploy.sh --rollback staging       # Rollback staging deployment
```

## Deployment Process

### 1. Validation Phase

The script performs comprehensive validation before deployment:

- **Environment Validation**: Ensures valid environment specified
- **System Requirements**: Checks Docker, memory, and disk space
- **Environment Configuration**: Validates using Environment Config Manager
- **Credential Validation**: Ensures required credentials are present
- **Docker Compose Validation**: Validates compose file syntax

### 2. Deployment Phase

- **Backup Creation**: Creates backup of current state
- **Deployment Confirmation**: Interactive confirmation (unless --force)
- **Service Shutdown**: Gracefully stops existing services
- **Service Startup**: Builds and starts new services
- **Health Verification**: Waits for services to become healthy

### 3. Verification Phase

- **API Health Check**: Validates API endpoints
- **Frontend Health Check**: Validates frontend availability
- **System Validation**: Runs comprehensive system validation
- **Service Status**: Shows running service status
- **URL Display**: Shows available service URLs

## Environment Configuration

### Development Configuration

```yaml
# configs/environments/development/data.yaml
era5:
  years: [2018, 2020]  # Reduced dataset
  area: [-33.9, 137.6, -35.9, 139.6]  # Smaller domain

preprocessing:
  normalize_method: 'minmax'
  fill_method: 'forward_fill'

gfs:
  lead_times: [6, 24]  # Limited forecast horizons
```

### Staging Configuration

```yaml
# configs/environments/staging/data.yaml
era5:
  years: [2015, 2023]  # Representative dataset
  area: [-33.4, 137.1, -36.4, 140.1]  # Production-scale domain

preprocessing:
  normalize_method: 'zscore'
  fill_method: 'interpolate'

gfs:
  lead_times: [6, 12, 24, 48]  # Core forecast horizons
```

### Production Configuration

```yaml
# configs/environments/production/data.yaml
era5:
  years: [2000, 2023]  # Full historical dataset
  area: [-32.4, 136.1, -37.4, 141.1]  # Full domain

preprocessing:
  normalize_method: 'zscore'
  fill_method: 'interpolate'

gfs:
  lead_times: [6, 12, 24, 48, 72]  # Complete forecast horizons
```

## Health Checks

The deployment script performs comprehensive health checks:

### API Health Check
- HTTP endpoint: `/health`
- Expected response: 200 OK with status information
- Timeout: 10 seconds per attempt
- Retries: Multiple attempts with backoff

### Frontend Health Check
- HTTP endpoint: `/` (root)
- Expected response: 200 OK
- Validates frontend accessibility

### System Validation
- Uses the Expert Validated Startup System
- Validates model integrity, database integrity, FAISS indices
- Ensures temporal alignment and system consistency

## Service URLs

### Development Environment
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Health: http://localhost:8000/health
- API Documentation: http://localhost:8000/docs
- API Metrics: http://localhost:8000/metrics
- Prometheus: http://localhost:9090 (with --monitoring)
- Grafana: http://localhost:3001 (with --monitoring)

### Staging Environment
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Health: http://localhost:8000/health
- API Documentation: http://localhost:8000/docs

### Production Environment
- Frontend: http://localhost
- API: http://localhost/api
- Health: http://localhost/health
- Metrics: http://localhost/metrics
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001

## Backup and Rollback

### Automatic Backups
- Backups created before each deployment
- Stored in `backups/{environment}/` directory
- Include configuration files and container states
- Timestamped for easy identification

### Rollback Process
```bash
# Automatic rollback prompt on deployment failure
# Manual rollback
./deploy.sh --rollback production

# Rollback process:
# 1. Stops current services
# 2. Restores configuration from backup
# 3. Starts services with backup configuration
```

## Monitoring

### Optional Monitoring Stack
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **Redis**: Caching layer (staging/production)

### Enable Monitoring
```bash
# Deploy with monitoring
./deploy.sh staging --monitoring
./deploy.sh production --monitoring

# Development with monitoring
docker-compose --profile monitoring up
```

## Troubleshooting

### Common Issues

#### 1. Port Conflicts
```bash
# Check for port usage
netstat -tulpn | grep :8000
netstat -tulpn | grep :3000

# Stop conflicting services
docker stop $(docker ps -q)
```

#### 2. Resource Issues
```bash
# Check system resources
free -h
df -h
docker system df

# Clean up Docker resources
docker system prune -f
```

#### 3. Configuration Issues
```bash
# Validate configuration
python3 -c "
from core.environment_config_manager import EnvironmentConfigManager
manager = EnvironmentConfigManager(environment='production')
config = manager.load_config()
print('Configuration valid')
"
```

#### 4. Health Check Failures
```bash
# Check service logs
docker-compose logs api
docker-compose logs frontend

# Manual health check
curl -f http://localhost:8000/health
```

### Log Analysis
```bash
# View deployment logs
ls deploy-*.log

# Real-time deployment log
tail -f deploy-production-$(date +%Y%m%d)*.log

# Service logs
docker-compose logs -f api
docker-compose logs -f frontend
```

## Security Considerations

### Production Security
- Use strong API tokens and passwords
- Regularly rotate credentials
- Enable security headers
- Use HTTPS in production
- Regularly update Docker images
- Monitor for security vulnerabilities

### Environment Variables
```bash
# Required for production
API_TOKEN=secure-production-token
GRAFANA_PASSWORD=secure-password
REDIS_PASSWORD=secure-redis-password

# Optional security settings
SSL_CERT_PATH=/etc/nginx/ssl/cert.pem
SSL_KEY_PATH=/etc/nginx/ssl/key.pem
```

## Performance Tuning

### Resource Allocation
- **Development**: Minimal resources for fast iteration
- **Staging**: Moderate resources for realistic testing
- **Production**: Full resource allocation with limits

### Caching Strategy
- **Development**: No caching for immediate feedback
- **Staging**: 3-minute cache TTL for testing
- **Production**: 5-minute cache TTL for performance

### Docker Optimization
```bash
# Production optimizations
- Multi-stage builds
- Layer caching
- Resource limits
- Health checks
- Restart policies
```

## Maintenance

### Regular Maintenance Tasks
1. **Log Rotation**: Monitor and rotate deployment logs
2. **Backup Cleanup**: Remove old backups to save space
3. **Image Updates**: Regularly update base Docker images
4. **Security Updates**: Apply security patches promptly
5. **Performance Monitoring**: Monitor resource usage and performance

### Deployment Best Practices
1. Always test in staging before production
2. Use version tags for production deployments
3. Monitor deployment logs for issues
4. Perform health checks after deployment
5. Have rollback plan ready
6. Document any configuration changes

## Advanced Usage

### CI/CD Integration
```bash
# Automated deployment
./deploy.sh production --force --no-health-check

# With validation
./deploy.sh production --force && ./validate_deployment.sh
```

### Custom Configuration
```bash
# Override environment variables
ENVIRONMENT=production API_TOKEN=custom-token ./deploy.sh production
```

### Multiple Environment Management
```bash
# Deploy multiple environments
./deploy.sh development &
./deploy.sh staging &
wait  # Wait for both to complete
```

This deployment system provides enterprise-grade deployment capabilities with comprehensive validation, monitoring, and rollback features suitable for production use.