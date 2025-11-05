/**
 * Performance Testing Utility Functions
 * Shared utilities for performance measurement and analysis
 */

import { performance } from 'perf_hooks';
import axios, { AxiosRequestConfig, AxiosResponse } from 'axios';

export interface PerformanceMetrics {
  timestamp: number;
  duration: number;
  memoryUsage: NodeJS.MemoryUsage;
  success: boolean;
  error?: string;
  responseSize?: number;
  statusCode?: number;
}

export interface TimingResult {
  count: number;
  avg: number;
  min: number;
  max: number;
  p50: number;
  p95: number;
  p99: number;
  stdDev: number;
}

export interface LoadTestConfig {
  baseUrl: string;
  concurrency: number;
  duration: number;
  rampUpTime: number;
  requestsPerSecond: number;
  timeout: number;
}

export interface CoreWebVitals {
  fcp?: number; // First Contentful Paint
  lcp?: number; // Largest Contentful Paint
  fid?: number; // First Input Delay
  cls?: number; // Cumulative Layout Shift
  ttfb?: number; // Time to First Byte
  tti?: number; // Time to Interactive
}

export class PerformanceTimer {
  private startTime: number = 0;
  private endTime: number = 0;
  private measurements: Array<{ name: string; value: number }> = [];

  start(): void {
    this.startTime = performance.now();
  }

  end(): number {
    this.endTime = performance.now();
    return this.endTime - this.startTime;
  }

  mark(name: string): void {
    const currentTime = performance.now();
    this.measurements.push({
      name,
      value: currentTime - this.startTime
    });
  }

  getMeasurements(): Array<{ name: string; value: number }> {
    return [...this.measurements];
  }

  getDuration(): number {
    return this.endTime - this.startTime;
  }

  reset(): void {
    this.startTime = 0;
    this.endTime = 0;
    this.measurements = [];
  }
}

export class PerformanceCollector {
  private metrics: PerformanceMetrics[] = [];
  private timer: PerformanceTimer;

  constructor() {
    this.timer = new PerformanceTimer();
  }

  async measureRequest(
    url: string, 
    config?: AxiosRequestConfig
  ): Promise<PerformanceMetrics> {
    this.timer.start();
    const startMemory = process.memoryUsage();
    
    let response: AxiosResponse;
    let success = true;
    let error: string | undefined;
    let statusCode: number | undefined;
    let responseSize: number | undefined;

    try {
      response = await axios.get(url, {
        timeout: 10000,
        ...config
      });
      statusCode = response.status;
      responseSize = JSON.stringify(response.data).length;
    } catch (err) {
      success = false;
      error = err instanceof Error ? err.message : 'Unknown error';
      statusCode = (err as any)?.response?.status;
    }

    const duration = this.timer.end();
    const endMemory = process.memoryUsage();

    const metric: PerformanceMetrics = {
      timestamp: Date.now(),
      duration,
      memoryUsage: {
        rss: endMemory.rss - startMemory.rss,
        heapTotal: endMemory.heapTotal - startMemory.heapTotal,
        heapUsed: endMemory.heapUsed - startMemory.heapUsed,
        external: endMemory.external - startMemory.external,
        arrayBuffers: endMemory.arrayBuffers - startMemory.arrayBuffers
      },
      success,
      error,
      responseSize,
      statusCode
    };

    this.metrics.push(metric);
    return metric;
  }

  getMetrics(): PerformanceMetrics[] {
    return [...this.metrics];
  }

  getSuccessfulMetrics(): PerformanceMetrics[] {
    return this.metrics.filter(m => m.success);
  }

  getFailedMetrics(): PerformanceMetrics[] {
    return this.metrics.filter(m => !m.success);
  }

  clear(): void {
    this.metrics = [];
  }

  getErrorRate(): number {
    if (this.metrics.length === 0) return 0;
    return (this.getFailedMetrics().length / this.metrics.length) * 100;
  }

  getThroughput(): number {
    const successful = this.getSuccessfulMetrics();
    if (successful.length < 2) return 0;
    
    const timeSpan = (successful[successful.length - 1].timestamp - successful[0].timestamp) / 1000;
    return successful.length / timeSpan;
  }
}

export function calculateTimingStats(durations: number[]): TimingResult {
  if (durations.length === 0) {
    return {
      count: 0,
      avg: 0,
      min: 0,
      max: 0,
      p50: 0,
      p95: 0,
      p99: 0,
      stdDev: 0
    };
  }

  const sorted = [...durations].sort((a, b) => a - b);
  const sum = durations.reduce((a, b) => a + b, 0);
  const avg = sum / durations.length;

  // Calculate standard deviation
  const variance = durations.reduce((acc, val) => acc + Math.pow(val - avg, 2), 0) / durations.length;
  const stdDev = Math.sqrt(variance);

  return {
    count: durations.length,
    avg,
    min: sorted[0],
    max: sorted[sorted.length - 1],
    p50: percentile(sorted, 50),
    p95: percentile(sorted, 95),
    p99: percentile(sorted, 99),
    stdDev
  };
}

