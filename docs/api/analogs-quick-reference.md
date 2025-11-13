# 🌩️ Analog Weather Patterns - Quick Reference

Fast reference for the `/api/analogs` endpoint - historical weather pattern search powered by FAISS.

## 🚀 Quick Start

```bash
# Basic search
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.adelaideweather.example.com/api/analogs?horizon=24h&k=10"
```

## 📋 Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `horizon` | `24h` | `6h`, `12h`, `24h`, `48h` | Forecast timeframe |
| `variables` | `t2m,u10,v10,msl` | See variables list | Weather variables to analyze |
| `k` | `10` | `1-200` | Number of similar patterns to return |
| `query_time` | current | ISO 8601 | Historical time to analyze |

### Variables List
- `t2m` - 2m temperature (°C)
- `u10`, `v10` - 10m wind components (m/s) 
- `msl` - Mean sea level pressure (Pa)
- `cape` - Convective energy (J/kg)
- `tp6h` - 6h precipitation (mm)
- `r850` - 850hPa humidity (%)
- `t850` - 850hPa temperature (°C)
- `z500` - 500hPa geopotential (m)

## 🎯 Common Use Cases

### Weather Pattern Recognition
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "/api/analogs?horizon=24h&variables=t2m,msl&k=5"
```

### Thunderstorm Analysis
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "/api/analogs?horizon=12h&variables=cape,t2m,r850&k=15"
```

### Wind Event Search
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "/api/analogs?horizon=6h&variables=u10,v10,msl&k=20"
```

### Historical Analysis
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "/api/analogs?query_time=2024-01-15T12:00:00Z&horizon=48h&k=10"
```

## 📊 Response Structure

```json
{
  "forecast_horizon": "24h",
  "top_analogs": [
    {
      "date": "2023-03-15T12:00:00Z",
      "similarity_score": 0.89,
      "initial_conditions": {"t2m": 22.1, "msl": 1013.4},
      "timeline": [
        {
          "hours_offset": 12,
          "values": {"t2m": 24.5},
          "events": ["Cloud cover increased"],
          "temperature_trend": "rising"
        }
      ],
      "outcome_narrative": "Pattern evolution description",
      "season_info": {"month": 3, "season": "autumn"}
    }
  ],
  "ensemble_stats": {
    "mean_outcomes": {"t2m": 23.7},
    "outcome_uncertainty": {"t2m": 2.8},
    "common_events": ["Weather pattern development"]
  }
}
```

## ⚡ Performance Tips

| Aspect | Recommendation | Reason |
|--------|----------------|---------|
| **K Value** | Use 5-10 for speed, 15-20 for analysis | Fewer patterns = faster response |
| **Variables** | 2-4 variables optimal | More variables = slower search |
| **Horizon** | Match your needs | 6h fastest, 48h slowest |
| **Caching** | Cache for 10-15 minutes | Reduce API load |

## 🔍 Interpreting Results

### Similarity Scores
- **>0.8** - Excellent pattern match (high confidence)
- **0.6-0.8** - Good pattern match (medium confidence) 
- **0.4-0.6** - Fair pattern match (low confidence)
- **<0.4** - Poor pattern match (consider different parameters)

### Uncertainty Assessment
- **Low uncertainty** (<2°C temp) = Consistent outcomes
- **Medium uncertainty** (2-5°C temp) = Variable outcomes
- **High uncertainty** (>5°C temp) = Diverse pattern evolution

## 🚨 Error Codes

| Code | Meaning | Solution |
|------|---------|----------|
| **400** | Invalid parameters | Check parameter format and ranges |
| **401** | Authentication failed | Verify API token |
| **429** | Rate limit exceeded | Wait and retry (60/min limit) |
| **503** | Service unavailable | Check `/health/faiss` endpoint |

## 🐍 Python Quick Client

```python
import requests

class QuickAnalogClient:
    def __init__(self, token, base_url="https://api.adelaideweather.example.com"):
        self.headers = {'Authorization': f'Bearer {token}'}
        self.base_url = base_url
    
    def search(self, horizon='24h', variables=None, k=10):
        params = {'horizon': horizon, 'k': k}
        if variables:
            params['variables'] = variables
        
        response = requests.get(f'{self.base_url}/api/analogs', 
                               headers=self.headers, params=params)
        return response.json()
    
    def best_match(self, **kwargs):
        result = self.search(**kwargs)
        return result['top_analogs'][0] if result['top_analogs'] else None

# Usage
client = QuickAnalogClient('your-token')
pattern = client.best_match(horizon='24h', variables='t2m,msl')
print(f"Best match: {pattern['similarity_score']:.2f} from {pattern['date']}")
```

## 🌐 JavaScript Quick Client

```javascript
class QuickAnalogAPI {
    constructor(token, baseUrl = 'https://api.adelaideweather.example.com') {
        this.headers = {'Authorization': `Bearer ${token}`};
        this.baseUrl = baseUrl;
    }
    
    async search(options = {}) {
        const {horizon = '24h', variables, k = 10} = options;
        const params = new URLSearchParams({horizon, k});
        if (variables) params.append('variables', variables);
        
        const response = await fetch(`${this.baseUrl}/api/analogs?${params}`, 
                                   {headers: this.headers});
        return response.json();
    }
    
    async bestMatch(options) {
        const result = await this.search(options);
        return result.top_analogs?.[0] || null;
    }
}

// Usage
const client = new QuickAnalogAPI('your-token');
const pattern = await client.bestMatch({horizon: '24h', variables: 't2m,msl'});
console.log(`Best match: ${pattern?.similarity_score?.toFixed(2)} from ${pattern?.date}`);
```

## 📈 Rate Limits

- **Limit**: 60 requests/minute
- **Headers**: `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- **Burst**: Short bursts allowed, sustained rates limited
- **Tip**: Check headers and implement backoff

## 🔧 Health Monitoring

```bash
# Check FAISS service health
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.adelaideweather.example.com/health/faiss"

# Expected healthy response:
{
  "status": "healthy",
  "indices": {"24h_flatip": {"status": "healthy", "vectors": 13148}},
  "performance": {"avg_search_time_ms": 145.2}
}
```

## 📚 Advanced Features

### Batch Analysis
```python
# Analyze multiple time periods
horizons = ['6h', '12h', '24h', '48h']
results = {}
for horizon in horizons:
    results[horizon] = client.search(horizon=horizon, k=5)
```

### Pattern Classification
```python
def classify_pattern(analog_result):
    top_analog = analog_result['top_analogs'][0]
    score = top_analog['similarity_score']
    
    if score > 0.8:
        return 'strong_pattern'
    elif score > 0.6:
        return 'moderate_pattern'
    else:
        return 'weak_pattern'
```

### Event Detection
```python
def detect_extreme_weather(analog_result):
    events = analog_result['ensemble_stats']['common_events']
    extreme_keywords = ['storm', 'extreme', 'severe', 'warning']
    
    return any(keyword in ' '.join(events).lower() 
              for keyword in extreme_keywords)
```

## 🎯 Next Steps

- Read [Full Integration Guide](./analogs-integration-guide.md)
- Check [API Documentation](./README.md)
- Review [Authentication Setup](./authentication.md)
- Monitor [Service Health](./quickstart.md#health-checks)

---

**Need help?** Include correlation ID from error responses when reporting issues.