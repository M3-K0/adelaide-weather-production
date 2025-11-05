/**
 * Performance Benchmarking Suite for Adelaide Weather Forecasting System
 * Establishes baseline performance metrics and monitors regression
 * 
 * Key Metrics:
 * - API response times
 * - Database query performance  
 * - FAISS search performance
 * - Memory usage patterns
 * - Cache efficiency
 */

const axios = require('axios');
const { performance } = require('perf_hooks');
const fs = require('fs').promises;
const path = require('path');

class PerformanceBenchmarks {
  constructor(config = {}) {
    this.apiUrl = config.apiUrl || 'http://localhost:8000';
    this.frontendUrl = config.frontendUrl || 'http://localhost:3000';
    this.iterations = config.iterations || 50;
    this.warmupIterations = config.warmupIterations || 10;
    
    this.results = {
      timestamp: new Date().toISOString(),
      environment: {
        apiUrl: this.apiUrl,
        frontendUrl: this.frontendUrl,
        nodeVersion: process.version,
        platform: process.platform
      },
      benchmarks: {},
      baseline: null,
      regression: {
        detected: false,
        details: []
      }
    };
    
    this.targets = {
      api: {
        forecast: { p95: 500, p99: 1000 }, // milliseconds
        health: { p95: 50, p99: 100 },
        metrics: { p95: 100, p99: 200 }
      },
      database: {
        simpleQuery: { p95: 50, p99: 100 },
        complexQuery: { p95: 200, p99: 500 },
        aggregation: { p95: 300, p99: 800 }
      },
      faiss: {
        search: { p95: 1, p99: 5 }, // Sub-millisecond targets
        indexLoad: { p95: 1000, p99: 2000 }
      },
      memory: {
        maxUsageMB: 1024,
        leakThresholdMB: 50
      }
    };
  }

  async runAllBenchmarks() {
    console.log('🚀 Starting Performance Benchmark Suite');
    console.log('========================================');
    console.log(`API Target: ${this.apiUrl}`);
    console.log(`Iterations: ${this.iterations} (warmup: ${this.warmupIterations})`);
    
    try {
      // Load existing baseline if available
      await this.loadBaseline();
      
      // Warmup phase
      console.log('\n🔥 Warming up systems...');
      await this.warmupPhase();
      
      // Run benchmarks
      console.log('\n📊 Running performance benchmarks...');
      
      await this.benchmarkAPIPerformance();
      await this.benchmarkDatabasePerformance();
      await this.benchmarkFAISSPerformance();
      await this.benchmarkMemoryUsage();
      await this.benchmarkCacheEfficiency();
      
      // Analysis and reporting
      this.analyzeResults();
      this.detectRegression();
      await this.saveResults();
      
      this.printSummary();
      
      return this.results;
      
    } catch (error) {
      console.error('❌ Benchmark suite failed:', error.message);
      throw error;
    }
  }

  async warmupPhase() {
    const warmupRequests = [
      '/health',
      '/forecast?horizon=24h&vars=t2m',
      '/performance',
      '/metrics'
    ];
    
    for (let i = 0; i < this.warmupIterations; i++) {
      for (const endpoint of warmupRequests) {
        try {
          await axios.get(`${this.apiUrl}${endpoint}`, { timeout: 5000 });
        } catch (error) {
          // Ignore warmup errors
        }
      }
    }
    console.log('✅ Warmup completed');
  }

