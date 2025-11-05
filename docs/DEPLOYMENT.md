# Adelaide Weather Forecasting System - Comprehensive Deployment Guide

## Overview

This document provides comprehensive deployment procedures for the Adelaide Weather Forecasting System, covering both local Docker deployment using the advanced deploy.sh script and cloud infrastructure deployment options.

## 🚀 Deployment Options

### Local Docker Deployment (Primary)

The system includes an advanced deployment script (`deploy.sh`) that provides production-ready local deployment with:
- **Multi-environment support**: Development, staging, production
- **Comprehensive validation**: System requirements, configuration, credentials
- **Health monitoring**: Post-deployment verification and health checks
- **Backup and rollback**: Automatic backup creation and rollback capability
- **Monitoring integration**: Optional Prometheus/Grafana stack

### Cloud Infrastructure Deployment (Advanced)

For enterprise deployments, the system also supports cloud infrastructure deployment (see Advanced Cloud Deployment section).

## 💻 Local Docker Deployment (Recommended)

### System Requirements

- **Docker Engine**: 20.10+ with Docker Compose support
- **Operating System**: Linux, macOS, or Windows with WSL2
- **Memory**: 4GB+ available RAM (recommended)
- **Storage**: 10GB+ available disk space
- **Python**: 3.8+ (for deployment script validation)

### Quick Start

#### 1. Environment Setup

```bash
# Clone the repository
git clone <repository>
cd adelaide-weather-final

# Set required environment variables
export ENVIRONMENT="development"  # or staging, production
export API_TOKEN="your-secure-api-token"

# For production deployment, also set:
export ADELAIDE_WEATHER_MASTER_KEY="your-master-encryption-key"
```

#### 2. Deploy Development Environment

```bash
# Basic development deployment
./deploy.sh development

# Development with monitoring stack
./deploy.sh development --monitoring
```

#### 3. Deploy Staging Environment

```bash
# Staging deployment with monitoring
./deploy.sh staging --monitoring
```

#### 4. Deploy Production Environment

```bash
# Production deployment (with confirmation prompt)
./deploy.sh production --monitoring

# Force production deployment (skip confirmation)
./deploy.sh production --force --monitoring
```

### Advanced Deployment Options

#### Deployment Script Options

```bash
# Show help and usage
./deploy.sh --help

# Deploy with specific options
./deploy.sh production --force           # Skip confirmation prompts
./deploy.sh staging --no-health-check    # Skip health verification
./deploy.sh production --monitoring      # Enable Prometheus/Grafana
./deploy.sh production --rollback        # Rollback to previous deployment
```

#### Environment-Specific Configurations

**Development Environment**
- Docker Compose: `docker-compose.yml` + `docker-compose.dev.yml`
- Frontend: http://localhost:3000
- API: http://localhost:8000
- Hot reload enabled for rapid development

**Staging Environment**
- Docker Compose: `docker-compose.staging.yml`
- Production-like settings for integration testing
- Full validation and monitoring enabled

**Production Environment**
- Docker Compose: `docker-compose.production.yml`
- Nginx reverse proxy with SSL termination
- Comprehensive security and monitoring
- Frontend: http://localhost/
- API: http://localhost/api/

### Deployment Validation

The deployment script performs comprehensive validation:

#### 1. System Requirements Check
- Docker installation and daemon status
- Available memory and disk space
- Docker Compose version compatibility

#### 2. Configuration Validation
- Environment configuration loading and validation
- YAML syntax and schema compliance
- Multi-environment configuration integrity

#### 3. Credential Validation
- Required environment variables
- Secure credential manager initialization
- Production-specific credential requirements

#### 4. Docker Compose Validation
- Compose file syntax validation
- Service dependency verification
- Image build capability check

### Health Monitoring

#### Post-Deployment Health Checks

The deployment script automatically verifies:

```bash
# API Health Check
curl http://localhost:8000/health

# FAISS Health Check
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/health/faiss

# Comprehensive Health Report
curl http://localhost:8000/health/detailed

# Frontend Health Check
curl http://localhost:3000
```