export function percentile(sortedArray: number[], p: number): number {
  if (sortedArray.length === 0) return 0;
  
  const index = (p / 100) * (sortedArray.length - 1);
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  const weight = index % 1;

  if (upper >= sortedArray.length) {
    return sortedArray[sortedArray.length - 1];
  }

  return sortedArray[lower] * (1 - weight) + sortedArray[upper] * weight;
}

export async function warmupSystem(
  baseUrl: string, 
  endpoints: string[], 
  iterations: number = 5
): Promise<void> {
  console.log(`🔥 Warming up system with ${iterations} iterations...`);
  
  for (let i = 0; i < iterations; i++) {
    for (const endpoint of endpoints) {
      try {
        await axios.get(`${baseUrl}${endpoint}`, { timeout: 5000 });
      } catch (error) {
        // Ignore warmup errors
      }
    }
  }
  
  console.log('✅ Warmup completed');
}

export function generateLoadTestScenarios(config: LoadTestConfig) {
  const scenarios = [];
  const totalDuration = config.duration + config.rampUpTime;
  
  // Ramp-up phase
  for (let i = 0; i < config.rampUpTime; i++) {
    const concurrencyLevel = Math.floor((i / config.rampUpTime) * config.concurrency);
    scenarios.push({
      duration: 1,
      arrivalRate: concurrencyLevel,
      name: `Ramp-up phase ${i + 1}/${config.rampUpTime}`
    });
  }
  
  // Sustained load phase
  scenarios.push({
    duration: config.duration,
    arrivalRate: config.concurrency,
    name: 'Sustained load phase'
  });
  
  return scenarios;
}

export class MemoryMonitor {
  private samples: Array<{ timestamp: number; memory: NodeJS.MemoryUsage }> = [];
  private isMonitoring = false;
  private interval?: NodeJS.Timeout;

  start(intervalMs: number = 1000): void {
    if (this.isMonitoring) return;
    
    this.isMonitoring = true;
    this.interval = setInterval(() => {
      this.samples.push({
        timestamp: Date.now(),
        memory: process.memoryUsage()
      });
    }, intervalMs);
  }

  stop(): void {
    if (this.interval) {
      clearInterval(this.interval);
      this.interval = undefined;
    }
    this.isMonitoring = false;
  }

  getSamples(): Array<{ timestamp: number; memory: NodeJS.MemoryUsage }> {
    return [...this.samples];
  }

  getMemoryGrowth(): { 
    initial: number; 
    peak: number; 
    current: number; 
    growth: number 
  } {
    if (this.samples.length === 0) {
      return { initial: 0, peak: 0, current: 0, growth: 0 };
    }

    const initial = this.samples[0].memory.heapUsed;
    const current = this.samples[this.samples.length - 1].memory.heapUsed;
    const peak = Math.max(...this.samples.map(s => s.memory.heapUsed));
    const growth = current - initial;

    return {
      initial: Math.round(initial / 1024 / 1024),
      peak: Math.round(peak / 1024 / 1024),
      current: Math.round(current / 1024 / 1024),
      growth: Math.round(growth / 1024 / 1024)
    };
  }

  clear(): void {
    this.samples = [];
  }
}

export function formatBytes(bytes: number, decimals: number = 2): string {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];

  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms.toFixed(2)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
  if (ms < 3600000) return `${(ms / 60000).toFixed(2)}m`;
  return `${(ms / 3600000).toFixed(2)}h`;
}

export async function checkSystemHealth(baseUrl: string): Promise<{
  api: boolean;
  health: boolean;
  responseTime: number;
  error?: string;
}> {
  const timer = new PerformanceTimer();
  
  try {
    timer.start();
    
    // Check basic connectivity
    const response = await axios.get(`${baseUrl}/health`, { 
      timeout: 5000,
      validateStatus: () => true // Accept any status code
    });
    
    const responseTime = timer.end();
    
    const isHealthy = response.status === 200 && 
                     response.data?.status === 'healthy';
    
    return {
      api: response.status < 500,
      health: isHealthy,
      responseTime,
    };
    
  } catch (error) {
    const responseTime = timer.end();
    
    return {
      api: false,
      health: false,
      responseTime,
      error: error instanceof Error ? error.message : 'Unknown error'
    };
  }
}

