#!/usr/bin/env node

/**
 * Load Testing Utilities and Helpers
 * 
 * Comprehensive utility functions for load testing the Adelaide Weather
 * Forecasting System including test data generation, result analysis,
 * reporting, and test orchestration helpers.
 */

const fs = require('fs').promises;
const path = require('path');
const { spawn, exec } = require('child_process');
const { promisify } = require('util');

const execAsync = promisify(exec);

/**
 * Test Data Generator
 * Generates realistic test data for load testing scenarios
 */
class TestDataGenerator {
  constructor() {
    this.weatherVariables = [
      't2m', 'u10', 'v10', 'msl', 'z500', 't850', 'q850', 'u850', 'v850', 'cape'
    ];
    
    this.horizons = ['6h', '12h', '24h', '48h'];
    
    this.userProfiles = [
      'casual_user', 'power_user', 'meteorologist', 'mobile_user', 'api_consumer'
    ];
  }

  /**
   * Generate CSV test data for Artillery/K6
   */
  async generateCSVTestData(outputDir, recordCount = 1000) {
    console.log(`📊 Generating CSV test data (${recordCount} records)...`);
    
    // Variables combinations CSV
    const variablesData = [];
    for (let i = 0; i < recordCount; i++) {
      const variableCount = Math.floor(Math.random() * 5) + 1;
      const selectedVars = this.getRandomVariables(variableCount);
      const horizon = this.horizons[Math.floor(Math.random() * this.horizons.length)];
      
      variablesData.push({
        horizon: horizon,
        variables: selectedVars.join(','),
        variable_count: variableCount
      });
    }
    
    await this.writeCSV(
      path.join(outputDir, 'variables.csv'),
      variablesData
    );
    
    // User profiles CSV
    const userProfilesData = [];
    for (let i = 0; i < recordCount; i++) {
      const profile = this.userProfiles[Math.floor(Math.random() * this.userProfiles.length)];
      const sessionDuration = this.getSessionDuration(profile);
      const apiCallsPerSession = this.getAPICallsPerSession(profile);
      
      userProfilesData.push({
        profile: profile,
        session_duration: sessionDuration,
        api_calls_per_session: apiCallsPerSession,
        mobile_probability: this.getMobileProbability(profile),
        think_time_multiplier: this.getThinkTimeMultiplier(profile)
      });
    }
    
    await this.writeCSV(
      path.join(outputDir, 'user-profiles.csv'),
      userProfilesData
    );
    
    // API tokens CSV (for distributed testing)
    const tokensData = [];
    const baseToken = 'dev-token-change-in-production';
    for (let i = 0; i < Math.min(recordCount, 50); i++) {
      tokensData.push({
        token: baseToken,
        token_id: `token_${i}`,
        rate_limit: 60 // requests per minute
      });
    }
    
    await this.writeCSV(
      path.join(outputDir, 'tokens.csv'),
      tokensData
    );
    
    console.log('✅ CSV test data generated successfully');
  }

  /**
   * Generate JSON test data
   */
  async generateJSONTestData(outputDir) {
    console.log('📊 Generating JSON test data...');
    
    const testData = {
      scenarios: this.generateScenarioData(),
      user_journeys: this.generateUserJourneys(),
      network_conditions: this.generateNetworkConditions(),
      load_patterns: this.generateLoadPatterns(),
      api_test_cases: this.generateAPITestCases()
    };
    
    await fs.writeFile(
      path.join(outputDir, 'test-data.json'),
      JSON.stringify(testData, null, 2)
    );
    
    console.log('✅ JSON test data generated successfully');
  }

  /**
   * Get random weather variables
   */
  getRandomVariables(count) {
    const shuffled = [...this.weatherVariables].sort(() => 0.5 - Math.random());
    return shuffled.slice(0, count);
  }

  /**
   * Get session duration based on user profile
   */
  getSessionDuration(profile) {
    const durations = {
      'casual_user': () => 60 + Math.random() * 120, // 1-3 minutes
      'power_user': () => 300 + Math.random() * 300, // 5-10 minutes
      'meteorologist': () => 600 + Math.random() * 600, // 10-20 minutes
      'mobile_user': () => 30 + Math.random() * 90, // 0.5-2 minutes
      'api_consumer': () => 10 + Math.random() * 20  // 10-30 seconds
    };
    
    return Math.floor(durations[profile]());
  }

