# T007 Nginx Integration Quick Reference

## Overview

**Mission Complete**: Production-ready nginx reverse proxy for Adelaide Weather System's 7-service architecture.

## Quick Start

```bash
# 1. Generate SSL certificates (if not already done)
cd nginx/ssl && ./generate_certs.sh localhost

# 2. Start the system
docker-compose -f docker-compose.production.yml up -d

# 3. Test the integration
./test_nginx_integration.sh

# 4. Access the system
open https://localhost/  # Frontend (accept SSL warning for self-signed cert)
```

## Service Architecture

```
External Traffic → nginx:80/443
                     ↓
    ┌─────────────────┼─────────────────┐
    │                 │                 │
frontend:3000    api:8000        Monitoring Stack
    │                 │                 │
    ├─ /             ├─ /api/*         ├─ /grafana/* → grafana:3000
    ├─ /forecast     ├─ /health        ├─ /prometheus/* → prometheus:9090
    ├─ /about        ├─ /metrics       └─ /alertmanager/* → alertmanager:9093
    └─ /analog-demo  └─ /docs
```

## Access Points

| Service | HTTP | HTTPS | Purpose |
|---------|------|-------|---------|
| Frontend | http://localhost/ | https://localhost/ | Main weather interface |
| API (prefixed) | http://localhost/api/ | https://localhost/api/ | API with prefix removal |
| API (direct) | http://localhost/health | https://localhost/health | Direct API access |
| Grafana | http://localhost/grafana/ | https://localhost/grafana/ | Monitoring dashboards |
| Prometheus | - | - | Internal networks only |
| Alertmanager | - | - | Internal networks only |

## Key Features Implemented

### ✅ SSL Termination
- **TLS 1.2 + 1.3** with modern cipher suites
- **Self-signed certificates** for development (replace for production)
- **Perfect Forward Secrecy** enabled
- **HSTS** with preload directive

### ✅ Security Headers
- **X-Frame-Options**: DENY
- **X-Content-Type-Options**: nosniff
- **X-XSS-Protection**: 1; mode=block
- **Referrer-Policy**: strict-origin-when-cross-origin
- **Content-Security-Policy**: Dynamic based on content type
- **Permissions-Policy**: Restrictive permissions

### ✅ Advanced Routing
- **API prefix removal**: `/api/health` → `api:8000/health`
- **Frontend SPA support**: WebSocket and hot reload support
- **Monitoring integration**: `/grafana/` → `grafana:3000/`
- **Health check aggregation**: `/health/upstream` checks API status

### ✅ Performance Optimization
- **Gzip compression** with optimized file types
- **Static asset caching** with appropriate cache headers
- **Connection keep-alive** with upstream pooling
- **Proxy caching** for static content

### ✅ Rate Limiting & DDoS Protection
- **API strict**: 10 req/s burst 20
- **API moderate**: 30 req/s burst 30
- **Frontend**: 50 req/s burst 50
- **Monitoring**: 5 req/s burst 5-10
- **Connection limiting**: 50 connections per IP

### ✅ Attack Mitigation
- **Block attack patterns**: PHP, ASP, JSP files
- **Block scanners**: nmap, nikto, sqlmap user agents
- **Block suspicious URLs**: eval(), base64_, /etc/passwd
- **Hidden file protection**: Block dotfiles and backups

## Configuration Files

| File | Purpose |
|------|---------|
| `/nginx/nginx.conf` | Main nginx configuration |
| `/nginx/ssl/cert.pem` | SSL certificate |
| `/nginx/ssl/key.pem` | SSL private key |
| `/nginx/routing_rules.md` | Detailed routing documentation |

## Docker Integration

### Volume Mounts
```yaml
- ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
- ./nginx/ssl:/etc/nginx/ssl:ro
- nginx_cache:/var/cache/nginx
- nginx_logs:/var/log/nginx
- nginx_certbot:/var/www/certbot
```

