/**
 * Frontend Load Testing with Browser Automation
 * Tests Next.js frontend performance under various load conditions
 * Measures Core Web Vitals and user interaction performance
 */

const { chromium } = require('playwright');
const { performance } = require('perf_hooks');

class FrontendLoadTester {
  constructor(options = {}) {
    this.baseUrl = options.baseUrl || 'http://localhost:3000';
    this.concurrency = options.concurrency || 10;
    this.duration = options.duration || 300; // 5 minutes default
    this.scenarios = options.scenarios || ['homepage', 'metrics', 'analog-demo', 'cape-demo'];
    this.results = {
      runs: [],
      metrics: {},
      errors: [],
      summary: {}
    };
  }

  async initialize() {
    console.log('🚀 Initializing Frontend Load Tester');
    console.log(`Target: ${this.baseUrl}`);
    console.log(`Concurrency: ${this.concurrency} users`);
    console.log(`Duration: ${this.duration} seconds`);
    
    // Verify frontend is accessible
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    
    try {
      await page.goto(this.baseUrl, { waitUntil: 'networkidle' });
      console.log('✅ Frontend accessibility verified');
    } catch (error) {
      console.error('❌ Frontend not accessible:', error.message);
      throw error;
    } finally {
      await browser.close();
    }
  }

  async runLoadTest() {
    console.log('\n📈 Starting Frontend Load Test...\n');
    
    const startTime = performance.now();
    const endTime = startTime + (this.duration * 1000);
    const workers = [];

    // Launch concurrent browser workers
    for (let i = 0; i < this.concurrency; i++) {
      workers.push(this.createWorker(i, endTime));
    }

    // Wait for all workers to complete
    await Promise.all(workers);
    
    const totalDuration = (performance.now() - startTime) / 1000;
    console.log(`\n✅ Load test completed in ${totalDuration.toFixed(2)} seconds`);
    
    return this.generateReport();
  }

