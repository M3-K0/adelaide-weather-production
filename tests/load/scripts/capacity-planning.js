#!/usr/bin/env node

/**
 * Automated Capacity Planning Analysis
 * 
 * Systematically tests system capacity limits, identifies bottlenecks,
 * and provides scaling recommendations for the Adelaide Weather 
 * Forecasting System under various load conditions.
 */

const fs = require('fs').promises;
const path = require('path');
const { spawn, exec } = require('child_process');
const { promisify } = require('util');

const execAsync = promisify(exec);

// Capacity testing scenarios
const CAPACITY_SCENARIOS = {
  'baseline': {
    name: 'Baseline Capacity',
    users: 10,
    duration: 300, // 5 minutes
    ramp_time: 60,
    description: 'Normal operating conditions'
  },
  'target_load': {
    name: 'Target Load Capacity',
    users: 50,
    duration: 600, // 10 minutes
    ramp_time: 120,
    description: 'Expected peak usage'
  },
  'stress_test': {
    name: 'Stress Test Capacity',
    users: 100,
    duration: 300, // 5 minutes
    ramp_time: 60,
    description: 'High demand periods'
  },
  'spike_test': {
    name: 'Spike Load Capacity',
    users: 200,
    duration: 180, // 3 minutes
    ramp_time: 30,
    description: 'Severe weather event spikes'
  },
  'break_point': {
    name: 'Break Point Analysis',
    users: 500,
    duration: 120, // 2 minutes
    ramp_time: 30,
    description: 'System failure threshold detection'
  },
  'sustained_load': {
    name: 'Sustained Load Capacity',
    users: 75,
    duration: 1800, // 30 minutes
    ramp_time: 300,
    description: 'Long-term stability testing'
  }
};

// Resource monitoring metrics
const RESOURCE_METRICS = [
  'cpu_usage_percent',
  'memory_usage_percent', 
  'disk_io_rate',
  'network_throughput',
  'response_time_p95',
  'error_rate',
  'cache_hit_rate',
  'database_connections',
  'thread_pool_usage'
];

class CapacityPlanningAnalyzer {
  constructor(config = {}) {
    this.config = {
      base_url: config.base_url || 'http://localhost:8000',
      frontend_url: config.frontend_url || 'http://localhost:3000',
      api_token: config.api_token || 'dev-token-change-in-production',
      report_dir: config.report_dir || './tests/load/reports',
      monitoring_enabled: config.monitoring_enabled !== false,
      prometheus_url: config.prometheus_url || 'http://localhost:9090',
      auto_scaling_test: config.auto_scaling_test || false,
      resource_monitoring: config.resource_monitoring !== false,
      parallel_scenarios: config.parallel_scenarios || false,
      ...config
    };
    
    this.results = {
      start_time: new Date(),
      scenarios: {},
      capacity_analysis: {},
      bottlenecks: [],
      scaling_recommendations: [],
      cost_analysis: {}
    };
    
    this.system_baseline = null;
  }

  /**
   * Run complete capacity planning analysis
   */
  async runCapacityAnalysis() {
    console.log('📊 Starting Automated Capacity Planning Analysis');
    console.log(`🎯 Testing ${Object.keys(CAPACITY_SCENARIOS).length} capacity scenarios`);
    console.log(`📈 Monitoring: ${this.config.monitoring_enabled ? 'Enabled' : 'Disabled'}`);
    
    try {
      // Prepare environment and establish baseline
      await this.prepareEnvironment();
      await this.establishBaseline();
      
      // Run capacity scenarios
      if (this.config.parallel_scenarios) {
        await this.runParallelScenarios();
      } else {
        await this.runSequentialScenarios();
      }
      
      // Analyze results and generate recommendations
      await this.analyzeCapacityResults();
      await this.identifyBottlenecks();
      await this.generateScalingRecommendations();
      await this.performCostAnalysis();
      
      // Generate comprehensive report
      await this.generateCapacityReport();
      
      console.log('✅ Capacity planning analysis completed successfully');
      
    } catch (error) {
      console.error('❌ Capacity planning analysis failed:', error.message);
      throw error;
    }
  }

  /**
   * Prepare test environment and validate systems
   */
  async prepareEnvironment() {
    console.log('🔧 Preparing capacity testing environment...');
    
    // Create reports directory
    await fs.mkdir(this.config.report_dir, { recursive: true });
    
    // Validate endpoints
    await this.validateEndpoints();
    
    // Setup monitoring if enabled
    if (this.config.monitoring_enabled) {
      await this.setupMonitoring();
    }
    
    // Check available tools
    await this.checkToolAvailability();
    
    console.log('✅ Environment preparation completed');
  }

