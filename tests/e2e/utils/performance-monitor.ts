/**
 * Performance Monitor for E2E Testing
 * 
 * Provides utilities for measuring and validating API performance
 * with specific focus on TEST2 requirements:
 * - API response time p95 < 150ms
 * - FAISS search time p95 < 1ms
 * - Memory usage monitoring
 */

import { Page } from '@playwright/test';

export interface PerformanceMetric {
  endpoint: string;
  method: string;
  status: number;
  duration: number;
  timestamp: number;
  faissTime?: number;
  memoryUsage?: number;
  success: boolean;
}

export interface PerformanceSummary {
  endpoint: string;
  totalRequests: number;
  successfulRequests: number;
  successRate: number;
  p50: number;
  p95: number;
  p99: number;
  mean: number;
  min: number;
  max: number;
  faissP95?: number;
  memoryPeak?: number;
}

export class PerformanceMonitor {
  private metrics: PerformanceMetric[];
  private page: Page;

  constructor(page: Page) {
    this.page = page;
    this.metrics = [];
  }

  /**
   * Start monitoring network requests and capture performance metrics
   */
  async startMonitoring(): Promise<void> {
    this.page.on('response', async (response) => {
      try {
        const request = response.request();
        const timing = response.timing();
        const url = new URL(request.url());
        
        // Only monitor API endpoints
        if (!url.pathname.startsWith('/api/') && !url.pathname.startsWith('/forecast')) {
          return;
        }

        const metric: PerformanceMetric = {
          endpoint: url.pathname,
          method: request.method(),
          status: response.status(),
          duration: timing.responseEnd - timing.requestStart,
          timestamp: Date.now(),
          success: response.status() >= 200 && response.status() < 300
        };

        // Extract FAISS timing from response if available
        if (metric.success && response.headers()['content-type']?.includes('application/json')) {
          try {
            const responseBody = await response.json();
            
            if (responseBody.search_stats?.faiss_search_time_ms) {
              metric.faissTime = responseBody.search_stats.faiss_search_time_ms;
            } else if (responseBody.performance_stats?.faiss_time_ms) {
              metric.faissTime = responseBody.performance_stats.faiss_time_ms;
            }
            
            // Extract memory usage if available
            if (responseBody.memory_usage_mb) {
              metric.memoryUsage = responseBody.memory_usage_mb;
            }
          } catch (e) {
            // Ignore JSON parsing errors
          }
        }

        this.metrics.push(metric);
      } catch (error) {
        console.warn('Error capturing performance metric:', error);
      }
    });
  }

  /**
   * Record a manual performance metric
   */
  recordMetric(metric: Omit<PerformanceMetric, 'timestamp'>): void {
    this.metrics.push({
      ...metric,
      timestamp: Date.now()
    });
  }

  /**
   * Get all recorded metrics
   */
  getMetrics(): PerformanceMetric[] {
    return [...this.metrics];
  }

  /**
   * Get metrics for a specific endpoint
   */
  getEndpointMetrics(endpoint: string): PerformanceMetric[] {
    return this.metrics.filter(m => m.endpoint === endpoint);
  }

  /**
   * Calculate percentile for a given array of values
   */
  private calculatePercentile(values: number[], percentile: number): number {
    if (values.length === 0) return 0;
    
    const sorted = [...values].sort((a, b) => a - b);
    const index = Math.ceil((percentile / 100) * sorted.length) - 1;
    return sorted[Math.max(0, index)];
  }

  /**
   * Generate performance summary for an endpoint
   */
  getEndpointSummary(endpoint: string): PerformanceSummary {
    const endpointMetrics = this.getEndpointMetrics(endpoint);
    const successfulMetrics = endpointMetrics.filter(m => m.success);
    const durations = successfulMetrics.map(m => m.duration);
    
    const summary: PerformanceSummary = {
      endpoint,
      totalRequests: endpointMetrics.length,
      successfulRequests: successfulMetrics.length,
      successRate: endpointMetrics.length > 0 ? successfulMetrics.length / endpointMetrics.length : 0,
      p50: this.calculatePercentile(durations, 50),
      p95: this.calculatePercentile(durations, 95),
      p99: this.calculatePercentile(durations, 99),
      mean: durations.length > 0 ? durations.reduce((sum, d) => sum + d, 0) / durations.length : 0,
      min: durations.length > 0 ? Math.min(...durations) : 0,
      max: durations.length > 0 ? Math.max(...durations) : 0
    };

    // Add FAISS performance if available
    const faissTimes = successfulMetrics
      .filter(m => m.faissTime !== undefined)
      .map(m => m.faissTime!);
      
    if (faissTimes.length > 0) {
      summary.faissP95 = this.calculatePercentile(faissTimes, 95);
    }

    // Add memory usage if available
    const memoryUsages = successfulMetrics
      .filter(m => m.memoryUsage !== undefined)
      .map(m => m.memoryUsage!);
      
    if (memoryUsages.length > 0) {
      summary.memoryPeak = Math.max(...memoryUsages);
    }

    return summary;
  }

  /**
   * Generate complete performance report
   */
  getPerformanceReport(): { [endpoint: string]: PerformanceSummary } {
    const endpoints = [...new Set(this.metrics.map(m => m.endpoint))];
    const report: { [endpoint: string]: PerformanceSummary } = {};

    for (const endpoint of endpoints) {
      report[endpoint] = this.getEndpointSummary(endpoint);
    }

    return report;
  }

  /**
   * Validate TEST2 performance requirements
   */
  validatePerformanceRequirements(): {
    apiP95Valid: boolean;
    faissP95Valid: boolean;
    issues: string[];
  } {
    const report = this.getPerformanceReport();
    const issues: string[] = [];
    let apiP95Valid = true;
    let faissP95Valid = true;

    // Check API response time requirements
    for (const [endpoint, summary] of Object.entries(report)) {
      if (summary.p95 > 150) {
        apiP95Valid = false;
        issues.push(`${endpoint} P95 latency ${summary.p95.toFixed(2)}ms exceeds 150ms requirement`);
      }

      if (summary.faissP95 !== undefined && summary.faissP95 > 1.0) {
        faissP95Valid = false;
        issues.push(`${endpoint} FAISS P95 search time ${summary.faissP95.toFixed(3)}ms exceeds 1ms requirement`);
      }
    }

    return {
      apiP95Valid,
      faissP95Valid,
      issues
    };
  }

  /**
   * Clear all recorded metrics
   */
  reset(): void {
    this.metrics = [];
  }

  /**
   * Export metrics to JSON for external analysis
   */
  exportMetrics(): string {
    return JSON.stringify({
      summary: this.getPerformanceReport(),
      detailed_metrics: this.metrics,
      validation: this.validatePerformanceRequirements(),
      timestamp: new Date().toISOString()
    }, null, 2);
  }
}