  async benchmarkAPIPerformance() {
    console.log('📡 Benchmarking API performance...');
    
    const endpoints = [
      {
        name: 'forecast_basic',
        url: '/forecast?horizon=24h&vars=t2m',
        target: this.targets.api.forecast
      },
      {
        name: 'forecast_complex', 
        url: '/forecast?horizon=24h&vars=t2m,u10,v10,z500,t850,q850,cape',
        target: this.targets.api.forecast
      },
      {
        name: 'forecast_6h',
        url: '/forecast?horizon=6h&vars=t2m,cape',
        target: this.targets.api.forecast
      },
      {
        name: 'forecast_48h',
        url: '/forecast?horizon=48h&vars=t2m,u10,v10',
        target: this.targets.api.forecast
      },
      {
        name: 'health_check',
        url: '/health',
        target: this.targets.api.health
      },
      {
        name: 'performance_stats',
        url: '/performance',
        target: this.targets.api.metrics
      }
    ];

    this.results.benchmarks.api = {};
    
    for (const endpoint of endpoints) {
      console.log(`  Testing ${endpoint.name}...`);
      const times = [];
      let errors = 0;
      
      for (let i = 0; i < this.iterations; i++) {
        const start = performance.now();
        
        try {
          const response = await axios.get(`${this.apiUrl}${endpoint.url}`, {
            timeout: 10000,
            headers: { 'User-Agent': 'PerformanceBenchmark/1.0' }
          });
          
          const duration = performance.now() - start;
          times.push(duration);
          
          // Validate response structure for forecast endpoints
          if (endpoint.name.includes('forecast') && response.data) {
            if (!response.data.forecast || !response.data.forecast.horizon) {
              console.warn(`    Warning: Invalid response structure for ${endpoint.name}`);
            }
          }
          
        } catch (error) {
          errors++;
          console.warn(`    Error in ${endpoint.name}: ${error.message}`);
        }
      }
      
      const stats = this.calculateStatistics(times);
      stats.errorRate = (errors / this.iterations) * 100;
      stats.target = endpoint.target;
      stats.passesTarget = stats.p95 <= endpoint.target.p95;
      
      this.results.benchmarks.api[endpoint.name] = stats;
      
      console.log(`    ${endpoint.name}: ${stats.avg.toFixed(2)}ms avg, ${stats.p95.toFixed(2)}ms p95 ${stats.passesTarget ? '✅' : '❌'}`);
    }
  }

  async benchmarkDatabasePerformance() {
    console.log('🗄️  Benchmarking database performance...');
    
    // Database benchmarks via API endpoints that trigger different query types
    const dbTests = [
      {
        name: 'simple_metadata_query',
        url: '/forecast?horizon=6h&vars=t2m',
        target: this.targets.database.simpleQuery
      },
      {
        name: 'complex_variable_query',
        url: '/forecast?horizon=24h&vars=t2m,u10,v10,z500,t850,q850',
        target: this.targets.database.complexQuery
      },
      {
        name: 'aggregation_query',
        url: '/forecast?horizon=48h&vars=cape,t2m,u10,v10',
        target: this.targets.database.aggregation
      }
    ];

    this.results.benchmarks.database = {};
    
    for (const test of dbTests) {
      console.log(`  Testing ${test.name}...`);
      const times = [];
      
      for (let i = 0; i < this.iterations; i++) {
        const start = performance.now();
        
        try {
          await axios.get(`${this.apiUrl}${test.url}`, { timeout: 10000 });
          const duration = performance.now() - start;
          times.push(duration);
        } catch (error) {
          console.warn(`    Database test error: ${error.message}`);
        }
      }
      
      const stats = this.calculateStatistics(times);
      stats.target = test.target;
      stats.passesTarget = stats.p95 <= test.target.p95;
      
      this.results.benchmarks.database[test.name] = stats;
      
      console.log(`    ${test.name}: ${stats.avg.toFixed(2)}ms avg, ${stats.p95.toFixed(2)}ms p95 ${stats.passesTarget ? '✅' : '❌'}`);
    }
  }

  async benchmarkFAISSPerformance() {
    console.log('🔍 Benchmarking FAISS search performance...');
    
    // FAISS performance is measured indirectly through forecast requests
    // as the API uses FAISS for analog weather pattern matching
    const faissTests = [
      {
        name: 'faiss_6h_search',
        url: '/forecast?horizon=6h&vars=t2m,u10,v10',
        target: this.targets.faiss.search,
        description: '6-hour analog search'
      },
      {
        name: 'faiss_24h_search', 
        url: '/forecast?horizon=24h&vars=t2m,u10,v10,z500',
        target: this.targets.faiss.search,
        description: '24-hour analog search'
      },
      {
        name: 'faiss_complex_search',
        url: '/forecast?horizon=24h&vars=t2m,u10,v10,z500,t850,q850,cape',
        target: this.targets.faiss.search,
        description: 'Complex multi-variable search'
      }
    ];

    this.results.benchmarks.faiss = {};
    
    for (const test of faissTests) {
      console.log(`  Testing ${test.description}...`);
      const times = [];
      let analogCounts = [];
      
      for (let i = 0; i < this.iterations; i++) {
        const start = performance.now();
        
        try {
          const response = await axios.get(`${this.apiUrl}${test.url}`, { timeout: 10000 });
          const duration = performance.now() - start;
          times.push(duration);
          
          // Extract analog count if available in response
          if (response.data && response.data.forecast && response.data.forecast.analogs_count) {
            analogCounts.push(response.data.forecast.analogs_count);
          }
          
        } catch (error) {
          console.warn(`    FAISS test error: ${error.message}`);
        }
      }
      
      const stats = this.calculateStatistics(times);
      stats.target = test.target;
      stats.passesTarget = stats.p95 <= test.target.p95;
      stats.avgAnalogs = analogCounts.length > 0 ? analogCounts.reduce((a, b) => a + b) / analogCounts.length : 0;
      
      this.results.benchmarks.faiss[test.name] = stats;
      
      console.log(`    ${test.description}: ${stats.avg.toFixed(2)}ms avg, ${stats.avgAnalogs.toFixed(0)} analogs ${stats.passesTarget ? '✅' : '❌'}`);
    }
  }

