# Error Codes Reference

The Adelaide Weather Forecasting API uses standard HTTP status codes along with detailed error responses to help you diagnose and resolve issues quickly.

## Error Response Format

All error responses follow a consistent JSON structure:

```json
{
    "error": {
        "code": 400,
        "message": "Invalid horizon. Must be one of: 6h, 12h, 24h, 48h",
        "timestamp": "2024-01-15T12:00:00Z",
        "correlation_id": "req_123456"
    },
    "details": "Additional context about the error (optional)"
}
```

### Error Response Fields

- **`code`**: HTTP status code
- **`message`**: Human-readable error description
- **`timestamp`**: ISO 8601 timestamp when error occurred
- **`correlation_id`**: Unique identifier for debugging (include in support requests)
- **`details`**: Additional error context (optional)

## HTTP Status Codes

### 2xx Success

#### 200 OK
Request successful and data returned.

```json
{
    "horizon": "24h",
    "generated_at": "2024-01-15T12:00:00Z",
    "variables": { /* forecast data */ }
}
```

### 4xx Client Errors

#### 400 Bad Request
Invalid request parameters or malformed request.

**Common Causes:**
- Invalid horizon value
- Invalid variable names
- Malformed query parameters
- Invalid request format

**Examples:**

```json
{
    "error": {
        "code": 400,
        "message": "Invalid horizon. Must be one of: 6h, 12h, 24h, 48h",
        "timestamp": "2024-01-15T12:00:00Z",
        "correlation_id": "req_123456"
    }
}
```

```json
{
    "error": {
        "code": 400,
        "message": "Invalid variables: invalid_var. Valid variables: t2m,u10,v10,msl,r850,tp6h,cape,t850,z500",
        "timestamp": "2024-01-15T12:00:00Z",
        "correlation_id": "req_123456"
    }
}
```

**Resolution:**
- Check parameter values against API documentation
- Validate request format
- Review query parameter syntax

#### 401 Unauthorized
Authentication required or invalid token.

**Common Causes:**
- Missing Authorization header
- Invalid API token
- Expired token
- Malformed token format

**Example:**

```json
{
    "error": {
        "code": 401,
        "message": "Invalid authentication token",
        "timestamp": "2024-01-15T12:00:00Z",
        "correlation_id": "req_123456"
    }
}
```

**Resolution:**
- Include `Authorization: Bearer YOUR_TOKEN` header
- Verify token is valid and not expired
- Check token format (no spaces, correct characters)
- Contact administrator for new token if needed

#### 403 Forbidden
Valid authentication but insufficient permissions.

**Common Causes:**
- Token doesn't have access to requested endpoint
- Token has been revoked
- Account suspended

**Example:**

```json
{
    "error": {
        "code": 403,
        "message": "Not authenticated",
        "timestamp": "2024-01-15T12:00:00Z",
        "correlation_id": "req_123456"
    }
}
```

**Resolution:**
- Verify token permissions with administrator
- Check if account is active
- Ensure using correct token for environment

#### 404 Not Found
Requested endpoint doesn't exist.

**Common Causes:**
- Incorrect URL path
- Typo in endpoint name
- Using deprecated endpoint

**Example:**

```json
{
    "error": {
        "code": 404,
        "message": "Endpoint not found",
        "timestamp": "2024-01-15T12:00:00Z",
        "correlation_id": "req_123456"
    }
}
```

**Resolution:**
- Check URL path against API documentation
- Verify endpoint exists and is not deprecated
- Check for typos in request URL

#### 422 Unprocessable Entity
Request is well-formed but contains semantic errors.

**Common Causes:**
- Parameter combinations that don't make sense
- Values outside acceptable ranges
- Conflicting parameters

**Example:**

```json
{
    "error": {
        "code": 422,
        "message": "Variable 'cape' not available for horizon '6h'",
        "timestamp": "2024-01-15T12:00:00Z",
        "correlation_id": "req_123456"
    }
}
```

