# FAISS Health Endpoints - API Reference

## Overview

The Adelaide Weather Forecasting System provides comprehensive FAISS health monitoring through dedicated API endpoints that track index readiness, search performance, and system degradation.

## Endpoints

### `/health/faiss`

**Dedicated FAISS Health Monitoring Endpoint**

**Method:** `GET`  
**Rate Limit:** 30 requests/minute  
**Authentication:** Required (API token)

**Description:**  
Returns comprehensive FAISS system health including index readiness for all horizons, last successful search timestamps, fallback counters, and performance metrics.

**Response Format:**

```json
{
  "faiss_status": "healthy",
  "message": "FAISS system operational",
  "timestamp": "2024-11-13T10:43:00.000Z",
  "check_duration_ms": 45.2,
  
  "index_readiness": {
    "6h": {
      "flatip_ready": true,
      "ivfpq_ready": true,
      "last_successful_search": "2024-11-13T10:42:00.000Z",
      "last_search_age_seconds": 60,
      "search_samples": 125
    },
    "12h": { "..." },
    "24h": { "..." },
    "48h": { "..." }
  },
  
  "index_validation": {
    "total_indices_available": 8,
    "expected_indices": 8,
    "indices_metadata": {
      "6h_flatip": {
        "horizon": "6h",
        "index_type": "flatip", 
        "ntotal": 6574,
        "d": 256,
        "file_size_mb": 6.4,
        "last_updated": "2024-11-13T10:00:00.000Z"
      }
    },
    "dimension_validation": {
      "6h": {
        "flatip": {
          "dimension": 256,
          "expected_dimension": 768,
          "dimension_valid": true,
          "ntotal": 6574,
          "ntotal_valid": true
        }
      }
    }
  },
  
  "performance_metrics": {
    "query_performance": {
      "total_queries": 1250,
      "active_queries": 2,
      "error_rate": 0.001,
      "avg_latency_ms": 45.2
    },
    "latency_by_horizon": {
      "6h": {"p50_ms": 32.1, "p95_ms": 78.5, "sample_count": 312}
    },
    "throughput_qps": 2.5
  },
  
  "degraded_mode": {
    "active": false,
    "fallback_counters": {
      "total_fallbacks": 12,
      "fallback_by_horizon": {"6h": 3, "12h": 2, "24h": 4, "48h": 3},
      "fallback_by_reason": {
        "index_unavailable": 8,
        "memory_pressure": 2,
        "timeout": 2
      },
      "last_fallback_time": "2024-11-13T09:15:00.000Z",
      "degraded_mode": {
        "active": false,
        "since": null,
        "reasons": []
      }
    }
  },
  
  "system_resources": {
    "memory_usage_mb": 125.4,
    "cpu_percent": 15.2
  },
  
  "monitoring": {
    "active": true,
    "uptime_seconds": 7200,
    "last_health_update": "2024-11-13T10:43:00.000Z"
  }
}
```

### `/health/detailed` (Enhanced)

**Comprehensive System Health with FAISS Integration**

**Method:** `GET`  
**Rate Limit:** 20 requests/minute  
**Authentication:** Required (API token)

**Description:**  
Returns comprehensive system health including enhanced FAISS metrics alongside other system components.

**FAISS-related fields added:**
- `faiss_indices` - Index metadata and status
- `faiss_performance` - Performance metrics
- `degraded_mode` - Degradation status

## Status Codes

| HTTP Code | FAISS Status | Description |
|-----------|--------------|-------------|
| `200` | `healthy` | All FAISS indices operational, normal performance |
| `200` | `degraded` | Some indices missing or performance degraded |
| `503` | `unhealthy` | Critical FAISS failure, service unavailable |
| `500` | `error` | Health check system failure |

## Health Status Levels

### `healthy`
- All 8 indices available (6h, 12h, 24h, 48h × flatip, ivfpq)
- Error rate < 5%
- Average latency < 100ms
- No recent fallbacks

### `degraded`  
- Some indices missing (but > 50% available)
- Error rate 5-10%
- Average latency 100-200ms
- Recent fallback activity

### `unhealthy`
- Most/all indices unavailable
- Error rate > 10%
- Critical system failures
- Service cannot operate

