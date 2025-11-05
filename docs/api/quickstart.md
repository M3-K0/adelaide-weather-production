# Quick Start Guide

Get up and running with the Adelaide Weather Forecasting API in minutes. This guide will walk you through making your first API call and understanding the response format.

## 🚀 Getting Started

### Step 1: Get Your API Token

Contact your system administrator to obtain an API token. You'll need this for all forecast requests.

### Step 2: Test the API

First, verify the API is responding:

```bash
curl -X GET "https://api.adelaideweather.example.com/health"
```

You should see a response like:
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
    "uptime_seconds": 3600.5
}
```

### Step 3: Make Your First Forecast Request

```bash
curl -X GET "https://api.adelaideweather.example.com/forecast?horizon=24h&vars=t2m,u10,v10,msl" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Accept: application/json"
```

## 📊 Understanding the Response

The API returns comprehensive forecast data with uncertainty quantification:

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
        },
        "u10": {
            "value": 3.2,
            "p05": 1.8,
            "p95": 5.1,
            "confidence": 0.75,
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
    "narrative": "Forecast for 24h: warm conditions with temperature around 25.3°C, light winds at 3.7 m/s from 209°, normal pressure system (1015 hPa).",
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
        "outcome_description": "Strong pattern match with typical seasonal conditions",
        "confidence_explanation": "Based on 45 historical analog patterns"
    },
    "confidence_explanation": "High confidence (82.0%) with 45 strong analog matches",
    "latency_ms": 127.5
}
```

### Key Response Fields

- **`variables`**: Individual forecasts for each requested weather variable
- **`wind10m`**: Combined wind speed and direction derived from u10/v10 components  
- **`narrative`**: Human-readable forecast summary
- **`risk_assessment`**: Weather hazard risk levels
- **`analogs_summary`**: Information about similar historical patterns
- **`confidence_explanation`**: Overall forecast confidence reasoning

## 🌡️ Available Variables

| Variable | Description | Unit | Typical Range |
|----------|-------------|------|---------------|
| `t2m` | 2-meter temperature | °C | -10 to 45 |
| `u10` | 10m U wind component | m/s | -30 to 30 |
| `v10` | 10m V wind component | m/s | -30 to 30 |
| `msl` | Mean sea level pressure | hPa | 980 to 1040 |
| `r850` | 850hPa relative humidity | % | 0 to 100 |
| `tp6h` | 6-hour precipitation | mm | 0 to 50 |
| `cape` | Convective potential energy | J/kg | 0 to 4000 |
| `t850` | 850hPa temperature | °C | -20 to 35 |
| `z500` | 500hPa geopotential height | m | 5000 to 6000 |

## ⏰ Forecast Horizons

| Horizon | Description | Update Frequency | Typical Use Case |
|---------|-------------|------------------|------------------|
| `6h` | Short-term | Every hour | Immediate planning |
| `12h` | Half-day | Every 3 hours | Daily operations |
| `24h` | One day | Every 6 hours | Next-day planning |
| `48h` | Two days | Every 12 hours | Extended planning |

## 💻 Code Examples

### Python Client

```python
import requests
import os
from datetime import datetime

class AdelaideWeatherClient:
    def __init__(self, api_token, base_url="https://api.adelaideweather.example.com"):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Accept': 'application/json',
            'User-Agent': 'Adelaide-Weather-Client/1.0.0'
        }
    
    def get_forecast(self, horizon="24h", variables=None):
        """Get weather forecast with uncertainty bounds."""
        if variables is None:
            variables = ["t2m", "u10", "v10", "msl"]
        
        params = {
            'horizon': horizon,
            'vars': ','.join(variables)
        }
        
        response = requests.get(
            f"{self.base_url}/forecast",
            params=params,
            headers=self.headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            raise Exception("Rate limit exceeded. Please wait before retrying.")
        elif response.status_code == 401:
            raise Exception("Authentication failed. Check your API token.")
        else:
            response.raise_for_status()
    
    def get_health(self):
        """Check API health status."""
        response = requests.get(f"{self.base_url}/health", timeout=5)
        return response.json()
    
    def print_forecast_summary(self, forecast):
        """Print a formatted forecast summary."""
        print(f"\n=== Adelaide Weather Forecast ({forecast['horizon']}) ===")
        print(f"Generated at: {forecast['generated_at']}")
        print(f"Narrative: {forecast['narrative']}")
        
        print(f"\n--- Temperature ---")
        temp = forecast['variables']['t2m']
        print(f"Temperature: {temp['value']:.1f}°C")
        print(f"Range: {temp['p05']:.1f}°C to {temp['p95']:.1f}°C")
        print(f"Confidence: {temp['confidence']:.1%}")
        
        if forecast['wind10m']['available']:
            wind = forecast['wind10m']
            print(f"\n--- Wind ---")
            print(f"Speed: {wind['speed']:.1f} m/s")
            print(f"Direction: {wind['direction']:.0f}°")
        
        print(f"\n--- Risk Assessment ---")
        risks = forecast['risk_assessment']
        for risk_type, level in risks.items():
            print(f"{risk_type.replace('_', ' ').title()}: {level}")
        
        print(f"\nResponse time: {forecast['latency_ms']:.1f}ms")

# Usage example
if __name__ == "__main__":
    # Get API token from environment
    api_token = os.getenv('WEATHER_API_TOKEN')
    if not api_token:
        print("Please set WEATHER_API_TOKEN environment variable")
        exit(1)
    
    # Create client
    client = AdelaideWeatherClient(api_token)
    
    try:
        # Check health
        health = client.get_health()
        if not health['ready']:
            print("⚠️  API is not ready")
            exit(1)
        
        # Get 24-hour forecast
        forecast = client.get_forecast(
            horizon="24h",
            variables=["t2m", "u10", "v10", "msl", "cape"]
        )
        
        # Print summary
        client.print_forecast_summary(forecast)
        
    except Exception as e:
        print(f"Error: {e}")
```

