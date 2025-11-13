/**
 * TEST2: Performance Processor for Load Testing
 * 
 * Custom Artillery.js processor for:
 * - Real-time performance monitoring
 * - FAISS search time validation  
 * - Fallback detection and alerting
 * - Memory usage tracking
 * - SLA violation detection
 */

const fs = require('fs');
const path = require('path');

class TEST2PerformanceProcessor {
  constructor() {
    this.performanceMetrics = {
      api: {
        requests: 0,
        successes: 0,
        failures: 0,
        responseTimes: [],
        p95: 0,
        p99: 0,
        mean: 0
      },
      faiss: {
        searchTimes: [],
        p95: 0,
        p99: 0,
        mean: 0,
        fallbackCount: 0,
        nonFaissDataSourceCount: 0
      },
      system: {
        memoryUsage: [],
        cpuUsage: [],
        peakMemory: 0,
        averageMemory: 0
      },
      violations: {
        apiSlaViolations: 0,
        faissSlaViolations: 0,
        fallbackUsageDetected: 0,
        errorRateViolations: 0
      },
      timestamps: {
        testStart: null,
        lastUpdate: null
      }
    };

    this.outputFile = path.join(__dirname, '../reports/test2-performance-metrics.json');
    this.realTimeFile = path.join(__dirname, '../reports/test2-realtime-metrics.json');
    
    // Ensure output directory exists
    const outputDir = path.dirname(this.outputFile);
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }
    
    this.slaThresholds = {
      apiResponseTimeMs: 150,    // TEST2 requirement: p95 < 150ms
      faissSearchTimeMs: 1.0,    // TEST2 requirement: p95 < 1ms
      errorRate: 0.001,          // < 0.1% error rate
      fallbackRate: 0,           // Zero fallback usage
      memoryLimitMB: 8000        // 8GB memory limit
    };

