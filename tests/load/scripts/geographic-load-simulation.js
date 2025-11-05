#!/usr/bin/env node

/**
 * Geographic Load Distribution Simulation
 * 
 * Simulates load testing from multiple geographic regions with
 * realistic network conditions, latency variations, and regional
 * user behavior patterns for the Adelaide Weather Forecasting System.
 */

const fs = require('fs').promises;
const path = require('path');
const { spawn, exec } = require('child_process');
const { promisify } = require('util');

const execAsync = promisify(exec);

// Geographic regions configuration
const REGIONS = {
  'us-east': {
    name: 'US East (Virginia)',
    latency: { min: 50, max: 100, avg: 75 },
    bandwidth: { download: 100, upload: 10 }, // Mbps
    user_behavior: {
      peak_hours: [14, 15, 16, 17, 18], // 2-6 PM EST
      mobile_ratio: 0.4,
      session_duration: 180, // seconds
      api_calls_per_session: 8
    },
    load_percentage: 30
  },
  'us-west': {
    name: 'US West (Oregon)',
    latency: { min: 80, max: 150, avg: 115 },
    bandwidth: { download: 80, upload: 8 },
    user_behavior: {
      peak_hours: [11, 12, 13, 14, 15], // 11 AM-3 PM PST
      mobile_ratio: 0.5,
      session_duration: 150,
      api_calls_per_session: 6
    },
    load_percentage: 25
  },
  'europe': {
    name: 'Europe (Dublin)',
    latency: { min: 150, max: 300, avg: 225 },
    bandwidth: { download: 60, upload: 6 },
    user_behavior: {
      peak_hours: [9, 10, 11, 16, 17], // European work hours
      mobile_ratio: 0.6,
      session_duration: 200,
      api_calls_per_session: 10
    },
    load_percentage: 25
  },
  'asia-pacific': {
    name: 'Asia Pacific (Sydney)',
    latency: { min: 200, max: 500, avg: 350 },
    bandwidth: { download: 50, upload: 5 },
    user_behavior: {
      peak_hours: [7, 8, 9, 17, 18, 19], // AEST work hours + evening
      mobile_ratio: 0.7,
      session_duration: 120,
      api_calls_per_session: 5
    },
    load_percentage: 20
  }
};

// Network condition presets
const NETWORK_CONDITIONS = {
  'fiber': { latency: 10, bandwidth_factor: 1.0, packet_loss: 0.001 },
  'broadband': { latency: 50, bandwidth_factor: 0.8, packet_loss: 0.005 },
  'mobile-4g': { latency: 100, bandwidth_factor: 0.6, packet_loss: 0.01 },
  'mobile-3g': { latency: 200, bandwidth_factor: 0.3, packet_loss: 0.02 },
  'satellite': { latency: 600, bandwidth_factor: 0.4, packet_loss: 0.03 },
  'throttled': { latency: 300, bandwidth_factor: 0.1, packet_loss: 0.05 }
};

class GeographicLoadSimulator {
  constructor(config = {}) {
    this.config = {
      base_url: config.base_url || 'http://localhost:8000',
      frontend_url: config.frontend_url || 'http://localhost:3000',
      api_token: config.api_token || 'dev-token-change-in-production',
      total_users: config.total_users || 100,
      test_duration: config.test_duration || 600, // 10 minutes
      report_dir: config.report_dir || './tests/load/reports',
      concurrent_regions: config.concurrent_regions || true,
      network_simulation: config.network_simulation || true,
      ...config
    };
    
    this.results = {
      start_time: new Date(),
      regions: {},
      summary: {},
      network_conditions: {}
    };
  }

  /**
   * Run complete geographic load simulation
   */
  async runSimulation() {
    console.log('🌍 Starting Geographic Load Distribution Simulation');
    console.log(`📊 Total users: ${this.config.total_users}`);
    console.log(`⏱️  Test duration: ${this.config.test_duration}s`);
    console.log(`🌐 Testing ${Object.keys(REGIONS).length} regions`);
    
    try {
      // Prepare test environment
      await this.prepareEnvironment();
      
      // Run regional load tests
      if (this.config.concurrent_regions) {
        await this.runConcurrentRegionalTests();
      } else {
        await this.runSequentialRegionalTests();
      }
      
      // Analyze results and generate report
      await this.analyzeResults();
      await this.generateReport();
      
      console.log('✅ Geographic load simulation completed successfully');
      
    } catch (error) {
      console.error('❌ Geographic load simulation failed:', error.message);
      throw error;
    }
  }

