# Adelaide Weather System - Nginx Routing Rules & Security Documentation

## Overview

This document details the comprehensive nginx reverse proxy configuration for the Adelaide Weather Forecasting System's 7-service architecture. The configuration provides production-ready routing, security headers, SSL termination, and monitoring integration.

## Service Architecture

```
External Traffic → nginx:80/443
                     ↓
    ┌─────────────────┼─────────────────┐
    │                 │                 │
frontend:3000    api:8000        Monitoring Stack
    │                 │                 │
    ├─ / (root)      ├─ /api/*         ├─ /grafana/* → grafana:3000
    ├─ /forecast     ├─ /health        ├─ /prometheus/* → prometheus:9090
    ├─ /about        ├─ /metrics       └─ /alertmanager/* → alertmanager:9093
    └─ /analog-demo  ├─ /forecast
                     └─ /docs
```

## Routing Configuration

### 1. Frontend Routes

**Pattern:** `/` (root and all frontend pages)
**Target:** `frontend:3000`
**Rate Limiting:** 50 requests/second with burst of 50
**Features:**
- WebSocket support for Next.js hot reloading
- Proxy buffering disabled for real-time updates
- Custom error handling with failover messages

**Specific Routes:**
- `/` - Main dashboard
- `/forecast` - Weather forecast interface
- `/about` - Application information
- `/analog-demo` - Analog forecasting demonstration
- `/cape-demo` - CAPE calculation demonstration
- `/metrics-demo` - Metrics visualization

### 2. API Routes

**Pattern:** `/api/*`
**Target:** `api:8000` (with `/api` prefix removed)
**Rate Limiting:** 10 requests/second with burst of 20
**Features:**
- Automatic `/api` prefix removal via rewrite
- Enhanced CORS configuration with credential support
- JSON error responses with timestamps
- API-specific timeout optimization (5s connect, 15s read)

**Direct API Endpoints:**
**Pattern:** `/health`, `/metrics`, `/forecast`, `/docs`, `/openapi.json`
**Target:** `api:8000` (direct access without prefix)
**Rate Limiting:** 30 requests/second with burst of 30
**Purpose:** Legacy support and direct API access

### 3. Monitoring Services Routes

#### Grafana Dashboard
**Pattern:** `/grafana/*`
**Target:** `grafana:3000`
**Access:** Public (can be restricted with HTTP Basic Auth)
**Rate Limiting:** 5 requests/second with burst of 10
**Features:**
- WebSocket support for Grafana Live features
- Path rewriting for proper dashboard routing
- Custom proxy headers for Grafana compatibility

#### Prometheus Metrics
**Pattern:** `/prometheus/*`
**Target:** `prometheus:9090`
**Access:** Restricted to internal Docker networks only
**Networks Allowed:**
- `172.20.0.0/16` (adelaide_internal)
- `172.21.0.0/16` (adelaide_monitoring)
- `127.0.0.1` (localhost)
**Rate Limiting:** 5 requests/second with burst of 5

#### Alertmanager
**Pattern:** `/alertmanager/*`
**Target:** `alertmanager:9093`
**Access:** Restricted to internal Docker networks only
**Rate Limiting:** 5 requests/second with burst of 5

### 4. Static Assets

#### Long-term Cached Assets
**Pattern:** `/static/*`
**Cache Duration:** 1 year
**Features:** Immutable caching, compression, security headers

#### Medium-term Cached Assets
**Pattern:** `*.css`, `*.js`, `*.map`
**Cache Duration:** 30 days
**Features:** Conditional requests (ETag), compression

#### Image Assets
**Pattern:** `*.jpg`, `*.png`, `*.svg`, `*.webp`, etc.
**Cache Duration:** 90 days
**Features:** Client hints for responsive images

#### Font Assets
**Pattern:** `*.woff`, `*.woff2`, `*.ttf`, etc.
**Cache Duration:** 1 year
**Features:** CORS headers for cross-origin font loading

## Security Configuration

### 1. SSL/TLS Configuration

**Protocols:** TLSv1.2, TLSv1.3
**Cipher Suites:** Modern secure ciphers (ECDHE, ChaCha20, AES-GCM)
**Features:**
- Perfect Forward Secrecy (PFS)
- Session caching for performance
- Session tickets disabled for security

### 2. Security Headers