  /**
   * Validate API and frontend endpoints
   */
  async validateEndpoints() {
    // API validation
    try {
      const { stdout } = await execAsync(
        `curl -s -H "Authorization: Bearer ${this.config.api_token}" "${this.config.base_url}/health"`
      );
      
      const health = JSON.parse(stdout);
      if (!health.ready) {
        throw new Error('API not ready');
      }
      
      console.log('✅ API endpoint validated and ready');
    } catch (error) {
      throw new Error(`API validation failed: ${error.message}`);
    }
    
    // Frontend validation
    try {
      const { stdout } = await execAsync(
        `curl -s -o /dev/null -w "%{http_code}" "${this.config.frontend_url}/"`
      );
      
      if (stdout.trim() !== '200') {
        throw new Error(`Frontend returned HTTP ${stdout.trim()}`);
      }
      
      console.log('✅ Frontend endpoint validated');
    } catch (error) {
      console.warn(`⚠️  Frontend validation failed: ${error.message}`);
    }
  }

  /**
   * Setup monitoring integration
   */
  async setupMonitoring() {
    console.log('📊 Setting up resource monitoring...');
    
    try {
      // Test Prometheus connection
      const { stdout } = await execAsync(
        `curl -s "${this.config.prometheus_url}/api/v1/query?query=up"`
      );
      
      const response = JSON.parse(stdout);
      if (response.status === 'success') {
        console.log('✅ Prometheus monitoring connected');
        this.monitoring_available = true;
      } else {
        throw new Error('Prometheus query failed');
      }
    } catch (error) {
      console.warn(`⚠️  Prometheus monitoring not available: ${error.message}`);
      this.monitoring_available = false;
    }
  }

  /**
   * Check availability of testing tools
   */
  async checkToolAvailability() {
    const tools = ['k6', 'artillery', 'curl', 'docker'];
    const available = {};
    
    for (const tool of tools) {
      try {
        await execAsync(`which ${tool}`);
        available[tool] = true;
        console.log(`✅ ${tool} available`);
      } catch (error) {
        available[tool] = false;
        console.warn(`⚠️  ${tool} not available`);
      }
    }
    
    this.tools_available = available;
    
    if (!available.k6 && !available.artillery) {
      throw new Error('No load testing tools available (k6 or artillery required)');
    }
  }

  /**
   * Establish system performance baseline
   */
  async establishBaseline() {
    console.log('📏 Establishing system performance baseline...');
    
    // Run minimal load test to establish baseline
    const baselineScenario = CAPACITY_SCENARIOS.baseline;
    
    console.log(`🔄 Running baseline test: ${baselineScenario.users} users for ${baselineScenario.duration}s`);
    
    const baselineResult = await this.runCapacityScenario('baseline', baselineScenario);
    
    this.system_baseline = {
      avg_response_time: baselineResult.metrics.avg_response_time,
      p95_response_time: baselineResult.metrics.p95_response_time,
      throughput: baselineResult.metrics.throughput,
      error_rate: baselineResult.metrics.error_rate,
      resource_usage: baselineResult.resource_metrics || {}
    };
    
    console.log('✅ Baseline established:');
    console.log(`   Response Time: ${this.system_baseline.avg_response_time}ms`);
    console.log(`   Throughput: ${this.system_baseline.throughput.toFixed(2)} req/s`);
    console.log(`   Error Rate: ${this.system_baseline.error_rate}%`);
  }

  /**
   * Run capacity scenarios sequentially
   */
  async runSequentialScenarios() {
    console.log('🔄 Running capacity scenarios sequentially...');
    
    // Skip baseline since it's already run
    const scenarios = Object.entries(CAPACITY_SCENARIOS).filter(([key]) => key !== 'baseline');
    
    for (const [scenarioId, scenario] of scenarios) {
      console.log(`\n🧪 Testing scenario: ${scenario.name}`);
      console.log(`   Users: ${scenario.users}, Duration: ${scenario.duration}s`);
      
      try {
        const result = await this.runCapacityScenario(scenarioId, scenario);
        this.results.scenarios[scenarioId] = result;
        
        console.log(`✅ ${scenario.name} completed`);
        
        // Analysis break between scenarios
        await this.analyzeScenarioResult(scenarioId, result);
        
        // Cool-down period
        console.log('😴 Cool-down period...');
        await this.sleep(60000); // 1 minute
        
      } catch (error) {
        console.error(`❌ ${scenario.name} failed:`, error.message);
        this.results.scenarios[scenarioId] = {
          success: false,
          error: error.message,
          scenario: scenario
        };
      }
    }
  }

  /**
   * Run capacity scenarios in parallel (for comparison)
   */
  async runParallelScenarios() {
    console.log('⚡ Running capacity scenarios in parallel...');
    
    // Note: Parallel execution is mainly for comparison of different approaches
    // In practice, capacity testing should be sequential to avoid interference
    
    const scenarios = Object.entries(CAPACITY_SCENARIOS).filter(([key]) => key !== 'baseline');
    const scenarioTests = scenarios.map(([scenarioId, scenario]) => 
      this.runCapacityScenario(scenarioId, scenario).catch(error => ({
        success: false,
        error: error.message,
        scenario: scenario
      }))
    );
    
    const results = await Promise.allSettled(scenarioTests);
    
    results.forEach((result, index) => {
      const [scenarioId] = scenarios[index];
      this.results.scenarios[scenarioId] = result.status === 'fulfilled' ? result.value : result.reason;
    });
  }