**Resolution:**
- Review parameter combinations
- Check valid ranges for parameters
- Consult documentation for parameter constraints

#### 429 Too Many Requests
Rate limit exceeded.

**Common Causes:**
- Too many requests in time window
- Burst of requests exceeding limit
- Multiple applications using same token

**Example:**

```json
{
    "error": {
        "code": 429,
        "message": "Rate limit exceeded. Please try again later.",
        "timestamp": "2024-01-15T12:00:00Z",
        "correlation_id": "req_123456"
    }
}
```

**Headers:**
```http
Retry-After: 60
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1642262460
```

**Resolution:**
- Wait for time specified in `Retry-After` header
- Implement exponential backoff
- Review rate limiting documentation
- Consider caching responses
- Check if multiple apps share token

### 5xx Server Errors

#### 500 Internal Server Error
Unexpected server error.

**Common Causes:**
- Server-side bug
- Database connectivity issues
- Unexpected system state

**Example:**

```json
{
    "error": {
        "code": 500,
        "message": "Internal server error",
        "timestamp": "2024-01-15T12:00:00Z",
        "correlation_id": "req_123456"
    }
}
```

**Resolution:**
- Retry request with exponential backoff
- Check system status page
- Contact support with correlation ID
- No client-side action needed

#### 502 Bad Gateway
Upstream service error.

**Common Causes:**
- Load balancer issues
- Proxy configuration problems
- Upstream service unavailable

**Resolution:**
- Retry request after short delay
- Check system status
- Contact support if persistent

#### 503 Service Unavailable
Service temporarily unavailable.

**Common Causes:**
- System maintenance
- Forecasting model loading
- High system load
- System startup

**Example:**

```json
{
    "error": {
        "code": 503,
        "message": "Forecasting system not ready",
        "timestamp": "2024-01-15T12:00:00Z",
        "correlation_id": "req_123456"
    }
}
```

**Resolution:**
- Wait and retry with exponential backoff
- Check `/health` endpoint for system status
- Monitor system startup progress
- Contact support if extended outage

#### 504 Gateway Timeout
Request timeout from upstream service.

**Common Causes:**
- Model computation taking too long
- Database query timeout
- Network connectivity issues

**Resolution:**
- Retry request
- Try simpler request (fewer variables)
- Check network connectivity
- Contact support if persistent

## Specific Error Scenarios

### Authentication Errors

#### Invalid Token Format
```json
{
    "error": {
        "code": 401,
        "message": "Invalid token format",
        "timestamp": "2024-01-15T12:00:00Z",
        "correlation_id": "req_123456"
    }
}
```

**Cause:** Token contains invalid characters or wrong length
**Fix:** Check token format, remove any spaces or special characters

#### Token Expired
```json
{
    "error": {
        "code": 401,
        "message": "Token has expired",
        "timestamp": "2024-01-15T12:00:00Z",
        "correlation_id": "req_123456"
    }
}
```

**Cause:** API token has expired
**Fix:** Request new token from administrator

#### Missing Authorization Header
```json
{
    "error": {
        "code": 401,
        "message": "Authorization header required",
        "timestamp": "2024-01-15T12:00:00Z",
        "correlation_id": "req_123456"
    }
}
```

**Cause:** Request doesn't include `Authorization` header
**Fix:** Add `Authorization: Bearer YOUR_TOKEN` header

### Validation Errors

#### Invalid Horizon
```json
{
    "error": {
        "code": 400,
        "message": "Invalid horizon 'abc'. Must be one of: 6h, 12h, 24h, 48h",
        "timestamp": "2024-01-15T12:00:00Z",
        "correlation_id": "req_123456"
    }
}
```

**Valid Values:** `6h`, `12h`, `24h`, `48h`

#### Invalid Variables
```json
{
    "error": {
        "code": 400,
        "message": "Invalid variables: temp, wind. Valid variables: t2m,u10,v10,msl,r850,tp6h,cape,t850,z500",
        "timestamp": "2024-01-15T12:00:00Z",
        "correlation_id": "req_123456"
    }
}
```

