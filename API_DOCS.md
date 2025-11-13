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
  - [Analog Pattern Analysis](#analog-pattern-analysis)
  - [FAISS Search Methodology](#faiss-search-methodology)
  - [Integration Examples](#integration-examples)
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

#### GET /api/analogs
Comprehensive analog weather pattern search with detailed FAISS-based historical pattern matching.

**Authentication Required:** Yes

**Overview:**
The `/api/analogs` endpoint provides in-depth historical weather pattern analysis by searching through vast FAISS-indexed databases to find atmospheric conditions most similar to current or specified conditions. This endpoint is particularly valuable for:

- Understanding historical precedents for current weather patterns
- Analyzing uncertainty through ensemble statistics 
- Exploring detailed weather evolution timelines
- Meteorological pattern recognition and research
- Risk assessment based on historical outcomes

**Parameters:**

| Parameter | Type | Required | Default | Description | Validation |
|-----------|------|----------|---------|-------------|-----------|
| `horizon` | string | No | `24h` | Forecast horizon to analyze | Must be one of: `6h`, `12h`, `24h`, `48h` |
| `variables` | string | No | `t2m,u10,v10,msl` | Comma-separated weather variables | Valid variables: `t2m`, `u10`, `v10`, `msl`, `r850`, `tp6h`, `cape`, `t850`, `z500` |
| `k` | integer | No | 10 | Number of analog patterns to return | Range: 1-200 |
| `query_time` | string | No | current time | ISO 8601 datetime for analog search | Must be within 5 years past to 30 days future |

**Examples:**

```bash
# Basic analog search for 24h horizon
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/analogs?horizon=24h"

# Advanced search with specific variables and more analogs
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/analogs?horizon=12h&variables=t2m,msl,cape&k=20"

# Historical analog search for specific time
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/analogs?horizon=48h&query_time=2024-01-15T12:00:00Z&k=5"
```

**Response Format:**

The response follows the `AnalogExplorerData` schema with comprehensive pattern analysis:

```json
{
  "forecast_horizon": "24h",
  "top_analogs": [
    {
      "date": "2023-03-15T12:00:00Z",
      "similarity_score": 0.89,
      "initial_conditions": {
        "t2m": 22.1,
        "msl": 1013.4,
        "u10": 2.5,
        "v10": -1.2
      },
      "timeline": [
        {
          "hours_offset": 0,
          "values": {
            "t2m": 22.1,
            "msl": 1013.4
          },
          "events": null,
          "temperature_trend": "stable",
          "pressure_trend": "stable"
        },
        {
          "hours_offset": 12,
          "values": {
            "t2m": 24.5,
            "msl": 1015.2
          },
          "events": ["Cloud cover increased"],
          "temperature_trend": "rising",
          "pressure_trend": "rising"
        },
        {
          "hours_offset": 24,
          "values": {
            "t2m": 26.2,
            "msl": 1016.8
          },
          "events": ["Clear skies returned"],
          "temperature_trend": "rising",
          "pressure_trend": "rising"
        }
      ],
      "outcome_narrative": "Pattern showed stable conditions evolving into typical autumn weather with gradual warming and pressure rise over 24 hours.",
      "location": {
        "latitude": -34.9285,
        "longitude": 138.6007,
        "name": "Adelaide Weather Station"
      },
      "season_info": {
        "month": 3,
        "season": "autumn"
      }
    }
  ],
  "ensemble_stats": {
    "mean_outcomes": {
      "t2m": 23.7,
      "msl": 1014.2,
      "u10": 4.1,
      "v10": -2.3
    },
    "outcome_uncertainty": {
      "t2m": 2.8,
      "msl": 5.4,
      "u10": 3.2,
      "v10": 2.9
    },
    "common_events": [
      "Cloud cover increased",
      "Wind direction shifted",
      "Pressure began rising"
    ]
  },
  "generated_at": "2024-01-15T14:30:00Z"
}
```

**Response Fields Explanation:**

- **`forecast_horizon`**: The forecast horizon for which analogs were searched
- **`top_analogs`**: Array of most similar historical patterns, ordered by similarity score
  - **`date`**: ISO 8601 datetime of historical pattern occurrence
  - **`similarity_score`**: Similarity to current conditions (0-1, higher = more similar)
  - **`initial_conditions`**: Weather conditions at the start of historical pattern
  - **`timeline`**: Chronological sequence of weather evolution during the pattern
  - **`outcome_narrative`**: Human-readable description of what happened historically
  - **`location`**: Geographic coordinates where pattern was observed
  - **`season_info`**: Temporal context (month and season)
- **`ensemble_stats`**: Statistical summary across all analog patterns
  - **`mean_outcomes`**: Mean final values across all analogs for each variable
  - **`outcome_uncertainty`**: Standard deviation of outcomes (uncertainty measure)
  - **`common_events`**: Weather events that occurred in multiple patterns
- **`generated_at`**: ISO 8601 timestamp when analysis was generated

**FAISS Search Methodology:**

The analog search uses advanced FAISS (Facebook AI Similarity Search) indexing for high-performance pattern matching:

1. **Embedding Generation**: Current atmospheric conditions are converted to high-dimensional vectors using trained meteorological embeddings
2. **Index Selection**: Horizon-specific FAISS indices (6h, 12h, 24h, 48h) ensure optimal pattern matching for the requested timeframe
3. **Similarity Search**: L2 distance metrics identify the most similar historical atmospheric patterns
4. **Post-processing**: Results include temporal context, geographical information, and meteorological narrative analysis

**Performance Characteristics:**
- **Search Time**: 100-300ms depending on horizon and k value
- **Index Size**: ~13,000 historical patterns per horizon
- **Memory Usage**: Optimized for production deployment with connection pooling
- **Accuracy**: Similarity scores >0.8 indicate strong pattern matches

**Rate Limiting:**
- **Rate Limit**: 60 requests/minute (same as forecast endpoints)
- **Headers**: Standard rate limiting headers included in response
- **Burst Protection**: Automatic throttling during high usage periods

**Error Responses:**

```json
// 400 Bad Request - Invalid parameters
{
  "error": {
    "code": 400,
    "message": "Invalid analog request parameters: Parameter 'k' must be an integer between 1 and 200",
    "timestamp": "2024-01-15T14:30:00Z",
    "correlation_id": "req_123456"
  }
}

// 503 Service Unavailable - FAISS service issues
{
  "error": {
    "code": 503,
    "message": "Analog search service not available",
    "timestamp": "2024-01-15T14:30:00Z",
    "correlation_id": "req_123456"
  }
}

// 500 Internal Server Error - Search failure
{
  "error": {
    "code": 500,
    "message": "Analog search failed: FAISS index not accessible",
    "timestamp": "2024-01-15T14:30:00Z",
    "correlation_id": "req_123456"
  }
}
```

**Integration Examples:**

#### Python Integration
```python
import requests
import json
from typing import Dict, Any

class AnalogSearchClient:
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Accept': 'application/json'
        }
    
    def search_analogs(self, horizon: str = '24h', variables: str = None, 
                      k: int = 10, query_time: str = None) -> Dict[str, Any]:
        """Search for historical analog weather patterns."""
        params = {'horizon': horizon, 'k': k}
        if variables:
            params['variables'] = variables
        if query_time:
            params['query_time'] = query_time
            
        response = requests.get(
            f'{self.base_url}/api/analogs',
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def analyze_pattern_reliability(self, analogs_response: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the reliability of analog patterns."""
        top_analogs = analogs_response['top_analogs']
        ensemble_stats = analogs_response['ensemble_stats']
        
        # Calculate reliability metrics
        avg_similarity = sum(a['similarity_score'] for a in top_analogs) / len(top_analogs)
        min_similarity = min(a['similarity_score'] for a in top_analogs)
        
        # Assess uncertainty from ensemble statistics
        temp_uncertainty = ensemble_stats['outcome_uncertainty'].get('t2m', 0)
        pressure_uncertainty = ensemble_stats['outcome_uncertainty'].get('msl', 0)
        
        reliability = "high" if avg_similarity > 0.8 and temp_uncertainty < 3.0 else \
                     "medium" if avg_similarity > 0.6 and temp_uncertainty < 5.0 else "low"
        
        return {
            "reliability_class": reliability,
            "average_similarity": avg_similarity,
            "minimum_similarity": min_similarity,
            "temperature_uncertainty_celsius": temp_uncertainty,
            "pressure_uncertainty_hpa": pressure_uncertainty / 100,  # Convert Pa to hPa
            "pattern_count": len(top_analogs),
            "common_events": ensemble_stats['common_events']
        }

# Usage example
client = AnalogSearchClient('http://localhost/api', 'your-token-here')

# Search for winter storm analogs
analogs = client.search_analogs(
    horizon='48h',
    variables='t2m,msl,cape,tp6h',
    k=15,
    query_time='2024-01-15T12:00:00Z'
)

print(f"Found {len(analogs['top_analogs'])} similar patterns")
print(f"Best match from: {analogs['top_analogs'][0]['date']}")
print(f"Similarity score: {analogs['top_analogs'][0]['similarity_score']:.3f}")

# Analyze reliability
reliability = client.analyze_pattern_reliability(analogs)
print(f"Pattern reliability: {reliability['reliability_class']}")
print(f"Average similarity: {reliability['average_similarity']:.3f}")
```

#### JavaScript Integration
```javascript
class AnalogSearchAPI {
    constructor(baseUrl, apiToken) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.headers = {
            'Authorization': `Bearer ${apiToken}`,
            'Accept': 'application/json'
        };
    }

    async searchAnalogs({horizon = '24h', variables = null, k = 10, queryTime = null} = {}) {
        const params = new URLSearchParams({horizon, k});
        if (variables) params.append('variables', variables);
        if (queryTime) params.append('query_time', queryTime);

        const response = await fetch(`${this.baseUrl}/api/analogs?${params}`, {
            headers: this.headers
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(`Analog search failed: ${error.error.message}`);
        }

        return response.json();
    }

    generatePatternSummary(analogsResponse) {
        const {top_analogs, ensemble_stats} = analogsResponse;
        
        const avgSimilarity = top_analogs.reduce((sum, a) => sum + a.similarity_score, 0) / top_analogs.length;
        const bestMatch = top_analogs[0];
        
        return {
            summary: `Found ${top_analogs.length} similar patterns with average similarity of ${(avgSimilarity * 100).toFixed(1)}%`,
            bestMatch: {
                date: new Date(bestMatch.date).toLocaleDateString(),
                similarity: (bestMatch.similarity_score * 100).toFixed(1),
                narrative: bestMatch.outcome_narrative
            },
            reliability: avgSimilarity > 0.8 ? 'High' : avgSimilarity > 0.6 ? 'Medium' : 'Low',
            commonEvents: ensemble_stats.common_events,
            uncertainty: {
                temperature: ensemble_stats.outcome_uncertainty.t2m?.toFixed(1) + '°C' || 'N/A',
                pressure: ensemble_stats.outcome_uncertainty.msl ? 
                    (ensemble_stats.outcome_uncertainty.msl / 100).toFixed(1) + ' hPa' : 'N/A'
            }
        };
    }
}

// Usage example
const analogAPI = new AnalogSearchAPI('http://localhost/api', 'your-token-here');

async function analyzeCurrentConditions() {
    try {
        const analogs = await analogAPI.searchAnalogs({
            horizon: '24h',
            variables: 't2m,msl,cape',
            k: 10
        });

        const summary = analogAPI.generatePatternSummary(analogs);
        console.log('Pattern Analysis:', summary);

        // Display results in UI
        document.getElementById('similarity-score').textContent = summary.bestMatch.similarity + '%';
        document.getElementById('pattern-narrative').textContent = summary.bestMatch.narrative;
        document.getElementById('reliability-level').textContent = summary.reliability;
        
    } catch (error) {
        console.error('Analog search failed:', error.message);
    }
}
```

**Best Practices:**

1. **Optimal Parameter Selection**:
   - Use `k=10-20` for general analysis, `k=5` for quick previews
   - Match horizon to your forecast needs (6h for nowcasting, 48h for extended forecasting)
   - Include relevant variables for your use case (add CAPE for convection analysis)

2. **Performance Optimization**:
   - Cache results for 10-15 minutes to reduce API load
   - Use smaller k values for real-time applications
   - Batch requests when analyzing multiple time periods

3. **Reliability Assessment**:
   - High similarity scores (>0.8) indicate strong pattern matches
   - Large uncertainty values suggest pattern diversity
   - Common events help identify recurring meteorological phenomena

4. **Error Handling**:
   - Implement retry logic for 503 service unavailable errors
   - Validate parameters before making requests
   - Handle correlation IDs for debugging and support

**Monitoring Integration:**

The analog search service integrates with the system's monitoring infrastructure:
- **Prometheus Metrics**: Search performance and success rates via `/metrics`
- **Health Checks**: FAISS-specific health monitoring via `/health/faiss`
- **Correlation IDs**: Every request includes tracking for debugging
- **Performance Alerts**: Automatic alerts for slow searches or failures

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