#### System Validation

Integrated startup validation system checks:
- Environment configuration integrity
- Credential manager functionality
- FAISS health monitoring
- Configuration drift detection
- Overall system readiness

### Monitoring Stack (Optional)

Enable comprehensive monitoring with `--monitoring` flag:

#### Prometheus Metrics
- **URL**: http://localhost:9090
- **Features**: System metrics, API metrics, FAISS metrics
- **Retention**: Configurable data retention policies

#### Grafana Dashboards
- **URL**: http://localhost:3001
- **Credentials**: admin/admin (change on first login)
- **Dashboards**: Pre-configured dashboards for all components

### Backup and Rollback

#### Automatic Backup Creation

The deployment script automatically creates backups:

```bash
# Backup location
backups/{environment}/backup-{timestamp}.tar.gz

# Backup contents
- Configuration files (configs/)
- Environment files (.env*)
- Docker Compose files
- Container state information
```

#### Rollback Procedures

```bash
# Automatic rollback on deployment failure
./deploy.sh production --rollback

# Manual rollback
tar -xzf backups/production/backup-20231102-123456.tar.gz
./deploy.sh production --force
```

## 🔍 Deployment Troubleshooting

### Common Issues

#### 1. Docker-related Issues

```bash
# Check Docker daemon
sudo systemctl status docker

# Check Docker Compose installation
docker-compose --version
# or
docker compose version

# Check available resources
docker system df
docker system prune -f  # Clean up if needed
```

#### 2. Configuration Issues

```bash
# Validate environment configuration
python3 -c "
from core.environment_config_manager import EnvironmentConfigManager
try:
    manager = EnvironmentConfigManager(environment='production')
    config = manager.load_config()
    print('✅ Configuration validation passed')
except Exception as e:
    print(f'❌ Configuration error: {e}')
"

# Check configuration drift
python3 demo_config_drift_detector.py
```

#### 3. Credential Issues

```bash
# Check master key
echo "Master key set: ${ADELAIDE_WEATHER_MASTER_KEY:+YES}"

# Test credential manager
python3 demo_credential_manager.py

# Validate API token
echo "API token set: ${API_TOKEN:+YES}"
```

#### 4. Health Check Failures

```bash
# Check service status
docker-compose ps

# Check logs
docker-compose logs api
docker-compose logs frontend

# Manual health check
curl -v http://localhost:8000/health
```

### Recovery Procedures

#### Service Recovery

```bash
# Restart all services
docker-compose down
./deploy.sh {environment}

# Restart specific service
docker-compose restart api
docker-compose restart frontend
```

#### Configuration Recovery

```bash
# Restore from backup
tar -xzf backups/{environment}/backup-{timestamp}.tar.gz

# Validate restored configuration
python3 -c "from core import EnvironmentConfigManager; EnvironmentConfigManager().load_config()"

# Redeploy
./deploy.sh {environment} --force
```

## 🌐 Advanced Cloud Deployment

### Infrastructure Components

## Deployment Pipeline

### 1. Code Quality & Security
- **Python**: Black, isort, flake8, mypy, bandit, safety
- **Frontend**: ESLint, TypeScript, npm audit
- **Security**: CodeQL, dependency scanning, secrets detection
- **Container**: Trivy vulnerability scanning

### 2. Testing
- **API**: Unit tests, integration tests, coverage reporting
- **Frontend**: Jest unit tests, Playwright E2E tests
- **Environment**: Staging integration tests, performance tests

### 3. Container Build
- **Multi-stage builds**: Optimized for production
- **Security scanning**: Trivy container vulnerability scanning
- **Registry**: GitHub Container Registry (ghcr.io)
- **Caching**: Layer caching for faster builds

### 4. Deployment Strategies
- **Development**: Rolling deployment
- **Staging**: Rolling deployment with integration tests
- **Production**: Blue-green deployment with traffic switching

## Getting Started