**Valid Variables:** `t2m`, `u10`, `v10`, `msl`, `r850`, `tp6h`, `cape`, `t850`, `z500`

#### Variables List Too Long
```json
{
    "error": {
        "code": 400,
        "message": "Variables parameter too long. Maximum 500 characters.",
        "timestamp": "2024-01-15T12:00:00Z",
        "correlation_id": "req_123456"
    }
}
```

**Fix:** Reduce number of variables or make multiple requests

#### Invalid Variable Pattern
```json
{
    "error": {
        "code": 400,
        "message": "Variables parameter contains invalid characters. Use only alphanumeric, underscore, and comma.",
        "timestamp": "2024-01-15T12:00:00Z",
        "correlation_id": "req_123456"
    }
}
```

**Fix:** Remove spaces and special characters from variables list

### System Errors

#### Model Not Ready
```json
{
    "error": {
        "code": 503,
        "message": "Forecasting model is loading. Please try again in a few minutes.",
        "timestamp": "2024-01-15T12:00:00Z",
        "correlation_id": "req_123456"
    }
}
```

**Fix:** Wait for model to load, check `/health` endpoint

#### Index Corrupted
```json
{
    "error": {
        "code": 503,
        "message": "Search index corrupted. System recovery in progress.",
        "timestamp": "2024-01-15T12:00:00Z",
        "correlation_id": "req_123456"
    }
}
```

**Fix:** Wait for system recovery, contact support if persistent

#### Data Unavailable
```json
{
    "error": {
        "code": 422,
        "message": "Forecast data temporarily unavailable for requested horizon",
        "timestamp": "2024-01-15T12:00:00Z",
        "correlation_id": "req_123456"
    }
}
```

**Fix:** Try different horizon or contact support

## Error Handling Best Practices

### 1. Implement Retry Logic

```python
import time
import random
from requests.exceptions import HTTPError

def make_request_with_retry(func, max_retries=3):
    """Make request with exponential backoff retry."""
    
    for attempt in range(max_retries):
        try:
            response = func()
            return response
            
        except HTTPError as e:
            status_code = e.response.status_code
            
            # Don't retry client errors (except 429)
            if 400 <= status_code < 500 and status_code != 429:
                raise
            
            if attempt == max_retries - 1:
                raise
            
            # Calculate backoff delay
            if status_code == 429:
                # Use Retry-After header if available
                retry_after = e.response.headers.get('Retry-After')
                delay = int(retry_after) if retry_after else 60
            else:
                # Exponential backoff with jitter
                delay = (2 ** attempt) + random.uniform(0.1, 1.0)
            
            print(f"Request failed (attempt {attempt + 1}), retrying in {delay:.1f}s")
            time.sleep(delay)
    
    return None
```

### 2. Handle Specific Error Types

```python
def handle_api_error(response):
    """Handle API errors with specific actions."""
    
    if not response.ok:
        try:
            error_data = response.json()
            error_code = error_data.get('error', {}).get('code', response.status_code)
            error_message = error_data.get('error', {}).get('message', 'Unknown error')
            correlation_id = error_data.get('error', {}).get('correlation_id', 'unknown')
            
        except ValueError:
            error_code = response.status_code
            error_message = response.reason
            correlation_id = 'unknown'
        
        if error_code == 401:
            raise AuthenticationError(f"Authentication failed: {error_message}")
        elif error_code == 403:
            raise PermissionError(f"Access denied: {error_message}")
        elif error_code == 400:
            raise ValueError(f"Invalid request: {error_message}")
        elif error_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            raise RateLimitError(f"Rate limited: {error_message}", retry_after)
        elif error_code == 503:
            raise ServiceUnavailableError(f"Service unavailable: {error_message}")
        else:
            raise APIError(f"API error {error_code}: {error_message}", correlation_id)
    
    return response
```

### 3. Log Errors for Debugging