  async benchmarkMemoryUsage() {
    console.log('💾 Benchmarking memory usage...');
    
    const memoryStats = {
      baseline: process.memoryUsage(),
      peak: process.memoryUsage(),
      samples: []
    };
    
    // Run memory-intensive operations
    for (let i = 0; i < 20; i++) {
      // Make complex forecast requests
      try {
        await axios.get(`${this.apiUrl}/forecast?horizon=24h&vars=t2m,u10,v10,z500,t850,q850,cape`, {
          timeout: 10000
        });
        
        const currentMemory = process.memoryUsage();
        memoryStats.samples.push(currentMemory);
        
        // Track peak memory
        if (currentMemory.heapUsed > memoryStats.peak.heapUsed) {
          memoryStats.peak = currentMemory;
        }
        
      } catch (error) {
        console.warn(`    Memory test error: ${error.message}`);
      }
    }
    
    const avgMemory = {
      heapUsed: memoryStats.samples.reduce((sum, m) => sum + m.heapUsed, 0) / memoryStats.samples.length,
      heapTotal: memoryStats.samples.reduce((sum, m) => sum + m.heapTotal, 0) / memoryStats.samples.length,
      external: memoryStats.samples.reduce((sum, m) => sum + m.external, 0) / memoryStats.samples.length
    };
    
    const memoryMB = {
      baseline: Math.round(memoryStats.baseline.heapUsed / 1024 / 1024),
      average: Math.round(avgMemory.heapUsed / 1024 / 1024),
      peak: Math.round(memoryStats.peak.heapUsed / 1024 / 1024)
    };
    
    const memoryGrowth = memoryMB.peak - memoryMB.baseline;
    const passesTarget = memoryMB.peak <= this.targets.memory.maxUsageMB;
    const hasLeak = memoryGrowth > this.targets.memory.leakThresholdMB;
    
    this.results.benchmarks.memory = {
      baseline: memoryMB.baseline,
      average: memoryMB.average,
      peak: memoryMB.peak,
      growth: memoryGrowth,
      passesTarget,
      hasLeak,
      target: this.targets.memory
    };
    
    console.log(`    Memory usage: ${memoryMB.baseline}MB → ${memoryMB.peak}MB (growth: ${memoryGrowth}MB) ${passesTarget ? '✅' : '❌'}`);
    if (hasLeak) {
      console.log(`    ⚠️  Potential memory leak detected (growth > ${this.targets.memory.leakThresholdMB}MB)`);
    }
  }

  async benchmarkCacheEfficiency() {
    console.log('🗃️  Benchmarking cache efficiency...');
    
    try {
      // Get initial cache stats
      const initialStats = await axios.get(`${this.apiUrl}/performance`);
      const initialCacheStats = initialStats.data.cache;
      
      // Make repeated requests to test cache
      const testUrl = '/forecast?horizon=24h&vars=t2m,u10,v10';
      for (let i = 0; i < 10; i++) {
        await axios.get(`${this.apiUrl}${testUrl}`);
      }
      
      // Get final cache stats
      const finalStats = await axios.get(`${this.apiUrl}/performance`);
      const finalCacheStats = finalStats.data.cache;
      
      const hitRateImprovement = finalCacheStats.hit_rate_percent - initialCacheStats.hit_rate_percent;
      const cacheEfficient = finalCacheStats.hit_rate_percent >= 60; // Target: >60%
      
      this.results.benchmarks.cache = {
        initialHitRate: initialCacheStats.hit_rate_percent,
        finalHitRate: finalCacheStats.hit_rate_percent,
        hitRateImprovement,
        cacheEfficient,
        totalRequests: finalCacheStats.total_requests,
        target: { minHitRate: 60 }
      };
      
      console.log(`    Cache hit rate: ${finalCacheStats.hit_rate_percent.toFixed(1)}% ${cacheEfficient ? '✅' : '❌'}`);
      
    } catch (error) {
      console.warn(`    Cache benchmark error: ${error.message}`);
      this.results.benchmarks.cache = { error: error.message };
    }
  }