### Network Configuration
- **adelaide_internal**: Service-to-service communication
- **adelaide_external**: Public traffic
- **adelaide_monitoring**: Monitoring stack

### Health Checks
```yaml
test: ["CMD", "curl", "-f", "http://localhost/health"]
interval: 30s
timeout: 5s
retries: 3
```

## Testing & Validation

### Manual Testing
```bash
# Health checks
curl http://localhost/health
curl http://localhost/health/upstream

# API routing
curl http://localhost/api/health
curl http://localhost/metrics

# Frontend
curl http://localhost/

# SSL
curl -k https://localhost/health

# Security headers
curl -I https://localhost/
```

### Automated Testing
```bash
# Run comprehensive integration test
./test_nginx_integration.sh

# Validate nginx config syntax
cd nginx && ./validate_config.sh

# Test with docker-compose
cd nginx && ./test_config.sh
```

### Monitoring
```bash
# View logs
docker-compose logs nginx
docker exec adelaide-weather-nginx tail -f /var/log/nginx/access.log

# Check service status
docker-compose ps nginx
docker-compose exec nginx nginx -t
```

## Production Considerations

### 🔐 SSL Certificates
- Replace self-signed certificates with proper CA-signed certificates
- Consider **Let's Encrypt** for free automated certificates
- Set up automatic certificate renewal

### 📊 Monitoring
- Configure log aggregation (ELK stack, Fluentd)
- Set up nginx metrics collection for Prometheus
- Monitor response times and error rates

### 🛡️ Security
- Implement **HTTP Basic Auth** for monitoring endpoints
- Configure **fail2ban** for additional IP blocking
- Regular security updates for nginx

### ⚡ Performance
- Enable **Brotli compression** if available
- Configure **HTTP/3** support for modern clients
- Implement **CDN** for static asset delivery

### 🔧 Maintenance
```bash
# Reload configuration without downtime
docker exec adelaide-weather-nginx nginx -s reload

# Test configuration changes
docker exec adelaide-weather-nginx nginx -t

# View real-time logs
docker exec adelaide-weather-nginx tail -f /var/log/nginx/access.log
```

## Troubleshooting

### Common Issues

**Nginx won't start:**
```bash
# Check configuration
docker exec adelaide-weather-nginx nginx -t

# Check logs
docker-compose logs nginx

# Verify SSL certificates
ls -la nginx/ssl/
```

**Service routing not working:**
```bash
# Check backend services are running
docker-compose ps

# Test internal service connectivity
docker exec adelaide-weather-nginx nslookup api
docker exec adelaide-weather-nginx nslookup frontend
```

**SSL certificate issues:**
```bash
# Regenerate certificates
cd nginx/ssl && ./generate_certs.sh localhost

# Check certificate validity
openssl x509 -in nginx/ssl/cert.pem -text -noout | grep "Not After"
```

**Rate limiting too aggressive:**
- Adjust rate limit zones in `nginx.conf`
- Increase burst capacity for legitimate traffic
- Consider IP whitelisting for internal services

## Integration with T006 Orchestration

✅ **Network Compatibility**: Uses docker-compose service names for routing  
✅ **Volume Integration**: Properly mounted SSL certificates and cache  
✅ **Health Check Alignment**: Consistent with docker-compose health strategy  
✅ **Service Dependencies**: Proper startup ordering with depends_on  
✅ **Resource Limits**: Optimized for container resource constraints

## Next Steps (Post-T007)

1. **Production SSL**: Implement Let's Encrypt or CA certificates
2. **Advanced Monitoring**: Integrate nginx metrics with Prometheus
3. **Load Testing**: Validate performance under load
4. **CDN Integration**: Implement edge caching for global distribution
5. **WAF Integration**: Web Application Firewall for advanced security

---

**T007 Status**: ✅ **COMPLETE**  
**Integration Specialist**: Mission accomplished - Production-ready nginx reverse proxy deployed with SSL termination, security headers, advanced routing, and comprehensive monitoring integration.