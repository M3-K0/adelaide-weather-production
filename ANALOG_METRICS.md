# Analog Search Prometheus Metrics (OBS1)

This document describes the Prometheus metrics implementation for analog search operations in the Adelaide Weather Forecasting System.

## Implemented Metrics

### 1. `analog_real_total` (Counter)
- **Description**: Total number of successful real FAISS analog searches
- **Type**: Counter
- **Labels**: None
- **Usage**: Tracks when the system successfully uses real FAISS indices for analog search
- **Incremented when**: Real FAISS search completes successfully

### 2. `analog_fallback_total` (Counter)
- **Description**: Total number of fallback analog searches used
- **Type**: Counter
- **Labels**: None
- **Usage**: Tracks when the system falls back to mock/fallback searches due to FAISS unavailability
- **Incremented when**: 
  - FAISS indices are unavailable
  - Real FAISS search fails
  - Service is in degraded mode
  - Search validation fails

### 3. `analog_search_seconds` (Histogram)
- **Description**: Analog search latency distribution
- **Type**: Histogram
- **Labels**: 
  - `horizon`: Forecast horizon (6h, 12h, 24h, 48h)
  - `k`: Number of analogs requested (as string)
- **Buckets**: [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, +Inf] seconds
- **Usage**: Measures search latency for both real FAISS and fallback searches
- **Recorded when**: Any analog search completes (successful or fallback)

### 4. `analog_results_count` (Gauge)
- **Description**: Number of analogs returned per horizon
- **Type**: Gauge
- **Labels**: 
  - `horizon`: Forecast horizon (6h, 12h, 24h, 48h)
- **Usage**: Tracks the actual number of analog results returned for each horizon
- **Updated when**: Search completes with results (real or fallback)

## Implementation Details

### Metrics Module
- **File**: `api/analog_metrics.py`
- **Purpose**: Centralized metrics definitions with safe metric creation
- **Features**: 
  - Prevents duplicate metric registration errors
  - Uses default Prometheus registry for automatic export

### Service Instrumentation
- **File**: `api/services/analog_search.py`
- **Instrumentation points**:
  - Real FAISS search completion
  - Fallback search usage
  - Degraded mode operations
  - Error handling paths

### Availability
- **Graceful degradation**: Metrics collection is optional
- **Flag**: `METRICS_AVAILABLE` indicates if Prometheus metrics are enabled
- **Fallback**: Service operates normally even if metrics are unavailable

## Monitoring Queries

### Key Performance Indicators

1. **Search Success Rate**:
   ```promql
   rate(analog_real_total[5m]) / (rate(analog_real_total[5m]) + rate(analog_fallback_total[5m]))
   ```

2. **Average Search Latency by Horizon**:
   ```promql
   rate(analog_search_seconds_sum[5m]) / rate(analog_search_seconds_count[5m])
   ```

3. **P95 Search Latency**:
   ```promql
   histogram_quantile(0.95, rate(analog_search_seconds_bucket[5m]))
   ```

4. **Fallback Rate**:
   ```promql
   rate(analog_fallback_total[5m])
   ```

5. **Results Distribution by Horizon**:
   ```promql
   analog_results_count
   ```

### Alerting Rules

1. **High Fallback Rate**:
   ```yaml
   - alert: HighAnalogFallbackRate
     expr: rate(analog_fallback_total[5m]) / (rate(analog_real_total[5m]) + rate(analog_fallback_total[5m])) > 0.5
     for: 2m
     labels:
       severity: warning
     annotations:
       summary: High analog search fallback rate detected
   ```

2. **Slow Search Performance**:
   ```yaml
   - alert: SlowAnalogSearch
     expr: histogram_quantile(0.95, rate(analog_search_seconds_bucket[5m])) > 1.0
     for: 5m
     labels:
       severity: warning
     annotations:
       summary: Analog search P95 latency exceeding 1 second
   ```

## Testing

Use the provided test script to verify metrics functionality:

```bash
python3 test_analog_metrics.py
```

The test script validates:
- Counter increments
- Histogram observations with labels
- Gauge value updates
- Prometheus output format

## Integration

The metrics are automatically exported via the existing `/metrics` endpoint and included in the unified Prometheus registry alongside other system metrics including:
- API request metrics
- FAISS health metrics
- Performance middleware metrics
- Configuration drift metrics

## Labels and Cardinality

- **horizon labels**: 4 values (6h, 12h, 24h, 48h)
- **k labels**: Variable, typically 10-200 range
- **Estimated cardinality**: Low to moderate (< 1000 series per metric)
- **Retention**: Follows standard Prometheus retention policies

## Performance Impact

- **Instrumentation overhead**: Minimal (<1ms per operation)
- **Memory usage**: Low (standard Prometheus metric overhead)
- **Network impact**: Included in existing metrics scraping