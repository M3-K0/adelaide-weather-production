# Adelaide Weather Forecasting System - Service Dependencies

## Overview

This document describes the comprehensive service dependency architecture for the Adelaide Weather production deployment, designed to eliminate mock data and ensure proper startup sequencing with FAISS analog forecasting.

## Service Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   External      │    │   Monitoring    │
│   Access        │    │   Stack         │
└─────────────────┘    └─────────────────┘
         │                       │
    ┌────▼────┐              ┌───▼───┐
    │  nginx  │              │grafana│
    │(Reverse │              │       │
    │ Proxy)  │              └───┬───┘
    └────┬────┘                  │
         │                   ┌───▼──────┐
    ┌────▼────┐              │prometheus│
    │frontend │              │          │
    │(Next.js)│              └───┬──────┘
    └────┬────┘                  │
         │                   ┌───▼──────┐
    ┌────▼────┐              │alertmgr  │
    │   api   │              │          │
    │(FastAPI)│              └──────────┘
    └────┬────┘
         │
    ┌────▼────┐
    │  redis  │
    │ (Cache) │
    └─────────┘
         │
┌────────▼────────┐
│  FAISS Indices  │
│   (Read-Only)   │
└─────────────────┘
```

## Startup Dependencies

### Phase 1: Infrastructure Services
1. **Redis Cache** (No dependencies)
   - Storage: Session cache and performance optimization
   - Health Check: Redis PING command
   - Startup Time: ~5 seconds
   - Critical for API performance

### Phase 2: Core Application Services
2. **API Service** (Depends on: Redis)
   - FAISS indices mounted read-only
   - Weather forecasting logic with analog search
   - Health Check: `/health` endpoint validation
   - Startup Time: ~60 seconds (includes FAISS loading)
   - **Zero Mock Data**: Only real FAISS indices and historical patterns

3. **Frontend Service** (Depends on: API)
   - React/Next.js web interface
   - Health Check: API proxy validation
   - Startup Time: ~90 seconds
   - Waits for API health before becoming ready

### Phase 3: Infrastructure & Routing
4. **Nginx Reverse Proxy** (Depends on: API, Frontend)
   - SSL termination and load balancing
   - Rate limiting and security headers
   - Health Check: Direct service validation
   - Startup Time: ~10 seconds

### Phase 4: Monitoring Stack (Independent)
5. **Prometheus** (Independent)
   - Metrics collection and storage
   - Health Check: Prometheus ready endpoint
   - Startup Time: ~30 seconds

6. **Grafana** (Depends on: Prometheus)
   - Visualization and dashboards
   - Health Check: Grafana API health
   - Startup Time: ~60 seconds

7. **Alertmanager** (Depends on: Prometheus)
   - Alert routing and notifications
   - Health Check: Alertmanager ready endpoint
   - Startup Time: ~30 seconds

## Critical Dependencies

### FAISS Data Dependencies
- **Indices**: 8 pre-built FAISS indices (6h, 12h, 24h, 48h × FlatIP, IVFPQ)
- **Embeddings**: Weather pattern embeddings for analog search
- **Outcomes**: Historical weather outcomes for forecasting
- **Models**: Trained neural network checkpoints

All FAISS data is mounted **read-only** to ensure production data integrity.

### Network Dependencies
- **adelaide_internal**: Private network for service communication
- **adelaide_external**: Public network for nginx ingress
- **adelaide_monitoring**: Dedicated network for observability

### Volume Dependencies
- **Read-Only Volumes**: FAISS data, application code, configurations
- **Writable Volumes**: Logs, cache, temporary files
- **Persistent Volumes**: Redis data, Prometheus metrics, Grafana dashboards

## Health Check Strategy

### Service Health Validation
Each service implements comprehensive health checks:

1. **Redis**: `redis-cli ping`
2. **API**: `curl http://api:8000/health` (includes FAISS validation)
3. **Frontend**: `curl http://frontend:3000/api/health` (proxy check)
4. **Nginx**: `curl http://nginx/health` (upstream validation)
5. **Prometheus**: `wget http://prometheus:9090/-/healthy`
6. **Grafana**: `curl http://grafana:3000/api/health`
7. **Alertmanager**: `wget http://alertmanager:9093/-/healthy`

### Health Check Timing
- **Interval**: 30 seconds (normal operation)
- **Timeout**: 3-10 seconds (service dependent)
- **Retries**: 3 attempts before marking unhealthy
- **Start Period**: 5-90 seconds (allows for initialization)

## Resource Allocation

### Production Resource Limits
```yaml
api:
  limits:   { cpus: '2.0', memory: '3G' }
  reserves: { cpus: '0.5', memory: '1G' }

frontend:
  limits:   { cpus: '1.0', memory: '1.5G' }
  reserves: { cpus: '0.25', memory: '512M' }

nginx:
  limits:   { cpus: '0.5', memory: '256M' }
  reserves: { cpus: '0.1', memory: '64M' }

redis:
  limits:   { cpus: '0.5', memory: '512M' }
  reserves: { cpus: '0.1', memory: '128M' }

prometheus:
  limits:   { cpus: '1.0', memory: '2G' }
  reserves: { cpus: '0.2', memory: '512M' }

grafana:
  limits:   { cpus: '1.0', memory: '1G' }
  reserves: { cpus: '0.2', memory: '256M' }

alertmanager:
  limits:   { cpus: '0.5', memory: '256M' }
  reserves: { cpus: '0.1', memory: '64M' }
```