  /**
   * Get API calls per session based on profile
   */
  getAPICallsPerSession(profile) {
    const callCounts = {
      'casual_user': () => 2 + Math.random() * 4, // 2-6 calls
      'power_user': () => 8 + Math.random() * 8, // 8-16 calls
      'meteorologist': () => 15 + Math.random() * 10, // 15-25 calls
      'mobile_user': () => 1 + Math.random() * 3, // 1-4 calls
      'api_consumer': () => 5 + Math.random() * 10  // 5-15 calls
    };
    
    return Math.floor(callCounts[profile]());
  }

  /**
   * Get mobile probability based on profile
   */
  getMobileProbability(profile) {
    const probabilities = {
      'casual_user': 0.4,
      'power_user': 0.2,
      'meteorologist': 0.1,
      'mobile_user': 0.9,
      'api_consumer': 0.0
    };
    
    return probabilities[profile];
  }

  /**
   * Get think time multiplier
   */
  getThinkTimeMultiplier(profile) {
    const multipliers = {
      'casual_user': 1.0,
      'power_user': 1.5,
      'meteorologist': 2.0,
      'mobile_user': 0.7,
      'api_consumer': 0.1
    };
    
    return multipliers[profile];
  }

  /**
   * Generate scenario data
   */
  generateScenarioData() {
    return [
      {
        name: 'weather_dashboard_browsing',
        weight: 0.4,
        description: 'Users browsing weather dashboard',
        api_calls: ['forecast', 'health'],
        think_time_range: [2, 8]
      },
      {
        name: 'detailed_weather_analysis',
        weight: 0.3, 
        description: 'Power users doing detailed analysis',
        api_calls: ['forecast', 'forecast', 'forecast', 'metrics'],
        think_time_range: [5, 15]
      },
      {
        name: 'mobile_quick_check',
        weight: 0.2,
        description: 'Mobile users checking weather quickly',
        api_calls: ['forecast'],
        think_time_range: [1, 3]
      },
      {
        name: 'api_integration',
        weight: 0.1,
        description: 'Automated API consumers',
        api_calls: ['forecast', 'forecast', 'forecast'],
        think_time_range: [0.1, 0.5]
      }
    ];
  }

  /**
   * Generate user journey definitions
   */
  generateUserJourneys() {
    return {
      casual_browsing: {
        steps: [
          { action: 'visit_homepage', duration: 3 },
          { action: 'get_forecast', params: { horizon: '24h', vars: 't2m,u10,v10' } },
          { action: 'think', duration: 5 },
          { action: 'visit_demo_page', duration: 2 }
        ]
      },
      power_user_analysis: {
        steps: [
          { action: 'visit_analog_demo', duration: 2 },
          { action: 'get_detailed_forecast', params: { horizon: '48h', vars: 'all' } },
          { action: 'analyze_results', duration: 10 },
          { action: 'get_forecast', params: { horizon: '6h', vars: 't2m,cape' } },
          { action: 'think', duration: 8 },
          { action: 'visit_metrics_demo', duration: 5 }
        ]
      },
      mobile_check: {
        steps: [
          { action: 'visit_homepage_mobile', duration: 1 },
          { action: 'get_quick_forecast', params: { horizon: '6h', vars: 't2m,u10,v10' } },
          { action: 'quick_think', duration: 2 }
        ]
      }
    };
  }

  /**
   * Generate network condition definitions
   */
  generateNetworkConditions() {
    return {
      conditions: [
        { name: 'fiber', latency: 10, bandwidth: 1000, packet_loss: 0.01 },
        { name: 'broadband', latency: 50, bandwidth: 100, packet_loss: 0.1 },
        { name: 'mobile_4g', latency: 100, bandwidth: 50, packet_loss: 0.5 },
        { name: 'mobile_3g', latency: 200, bandwidth: 10, packet_loss: 1.0 },
        { name: 'satellite', latency: 600, bandwidth: 25, packet_loss: 2.0 }
      ],
      distribution: [
        { condition: 'fiber', probability: 0.2 },
        { condition: 'broadband', probability: 0.5 },
        { condition: 'mobile_4g', probability: 0.2 },
        { condition: 'mobile_3g', probability: 0.08 },
        { condition: 'satellite', probability: 0.02 }
      ]
    };
  }