export function validateCoreWebVitals(vitals: CoreWebVitals): {
  pass: boolean;
  details: Array<{ metric: string; value: number; target: number; pass: boolean }>;
} {
  const targets = {
    fcp: 1500, // 1.5s
    lcp: 2500, // 2.5s
    fid: 100,  // 100ms
    cls: 0.1,  // 0.1
    ttfb: 600, // 600ms
    tti: 3500  // 3.5s
  };

  const details = Object.entries(vitals)
    .filter(([_, value]) => value !== undefined)
    .map(([metric, value]) => ({
      metric,
      value: value!,
      target: targets[metric as keyof typeof targets] || 0,
      pass: value! <= (targets[metric as keyof typeof targets] || Infinity)
    }));

  const pass = details.every(d => d.pass);

  return { pass, details };
}

export class PerformanceReporter {
  generateReport(
    collector: PerformanceCollector,
    memoryMonitor: MemoryMonitor,
    testConfig: Partial<LoadTestConfig>
  ): any {
    const metrics = collector.getMetrics();
    const successfulMetrics = collector.getSuccessfulMetrics();
    const durations = successfulMetrics.map(m => m.duration);
    
    const timingStats = calculateTimingStats(durations);
    const memoryGrowth = memoryMonitor.getMemoryGrowth();
    
    return {
      summary: {
        totalRequests: metrics.length,
        successfulRequests: successfulMetrics.length,
        failedRequests: collector.getFailedMetrics().length,
        errorRate: collector.getErrorRate().toFixed(2) + '%',
        throughput: collector.getThroughput().toFixed(2) + ' req/s',
        testDuration: testConfig.duration ? formatDuration(testConfig.duration * 1000) : 'N/A'
      },
      
      performance: {
        averageResponseTime: formatDuration(timingStats.avg),
        medianResponseTime: formatDuration(timingStats.p50),
        p95ResponseTime: formatDuration(timingStats.p95),
        p99ResponseTime: formatDuration(timingStats.p99),
        minResponseTime: formatDuration(timingStats.min),
        maxResponseTime: formatDuration(timingStats.max),
        standardDeviation: formatDuration(timingStats.stdDev)
      },
      
      memory: {
        initialUsage: formatBytes(memoryGrowth.initial * 1024 * 1024),
        peakUsage: formatBytes(memoryGrowth.peak * 1024 * 1024),
        currentUsage: formatBytes(memoryGrowth.current * 1024 * 1024),
        growth: formatBytes(memoryGrowth.growth * 1024 * 1024),
        growthMB: memoryGrowth.growth
      },
      
      targets: {
        responseTimeTarget: testConfig.timeout ? formatDuration(testConfig.timeout) : 'N/A',
        responseTimeMet: testConfig.timeout ? timingStats.p95 <= testConfig.timeout : true,
        errorRateTarget: '< 1%',
        errorRateMet: collector.getErrorRate() < 1,
        throughputTarget: testConfig.requestsPerSecond ? `${testConfig.requestsPerSecond} req/s` : 'N/A',
        throughputMet: testConfig.requestsPerSecond ? collector.getThroughput() >= testConfig.requestsPerSecond : true
      },
      
      rawData: {
        timingStats,
        memoryGrowth,
        errorRate: collector.getErrorRate(),
        throughput: collector.getThroughput()
      }
    };
  }

  printReport(report: any): void {
    console.log('\n📊 Performance Test Report');
    console.log('='.repeat(50));
    
    console.log('\n📈 Summary:');
    Object.entries(report.summary).forEach(([key, value]) => {
      console.log(`  ${key}: ${value}`);
    });
    
    console.log('\n⚡ Performance:');
    Object.entries(report.performance).forEach(([key, value]) => {
      console.log(`  ${key}: ${value}`);
    });
    
    console.log('\n💾 Memory:');
    Object.entries(report.memory).forEach(([key, value]) => {
      console.log(`  ${key}: ${value}`);
    });
    
    console.log('\n🎯 Targets:');
    Object.entries(report.targets).forEach(([key, value]) => {
      const icon = key.endsWith('Met') ? (value ? '✅' : '❌') : '';
      console.log(`  ${key}: ${value} ${icon}`);
    });
  }

  async saveReport(report: any, filename?: string): Promise<string> {
    const fs = require('fs').promises;
    const path = require('path');
    
    const reportsDir = path.join(__dirname, '..', 'reports');
    
    try {
      await fs.mkdir(reportsDir, { recursive: true });
    } catch (error) {
      // Directory already exists
    }
    
    const reportFilename = filename || `performance-report-${Date.now()}.json`;
    const filepath = path.join(reportsDir, reportFilename);
    
    await fs.writeFile(filepath, JSON.stringify(report, null, 2));
    
    return filepath;
  }
}

export async function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

export default {
  PerformanceTimer,
  PerformanceCollector,
  MemoryMonitor,
  PerformanceReporter,
  calculateTimingStats,
  percentile,
  warmupSystem,
  generateLoadTestScenarios,
  formatBytes,
  formatDuration,
  checkSystemHealth,
  validateCoreWebVitals,
  sleep
};