## Field Descriptions

### Index Readiness
- **`flatip_ready`** - IndexFlatIP (exact search) available
- **`ivfpq_ready`** - IndexIVFPQ (approximate search) available  
- **`last_successful_search`** - ISO timestamp of last successful search
- **`last_search_age_seconds`** - Seconds since last successful search
- **`search_samples`** - Number of search samples collected

### Index Validation
- **`ntotal`** - Number of vectors in index
- **`d`** - Vector dimension (should be 256 for this system)
- **`dimension_valid`** - Whether dimension matches expected value
- **`ntotal_valid`** - Whether vector count > 0

### Performance Metrics
- **`total_queries`** - Total FAISS searches performed
- **`active_queries`** - Currently executing searches
- **`error_rate`** - Fraction of failed searches (0.0-1.0)
- **`avg_latency_ms`** - Mean search latency in milliseconds
- **`p50_ms`/`p95_ms`** - Latency percentiles
- **`throughput_qps`** - Queries per second

### Fallback Tracking
- **`total_fallbacks`** - Total fallback events
- **`fallback_by_horizon`** - Per-horizon fallback counts
- **`fallback_by_reason`** - Fallback events grouped by cause
- **`last_fallback_time`** - Timestamp of most recent fallback
- **`degraded_mode.active`** - Whether system is in degraded mode
- **`degraded_mode.since`** - When degraded mode started
- **`degraded_mode.reasons`** - List of degradation causes

## Usage Examples

### Check Overall FAISS Health
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.adelaide-weather.com/health/faiss
```

### Monitor Specific Horizon
```python
import requests

response = requests.get(
    "https://api.adelaide-weather.com/health/faiss",
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)

faiss_health = response.json()
h24_status = faiss_health["index_readiness"]["24h"]

if h24_status["flatip_ready"] and h24_status["ivfpq_ready"]:
    print("24h forecasting fully operational")
else:
    print("24h forecasting degraded")
```

### Check for Degraded Mode
```python
degraded = faiss_health["degraded_mode"]
if degraded["active"]:
    print(f"FAISS in degraded mode: {degraded['fallback_counters']['degraded_mode']['reasons']}")
    print(f"Total fallbacks: {degraded['fallback_counters']['total_fallbacks']}")
```

### Performance Monitoring
```python
perf = faiss_health["performance_metrics"]
latency_24h = perf["latency_by_horizon"]["24h"]

print(f"24h search performance:")
print(f"  - p50: {latency_24h['p50_ms']}ms")
print(f"  - p95: {latency_24h['p95_ms']}ms") 
print(f"  - samples: {latency_24h['sample_count']}")
```

## Monitoring Integration

### Prometheus Metrics
The FAISS health monitoring integrates with Prometheus metrics:

- `faiss_query_duration_seconds` - Query latency histogram
- `faiss_search_duration_p50_seconds` - Per-horizon p50 latency
- `faiss_search_duration_p95_seconds` - Per-horizon p95 latency
- `faiss_queries_total` - Total query counter
- `faiss_search_errors_total` - Error counter by horizon
- `faiss_degraded_mode_total` - Degraded mode events

### Alerting Thresholds

**Critical Alerts (immediate attention):**
- `faiss_status == "unhealthy"`
- `error_rate > 0.1` (>10% errors)
- `degraded_mode.active == true` for >15 minutes

**Warning Alerts (monitoring required):**
- `error_rate > 0.05` (>5% errors) 
- `p95_latency > 200ms` for any horizon
- `last_search_age_seconds > 300` (>5 minutes since last search)
- Missing indices (`total_indices_available < 8`)

### Health Check Integration
For Kubernetes or container orchestration:

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /health/faiss
    port: 8000
  periodSeconds: 10
  successThreshold: 1
  failureThreshold: 3
```

## Error Handling

The endpoints handle various error conditions gracefully:

- **FAISS library unavailable** - Returns degraded status with explanation
- **Index files missing** - Detailed information about which indices are unavailable  
- **Memory pressure** - Automatic fallback counting and degraded mode detection
- **Network issues** - Proper HTTP status codes and error messages

All errors are logged with appropriate detail for operational debugging.