  /**
   * Generate load patterns
   */
  generateLoadPatterns() {
    return {
      business_hours: {
        name: 'Business Hours Pattern',
        timeline: [
          { time: '06:00', load_factor: 0.1 },
          { time: '08:00', load_factor: 0.3 },
          { time: '10:00', load_factor: 0.6 },
          { time: '12:00', load_factor: 0.8 },
          { time: '14:00', load_factor: 1.0 },
          { time: '16:00', load_factor: 0.9 },
          { time: '18:00', load_factor: 0.7 },
          { time: '20:00', load_factor: 0.4 },
          { time: '22:00', load_factor: 0.2 }
        ]
      },
      severe_weather_spike: {
        name: 'Severe Weather Event',
        timeline: [
          { time: '00:00', load_factor: 0.2 },
          { time: '01:00', load_factor: 0.8 },
          { time: '02:00', load_factor: 2.0 },
          { time: '03:00', load_factor: 3.0 },
          { time: '04:00', load_factor: 2.5 },
          { time: '05:00', load_factor: 1.5 },
          { time: '06:00', load_factor: 1.0 }
        ]
      },
      seasonal_pattern: {
        name: 'Seasonal Usage Pattern',
        timeline: [
          { time: 'summer', load_factor: 1.5 },
          { time: 'autumn', load_factor: 1.0 },
          { time: 'winter', load_factor: 0.8 },
          { time: 'spring', load_factor: 1.2 }
        ]
      }
    };
  }

  /**
   * Generate API test cases
   */
  generateAPITestCases() {
    return {
      positive_cases: [
        {
          name: 'basic_forecast',
          endpoint: '/forecast',
          params: { horizon: '24h', vars: 't2m,u10,v10' },
          expected_status: 200,
          weight: 0.4
        },
        {
          name: 'detailed_forecast',
          endpoint: '/forecast',
          params: { horizon: '48h', vars: 't2m,u10,v10,msl,cape' },
          expected_status: 200,
          weight: 0.3
        },
        {
          name: 'quick_forecast',
          endpoint: '/forecast', 
          params: { horizon: '6h', vars: 't2m' },
          expected_status: 200,
          weight: 0.2
        },
        {
          name: 'health_check',
          endpoint: '/health',
          params: {},
          expected_status: 200,
          auth_required: false,
          weight: 0.1
        }
      ],
      negative_cases: [
        {
          name: 'invalid_horizon',
          endpoint: '/forecast',
          params: { horizon: 'invalid', vars: 't2m' },
          expected_status: 400,
          weight: 0.05
        },
        {
          name: 'invalid_variables',
          endpoint: '/forecast',
          params: { horizon: '24h', vars: 'invalid_var' },
          expected_status: 400,
          weight: 0.05
        },
        {
          name: 'missing_auth',
          endpoint: '/forecast',
          params: { horizon: '24h', vars: 't2m' },
          expected_status: 403,
          auth_required: false,
          weight: 0.02
        }
      ]
    };
  }

  /**
   * Write data to CSV file
   */
  async writeCSV(filePath, data) {
    if (data.length === 0) return;
    
    const headers = Object.keys(data[0]);
    const csvContent = [
      headers.join(','),
      ...data.map(row => 
        headers.map(header => 
          typeof row[header] === 'string' && row[header].includes(',') 
            ? `"${row[header]}"` 
            : row[header]
        ).join(',')
      )
    ].join('\n');
    
    await fs.writeFile(filePath, csvContent);
  }
}

/**
 * Test Result Analyzer
 * Analyzes and processes load test results
 */
class TestResultAnalyzer {
  constructor() {
    this.thresholds = {
      response_time_excellent: 500,
      response_time_good: 1000,
      response_time_acceptable: 2000,
      error_rate_excellent: 0.1,
      error_rate_good: 0.5,
      error_rate_acceptable: 1.0,
      throughput_minimum: 10
    };
  }