  async createWorker(workerId, endTime) {
    const browser = await chromium.launch({ 
      headless: true,
      args: ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
    });
    
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      userAgent: `LoadTest-Worker-${workerId}/1.0`
    });

    try {
      let runCount = 0;
      
      while (performance.now() < endTime) {
        const scenario = this.scenarios[runCount % this.scenarios.length];
        await this.executeScenario(context, workerId, scenario, runCount);
        runCount++;
        
        // Small delay between runs to simulate real user behavior
        await this.sleep(Math.random() * 2000 + 500); // 0.5-2.5s
      }
      
      console.log(`Worker ${workerId} completed ${runCount} runs`);
      
    } catch (error) {
      console.error(`Worker ${workerId} error:`, error.message);
      this.results.errors.push({
        workerId,
        error: error.message,
        timestamp: new Date().toISOString()
      });
    } finally {
      await browser.close();
    }
  }

  async executeScenario(context, workerId, scenario, runCount) {
    const page = await context.newPage();
    const runStart = performance.now();
    
    try {
      // Configure performance monitoring
      await page.addInitScript(() => {
        window.performanceMetrics = {
          navigationStart: performance.timeOrigin,
          measurements: []
        };
        
        // Collect Core Web Vitals
        new PerformanceObserver((list) => {
          list.getEntries().forEach((entry) => {
            window.performanceMetrics.measurements.push({
              name: entry.name,
              startTime: entry.startTime,
              duration: entry.duration,
              entryType: entry.entryType
            });
          });
        }).observe({ entryTypes: ['navigation', 'paint', 'largest-contentful-paint', 'layout-shift'] });
      });

      const metrics = await this.runScenario(page, scenario);
      
      const runDuration = performance.now() - runStart;
      const result = {
        workerId,
        scenario,
        runCount,
        duration: runDuration,
        success: true,
        timestamp: new Date().toISOString(),
        metrics
      };
      
      this.results.runs.push(result);
      
      if (runCount % 10 === 0) {
        console.log(`Worker ${workerId}: ${runCount} runs completed (${scenario})`);
      }
      
    } catch (error) {
      this.results.errors.push({
        workerId,
        scenario,
        runCount,
        error: error.message,
        timestamp: new Date().toISOString()
      });
    } finally {
      await page.close();
    }
  }

  async runScenario(page, scenario) {
    const metrics = {
      scenario,
      timings: {},
      coreWebVitals: {},
      networkRequests: 0,
      jsErrors: []
    };

    // Monitor JavaScript errors
    page.on('pageerror', (error) => {
      metrics.jsErrors.push(error.message);
    });

    // Monitor network requests
    page.on('request', () => {
      metrics.networkRequests++;
    });

    const startTime = performance.now();

    switch (scenario) {
      case 'homepage':
        await this.homepageScenario(page, metrics);
        break;
      case 'metrics':
        await this.metricsScenario(page, metrics);
        break;
      case 'analog-demo':
        await this.analogDemoScenario(page, metrics);
        break;
      case 'cape-demo':
        await this.capeDemoScenario(page, metrics);
        break;
      default:
        throw new Error(`Unknown scenario: ${scenario}`);
    }

    metrics.timings.total = performance.now() - startTime;
    
    // Collect Core Web Vitals from browser
    const webVitals = await page.evaluate(() => {
      const measurements = window.performanceMetrics?.measurements || [];
      const vitals = {};
      
      // Extract key performance metrics
      measurements.forEach(entry => {
        switch (entry.name) {
          case 'first-contentful-paint':
            vitals.fcp = entry.startTime;
            break;
          case 'largest-contentful-paint':
            vitals.lcp = entry.startTime;
            break;
        }
      });
      
      // Calculate CLS from layout-shift entries
      const layoutShifts = measurements.filter(e => e.entryType === 'layout-shift');
      vitals.cls = layoutShifts.reduce((sum, entry) => sum + (entry.value || 0), 0);
      
      return vitals;
    });
    
    metrics.coreWebVitals = webVitals;
    return metrics;
  }

  async homepageScenario(page, metrics) {
    const startTime = performance.now();
    
    // Navigate to homepage
    await page.goto(this.baseUrl, { waitUntil: 'networkidle' });
    metrics.timings.pageLoad = performance.now() - startTime;
    
    // Wait for key elements to load
    await page.waitForSelector('[data-testid="forecast-dashboard"]', { timeout: 5000 });
    
    // Simulate user interactions
    if (await page.locator('button:has-text("Get Forecast")').isVisible()) {
      await page.click('button:has-text("Get Forecast")');
      await page.waitForTimeout(1000);
    }
    
    // Check for error states
    const errorElements = await page.locator('[data-testid="error-message"]').count();
    metrics.hasErrors = errorElements > 0;
  }

  async metricsScenario(page, metrics) {
    const startTime = performance.now();
    
    await page.goto(`${this.baseUrl}/metrics-demo`, { waitUntil: 'networkidle' });
    metrics.timings.pageLoad = performance.now() - startTime;
    
    // Wait for metrics dashboard to load
    await page.waitForSelector('[data-testid="metrics-dashboard"]', { timeout: 10000 });
    
    // Wait for charts to render (they may take longer)
    await page.waitForTimeout(2000);
    
    // Verify charts loaded
    const chartElements = await page.locator('[data-testid="performance-chart"]').count();
    metrics.chartsLoaded = chartElements > 0;
    
    // Test dashboard interactions
    if (await page.locator('button:has-text("Refresh")').isVisible()) {
      await page.click('button:has-text("Refresh")');
      await page.waitForTimeout(1500);
    }
  }

  async analogDemoScenario(page, metrics) {
    const startTime = performance.now();
    
    await page.goto(`${this.baseUrl}/analog-demo`, { waitUntil: 'networkidle' });
    metrics.timings.pageLoad = performance.now() - startTime;
    
    // Wait for analog explorer to load
    await page.waitForSelector('[data-testid="analog-explorer"]', { timeout: 10000 });
    
    // Test analog search functionality
    if (await page.locator('input[placeholder*="search"]').isVisible()) {
      await page.fill('input[placeholder*="search"]', 'temperature');
      await page.waitForTimeout(1000);
    }
    
    // Verify analog results
    const analogResults = await page.locator('[data-testid="analog-result"]').count();
    metrics.analogsFound = analogResults;
  }

  async capeDemoScenario(page, metrics) {
    const startTime = performance.now();
    
    await page.goto(`${this.baseUrl}/cape-demo`, { waitUntil: 'networkidle' });
    metrics.timings.pageLoad = performance.now() - startTime;
    
    // Wait for CAPE calculator to load
    await page.waitForSelector('[data-testid="cape-calculator"]', { timeout: 8000 });
    
    // Test CAPE calculations
    if (await page.locator('button:has-text("Calculate CAPE")').isVisible()) {
      await page.click('button:has-text("Calculate CAPE")');
      await page.waitForTimeout(2000);
    }
    
    // Verify CAPE results
    const capeValue = await page.locator('[data-testid="cape-value"]').textContent();
    metrics.capeCalculated = capeValue && capeValue.includes('J/kg');
  }

  generateReport() {
    const successfulRuns = this.results.runs.filter(r => r.success);
    const errorRate = (this.results.errors.length / (this.results.runs.length + this.results.errors.length)) * 100;
    
    // Calculate performance statistics
    const durations = successfulRuns.map(r => r.duration);
    const loadTimes = successfulRuns.map(r => r.metrics.timings.pageLoad).filter(t => t);
    const fcpTimes = successfulRuns.map(r => r.metrics.coreWebVitals.fcp).filter(t => t);
    const lcpTimes = successfulRuns.map(r => r.metrics.coreWebVitals.lcp).filter(t => t);
    
    this.results.summary = {
      totalRuns: this.results.runs.length,
      successfulRuns: successfulRuns.length,
      errorCount: this.results.errors.length,
      errorRate: errorRate.toFixed(2) + '%',
      
      performance: {
        avgDuration: this.average(durations).toFixed(2) + 'ms',
        p95Duration: this.percentile(durations, 95).toFixed(2) + 'ms',
        avgPageLoad: this.average(loadTimes).toFixed(2) + 'ms',
        p95PageLoad: this.percentile(loadTimes, 95).toFixed(2) + 'ms'
      },
      
      coreWebVitals: {
        avgFCP: this.average(fcpTimes).toFixed(2) + 'ms',
        p95FCP: this.percentile(fcpTimes, 95).toFixed(2) + 'ms',
        avgLCP: this.average(lcpTimes).toFixed(2) + 'ms',
        p95LCP: this.percentile(lcpTimes, 95).toFixed(2) + 'ms',
        fcpTarget: fcpTimes.filter(t => t < 1500).length / fcpTimes.length * 100,
        lcpTarget: lcpTimes.filter(t => t < 2500).length / lcpTimes.length * 100
      },
      
      scenarios: this.analyzeScenarios()
    };

    this.printReport();
    return this.results;
  }

  analyzeScenarios() {
    const scenarioStats = {};
    
    this.scenarios.forEach(scenario => {
      const scenarioRuns = this.results.runs.filter(r => r.scenario === scenario);
      const durations = scenarioRuns.map(r => r.duration);
      
      scenarioStats[scenario] = {
        runs: scenarioRuns.length,
        avgDuration: this.average(durations).toFixed(2) + 'ms',
        p95Duration: this.percentile(durations, 95).toFixed(2) + 'ms',
        successRate: (scenarioRuns.filter(r => r.success).length / scenarioRuns.length * 100).toFixed(1) + '%'
      };
    });
    
    return scenarioStats;
  }

  printReport() {
    console.log('\n📊 Frontend Load Test Report');
    console.log('═'.repeat(50));
    console.log(`Total Runs: ${this.results.summary.totalRuns}`);
    console.log(`Successful: ${this.results.summary.successfulRuns}`);
    console.log(`Error Rate: ${this.results.summary.errorRate}`);
    
    console.log('\n⚡ Performance Metrics:');
    console.log(`Avg Duration: ${this.results.summary.performance.avgDuration}`);
    console.log(`P95 Duration: ${this.results.summary.performance.p95Duration}`);
    console.log(`Avg Page Load: ${this.results.summary.performance.avgPageLoad}`);
    console.log(`P95 Page Load: ${this.results.summary.performance.p95PageLoad}`);
    
    console.log('\n🎯 Core Web Vitals:');
    console.log(`FCP (Avg/P95): ${this.results.summary.coreWebVitals.avgFCP} / ${this.results.summary.coreWebVitals.p95FCP}`);
    console.log(`LCP (Avg/P95): ${this.results.summary.coreWebVitals.avgLCP} / ${this.results.summary.coreWebVitals.p95LCP}`);
    console.log(`FCP Target Met: ${this.results.summary.coreWebVitals.fcpTarget.toFixed(1)}% < 1.5s`);
    console.log(`LCP Target Met: ${this.results.summary.coreWebVitals.lcpTarget.toFixed(1)}% < 2.5s`);
    
    console.log('\n📝 Scenario Analysis:');
    Object.entries(this.results.summary.scenarios).forEach(([scenario, stats]) => {
      console.log(`${scenario}: ${stats.runs} runs, ${stats.avgDuration} avg, ${stats.successRate} success`);
    });
    
    if (this.results.errors.length > 0) {
      console.log('\n❌ Errors:');
      this.results.errors.slice(0, 5).forEach(error => {
        console.log(`- Worker ${error.workerId}: ${error.error}`);
      });
      if (this.results.errors.length > 5) {
        console.log(`... and ${this.results.errors.length - 5} more errors`);
      }
    }
  }

  average(numbers) {
    return numbers.length ? numbers.reduce((a, b) => a + b) / numbers.length : 0;
  }

  percentile(numbers, p) {
    if (!numbers.length) return 0;
    const sorted = numbers.slice().sort((a, b) => a - b);
    const index = (p / 100) * (sorted.length - 1);
    const lower = Math.floor(index);
    const upper = Math.ceil(index);
    const weight = index % 1;
    return sorted[lower] * (1 - weight) + sorted[upper] * weight;
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// CLI execution
async function main() {
  const args = process.argv.slice(2);
  const options = {
    baseUrl: process.env.FRONTEND_URL || 'http://localhost:3000',
    concurrency: parseInt(process.env.CONCURRENCY) || 10,
    duration: parseInt(process.env.DURATION) || 300
  };

  console.log('🎭 Adelaide Weather Frontend Load Tester');
  console.log('==========================================');

  const tester = new FrontendLoadTester(options);
  
  try {
    await tester.initialize();
    const results = await tester.runLoadTest();
    
    // Save results
    const fs = require('fs');
    const reportPath = './tests/performance/reports/frontend-load-test-results.json';
    fs.writeFileSync(reportPath, JSON.stringify(results, null, 2));
    console.log(`\n💾 Results saved to: ${reportPath}`);
    
    // Exit with appropriate code
    const errorRate = parseFloat(results.summary.errorRate);
    const avgPageLoad = parseFloat(results.summary.performance.avgPageLoad);
    
    if (errorRate > 5.0) {
      console.log('\n❌ FAIL: Error rate too high (>5%)');
      process.exit(1);
    } else if (avgPageLoad > 3000) {
      console.log('\n⚠️  WARN: Average page load time exceeds 3s');
      process.exit(1);
    } else {
      console.log('\n✅ PASS: Frontend performance within acceptable limits');
      process.exit(0);
    }
    
  } catch (error) {
    console.error('\n💥 Load test failed:', error.message);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = FrontendLoadTester;