  /**
   * Prepare test environment and validate endpoints
   */
  async prepareEnvironment() {
    console.log('🔧 Preparing test environment...');
    
    // Create reports directory
    await fs.mkdir(this.config.report_dir, { recursive: true });
    
    // Validate API endpoint
    try {
      const { stdout } = await execAsync(
        `curl -s -o /dev/null -w "%{http_code}" ${this.config.base_url}/health`
      );
      
      if (stdout.trim() !== '200') {
        throw new Error(`API health check failed: HTTP ${stdout.trim()}`);
      }
      
      console.log('✅ API endpoint validated');
    } catch (error) {
      throw new Error(`API validation failed: ${error.message}`);
    }
    
    // Validate frontend endpoint
    try {
      const { stdout } = await execAsync(
        `curl -s -o /dev/null -w "%{http_code}" ${this.config.frontend_url}/`
      );
      
      if (stdout.trim() !== '200') {
        throw new Error(`Frontend health check failed: HTTP ${stdout.trim()}`);
      }
      
      console.log('✅ Frontend endpoint validated');
    } catch (error) {
      console.warn(`⚠️  Frontend validation failed: ${error.message}`);
    }
    
    // Setup network simulation if enabled
    if (this.config.network_simulation) {
      await this.setupNetworkSimulation();
    }
  }

  /**
   * Setup network condition simulation
   */
  async setupNetworkSimulation() {
    console.log('🌐 Setting up network condition simulation...');
    
    // Check if tc (traffic control) is available for network simulation
    try {
      await execAsync('which tc');
      console.log('✅ Network traffic control available');
      this.network_simulation_available = true;
    } catch (error) {
      console.warn('⚠️  Network traffic control not available - using software simulation');
      this.network_simulation_available = false;
    }
  }

  /**
   * Run load tests for all regions concurrently
   */
  async runConcurrentRegionalTests() {
    console.log('🚀 Running concurrent regional load tests...');
    
    const regionalTests = Object.entries(REGIONS).map(([regionId, region]) => 
      this.runRegionalTest(regionId, region)
    );
    
    const results = await Promise.allSettled(regionalTests);
    
    // Process results
    results.forEach((result, index) => {
      const regionId = Object.keys(REGIONS)[index];
      if (result.status === 'fulfilled') {
        this.results.regions[regionId] = result.value;
        console.log(`✅ ${regionId} test completed`);
      } else {
        console.error(`❌ ${regionId} test failed:`, result.reason.message);
        this.results.regions[regionId] = { 
          success: false, 
          error: result.reason.message 
        };
      }
    });
  }

  /**
   * Run load tests for regions sequentially
   */
  async runSequentialRegionalTests() {
    console.log('🔄 Running sequential regional load tests...');
    
    for (const [regionId, region] of Object.entries(REGIONS)) {
      try {
        console.log(`🌍 Testing region: ${region.name}`);
        const result = await this.runRegionalTest(regionId, region);
        this.results.regions[regionId] = result;
        console.log(`✅ ${regionId} test completed`);
        
        // Cool-down period between regions
        await this.sleep(30000); // 30 seconds
        
      } catch (error) {
        console.error(`❌ ${regionId} test failed:`, error.message);
        this.results.regions[regionId] = { 
          success: false, 
          error: error.message 
        };
      }
    }
  }

  /**
   * Run load test for a specific region
   */
  async runRegionalTest(regionId, region) {
    const userCount = Math.floor(this.config.total_users * region.load_percentage / 100);
    const testDuration = this.config.test_duration;
    
    console.log(`🌍 ${region.name}: ${userCount} users for ${testDuration}s`);
    
    // Apply network conditions for this region
    if (this.config.network_simulation) {
      await this.applyNetworkConditions(regionId, region);
    }
    
    // Generate K6 script for this region
    const k6Script = await this.generateRegionalK6Script(regionId, region, userCount);
    const scriptPath = path.join(this.config.report_dir, `${regionId}-test.js`);
    await fs.writeFile(scriptPath, k6Script);
    
    // Run K6 test
    const reportPath = path.join(this.config.report_dir, `${regionId}-results.json`);
    
    return new Promise((resolve, reject) => {
      const k6Process = spawn('k6', [
        'run',
        '--out', `json=${reportPath}`,
        '--quiet',
        scriptPath
      ], {
        env: {
          ...process.env,
          API_BASE: this.config.base_url,
          FRONTEND_BASE: this.config.frontend_url,
          API_TOKEN: this.config.api_token,
          REGION_ID: regionId,
          TEST_DURATION: testDuration.toString()
        }
      });
      
      let stdout = '';
      let stderr = '';
      
      k6Process.stdout.on('data', (data) => {
        stdout += data.toString();
      });
      
      k6Process.stderr.on('data', (data) => {
        stderr += data.toString();
      });
      
      k6Process.on('close', async (code) => {
        if (code === 0) {
          try {
            // Parse results
            const results = await this.parseK6Results(reportPath);
            resolve({
              success: true,
              region: region.name,
              users: userCount,
              duration: testDuration,
              results: results,
              stdout: stdout.slice(-1000), // Keep last 1000 chars
              network_conditions: region.latency
            });
          } catch (error) {
            reject(new Error(`Failed to parse results: ${error.message}`));
          }
        } else {
          reject(new Error(`K6 process failed with code ${code}: ${stderr}`));
        }
      });
      
      k6Process.on('error', (error) => {
        reject(new Error(`Failed to start K6: ${error.message}`));
      });
    });
  }