  /**
   * Analyze K6 JSON results
   */
  async analyzeK6Results(resultsFilePath) {
    console.log('📊 Analyzing K6 test results...');
    
    const rawData = await fs.readFile(resultsFilePath, 'utf8');
    const lines = rawData.trim().split('\n').filter(line => line.trim());
    
    const analysis = {
      summary: {},
      metrics: {},
      performance_grade: '',
      recommendations: [],
      timeline: []
    };
    
    const metrics = {
      response_times: [],
      error_count: 0,
      total_requests: 0,
      timestamps: []
    };
    
    // Parse K6 output
    for (const line of lines) {
      try {
        const entry = JSON.parse(line);
        
        if (entry.type === 'Point') {
          if (entry.metric === 'http_req_duration') {
            metrics.response_times.push(entry.data.value);
            metrics.timestamps.push(new Date(entry.data.time));
            metrics.total_requests++;
          }
          
          if (entry.metric === 'http_req_failed' && entry.data.value === 1) {
            metrics.error_count++;
          }
        }
      } catch (e) {
        continue;
      }
    }
    
    // Calculate summary metrics
    if (metrics.response_times.length > 0) {
      const sorted = metrics.response_times.sort((a, b) => a - b);
      
      analysis.summary = {
        total_requests: metrics.total_requests,
        error_count: metrics.error_count,
        error_rate: (metrics.error_count / metrics.total_requests * 100).toFixed(2),
        avg_response_time: (metrics.response_times.reduce((a, b) => a + b, 0) / metrics.response_times.length).toFixed(0),
        min_response_time: Math.min(...metrics.response_times).toFixed(0),
        max_response_time: Math.max(...metrics.response_times).toFixed(0),
        p50_response_time: sorted[Math.floor(sorted.length * 0.5)].toFixed(0),
        p95_response_time: sorted[Math.floor(sorted.length * 0.95)].toFixed(0),
        p99_response_time: sorted[Math.floor(sorted.length * 0.99)].toFixed(0)
      };
      
      // Calculate throughput
      const testDuration = this.calculateTestDuration(metrics.timestamps);
      analysis.summary.throughput = (metrics.total_requests / testDuration).toFixed(2);
      analysis.summary.test_duration = testDuration.toFixed(0);
    }
    
    // Performance grading
    analysis.performance_grade = this.calculatePerformanceGrade(analysis.summary);
    
    // Generate recommendations
    analysis.recommendations = this.generateRecommendations(analysis.summary);
    
    // Timeline analysis
    analysis.timeline = this.generateTimeline(metrics);
    
    return analysis;
  }

  /**
   * Analyze Artillery results
   */
  async analyzeArtilleryResults(resultsFilePath) {
    console.log('📊 Analyzing Artillery test results...');
    
    try {
      const rawData = await fs.readFile(resultsFilePath, 'utf8');
      const results = JSON.parse(rawData);
      
      const analysis = {
        summary: this.extractArtillerySummary(results),
        performance_grade: '',
        recommendations: [],
        detailed_metrics: results
      };
      
      analysis.performance_grade = this.calculatePerformanceGrade(analysis.summary);
      analysis.recommendations = this.generateRecommendations(analysis.summary);
      
      return analysis;
      
    } catch (error) {
      throw new Error(`Failed to analyze Artillery results: ${error.message}`);
    }
  }

  /**
   * Extract summary from Artillery results
   */
  extractArtillerySummary(results) {
    const summary = results.aggregate || {};
    
    return {
      total_requests: summary.requestsCompleted || 0,
      error_count: summary.errors || 0,
      error_rate: summary.errors && summary.requestsCompleted ? 
        (summary.errors / summary.requestsCompleted * 100).toFixed(2) : '0',
      avg_response_time: summary.latency?.mean || 0,
      min_response_time: summary.latency?.min || 0,
      max_response_time: summary.latency?.max || 0,
      p50_response_time: summary.latency?.p50 || 0,
      p95_response_time: summary.latency?.p95 || 0,
      p99_response_time: summary.latency?.p99 || 0,
      throughput: summary.rps?.mean || 0,
      test_duration: summary.scenarioDuration || 0
    };
  }

  /**
   * Calculate test duration from timestamps
   */
  calculateTestDuration(timestamps) {
    if (timestamps.length < 2) return 1;
    
    const start = Math.min(...timestamps.map(t => t.getTime()));
    const end = Math.max(...timestamps.map(t => t.getTime()));
    
    return (end - start) / 1000; // Convert to seconds
  }