### JavaScript/Node.js Client

```javascript
const fetch = require('node-fetch');

class AdelaideWeatherClient {
    constructor(apiToken, baseUrl = 'https://api.adelaideweather.example.com') {
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${apiToken}`,
            'Accept': 'application/json',
            'User-Agent': 'Adelaide-Weather-Client/1.0.0'
        };
    }
    
    async getForecast(horizon = '24h', variables = ['t2m', 'u10', 'v10', 'msl']) {
        const params = new URLSearchParams({
            horizon,
            vars: variables.join(',')
        });
        
        const response = await fetch(`${this.baseUrl}/forecast?${params}`, {
            headers: this.headers
        });
        
        if (!response.ok) {
            if (response.status === 429) {
                throw new Error('Rate limit exceeded');
            } else if (response.status === 401) {
                throw new Error('Authentication failed');
            }
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    async getHealth() {
        const response = await fetch(`${this.baseUrl}/health`);
        return await response.json();
    }
    
    printForecastSummary(forecast) {
        console.log(`\n=== Adelaide Weather Forecast (${forecast.horizon}) ===`);
        console.log(`Generated at: ${forecast.generated_at}`);
        console.log(`Narrative: ${forecast.narrative}`);
        
        const temp = forecast.variables.t2m;
        console.log(`\n--- Temperature ---`);
        console.log(`Temperature: ${temp.value.toFixed(1)}°C`);
        console.log(`Range: ${temp.p05.toFixed(1)}°C to ${temp.p95.toFixed(1)}°C`);
        console.log(`Confidence: ${(temp.confidence * 100).toFixed(1)}%`);
        
        if (forecast.wind10m?.available) {
            const wind = forecast.wind10m;
            console.log(`\n--- Wind ---`);
            console.log(`Speed: ${wind.speed.toFixed(1)} m/s`);
            console.log(`Direction: ${wind.direction.toFixed(0)}°`);
        }
        
        console.log(`\n--- Risk Assessment ---`);
        Object.entries(forecast.risk_assessment).forEach(([type, level]) => {
            const readable = type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
            console.log(`${readable}: ${level}`);
        });
        
        console.log(`\nResponse time: ${forecast.latency_ms.toFixed(1)}ms`);
    }
}

// Usage example
async function main() {
    const apiToken = process.env.WEATHER_API_TOKEN;
    if (!apiToken) {
        console.error('Please set WEATHER_API_TOKEN environment variable');
        process.exit(1);
    }
    
    const client = new AdelaideWeatherClient(apiToken);
    
    try {
        // Check health
        const health = await client.getHealth();
        if (!health.ready) {
            console.error('⚠️  API is not ready');
            process.exit(1);
        }
        
        // Get forecast
        const forecast = await client.getForecast('24h', ['t2m', 'u10', 'v10', 'msl', 'cape']);
        
        // Print summary
        client.printForecastSummary(forecast);
        
    } catch (error) {
        console.error('Error:', error.message);
    }
}

if (require.main === module) {
    main();
}

module.exports = AdelaideWeatherClient;
```

### curl Examples

```bash
#!/bin/bash

# Set your API token
API_TOKEN="YOUR_TOKEN_HERE"
BASE_URL="https://api.adelaideweather.example.com"

# Function to make authenticated requests
api_request() {
    curl -s -X GET "$BASE_URL$1" \
        -H "Authorization: Bearer $API_TOKEN" \
        -H "Accept: application/json" \
        -H "User-Agent: curl-client/1.0.0"
}

echo "=== Checking API Health ==="
api_request "/health" | jq '.ready'

echo -e "\n=== Getting 24h Forecast ==="
api_request "/forecast?horizon=24h&vars=t2m,u10,v10,msl" | jq '{
    horizon,
    temperature: .variables.t2m.value,
    wind_speed: .wind10m.speed,
    narrative,
    confidence: .confidence_explanation
}'

