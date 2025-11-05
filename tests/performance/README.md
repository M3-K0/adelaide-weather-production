# Adelaide Weather Forecasting System - Performance Test Suite

A comprehensive performance testing framework designed to ensure optimal performance under all operational conditions with automated quality gates for production deployment.

## 🎯 Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| **API Response Time (P95)** | < 500ms | Artillery.js load testing |
| **Frontend FCP** | < 1.5s | Lighthouse CI audits |
| **Frontend LCP** | < 2.5s | Lighthouse CI audits |
| **Frontend FID** | < 100ms | Real user monitoring |
| **Frontend CLS** | < 0.1 | Lighthouse CI audits |
| **Frontend TTI** | < 3.5s | Lighthouse CI audits |
| **Database Queries (P95)** | < 200ms | Embedded monitoring |
| **FAISS Search (P95)** | < 1ms | Similarity search timing |
| **Memory Usage** | < 1GB heap | Process monitoring |
| **Error Rate** | < 1% | Request tracking |
| **Cache Hit Rate** | > 60% | Performance endpoint |

## 🏗️ Test Suite Architecture

```
tests/performance/
├── lighthouse.config.js          # Lighthouse CI configuration
├── load-tests/
│   ├── api-load-test.yml         # Artillery.js API load testing
│   └── frontend-load-test.js     # Browser-based frontend testing
├── scripts/
│   ├── performance-benchmarks.js # Comprehensive benchmarking
│   ├── memory-leak-detection.js  # Long-running memory monitoring
│   └── health-check.js           # System readiness validation
├── utils/
│   ├── performance-helpers.ts    # Utility functions and classes
│   └── performance-processor.js  # Artillery custom processor
├── reports/
│   ├── performance-baseline.json # Performance baseline data
│   └── performance-test-plan.md  # Detailed test documentation
└── package.json                  # Dependencies and scripts
```

## 🚀 Quick Start

### Prerequisites

- Node.js 18.17.0+
- Docker and Docker Compose
- Services running (API on port 8000, Frontend on port 3000)

### Installation

```bash
# Install dependencies
cd tests/performance
npm install

# Install Playwright browser
npx playwright install chromium

# Install global tools
npm install -g artillery @lhci/cli
```

### Basic Usage

```bash
# 1. Health check (verify services are ready)
npm run health-check

# 2. Quick performance validation
npm run test:quick

# 3. Comprehensive performance testing
npm run test:full

# 4. Generate performance report
npm run report
```

## 📊 Test Types

### 1. Performance Benchmarks
Establishes baseline performance metrics across all system components.

```bash
npm run test:benchmarks

# With custom configuration
API_URL=http://localhost:8000 ITERATIONS=100 npm run test:benchmarks
```

**Features:**
- API endpoint response time measurement
- Database query performance validation
- FAISS similarity search timing
- Memory usage monitoring
- Cache efficiency analysis
- Regression detection

### 2. Frontend Load Testing
Browser automation testing Core Web Vitals under load.

```bash
npm run test:frontend

# Custom load configuration
CONCURRENCY=20 DURATION=600 npm run test:frontend
```

**Scenarios:**
- Homepage performance testing
- Metrics dashboard interaction
- Analog explorer functionality
- CAPE calculator performance

### 3. API Load Testing
Comprehensive API load testing with realistic usage patterns.

```bash
npm run test:api

# Environment-specific testing
NODE_ENV=staging npm run test:api
```

**Load Patterns:**
- Normal operation: 50 concurrent users, 2 hours
- Peak weather events: 200 concurrent users, 30 minutes
- Stress testing: 500 concurrent users until failure
- Soak testing: 24-hour continuous operation

### 4. Memory Leak Detection
Long-running session monitoring for memory stability.

```bash
npm run test:memory

# 24-hour soak test
npm run test:soak

# Custom duration (in milliseconds)
SESSION_DURATION=7200000 npm run test:memory  # 2 hours
```

### 5. Lighthouse CI Audits
Automated Core Web Vitals and performance budgets.

```bash
npm run test:lighthouse

# Mobile-specific testing
LIGHTHOUSE_CONFIG=mobile npm run test:lighthouse
```

## 🔧 Configuration

### Environment Variables