### Total System Requirements
- **CPU**: 6.5 cores total (2.65 cores reserved)
- **Memory**: 9.5GB total (3.4GB reserved)
- **Storage**: 50GB minimum for logs and monitoring data

## Environment Variables

### Required Variables
```bash
# Authentication (Required)
API_TOKEN=<secure-token>
```

### Optional Configuration Variables
```bash
# Versioning & Build Info
VERSION=1.0.0
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
VCS_REF=$(git rev-parse --short HEAD)

# Security & Access
GRAFANA_PASSWORD=<secure-password>
GRAFANA_SECRET_KEY=<random-secret>
REDIS_PASSWORD=<optional-password>
CORS_ORIGINS=http://localhost:3000,https://your-domain.com

# Performance Tuning
LOG_LEVEL=INFO
RATE_LIMIT_PER_MINUTE=60
COMPRESSION_ENABLED=true
MONITORING_ENABLED=true

# External Services (Optional Enhancement)
WEATHER_API_KEY=<weatherapi.com-key>
WEATHER_API_ENABLED=false
```

## Startup Sequence

### Initialization Flow
1. **Environment Validation**
   - Check required environment variables
   - Validate FAISS data availability
   - Verify network connectivity

2. **Infrastructure Startup** (0-15 seconds)
   - Redis cache initialization
   - Network creation
   - Volume mounting

3. **Core Services** (15-75 seconds)
   - API service with FAISS loading
   - Frontend service build and start
   - Nginx proxy configuration

4. **Monitoring Stack** (75-135 seconds)
   - Prometheus metrics collection
   - Grafana dashboard loading
   - Alertmanager alert routing

### Failure Recovery
- **Restart Policy**: `unless-stopped` for all services
- **Health-based Dependencies**: Services wait for upstream health
- **Graceful Degradation**: Monitoring failures don't affect core services
- **Circuit Breakers**: Built-in rate limiting and timeout handling

## Security Architecture

### Network Segmentation
- **External Network**: Only nginx has public access
- **Internal Network**: Service-to-service communication
- **Monitoring Network**: Isolated observability stack

### Data Security
- **Read-Only Mounts**: All application data and FAISS indices
- **Non-Root Users**: All containers run as non-privileged users
- **Secret Management**: Environment-based secret injection
- **Security Scanning**: Automated vulnerability assessment in build

### Access Controls
- **Authentication**: Token-based API access
- **Authorization**: Service-level access controls
- **Rate Limiting**: API and proxy-level protection
- **Headers**: Security headers for web protection

## Monitoring Integration

### Metrics Collection
- **API Metrics**: Request rates, latency, errors, FAISS performance
- **System Metrics**: CPU, memory, disk, network utilization
- **Business Metrics**: Forecast accuracy, analog matching performance
- **Security Metrics**: Failed authentications, rate limit violations

### Alerting Rules
- **Service Health**: Service down or unhealthy
- **Performance**: High latency or error rates
- **Resources**: Memory/CPU/disk threshold alerts
- **Business Logic**: FAISS index corruption or forecast failures

### Dashboard Coverage
- **System Overview**: All services health and performance
- **API Performance**: Request patterns and FAISS analytics
- **Resource Utilization**: Infrastructure monitoring
- **Weather Forecast**: Business-specific meteorological dashboards

## Deployment Commands

### Production Deployment
```bash
# Set required environment variables
export API_TOKEN="your-secure-token"
export VERSION="1.0.0"
export BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
export VCS_REF=$(git rev-parse --short HEAD)

# Create log directories
mkdir -p logs/{api,frontend,nginx}

# Deploy the stack
docker-compose -f docker-compose.production.yml up -d

# Monitor startup
docker-compose -f docker-compose.production.yml logs -f
```

### Health Validation
```bash
# Check all services are healthy
docker-compose -f docker-compose.production.yml ps

# Validate API functionality
curl -H "Authorization: Bearer $API_TOKEN" \
     http://localhost/api/forecast?horizon=24h

# Access monitoring
open http://localhost:3001  # Grafana dashboards
open http://localhost:9090  # Prometheus metrics
```

### Troubleshooting
```bash
# Check individual service health
docker-compose -f docker-compose.production.yml exec api curl -f http://localhost:8000/health
docker-compose -f docker-compose.production.yml exec frontend curl -f http://localhost:3000/api/health

# Monitor FAISS performance
curl -H "Authorization: Bearer $API_TOKEN" \
     http://localhost/api/health/faiss

# View service logs
docker-compose -f docker-compose.production.yml logs api
docker-compose -f docker-compose.production.yml logs frontend
docker-compose -f docker-compose.production.yml logs nginx
```

## Performance Optimization

### Caching Strategy
- **Redis**: API response caching and session storage
- **Nginx**: Static file caching and compression
- **Application**: In-memory FAISS index caching

### FAISS Optimization
- **Memory Mapping**: Efficient index loading without full memory copy
- **Query Pooling**: Connection pooling for analog searches
- **Batch Processing**: Optimized batch forecast generation

### Container Optimization
- **Multi-stage Builds**: Minimal production images
- **Layer Caching**: Optimized Docker layer structure
- **Resource Limits**: Prevent resource contention

This dependency architecture ensures zero mock data usage, proper startup sequencing, comprehensive monitoring, and production-grade reliability for the Adelaide Weather Forecasting System.