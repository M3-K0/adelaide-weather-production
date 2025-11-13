# Adelaide Weather API Documentation - Transparency & FAISS Features

## Overview

Comprehensive API documentation has been created for the new analog search endpoints and transparency features. The documentation provides complete visibility into FAISS vs fallback data sources and detailed performance metrics.

## Documentation Files Updated

### Primary Documentation
- **`/docs/api/openapi.yaml`** - Complete OpenAPI 3.0 specification with new endpoints and transparency features

## New Features Documented

### 1. Enhanced `/api/analogs` Endpoint

#### Key Features
- **Comprehensive analog search** with historical weather pattern matching
- **Full transparency** about data sources (FAISS vs fallback)
- **Rich metadata** including search performance and quality metrics
- **Environment configuration** via `ALLOW_ANALOG_FALLBACK`

#### Parameters
- `horizon` - Forecast time horizon (6h, 12h, 24h, 48h)
- `variables` - Weather variables for search (default: t2m,u10,v10,msl)
- `k` - Number of analog patterns to return (1-200)
- `query_time` - ISO 8601 datetime for analysis

#### Response Transparency Fields
- `data_source` - "faiss" or "fallback" indicator
- `search_metadata` - Comprehensive search performance data
  - Search method and execution time
  - Performance metrics (latency percentiles)
  - Quality validation checks
  - Total patterns searched

### 2. Enhanced Health Monitoring

#### `/health/faiss` Endpoint
- **Real-time FAISS performance monitoring**
- **Per-index health status** and metrics
- **Performance tracking** with percentile latencies
- **Health scoring** (0-100) with diagnostic factors
- **Availability monitoring** and uptime tracking

#### Enhanced `/health/detailed` Endpoint
- **Analog search transparency** section
- **FAISS infrastructure status** with per-horizon metrics
- **Environment configuration** including fallback settings
- **Data source distribution** tracking (FAISS vs fallback percentages)
- **Quality metrics** and performance indicators

### 3. Transparency Schema Updates

#### AnalogExplorerData Schema
- Added required `data_source` and `search_metadata` fields
- Comprehensive search metadata structure
- Performance metrics and validation checks
- Request context and environment configuration

## Environment Configuration

### ALLOW_ANALOG_FALLBACK Environment Variable
- **Purpose**: Controls fallback behavior when FAISS unavailable
- **Values**: "true" (fallback enabled) or "false" (503 errors when FAISS down)
- **Documentation**: Fully documented in health endpoints and error scenarios

## API Usage Examples

### Curl Examples
```bash
# Basic analog search
curl -X GET "https://api.adelaideweather.example.com/api/analogs?horizon=24h&k=10" \
  -H "Authorization: Bearer YOUR_TOKEN"

# FAISS health monitoring
curl -X GET "https://api.adelaideweather.example.com/health/faiss" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Comprehensive health with transparency
curl -X GET "https://api.adelaideweather.example.com/health/detailed"
```

### Python Integration
- **Full transparency checking** with data source detection
- **Quality assessment utilities** for analog data validation
- **Health monitoring** with FAISS status tracking
- **Performance metrics extraction** and analysis

### JavaScript Integration
- **Modern fetch API** implementations with error handling
- **Transparency feature demonstration** with real-time monitoring
- **Quality assessment functions** for data validation
- **Comprehensive health checking** with metric extraction

## Response Examples

### FAISS Search Response
```json
{
  "data_source": "faiss",
  "search_metadata": {
    "search_method": "faiss",
    "faiss_search_successful": true,
    "search_time_ms": 15.7,
    "total_candidates": 50000,
    "performance_metrics": {
      "current_latency_ms": 15.7,
      "p95_latency_ms": 45.1
    }
  }
}
```

### Fallback Response
```json
{
  "data_source": "fallback",
  "search_metadata": {
    "search_method": "fallback_mock",
    "faiss_search_successful": false,
    "fallback_reason": "FAISS indices unavailable",
    "search_time_ms": 8.3
  }
}
```

## Error Scenarios Documented

### HTTP Status Codes
- **400**: Invalid request parameters with detailed examples
- **401**: Authentication required
- **500**: Internal server errors
- **503**: Service unavailable (FAISS down and fallback disabled)

### Transparency in Error Responses
- Clear indication when FAISS is unavailable
- Fallback behavior explanation
- Environment configuration impact

## Monitoring & Observability

### FAISS Health Metrics
- **Index status** per horizon with vector counts
- **Performance percentiles** (P50, P95, P99)
- **Availability tracking** with uptime percentages
- **Memory usage** and optimization status
- **Quality scoring** with diagnostic factors

### System Integration
- **Kubernetes health probes** compatibility
- **Prometheus metrics** endpoint documentation
- **Real-time monitoring** with transparency indicators

## Quality Assurance Features

### Search Validation
- **Distance monotonicity** checking
- **Similarity bounds** validation  
- **Temporal consistency** verification
- **Pattern diversity** assessment

### Performance Validation
- **Latency tracking** across all searches
- **Throughput monitoring** with QPS metrics
- **Cache performance** tracking
- **Error rate monitoring**

## Developer Experience

### Documentation Quality
- **Comprehensive parameter descriptions** with examples
- **Realistic response examples** for both FAISS and fallback scenarios  
- **Error case documentation** with troubleshooting guidance
- **Code samples** in multiple languages (curl, Python, JavaScript)

### Integration Support
- **Transparency helper functions** for quality assessment
- **Health monitoring utilities** for operational visibility
- **Performance tracking examples** for optimization
- **Configuration validation** for environment setup

## Summary

The API documentation now provides complete transparency and comprehensive monitoring capabilities for the Adelaide Weather API's analog search functionality. Users can:

1. **Understand data sources** - Clear indication of FAISS vs fallback usage
2. **Monitor performance** - Real-time metrics and health scoring
3. **Validate quality** - Comprehensive search result validation
4. **Configure behavior** - Environment-based fallback control
5. **Integrate effectively** - Rich examples and utility functions
6. **Troubleshoot issues** - Detailed error scenarios and diagnostics

The documentation enables operational teams to monitor FAISS health, developers to integrate with transparency features, and users to understand the quality and source of analog search results.