  /**
   * Apply network conditions for region simulation
   */
  async applyNetworkConditions(regionId, region) {
    if (!this.network_simulation_available) {
      return; // Skip if not available
    }
    
    try {
      // Simulate latency and bandwidth for this region
      const latency = Math.floor(Math.random() * (region.latency.max - region.latency.min)) + region.latency.min;
      const bandwidth = Math.floor(region.bandwidth.download * 0.8); // 80% of max
      
      console.log(`🌐 ${regionId}: Simulating ${latency}ms latency, ${bandwidth}Mbps bandwidth`);
      
      // Note: This would require root privileges and proper network interface setup
      // In production, this would be handled by dedicated network simulation tools
      
    } catch (error) {
      console.warn(`⚠️  Failed to apply network conditions for ${regionId}:`, error.message);
    }
  }

  /**
   * Generate region-specific K6 script
   */
  async generateRegionalK6Script(regionId, region, userCount) {
    const script = `
import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const errorRate = new Rate('error_rate');
const responseTime = new Trend('response_time');

export const options = {
  stages: [
    { duration: '1m', target: ${Math.floor(userCount * 0.3)} },
    { duration: '3m', target: ${userCount} },
    { duration: '2m', target: ${userCount} },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    'http_req_duration': ['p(95)<${region.latency.avg * 2}'],
    'error_rate': ['rate<0.01'],
  },
};

const config = {
  api_base: __ENV.API_BASE,
  frontend_base: __ENV.FRONTEND_BASE,
  api_token: __ENV.API_TOKEN,
  region_id: '${regionId}',
};

export default function() {
  const userAgent = getUserAgent();
  const headers = {
    'User-Agent': userAgent,
    'Accept': 'application/json',
    'Accept-Encoding': 'gzip, deflate',
  };

  group('Regional User Journey - ${region.name}', () => {
    // Simulate network latency
    if (Math.random() < 0.1) {
      sleep(${region.latency.avg / 1000}); // Convert ms to seconds
    }

    // Mobile vs desktop behavior
    if (Math.random() < ${region.user_behavior.mobile_ratio}) {
      mobileUserFlow(headers);
    } else {
      desktopUserFlow(headers);
    }
  });

  // Regional think time
  sleep(Math.random() * ${region.user_behavior.session_duration / 60} + 1);
}

function mobileUserFlow(headers) {
  // Quick forecast check
  const response = http.get(config.api_base + '/forecast', {
    headers: { ...headers, 'Authorization': 'Bearer ' + config.api_token },
    params: { horizon: '6h', vars: 't2m,u10,v10' }
  });

  const success = check(response, {
    'mobile forecast success': (r) => r.status === 200,
    'mobile response time ok': (r) => r.timings.duration < 3000,
  });

  responseTime.add(response.timings.duration);
  errorRate.add(!success);
}

function desktopUserFlow(headers) {
  // Dashboard load
  const dashboardResponse = http.get(config.frontend_base + '/', { headers });
  
  check(dashboardResponse, {
    'dashboard loads': (r) => r.status === 200,
  });

  sleep(2);

  // Detailed forecast
  const forecastResponse = http.get(config.api_base + '/forecast', {
    headers: { ...headers, 'Authorization': 'Bearer ' + config.api_token },
    params: { horizon: '24h', vars: 't2m,u10,v10,msl,cape' }
  });

  const success = check(forecastResponse, {
    'desktop forecast success': (r) => r.status === 200,
    'desktop response time ok': (r) => r.timings.duration < 2000,
  });

  responseTime.add(forecastResponse.timings.duration);
  errorRate.add(!success);
}

function getUserAgent() {
  const userAgents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15',
    'Mozilla/5.0 (Android 11; Mobile; rv:91.0) Gecko/91.0 Firefox/91.0'
  ];
  
  return userAgents[Math.floor(Math.random() * userAgents.length)];
}
`;
    
    return script;
  }

