# Nginx Integration - Quick Reference

## Overview
Nginx has been integrated into the Adelaide Weather Forecasting System as a reverse proxy for both development and staging environments, providing:

- **API Proxy**: Routes `/api/*` requests to FastAPI backend with path rewriting
- **Gzip Compression**: Automatic compression for text-based responses
- **CORS Headers**: Proper CORS configuration for cross-origin requests
- **Rate Limiting**: Basic rate limiting to prevent abuse
- **Security Headers**: Standard security headers for production readiness

## Quick Start

### Development Environment
```bash
# Start with nginx proxy
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Access points
curl http://localhost/              # Frontend via nginx
curl http://localhost/api/health    # API via nginx proxy
curl http://localhost/health        # Direct API access
```

### Staging Environment  
```bash
# Start staging with nginx
docker-compose -f docker-compose.staging.yml up -d

# Access points
curl http://localhost/              # Frontend via nginx
curl http://localhost/api/health    # API via nginx proxy
```

## Key Features Implemented

### 1. API Path Rewriting
- **Route**: `/api/*` → removes `/api` prefix and forwards to backend
- **Example**: `GET /api/health` → `GET /health` on FastAPI backend
- **Rate Limit**: 10 requests/second with burst of 10

### 2. Gzip Compression
- **Enabled for**: JSON, HTML, CSS, JS, XML, SVG
- **Min Size**: 1024 bytes
- **Compression Level**: 6

### 3. CORS Configuration
- **Origin**: `*` (configurable)
- **Methods**: `GET, POST, PUT, DELETE, OPTIONS, HEAD`
- **Headers**: `Origin, X-Requested-With, Content-Type, Accept, Authorization, Cache-Control`
- **Preflight**: Automatic handling of OPTIONS requests

### 4. Security Headers
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`

### 5. Rate Limiting
- **API Endpoints**: 10 req/s (burst 10)
- **Frontend**: 30 req/s (burst 20)
- **Zone Size**: 10MB memory

## Validation

### Automated Testing
```bash
./test_nginx_integration.sh
```

### Manual Testing
```bash
# Test CORS headers
curl -H "Origin: http://localhost:3000" -X OPTIONS http://localhost/api/health -I

# Test compression
curl -H "Accept-Encoding: gzip" http://localhost/ -I

# Test rate limiting
for i in {1..15}; do curl http://localhost/api/health; done
```

## Configuration Files

### Main Configuration
- **File**: `nginx/nginx.conf`
- **Mount**: Read-only in all environments
- **Features**: All proxy rules, compression, CORS, security headers

### Docker Compose Integration
- **Development**: `docker-compose.yml` + `docker-compose.dev.yml`
- **Staging**: `docker-compose.staging.yml`
- **Ports**: 80 (HTTP), 443 (HTTPS staging-ready)

## Monitoring & Debugging

### Development Logs
```bash
# Nginx logs are mounted to ./logs/nginx/
tail -f logs/nginx/access.log
tail -f logs/nginx/error.log

# Container logs
docker-compose logs -f nginx
```

### Staging Logs
```bash
# Logs stored in named volume
docker-compose -f docker-compose.staging.yml logs -f nginx

# Access volume
docker volume inspect adelaide-staging-nginx-logs
```

## Health Checks

### Nginx Health
- **Endpoint**: `wget http://localhost/health` 
- **Interval**: 30s
- **Timeout**: 10s
- **Retries**: 3

### Service Dependencies
- Nginx waits for both API and UI services to be healthy before starting
- Proper startup order: API → UI → Nginx

## Performance Configuration

### Connection Settings
- **Worker Connections**: 1024
- **Keepalive**: 32 upstream connections
- **Multi-accept**: Enabled
- **Sendfile**: Enabled

### Timeouts
- **API Requests**: 5s connect, 10s send/read
- **Frontend Requests**: 10s connect, 30s send/read

## Future Enhancements

### SSL/TLS (Staging Ready)
- Port 443 exposed in staging
- SSL configuration template in nginx.conf
- Certificate mounting points prepared

### Caching
- Static file caching configured
- API response caching disabled
- Frontend asset caching (1 day)

## Troubleshooting

### Common Issues
1. **502 Bad Gateway**: Backend services not ready
2. **Rate Limited**: Too many requests
3. **CORS Errors**: Check Origin headers
4. **No Compression**: Response too small or wrong content-type

### Debug Commands
```bash
# Check nginx config syntax
docker-compose exec nginx nginx -t

# Reload nginx config
docker-compose exec nginx nginx -s reload

# Check upstream health
curl http://localhost/api/health
curl http://localhost:3000/  # direct frontend
curl http://localhost:8000/health  # direct API
```

## Quality Gates Satisfied

✅ **Compose service exists in dev path**  
✅ **Proxy routes `/api/*` correctly with compression and CORS headers**  
✅ **All proxy features validated** (via test script)

The nginx integration provides a production-ready reverse proxy solution with proper security, performance, and operational features for the Adelaide Weather Forecasting System.