  /**
   * Calculate performance grade
   */
  calculatePerformanceGrade(summary) {
    const responseTime = parseFloat(summary.avg_response_time);
    const errorRate = parseFloat(summary.error_rate);
    const throughput = parseFloat(summary.throughput);
    
    let score = 100;
    
    // Response time scoring
    if (responseTime > this.thresholds.response_time_acceptable) {
      score -= 40;
    } else if (responseTime > this.thresholds.response_time_good) {
      score -= 20;
    } else if (responseTime > this.thresholds.response_time_excellent) {
      score -= 10;
    }
    
    // Error rate scoring
    if (errorRate > this.thresholds.error_rate_acceptable) {
      score -= 30;
    } else if (errorRate > this.thresholds.error_rate_good) {
      score -= 15;
    } else if (errorRate > this.thresholds.error_rate_excellent) {
      score -= 5;
    }
    
    // Throughput scoring
    if (throughput < this.thresholds.throughput_minimum) {
      score -= 20;
    }
    
    // Grade assignment
    if (score >= 90) return 'A';
    if (score >= 80) return 'B';
    if (score >= 70) return 'C';
    if (score >= 60) return 'D';
    return 'F';
  }

  /**
   * Generate performance recommendations
   */
  generateRecommendations(summary) {
    const recommendations = [];
    const responseTime = parseFloat(summary.avg_response_time);
    const errorRate = parseFloat(summary.error_rate);
    const throughput = parseFloat(summary.throughput);
    
    if (responseTime > this.thresholds.response_time_acceptable) {
      recommendations.push({
        category: 'performance',
        priority: 'high',
        issue: `High response time: ${responseTime}ms`,
        recommendation: 'Optimize database queries, implement caching, or scale resources'
      });
    }
    
    if (errorRate > this.thresholds.error_rate_acceptable) {
      recommendations.push({
        category: 'reliability',
        priority: 'critical',
        issue: `High error rate: ${errorRate}%`,
        recommendation: 'Investigate error causes and improve error handling'
      });
    }
    
    if (throughput < this.thresholds.throughput_minimum) {
      recommendations.push({
        category: 'capacity',
        priority: 'medium',
        issue: `Low throughput: ${throughput} req/s`,
        recommendation: 'Scale application instances or optimize request processing'
      });
    }
    
    if (responseTime > this.thresholds.response_time_good && errorRate < this.thresholds.error_rate_good) {
      recommendations.push({
        category: 'optimization',
        priority: 'medium',
        issue: 'Response time could be improved',
        recommendation: 'Implement response caching and optimize critical code paths'
      });
    }
    
    return recommendations;
  }

  /**
   * Generate timeline analysis
   */
  generateTimeline(metrics) {
    if (metrics.timestamps.length === 0) return [];
    
    // Group by time windows (e.g., 30-second intervals)
    const windowSize = 30000; // 30 seconds in milliseconds
    const windows = new Map();
    
    metrics.timestamps.forEach((timestamp, index) => {
      const windowStart = Math.floor(timestamp.getTime() / windowSize) * windowSize;
      
      if (!windows.has(windowStart)) {
        windows.set(windowStart, {
          timestamp: new Date(windowStart),
          response_times: [],
          request_count: 0
        });
      }
      
      const window = windows.get(windowStart);
      window.response_times.push(metrics.response_times[index]);
      window.request_count++;
    });
    
    // Convert to timeline array
    return Array.from(windows.values()).map(window => ({
      timestamp: window.timestamp.toISOString(),
      avg_response_time: window.response_times.reduce((a, b) => a + b, 0) / window.response_times.length,
      request_count: window.request_count,
      throughput: window.request_count / (windowSize / 1000)
    }));
  }
}

/**
 * Load Test Orchestrator
 * Coordinates and manages multiple load tests
 */
class LoadTestOrchestrator {
  constructor(config = {}) {
    this.config = {
      parallel_tests: config.parallel_tests || false,
      cool_down_period: config.cool_down_period || 60, // seconds
      max_concurrent_tests: config.max_concurrent_tests || 3,
      results_dir: config.results_dir || './tests/load/reports',
      ...config
    };
    
    this.activeTests = new Map();
    this.testQueue = [];
    this.results = [];
  }