  /**
   * Run individual capacity testing scenario
   */
  async runCapacityScenario(scenarioId, scenario) {
    const startTime = Date.now();
    
    // Start resource monitoring if available
    let monitoringProcess = null;
    if (this.monitoring_available) {
      monitoringProcess = await this.startResourceMonitoring(scenarioId);
    }
    
    try {
      // Generate and run load test
      const loadTestResult = await this.executeLoadTest(scenarioId, scenario);
      
      // Collect resource metrics
      const resourceMetrics = this.monitoring_available ? 
        await this.collectResourceMetrics(scenarioId, startTime, Date.now()) : {};
      
      // Analyze auto-scaling if enabled
      const autoScalingMetrics = this.config.auto_scaling_test ? 
        await this.analyzeAutoScaling(scenarioId, scenario) : {};
      
      return {
        success: true,
        scenario: scenario,
        start_time: new Date(startTime).toISOString(),
        duration: Date.now() - startTime,
        metrics: loadTestResult,
        resource_metrics: resourceMetrics,
        auto_scaling: autoScalingMetrics
      };
      
    } finally {
      // Stop monitoring
      if (monitoringProcess) {
        await this.stopResourceMonitoring(monitoringProcess);
      }
    }
  }

  /**
   * Execute load test using available tools
   */
  async executeLoadTest(scenarioId, scenario) {
    if (this.tools_available.k6) {
      return await this.runK6LoadTest(scenarioId, scenario);
    } else if (this.tools_available.artillery) {
      return await this.runArtilleryLoadTest(scenarioId, scenario);
    } else {
      throw new Error('No load testing tools available');
    }
  }

