# Rate Limiting Policy

The Adelaide Weather Forecasting API implements rate limiting to ensure fair usage and system stability for all users.

## Overview

Rate limits are applied per API token and are designed to allow normal operational usage while preventing abuse. Limits are enforced using a sliding window algorithm with automatic reset periods.

## Rate Limits by Endpoint

| Endpoint | Rate Limit | Time Window | Authentication Required |
|----------|------------|-------------|------------------------|
| `/forecast` | 60 requests | per minute | Yes |
| `/health` | 30 requests | per minute | No |
| `/metrics` | 10 requests | per minute | Yes |
| `/analogs` | 10 requests | per minute | Yes |

## Rate Limit Headers

Every API response includes rate limiting information in the headers:

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1642262400
X-RateLimit-Window: 60
```

### Header Descriptions

- **`X-RateLimit-Limit`**: Maximum requests allowed in the time window
- **`X-RateLimit-Remaining`**: Requests remaining in current window
- **`X-RateLimit-Reset`**: Unix timestamp when the current window resets
- **`X-RateLimit-Window`**: Time window in seconds

## Rate Limit Exceeded Response

When you exceed the rate limit, the API returns HTTP 429 with details:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1642262460
Content-Type: application/json

{
    "error": {
        "code": 429,
        "message": "Rate limit exceeded. Please try again later.",
        "timestamp": "2024-01-15T12:00:00Z",
        "correlation_id": "req_123456"
    }
}
```

### Retry-After Header

The `Retry-After` header indicates how many seconds to wait before making another request.

## Best Practices

### 1. Monitor Rate Limit Headers

Always check rate limit headers in responses to avoid hitting limits:

```python
import requests
import time

def make_request_with_rate_limiting(url, headers):
    response = requests.get(url, headers=headers)
    
    # Check rate limit headers
    remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
    reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
    
    if remaining < 5:  # Buffer before hitting limit
        sleep_time = reset_time - int(time.time()) + 1
        if sleep_time > 0:
            print(f"Rate limit approaching, sleeping for {sleep_time}s")
            time.sleep(sleep_time)
    
    return response
```

### 2. Implement Exponential Backoff

When you receive a 429 response, implement exponential backoff:

```python
import time
import random

def exponential_backoff_retry(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                if attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    base_delay = 2 ** attempt
                    jitter = random.uniform(0.1, 0.5)
                    delay = base_delay + jitter
                    
                    # Use Retry-After if provided
                    retry_after = e.response.headers.get('Retry-After')
                    if retry_after:
                        delay = max(delay, int(retry_after))
                    
                    print(f"Rate limited, retrying in {delay:.1f}s")
                    time.sleep(delay)
                else:
                    raise
            else:
                raise
```

### 3. Use Intelligent Caching

Cache responses to reduce API calls:

```python
import time
from functools import wraps

def cache_with_ttl(ttl_seconds=300):  # 5 minute default
    cache = {}
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            key = str(args) + str(sorted(kwargs.items()))
            
            # Check cache
            if key in cache:
                value, timestamp = cache[key]
                if time.time() - timestamp < ttl_seconds:
                    return value
            
            # Make request and cache
            result = func(*args, **kwargs)
            cache[key] = (result, time.time())
            
            return result
        return wrapper
    return decorator

@cache_with_ttl(300)  # Cache for 5 minutes
def get_forecast(client, horizon='24h', variables='t2m,u10,v10,msl'):
    return client.get_forecast({'horizon': horizon, 'variables': variables.split(',')})
```

### 4. Batch Similar Requests

Instead of making multiple requests, batch similar data in fewer calls:

```python
# ❌ Multiple requests
temp_6h = client.get_forecast({'horizon': '6h', 'variables': ['t2m']})
temp_12h = client.get_forecast({'horizon': '12h', 'variables': ['t2m']})
temp_24h = client.get_forecast({'horizon': '24h', 'variables': ['t2m']})

# ✅ Single request with more variables
forecast_24h = client.get_forecast({
    'horizon': '24h', 
    'variables': ['t2m', 'u10', 'v10', 'msl', 'cape']
})
```

## Rate Limiting Strategies

### 1. Token Bucket Algorithm

The API uses a token bucket algorithm with the following characteristics:

- **Bucket Size**: Equal to the rate limit (e.g., 60 for `/forecast`)
- **Refill Rate**: Tokens are added continuously
- **Window**: Sliding window, not fixed intervals

### 2. Per-Token Limits

Rate limits are applied per API token, not per IP address. This means:

- Each token has independent rate limits
- Multiple applications can use different tokens
- Rate limits don't affect other users

### 3. Burst Allowance

The system allows short bursts up to the bucket size, then enforces the sustained rate.

## Monitoring Your Usage

### 1. Track Rate Limit Headers

