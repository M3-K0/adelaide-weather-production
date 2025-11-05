# Adelaide Weather Forecasting System - Comprehensive Deployment Guide

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start Deployment](#quick-start-deployment)
4. [Multi-Environment Deployment](#multi-environment-deployment)
5. [Docker Composition Management](#docker-composition-management)
6. [CI/CD Pipeline Integration](#cicd-pipeline-integration)
7. [Security Configuration](#security-configuration)
8. [Performance Optimization](#performance-optimization)
9. [Monitoring and Observability](#monitoring-and-observability)
10. [Backup and Recovery](#backup-and-recovery)
11. [Rollback Procedures](#rollback-procedures)
12. [Kubernetes Deployment](#kubernetes-deployment)
13. [Cloud Infrastructure Deployment](#cloud-infrastructure-deployment)
14. [Troubleshooting](#troubleshooting)

## 🌐 Overview

The Adelaide Weather Forecasting System provides multiple deployment strategies to meet different operational requirements:

### Deployment Options
- **Local Docker**: Production-ready containerized deployment with Docker Compose
- **Kubernetes**: Cloud-native deployment with Helm charts and Kustomize
- **Cloud Infrastructure**: AWS/Azure/GCP with Terraform infrastructure as code
- **CI/CD Automated**: Fully automated deployment with GitHub Actions

### Key Features
- **Multi-environment support**: development, staging, production
- **Enhanced security**: Token management, encryption, audit trails
- **Comprehensive monitoring**: Prometheus, Grafana, alerting
- **FAISS integration**: High-performance similarity search
- **Auto-scaling**: Kubernetes HPA and resource management
- **Backup/Recovery**: Automated backup and rollback procedures

## 🔧 Prerequisites

### System Requirements

#### Minimum Requirements
- **CPU**: 2 cores
- **Memory**: 4GB RAM
- **Storage**: 10GB available disk space
- **Network**: Internet connectivity for Docker image pulls

#### Recommended Requirements
- **CPU**: 4+ cores
- **Memory**: 8GB+ RAM
- **Storage**: 20GB+ SSD storage
- **Network**: High-speed internet for optimal performance

#### Software Dependencies
- **Docker Engine**: 20.10+ with Docker Compose 2.0+
- **Python**: 3.8+ (for deployment script validation)
- **Git**: Latest version (for CI/CD integration)
- **Kubernetes**: 1.20+ (for Kubernetes deployment)
- **Helm**: 3.0+ (for Helm chart deployment)

### Environment Variables

#### Required Configuration
```bash
# Primary environment identifier
export ENVIRONMENT="production"         # development|staging|production

# Authentication and security
export API_TOKEN="$(openssl rand -hex 32)"
export ADELAIDE_WEATHER_MASTER_KEY="$(openssl rand -hex 32)"

# Optional configuration
export LOG_LEVEL="INFO"                 # DEBUG|INFO|WARNING|ERROR
export CORS_ORIGINS="https://your-domain.com"
```

#### Production Security Requirements
```bash
# Generate secure tokens
export API_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')"
export ADELAIDE_WEATHER_MASTER_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"

# Additional security settings
export RATE_LIMIT_PER_MINUTE=60
export AUDIT_ALL_REQUESTS=true
export SECURITY_LOG_LEVEL=INFO
```

## 🚀 Quick Start Deployment

### Development Environment (5 minutes)

```bash
# 1. Clone and setup
git clone <repository>
cd adelaide-weather-final

# 2. Configure environment
export ENVIRONMENT=development
export API_TOKEN=dev-token-change-in-production

# 3. Deploy with enhanced features
./deploy.sh development --monitoring

# 4. Verify deployment
curl http://localhost:8000/health
curl http://localhost:3000  # Frontend
```

### Staging Environment (10 minutes)

```bash
# 1. Production-like configuration
export ENVIRONMENT=staging
export API_TOKEN="$(openssl rand -hex 32)"
export ADELAIDE_WEATHER_MASTER_KEY="$(openssl rand -hex 32)"

# 2. Deploy with full validation
./deploy.sh staging --monitoring --validate --backup

# 3. Run integration tests
python test_e2e_smoke.py --environment staging
```

### Production Environment (15 minutes)

```bash
# 1. Secure production configuration
export ENVIRONMENT=production
export API_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')"
export ADELAIDE_WEATHER_MASTER_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"

# 2. Deploy with comprehensive validation
./deploy.sh production --monitoring --validate --backup --security-check

# 3. Verify production deployment
curl https://api.your-domain.com/health/detailed
```

## 🏗 Multi-Environment Deployment

### Environment Configuration Structure

```
configs/
├── environments/
│   ├── development/
│   │   ├── data.yaml          # Development data configuration
│   │   └── model.yaml         # Development model configuration
│   ├── staging/
│   │   ├── data.yaml          # Staging configuration
│   │   └── model.yaml         # Staging model configuration
│   └── production/
│       ├── data.yaml          # Production configuration
│       └── model.yaml         # Production model configuration
├── data.yaml                  # Base data configuration
├── model.yaml                 # Base model configuration
└── training.yaml              # Training configuration
```

### Development Environment

**Purpose**: Local development and testing
**Configuration**: Relaxed security, verbose logging, fast startup

```bash
# Development deployment
./deploy.sh development --force

# Environment-specific features
export DEBUG_MODE=true
export VERBOSE_LOGGING=true
export SKIP_STARTUP_VALIDATION=false
export RATE_LIMIT_ENABLED=false

# Access points
curl http://localhost:8000/health
curl http://localhost:3000
```

**Docker Compose**: `docker-compose.yml` + `docker-compose.dev.yml`

### Staging Environment

**Purpose**: Pre-production testing and validation
**Configuration**: Production-like settings with enhanced monitoring

```bash
# Staging deployment with validation
./deploy.sh staging --monitoring --validate

# Environment-specific features
export PERFORMANCE_MODE=true
export ENHANCED_VALIDATION=true
export CONFIG_DRIFT_ENABLED=true

# Automated testing
python test_e2e_smoke.py --environment staging --full-suite
```

**Docker Compose**: `docker-compose.staging.yml`

### Production Environment

**Purpose**: Live production system
**Configuration**: Maximum security, performance, and monitoring

```bash
# Production deployment with all safeguards
./deploy.sh production --monitoring --backup --security-check --validate

# Environment-specific features
export PERFORMANCE_MODE=true
export AUDIT_ALL_REQUESTS=true
export SECURITY_LOG_LEVEL=INFO
export COMPRESSION_ENABLED=true
export NGINX_COMPRESSION=true
```

**Docker Compose**: `docker-compose.production.yml`

## 📦 Docker Composition Management

### Docker Compose Files

#### Base Configuration (`docker-compose.yml`)
```yaml
# Core services configuration
services:
  api:
    build:
      context: ./api
      dockerfile: Dockerfile
    environment:
      - ENVIRONMENT=${ENVIRONMENT}
      - API_TOKEN=${API_TOKEN}
    ports:
      - "8000:8000"
    depends_on:
      - redis
    
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    depends_on:
      - api
      
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

#### Development Override (`docker-compose.dev.yml`)
```yaml
# Development-specific overrides
services:
  api:
    environment:
      - DEBUG_MODE=true
      - VERBOSE_LOGGING=true
    volumes:
      - ./api:/app  # Hot reload
      
  frontend:
    environment:
      - NODE_ENV=development
    volumes:
      - ./frontend:/app
      - /app/node_modules
```

#### Production Configuration (`docker-compose.production.yml`)
```yaml
# Production-optimized configuration
services:
  api:
    image: adelaide-weather-api:production
    environment:
      - PERFORMANCE_MODE=true
      - COMPRESSION_ENABLED=true
    restart: unless-stopped
    
  frontend:
    image: adelaide-weather-frontend:production
    restart: unless-stopped
    
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - api
      - frontend
    restart: unless-stopped
```

### Advanced Deployment Script Features

#### Comprehensive Validation
```bash
# Pre-deployment validation
./deploy.sh production --validate

# Validation includes:
# - Environment variable validation
# - Configuration file validation
# - Docker requirements check
# - Network connectivity test
# - Security configuration audit
```

#### Automatic Backup Creation
```bash
# Deployment with backup
./deploy.sh production --backup

# Backup includes:
# - Docker container configurations
# - Environment configuration files
# - Application data volumes
# - Database snapshots (if applicable)
# - Credential backups (encrypted)
```

#### Health Check Integration
```bash
# Deployment with health verification
./deploy.sh production --health-check

# Health checks include:
# - API endpoint availability
# - FAISS index health
# - Configuration consistency
# - Security status validation
# - Performance baseline check
```

## 🔄 CI/CD Pipeline Integration

### GitHub Actions Workflow

#### Comprehensive CI/CD Pipeline (`.github/workflows/deploy.yml`)
```yaml
name: Comprehensive Deployment Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
          
      - name: Install dependencies
        run: |
          cd api
          pip install -r requirements.txt
          
      - name: Run unit tests
        run: |
          cd api
          python -m pytest test_api.py -v --cov=. --cov-report=xml
          
      - name: Run security scan
        run: |
          pip install bandit safety
          bandit -r api/ -f json -o security-report.json
          safety check -r api/requirements.txt

  build:
    needs: test
    runs-on: ubuntu-latest
    outputs:
      image-digest: ${{ steps.build.outputs.digest }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Docker Buildx
        uses: docker/setup-buildx-action@v3
        
      - name: Login to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
          
      - name: Build and push API image
        id: build
        uses: docker/build-push-action@v5
        with:
          context: ./api
          file: ./api/Dockerfile.production
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-api:latest
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-api:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    environment: staging
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to staging
        run: |
          export ENVIRONMENT=staging
          export API_TOKEN="${{ secrets.STAGING_API_TOKEN }}"
          export ADELAIDE_WEATHER_MASTER_KEY="${{ secrets.STAGING_MASTER_KEY }}"
          ./deploy.sh staging --monitoring --validate

  deploy-production:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to production
        run: |
          export ENVIRONMENT=production
          export API_TOKEN="${{ secrets.PRODUCTION_API_TOKEN }}"
          export ADELAIDE_WEATHER_MASTER_KEY="${{ secrets.PRODUCTION_MASTER_KEY }}"
          ./deploy.sh production --monitoring --backup --validate --security-check
          
      - name: Run smoke tests
        run: |
          python test_e2e_smoke.py --environment production
          
      - name: Notify deployment success
        run: |
          curl -X POST "${{ secrets.SLACK_WEBHOOK_URL }}" \
            -H "Content-Type: application/json" \
            -d '{"text":"✅ Production deployment successful"}'
```

#### Quality Gates
- **Unit Tests**: >90% code coverage required
- **Security Scanning**: No HIGH or CRITICAL vulnerabilities
- **Performance Tests**: Response time <150ms P95
- **Integration Tests**: All E2E scenarios pass
- **Contract Tests**: API contract compliance

### Deployment Environments

#### Environment Configuration
```bash
# Development (automatic deployment)
- Trigger: Push to develop branch
- Features: Debug mode, verbose logging
- Validation: Basic tests only
- Monitoring: Development metrics

# Staging (automated with approval)
- Trigger: Push to develop branch
- Features: Production-like configuration
- Validation: Full test suite
- Monitoring: Enhanced monitoring

# Production (manual approval required)
- Trigger: Push to main branch
- Features: Maximum security and performance
- Validation: Comprehensive validation
- Monitoring: Full observability stack
```

## 🔐 Security Configuration

### Token Management

#### Secure Token Generation
```bash
# Generate production-grade API token
export API_TOKEN="$(python3 -c '
import secrets
import string
alphabet = string.ascii_letters + string.digits + ".-_"
token = "".join(secrets.choice(alphabet) for _ in range(64))
print(token)
')"

# Generate master encryption key
export ADELAIDE_WEATHER_MASTER_KEY="$(python3 -c '
import secrets
print(secrets.token_hex(32))
')"

# Validate token strength
python api/token_rotation_cli.py validate
```

#### Token Rotation Procedures
```bash
# Manual token rotation
python api/token_rotation_cli.py rotate --user admin

# Automated rotation (production)
python api/token_rotation_cli.py rotate --schedule weekly

# Emergency rotation
python api/token_rotation_cli.py rotate --emergency
```

### Security Hardening

#### Production Security Configuration
```bash
# Security middleware settings
export SECURITY_MIDDLEWARE=true
export RATE_LIMIT_PER_MINUTE=60
export AUDIT_ALL_REQUESTS=true
export LOG_CLIENT_IPS=true

# Enhanced validation
export ENHANCED_VALIDATION=true
export INPUT_SANITIZATION=true
export SECURITY_HEADERS=true

# Credential management
export CREDENTIAL_ENCRYPTION=true
export SECURE_AUDIT_LOGGING=true
```

#### Security Monitoring
```bash
# Real-time security monitoring
curl -H "Authorization: Bearer $API_TOKEN" \
  "https://api.your-domain.com/monitor/security"

# Security audit summary
curl -H "Authorization: Bearer $API_TOKEN" \
  "https://api.your-domain.com/admin/security"
```

## ⚡ Performance Optimization

### Performance Configuration

#### High-Performance Settings
```bash
# Performance optimization
export PERFORMANCE_MODE=true
export COMPRESSION_ENABLED=true
export RESPONSE_CACHING=true
export NGINX_COMPRESSION=true

# FAISS optimization
export FAISS_LAZY_LOAD=true
export FAISS_CPU_THREADS=4
export FAISS_CACHE_TTL=300

# Memory optimization
export MEMORY_OPTIMIZATION=true
export PYTHON_GC_AGGRESSIVE=true
```

#### Performance Profiles

##### High-Throughput Profile
```bash
export PERFORMANCE_MODE=high_throughput
export CACHE_MAX_SIZE=5000
export FAISS_CPU_THREADS=8
export COMPRESSION_LEVEL=3
```

##### Low-Latency Profile
```bash
export PERFORMANCE_MODE=low_latency
export CACHE_MAX_SIZE=2000
export FAISS_LAZY_LOAD=false
export COMPRESSION_ENABLED=false
```

##### Memory-Optimized Profile
```bash
export PERFORMANCE_MODE=memory_optimized
export MEMORY_OPTIMIZATION=true
export CACHE_MAX_SIZE=500
export PYTHON_GC_AGGRESSIVE=true
```

## 📊 Monitoring and Observability

### Prometheus and Grafana Stack

#### Deploy with Monitoring
```bash
# Deploy with full monitoring stack
./deploy.sh production --monitoring

# Manual monitoring deployment
docker-compose -f docker-compose.production.yml \
               -f monitoring/docker-compose.monitoring.yml up -d
```

#### Monitoring Stack Components
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **Alertmanager**: Alert routing and management
- **Node Exporter**: System metrics
- **Blackbox Exporter**: Endpoint monitoring

#### Key Dashboards
- **API Performance**: Response times, throughput, SLA compliance
- **System Health**: CPU, memory, disk usage
- **FAISS Performance**: Search latency, index health
- **Security Events**: Authentication, rate limiting, violations
- **Infrastructure**: Docker containers, network, storage

#### Access Points
```bash
# Grafana (default credentials: admin/admin)
open http://localhost:3001

# Prometheus
open http://localhost:9090

# Alertmanager
open http://localhost:9093
```

### Alerting Configuration

#### Critical Alerts
```bash
# Configure alert webhooks
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
export PAGERDUTY_ROUTING_KEY="your-routing-key"

# Alert conditions
- API response time > 500ms (P95)
- Error rate > 5%
- FAISS search time > 5ms
- Memory usage > 85%
- Authentication failures > 10/minute
```

## 💾 Backup and Recovery

### Automated Backup

#### Backup Creation
```bash
# Create comprehensive backup
./deploy.sh production --backup

# Manual backup
BACKUP_DATE=$(date +%Y%m%d-%H%M%S)
mkdir -p backups/production/backup-$BACKUP_DATE

# Backup components
docker-compose config > backups/production/backup-$BACKUP_DATE/docker-compose.yml
cp -r configs/ backups/production/backup-$BACKUP_DATE/
cp .env.production backups/production/backup-$BACKUP_DATE/
```

#### Backup Contents
- **Configuration files**: All YAML and environment files
- **Container state**: Docker Compose configuration
- **Application data**: Volumes and persistent data
- **Credentials**: Encrypted credential backups
- **Database dumps**: If applicable
- **SSL certificates**: Security certificates

### Recovery Procedures

#### Full System Recovery
```bash
# Recover from backup
BACKUP_ID="20251105-120000"
BACKUP_DIR="backups/production/backup-$BACKUP_ID"

# Stop current deployment
docker-compose down

# Restore configuration
cp $BACKUP_DIR/.env.production ./
cp -r $BACKUP_DIR/configs/ ./

# Restore and deploy
docker-compose -f $BACKUP_DIR/docker-compose.yml up -d

# Verify recovery
./deploy.sh production --verify-only
```

## 🔄 Rollback Procedures

### Automatic Rollback

#### Deploy with Auto-Rollback
```bash
# Deploy with automatic rollback on failure
./deploy.sh production --auto-rollback

# Rollback triggers:
# - Health check failures
# - Startup validation errors
# - Critical performance degradation
# - Security violations
```

### Manual Rollback

#### Quick Rollback
```bash
# Rollback to previous version
./deploy.sh production --rollback

# Rollback to specific backup
./deploy.sh production --rollback --backup-id 20251105-120000

# Emergency rollback (fastest)
./deploy.sh production --emergency-rollback
```

#### Rollback Verification
```bash
# Verify rollback success
curl https://api.your-domain.com/health/detailed
curl https://api.your-domain.com/version

# Run post-rollback tests
python test_e2e_smoke.py --environment production
```

## ☸️ Kubernetes Deployment

### Helm Chart Deployment

#### Install with Helm
```bash
# Add Helm repository (if applicable)
helm repo add adelaide-weather ./helm

# Install with default values
helm install adelaide-weather ./helm/adelaide-weather-forecast \
  --namespace weather-forecast-prod \
  --create-namespace

# Install with custom values
helm install adelaide-weather ./helm/adelaide-weather-forecast \
  --namespace weather-forecast-prod \
  --values values.production.yaml
```

#### Helm Values Configuration (`values.production.yaml`)
```yaml
# Production Helm values
replicaCount: 3

image:
  repository: ghcr.io/your-org/adelaide-weather-api
  tag: "v2.0.0"
  pullPolicy: IfNotPresent

service:
  type: LoadBalancer
  port: 80

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: api.your-domain.com
      paths:
        - path: /
          pathType: Prefix

resources:
  limits:
    cpu: 2000m
    memory: 4Gi
  requests:
    cpu: 1000m
    memory: 2Gi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
    namespace: monitoring
```

### Kustomize Deployment

#### Deploy with Kustomize
```bash
# Deploy base configuration
kubectl apply -k k8s/base

# Deploy production overlay
kubectl apply -k k8s/overlays/production

# Deploy staging overlay
kubectl apply -k k8s/overlays/staging
```

#### Kustomization Structure
```
k8s/
├── base/
│   ├── api-deployment.yaml
│   ├── api-service.yaml
│   ├── frontend-deployment.yaml
│   ├── frontend-service.yaml
│   ├── ingress.yaml
│   ├── monitoring-config.yaml
│   └── kustomization.yaml
└── overlays/
    ├── production/
    │   ├── kustomization.yaml
    │   ├── production-hpa.yaml
    │   ├── production-monitoring.yaml
    │   └── production-patches.yaml
    └── staging/
        ├── kustomization.yaml
        └── staging-patches.yaml
```

### Kubernetes Operations

#### Health Checks
```bash
# Check pod status
kubectl get pods -n weather-forecast-prod

# Check service status
kubectl get services -n weather-forecast-prod

# Check ingress status
kubectl get ingress -n weather-forecast-prod

# View logs
kubectl logs -l app=api -n weather-forecast-prod --tail=100
```

#### Scaling Operations
```bash
# Manual scaling
kubectl scale deployment api --replicas=5 -n weather-forecast-prod

# Horizontal Pod Autoscaler
kubectl get hpa -n weather-forecast-prod

# Vertical Pod Autoscaler (if enabled)
kubectl get vpa -n weather-forecast-prod
```

## ☁️ Cloud Infrastructure Deployment

### Terraform Infrastructure

#### AWS Deployment
```bash
# Initialize Terraform
cd terraform/environments/production
terraform init

# Plan deployment
terraform plan -var-file="production.tfvars"

# Apply infrastructure
terraform apply -var-file="production.tfvars"

# Deploy application
kubectl apply -k ../../../k8s/overlays/production
```

#### Azure Deployment
```bash
# Azure-specific deployment
cd infrastructure/environments/prod
terraform init
terraform plan -var-file="azure-prod.tfvars"
terraform apply
```

#### GCP Deployment
```bash
# GCP-specific deployment
cd infrastructure/environments/prod
terraform init
terraform plan -var-file="gcp-prod.tfvars"
terraform apply
```

### Infrastructure Components

#### AWS Infrastructure
- **EKS Cluster**: Managed Kubernetes service
- **RDS**: Managed database service
- **ElastiCache**: Redis caching layer
- **Application Load Balancer**: Traffic distribution
- **Auto Scaling Groups**: Automatic scaling
- **CloudWatch**: Monitoring and logging

#### Monitoring Integration
- **CloudWatch**: AWS native monitoring
- **Prometheus**: Kubernetes monitoring
- **Grafana**: Visualization
- **Alert Manager**: Alert routing

## 🔧 Troubleshooting

### Common Deployment Issues

#### Port Conflicts
```bash
# Check port usage
netstat -tlnp | grep :8000
lsof -i :8000

# Solution: Change port or stop conflicting service
export PORT=8001
./deploy.sh development
```

#### Docker Issues
```bash
# Docker daemon not running
sudo systemctl start docker

# Permission issues
sudo usermod -aG docker $USER
newgrp docker

# Container build failures
docker system prune -a
./deploy.sh development --force
```

#### Environment Variable Issues
```bash
# Verify environment variables
echo "Environment: $ENVIRONMENT"
echo "API Token: ${API_TOKEN:0:10}..."

# Validate configuration
python3 -c "from core import EnvironmentConfigManager; EnvironmentConfigManager().load_config()"
```

#### Health Check Failures
```bash
# Check API health
curl http://localhost:8000/health/detailed

# Check logs
docker-compose logs api --tail=50

# Check container status
docker-compose ps
```

### Performance Issues

#### High Response Times
```bash
# Check performance metrics
curl -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/admin/performance"

# Enable performance optimizations
export PERFORMANCE_MODE=true
export COMPRESSION_ENABLED=true
./deploy.sh production --force
```

#### Memory Issues
```bash
# Check memory usage
docker stats

# Enable memory optimization
export MEMORY_OPTIMIZATION=true
export PYTHON_GC_AGGRESSIVE=true
./deploy.sh production --force
```

### Monitoring and Debugging

#### Log Analysis
```bash
# Application logs
docker-compose logs api --tail=100 --follow

# System logs
docker-compose logs --tail=100

# Specific service logs
docker-compose logs nginx --tail=50
```

#### Health Diagnostics
```bash
# Comprehensive health check
curl -s http://localhost:8000/health/detailed | jq '.'

# FAISS health check
curl -s -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/health/faiss" | jq '.'

# Performance diagnostics
curl -s -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/monitor/live" | jq '.'
```

## 📞 Support and Maintenance

### Operational Contacts

| Severity | Contact Method | Response Time |
|----------|----------------|---------------|
| Critical | PagerDuty + Slack | < 5 minutes |
| High | Slack alerts | < 15 minutes |
| Medium | Email | < 2 hours |
| Low | Documentation | Next business day |

### Regular Maintenance

#### Daily Tasks
- Monitor system health dashboards
- Review security alerts
- Check backup completion
- Validate performance metrics

#### Weekly Tasks
- Review security audit logs
- Performance optimization review
- Backup verification
- Dependency updates

#### Monthly Tasks
- Security audit and penetration testing
- Performance baseline updates
- Disaster recovery testing
- Infrastructure cost optimization

## 🎯 Next Steps

After successful deployment:

1. **Configure Monitoring**: Set up alerting thresholds
2. **Security Hardening**: Implement additional security measures
3. **Performance Tuning**: Optimize for your specific workload
4. **Backup Verification**: Test backup and recovery procedures
5. **Documentation**: Customize operational procedures
6. **Training**: Train operations team on system management

For additional support, refer to:
- [Operational Runbooks](OPERATIONAL_RUNBOOKS.md)
- [Security Documentation](SECURE_CREDENTIAL_MANAGEMENT.md)
- [Performance Tuning Guide](../api/PERFORMANCE_CONFIG.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)