#### Applied to All Responses:
```nginx
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

#### Content Security Policy (CSP):
**Default:** Restrictive policy for API endpoints
**HTML Content:** Relaxed policy allowing external weather APIs and CDNs
- Allows `api.weatherapi.com` for weather data
- Permits Google Fonts and jsdelivr CDN
- Blocks inline scripts except where necessary

### 3. Rate Limiting & DDoS Protection

#### Rate Limit Zones:
- **API (Strict):** 10 requests/second
- **API (Moderate):** 30 requests/second  
- **Frontend:** 50 requests/second
- **Monitoring:** 5 requests/second

#### Connection Limiting:
- **Max Connections per IP:** 50
- **Rate limiting after:** 1MB transfer
- **Rate limit:** 250KB/s per connection

### 4. Attack Mitigation

#### Blocked Patterns:
- PHP/ASP/JSP files (returns 444)
- Hidden files (dotfiles)
- Backup files (*.bak, *.backup, *.swp)
- Suspicious URL patterns (eval, base64, /etc/passwd)
- Scanner user agents (nmap, nikto, sqlmap, etc.)
- Empty user agents

#### HTTP to HTTPS Redirect:
- All HTTP traffic redirected to HTTPS except:
  - Health check endpoint (`/health`)
  - Let's Encrypt ACME challenge (`/.well-known/acme-challenge/`)

## Performance Optimization

### 1. Compression

**Gzip Enabled:** Level 6 compression
**Compressed Types:**
- Text: HTML, CSS, JavaScript, XML, JSON
- Fonts: TTF, OpenType
- Images: SVG
- Applications: JSON, XML+RSS, Atom

**Brotli Support:** Commented configuration ready for module installation

### 2. Caching

**Proxy Cache:** 1GB cache for upstream responses
**File Cache:** 10,000 files cached for 30 seconds
**Browser Caching:** Optimized cache headers by content type

### 3. Connection Optimization

**Keep-Alive:** 65 seconds with 1000 requests per connection
**Upstream Keep-Alive:** Connection pooling to backend services
**Buffer Optimization:** Tuned buffer sizes for containerized deployment

## Health Checks & Monitoring

### 1. Health Check Endpoints

#### Primary Health Check:
**Endpoint:** `/health`
**Response:** `200 OK` with "nginx healthy"
**Purpose:** Load balancer health verification

#### Upstream Health Aggregator:
**Endpoint:** `/health/upstream`
**Behavior:** Proxies to API health endpoint
**Timeout:** 1 second (fast fail for monitoring)
**Error Response:** `503` with "upstream services unavailable"

### 2. Logging

#### Access Logs:
- **Extended Format:** Includes upstream response times and cache status
- **JSON Format:** Structured logs for log aggregation systems
- **Location:** `/var/log/nginx/access.log` and `/var/log/nginx/access_json.log`

#### Error Logs:
- **Level:** Warning and above
- **Location:** `/var/log/nginx/error.log`

## Network Security

### 1. Docker Network Integration

**Internal Network:** `adelaide_internal` (172.20.0.0/16)
**Monitoring Network:** `adelaide_monitoring` (172.21.0.0/16)
**External Network:** `adelaide_external` (bridge)

### 2. Service Communication

All backend services communicate through Docker's internal DNS:
- `api:8000` - FastAPI service
- `frontend:3000` - Next.js application
- `grafana:3000` - Grafana dashboard
- `prometheus:9090` - Prometheus metrics
- `alertmanager:9093` - Alert manager
- `redis:6379` - Redis cache

## Error Handling

### 1. Custom Error Pages

- **404:** Custom not found page
- **50x:** Server error page
- **503:** Maintenance mode with retry headers

### 2. Service-Specific Error Handling

- **Frontend Errors:** Plain text error messages with retry instructions
- **API Errors:** JSON-formatted error responses with timestamps
- **Upstream Errors:** Graceful fallback with appropriate HTTP status codes

## Deployment Considerations

### 1. SSL Certificate Management

**Development:** Self-signed certificates generated automatically
**Production:** Replace with proper CA-signed certificates
**Let's Encrypt:** ACME challenge support configured

### 2. Configuration Validation

```bash
# Test nginx configuration
docker exec adelaide-weather-nginx nginx -t

# Reload configuration without downtime
docker exec adelaide-weather-nginx nginx -s reload
```

### 3. Scaling Considerations

**Load Balancing:** Configured for multiple backend instances
**Health Checks:** Automatic failover on backend failure
**Session Affinity:** Not required (stateless API design)

## Integration with T006 Orchestration

This nginx configuration integrates seamlessly with the docker-compose.production.yml orchestration:

1. **Service Discovery:** Uses Docker internal DNS for backend routing
2. **Volume Mounts:** SSL certificates and static files properly mounted
3. **Network Segmentation:** Respects internal/external network boundaries
4. **Health Checks:** Aligned with docker-compose health check strategy
5. **Resource Limits:** Optimized for container resource constraints

## Monitoring Integration

The nginx configuration supports comprehensive monitoring:

1. **Prometheus Metrics:** Direct access to Prometheus endpoint
2. **Grafana Dashboards:** Seamless routing to visualization
3. **Log Aggregation:** Structured JSON logs for centralized logging
4. **Health Monitoring:** Multiple health check endpoints for different purposes

## Security Compliance

This configuration implements security best practices:

1. **OWASP Guidelines:** Implements OWASP security recommendations
2. **TLS Best Practices:** Modern TLS configuration with secure ciphers
3. **HSTS Compliance:** HTTP Strict Transport Security with preload
4. **CSP Implementation:** Content Security Policy for XSS protection
5. **Rate Limiting:** Protection against abuse and DDoS attacks

## Maintenance & Updates

### Regular Maintenance Tasks:

1. **Certificate Renewal:** Monitor SSL certificate expiration
2. **Security Updates:** Keep nginx updated with security patches
3. **Log Rotation:** Implement log rotation for disk space management
4. **Performance Monitoring:** Monitor response times and error rates
5. **Configuration Validation:** Test configuration changes in staging first

This comprehensive nginx configuration provides a production-ready foundation for the Adelaide Weather Forecasting System with security, performance, and maintainability as core principles.