  /**
   * Run K6 load test for capacity scenario
   */
  async runK6LoadTest(scenarioId, scenario) {
    const k6Script = this.generateCapacityK6Script(scenario);
    const scriptPath = path.join(this.config.report_dir, `${scenarioId}-capacity-test.js`);
    const reportPath = path.join(this.config.report_dir, `${scenarioId}-results.json`);
    
    await fs.writeFile(scriptPath, k6Script);
    
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
          SCENARIO_ID: scenarioId
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
            const metrics = await this.parseK6CapacityResults(reportPath);
            resolve(metrics);
          } catch (error) {
            reject(new Error(`Failed to parse K6 results: ${error.message}`));
          }
        } else {
          reject(new Error(`K6 failed with code ${code}: ${stderr}`));
        }
      });
    });
  }

  /**
   * Generate K6 script for capacity testing
   */
  generateCapacityK6Script(scenario) {
    return `
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Capacity-focused metrics
const responseTime = new Trend('response_time');
const errorRate = new Rate('error_rate');
const throughput = new Counter('total_requests');

export const options = {
  stages: [
    { duration: '${scenario.ramp_time}s', target: ${scenario.users} },
    { duration: '${scenario.duration - scenario.ramp_time}s', target: ${scenario.users} },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    'response_time': ['p(95)<5000'], // Lenient for capacity testing
    'error_rate': ['rate<0.1'],      // Allow higher error rate for break point testing
  },
};

const config = {
  api_base: __ENV.API_BASE,
  frontend_base: __ENV.FRONTEND_BASE,
  api_token: __ENV.API_TOKEN,
};

export default function() {
  // Primary API load pattern for capacity testing
  const response = http.get(config.api_base + '/forecast', {
    headers: { 'Authorization': 'Bearer ' + config.api_token },
    params: {
      horizon: ['6h', '12h', '24h', '48h'][Math.floor(Math.random() * 4)],
      vars: 't2m,u10,v10,msl,cape'
    }
  });

  const success = check(response, {
    'status is 200': (r) => r.status === 200,
    'response time under 10s': (r) => r.timings.duration < 10000,
  });

  responseTime.add(response.timings.duration);
  errorRate.add(!success);
  throughput.add(1);

  // Minimal think time for capacity testing
  sleep(0.5 + Math.random() * 0.5);
}
`;
  }

  /**
   * Parse K6 results for capacity analysis
   */
  async parseK6CapacityResults(reportPath) {
    const data = await fs.readFile(reportPath, 'utf8');
    const lines = data.trim().split('\n').filter(line => line.trim());
    
    const metrics = {
      total_requests: 0,
      successful_requests: 0,
      failed_requests: 0,
      avg_response_time: 0,
      p95_response_time: 0,
      p99_response_time: 0,
      min_response_time: Infinity,
      max_response_time: 0,
      throughput: 0,
      error_rate: 0
    };
    
    const responseTimes = [];
    
    for (const line of lines) {
      try {
        const entry = JSON.parse(line);
        
        if (entry.type === 'Point') {
          if (entry.metric === 'http_req_duration') {
            metrics.total_requests++;
            const duration = entry.data.value;
            responseTimes.push(duration);
            
            metrics.min_response_time = Math.min(metrics.min_response_time, duration);
            metrics.max_response_time = Math.max(metrics.max_response_time, duration);
          }
          
          if (entry.metric === 'http_req_failed') {
            if (entry.data.value === 1) {
              metrics.failed_requests++;
            } else {
              metrics.successful_requests++;
            }
          }
        }
      } catch (e) {
        continue;
      }
    }
    
    // Calculate derived metrics
    if (responseTimes.length > 0) {
      metrics.avg_response_time = responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length;
      
      const sorted = responseTimes.sort((a, b) => a - b);
      metrics.p95_response_time = sorted[Math.floor(sorted.length * 0.95)];
      metrics.p99_response_time = sorted[Math.floor(sorted.length * 0.99)];
    }
    
    metrics.error_rate = metrics.total_requests > 0 ? 
      (metrics.failed_requests / metrics.total_requests * 100) : 0;
    
    metrics.throughput = metrics.total_requests / 300; // Approximate duration
    
    return metrics;
  }

  /**
   * Start resource monitoring for scenario
   */
  async startResourceMonitoring(scenarioId) {
    if (!this.monitoring_available) return null;
    
    console.log(`📊 Starting resource monitoring for ${scenarioId}...`);
    
    // This would integrate with Prometheus/Grafana or system monitoring
    // For now, we'll simulate basic monitoring
    
    return {
      scenario_id: scenarioId,
      start_time: Date.now(),
      monitoring: true
    };
  }

  /**
   * Stop resource monitoring
   */
  async stopResourceMonitoring(monitoringProcess) {
    if (!monitoringProcess) return;
    
    console.log(`📊 Stopping resource monitoring for ${monitoringProcess.scenario_id}...`);
    
    // Stop monitoring process
    monitoringProcess.monitoring = false;
  }

  /**
   * Collect resource metrics during test
   */
  async collectResourceMetrics(scenarioId, startTime, endTime) {
    if (!this.monitoring_available) {
      return {};
    }
    
    try {
      // Query Prometheus for resource metrics during test period
      const duration = Math.floor((endTime - startTime) / 1000);
      const queries = {
        cpu_usage: 'rate(cpu_usage_seconds_total[5m]) * 100',
        memory_usage: 'memory_usage_bytes / memory_total_bytes * 100',
        response_time: 'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))',
        error_rate: 'rate(http_requests_total{status!~"2.."}[5m]) / rate(http_requests_total[5m]) * 100'
      };
      
      const metrics = {};
      
      for (const [name, query] of Object.entries(queries)) {
        try {
          const { stdout } = await execAsync(
            `curl -s "${this.config.prometheus_url}/api/v1/query?query=${encodeURIComponent(query)}"`
          );
          
          const response = JSON.parse(stdout);
          if (response.status === 'success' && response.data.result.length > 0) {
            metrics[name] = parseFloat(response.data.result[0].value[1]);
          }
        } catch (error) {
          console.warn(`⚠️  Failed to collect ${name} metric:`, error.message);
        }
      }
      
      return metrics;
      
    } catch (error) {
      console.warn(`⚠️  Resource metrics collection failed:`, error.message);
      return {};
    }
  }

  /**
   * Analyze scenario result immediately after completion
   */
  async analyzeScenarioResult(scenarioId, result) {
    console.log(`📊 Analyzing ${scenarioId} results...`);
    
    if (!result.success) {
      console.log(`❌ Scenario failed: ${result.error}`);
      return;
    }
    
    const metrics = result.metrics;
    const baseline = this.system_baseline;
    
    // Performance degradation analysis
    const responseTimeDegradation = ((metrics.avg_response_time - baseline.avg_response_time) / baseline.avg_response_time) * 100;
    const throughputChange = ((metrics.throughput - baseline.throughput) / baseline.throughput) * 100;
    const errorRateIncrease = metrics.error_rate - baseline.error_rate;
    
    console.log(`   Response Time: ${metrics.avg_response_time.toFixed(0)}ms (${responseTimeDegradation.toFixed(1)}% vs baseline)`);
    console.log(`   Throughput: ${metrics.throughput.toFixed(2)} req/s (${throughputChange.toFixed(1)}% vs baseline)`);
    console.log(`   Error Rate: ${metrics.error_rate.toFixed(2)}% (+${errorRateIncrease.toFixed(2)}% vs baseline)`);
    
    // Capacity threshold detection
    if (metrics.error_rate > 5) {
      console.log(`⚠️  HIGH ERROR RATE: System may be approaching capacity limit`);
    }
    
    if (responseTimeDegradation > 200) {
      console.log(`⚠️  PERFORMANCE DEGRADATION: Response time increased by ${responseTimeDegradation.toFixed(1)}%`);
    }
    
    if (metrics.p95_response_time > 5000) {
      console.log(`⚠️  SLA BREACH: P95 response time exceeds 5 seconds`);
    }
  }

  /**
   * Analyze capacity results and identify patterns
   */
  async analyzeCapacityResults() {
    console.log('🔍 Analyzing capacity test results...');
    
    const analysis = {
      performance_curve: [],
      capacity_limits: {},
      breaking_points: {},
      efficiency_metrics: {},
      scalability_assessment: {}
    };
    
    // Build performance curve
    for (const [scenarioId, result] of Object.entries(this.results.scenarios)) {
      if (result.success) {
        analysis.performance_curve.push({
          scenario: scenarioId,
          users: CAPACITY_SCENARIOS[scenarioId].users,
          response_time: result.metrics.avg_response_time,
          throughput: result.metrics.throughput,
          error_rate: result.metrics.error_rate,
          efficiency: result.metrics.throughput / CAPACITY_SCENARIOS[scenarioId].users
        });
      }
    }
    
    // Sort by user count for analysis
    analysis.performance_curve.sort((a, b) => a.users - b.users);
    
    // Identify capacity limits
    for (const point of analysis.performance_curve) {
      if (point.error_rate > 1) { // 1% error rate threshold
        analysis.capacity_limits.reliability = point.users;
        break;
      }
    }
    
    for (const point of analysis.performance_curve) {
      if (point.response_time > 2000) { // 2s response time threshold
        analysis.capacity_limits.performance = point.users;
        break;
      }
    }
    
    // Breaking point analysis
    const maxErrorRate = Math.max(...analysis.performance_curve.map(p => p.error_rate));
    const maxResponseTime = Math.max(...analysis.performance_curve.map(p => p.response_time));
    
    analysis.breaking_points = {
      max_error_rate: maxErrorRate,
      max_response_time: maxResponseTime,
      estimated_max_users: this.estimateMaxUsers(analysis.performance_curve)
    };
    
    // Efficiency analysis
    const efficiencies = analysis.performance_curve.map(p => p.efficiency);
    analysis.efficiency_metrics = {
      peak_efficiency: Math.max(...efficiencies),
      min_efficiency: Math.min(...efficiencies),
      efficiency_drop_threshold: this.findEfficiencyDropThreshold(analysis.performance_curve)
    };
    
    this.results.capacity_analysis = analysis;
  }

  /**
   * Estimate maximum user capacity
   */
  estimateMaxUsers(performanceCurve) {
    // Linear extrapolation based on error rate trend
    const validPoints = performanceCurve.filter(p => p.error_rate < 10);
    
    if (validPoints.length < 2) {
      return performanceCurve[performanceCurve.length - 1].users;
    }
    
    const lastTwo = validPoints.slice(-2);
    const errorRateSlope = (lastTwo[1].error_rate - lastTwo[0].error_rate) / 
                          (lastTwo[1].users - lastTwo[0].users);
    
    if (errorRateSlope <= 0) {
      return validPoints[validPoints.length - 1].users * 2; // Conservative estimate
    }
    
    // Extrapolate to 5% error rate
    const usersTo5PercentError = lastTwo[1].users + 
      (5 - lastTwo[1].error_rate) / errorRateSlope;
    
    return Math.max(usersTo5PercentError, validPoints[validPoints.length - 1].users);
  }

  /**
   * Find efficiency drop threshold
   */
  findEfficiencyDropThreshold(performanceCurve) {
    if (performanceCurve.length < 2) return null;
    
    let maxEfficiency = 0;
    let dropThreshold = null;
    
    for (const point of performanceCurve) {
      if (point.efficiency > maxEfficiency) {
        maxEfficiency = point.efficiency;
      } else if (point.efficiency < maxEfficiency * 0.8) { // 20% efficiency drop
        dropThreshold = point.users;
        break;
      }
    }
    
    return dropThreshold;
  }

  /**
   * Identify system bottlenecks
   */
  async identifyBottlenecks() {
    console.log('🔍 Identifying system bottlenecks...');
    
    const bottlenecks = [];
    const analysis = this.results.capacity_analysis;
    
    // Response time bottleneck
    if (analysis.capacity_limits.performance) {
      bottlenecks.push({
        type: 'performance',
        component: 'application',
        threshold: analysis.capacity_limits.performance,
        description: `Response time exceeds 2s at ${analysis.capacity_limits.performance} users`,
        severity: 'high',
        recommendation: 'Optimize application code, database queries, or add caching'
      });
    }
    
    // Error rate bottleneck
    if (analysis.capacity_limits.reliability) {
      bottlenecks.push({
        type: 'reliability',
        component: 'system',
        threshold: analysis.capacity_limits.reliability,
        description: `Error rate exceeds 1% at ${analysis.capacity_limits.reliability} users`,
        severity: 'critical',
        recommendation: 'Investigate error causes, improve error handling, or scale resources'
      });
    }
    
    // Efficiency bottleneck
    if (analysis.efficiency_metrics.efficiency_drop_threshold) {
      bottlenecks.push({
        type: 'efficiency',
        component: 'resource_utilization',
        threshold: analysis.efficiency_metrics.efficiency_drop_threshold,
        description: `Efficiency drops significantly at ${analysis.efficiency_metrics.efficiency_drop_threshold} users`,
        severity: 'medium',
        recommendation: 'Optimize resource allocation or implement auto-scaling'
      });
    }
    
    // Resource-based bottlenecks (if monitoring available)
    for (const [scenarioId, result] of Object.entries(this.results.scenarios)) {
      if (result.success && result.resource_metrics) {
        const resources = result.resource_metrics;
        
        if (resources.cpu_usage > 80) {
          bottlenecks.push({
            type: 'resource',
            component: 'cpu',
            threshold: CAPACITY_SCENARIOS[scenarioId].users,
            description: `CPU usage exceeds 80% at ${CAPACITY_SCENARIOS[scenarioId].users} users`,
            severity: 'high',
            recommendation: 'Scale CPU resources or optimize CPU-intensive operations'
          });
        }
        
        if (resources.memory_usage > 85) {
          bottlenecks.push({
            type: 'resource',
            component: 'memory',
            threshold: CAPACITY_SCENARIOS[scenarioId].users,
            description: `Memory usage exceeds 85% at ${CAPACITY_SCENARIOS[scenarioId].users} users`,
            severity: 'high',
            recommendation: 'Scale memory resources or optimize memory usage'
          });
        }
      }
    }
    
    this.results.bottlenecks = bottlenecks;
    
    console.log(`🔍 Identified ${bottlenecks.length} potential bottlenecks`);
    bottlenecks.forEach(bottleneck => {
      console.log(`   ${bottleneck.severity.toUpperCase()}: ${bottleneck.description}`);
    });
  }

  /**
   * Generate scaling recommendations
   */
  async generateScalingRecommendations() {
    console.log('📈 Generating scaling recommendations...');
    
    const recommendations = [];
    const analysis = this.results.capacity_analysis;
    const bottlenecks = this.results.bottlenecks;
    
    // Horizontal scaling recommendations
    const currentMaxUsers = Math.max(...analysis.performance_curve.map(p => p.users));
    const estimatedMaxUsers = analysis.breaking_points.estimated_max_users;
    
    if (estimatedMaxUsers > currentMaxUsers * 1.5) {
      recommendations.push({
        type: 'horizontal_scaling',
        priority: 'high',
        target_improvement: `Support up to ${Math.floor(estimatedMaxUsers)} concurrent users`,
        implementation: 'Add additional API server instances behind load balancer',
        estimated_cost_increase: '40-60%',
        complexity: 'medium'
      });
    }
    
    // Vertical scaling recommendations
    const criticalBottlenecks = bottlenecks.filter(b => b.severity === 'critical');
    if (criticalBottlenecks.length > 0) {
      recommendations.push({
        type: 'vertical_scaling',
        priority: 'critical',
        target_improvement: 'Resolve critical bottlenecks',
        implementation: 'Increase CPU and memory resources',
        estimated_cost_increase: '25-40%',
        complexity: 'low'
      });
    }
    
    // Caching recommendations
    const responseTimeIssues = bottlenecks.filter(b => b.type === 'performance');
    if (responseTimeIssues.length > 0) {
      recommendations.push({
        type: 'caching_optimization',
        priority: 'high',
        target_improvement: 'Reduce response times by 30-50%',
        implementation: 'Implement Redis caching layer and CDN',
        estimated_cost_increase: '15-25%',
        complexity: 'medium'
      });
    }
    
    // Database scaling recommendations
    if (analysis.capacity_limits.performance && analysis.capacity_limits.performance < 100) {
      recommendations.push({
        type: 'database_optimization',
        priority: 'medium',
        target_improvement: 'Improve query performance and reduce database load',
        implementation: 'Database query optimization, read replicas, connection pooling',
        estimated_cost_increase: '20-35%',
        complexity: 'high'
      });
    }
    
    // Auto-scaling recommendations
    recommendations.push({
      type: 'auto_scaling',
      priority: 'medium',
      target_improvement: 'Automatic resource adjustment based on demand',
      implementation: 'Implement container orchestration with auto-scaling policies',
      estimated_cost_increase: '10-20% (more efficient resource usage)',
      complexity: 'high'
    });
    
    this.results.scaling_recommendations = recommendations;
    
    console.log(`📈 Generated ${recommendations.length} scaling recommendations`);
    recommendations.forEach(rec => {
      console.log(`   ${rec.priority.toUpperCase()}: ${rec.type} - ${rec.target_improvement}`);
    });
  }

  /**
   * Perform cost analysis for scaling options
   */
  async performCostAnalysis() {
    console.log('💰 Performing cost analysis...');
    
    const baseCost = 1000; // Monthly base cost in USD
    const analysis = {};
    
    for (const recommendation of this.results.scaling_recommendations) {
      const costIncrease = this.parseCostIncrease(recommendation.estimated_cost_increase);
      
      analysis[recommendation.type] = {
        monthly_cost_increase: baseCost * costIncrease,
        implementation_cost: this.estimateImplementationCost(recommendation),
        roi_months: this.estimateROI(recommendation, costIncrease),
        cost_per_user: this.estimateCostPerUser(recommendation, costIncrease)
      };
    }
    
    this.results.cost_analysis = analysis;
  }

  /**
   * Parse cost increase percentage
   */
  parseCostIncrease(costString) {
    const match = costString.match(/(\d+)-(\d+)%/);
    if (match) {
      return (parseInt(match[1]) + parseInt(match[2])) / 200; // Average percentage as decimal
    }
    return 0.3; // Default 30%
  }

  /**
   * Estimate implementation cost
   */
  estimateImplementationCost(recommendation) {
    const costs = {
      'horizontal_scaling': 5000,
      'vertical_scaling': 2000,
      'caching_optimization': 8000,
      'database_optimization': 12000,
      'auto_scaling': 15000
    };
    
    return costs[recommendation.type] || 5000;
  }

  /**
   * Estimate ROI timeline
   */
  estimateROI(recommendation, costIncrease) {
    // Simplified ROI calculation based on user capacity improvement
    const complexityMultiplier = {
      'low': 1,
      'medium': 1.5,
      'high': 2
    };
    
    return Math.ceil(6 * complexityMultiplier[recommendation.complexity] * costIncrease);
  }

  /**
   * Estimate cost per additional user
   */
  estimateCostPerUser(recommendation, costIncrease) {
    const estimatedUserIncrease = 50; // Conservative estimate
    const monthlyCostIncrease = 1000 * costIncrease;
    
    return monthlyCostIncrease / estimatedUserIncrease;
  }

  /**
   * Generate comprehensive capacity planning report
   */
  async generateCapacityReport() {
    console.log('📋 Generating capacity planning report...');
    
    const report = {
      executive_summary: this.generateExecutiveSummary(),
      test_details: {
        start_time: this.results.start_time.toISOString(),
        end_time: new Date().toISOString(),
        scenarios_tested: Object.keys(CAPACITY_SCENARIOS).length,
        baseline: this.system_baseline
      },
      capacity_analysis: this.results.capacity_analysis,
      bottlenecks: this.results.bottlenecks,
      scaling_recommendations: this.results.scaling_recommendations,
      cost_analysis: this.results.cost_analysis,
      detailed_results: this.results.scenarios,
      action_plan: this.generateActionPlan()
    };
    
    // Save JSON report
    const jsonPath = path.join(this.config.report_dir, 'capacity-planning-report.json');
    await fs.writeFile(jsonPath, JSON.stringify(report, null, 2));
    
    // Generate markdown report
    const markdownReport = this.generateMarkdownCapacityReport(report);
    const mdPath = path.join(this.config.report_dir, 'capacity-planning-report.md');
    await fs.writeFile(mdPath, markdownReport);
    
    console.log(`📊 Capacity planning reports generated:`);
    console.log(`   JSON: ${jsonPath}`);
    console.log(`   Markdown: ${mdPath}`);
  }

  /**
   * Generate executive summary
   */
  generateExecutiveSummary() {
    const analysis = this.results.capacity_analysis;
    const bottlenecks = this.results.bottlenecks;
    
    const maxUsers = Math.max(...analysis.performance_curve.map(p => p.users));
    const criticalBottlenecks = bottlenecks.filter(b => b.severity === 'critical').length;
    const highBottlenecks = bottlenecks.filter(b => b.severity === 'high').length;
    
    return {
      current_capacity: `System tested up to ${maxUsers} concurrent users`,
      estimated_maximum: `Estimated maximum capacity: ${analysis.breaking_points.estimated_max_users} users`,
      critical_issues: criticalBottlenecks,
      high_priority_issues: highBottlenecks,
      primary_recommendation: this.results.scaling_recommendations[0]?.type || 'No scaling needed',
      investment_required: this.estimateTotalInvestment()
    };
  }

  /**
   * Estimate total investment required
   */
  estimateTotalInvestment() {
    const costs = Object.values(this.results.cost_analysis || {});
    const totalImplementation = costs.reduce((sum, cost) => sum + cost.implementation_cost, 0);
    const totalMonthly = costs.reduce((sum, cost) => sum + cost.monthly_cost_increase, 0);
    
    return {
      implementation: `$${totalImplementation.toLocaleString()}`,
      monthly_increase: `$${totalMonthly.toLocaleString()}`
    };
  }

  /**
   * Generate action plan
   */
  generateActionPlan() {
    const plan = [];
    
    // Immediate actions (critical bottlenecks)
    const criticalBottlenecks = this.results.bottlenecks.filter(b => b.severity === 'critical');
    if (criticalBottlenecks.length > 0) {
      plan.push({
        phase: 'immediate',
        timeline: '1-2 weeks',
        actions: criticalBottlenecks.map(b => b.recommendation),
        priority: 'critical'
      });
    }
    
    // Short-term actions (high priority recommendations)
    const highPriorityRecs = this.results.scaling_recommendations.filter(r => r.priority === 'high');
    if (highPriorityRecs.length > 0) {
      plan.push({
        phase: 'short_term',
        timeline: '1-3 months',
        actions: highPriorityRecs.map(r => r.implementation),
        priority: 'high'
      });
    }
    
    // Medium-term actions
    const mediumPriorityRecs = this.results.scaling_recommendations.filter(r => r.priority === 'medium');
    if (mediumPriorityRecs.length > 0) {
      plan.push({
        phase: 'medium_term',
        timeline: '3-6 months',
        actions: mediumPriorityRecs.map(r => r.implementation),
        priority: 'medium'
      });
    }
    
    return plan;
  }

  /**
   * Generate markdown capacity report
   */
  generateMarkdownCapacityReport(report) {
    return `# Capacity Planning Analysis Report

## Executive Summary

**Current Capacity**: ${report.executive_summary.current_capacity}
**Estimated Maximum**: ${report.executive_summary.estimated_maximum}
**Critical Issues**: ${report.executive_summary.critical_issues}
**High Priority Issues**: ${report.executive_summary.high_priority_issues}

**Investment Required**:
- Implementation: ${report.executive_summary.investment_required.implementation}
- Monthly Increase: ${report.executive_summary.investment_required.monthly_increase}

## Capacity Analysis

### Performance Curve
${report.capacity_analysis.performance_curve.map(point => 
`- **${point.users} users**: ${point.response_time.toFixed(0)}ms avg, ${point.throughput.toFixed(2)} req/s, ${point.error_rate.toFixed(2)}% errors`
).join('\n')}

### Capacity Limits
- **Performance Limit**: ${report.capacity_analysis.capacity_limits.performance || 'Not reached'} users
- **Reliability Limit**: ${report.capacity_analysis.capacity_limits.reliability || 'Not reached'} users

## Identified Bottlenecks

${report.bottlenecks.map(bottleneck => `
### ${bottleneck.type.toUpperCase()} - ${bottleneck.severity.toUpperCase()}
**Component**: ${bottleneck.component}
**Description**: ${bottleneck.description}
**Recommendation**: ${bottleneck.recommendation}
`).join('')}

## Scaling Recommendations

${report.scaling_recommendations.map(rec => `
### ${rec.type.replace('_', ' ').toUpperCase()} - ${rec.priority.toUpperCase()}
**Target**: ${rec.target_improvement}
**Implementation**: ${rec.implementation}
**Cost Impact**: ${rec.estimated_cost_increase}
**Complexity**: ${rec.complexity}
`).join('')}

## Action Plan

${report.action_plan.map(phase => `
### ${phase.phase.replace('_', ' ').toUpperCase()} (${phase.timeline})
**Priority**: ${phase.priority}
**Actions**:
${phase.actions.map(action => `- ${action}`).join('\n')}
`).join('')}

## Cost Analysis

${Object.entries(report.cost_analysis).map(([type, cost]) => `
### ${type.replace('_', ' ').toUpperCase()}
- **Monthly Cost Increase**: $${cost.monthly_cost_increase.toLocaleString()}
- **Implementation Cost**: $${cost.implementation_cost.toLocaleString()}
- **ROI Timeline**: ${cost.roi_months} months
- **Cost Per User**: $${cost.cost_per_user.toFixed(2)}/month
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
      if (!isNaN(value)) {
        config[key] = parseInt(value);
      } else if (value === 'true' || value === 'false') {
        config[key] = value === 'true';
      } else {
        config[key] = value;
      }
    }
  }
  
  const analyzer = new CapacityPlanningAnalyzer(config);
  
  analyzer.runCapacityAnalysis()
    .then(() => {
      console.log('🎉 Capacity planning analysis completed successfully');
      process.exit(0);
    })
    .catch((error) => {
      console.error('💥 Capacity planning analysis failed:', error.message);
      process.exit(1);
    });
}

module.exports = CapacityPlanningAnalyzer;