  calculateStatistics(times) {
    if (times.length === 0) return { avg: 0, min: 0, max: 0, p50: 0, p95: 0, p99: 0 };
    
    const sorted = times.slice().sort((a, b) => a - b);
    
    return {
      count: times.length,
      avg: times.reduce((a, b) => a + b) / times.length,
      min: sorted[0],
      max: sorted[sorted.length - 1],
      p50: this.percentile(sorted, 50),
      p95: this.percentile(sorted, 95),
      p99: this.percentile(sorted, 99)
    };
  }

  percentile(sortedArray, p) {
    const index = (p / 100) * (sortedArray.length - 1);
    const lower = Math.floor(index);
    const upper = Math.ceil(index);
    const weight = index % 1;
    
    if (upper >= sortedArray.length) return sortedArray[sortedArray.length - 1];
    return sortedArray[lower] * (1 - weight) + sortedArray[upper] * weight;
  }

  analyzeResults() {
    console.log('\n🔍 Analyzing benchmark results...');
    
    const analysis = {
      overallPass: true,
      failures: [],
      warnings: [],
      performance: {
        excellent: 0,
        good: 0,
        poor: 0
      }
    };
    
    // Analyze each benchmark category
    Object.entries(this.results.benchmarks).forEach(([category, benchmarks]) => {
      if (category === 'memory') {
        if (!benchmarks.passesTarget) {
          analysis.overallPass = false;
          analysis.failures.push(`Memory usage exceeded target: ${benchmarks.peak}MB > ${benchmarks.target.maxUsageMB}MB`);
        }
        if (benchmarks.hasLeak) {
          analysis.warnings.push(`Potential memory leak: ${benchmarks.growth}MB growth`);
        }
        return;
      }
      
      if (category === 'cache') {
        if (!benchmarks.cacheEfficient) {
          analysis.warnings.push(`Cache hit rate below target: ${benchmarks.finalHitRate}% < ${benchmarks.target.minHitRate}%`);
        }
        return;
      }
      
      // Analyze performance benchmarks
      Object.entries(benchmarks).forEach(([test, stats]) => {
        if (stats.passesTarget) {
          if (stats.p95 <= stats.target.p95 * 0.7) {
            analysis.performance.excellent++;
          } else {
            analysis.performance.good++;
          }
        } else {
          analysis.performance.poor++;
          analysis.overallPass = false;
          analysis.failures.push(`${category}.${test}: P95 ${stats.p95.toFixed(2)}ms > ${stats.target.p95}ms`);
        }
        
        if (stats.errorRate > 1) {
          analysis.warnings.push(`${category}.${test}: High error rate ${stats.errorRate.toFixed(1)}%`);
        }
      });
    });
    
    this.results.analysis = analysis;
    
    console.log(`  Overall: ${analysis.overallPass ? 'PASS ✅' : 'FAIL ❌'}`);
    console.log(`  Performance: ${analysis.performance.excellent} excellent, ${analysis.performance.good} good, ${analysis.performance.poor} poor`);
    
    if (analysis.failures.length > 0) {
      console.log('  Failures:');
      analysis.failures.forEach(failure => console.log(`    - ${failure}`));
    }
    
    if (analysis.warnings.length > 0) {
      console.log('  Warnings:');
      analysis.warnings.forEach(warning => console.log(`    - ${warning}`));
    }
  }

  async loadBaseline() {
    try {
      const baselinePath = path.join(__dirname, '..', 'reports', 'performance-baseline.json');
      const data = await fs.readFile(baselinePath, 'utf8');
      this.results.baseline = JSON.parse(data);
      console.log('📋 Loaded performance baseline');
    } catch (error) {
      console.log('📋 No existing baseline found, will create new one');
    }
  }