  /**
   * Add test to orchestration queue
   */
  addTest(testConfig) {
    const testId = `test_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    this.testQueue.push({
      id: testId,
      ...testConfig,
      status: 'queued',
      queued_at: new Date()
    });
    
    return testId;
  }

  /**
   * Execute all queued tests
   */
  async executeTests() {
    console.log(`🚀 Starting load test orchestration (${this.testQueue.length} tests)`);
    
    if (this.config.parallel_tests) {
      await this.executeTestsParallel();
    } else {
      await this.executeTestsSequential();
    }
    
    console.log('✅ Load test orchestration completed');
    
    return this.generateOrchestrationReport();
  }

  /**
   * Execute tests in parallel with concurrency limits
   */
  async executeTestsParallel() {
    const batches = this.createTestBatches();
    
    for (const batch of batches) {
      console.log(`⚡ Executing batch of ${batch.length} tests...`);
      
      const batchPromises = batch.map(test => this.executeTest(test));
      const batchResults = await Promise.allSettled(batchPromises);
      
      batchResults.forEach((result, index) => {
        const test = batch[index];
        if (result.status === 'fulfilled') {
          this.results.push(result.value);
        } else {
          console.error(`❌ Test ${test.id} failed:`, result.reason.message);
          this.results.push({
            test_id: test.id,
            success: false,
            error: result.reason.message
          });
        }
      });
      
      // Cool down between batches
      if (batches.indexOf(batch) < batches.length - 1) {
        console.log(`😴 Cool down period: ${this.config.cool_down_period}s`);
        await this.sleep(this.config.cool_down_period * 1000);
      }
    }
  }

  /**
   * Execute tests sequentially
   */
  async executeTestsSequential() {
    for (const test of this.testQueue) {
      console.log(`🔄 Executing test: ${test.name || test.id}`);
      
      try {
        const result = await this.executeTest(test);
        this.results.push(result);
        
        // Cool down between tests
        if (this.testQueue.indexOf(test) < this.testQueue.length - 1) {
          console.log(`😴 Cool down period: ${this.config.cool_down_period}s`);
          await this.sleep(this.config.cool_down_period * 1000);
        }
        
      } catch (error) {
        console.error(`❌ Test ${test.id} failed:`, error.message);
        this.results.push({
          test_id: test.id,
          success: false,
          error: error.message
        });
      }
    }
  }

  /**
   * Create test batches for parallel execution
   */
  createTestBatches() {
    const batches = [];
    const batchSize = this.config.max_concurrent_tests;
    
    for (let i = 0; i < this.testQueue.length; i += batchSize) {
      batches.push(this.testQueue.slice(i, i + batchSize));
    }
    
    return batches;
  }

  /**
   * Execute individual test
   */
  async executeTest(test) {
    test.status = 'running';
    test.started_at = new Date();
    this.activeTests.set(test.id, test);
    
    try {
      let result;
      
      if (test.tool === 'k6') {
        result = await this.executeK6Test(test);
      } else if (test.tool === 'artillery') {
        result = await this.executeArtilleryTest(test);
      } else {
        throw new Error(`Unsupported test tool: ${test.tool}`);
      }
      
      test.status = 'completed';
      test.completed_at = new Date();
      
      return {
        test_id: test.id,
        test_config: test,
        success: true,
        result: result
      };
      
    } catch (error) {
      test.status = 'failed';
      test.failed_at = new Date();
      test.error = error.message;
      
      throw error;
      
    } finally {
      this.activeTests.delete(test.id);
    }
  }

  /**
   * Execute K6 test
   */
  async executeK6Test(test) {
    const scriptPath = test.script_path;
    const outputPath = path.join(this.config.results_dir, `${test.id}-results.json`);
    
    return new Promise((resolve, reject) => {
      const k6Process = spawn('k6', [
        'run',
        '--out', `json=${outputPath}`,
        ...(test.k6_options || []),
        scriptPath
      ], {
        env: { ...process.env, ...test.env_vars }
      });
      
      let stdout = '';
      let stderr = '';
      
      k6Process.stdout.on('data', (data) => {
        stdout += data.toString();
      });
      
      k6Process.stderr.on('data', (data) => {
        stderr += data.toString();
      });
      
      k6Process.on('close', (code) => {
        if (code === 0) {
          resolve({
            tool: 'k6',
            output_file: outputPath,
            stdout: stdout,
            exit_code: code
          });
        } else {
          reject(new Error(`K6 failed with code ${code}: ${stderr}`));
        }
      });
    });
  }

  /**
   * Execute Artillery test
   */
  async executeArtilleryTest(test) {
    const configPath = test.config_path;
    const outputPath = path.join(this.config.results_dir, `${test.id}-results.json`);
    
    return new Promise((resolve, reject) => {
      const artilleryProcess = spawn('artillery', [
        'run',
        '--output', outputPath,
        ...(test.artillery_options || []),
        configPath
      ], {
        env: { ...process.env, ...test.env_vars }
      });
      
      let stdout = '';
      let stderr = '';
      
      artilleryProcess.stdout.on('data', (data) => {
        stdout += data.toString();
      });
      
      artilleryProcess.stderr.on('data', (data) => {
        stderr += data.toString();
      });
      
      artilleryProcess.on('close', (code) => {
        if (code === 0) {
          resolve({
            tool: 'artillery',
            output_file: outputPath,
            stdout: stdout,
            exit_code: code
          });
        } else {
          reject(new Error(`Artillery failed with code ${code}: ${stderr}`));
        }
      });
    });
  }

  /**
   * Generate orchestration report
   */
  generateOrchestrationReport() {
    const successful = this.results.filter(r => r.success);
    const failed = this.results.filter(r => !r.success);
    
    return {
      summary: {
        total_tests: this.results.length,
        successful_tests: successful.length,
        failed_tests: failed.length,
        success_rate: ((successful.length / this.results.length) * 100).toFixed(1)
      },
      test_results: this.results,
      execution_timeline: this.generateExecutionTimeline(),
      recommendations: this.generateOrchestrationRecommendations()
    };
  }

  /**
   * Generate execution timeline
   */
  generateExecutionTimeline() {
    return this.testQueue.map(test => ({
      test_id: test.id,
      name: test.name || test.id,
      queued_at: test.queued_at,
      started_at: test.started_at,
      completed_at: test.completed_at || test.failed_at,
      status: test.status,
      duration: test.completed_at || test.failed_at ? 
        ((test.completed_at || test.failed_at) - test.started_at) / 1000 : null
    }));
  }

  /**
   * Generate orchestration recommendations
   */
  generateOrchestrationRecommendations() {
    const recommendations = [];
    const successful = this.results.filter(r => r.success);
    const failed = this.results.filter(r => !r.success);
    
    if (failed.length > successful.length * 0.2) {
      recommendations.push({
        category: 'reliability',
        priority: 'high',
        issue: `High test failure rate: ${failed.length}/${this.results.length}`,
        recommendation: 'Review test configurations and system stability'
      });
    }
    
    if (this.config.parallel_tests && failed.length > 0) {
      recommendations.push({
        category: 'optimization',
        priority: 'medium',
        issue: 'Some parallel tests failed',
        recommendation: 'Consider reducing concurrency or increasing cool-down periods'
      });
    }
    
    return recommendations;
  }

  /**
   * Utility function for delays
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// Export utility classes
module.exports = {
  TestDataGenerator,
  TestResultAnalyzer,
  LoadTestOrchestrator
};

// CLI interface for utilities
if (require.main === module) {
  const command = process.argv[2];
  
  switch (command) {
    case 'generate-data':
      const generator = new TestDataGenerator();
      const outputDir = process.argv[3] || './test-data';
      const recordCount = parseInt(process.argv[4]) || 1000;
      
      generator.generateCSVTestData(outputDir, recordCount)
        .then(() => generator.generateJSONTestData(outputDir))
        .then(() => console.log('✅ Test data generation completed'))
        .catch(error => {
          console.error('❌ Test data generation failed:', error.message);
          process.exit(1);
        });
      break;
      
    case 'analyze-results':
      const analyzer = new TestResultAnalyzer();
      const resultsFile = process.argv[3];
      const tool = process.argv[4] || 'k6';
      
      if (!resultsFile) {
        console.error('❌ Results file path required');
        process.exit(1);
      }
      
      const analyzeMethod = tool === 'artillery' ? 
        analyzer.analyzeArtilleryResults.bind(analyzer) :
        analyzer.analyzeK6Results.bind(analyzer);
      
      analyzeMethod(resultsFile)
        .then(analysis => {
          console.log(JSON.stringify(analysis, null, 2));
        })
        .catch(error => {
          console.error('❌ Results analysis failed:', error.message);
          process.exit(1);
        });
      break;
      
    default:
      console.log(`
Load Test Utilities

Usage:
  node load-test-helpers.js generate-data [output-dir] [record-count]
  node load-test-helpers.js analyze-results <results-file> [tool]

Commands:
  generate-data   Generate CSV and JSON test data
  analyze-results Analyze K6 or Artillery test results

Examples:
  node load-test-helpers.js generate-data ./test-data 1000
  node load-test-helpers.js analyze-results results.json k6
      `);
  }
}