```javascript
class RateLimitMonitor {
    constructor() {
        this.stats = {
            total_requests: 0,
            rate_limited: 0,
            last_reset: 0
        };
    }
    
    updateFromResponse(response) {
        this.stats.total_requests++;
        
        const remaining = parseInt(response.headers.get('X-RateLimit-Remaining') || '0');
        const reset = parseInt(response.headers.get('X-RateLimit-Reset') || '0');
        
        if (response.status === 429) {
            this.stats.rate_limited++;
        }
        
        this.stats.last_reset = reset;
        
        // Log warning if approaching limit
        if (remaining < 5) {
            console.warn(`Rate limit warning: ${remaining} requests remaining`);
        }
    }
    
    getStats() {
        return {
            ...this.stats,
            rate_limited_percentage: (this.stats.rate_limited / this.stats.total_requests) * 100
        };
    }
}
```

### 2. Set Up Alerts

Monitor rate limiting metrics in your application:

```python
import logging

# Set up rate limit monitoring
rate_limit_logger = logging.getLogger('rate_limits')
handler = logging.FileHandler('rate_limits.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
rate_limit_logger.addHandler(handler)

def log_rate_limit_status(response):
    remaining = response.headers.get('X-RateLimit-Remaining', 'unknown')
    limit = response.headers.get('X-RateLimit-Limit', 'unknown')
    
    rate_limit_logger.info(f"Rate limit status: {remaining}/{limit}")
    
    if response.status_code == 429:
        rate_limit_logger.warning("Rate limit exceeded!")
        # Send alert to monitoring system
        send_alert("Rate limit exceeded for weather API")
```

## Optimizing API Usage

### 1. Choose Appropriate Horizons

Different horizons have different use cases and update frequencies:

```python
# For real-time monitoring (updates every hour)
current_conditions = client.get_forecast({'horizon': '6h'})

# For daily planning (updates every 6 hours)
daily_forecast = client.get_forecast({'horizon': '24h'})

# For extended planning (updates every 12 hours)
extended_forecast = client.get_forecast({'horizon': '48h'})
```

### 2. Request Only Needed Variables

Only request variables you actually use:

```python
# ❌ Requesting all variables
all_vars = client.get_forecast({
    'variables': ['t2m', 'u10', 'v10', 'msl', 'r850', 'tp6h', 'cape', 't850', 'z500']
})

# ✅ Request only what you need
temperature_only = client.get_forecast({
    'variables': ['t2m']
})
```

### 3. Use Health Endpoint for Monitoring

The `/health` endpoint has higher rate limits and doesn't require authentication:

```python
# Use health endpoint for system monitoring
def is_api_healthy():
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        health_data = response.json()
        return health_data.get('ready', False)
    except:
        return False

# Check health before making forecast requests
if is_api_healthy():
    forecast = client.get_forecast()
else:
    print("API not ready, skipping forecast request")
```

## Rate Limit Exemptions

### 1. Health Checks

The `/health` endpoint has relaxed rate limiting to support:
- System monitoring and alerting
- Load balancer health checks
- Automated testing

### 2. Emergency Conditions

During severe weather events, rate limits may be temporarily relaxed for critical applications. Contact support if you need emergency access.

## Troubleshooting

### Common Issues

1. **Unexpected 429 responses**
   - Check if multiple applications share the same token
   - Verify request timing isn't too aggressive
   - Confirm you're handling Retry-After headers

2. **Rate limit headers missing**
   - Some proxy/CDN configurations may strip headers
   - Contact support if headers are consistently missing

3. **Inconsistent rate limits**
   - Ensure system clocks are synchronized
   - Rate limits use server time, not client time

### Debug Rate Limiting

```bash
#!/bin/bash
# Debug script to check rate limiting behavior

API_TOKEN="your_token_here"
BASE_URL="https://api.adelaideweather.example.com"

echo "Testing rate limits..."

for i in {1..65}; do
    echo -n "Request $i: "
    
    response=$(curl -s -w "%{http_code}|%{header_json}" \
        -H "Authorization: Bearer $API_TOKEN" \
        "$BASE_URL/forecast?horizon=6h&vars=t2m")
    
    http_code=$(echo "$response" | cut -d'|' -f1)
    headers=$(echo "$response" | cut -d'|' -f2-)
    
    remaining=$(echo "$headers" | jq -r '.["x-ratelimit-remaining"] // "unknown"')
    reset=$(echo "$headers" | jq -r '.["x-ratelimit-reset"] // "unknown"')
    
    echo "Status: $http_code, Remaining: $remaining, Reset: $reset"
    
    if [ "$http_code" = "429" ]; then
        retry_after=$(echo "$headers" | jq -r '.["retry-after"] // "60"')
        echo "Rate limited! Waiting ${retry_after}s..."
        sleep "$retry_after"
    fi
    
    sleep 1
done
```

## Support

If you're experiencing rate limiting issues:

1. **Check your implementation** against the best practices above
2. **Review your usage patterns** - are you making unnecessary requests?
3. **Contact support** at support@adelaideweather.example.com with:
   - Your API token (last 4 characters only)
   - Request patterns and timing
   - Error responses with correlation IDs
   - Your application requirements

## API Evolution

Rate limits may change over time based on:
- System capacity improvements
- Usage pattern analysis
- User feedback and requirements

Changes will be announced via:
- API changelog
- Email notifications to token holders
- HTTP warning headers before implementation

Subscribe to our developer newsletter for updates on rate limiting changes.