    console.log('TEST2 Performance Processor initialized');
    console.log(`SLA Thresholds: API ${this.slaThresholds.apiResponseTimeMs}ms, FAISS ${this.slaThresholds.faissSearchTimeMs}ms`);
  }

  /**
   * Called before the test starts
   */
  beforeScenario(scenario, ee) {
    this.performanceMetrics.timestamps.testStart = Date.now();
    console.log(`Starting TEST2 performance monitoring for scenario: ${scenario.name}`);
  }

  /**
   * Called on each request
   */
  beforeRequest(req, context) {
    req._startTime = Date.now();
  }

  /**
   * Called on each response
   */
  afterResponse(req, res, context, ee) {
    const endTime = Date.now();
    const responseTime = endTime - req._startTime;
    
    this.performanceMetrics.api.requests++;
    this.performanceMetrics.timestamps.lastUpdate = endTime;

    // Record API performance
    if (res.statusCode >= 200 && res.statusCode < 300) {
      this.performanceMetrics.api.successes++;
      this.performanceMetrics.api.responseTimes.push(responseTime);
      
      // Check API SLA violation
      if (responseTime > this.slaThresholds.apiResponseTimeMs) {
        this.performanceMetrics.violations.apiSlaViolations++;
        console.warn(`⚠️  API SLA violation: ${responseTime}ms > ${this.slaThresholds.apiResponseTimeMs}ms`);
      }

      // Extract and validate FAISS metrics from response
      if (res.body) {
        try {
          const responseData = JSON.parse(res.body);
          this.processFAISSMetrics(responseData);
          this.processSystemMetrics(responseData);
        } catch (error) {
          console.warn('Failed to parse response for metrics extraction:', error.message);
        }
      }
    } else {
      this.performanceMetrics.api.failures++;
      console.warn(`❌ Request failed: ${res.statusCode} ${req.url}`);
    }

    // Real-time SLA monitoring
    this.updateRealTimeMetrics();
    
    // Check error rate SLA
    const errorRate = this.performanceMetrics.api.failures / this.performanceMetrics.api.requests;
    if (errorRate > this.slaThresholds.errorRate) {
      this.performanceMetrics.violations.errorRateViolations++;
    }
  }

  /**
   * Process FAISS-specific metrics from API response
   */
  processFAISSMetrics(responseData) {
    // Extract FAISS search time
    let faissTime = null;
    if (responseData.search_stats?.faiss_search_time_ms !== undefined) {
      faissTime = responseData.search_stats.faiss_search_time_ms;
    } else if (responseData.performance_stats?.faiss_time_ms !== undefined) {
      faissTime = responseData.performance_stats.faiss_time_ms;
    }

    if (faissTime !== null) {
      this.performanceMetrics.faiss.searchTimes.push(faissTime);
      
      // Check FAISS SLA violation
      if (faissTime > this.slaThresholds.faissSearchTimeMs) {
        this.performanceMetrics.violations.faissSlaViolations++;
        console.warn(`⚠️  FAISS SLA violation: ${faissTime}ms > ${this.slaThresholds.faissSearchTimeMs}ms`);
      }
    }

    // Check fallback usage (TEST2 requirement: zero fallback)
    const fallbackUsed = responseData.search_stats?.fallback_used || responseData.performance_stats?.fallback_used;
    if (fallbackUsed === true) {
      this.performanceMetrics.faiss.fallbackCount++;
      this.performanceMetrics.violations.fallbackUsageDetected++;
      console.error(`🚨 FALLBACK DETECTED: Zero fallback required for TEST2!`);
    }

    // Check data source (must be FAISS)
    const dataSource = responseData.search_stats?.data_source || responseData.forecast?.data_source;
    if (dataSource && dataSource.toLowerCase() !== 'faiss') {
      this.performanceMetrics.faiss.nonFaissDataSourceCount++;
      console.warn(`⚠️  Non-FAISS data source detected: ${dataSource}`);
    }
  }

  /**
   * Process system-level metrics from API response
   */
  processSystemMetrics(responseData) {
    // Extract memory usage
    const memoryUsage = responseData.memory_usage_mb || 
                       responseData.search_stats?.memory_usage_mb ||
                       responseData.performance_stats?.memory_usage_mb;
                       
    if (memoryUsage !== undefined) {
      this.performanceMetrics.system.memoryUsage.push(memoryUsage);
      
      if (memoryUsage > this.performanceMetrics.system.peakMemory) {
        this.performanceMetrics.system.peakMemory = memoryUsage;
      }
      
      // Check memory limit
      if (memoryUsage > this.slaThresholds.memoryLimitMB) {
        console.warn(`⚠️  High memory usage: ${memoryUsage}MB > ${this.slaThresholds.memoryLimitMB}MB`);
      }
    }

    // Extract CPU usage if available
    const cpuUsage = responseData.cpu_usage_percent;
    if (cpuUsage !== undefined) {
      this.performanceMetrics.system.cpuUsage.push(cpuUsage);
    }
  }

  /**
   * Calculate percentile for array of values
   */
  calculatePercentile(values, percentile) {
    if (values.length === 0) return 0;
    
    const sorted = [...values].sort((a, b) => a - b);
    const index = Math.ceil((percentile / 100) * sorted.length) - 1;
    return sorted[Math.max(0, index)];
  }

  /**
   * Update real-time performance calculations
   */
  updateRealTimeMetrics() {
    // Update API metrics
    if (this.performanceMetrics.api.responseTimes.length > 0) {
      this.performanceMetrics.api.p95 = this.calculatePercentile(this.performanceMetrics.api.responseTimes, 95);
      this.performanceMetrics.api.p99 = this.calculatePercentile(this.performanceMetrics.api.responseTimes, 99);
      this.performanceMetrics.api.mean = this.performanceMetrics.api.responseTimes.reduce((sum, time) => sum + time, 0) / this.performanceMetrics.api.responseTimes.length;
    }

    // Update FAISS metrics
    if (this.performanceMetrics.faiss.searchTimes.length > 0) {
      this.performanceMetrics.faiss.p95 = this.calculatePercentile(this.performanceMetrics.faiss.searchTimes, 95);
      this.performanceMetrics.faiss.p99 = this.calculatePercentile(this.performanceMetrics.faiss.searchTimes, 99);
      this.performanceMetrics.faiss.mean = this.performanceMetrics.faiss.searchTimes.reduce((sum, time) => sum + time, 0) / this.performanceMetrics.faiss.searchTimes.length;
    }

    // Update system metrics
    if (this.performanceMetrics.system.memoryUsage.length > 0) {
      this.performanceMetrics.system.averageMemory = this.performanceMetrics.system.memoryUsage.reduce((sum, mem) => sum + mem, 0) / this.performanceMetrics.system.memoryUsage.length;
    }

    // Write real-time metrics every 100 requests
    if (this.performanceMetrics.api.requests % 100 === 0) {
      this.writeRealTimeMetrics();
    }
  }

  /**
   * Write real-time metrics to file for monitoring
   */
  writeRealTimeMetrics() {
    const realTimeData = {
      timestamp: new Date().toISOString(),
      test_duration_ms: Date.now() - this.performanceMetrics.timestamps.testStart,
      current_metrics: {
        requests_processed: this.performanceMetrics.api.requests,
        success_rate: this.performanceMetrics.api.successes / this.performanceMetrics.api.requests,
        api_p95_ms: this.performanceMetrics.api.p95,
        faiss_p95_ms: this.performanceMetrics.faiss.p95,
        fallback_count: this.performanceMetrics.faiss.fallbackCount,
        peak_memory_mb: this.performanceMetrics.system.peakMemory,
        sla_violations: this.performanceMetrics.violations
      },
      sla_compliance: {
        api_p95_compliant: this.performanceMetrics.api.p95 <= this.slaThresholds.apiResponseTimeMs,
        faiss_p95_compliant: this.performanceMetrics.faiss.p95 <= this.slaThresholds.faissSearchTimeMs,
        zero_fallback_compliant: this.performanceMetrics.faiss.fallbackCount === 0,
        error_rate_compliant: (this.performanceMetrics.api.failures / this.performanceMetrics.api.requests) <= this.slaThresholds.errorRate
      }
    };

    try {
      fs.writeFileSync(this.realTimeFile, JSON.stringify(realTimeData, null, 2));
    } catch (error) {
      console.warn('Failed to write real-time metrics:', error.message);
    }
  }

  /**
   * Called when the test ends
   */
  afterScenario(scenario, ee) {
    console.log(`\n=== TEST2 Performance Summary for ${scenario.name} ===`);
    
    // Final calculations
    this.updateRealTimeMetrics();
    
    // Generate final report
    const finalReport = this.generateFinalReport();
    
    // Write final metrics
    try {
      fs.writeFileSync(this.outputFile, JSON.stringify(finalReport, null, 2));
      console.log(`📊 Final metrics written to: ${this.outputFile}`);
    } catch (error) {
      console.error('Failed to write final metrics:', error.message);
    }

    // Print summary
    this.printSummary();
    
    // Validate TEST2 requirements
    this.validateTEST2Requirements();
  }

  /**
   * Generate comprehensive final report
   */
  generateFinalReport() {
    const testDuration = Date.now() - this.performanceMetrics.timestamps.testStart;
    
    return {
      test_metadata: {
        test_name: 'TEST2 Comprehensive Load Test',
        timestamp: new Date().toISOString(),
        duration_ms: testDuration,
        duration_formatted: this.formatDuration(testDuration)
      },
      performance_summary: {
        api: {
          total_requests: this.performanceMetrics.api.requests,
          successful_requests: this.performanceMetrics.api.successes,
          failed_requests: this.performanceMetrics.api.failures,
          success_rate: this.performanceMetrics.api.successes / this.performanceMetrics.api.requests,
          response_times: {
            p50: this.calculatePercentile(this.performanceMetrics.api.responseTimes, 50),
            p95: this.performanceMetrics.api.p95,
            p99: this.performanceMetrics.api.p99,
            mean: this.performanceMetrics.api.mean,
            min: Math.min(...this.performanceMetrics.api.responseTimes),
            max: Math.max(...this.performanceMetrics.api.responseTimes)
          }
        },
        faiss: {
          total_searches: this.performanceMetrics.faiss.searchTimes.length,
          search_times: {
            p50: this.calculatePercentile(this.performanceMetrics.faiss.searchTimes, 50),
            p95: this.performanceMetrics.faiss.p95,
            p99: this.performanceMetrics.faiss.p99,
            mean: this.performanceMetrics.faiss.mean,
            min: this.performanceMetrics.faiss.searchTimes.length > 0 ? Math.min(...this.performanceMetrics.faiss.searchTimes) : 0,
            max: this.performanceMetrics.faiss.searchTimes.length > 0 ? Math.max(...this.performanceMetrics.faiss.searchTimes) : 0
          },
          fallback_count: this.performanceMetrics.faiss.fallbackCount,
          non_faiss_data_source_count: this.performanceMetrics.faiss.nonFaissDataSourceCount
        },
        system: {
          memory_usage: {
            peak_mb: this.performanceMetrics.system.peakMemory,
            average_mb: this.performanceMetrics.system.averageMemory,
            samples: this.performanceMetrics.system.memoryUsage.length
          },
          cpu_usage: {
            samples: this.performanceMetrics.system.cpuUsage.length,
            average_percent: this.performanceMetrics.system.cpuUsage.length > 0 ?
              this.performanceMetrics.system.cpuUsage.reduce((sum, cpu) => sum + cpu, 0) / this.performanceMetrics.system.cpuUsage.length : 0
          }
        }
      },
      sla_compliance: {
        api_p95_requirement: {
          threshold_ms: this.slaThresholds.apiResponseTimeMs,
          actual_ms: this.performanceMetrics.api.p95,
          compliant: this.performanceMetrics.api.p95 <= this.slaThresholds.apiResponseTimeMs,
          violations: this.performanceMetrics.violations.apiSlaViolations
        },
        faiss_p95_requirement: {
          threshold_ms: this.slaThresholds.faissSearchTimeMs,
          actual_ms: this.performanceMetrics.faiss.p95,
          compliant: this.performanceMetrics.faiss.p95 <= this.slaThresholds.faissSearchTimeMs,
          violations: this.performanceMetrics.violations.faissSlaViolations
        },
        zero_fallback_requirement: {
          threshold: 0,
          actual: this.performanceMetrics.faiss.fallbackCount,
          compliant: this.performanceMetrics.faiss.fallbackCount === 0,
          violations: this.performanceMetrics.violations.fallbackUsageDetected
        },
        error_rate_requirement: {
          threshold: this.slaThresholds.errorRate,
          actual: this.performanceMetrics.api.failures / this.performanceMetrics.api.requests,
          compliant: (this.performanceMetrics.api.failures / this.performanceMetrics.api.requests) <= this.slaThresholds.errorRate,
          violations: this.performanceMetrics.violations.errorRateViolations
        }
      },
      test2_requirements_validation: {
        all_requirements_met: this.allTEST2RequirementsMet(),
        detailed_validation: this.getTEST2ValidationDetails()
      }
    };
  }

  /**
   * Print summary to console
   */
  printSummary() {
    console.log(`📈 Requests: ${this.performanceMetrics.api.requests} (${this.performanceMetrics.api.successes} success, ${this.performanceMetrics.api.failures} failed)`);
    console.log(`⏱️  API P95: ${this.performanceMetrics.api.p95.toFixed(2)}ms (limit: ${this.slaThresholds.apiResponseTimeMs}ms)`);
    console.log(`🔍 FAISS P95: ${this.performanceMetrics.faiss.p95.toFixed(3)}ms (limit: ${this.slaThresholds.faissSearchTimeMs}ms)`);
    console.log(`🚫 Fallback count: ${this.performanceMetrics.faiss.fallbackCount} (required: 0)`);
    console.log(`💾 Peak memory: ${this.performanceMetrics.system.peakMemory.toFixed(2)}MB`);
  }

  /**
   * Check if all TEST2 requirements are met
   */
  allTEST2RequirementsMet() {
    return this.performanceMetrics.api.p95 <= this.slaThresholds.apiResponseTimeMs &&
           this.performanceMetrics.faiss.p95 <= this.slaThresholds.faissSearchTimeMs &&
           this.performanceMetrics.faiss.fallbackCount === 0 &&
           (this.performanceMetrics.api.failures / this.performanceMetrics.api.requests) <= this.slaThresholds.errorRate;
  }

  /**
   * Get detailed TEST2 validation results
   */
  getTEST2ValidationDetails() {
    return {
      api_p95_under_150ms: {
        met: this.performanceMetrics.api.p95 <= 150,
        actual: this.performanceMetrics.api.p95,
        target: 150
      },
      faiss_p95_under_1ms: {
        met: this.performanceMetrics.faiss.p95 <= 1.0,
        actual: this.performanceMetrics.faiss.p95,
        target: 1.0
      },
      zero_fallback_usage: {
        met: this.performanceMetrics.faiss.fallbackCount === 0,
        actual: this.performanceMetrics.faiss.fallbackCount,
        target: 0
      },
      all_faiss_data_source: {
        met: this.performanceMetrics.faiss.nonFaissDataSourceCount === 0,
        actual: this.performanceMetrics.faiss.nonFaissDataSourceCount,
        target: 0
      }
    };
  }

  /**
   * Validate and report TEST2 requirements compliance
   */
  validateTEST2Requirements() {
    console.log('\n=== TEST2 Requirements Validation ===');
    
    const allMet = this.allTEST2RequirementsMet();
    const details = this.getTEST2ValidationDetails();
    
    console.log(`✅ API p95 < 150ms: ${details.api_p95_under_150ms.met ? 'PASS' : 'FAIL'} (${details.api_p95_under_150ms.actual.toFixed(2)}ms)`);
    console.log(`✅ FAISS p95 < 1ms: ${details.faiss_p95_under_1ms.met ? 'PASS' : 'FAIL'} (${details.faiss_p95_under_1ms.actual.toFixed(3)}ms)`);
    console.log(`✅ Zero fallback usage: ${details.zero_fallback_usage.met ? 'PASS' : 'FAIL'} (${details.zero_fallback_usage.actual} fallbacks)`);
    console.log(`✅ All FAISS data source: ${details.all_faiss_data_source.met ? 'PASS' : 'FAIL'} (${details.all_faiss_data_source.actual} non-FAISS)`);
    
    if (allMet) {
      console.log('\n🎉 ALL TEST2 REQUIREMENTS MET! 🎉');
    } else {
      console.log('\n❌ TEST2 REQUIREMENTS NOT MET - Review violations above');
      process.exit(1);
    }
  }

  /**
   * Format duration in human-readable format
   */
  formatDuration(ms) {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    } else {
      return `${seconds}s`;
    }
  }
}

// Artillery.js processor interface
const processor = new TEST2PerformanceProcessor();

module.exports = {
  beforeScenario: (scenario, ee) => processor.beforeScenario(scenario, ee),
  beforeRequest: (req, context) => processor.beforeRequest(req, context),
  afterResponse: (req, res, context, ee) => processor.afterResponse(req, res, context, ee),
  afterScenario: (scenario, ee) => processor.afterScenario(scenario, ee)
};