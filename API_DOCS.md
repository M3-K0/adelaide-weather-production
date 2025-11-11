# Adelaide Weather System - Complete API Documentation

## Table of Contents
- [Overview](#overview)
- [Authentication](#authentication)
- [Quick Start](#quick-start)
- [Core Endpoints](#core-endpoints)
- [Health Monitoring](#health-monitoring)
- [Administrative Endpoints](#administrative-endpoints)
- [Real-time Monitoring](#real-time-monitoring)
- [FAISS Analog Forecasting](#faiss-analog-forecasting)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Integration Examples](#integration-examples)
- [WebSocket Support](#websocket-support)
- [SDK and Client Libraries](#sdk-and-client-libraries)
- [Performance and Caching](#performance-and-caching)

## Overview

The Adelaide Weather System provides a production-ready REST API for analog ensemble weather forecasting using FAISS-powered historical pattern matching. The API delivers real-time forecasts with uncertainty quantification, risk assessment, and detailed analog analysis.

### Base URLs
- **Production**: `https://api.adelaideweather.example.com`
- **Staging**: `https://staging-api.adelaideweather.example.com`
- **Local Development**: `http://localhost:8000`
- **Local via NGINX**: `http://localhost/api` or `https://localhost/api`

### API Version
- **Current Version**: v2.0.0
- **Schema Version**: OpenAPI 3.0.3
- **Supported Formats**: JSON
- **Character Encoding**: UTF-8

### Key Features
- **Real-time forecasting** with 6h, 12h, 24h, and 48h horizons
- **FAISS analog search** with historical pattern matching
- **Uncertainty quantification** with confidence intervals and percentiles
- **Risk assessment** for weather hazards
- **Comprehensive health monitoring** with Kubernetes probe support
- **Performance optimization** with intelligent caching
- **Production security** with token authentication and rate limiting

## Authentication

### API Token Authentication

All endpoints require Bearer token authentication in the Authorization header:

```http
Authorization: Bearer YOUR_API_TOKEN_HERE
```

### Token Management

#### Obtaining a Token
```bash
# Token is provided during system deployment
# Check your deployment logs or environment file
cat .env.production | grep API_TOKEN

# Example token format (64 characters)
API_TOKEN=a1c8b9acf1c0450886a1e458aa4b69fb12be2c9c91bd32442b6203b6e4ccf0cb
```

#### Token Security
- Tokens are 256-bit cryptographically secure random values
- Automatic rotation every 24 hours (if enabled)
- Tokens should be stored securely and never logged
- Use environment variables or secure key management systems

#### Token Validation
```bash
# Validate token strength and status
curl -X POST -H "Authorization: Bearer $API_TOKEN" \
  http://localhost/api/admin/token/validate
```

### Authentication Examples

#### cURL
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Accept: application/json" \
     http://localhost/api/health
```

#### Python
```python
import requests

headers = {
    'Authorization': 'Bearer YOUR_TOKEN',
    'Accept': 'application/json'
}

response = requests.get('http://localhost/api/health', headers=headers)
```

#### JavaScript
```javascript
const headers = {
    'Authorization': 'Bearer YOUR_TOKEN',
    'Accept': 'application/json'
};

fetch('http://localhost/api/health', { headers })
    .then(response => response.json())
    .then(data => console.log(data));
```

## Quick Start

### 1. Basic Health Check

```bash
# Check if the system is running
curl http://localhost/api/health
```

**Expected Response:**
```json
{
  "ready": true,
  "checks": [
    {
      "name": "startup_validation",
      "status": "pass",
      "message": "Expert startup validation passed"
    }
  ],
  "model": {
    "version": "v1.0.0",
    "hash": "a7c3f92",
    "matched_ratio": 1.0
  },
  "uptime_seconds": 3600.5
}
```

### 2. First Forecast Request

```bash
# Get a 24-hour forecast for default variables
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost/api/forecast?horizon=24h"
```

**Expected Response:**
```json
{
  "horizon": "24h",
  "generated_at": "2024-01-15T12:00:00Z",
  "variables": {
    "t2m": {
      "value": 25.3,
      "p05": 22.1,
      "p95": 28.5,
      "confidence": 0.82,
      "available": true,
      "analog_count": 45
    }
  },
  "wind10m": {
    "speed": 3.7,
    "direction": 209,
    "available": true
  },
  "narrative": "Warm conditions with temperature around 25.3°C, light winds from SSW",
  "risk_assessment": {
    "thunderstorm": "low",
    "heat_stress": "low",
    "wind_damage": "minimal",
    "precipitation": "low"
  },
  "latency_ms": 127.5
}
```

### 3. Detailed Analog Analysis

```bash
# Get detailed analog patterns
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost/api/analogs?horizon=24h"
```

## Core Endpoints

### Forecast Generation

#### GET /forecast
Generate weather forecasts using analog ensemble methods.

**Parameters:**
- `horizon` (optional): Forecast time horizon - `6h`, `12h`, `24h`, `48h` (default: `24h`)
- `vars` (optional): Comma-separated weather variables (default: `t2m,u10,v10,msl`)

**Available Variables:**
- `t2m`: 2-meter temperature (°C)
- `u10`: 10-meter U wind component (m/s)
- `v10`: 10-meter V wind component (m/s)
- `msl`: Mean sea level pressure (hPa)
- `r850`: 850hPa relative humidity (%)
- `tp6h`: 6-hour total precipitation (mm)
- `cape`: Convective available potential energy (J/kg)
- `t850`: 850hPa temperature (°C)
- `z500`: 500hPa geopotential height (m)

**Examples:**

```bash
# Standard 24h forecast
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/forecast?horizon=24h"

# Extended 48h forecast with additional variables
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/forecast?horizon=48h&vars=t2m,u10,v10,msl,cape,tp6h"

# Short-term 6h forecast for temperature only
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/forecast?horizon=6h&vars=t2m"
```

**Response Format:**
```json
{
  "horizon": "24h",
  "generated_at": "2024-01-15T12:00:00Z",
  "variables": {
    "t2m": {
      "value": 25.3,
      "p05": 22.1,
      "p95": 28.5,
      "confidence": 0.82,
      "available": true,
      "analog_count": 45
    }
  },
  "wind10m": {
    "speed": 3.7,
    "direction": 209,
    "gust": null,
    "available": true
  },
  "narrative": "Forecast narrative description",
  "risk_assessment": {
    "thunderstorm": "low",
    "heat_stress": "low",
    "wind_damage": "minimal",
    "precipitation": "low"
  },
  "analogs_summary": {
    "most_similar_date": "2023-03-15T12:00:00Z",
    "similarity_score": 0.82,
    "analog_count": 45,
    "confidence_explanation": "Based on 45 historical analog patterns"
  },
  "versions": {
    "model": "v1.0.0",
    "index": "v1.0.0",
    "datasets": "v1.0.0"
  },
  "latency_ms": 127.5
}
```

### System Information

#### GET /health
Basic system health check suitable for monitoring and load balancer probes.

```bash
curl http://localhost/api/health
```

#### GET /info
System version and capability information.

```bash
curl http://localhost/api/info
```

#### GET /version
API version and compatibility information.

```bash
curl http://localhost/api/version
```

### Metrics and Monitoring

#### GET /metrics
Prometheus-compatible metrics for system monitoring.

**Authentication Required:** Yes

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost/api/metrics
```

**Response:** Prometheus text format
```
# HELP forecast_requests_total Total forecast requests
# TYPE forecast_requests_total counter
forecast_requests_total 1234.0

# HELP response_duration_seconds Forecast request duration
# TYPE response_duration_seconds histogram
response_duration_seconds_bucket{le="0.1"} 891.0
response_duration_seconds_bucket{le="0.25"} 1198.0
response_duration_seconds_sum 156.78
```

#### GET /metrics/summary
Human-readable metrics summary for operational monitoring.

**Authentication Required:** Yes

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost/api/metrics/summary
```

## Health Monitoring

### Kubernetes Health Probes

#### GET /health/live
Kubernetes liveness probe endpoint for container orchestration.

```bash
curl http://localhost/api/health/live
```

**Response:**
```json
{
  "status": "alive",
  "timestamp": "2024-01-15T12:00:00Z",
  "uptime_seconds": 3600.5
}
```

#### GET /health/ready
Kubernetes readiness probe endpoint for load balancer integration.

```bash
curl http://localhost/api/health/ready
```

**Response:**
```json
{
  "status": "ready",
  "timestamp": "2024-01-15T12:00:00Z",
  "components": {
    "forecast_adapter": "ready",
    "faiss_indices": "ready",
    "dependencies": "ready"
  }
}
```

### Detailed Health Checks

#### GET /health/detailed
Comprehensive health report with system status, startup validation, FAISS indices, configuration, security, and performance metrics.

**Authentication Required:** Yes

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost/api/health/detailed
```

#### GET /health/faiss
FAISS-specific health monitoring with real-time performance metrics.

**Authentication Required:** Yes

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost/api/health/faiss
```

**Response:**
```json
{
  "status": "healthy",
  "faiss_version": "1.7.4",
  "indices": {
    "24h_flatip": {
      "status": "healthy",
      "vectors": 13148,
      "size_mb": 45.2,
      "last_search_ms": 127.5
    }
  },
  "performance": {
    "avg_search_time_ms": 145.2,
    "cache_hit_rate": 0.85,
    "searches_per_second": 15.3,
    "memory_usage_mb": 512.8
  },
  "health_score": 95
}
```

#### GET /health/dependencies
External dependency status monitoring.

```bash
curl http://localhost/api/health/dependencies
```

#### GET /health/performance
Performance health check with SLA compliance metrics.

```bash
curl http://localhost/api/health/performance
```

#### GET /health/security
Security status and audit summary.

```bash
curl http://localhost/api/health/security
```

## Administrative Endpoints

### System Administration

#### GET /admin/status
Comprehensive administrative system status and overview.

**Authentication Required:** Yes

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost/api/admin/status
```

#### GET /admin/config
Configuration validation and status.

**Authentication Required:** Yes

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost/api/admin/config
```

#### GET /admin/security
Security audit summary and status.

**Authentication Required:** Yes

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost/api/admin/security
```

#### GET /admin/performance
Performance analytics with optimization recommendations.

**Authentication Required:** Yes

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost/api/admin/performance
```

### Token Management

#### POST /admin/token/validate
Validate current token strength and security.

**Authentication Required:** Yes

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost/api/admin/token/validate
```

#### GET /admin/token/status
Token status and rotation history.

**Authentication Required:** Yes

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost/api/admin/token/status
```

#### POST /admin/token/rotate
Initiate authentication token rotation (if enabled).

**Authentication Required:** Yes

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost/api/admin/token/rotate
```

## Real-time Monitoring

### Live System Metrics

#### GET /monitor/live
Real-time system metrics and status updates.

```bash
curl http://localhost/api/monitor/live
```

#### GET /monitor/faiss
Real-time FAISS performance monitoring and metrics.

```bash
curl http://localhost/api/monitor/faiss
```

#### GET /monitor/config
Configuration drift monitoring and alerts.

```bash
curl http://localhost/api/monitor/config
```

#### GET /monitor/security
Security event monitoring and alerts.

```bash
curl http://localhost/api/monitor/security
```

### Historical Analytics

#### GET /analytics/performance
Historical performance analytics and trends.

**Authentication Required:** Yes

```bash
# Get 24-hour performance data
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/analytics/performance?timerange=24h"

# Available timeranges: 1h, 24h, 7d, 30d
```

#### GET /analytics/usage
API usage patterns and trends.

**Authentication Required:** Yes

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost/api/analytics/usage
```

#### GET /analytics/errors
Error analysis and patterns with root cause analysis.

**Authentication Required:** Yes

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost/api/analytics/errors
```

## FAISS Analog Forecasting

### Analog Pattern Analysis

#### GET /analogs
Detailed historical analog patterns for current atmospheric conditions.

**Authentication Required:** Yes

**Parameters:**
- `horizon` (optional): Forecast horizon to analyze - `6h`, `12h`, `24h`, `48h` (default: `24h`)

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/analogs?horizon=24h"
```

**Response:**
```json
{
  "forecast_horizon": "24h",
  "top_analogs": [
    {
      "date": "2023-03-15T12:00:00Z",
      "similarity_score": 0.85,
      "initial_conditions": {
        "t2m": 24.8,
        "msl": 1014.5,
        "u10": 3.1,
        "v10": -1.5
      },
      "timeline": [
        {
          "hours_offset": 6,
          "values": {
            "t2m": 26.2,
            "msl": 1013.8
          },
          "events": ["clear_skies"],
          "temperature_trend": "rising",
          "pressure_trend": "falling"
        }
      ],
      "outcome_narrative": "Clear conditions continued with gradual temperature rise",
      "season_info": {
        "month": 3,
        "season": "autumn"
      }
    }
  ],
  "ensemble_stats": {
    "mean_outcomes": {
      "t2m": 25.3,
      "msl": 1015.2
    },
    "outcome_uncertainty": {
      "t2m": 2.1,
      "msl": 1.8
    },
    "common_events": ["clear_skies", "light_winds"]
  },
  "generated_at": "2024-01-15T12:00:00Z"
}
```

### FAISS Index Health

#### GET /health/faiss
Real-time FAISS index health and performance monitoring.

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost/api/health/faiss
```

#### GET /health/startup
Startup validation status including FAISS index loading.

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost/api/health/startup
```

#### GET /health/config
Configuration health including FAISS index configuration.

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost/api/health/config
```

## Error Handling

### Standard Error Format

All API errors follow a consistent format:

```json
{
  "error": {
    "code": 400,
    "message": "Invalid request parameters",
    "timestamp": "2024-01-15T12:00:00Z",
    "correlation_id": "req_123456"
  },
  "details": "Additional error details if available"
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Authentication required or invalid |
| 403 | Forbidden | Access denied |
| 404 | Not Found | Endpoint or resource not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | System not ready or overloaded |

### Common Error Scenarios

#### 1. Authentication Errors

```bash
# Missing token
curl http://localhost/api/forecast
# Response: 401 Unauthorized

# Invalid token
curl -H "Authorization: Bearer invalid_token" \
  http://localhost/api/forecast
# Response: 401 Unauthorized with error details
```

#### 2. Parameter Validation Errors

```bash
# Invalid horizon
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/forecast?horizon=invalid"

# Response:
{
  "error": {
    "code": 400,
    "message": "Invalid horizon. Must be one of: 6h, 12h, 24h, 48h",
    "timestamp": "2024-01-15T12:00:00Z",
    "correlation_id": "req_123456"
  }
}
```

#### 3. Rate Limiting Errors

```bash
# Rate limit exceeded
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost/api/forecast

# Response: 429 Too Many Requests
{
  "error": {
    "code": 429,
    "message": "Rate limit exceeded. Please try again later.",
    "timestamp": "2024-01-15T12:00:00Z",
    "correlation_id": "req_123456"
  }
}
# Headers: Retry-After: 60
```

#### 4. System Unavailable

```bash
# Service unavailable
curl http://localhost/api/forecast

# Response: 503 Service Unavailable
{
  "error": {
    "code": 503,
    "message": "Forecasting system not ready",
    "timestamp": "2024-01-15T12:00:00Z",
    "correlation_id": "req_123456"
  }
}
```

### Error Response Headers

| Header | Description | Example |
|--------|-------------|---------|
| `X-Request-ID` | Unique request identifier | `req_123456` |
| `Retry-After` | Seconds to wait before retry (429 errors) | `60` |
| `Cache-Control` | Caching policy | `no-cache` |

## Rate Limiting

### Rate Limit Policy

| Endpoint Category | Requests per Minute | Authentication Required |
|------------------|-------------------|------------------------|
| Forecast endpoints | 60 | Yes |
| Health endpoints | 30 | No |
| Admin endpoints | 20 | Yes |
| Metrics endpoints | 10 | Yes |
| Monitor endpoints | 15 | Yes |

### Rate Limit Headers

All responses include rate limiting information:

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1642248000
X-RateLimit-Window: 60
```

### Rate Limit Configuration

Rate limiting can be configured via environment variables:

```bash
# Enable/disable rate limiting
RATE_LIMIT_ENABLED=true

# Requests per minute for forecast endpoints
RATE_LIMIT_PER_MINUTE=60

# Custom rate limits for specific endpoints
RATE_LIMIT_HEALTH_PER_MINUTE=30
RATE_LIMIT_ADMIN_PER_MINUTE=20
```

### Handling Rate Limits

```python
import time
import requests

def make_request_with_retry(url, headers, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            continue
        
        return response
    
    raise Exception("Max retries exceeded")
```

## Integration Examples

### Python Client Example

```python
import requests
import time
from typing import Dict, Any, Optional

class AdelaideForecastClient:
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_token}',
            'Accept': 'application/json'
        })
    
    def get_forecast(self, horizon: str = '24h', 
                    variables: Optional[str] = None) -> Dict[str, Any]:
        """Get weather forecast with optional variables."""
        params = {'horizon': horizon}
        if variables:
            params['vars'] = variables
            
        response = self.session.get(
            f'{self.base_url}/forecast',
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def get_analogs(self, horizon: str = '24h') -> Dict[str, Any]:
        """Get detailed analog patterns."""
        response = self.session.get(
            f'{self.base_url}/analogs',
            params={'horizon': horizon}
        )
        response.raise_for_status()
        return response.json()
    
    def check_health(self) -> Dict[str, Any]:
        """Check system health."""
        # Health endpoint doesn't require authentication
        response = requests.get(f'{self.base_url}/health')
        response.raise_for_status()
        return response.json()
    
    def get_detailed_health(self) -> Dict[str, Any]:
        """Get detailed health information."""
        response = self.session.get(f'{self.base_url}/health/detailed')
        response.raise_for_status()
        return response.json()

# Usage example
client = AdelaideForecastClient(
    base_url='http://localhost/api',
    api_token='your-token-here'
)

# Get forecast
forecast = client.get_forecast(horizon='24h', variables='t2m,u10,v10,msl')
print(f"Temperature: {forecast['variables']['t2m']['value']}°C")
print(f"Wind Speed: {forecast['wind10m']['speed']} m/s")
print(f"Narrative: {forecast['narrative']}")

# Get analog patterns
analogs = client.get_analogs(horizon='24h')
print(f"Most similar date: {analogs['top_analogs'][0]['date']}")
print(f"Similarity score: {analogs['top_analogs'][0]['similarity_score']}")
```

### JavaScript/Node.js Client Example

```javascript
class AdelaideForecastClient {
    constructor(baseUrl, apiToken) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.apiToken = apiToken;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: {
                'Authorization': `Bearer ${this.apiToken}`,
                'Accept': 'application/json',
                ...options.headers
            },
            ...options
        };

        const response = await fetch(url, config);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(`API Error: ${error.error.message}`);
        }

        return response.json();
    }

    async getForecast(horizon = '24h', variables = null) {
        const params = new URLSearchParams({ horizon });
        if (variables) params.append('vars', variables);
        
        return this.request(`/forecast?${params}`);
    }

    async getAnalogs(horizon = '24h') {
        const params = new URLSearchParams({ horizon });
        return this.request(`/analogs?${params}`);
    }

    async checkHealth() {
        // Health endpoint doesn't require authentication
        const response = await fetch(`${this.baseUrl}/health`);
        if (!response.ok) throw new Error('Health check failed');
        return response.json();
    }

    async getDetailedHealth() {
        return this.request('/health/detailed');
    }

    async getMetrics() {
        return this.request('/metrics');
    }
}

// Usage example
const client = new AdelaideForecastClient(
    'http://localhost/api',
    'your-token-here'
);

// Get forecast with error handling
async function getForecastExample() {
    try {
        const forecast = await client.getForecast('24h', 't2m,u10,v10,msl');
        console.log('Temperature:', forecast.variables.t2m.value, '°C');
        console.log('Wind Speed:', forecast.wind10m.speed, 'm/s');
        console.log('Narrative:', forecast.narrative);
    } catch (error) {
        console.error('Forecast request failed:', error.message);
    }
}

// Get analog patterns
async function getAnalogsExample() {
    try {
        const analogs = await client.getAnalogs('24h');
        console.log('Most similar date:', analogs.top_analogs[0].date);
        console.log('Similarity score:', analogs.top_analogs[0].similarity_score);
        console.log('Outcome:', analogs.top_analogs[0].outcome_narrative);
    } catch (error) {
        console.error('Analogs request failed:', error.message);
    }
}
```

### cURL Script Examples

#### Automated Forecast Monitoring

```bash
#!/bin/bash
# forecast-monitor.sh - Monitor Adelaide Weather forecasts

API_TOKEN="your-token-here"
BASE_URL="http://localhost/api"
LOG_FILE="forecast-monitor.log"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to get forecast
get_forecast() {
    local horizon="$1"
    local variables="$2"
    
    curl -s -H "Authorization: Bearer $API_TOKEN" \
         -H "Accept: application/json" \
         "$BASE_URL/forecast?horizon=$horizon&vars=$variables"
}

# Function to check health
check_health() {
    curl -s -H "Accept: application/json" "$BASE_URL/health"
}

# Main monitoring loop
main() {
    log "Starting forecast monitoring..."
    
    while true; do
        # Check system health
        health=$(check_health)
        ready=$(echo "$health" | jq -r '.ready')
        
        if [ "$ready" = "true" ]; then
            log "System healthy - getting forecast"
            
            # Get 24h forecast
            forecast=$(get_forecast "24h" "t2m,u10,v10,msl")
            
            if echo "$forecast" | jq -e '.variables.t2m.value' > /dev/null; then
                temp=$(echo "$forecast" | jq -r '.variables.t2m.value')
                confidence=$(echo "$forecast" | jq -r '.variables.t2m.confidence')
                latency=$(echo "$forecast" | jq -r '.latency_ms')
                
                log "Forecast: ${temp}°C (confidence: $confidence, latency: ${latency}ms)"
            else
                log "ERROR: Failed to get forecast"
                echo "$forecast" | jq '.' >> "$LOG_FILE"
            fi
        else
            log "WARNING: System not ready"
        fi
        
        # Wait 5 minutes before next check
        sleep 300
    done
}

# Run monitoring
main "$@"
```

#### Batch Forecast Processing

```bash
#!/bin/bash
# batch-forecast.sh - Process multiple forecast requests

API_TOKEN="your-token-here"
BASE_URL="http://localhost/api"

# Array of forecast configurations
declare -a forecasts=(
    "6h:t2m,msl:short-term"
    "24h:t2m,u10,v10,msl:standard"
    "48h:t2m,u10,v10,msl,cape,tp6h:extended"
)

# Function to get forecast and save to file
process_forecast() {
    local horizon="$1"
    local variables="$2"
    local name="$3"
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local output_file="forecast_${name}_${timestamp}.json"
    
    echo "Processing $name forecast ($horizon with $variables)..."
    
    curl -s -H "Authorization: Bearer $API_TOKEN" \
         -H "Accept: application/json" \
         "$BASE_URL/forecast?horizon=$horizon&vars=$variables" \
         -o "$output_file"
    
    if jq -e '.variables' "$output_file" > /dev/null; then
        echo "✓ $name forecast saved to $output_file"
        
        # Extract key metrics
        local temp=$(jq -r '.variables.t2m.value // "N/A"' "$output_file")
        local latency=$(jq -r '.latency_ms // "N/A"' "$output_file")
        echo "  Temperature: ${temp}°C, Latency: ${latency}ms"
    else
        echo "✗ $name forecast failed"
        cat "$output_file"
    fi
}

# Process all forecasts
for forecast in "${forecasts[@]}"; do
    IFS=':' read -ra PARTS <<< "$forecast"
    process_forecast "${PARTS[0]}" "${PARTS[1]}" "${PARTS[2]}"
    echo ""
done

echo "Batch processing complete!"
```

## WebSocket Support

**Note**: The current API version focuses on REST endpoints. WebSocket support for real-time updates is planned for future releases.

### Planned WebSocket Endpoints

- `/ws/forecasts` - Real-time forecast updates
- `/ws/health` - Live system health monitoring
- `/ws/analogs` - Streaming analog pattern updates

### Alternative: Server-Sent Events

For real-time updates, consider polling the monitoring endpoints:

```javascript
// Simple polling for live updates
function startLiveMonitoring(callback, interval = 30000) {
    const poll = async () => {
        try {
            const response = await fetch('http://localhost/api/monitor/live');
            const data = await response.json();
            callback(data);
        } catch (error) {
            console.error('Monitoring update failed:', error);
        }
    };

    poll(); // Initial call
    return setInterval(poll, interval);
}

// Usage
const monitoringInterval = startLiveMonitoring(
    (data) => console.log('Live update:', data),
    30000  // Update every 30 seconds
);

// Stop monitoring
clearInterval(monitoringInterval);
```

## SDK and Client Libraries

### Official Python SDK

A comprehensive Python SDK is available for advanced integration:

```python
# Install the SDK
pip install adelaide-weather-sdk

# Use the SDK
from adelaide_weather import AdelaideWeatherClient

client = AdelaideWeatherClient(
    base_url='http://localhost/api',
    api_token='your-token'
)

# Advanced forecast with confidence intervals
forecast = client.get_forecast_with_uncertainty(
    horizon='24h',
    variables=['t2m', 'u10', 'v10', 'msl'],
    confidence_levels=[0.05, 0.95]
)

# Batch analog analysis
analogs = client.analyze_analogs_batch([
    '6h', '12h', '24h', '48h'
])

# Health monitoring with alerts
health_monitor = client.create_health_monitor(
    alert_callback=lambda event: print(f"Alert: {event}")
)
```

### JavaScript/TypeScript SDK

```typescript
// Install the SDK
npm install adelaide-weather-client

// Use the SDK
import { AdelaideWeatherClient } from 'adelaide-weather-client';

const client = new AdelaideWeatherClient({
    baseUrl: 'http://localhost/api',
    apiToken: 'your-token'
});

// TypeScript support with full type definitions
interface ForecastResponse {
    horizon: string;
    variables: Record<string, VariableResult>;
    wind10m: WindResult;
    narrative: string;
    // ... full type definitions available
}

const forecast: ForecastResponse = await client.getForecast({
    horizon: '24h',
    variables: ['t2m', 'u10', 'v10', 'msl']
});
```

## Performance and Caching

### Caching Strategy

The API implements intelligent caching to optimize performance:

#### Response Caching
- **Forecast endpoints**: 5-minute cache for identical requests
- **Health endpoints**: 30-second cache
- **Metrics endpoints**: 1-minute cache
- **Analog analysis**: 10-minute cache

#### Cache Headers

```http
Cache-Control: public, max-age=300
ETag: "abc123"
Last-Modified: Mon, 15 Jan 2024 12:00:00 GMT
```

#### Cache Validation

```bash
# Conditional request with ETag
curl -H "If-None-Match: abc123" \
     -H "Authorization: Bearer $TOKEN" \
     http://localhost/api/forecast

# Response: 304 Not Modified (if cached)
```

### Performance Optimization

#### Request Optimization
```bash
# Use compression
curl -H "Accept-Encoding: gzip, deflate" \
     -H "Authorization: Bearer $TOKEN" \
     http://localhost/api/forecast

# Minimize variables for faster response
curl -H "Authorization: Bearer $TOKEN" \
     "http://localhost/api/forecast?horizon=24h&vars=t2m"

# Use appropriate horizon for your use case
# 6h: ~50ms, 24h: ~150ms, 48h: ~300ms
```

#### Batch Processing
```python
# Efficient batch processing
import asyncio
import aiohttp

async def get_multiple_forecasts(horizons):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for horizon in horizons:
            task = session.get(
                f'http://localhost/api/forecast?horizon={horizon}',
                headers={'Authorization': 'Bearer YOUR_TOKEN'}
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        return [await r.json() for r in responses]

# Usage
forecasts = asyncio.run(get_multiple_forecasts(['6h', '24h', '48h']))
```

### Performance Monitoring

#### Response Time Monitoring
```bash
# Monitor API response times
curl -w "@curl-format.txt" \
     -H "Authorization: Bearer $TOKEN" \
     http://localhost/api/forecast

# curl-format.txt content:
#     time_namelookup:  %{time_namelookup}\n
#     time_connect:     %{time_connect}\n
#     time_appconnect:  %{time_appconnect}\n
#     time_pretransfer: %{time_pretransfer}\n
#     time_redirect:    %{time_redirect}\n
#     time_starttransfer: %{time_starttransfer}\n
#     ----------\n
#     time_total:       %{time_total}\n
```

#### Performance Metrics
```bash
# Get performance analytics
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost/api/admin/performance

# Get metrics summary
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost/api/metrics/summary
```

---

## Summary

The Adelaide Weather API provides comprehensive weather forecasting capabilities with:

- **Production-ready architecture** with health monitoring and observability
- **FAISS-powered analog forecasting** for accurate pattern-based predictions
- **Uncertainty quantification** with confidence intervals and risk assessment
- **Comprehensive monitoring** with health checks, metrics, and alerting
- **Security-first design** with authentication, rate limiting, and audit trails
- **Developer-friendly** with detailed documentation, SDKs, and examples

### Key Performance Characteristics
- **Forecast Generation**: 50-300ms depending on horizon
- **Health Checks**: <50ms response time
- **FAISS Search**: 100-200ms for analog analysis
- **Availability**: 99.9% uptime with proper deployment
- **Rate Limits**: 60 requests/minute for forecast endpoints

### Getting Started Checklist
1. ✓ Deploy the system using `./deploy-adelaide-weather.sh`
2. ✓ Obtain your API token from deployment logs
3. ✓ Test basic health check: `curl http://localhost/api/health`
4. ✓ Get your first forecast: `curl -H "Authorization: Bearer TOKEN" http://localhost/api/forecast`
5. ✓ Explore detailed analog patterns: `curl -H "Authorization: Bearer TOKEN" http://localhost/api/analogs`
6. ✓ Monitor system health: Access Grafana at http://localhost:3001

For additional support, refer to the deployment guide (README-DEPLOYMENT.md) or the system monitoring dashboards.