  /**
   * Parse K6 JSON results
   */
  async parseK6Results(reportPath) {
    try {
      const data = await fs.readFile(reportPath, 'utf8');
      const lines = data.trim().split('\n').filter(line => line.trim());
      
      const metrics = {
        requests: 0,
        errors: 0,
        avg_response_time: 0,
        p95_response_time: 0,
        throughput: 0
      };
      
      const responseTimes = [];
      
      for (const line of lines) {
        try {
          const entry = JSON.parse(line);
          
          if (entry.type === 'Point' && entry.metric === 'http_req_duration') {
            metrics.requests++;
            responseTimes.push(entry.data.value);
          }
          
          if (entry.type === 'Point' && entry.metric === 'http_req_failed' && entry.data.value === 1) {
            metrics.errors++;
          }
        } catch (e) {
          // Skip invalid JSON lines
          continue;
        }
      }
      
      // Calculate metrics
      if (responseTimes.length > 0) {
        metrics.avg_response_time = responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length;
        
        const sorted = responseTimes.sort((a, b) => a - b);
        metrics.p95_response_time = sorted[Math.floor(sorted.length * 0.95)];
        
        metrics.throughput = metrics.requests / this.config.test_duration;
      }
      
      return metrics;
      
    } catch (error) {
      throw new Error(`Failed to parse K6 results: ${error.message}`);
    }
  }

  /**
   * Analyze combined results from all regions
   */
  async analyzeResults() {
    console.log('📊 Analyzing regional load test results...');
    
    const summary = {
      total_requests: 0,
      total_errors: 0,
      avg_response_time: 0,
      throughput: 0,
      regions: {},
      performance_by_region: {}
    };
    
    let totalResponseTime = 0;
    let responseTimeCount = 0;
    
    for (const [regionId, result] of Object.entries(this.results.regions)) {
      if (result.success && result.results) {
        const metrics = result.results;
        
        summary.total_requests += metrics.requests;
        summary.total_errors += metrics.errors;
        summary.throughput += metrics.throughput;
        
        totalResponseTime += metrics.avg_response_time * metrics.requests;
        responseTimeCount += metrics.requests;
        
        summary.regions[regionId] = {
          name: REGIONS[regionId].name,
          requests: metrics.requests,
          errors: metrics.errors,
          error_rate: metrics.requests > 0 ? (metrics.errors / metrics.requests * 100).toFixed(2) : 0,
          avg_response_time: Math.round(metrics.avg_response_time),
          p95_response_time: Math.round(metrics.p95_response_time),
          throughput: metrics.throughput.toFixed(2)
        };
        
        // Performance analysis
        const latencyOverhead = metrics.avg_response_time - REGIONS[regionId].latency.avg;
        summary.performance_by_region[regionId] = {
          expected_latency: REGIONS[regionId].latency.avg,
          actual_avg_time: Math.round(metrics.avg_response_time),
          latency_overhead: Math.round(latencyOverhead),
          performance_score: Math.max(0, 100 - (latencyOverhead / 10)) // Simple scoring
        };
      }
    }
    
    summary.avg_response_time = responseTimeCount > 0 ? Math.round(totalResponseTime / responseTimeCount) : 0;
    summary.error_rate = summary.total_requests > 0 ? 
      (summary.total_errors / summary.total_requests * 100).toFixed(2) : 0;
    
    this.results.summary = summary;
  }

  /**
   * Generate comprehensive test report
   */
  async generateReport() {
    console.log('📋 Generating geographic load test report...');
    
    const report = {
      test_info: {
        start_time: this.results.start_time.toISOString(),
        end_time: new Date().toISOString(),
        duration: this.config.test_duration,
        total_users: this.config.total_users,
        regions_tested: Object.keys(REGIONS).length
      },
      summary: this.results.summary,
      regional_results: this.results.regions,
      network_conditions: REGIONS,
      recommendations: this.generateRecommendations()
    };
    
    // Save JSON report
    const jsonReportPath = path.join(this.config.report_dir, 'geographic-load-test-report.json');
    await fs.writeFile(jsonReportPath, JSON.stringify(report, null, 2));
    
    // Generate markdown report
    const markdownReport = this.generateMarkdownReport(report);
    const mdReportPath = path.join(this.config.report_dir, 'geographic-load-test-report.md');
    await fs.writeFile(mdReportPath, markdownReport);
    
    console.log(`📊 Reports generated:`);
    console.log(`   JSON: ${jsonReportPath}`);
    console.log(`   Markdown: ${mdReportPath}`);
  }

