# Performance Middleware Configuration

This document describes the performance middleware enhancement configuration options for the Adelaide Weather Forecasting API.

## Environment Variables

### Rate Limiting Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_PER_MINUTE` | `60` | Maximum requests per minute per IP address |
| `RATE_LIMIT_ENABLED` | `true` | Enable/disable rate limiting |

**Examples:**
```bash
export RATE_LIMIT_PER_MINUTE=120  # Allow 120 requests per minute
export RATE_LIMIT_ENABLED=false   # Disable rate limiting entirely
```

### Compression Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `COMPRESSION_MIN_SIZE` | `500` | Minimum response size (bytes) to trigger compression |
| `COMPRESSION_ENABLED` | `true` | Enable/disable GZip compression |
| `NGINX_COMPRESSION` | `false` | Set to `true` if nginx handles compression |

**Examples:**
```bash
export COMPRESSION_MIN_SIZE=1000   # Only compress responses > 1KB
export COMPRESSION_ENABLED=false   # Disable API-level compression
export NGINX_COMPRESSION=true      # Skip compression when behind nginx
```

## Endpoint Rate Limits

Different endpoints have different rate limit multipliers based on the main `RATE_LIMIT_PER_MINUTE` setting:

- **Forecast endpoint**: 100% of main limit (configurable)
- **Health endpoints**: 50% of main limit
- **Metrics/Admin endpoints**: 20% of main limit

## Performance Monitoring

### New Endpoints

1. **`GET /admin/performance`** - Detailed performance statistics
   - Requires authentication
   - Returns comprehensive middleware metrics
   - Rate limited to metrics limit (20% of main)

### Enhanced Metrics

The `/metrics` endpoint now includes additional performance metrics:

```
# Compression metrics
compression_requests_total      # Total requests processed
compression_ratio              # Average compression ratio

# Rate limiting metrics  
rate_limit_requests_total       # Total rate limit checks
rate_limit_violations_total     # Total rate limit violations
```

## Nginx Integration

When deploying behind nginx with compression enabled:

1. Set `NGINX_COMPRESSION=true`
2. API will detect proxy headers and skip double compression
3. Configure nginx with:
   ```nginx
   gzip on;
   gzip_min_length 500;
   gzip_types application/json text/plain;
   ```

## Performance Features

### Intelligent Compression
- Automatically detects nginx proxy to prevent double compression
- Only compresses appropriate content types (JSON, text)
- Respects client Accept-Encoding headers
- Tracks compression ratios and bandwidth savings

### Configurable Rate Limiting
- Environment-driven configuration
- Per-endpoint rate limit multipliers
- Comprehensive violation tracking
- SlowAPI integration for distributed scenarios

### Enhanced Monitoring
- Real-time performance statistics
- Prometheus-compatible metrics
- Cache hit/miss ratios
- Response time tracking

## Default Configuration

For production deployment, the following defaults provide good performance:

```bash
# Rate limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_ENABLED=true

# Compression  
COMPRESSION_MIN_SIZE=500
COMPRESSION_ENABLED=true
NGINX_COMPRESSION=false

# Other standard variables
API_TOKEN=your-secure-token
ENVIRONMENT=production
```

## Troubleshooting

### High CPU Usage
- Increase `COMPRESSION_MIN_SIZE` to reduce compression overhead
- Consider setting `NGINX_COMPRESSION=true` and handling compression at nginx level

### Rate Limit Issues
- Check `/admin/performance` for violation statistics
- Adjust `RATE_LIMIT_PER_MINUTE` based on traffic patterns
- Monitor endpoint-specific limits in logs

### Compression Problems
- Verify client sends `Accept-Encoding: gzip`
- Check response headers for `Content-Encoding: gzip`
- Monitor compression ratios via `/admin/performance`

## Backward Compatibility

All changes are backward compatible:
- Existing deployments work without configuration changes
- Default values maintain current behavior
- New features are opt-in via environment variables