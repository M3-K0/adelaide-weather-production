# Authentication Guide

The Adelaide Weather Forecasting API uses Bearer token authentication to secure access to forecast data and system metrics.

## Overview

All API endpoints except `/health` require authentication using a Bearer token in the `Authorization` header.

## Getting Your API Token

1. **Contact your system administrator** to request an API token
2. **Store the token securely** - treat it like a password
3. **Use environment variables** in production applications
4. **Rotate tokens regularly** for security

## Authentication Header Format

Include your token in every API request:

```http
Authorization: Bearer YOUR_TOKEN_HERE
```

## Implementation Examples

### curl

```bash
# Basic forecast request
curl -X GET "https://api.adelaideweather.example.com/forecast" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Accept: application/json"

# Request with parameters
curl -X GET "https://api.adelaideweather.example.com/forecast?horizon=24h&vars=t2m,u10,v10,msl" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Accept: application/json"
```

### Python

```python
import requests
import os

# Store token in environment variable
API_TOKEN = os.getenv('WEATHER_API_TOKEN')
BASE_URL = 'https://api.adelaideweather.example.com'

headers = {
    'Authorization': f'Bearer {API_TOKEN}',
    'Accept': 'application/json',
    'User-Agent': 'MyApp/1.0.0'
}

# Make authenticated request
response = requests.get(f'{BASE_URL}/forecast', headers=headers)

if response.status_code == 200:
    forecast = response.json()
    print(f"Temperature: {forecast['variables']['t2m']['value']}°C")
elif response.status_code == 401:
    print("Authentication failed - check your token")
elif response.status_code == 403:
    print("Access forbidden - token may be invalid")
else:
    print(f"Request failed: {response.status_code}")
```

### JavaScript (Node.js)

```javascript
const fetch = require('node-fetch');

const API_TOKEN = process.env.WEATHER_API_TOKEN;
const BASE_URL = 'https://api.adelaideweather.example.com';

const headers = {
    'Authorization': `Bearer ${API_TOKEN}`,
    'Accept': 'application/json',
    'User-Agent': 'MyApp/1.0.0'
};

async function getForecast() {
    try {
        const response = await fetch(`${BASE_URL}/forecast`, { headers });
        
        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('Authentication failed - check your token');
            }
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const forecast = await response.json();
        return forecast;
    } catch (error) {
        console.error('Forecast request failed:', error.message);
        throw error;
    }
}

// Usage
getForecast()
    .then(forecast => {
        console.log('Forecast narrative:', forecast.narrative);
    })
    .catch(error => {
        console.error('Error:', error.message);
    });
```

### JavaScript (Browser)

```javascript
class WeatherClient {
    constructor(apiToken, baseUrl = 'https://api.adelaideweather.example.com') {
        this.apiToken = apiToken;
        this.baseUrl = baseUrl;
    }
    
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const headers = {
            'Authorization': `Bearer ${this.apiToken}`,
            'Accept': 'application/json',
            ...options.headers
        };
        
        try {
            const response = await fetch(url, { ...options, headers });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error?.message || `HTTP ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }
    
    async getForecast(horizon = '24h', variables = 't2m,u10,v10,msl') {
        const params = new URLSearchParams({ horizon, vars: variables });
        return this.request(`/forecast?${params}`);
    }
    
    async getHealth() {
        return this.request('/health');
    }
}

// Usage
const client = new WeatherClient('YOUR_TOKEN_HERE');

client.getForecast('24h', 't2m,u10,v10,msl,cape')
    .then(forecast => {
        console.log('Temperature:', forecast.variables.t2m.value);
        console.log('Risk assessment:', forecast.risk_assessment);
    })
    .catch(error => console.error('Error:', error.message));