```python
import logging

logger = logging.getLogger('weather_api')

def log_api_error(response, request_details=None):
    """Log API errors with correlation IDs."""
    
    try:
        error_data = response.json()
        correlation_id = error_data.get('error', {}).get('correlation_id', 'unknown')
        error_message = error_data.get('error', {}).get('message', 'Unknown error')
        
        logger.error(
            f"API Error {response.status_code}: {error_message} "
            f"(correlation_id: {correlation_id})",
            extra={
                'correlation_id': correlation_id,
                'status_code': response.status_code,
                'request_details': request_details
            }
        )
    except ValueError:
        logger.error(
            f"API Error {response.status_code}: {response.reason}",
            extra={'status_code': response.status_code}
        )
```

### 4. Graceful Degradation

```python
def get_forecast_with_fallback(client, horizon='24h', variables=None):
    """Get forecast with graceful degradation."""
    
    if variables is None:
        variables = ['t2m', 'u10', 'v10', 'msl']
    
    try:
        # Try full request
        return client.get_forecast({
            'horizon': horizon,
            'variables': variables
        })
        
    except ValidationError as e:
        # Try with fewer variables
        logger.warning(f"Full request failed: {e}")
        essential_vars = ['t2m', 'msl']  # Most important variables
        
        try:
            return client.get_forecast({
                'horizon': horizon,
                'variables': essential_vars
            })
        except Exception as fallback_error:
            logger.error(f"Fallback request also failed: {fallback_error}")
            raise
    
    except ServiceUnavailableError:
        # Try shorter horizon
        if horizon != '6h':
            logger.warning(f"Service unavailable for {horizon}, trying 6h")
            return get_forecast_with_fallback(client, '6h', variables)
        else:
            raise
```

## Debugging with Correlation IDs

Every error response includes a correlation ID for debugging. Include this when contacting support:

```bash
# Extract correlation ID from error response
curl -s -X GET "https://api.adelaideweather.example.com/forecast?horizon=invalid" \
  -H "Authorization: Bearer YOUR_TOKEN" | jq '.error.correlation_id'
```

**Support Request Template:**
```
Subject: API Error - [Brief Description]

Error Details:
- HTTP Status: 400
- Error Message: Invalid horizon
- Correlation ID: req_123456
- Timestamp: 2024-01-15T12:00:00Z
- Request URL: /forecast?horizon=invalid&vars=t2m

Additional Context:
[Your description of what you were trying to do]
```

## Error Monitoring

Set up monitoring for different error types:

```python
# Track error rates by type
error_counts = {
    'authentication': 0,
    'validation': 0,
    'rate_limit': 0,
    'server_error': 0,
    'total_requests': 0
}

def track_error(response):
    error_counts['total_requests'] += 1
    
    if response.status_code == 401:
        error_counts['authentication'] += 1
    elif response.status_code == 400:
        error_counts['validation'] += 1
    elif response.status_code == 429:
        error_counts['rate_limit'] += 1
    elif response.status_code >= 500:
        error_counts['server_error'] += 1

# Alert if error rate exceeds threshold
def check_error_rate():
    total = error_counts['total_requests']
    if total > 100:  # Minimum requests for meaningful stats
        error_rate = (total - sum([
            error_counts['authentication'],
            error_counts['validation'], 
            error_counts['rate_limit'],
            error_counts['server_error']
        ])) / total
        
        if error_rate > 0.1:  # 10% error rate
            send_alert(f"High error rate: {error_rate:.1%}")
```

## Getting Help

When encountering errors:

1. **Check this documentation** for common solutions
2. **Review your request** against the API specification
3. **Check system status** via the `/health` endpoint
4. **Implement proper error handling** and retry logic
5. **Contact support** with correlation IDs and detailed error information

**Support Contact:** support@adelaideweather.example.com

**Include in Support Requests:**
- Error message and HTTP status code
- Correlation ID from error response
- Full request details (URL, headers, parameters)
- Timestamp when error occurred
- Description of expected vs. actual behavior
- Your application environment details