### Prerequisites
1. **AWS Account** with appropriate permissions
2. **GitHub repository** with Actions enabled
3. **Domain name** and SSL certificate (optional)
4. **Terraform state bucket** configured

### Initial Setup

#### 1. Configure AWS Credentials
```bash
# In GitHub repository secrets
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

#### 2. Setup Terraform State Backend
```bash
# Create S3 bucket for Terraform state
aws s3 mb s3://weather-forecast-terraform-state

# Optional: Create DynamoDB table for state locking
aws dynamodb create-table \
    --table-name terraform-state-lock \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
```

#### 3. Configure Domain (Optional)
```bash
# If using Route53, create hosted zone
aws route53 create-hosted-zone --name weather-forecast.dev --caller-reference $(date +%s)

# Update NS records with your domain registrar
```

#### 4. Initialize Infrastructure
```bash
# Development environment
cd infrastructure/environments/dev
terraform init
terraform plan
terraform apply

# Staging environment
cd ../staging
terraform init
terraform plan
terraform apply
```

## Manual Deployment

### Development Environment
Development deployments are automatic when pushing to the `develop` branch.

```bash
git checkout develop
git push origin develop
```

### Staging Environment
Staging deployments are automatic when pushing to the `main` branch.

```bash
git checkout main
git merge develop
git push origin main
```

### Production Environment
Production deployments require manual approval via GitHub Actions.

1. Navigate to **Actions** tab in GitHub
2. Select **CI/CD Pipeline** workflow
3. Click **Run workflow**
4. Select `prod` environment
5. Confirm deployment

### Ephemeral Environments
Ephemeral environments are automatically created for feature branches.

```bash
git checkout -b feature/new-feature
git push origin feature/new-feature
# Environment automatically created at: https://feature-new-feature.preview.weather-forecast.dev
```

## Monitoring & Alerting

### CloudWatch Dashboards
- **ECS Service Metrics**: CPU, memory, task count
- **Load Balancer Metrics**: Request count, response time, error rates
- **Custom Application Metrics**: API errors, forecast accuracy

### Alerts
- **High CPU/Memory**: > 80% utilization
- **High Error Rate**: > 10 5XX errors in 5 minutes
- **High Response Time**: > 5 seconds average
- **Unhealthy Targets**: Any unhealthy targets detected

### Log Aggregation
- **API Logs**: `/aws/ecs/weather-forecast-{env}/api`
- **Frontend Logs**: `/aws/ecs/weather-forecast-{env}/frontend`
- **Retention**: 7 days (dev), 14 days (staging), 30 days (prod)

## Troubleshooting

### Common Issues

#### 1. Deployment Failures
```bash
# Check ECS service events
aws ecs describe-services --cluster weather-forecast-prod-cluster --services weather-forecast-prod-api

# Check task logs
aws logs get-log-events --log-group-name /ecs/weather-forecast-prod/api --log-stream-name ecs/api/task-id
```

#### 2. Health Check Failures
```bash
# Check target group health
aws elbv2 describe-target-health --target-group-arn arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/weather-forecast-prod-api-tg/1234567890123456

# Test health endpoint directly
curl https://api.weather-forecast.dev/health
```

#### 3. SSL Certificate Issues
```bash
# Check certificate validation
aws acm describe-certificate --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012

# Verify DNS records
dig _acme-challenge.weather-forecast.dev
```

#### 4. Auto Scaling Issues
```bash
# Check scaling policies
aws application-autoscaling describe-scaling-policies --service-namespace ecs

# Check scaling activities
aws application-autoscaling describe-scaling-activities --service-namespace ecs
```

### Rollback Procedures

#### 1. ECS Service Rollback
```bash
# Get previous task definition
aws ecs list-task-definitions --family-prefix weather-forecast-prod-api --sort DESC

# Update service to previous version
aws ecs update-service \
    --cluster weather-forecast-prod-cluster \
    --service weather-forecast-prod-api \
    --task-definition weather-forecast-prod-api:123