```

## Security Best Practices

### 1. Token Storage

**✅ Do:**
- Store tokens in environment variables
- Use secure credential management systems
- Rotate tokens regularly
- Use different tokens for different environments

**❌ Don't:**
- Hard-code tokens in source code
- Commit tokens to version control
- Share tokens between applications
- Log tokens in application logs

### 2. Network Security

**✅ Do:**
- Always use HTTPS in production
- Validate SSL certificates
- Use connection timeouts
- Implement retry logic with exponential backoff

**❌ Don't:**
- Use HTTP for API calls
- Ignore SSL certificate errors
- Make requests without timeouts
- Retry immediately on failures

### 3. Error Handling

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_session_with_retries():
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        method_whitelist=["HEAD", "GET", "OPTIONS"],
        backoff_factor=1
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

def make_authenticated_request(endpoint, token):
    session = create_session_with_retries()
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }
    
    try:
        response = session.get(endpoint, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise AuthenticationError("Invalid or expired token")
        elif e.response.status_code == 429:
            raise RateLimitError("Rate limit exceeded")
        else:
            raise APIError(f"HTTP {e.response.status_code}: {e.response.text}")
    except requests.exceptions.Timeout:
        raise TimeoutError("Request timed out")
    except requests.exceptions.ConnectionError:
        raise ConnectionError("Failed to connect to API")
```

## Rate Limiting

Each endpoint has specific rate limits:

- **Forecast endpoint**: 60 requests per minute
- **Health endpoint**: 30 requests per minute (no auth required)
- **Metrics endpoint**: 10 requests per minute (requires auth)
- **Analogs endpoint**: 10 requests per minute (requires auth)

### Handling Rate Limits

When you exceed rate limits, the API returns HTTP 429 with a `Retry-After` header:

```python
def handle_rate_limit(response):
    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 60))
        print(f"Rate limited. Retry after {retry_after} seconds")
        time.sleep(retry_after)
        # Retry the request
```

## Error Responses

Authentication errors return standardized error responses:

### 401 Unauthorized

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

### 403 Forbidden

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

## Testing Authentication

### Using the Interactive Documentation

1. Go to the [API documentation portal](./index.html)
2. Click the **"Authorize"** button
3. Enter your token in the format: `YOUR_TOKEN_HERE`
4. Click **"Authorize"**
5. Test endpoints using the **"Try it out"** button

### Using curl

Test your token:

```bash
# Test authentication
curl -X GET "https://api.adelaideweather.example.com/forecast" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Accept: application/json" \
  -w "\nHTTP Status: %{http_code}\n"

# Expected output for valid token:
# HTTP Status: 200
# + JSON forecast response

# Expected output for invalid token:
# HTTP Status: 401
# + JSON error response
```

## Environment Setup

### Development Environment

```bash
# .env file
WEATHER_API_TOKEN=your_development_token_here
WEATHER_API_BASE_URL=http://localhost:8000

# Load in your application
export $(cat .env | xargs)
```

### Production Environment

```bash
# Set environment variables securely
export WEATHER_API_TOKEN="your_production_token_here"
export WEATHER_API_BASE_URL="https://api.adelaideweather.example.com"
```

### Docker Environment

```dockerfile
# Dockerfile
ENV WEATHER_API_TOKEN=""
ENV WEATHER_API_BASE_URL="https://api.adelaideweather.example.com"

# Pass token at runtime
docker run -e WEATHER_API_TOKEN="your_token" your_app
```

## Troubleshooting

### Common Issues

1. **"Not authenticated" error**
   - Check token format (should not include "Bearer ")
   - Verify token is valid and not expired
   - Ensure Authorization header is correctly formatted

2. **"Invalid authentication token format" error**
   - Token contains invalid characters
   - Token is too short or too long
   - Leading/trailing whitespace in token

3. **Connection errors**
   - Check network connectivity
   - Verify API endpoint URL
   - Ensure HTTPS is used for production

### Debug Steps

1. **Verify token format**:
   ```bash
   echo "Token length: ${#WEATHER_API_TOKEN}"
   echo "Token starts with: ${WEATHER_API_TOKEN:0:10}..."
   ```

2. **Test with curl**:
   ```bash
   curl -v -X GET "https://api.adelaideweather.example.com/health"
   ```

3. **Check headers**:
   ```bash
   curl -X GET "https://api.adelaideweather.example.com/forecast" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -D headers.txt \
     -o response.json
   cat headers.txt
   ```

## Support

If you're experiencing authentication issues:

1. **Verify token validity** with your system administrator
2. **Check rate limits** - you may be making too many requests
3. **Review error logs** for correlation IDs to help with debugging
4. **Contact support** at support@adelaideweather.example.com with:
   - Error message and HTTP status code
   - Correlation ID from error response
   - Timestamp of the request
   - Your application details (but never include your token)

Remember: Never share your API token in support requests or public forums.