echo -e "\n=== Getting Extended Forecast with Weather Variables ==="
api_request "/forecast?horizon=48h&vars=t2m,u10,v10,msl,cape,tp6h" | jq '{
    horizon,
    temperature: .variables.t2m.value,
    precipitation: .variables.tp6h.value,
    cape: .variables.cape.value,
    risk_assessment
}'

echo -e "\n=== Getting Quick Temperature Check ==="
api_request "/forecast?horizon=6h&vars=t2m" | jq '{
    temperature: .variables.t2m.value,
    range: {
        min: .variables.t2m.p05,
        max: .variables.t2m.p95
    },
    confidence: .variables.t2m.confidence
}'
```

## 🔍 Testing with the Interactive Documentation

1. **Visit the API Portal**: Open [index.html](./index.html) in your browser
2. **Authorize**: Click "Authorize" and enter your API token
3. **Try Endpoints**: Use "Try it out" on any endpoint
4. **Experiment**: Modify parameters to see how responses change

## 📈 Common Use Cases

### 1. Current Conditions Check

```bash
# Quick temperature and wind check
curl -X GET "$BASE_URL/forecast?horizon=6h&vars=t2m,u10,v10" \
  -H "Authorization: Bearer $API_TOKEN"
```

### 2. Daily Planning

```bash
# Get full day forecast with precipitation
curl -X GET "$BASE_URL/forecast?horizon=24h&vars=t2m,u10,v10,msl,tp6h" \
  -H "Authorization: Bearer $API_TOKEN"
```

### 3. Severe Weather Monitoring

```bash
# Monitor convective potential and wind
curl -X GET "$BASE_URL/forecast?horizon=12h&vars=cape,u10,v10,t2m" \
  -H "Authorization: Bearer $API_TOKEN"
```

### 4. Extended Planning

```bash
# Two-day outlook
curl -X GET "$BASE_URL/forecast?horizon=48h&vars=t2m,msl,tp6h" \
  -H "Authorization: Bearer $API_TOKEN"
```

## ⚠️ Error Handling

### Common Errors and Solutions

**401 Unauthorized**
```json
{
    "error": {
        "code": 401,
        "message": "Invalid authentication token"
    }
}
```
*Solution*: Check your API token and ensure it's correctly formatted.

**400 Bad Request**
```json
{
    "error": {
        "code": 400,
        "message": "Invalid horizon. Must be one of: 6h, 12h, 24h, 48h"
    }
}
```
*Solution*: Use only valid horizon values.

**429 Too Many Requests**
```json
{
    "error": {
        "code": 429,
        "message": "Rate limit exceeded. Please try again later."
    }
}
```
*Solution*: Wait before retrying. Check rate limits in the [Rate Limiting Guide](./rate-limiting.md).

**503 Service Unavailable**
```json
{
    "error": {
        "code": 503,
        "message": "Forecasting system not ready"
    }
}
```
*Solution*: The system is starting up or experiencing issues. Check the health endpoint.

## 🚦 Rate Limits

- **Forecast endpoint**: 60 requests/minute
- **Health endpoint**: 30 requests/minute (no auth required)
- **Metrics endpoint**: 10 requests/minute (requires auth)

## 📝 Next Steps

1. **Explore more endpoints**: Try the `/analogs` endpoint for historical pattern analysis
2. **Read detailed guides**: Check out the [Authentication Guide](./authentication.md)
3. **Review error codes**: See the [Error Codes Reference](./error-codes.md)
4. **Monitor usage**: Use the `/metrics` endpoint for monitoring
5. **Integrate monitoring**: Set up health checks in your applications

## 🆘 Getting Help

- **Documentation**: Browse the full [API documentation](./index.html)
- **Examples**: Check the [examples directory](./examples/) for more code samples
- **Support**: Contact support@adelaideweather.example.com
- **Issues**: Include correlation IDs from error responses for faster debugging

## 🔗 Useful Links

- [Interactive API Documentation](./index.html)
- [Authentication Guide](./authentication.md)
- [Rate Limiting Policy](./rate-limiting.md)
- [Error Codes Reference](./error-codes.md)
- [Python Client Example](./examples/python-client.py)
- [JavaScript Client Example](./examples/javascript-client.js)