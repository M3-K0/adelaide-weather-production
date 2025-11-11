# Adelaide Weather System - Complete Deployment Guide

## Table of Contents
- [Overview](#overview)
- [Quick Start](#quick-start)
- [System Requirements](#system-requirements)
- [Pre-Installation Setup](#pre-installation-setup)
- [Deployment Process](#deployment-process)
- [System Architecture](#system-architecture)
- [Configuration Options](#configuration-options)
- [Health Monitoring](#health-monitoring)
- [Troubleshooting](#troubleshooting)
- [Production Operations](#production-operations)
- [Security Configuration](#security-configuration)
- [Performance Tuning](#performance-tuning)

## Overview

The Adelaide Weather System is a production-ready analog ensemble weather forecasting system that provides real-time weather forecasts using advanced machine learning and historical pattern matching. This guide covers complete deployment procedures from development to production environments.

### Key Features
- **Real-time forecasting** with 6h, 12h, 24h, and 48h horizons
- **FAISS-powered analog search** for historical pattern matching
- **Uncertainty quantification** with confidence intervals
- **Complete monitoring stack** with Prometheus and Grafana
- **Production-ready security** with authentication and SSL
- **Auto-deployment** with comprehensive validation

### Architecture Components
- **API Server**: FastAPI-based REST API for forecast generation
- **Frontend**: Next.js React application for user interface
- **NGINX**: Reverse proxy with SSL termination and load balancing
- **Redis**: Caching and session management
- **Prometheus**: Metrics collection and monitoring
- **Grafana**: Visualization and alerting dashboards
- **AlertManager**: Alert routing and notification management

## Quick Start

### One-Command Deployment

```bash
# Clone the repository
git clone https://github.com/your-org/adelaide-weather-final.git
cd adelaide-weather-final

# Deploy the complete system
./deploy-adelaide-weather.sh
```

This single command will:
1. Validate all prerequisites
2. Generate SSL certificates
3. Build and start all services
4. Run comprehensive validation tests
5. Display access information and credentials

### Quick Access After Deployment

Once deployment completes successfully:

- **Main Application**: http://localhost (HTTPS: https://localhost)
- **API Documentation**: http://localhost/docs
- **Grafana Dashboard**: http://localhost:3001
- **Prometheus Metrics**: http://localhost:9090
- **System Health**: http://localhost/api/health

## System Requirements

### Minimum Requirements
- **CPU**: 2 cores (4+ cores recommended)
- **Memory**: 6GB RAM (8GB+ recommended)
- **Storage**: 10GB available disk space
- **Network**: Internet connection for Docker image downloads

### Software Dependencies
- **Docker Engine**: 20.10+ with Docker Compose support
- **Docker Compose**: 2.0+ (included with Docker Desktop)
- **Operating System**: 
  - Linux (Ubuntu 20.04+, CentOS 8+, RHEL 8+)
  - macOS (10.15+)
  - Windows 10/11 with WSL2

### Supported Platforms
- **Development**: Docker Desktop on macOS/Windows, Docker Engine on Linux
- **Production**: Linux servers, AWS EC2, Azure VMs, Google Cloud VMs
- **Container Orchestration**: Kubernetes (optional, see k8s/ directory)

## Pre-Installation Setup

### 1. Install Docker and Docker Compose

#### Ubuntu/Debian
```bash
# Update package index
sudo apt-get update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker-compose --version
```

#### CentOS/RHEL
```bash
# Install Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER
```

#### macOS/Windows
Download and install Docker Desktop from https://www.docker.com/products/docker-desktop

### 2. Prepare FAISS Data

The system requires pre-built FAISS indices and embedding data:

```bash
# Check if data exists
ls -la indices/ embeddings/ outcomes/

# If data is missing, build it (requires significant time and resources)
python scripts/generate_embeddings.py
python scripts/build_indices.py
python scripts/build_outcomes_database.py
```

**Note**: Building FAISS data from scratch can take 2-4 hours and requires substantial memory (16GB+). Pre-built data files are recommended for most deployments.

### 3. System Permissions

Ensure proper permissions for deployment:

```bash
# Make deployment script executable
chmod +x deploy-adelaide-weather.sh

# Create necessary directories
mkdir -p logs deployment_logs validation_scripts

# Set ownership (if needed)
sudo chown -R $USER:$USER .
```

## Deployment Process

### Deployment Script Options

The `deploy-adelaide-weather.sh` script supports multiple operations:

```bash
# Full deployment (default)
./deploy-adelaide-weather.sh

# View system status
./deploy-adelaide-weather.sh status

# View service logs
./deploy-adelaide-weather.sh logs          # All services
./deploy-adelaide-weather.sh logs api      # Specific service

# Restart services
./deploy-adelaide-weather.sh restart

# Stop all services
./deploy-adelaide-weather.sh stop

# Run health checks
./deploy-adelaide-weather.sh health

# Rollback failed deployment
./deploy-adelaide-weather.sh rollback

# View help
./deploy-adelaide-weather.sh --help
```

### Deployment Process Steps

The deployment script executes 8 comprehensive steps:

1. **Prerequisites Validation** (30-60 seconds)
   - Docker installation and daemon status
   - Docker Compose availability
   - System resources (CPU, memory, disk)
   - Required files and directories
   - FAISS data availability

2. **Environment Setup** (5-10 seconds)
   - Deployment logging configuration
   - Directory structure creation
   - Permission settings

3. **Configuration Generation** (10-15 seconds)
   - Production environment file generation
   - SSL certificate creation (self-signed for local deployment)
   - Security token generation

4. **Image Building** (3-5 minutes)
   - Base image pulling
   - Application image building
   - Progress indication with spinners

5. **Service Startup** (2-3 minutes)
   - Sequenced service startup
   - Health check validation per service
   - Dependency management

6. **Validation Script Creation** (5-10 seconds)
   - System validation script generation
   - Performance test script creation
   - Security validation script generation

7. **System Validation** (30-45 seconds)
   - Comprehensive health checks
   - API endpoint testing
   - Performance validation
   - Security validation

8. **End-to-End Testing** (30-60 seconds)
   - Complete forecast workflow testing
   - Analog search validation
   - Integration testing

### Environment-Specific Deployment

#### Development Environment
```bash
# Development with hot-reloading and debugging
cp docker-compose.dev.yml docker-compose.yml
export ENVIRONMENT=development
./deploy-adelaide-weather.sh
```

#### Staging Environment
```bash
# Staging with production-like settings
cp docker-compose.staging.yml docker-compose.yml
export ENVIRONMENT=staging
./deploy-adelaide-weather.sh
```

#### Production Environment
```bash
# Production with full security and monitoring
cp docker-compose.production.yml docker-compose.yml
export ENVIRONMENT=production
./deploy-adelaide-weather.sh
```

## System Architecture

### Service Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Grafana       │    │  AlertManager   │
│   (Next.js)     │    │  (Monitoring)   │    │   (Alerts)      │
│   Port: 3000    │    │   Port: 3001    │    │   Port: 9093    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐              │
│      NGINX      │    │   Prometheus    │              │
│  (Reverse Proxy)│    │   (Metrics)     │              │
│   Port: 80/443  │    │   Port: 9090    │              │
└─────────────────┘    └─────────────────┘              │
         │                       │                       │
         │                       │                       │
┌─────────────────┐              │              ┌─────────────────┐
│   API Server    │              │              │     Redis       │
│   (FastAPI)     │──────────────┼──────────────│   (Cache)       │
│   Port: 8000    │              │              │   Port: 6379    │
└─────────────────┘              │              └─────────────────┘
         │                       │                       │
         │                       │                       │
┌─────────────────────────────────────────────────────────────────┐
│                    Shared Volumes                               │
│   - FAISS Indices (indices/)                                   │
│   - Embeddings (embeddings/)                                   │
│   - Outcomes Data (outcomes/)                                  │
│   - Configuration (configs/)                                   │
│   - SSL Certificates (nginx/ssl/)                             │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   User Request  │────▶│      NGINX      │────▶│   API Server    │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                          │
                                                          │
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Response      │◀────│      Redis      │◀────│ FAISS Search    │
│                 │     │    (Cache)      │     │   (Analog)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Network Configuration

```yaml
# Default network configuration
networks:
  adelaide-weather:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

# Service network assignments
services:
  api:      172.20.0.10
  frontend: 172.20.0.20
  nginx:    172.20.0.30
  redis:    172.20.0.40
  prometheus: 172.20.0.50
  grafana:    172.20.0.60
```

## Configuration Options

### Environment Variables

The system supports extensive configuration through environment variables:

#### Core Application Settings
```bash
# Application version and build info
VERSION=2.0.0
BUILD_DATE=2024-01-15T12:00:00Z
VCS_REF=abc123

# API Configuration
API_TOKEN=your-secure-token-here
CORS_ORIGINS=http://localhost,http://localhost:3000,https://localhost
TRUSTED_HOSTS=localhost,127.0.0.1,*.adelaide-weather.local
```

#### Performance Settings
```bash
# Logging and caching
LOG_LEVEL=INFO
PERFORMANCE_CACHE_TTL=300
COMPRESSION_ENABLED=true
NGINX_COMPRESSION=true

# Rate limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_ENABLED=true
```

#### Monitoring Configuration
```bash
# Prometheus and Grafana
PROMETHEUS_ENABLED=true
MONITORING_ENABLED=true
GRAFANA_PASSWORD=secure-password
GRAFANA_SECRET_KEY=32-character-secret
METRICS_COLLECTION_INTERVAL=30
```

#### Security Settings
```bash
# Token management
TOKEN_ROTATION_ENABLED=true
TOKEN_ROTATION_INTERVAL_HOURS=24

# Configuration monitoring
CONFIG_DRIFT_REALTIME_ENABLED=true
```

### Docker Compose Configurations

The system includes multiple Docker Compose configurations for different deployment scenarios:

- `docker-compose.yml`: Default development configuration
- `docker-compose.dev.yml`: Development with hot-reloading
- `docker-compose.staging.yml`: Staging environment
- `docker-compose.production.yml`: Production environment
- `docker-compose.minimal.yml`: Minimal services only
- `docker-compose.lite.yml`: Lightweight configuration

### SSL Certificate Configuration

#### Self-Signed Certificates (Default)
```bash
# Certificates are automatically generated during deployment
ls -la nginx/ssl/
# cert.pem - SSL certificate
# key.pem  - Private key
# dhparam.pem - Diffie-Hellman parameters
```

#### Custom Certificates
```bash
# Replace self-signed certificates with your own
cp your-certificate.crt nginx/ssl/cert.pem
cp your-private-key.key nginx/ssl/key.pem

# Restart NGINX to apply changes
docker-compose restart nginx
```

## Health Monitoring

### Built-in Health Checks

The system includes comprehensive health monitoring at multiple levels:

#### System Health Endpoints
```bash
# Basic health check
curl http://localhost/api/health

# Kubernetes liveness probe
curl http://localhost/api/health/live

# Kubernetes readiness probe
curl http://localhost/api/health/ready

# Detailed health report
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost/api/health/detailed
```

#### FAISS-Specific Health Monitoring
```bash
# FAISS index health
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost/api/health/faiss

# Startup validation status
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost/api/health/startup

# Configuration health
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost/api/health/config
```

### Grafana Dashboards

Access comprehensive monitoring dashboards at http://localhost:3001:

- **System Overview**: Resource usage, service status, alert summary
- **API Performance**: Request rates, response times, error rates
- **FAISS Monitoring**: Index status, search performance, memory usage
- **Security Dashboard**: Authentication events, security alerts
- **Application Metrics**: Forecast generation metrics, analog search performance

### Prometheus Metrics

View raw metrics at http://localhost:9090:

```prometheus
# Example key metrics
forecast_requests_total          # Total forecast requests
response_duration_seconds        # Response time histogram
faiss_search_duration_seconds   # FAISS search performance
system_memory_usage_bytes       # Memory usage
api_errors_total                 # API error count
```

### Alerting Rules

The system includes pre-configured alerts for:

- **High Error Rate**: API error rate > 5%
- **Slow Response Time**: 95th percentile > 2 seconds
- **FAISS Performance**: Search time > 1 second
- **System Resources**: Memory/CPU usage > 80%
- **Service Down**: Any service unhealthy for > 1 minute

## Troubleshooting

### Common Issues and Solutions

#### 1. Docker Permission Errors
```bash
# Error: permission denied while trying to connect to Docker daemon
# Solution: Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Or run with sudo (not recommended for production)
sudo ./deploy-adelaide-weather.sh
```

#### 2. Port Conflicts
```bash
# Error: Port 80/443/3000 already in use
# Solution: Stop conflicting services or change ports

# Check what's using the port
sudo lsof -i :80
sudo lsof -i :443

# Stop conflicting services
sudo systemctl stop apache2
sudo systemctl stop nginx

# Or modify port configuration in docker-compose.yml
```

#### 3. Insufficient Memory
```bash
# Error: Container killed due to OOM
# Solution: Increase available memory or reduce services

# Check memory usage
free -h
docker stats

# Stop non-essential services
docker-compose stop grafana alertmanager

# Or increase system memory allocation
```

#### 4. FAISS Data Missing
```bash
# Error: FAISS indices not found
# Solution: Ensure data files are present

ls -la indices/ embeddings/ outcomes/

# If missing, build data (time-intensive)
python scripts/generate_embeddings.py
python scripts/build_indices.py
python scripts/build_outcomes_database.py
```

#### 5. SSL Certificate Issues
```bash
# Error: SSL handshake failed
# Solution: Regenerate certificates

rm -f nginx/ssl/cert.pem nginx/ssl/key.pem
./deploy-adelaide-weather.sh

# Or use HTTP instead of HTTPS
curl http://localhost/api/health  # instead of https://
```

### Debugging Commands

#### Service Status and Logs
```bash
# View all service status
./deploy-adelaide-weather.sh status

# View logs for all services
./deploy-adelaide-weather.sh logs

# View logs for specific service
./deploy-adelaide-weather.sh logs api
./deploy-adelaide-weather.sh logs frontend
./deploy-adelaide-weather.sh logs nginx

# Follow logs in real-time
docker-compose logs -f api
```

#### Container Debugging
```bash
# Enter container for debugging
docker exec -it adelaide-weather_api_1 /bin/bash
docker exec -it adelaide-weather_frontend_1 /bin/sh

# View container resource usage
docker stats

# Inspect container configuration
docker inspect adelaide-weather_api_1
```

#### Network Debugging
```bash
# Test internal connectivity
docker exec adelaide-weather_api_1 curl http://redis:6379
docker exec adelaide-weather_frontend_1 curl http://api:8000/health

# Test external connectivity
curl -v http://localhost/api/health
curl -v https://localhost/api/health -k
```

### Log Locations

```bash
# Deployment logs
deployment_logs/deploy-YYYYMMDD-HHMMSS.log

# Service-specific logs
logs/api/
logs/frontend/
logs/nginx/

# Docker Compose logs
docker-compose logs > all-services.log
```

### Validation Scripts

The deployment creates validation scripts in `validation_scripts/`:

```bash
# Run system validation
./validation_scripts/system_validation.sh

# Run performance validation
./validation_scripts/performance_validation.sh

# Run security validation
./validation_scripts/security_validation.sh
```

## Production Operations

### Backup Procedures

#### Automated Backup
```bash
# Create system backup
./deploy-adelaide-weather.sh backup

# Backup includes:
# - Configuration files (.env.production)
# - SSL certificates (nginx/ssl/)
# - Deployment logs
# - FAISS indices and data
```

#### Manual Backup
```bash
# Create manual backup
tar -czf adelaide-weather-backup-$(date +%Y%m%d).tar.gz \
  .env.production \
  nginx/ssl/ \
  indices/ \
  embeddings/ \
  outcomes/ \
  configs/ \
  deployment_logs/
```

### Update Procedures

#### Application Updates
```bash
# Stop services
./deploy-adelaide-weather.sh stop

# Pull latest code
git pull origin main

# Rebuild and restart
./deploy-adelaide-weather.sh
```

#### Security Updates
```bash
# Update base images
docker-compose pull

# Rebuild with latest security patches
docker-compose build --no-cache

# Restart services
./deploy-adelaide-weather.sh restart
```

### Scaling Considerations

#### Horizontal Scaling
```bash
# Scale API service
docker-compose up -d --scale api=3

# Scale with load balancing (requires nginx configuration)
# See nginx/nginx.conf for upstream configuration
```

#### Vertical Scaling
```yaml
# Increase resource limits in docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
```

### Monitoring and Alerting

#### Production Monitoring Stack
```bash
# Enable full monitoring
export PROMETHEUS_ENABLED=true
export GRAFANA_PASSWORD=secure-production-password
./deploy-adelaide-weather.sh
```

#### Custom Alerts
```yaml
# Add custom alerts in monitoring/alerts.yml
groups:
  - name: custom.rules
    rules:
      - alert: CustomAlert
        expr: custom_metric > threshold
        for: 5m
        annotations:
          summary: "Custom alert triggered"
```

## Security Configuration

### Authentication and Authorization

#### API Token Management
```bash
# Generate secure API token
export API_TOKEN=$(openssl rand -hex 32)

# Set in environment file
echo "API_TOKEN=$API_TOKEN" >> .env.production

# Rotate token (if enabled)
./deploy-adelaide-weather.sh rotate-token
```

#### Token Rotation
```bash
# Enable automatic rotation
export TOKEN_ROTATION_ENABLED=true
export TOKEN_ROTATION_INTERVAL_HOURS=24

# Manual rotation
curl -X POST -H "Authorization: Bearer $API_TOKEN" \
  http://localhost/api/admin/token/rotate
```

### SSL/TLS Configuration

#### Production SSL Setup
```bash
# Use Let's Encrypt for production
certbot certonly --webroot -w nginx/ssl \
  -d your-domain.com

# Copy certificates
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/key.pem

# Restart nginx
docker-compose restart nginx
```

#### SSL Security Headers
```nginx
# nginx/nginx.conf includes security headers:
add_header Strict-Transport-Security "max-age=31536000";
add_header X-Content-Type-Options "nosniff";
add_header X-Frame-Options "DENY";
add_header X-XSS-Protection "1; mode=block";
```

### Network Security

#### Firewall Configuration
```bash
# Ubuntu UFW example
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw enable

# Block internal service ports from external access
sudo ufw deny 8000/tcp     # API (accessed via nginx)
sudo ufw deny 3000/tcp     # Frontend (accessed via nginx)
sudo ufw deny 6379/tcp     # Redis
sudo ufw deny 9090/tcp     # Prometheus
sudo ufw deny 3001/tcp     # Grafana
```

#### Container Network Isolation
```yaml
# docker-compose.yml network configuration
networks:
  adelaide-weather:
    driver: bridge
    internal: true  # Isolate from external networks
```

### Security Monitoring

#### Security Health Checks
```bash
# Security status
curl -H "Authorization: Bearer $API_TOKEN" \
  http://localhost/api/health/security

# Security monitoring
curl -H "Authorization: Bearer $API_TOKEN" \
  http://localhost/api/monitor/security
```

#### Security Events
```bash
# View security events in Grafana
# Dashboard: "Security Overview"
# Metrics: auth_failures_total, security_events_count

# Security logs
grep -i "security\|auth\|unauthorized" logs/api/*.log
```

## Performance Tuning

### Resource Optimization

#### Memory Tuning
```yaml
# docker-compose.yml resource limits
services:
  api:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
  
  frontend:
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

#### CPU Optimization
```bash
# Set CPU affinity for critical services
docker update --cpuset-cpus="0,1" adelaide-weather_api_1
docker update --cpuset-cpus="2,3" adelaide-weather_frontend_1
```

### Database Performance

#### Redis Optimization
```yaml
# Redis configuration for performance
redis:
  command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
```

#### FAISS Performance
```bash
# FAISS index optimization
export OMP_NUM_THREADS=4         # Control CPU threads
export FAISS_NO_AVX=1           # Disable AVX if causing issues
```

### Network Performance

#### NGINX Optimization
```nginx
# nginx/nginx.conf performance settings
worker_processes auto;
worker_connections 1024;
gzip on;
gzip_comp_level 6;
client_max_body_size 10M;
keepalive_timeout 65;
```

#### Connection Pooling
```python
# API server connection pooling
REDIS_CONNECTION_POOL_SIZE=10
FASTAPI_WORKERS=4
```

### Monitoring Performance

#### Performance Metrics
```bash
# API performance
curl -H "Authorization: Bearer $API_TOKEN" \
  http://localhost/api/admin/performance

# System performance
curl http://localhost/api/health/performance
```

#### Performance Dashboards
Access performance dashboards in Grafana:
- API Performance Dashboard
- System Resource Dashboard
- FAISS Performance Dashboard

---

## Summary

This deployment guide provides comprehensive instructions for deploying and operating the Adelaide Weather System. The single-command deployment script (`deploy-adelaide-weather.sh`) automates most complexity while providing extensive customization options for production environments.

Key deployment features:
- **One-command deployment** with comprehensive validation
- **Multi-environment support** (development, staging, production)
- **Complete monitoring stack** with Prometheus and Grafana
- **Security-first approach** with SSL, authentication, and monitoring
- **Production-ready operations** with backup, scaling, and maintenance procedures

For additional support or questions, refer to the API documentation (API_DOCS.md) or contact the development team.