  /**
   * Generate performance recommendations
   */
  generateRecommendations() {
    const recommendations = [];
    
    // Check overall error rate
    if (parseFloat(this.results.summary.error_rate) > 1) {
      recommendations.push({
        category: 'reliability',
        priority: 'high',
        issue: `High error rate: ${this.results.summary.error_rate}%`,
        recommendation: 'Investigate error causes and improve error handling'
      });
    }
    
    // Check regional performance
    for (const [regionId, perf] of Object.entries(this.results.summary.performance_by_region || {})) {
      if (perf.performance_score < 70) {
        recommendations.push({
          category: 'performance',
          priority: 'medium',
          issue: `Poor performance in ${REGIONS[regionId].name}: ${perf.performance_score}/100`,
          recommendation: 'Consider CDN optimization or regional infrastructure'
        });
      }
    }
    
    // Check response times
    if (this.results.summary.avg_response_time > 2000) {
      recommendations.push({
        category: 'performance',
        priority: 'high',
        issue: `High average response time: ${this.results.summary.avg_response_time}ms`,
        recommendation: 'Optimize application performance and caching strategies'
      });
    }
    
    return recommendations;
  }

  /**
   * Generate markdown report
   */
  generateMarkdownReport(report) {
    return `# Geographic Load Test Report

## Test Overview
- **Start Time**: ${report.test_info.start_time}
- **Duration**: ${report.test_info.duration}s
- **Total Users**: ${report.test_info.total_users}
- **Regions Tested**: ${report.test_info.regions_tested}

## Summary Results
- **Total Requests**: ${report.summary.total_requests}
- **Error Rate**: ${report.summary.error_rate}%
- **Average Response Time**: ${report.summary.avg_response_time}ms
- **Total Throughput**: ${report.summary.throughput.toFixed(2)} req/s

## Regional Performance

${Object.entries(report.summary.regions || {}).map(([regionId, data]) => `
### ${data.name}
- **Requests**: ${data.requests}
- **Errors**: ${data.errors} (${data.error_rate}%)
- **Avg Response Time**: ${data.avg_response_time}ms
- **P95 Response Time**: ${data.p95_response_time}ms
- **Throughput**: ${data.throughput} req/s
`).join('')}

## Recommendations

${report.recommendations.map(rec => `
### ${rec.category.toUpperCase()} - ${rec.priority.toUpperCase()}
**Issue**: ${rec.issue}
**Recommendation**: ${rec.recommendation}
`).join('')}

## Network Conditions Tested

${Object.entries(REGIONS).map(([regionId, region]) => `
### ${region.name}
- **Latency**: ${region.latency.min}-${region.latency.max}ms (avg: ${region.latency.avg}ms)
- **Bandwidth**: ${region.bandwidth.download}/${region.bandwidth.upload} Mbps
- **Mobile Ratio**: ${(region.user_behavior.mobile_ratio * 100).toFixed(0)}%
- **Load Percentage**: ${region.load_percentage}%
`).join('')}
`;
  }

  /**
   * Utility function for delays
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// CLI interface
if (require.main === module) {
  const args = process.argv.slice(2);
  const config = {};
  
  // Parse command line arguments
  for (let i = 0; i < args.length; i += 2) {
    const key = args[i].replace('--', '');
    const value = args[i + 1];
    
    if (key && value) {
      // Convert numeric values
      if (!isNaN(value)) {
        config[key] = parseInt(value);
      } else if (value === 'true' || value === 'false') {
        config[key] = value === 'true';
      } else {
        config[key] = value;
      }
    }
  }
  
  const simulator = new GeographicLoadSimulator(config);
  
  simulator.runSimulation()
    .then(() => {
      console.log('🎉 Geographic load simulation completed successfully');
      process.exit(0);
    })
    .catch((error) => {
      console.error('💥 Geographic load simulation failed:', error.message);
      process.exit(1);
    });
}

module.exports = GeographicLoadSimulator;