```

#### 2. Blue-Green Rollback
```bash
# Switch traffic back to previous environment
cd infrastructure/environments/prod
terraform apply -var="active_environment=green" -auto-approve
```

#### 3. Infrastructure Rollback
```bash
# Revert to previous Terraform state
terraform state pull > current.tfstate
terraform state push previous.tfstate
terraform apply
```

## Security Best Practices

### 1. Container Security
- **Non-root user**: All containers run as non-root
- **Minimal base images**: Using slim Python and Node.js images
- **Security scanning**: Automated with Trivy
- **Regular updates**: Dependabot for dependency updates

### 2. Network Security
- **Private subnets**: Application containers in private subnets
- **Security groups**: Least privilege access
- **WAF**: Web Application Firewall (optional)
- **VPC Flow Logs**: Network traffic monitoring

### 3. Access Control
- **IAM roles**: Least privilege for ECS tasks
- **Secrets management**: AWS Secrets Manager integration
- **API authentication**: Rate limiting and authentication
- **SSL/TLS**: End-to-end encryption

### 4. Monitoring & Compliance
- **Audit logging**: CloudTrail for API calls
- **Configuration compliance**: AWS Config rules
- **Vulnerability management**: Regular security scans
- **Incident response**: Automated alerting and runbooks

## Performance Optimization

### 1. Auto Scaling Configuration
```hcl
# CPU-based scaling
target_cpu_utilization = 70

# Request-based scaling
target_requests_per_target = 1000

# Memory-based scaling
target_memory_utilization = 70
```

### 2. Container Optimization
- **Multi-stage builds**: Minimal production images
- **Layer caching**: Docker build cache optimization
- **Resource limits**: Appropriate CPU/memory allocation
- **Health checks**: Fast and reliable health endpoints

### 3. Load Balancer Optimization
- **Connection draining**: Graceful request handling
- **Sticky sessions**: When needed for stateful applications
- **Compression**: GZIP compression enabled
- **Caching**: CloudFront integration (optional)

## Disaster Recovery

### 1. Backup Strategy
- **Infrastructure**: Terraform state in S3 with versioning
- **Application data**: Automated snapshots
- **Container images**: Multi-region registry replication
- **Configuration**: GitOps with version control

### 2. Recovery Procedures
1. **Infrastructure recreation**: `terraform apply` from backed-up state
2. **Application deployment**: Redeploy from latest working images
3. **Data restoration**: Restore from snapshots
4. **DNS failover**: Route53 health checks and failover

### 3. Testing
- **Monthly**: Disaster recovery testing
- **Quarterly**: Full environment recreation
- **Documentation**: Updated recovery procedures
- **Training**: Team disaster recovery training

## Cost Optimization

### 1. Resource Right-Sizing
- **Fargate Spot**: For development environments
- **Reserved capacity**: For production workloads
- **Auto scaling**: Dynamic capacity adjustment
- **Scheduled scaling**: For predictable traffic patterns

### 2. Monitoring & Alerts
- **Cost budgets**: AWS Budgets with alerts
- **Resource utilization**: CloudWatch metrics
- **Unused resources**: AWS Trusted Advisor
- **Optimization recommendations**: AWS Cost Explorer

## Support & Contact

### Team Contacts
- **DevOps Lead**: devops@yourcompany.com
- **Development Team**: dev@yourcompany.com
- **On-call**: +1-XXX-XXX-XXXX

### Documentation
- **API Documentation**: https://api.weather-forecast.dev/docs
- **Architecture Diagrams**: `/docs/architecture/`
- **Runbooks**: `/docs/runbooks/`
- **Change Log**: `/CHANGELOG.md`

### Emergency Procedures
1. **Critical Issues**: Contact on-call immediately
2. **Service Degradation**: Follow incident response playbook
3. **Security Incidents**: Escalate to security team
4. **Data Issues**: Coordinate with data team

---

**Last Updated**: 2024-10-29  
**Version**: 1.0  
**Next Review**: 2024-11-29