  detectRegression() {
    if (!this.results.baseline) {
      console.log('🔍 No baseline available for regression detection');
      return;
    }
    
    console.log('🔍 Detecting performance regression...');
    
    const regressionThreshold = 1.2; // 20% performance degradation threshold
    const regressions = [];
    
    // Compare current results with baseline
    Object.entries(this.results.benchmarks).forEach(([category, benchmarks]) => {
      if (!this.results.baseline.benchmarks[category]) return;
      
      Object.entries(benchmarks).forEach(([test, stats]) => {
        const baseline = this.results.baseline.benchmarks[category][test];
        if (!baseline || typeof stats.p95 !== 'number' || typeof baseline.p95 !== 'number') return;
        
        const regression = stats.p95 / baseline.p95;
        if (regression > regressionThreshold) {
          regressions.push({
            test: `${category}.${test}`,
            current: stats.p95,
            baseline: baseline.p95,
            regression: ((regression - 1) * 100).toFixed(1) + '%'
          });
        }
      });
    });
    
    this.results.regression.detected = regressions.length > 0;
    this.results.regression.details = regressions;
    
    if (regressions.length > 0) {
      console.log('  🐌 Performance regressions detected:');
      regressions.forEach(reg => {
        console.log(`    - ${reg.test}: ${reg.current.toFixed(2)}ms vs ${reg.baseline.toFixed(2)}ms baseline (+${reg.regression})`);
      });
    } else {
      console.log('  ✅ No significant performance regression detected');
    }
  }

  async saveResults() {
    const reportsDir = path.join(__dirname, '..', 'reports');
    
    // Ensure reports directory exists
    try {
      await fs.mkdir(reportsDir, { recursive: true });
    } catch (error) {
      // Directory already exists
    }
    
    // Save detailed results
    const resultsPath = path.join(reportsDir, `performance-benchmark-${Date.now()}.json`);
    await fs.writeFile(resultsPath, JSON.stringify(this.results, null, 2));
    
    // Update baseline if this run was successful
    if (this.results.analysis && this.results.analysis.overallPass) {
      const baselinePath = path.join(reportsDir, 'performance-baseline.json');
      await fs.writeFile(baselinePath, JSON.stringify(this.results, null, 2));
      console.log('💾 Updated performance baseline');
    }
    
    console.log(`💾 Results saved to: ${resultsPath}`);
  }

  printSummary() {
    console.log('\n📊 Performance Benchmark Summary');
    console.log('='.repeat(50));
    
    const { benchmarks } = this.results;
    
    // API Summary
    if (benchmarks.api) {
      console.log('\n📡 API Performance:');
      Object.entries(benchmarks.api).forEach(([test, stats]) => {
        const status = stats.passesTarget ? '✅' : '❌';
        console.log(`  ${test}: ${stats.avg.toFixed(2)}ms avg, ${stats.p95.toFixed(2)}ms p95 ${status}`);
      });
    }
    
    // Memory Summary
    if (benchmarks.memory) {
      const mem = benchmarks.memory;
      console.log(`\n💾 Memory: ${mem.baseline}MB → ${mem.peak}MB (${mem.growth >= 0 ? '+' : ''}${mem.growth}MB) ${mem.passesTarget ? '✅' : '❌'}`);
    }
    
    // Cache Summary
    if (benchmarks.cache && !benchmarks.cache.error) {
      console.log(`\n🗃️  Cache: ${benchmarks.cache.finalHitRate.toFixed(1)}% hit rate ${benchmarks.cache.cacheEfficient ? '✅' : '❌'}`);
    }
    
    // Overall Status
    const overall = this.results.analysis.overallPass ? 'PASS ✅' : 'FAIL ❌';
    console.log(`\n🎯 Overall Result: ${overall}`);
    
    if (this.results.regression.detected) {
      console.log(`🐌 Performance regression detected in ${this.results.regression.details.length} tests`);
    }
  }
}

// CLI execution
async function main() {
  const config = {
    apiUrl: process.env.API_URL || 'http://localhost:8000',
    frontendUrl: process.env.FRONTEND_URL || 'http://localhost:3000',
    iterations: parseInt(process.env.ITERATIONS) || 50,
    warmupIterations: parseInt(process.env.WARMUP_ITERATIONS) || 10
  };
  
  const benchmarks = new PerformanceBenchmarks(config);
  
  try {
    const results = await benchmarks.runAllBenchmarks();
    
    // Exit with appropriate code
    if (results.analysis.overallPass && !results.regression.detected) {
      console.log('\n✅ All benchmarks passed');
      process.exit(0);
    } else if (results.regression.detected) {
      console.log('\n⚠️  Performance regression detected');
      process.exit(1);
    } else {
      console.log('\n❌ Benchmark failures detected');
      process.exit(1);
    }
    
  } catch (error) {
    console.error('\n💥 Benchmark suite failed:', error.message);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = PerformanceBenchmarks;