```bash
# Service URLs
API_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000

# Authentication
API_TOKEN=your-api-token

# Test Configuration
ITERATIONS=50                    # Benchmark iterations
CONCURRENCY=10                   # Concurrent users
DURATION=300                     # Test duration (seconds)
SESSION_DURATION=86400000        # Memory test duration (ms)
SAMPLE_INTERVAL=30000            # Memory sample interval (ms)

# Performance Thresholds
PERFORMANCE_THRESHOLD_MS=500     # API response time threshold
MEMORY_THRESHOLD_MB=1024         # Memory usage threshold
ERROR_RATE_THRESHOLD=1.0         # Error rate threshold (%)
```

### Custom Configuration Files

#### Artillery Configuration (`load-tests/api-load-test.yml`)
```yaml
config:
  target: 'http://localhost:8000'
  phases:
    - duration: 300
      arrivalRate: 50
  variables:
    horizons: ["6h", "12h", "24h", "48h"]
    variable_sets: ["t2m", "t2m,u10,v10", "t2m,u10,v10,cape"]
```

#### Lighthouse Configuration (`lighthouse.config.js`)
```javascript
module.exports = {
  ci: {
    assert: {
      assertions: {
        'first-contentful-paint': ['error', { maxNumericValue: 1500 }],
        'largest-contentful-paint': ['error', { maxNumericValue: 2500 }],
        'cumulative-layout-shift': ['error', { maxNumericValue: 0.1 }]
      }
    }
  }
};
```

## 📈 Monitoring & Analysis

### Real-time Performance Monitoring

The test suite includes comprehensive monitoring capabilities:

```bash
# Start performance monitoring
npm run monitor

# Analyze recent test results
npm run analyze

# Update performance baseline
npm run baseline:update
```

### Performance Metrics Collection

- **Response Time Distribution**: Average, P50, P95, P99 measurements
- **Throughput Analysis**: Requests per second and concurrent capacity
- **Error Rate Tracking**: Categorized error analysis and recovery patterns
- **Resource Utilization**: CPU, memory, and network usage patterns
- **Cache Performance**: Hit/miss ratios and efficiency metrics

### Automated Reporting

Performance reports include:

1. **Executive Summary**: High-level performance status
2. **Detailed Metrics**: Comprehensive timing and resource data
3. **Regression Analysis**: Comparison with historical baselines
4. **Recommendations**: Specific optimization suggestions
5. **Trend Analysis**: Performance patterns over time

## 🔄 CI/CD Integration

### GitHub Actions Workflow

The performance test suite integrates with GitHub Actions for automated testing:

```yaml
# .github/workflows/performance-ci.yml
- name: Performance Gates
  run: |
    npm run health-check
    npm run test:quick
    npm run analyze
```

### Performance Gates

- **PR Validation**: Quick performance tests on pull requests
- **Nightly Testing**: Comprehensive performance validation
- **Baseline Updates**: Automatic baseline updates on main branch
- **Regression Alerts**: Automatic notifications for performance degradation

### Quality Gates

Performance tests will fail CI if:
- API P95 response time > 500ms
- Frontend Core Web Vitals exceed targets
- Error rate > 1%
- Memory usage > 1GB
- Cache hit rate < 60%

## 🚨 Alerting & Notifications

### Performance Regression Detection

The suite automatically detects:
- Response time degradation > 20%
- Memory usage increases > 50MB
- Error rate increases > 0.5%
- Cache efficiency decreases > 10%

### Alert Channels

- **GitHub**: PR comments and workflow notifications
- **Slack**: Real-time performance alerts (configure SLACK_WEBHOOK_URL)
- **Email**: Critical performance regression notifications

## 📋 Common Use Cases

### Daily Development Workflow

```bash
# Before starting development
npm run health-check

# Before committing changes
npm run test:quick

# Before merging to main
npm run test:full
```

### Performance Investigation

```bash
# Identify performance bottlenecks
npm run test:benchmarks

# Analyze memory usage patterns
npm run test:memory

# Deep-dive into specific endpoints
artillery run -t http://localhost:8000 -p load-tests/api-load-test.yml
```

### Load Testing Scenarios

