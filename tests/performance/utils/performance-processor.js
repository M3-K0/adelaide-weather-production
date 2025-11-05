/**
 * Artillery.js Performance Processor
 * Custom processor for advanced performance metrics collection
 */

const fs = require('fs');
const path = require('path');

module.exports = {
  // Called when Artillery starts
  init: function(config, ee, helpers) {
    this.startTime = Date.now();
    this.metrics = {
      requests: [],
      errors: [],
      responseTimeStats: {
        sum: 0,
        count: 0,
        min: Infinity,
        max: 0,
        p95Values: []
      },
      cacheStats: {
        hits: 0,
        misses: 0
      },
      endpointStats: {}
    };
    
    console.log('🔧 Artillery performance processor initialized');
    
    // Listen for request events
    ee.on('request', this.onRequest.bind(this));
    ee.on('response', this.onResponse.bind(this));
    ee.on('error', this.onError.bind(this));
    
    // Periodic stats collection
    this.statsInterval = setInterval(this.collectStats.bind(this), 10000);
  },

  // Called for each request
  onRequest: function(params, context, ee, next) {
    const requestStart = Date.now();
    
    // Add request tracking
    context.vars = context.vars || {};
    context.vars._requestStart = requestStart;
    context.vars._requestId = Math.random().toString(36).substr(2, 9);
    
    if (next) next();
  },

  // Called for each response
  onResponse: function(params, response, context, ee, next) {
    const responseTime = Date.now() - (context.vars._requestStart || Date.now());
    const endpoint = this.extractEndpoint(params.url);
    
    // Store response metrics
    this.metrics.requests.push({
      id: context.vars._requestId,
      url: params.url,
      endpoint,
      method: params.method || 'GET',
      statusCode: response.statusCode,
      responseTime,
      timestamp: Date.now(),
      cacheHit: response.headers['x-cache'] === 'HIT',
      responseSize: this.getResponseSize(response)
    });
    
    // Update running statistics
    this.updateStats(responseTime, endpoint, response);
    
    // Track cache performance
    if (response.headers['x-cache'] === 'HIT') {
      this.metrics.cacheStats.hits++;
    } else {
      this.metrics.cacheStats.misses++;
    }
    
    if (next) next();
  },

  // Called for each error
  onError: function(error, context, ee, next) {
    this.metrics.errors.push({
      id: context.vars._requestId,
      error: error.message,
      code: error.code,
      timestamp: Date.now(),
      url: error.url || 'unknown'
    });
    
    if (next) next();
  },

  updateStats: function(responseTime, endpoint, response) {
    const stats = this.metrics.responseTimeStats;
    
    // Update global stats
    stats.sum += responseTime;
    stats.count++;
    stats.min = Math.min(stats.min, responseTime);
    stats.max = Math.max(stats.max, responseTime);
    stats.p95Values.push(responseTime);
    
    // Keep only recent values for P95 calculation
    if (stats.p95Values.length > 1000) {
      stats.p95Values = stats.p95Values.slice(-1000);
    }
    
    // Update endpoint-specific stats
    if (!this.metrics.endpointStats[endpoint]) {
      this.metrics.endpointStats[endpoint] = {
        count: 0,
        sum: 0,
        min: Infinity,
        max: 0,
        errors: 0,
        successRate: 100
      };
    }
    
    const endpointStat = this.metrics.endpointStats[endpoint];
    endpointStat.count++;
    endpointStat.sum += responseTime;
    endpointStat.min = Math.min(endpointStat.min, responseTime);
    endpointStat.max = Math.max(endpointStat.max, responseTime);
    
    if (response.statusCode >= 400) {
      endpointStat.errors++;
    }
    
    endpointStat.successRate = ((endpointStat.count - endpointStat.errors) / endpointStat.count) * 100;
  },

  extractEndpoint: function(url) {
    try {
      const urlObj = new URL(url);
      const path = urlObj.pathname;
      
      // Normalize forecast endpoints
      if (path.includes('/forecast')) {
        return '/forecast';
      } else if (path.includes('/health')) {
        return '/health';
      } else if (path.includes('/performance')) {
        return '/performance';
      } else if (path.includes('/metrics')) {
        return '/metrics';
      }
      
      return path;
    } catch (error) {
      return 'unknown';
    }
  },

  getResponseSize: function(response) {
    const contentLength = response.headers['content-length'];
    if (contentLength) {
      return parseInt(contentLength, 10);
    }
    
    // Estimate from response body if available
    if (response.body) {
      return Buffer.byteLength(response.body, 'utf8');
    }
    
    return 0;
  },

  collectStats: function() {
    const now = Date.now();
    const elapsedSeconds = (now - this.startTime) / 1000;
    const stats = this.metrics.responseTimeStats;
    
    // Calculate current performance metrics
    const currentMetrics = {
      timestamp: now,
      elapsed: elapsedSeconds,
      totalRequests: stats.count,
      requestsPerSecond: stats.count / elapsedSeconds,
      averageResponseTime: stats.count > 0 ? stats.sum / stats.count : 0,
      minResponseTime: stats.min !== Infinity ? stats.min : 0,
      maxResponseTime: stats.max,
      p95ResponseTime: this.calculateP95(stats.p95Values),
      errorCount: this.metrics.errors.length,
      errorRate: stats.count > 0 ? (this.metrics.errors.length / stats.count) * 100 : 0,
      cacheHitRate: this.getCacheHitRate(),
      endpointBreakdown: this.getEndpointBreakdown()
    };
    
    // Log performance status
    console.log(`📊 [${Math.floor(elapsedSeconds)}s] Requests: ${currentMetrics.totalRequests} | ` +
                `RPS: ${currentMetrics.requestsPerSecond.toFixed(1)} | ` +
                `Avg: ${currentMetrics.averageResponseTime.toFixed(1)}ms | ` +
                `P95: ${currentMetrics.p95ResponseTime.toFixed(1)}ms | ` +
                `Errors: ${currentMetrics.errorRate.toFixed(1)}%`);
    
    // Check for performance alerts
    this.checkPerformanceAlerts(currentMetrics);
  },

  calculateP95: function(values) {
    if (values.length === 0) return 0;
    
    const sorted = values.slice().sort((a, b) => a - b);
    const index = Math.ceil(sorted.length * 0.95) - 1;
    return sorted[Math.max(0, index)];
  },

  getCacheHitRate: function() {
    const total = this.metrics.cacheStats.hits + this.metrics.cacheStats.misses;
    return total > 0 ? (this.metrics.cacheStats.hits / total) * 100 : 0;
  },

  getEndpointBreakdown: function() {
    const breakdown = {};
    
    Object.entries(this.metrics.endpointStats).forEach(([endpoint, stats]) => {
      breakdown[endpoint] = {
        count: stats.count,
        avgResponseTime: stats.count > 0 ? stats.sum / stats.count : 0,
        minResponseTime: stats.min !== Infinity ? stats.min : 0,
        maxResponseTime: stats.max,
        errorRate: ((stats.errors / stats.count) * 100).toFixed(1) + '%',
        successRate: stats.successRate.toFixed(1) + '%'
      };
    });
    
    return breakdown;
  },

  checkPerformanceAlerts: function(metrics) {
    const alerts = [];
    
    // Response time alerts
    if (metrics.p95ResponseTime > 500) {
      alerts.push(`P95 response time: ${metrics.p95ResponseTime.toFixed(1)}ms > 500ms target`);
    }
    
    // Error rate alerts
    if (metrics.errorRate > 1) {
      alerts.push(`Error rate: ${metrics.errorRate.toFixed(1)}% > 1% target`);
    }
    
    // Cache performance alerts
    if (metrics.cacheHitRate < 60 && metrics.totalRequests > 50) {
      alerts.push(`Cache hit rate: ${metrics.cacheHitRate.toFixed(1)}% < 60% target`);
    }
    
    // Throughput alerts (if very low)
    if (metrics.requestsPerSecond < 1 && metrics.totalRequests > 10) {
      alerts.push(`Low throughput: ${metrics.requestsPerSecond.toFixed(1)} RPS`);
    }
    
    // Log alerts
    alerts.forEach(alert => {
      console.log(`⚠️  PERFORMANCE ALERT: ${alert}`);
    });
  },

  // Called when Artillery finishes
  cleanup: function(config, ee, done) {
    clearInterval(this.statsInterval);
    
    const finalReport = this.generateFinalReport();
    
    // Save detailed results
    this.saveResults(finalReport);
    
    console.log('\n📋 Artillery Performance Report');
    console.log('=' .repeat(50));
    this.printSummary(finalReport);
    
    if (done) done();
  },

  generateFinalReport: function() {
    const stats = this.metrics.responseTimeStats;
    const totalDuration = (Date.now() - this.startTime) / 1000;
    
    return {
      metadata: {
        testDuration: totalDuration,
        startTime: new Date(this.startTime).toISOString(),
        endTime: new Date().toISOString(),
        artillery: true
      },
      
      summary: {
        totalRequests: stats.count,
        totalErrors: this.metrics.errors.length,
        requestsPerSecond: stats.count / totalDuration,
        errorRate: stats.count > 0 ? (this.metrics.errors.length / stats.count) * 100 : 0,
        testDurationSeconds: totalDuration
      },
      
      performance: {
        averageResponseTime: stats.count > 0 ? stats.sum / stats.count : 0,
        minResponseTime: stats.min !== Infinity ? stats.min : 0,
        maxResponseTime: stats.max,
        p95ResponseTime: this.calculateP95(stats.p95Values),
        p99ResponseTime: this.calculateP99(stats.p95Values)
      },
      
      cache: {
        hitRate: this.getCacheHitRate(),
        totalHits: this.metrics.cacheStats.hits,
        totalMisses: this.metrics.cacheStats.misses
      },
      
      endpoints: this.metrics.endpointStats,
      
      targets: {
        responseTimeTarget: 500,
        responseTimeMet: this.calculateP95(stats.p95Values) <= 500,
        errorRateTarget: 1,
        errorRateMet: (this.metrics.errors.length / stats.count) * 100 <= 1,
        cacheTarget: 60,
        cacheTargetMet: this.getCacheHitRate() >= 60
      },
      
      rawData: {
        requests: this.metrics.requests.slice(-100), // Last 100 requests
        errors: this.metrics.errors,
        allResponseTimes: stats.p95Values
      }
    };
  },

  calculateP99: function(values) {
    if (values.length === 0) return 0;
    
    const sorted = values.slice().sort((a, b) => a - b);
    const index = Math.ceil(sorted.length * 0.99) - 1;
    return sorted[Math.max(0, index)];
  },

  saveResults: function(report) {
    try {
      const reportsDir = path.join(__dirname, '..', 'reports');
      
      // Ensure directory exists
      if (!fs.existsSync(reportsDir)) {
        fs.mkdirSync(reportsDir, { recursive: true });
      }
      
      const filename = `artillery-results-${Date.now()}.json`;
      const filepath = path.join(reportsDir, filename);
      
      fs.writeFileSync(filepath, JSON.stringify(report, null, 2));
      console.log(`💾 Results saved to: ${filepath}`);
      
      // Save summary for CI integration
      const summaryPath = path.join(reportsDir, 'artillery-summary.json');
      const summary = {
        avgResponseTime: report.performance.averageResponseTime.toFixed(2),
        p95ResponseTime: report.performance.p95ResponseTime.toFixed(2),
        errorRate: report.summary.errorRate.toFixed(2),
        throughput: report.summary.requestsPerSecond.toFixed(2),
        cacheHitRate: report.cache.hitRate.toFixed(1),
        targetsMet: Object.values(report.targets).filter(met => met === true).length,
        totalTargets: Object.keys(report.targets).filter(key => key.endsWith('Met')).length
      };
      
      fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2));
      
    } catch (error) {
      console.error('Error saving results:', error.message);
    }
  },

  printSummary: function(report) {
    console.log(`Total Requests: ${report.summary.totalRequests}`);
    console.log(`Error Rate: ${report.summary.errorRate.toFixed(2)}%`);
    console.log(`Requests/sec: ${report.summary.requestsPerSecond.toFixed(2)}`);
    console.log(`Avg Response Time: ${report.performance.averageResponseTime.toFixed(2)}ms`);
    console.log(`P95 Response Time: ${report.performance.p95ResponseTime.toFixed(2)}ms`);
    console.log(`Cache Hit Rate: ${report.cache.hitRate.toFixed(1)}%`);
    
    console.log('\nEndpoint Breakdown:');
    Object.entries(report.endpoints).forEach(([endpoint, stats]) => {
      const avg = stats.count > 0 ? stats.sum / stats.count : 0;
      console.log(`  ${endpoint}: ${stats.count} requests, ${avg.toFixed(1)}ms avg`);
    });
    
    console.log('\nTargets:');
    console.log(`  Response Time (P95 < 500ms): ${report.targets.responseTimeMet ? '✅' : '❌'}`);
    console.log(`  Error Rate (< 1%): ${report.targets.errorRateMet ? '✅' : '❌'}`);
    console.log(`  Cache Hit Rate (> 60%): ${report.targets.cacheTargetMet ? '✅' : '❌'}`);
    
    const overallPass = report.targets.responseTimeMet && 
                       report.targets.errorRateMet && 
                       report.targets.cacheTargetMet;
    
    console.log(`\nOverall: ${overallPass ? 'PASS ✅' : 'FAIL ❌'}`);
  }
};