```bash
# Normal business hours simulation
CONCURRENCY=50 DURATION=7200 npm run test:api

# Black Friday / high-traffic simulation
CONCURRENCY=200 DURATION=1800 npm run test:api

# Stress testing to failure
npm run test:stress
```

### Performance Optimization

```bash
# Establish baseline before optimization
npm run baseline:update

# Test optimization impact
npm run test:benchmarks

# Validate no regression
npm run analyze
```

## 🛠️ Advanced Usage

### Custom Test Scenarios

Create custom Artillery scenarios:

```yaml
# custom-scenario.yml
config:
  target: 'http://localhost:8000'
  phases:
    - duration: 60
      arrivalRate: 100
scenarios:
  - name: "Custom Weather API Test"
    flow:
      - get:
          url: "/forecast?horizon=24h&vars=t2m,cape"
          expect:
            - statusCode: 200
            - property: 'forecast.horizon'
              equals: '24h'
```

```bash
artillery run custom-scenario.yml
```

### Memory Profiling

Advanced memory leak detection:

```bash
# Run with heap snapshots
node --expose-gc --inspect scripts/memory-leak-detection.js

# Analyze with Chrome DevTools
# chrome://inspect -> Open dedicated DevTools for Node
```

### Custom Performance Processors

Extend Artillery with custom metrics:

```javascript
// custom-processor.js
module.exports = {
  init: function(config, ee, helpers) {
    // Custom initialization
  },
  
  onResponse: function(params, response, context, ee, next) {
    // Custom response analysis
    if (next) next();
  }
};
```

### Lighthouse Custom Audits

Add custom performance audits:

```javascript
// custom-lighthouse-config.js
module.exports = {
  extends: 'lighthouse:default',
  settings: {
    onlyAudits: [
      'first-contentful-paint',
      'largest-contentful-paint',
      'custom-weather-metrics'
    ]
  }
};
```

## 📊 Performance Baseline Management

### Establishing Baselines

```bash
# Run comprehensive baseline establishment
npm run test:full
npm run baseline:update
```

### Baseline Validation

The baseline includes:
- API response time percentiles
- Frontend Core Web Vitals measurements
- Database query performance metrics
- Memory usage patterns
- Cache efficiency statistics

### Updating Baselines

Baselines are automatically updated when:
- All performance tests pass
- No regressions are detected
- Running on main branch
- Manual baseline update is triggered

## 🔍 Troubleshooting

### Common Issues

#### Services Not Ready
```bash
# Check service status
npm run health-check

# Common solutions
docker-compose up -d
npm run warm-up
```

#### High Response Times
```bash
# Investigate specific endpoints
npm run test:benchmarks
npm run analyze

# Check system resources
docker stats
```

#### Memory Issues
```bash
# Run memory analysis
npm run test:memory

# Check for memory leaks
node --expose-gc scripts/memory-leak-detection.js
```

#### Cache Performance
```bash
# Analyze cache efficiency
curl http://localhost:8000/performance | jq '.cache'

# Clear cache and retest
curl -X POST http://localhost:8000/admin/clear-cache
```

### Debug Mode

Enable detailed logging:

```bash
DEBUG=* npm run test:benchmarks
VERBOSE=true npm run test:frontend
```

### Performance Logs

Logs are saved to:
- `tests/performance/reports/` - Test results and reports
- `performance_metrics.log` - Detailed performance logs
- `artillery-results-*.json` - Load test outputs
- `lighthouse-results.json` - Frontend audit results

## 📚 References

- [Performance Test Plan](reports/performance-test-plan.md) - Comprehensive testing strategy
- [Artillery.js Documentation](https://artillery.io/docs/) - Load testing framework
- [Lighthouse CI](https://github.com/GoogleChrome/lighthouse-ci) - Performance auditing
- [Playwright](https://playwright.dev/) - Browser automation
- [Web Vitals](https://web.dev/vitals/) - Core performance metrics

## 🤝 Contributing

When contributing to the performance test suite:

1. Run existing tests to ensure no regression
2. Add tests for new features or endpoints
3. Update baselines if performance improves
4. Document new test scenarios
5. Follow existing code style and patterns

## 📄 License

This performance test suite is part of the Adelaide Weather Forecasting System and follows the same MIT license terms.