/**
 * TEST2: Comprehensive Integration and Performance Tests
 * 
 * E2E tests for Adelaide Weather Forecasting System with:
 * - /api/analogs endpoint integration with real FAISS data
 * - /forecast endpoint integration with transparency validation
 * - Performance benchmarks: API p95 < 150ms, FAISS p95 < 1ms
 * - Zero fallback validation and data source verification
 * - Distance monotonicity and memory usage monitoring
 */

import { test, expect, Page } from '@playwright/test';
import { PerformanceMonitor } from '../../utils/performance-monitor';
import { FAISSValidator } from '../../utils/faiss-validator';
import { TransparencyValidator } from '../../utils/transparency-validator';

interface AnalogResponse {
  analogs: Array<{
    similarity_score: number;
    metadata: any;
    distance: number;
  }>;
  search_stats: {
    total_search_time_ms: number;
    faiss_search_time_ms: number;
    data_source: string;
    fallback_used: boolean;
  };
  transparency: {
    model_version: string;
    search_method: string;
    confidence_intervals: any;
    quality_scores: any;
  };
}

interface ForecastResponse {
  forecast: {
    horizon: string;
    variables: string[];
    analogs_count: number;
    data_source: string;
  };
  performance_stats: {
    total_time_ms: number;
    faiss_time_ms: number;
    fallback_used: boolean;
  };
  transparency: {
    model_version: string;
    analog_quality: any;
    uncertainty_quantification: any;
  };
}

class APITestSuite {
  private performanceMonitor: PerformanceMonitor;
  private faissValidator: FAISSValidator;
  private transparencyValidator: TransparencyValidator;
  private performanceMetrics: Array<{
    endpoint: string;
    duration: number;
    timestamp: number;
    success: boolean;
  }>;

  constructor(page: Page) {
    this.performanceMonitor = new PerformanceMonitor(page);
    this.faissValidator = new FAISSValidator();
    this.transparencyValidator = new TransparencyValidator();
    this.performanceMetrics = [];
  }

  async validateAnalogResponse(response: AnalogResponse): Promise<void> {
    // Validate FAISS data source requirement
    expect(response.search_stats.data_source).toBe('faiss');
    expect(response.search_stats.fallback_used).toBe(false);
    
    // Validate FAISS performance requirement: p95 < 1ms
    expect(response.search_stats.faiss_search_time_ms).toBeLessThan(1.0);
    
    // Validate distance monotonicity
    const distances = response.analogs.map(a => a.distance);
    for (let i = 1; i < distances.length; i++) {
      expect(distances[i]).toBeGreaterThanOrEqual(distances[i - 1]);
    }
    
    // Validate transparency fields
    expect(response.transparency).toBeDefined();
    expect(response.transparency.model_version).toBeDefined();
    expect(response.transparency.search_method).toBe('faiss');
    expect(response.transparency.confidence_intervals).toBeDefined();
    
    // Validate analog quality
    expect(response.analogs).toHaveLength(100); // Default analog count
    response.analogs.forEach(analog => {
      expect(analog.similarity_score).toBeGreaterThan(0);
      expect(analog.similarity_score).toBeLessThanOrEqual(1);
      expect(analog.distance).toBeGreaterThanOrEqual(0);
      expect(analog.metadata).toBeDefined();
    });
  }

  async validateForecastResponse(response: ForecastResponse): Promise<void> {
    // Validate data source and fallback requirements
    expect(response.forecast.data_source).toBe('faiss');
    expect(response.performance_stats.fallback_used).toBe(false);
    
    // Validate transparency fields
    expect(response.transparency).toBeDefined();
    expect(response.transparency.model_version).toBeDefined();
    expect(response.transparency.analog_quality).toBeDefined();
    expect(response.transparency.uncertainty_quantification).toBeDefined();
    
    // Validate forecast structure
    expect(response.forecast.horizon).toMatch(/^(6h|12h|24h|48h)$/);
    expect(response.forecast.variables).toBeInstanceOf(Array);
    expect(response.forecast.analogs_count).toBeGreaterThan(0);
    
    // Validate performance stats
    expect(response.performance_stats.total_time_ms).toBeGreaterThan(0);
    expect(response.performance_stats.faiss_time_ms).toBeLessThan(1.0);
  }

  recordPerformanceMetric(endpoint: string, duration: number, success: boolean): void {
    this.performanceMetrics.push({
      endpoint,
      duration,
      timestamp: Date.now(),
      success
    });
  }

  calculateP95Latency(endpoint: string): number {
    const metrics = this.performanceMetrics
      .filter(m => m.endpoint === endpoint && m.success)
      .map(m => m.duration)
      .sort((a, b) => a - b);
    
    if (metrics.length === 0) return 0;
    
    const p95Index = Math.floor(metrics.length * 0.95);
    return metrics[p95Index];
  }

  getPerformanceReport(): any {
    const endpoints = [...new Set(this.performanceMetrics.map(m => m.endpoint))];
    
    return endpoints.reduce((report, endpoint) => {
      const endpointMetrics = this.performanceMetrics.filter(m => m.endpoint === endpoint);
      const successfulMetrics = endpointMetrics.filter(m => m.success);
      
      report[endpoint] = {
        total_requests: endpointMetrics.length,
        successful_requests: successfulMetrics.length,
        success_rate: successfulMetrics.length / endpointMetrics.length,
        p95_latency_ms: this.calculateP95Latency(endpoint),
        mean_latency_ms: successfulMetrics.reduce((sum, m) => sum + m.duration, 0) / successfulMetrics.length,
        min_latency_ms: Math.min(...successfulMetrics.map(m => m.duration)),
        max_latency_ms: Math.max(...successfulMetrics.map(m => m.duration))
      };
      
      return report;
    }, {} as any);
  }
}

test.describe('TEST2: Comprehensive API Integration Tests', () => {
  let apiTestSuite: APITestSuite;
  let baseURL: string;

  test.beforeEach(async ({ page }) => {
    apiTestSuite = new APITestSuite(page);
    baseURL = process.env.BASE_URL || 'http://localhost:8000';
  });

  test('API-001: /api/analogs endpoint integration with real FAISS data', async ({ request }) => {
    const testCases = [
      {
        horizon: '24h',
        variables: ['t2m', 'u10', 'v10'],
        expected_analogs: 100
      },
      {
        horizon: '6h',
        variables: ['t2m'],
        expected_analogs: 100
      },
      {
        horizon: '12h',
        variables: ['t2m', 'u10', 'v10', 'cape'],
        expected_analogs: 100
      },
      {
        horizon: '48h',
        variables: ['t2m', 'u10', 'v10', 'z500'],
        expected_analogs: 100
      }
    ];

    for (const testCase of testCases) {
      const startTime = Date.now();
      
      try {
        const response = await request.get(`${baseURL}/api/analogs`, {
          params: {
            horizon: testCase.horizon,
            variables: testCase.variables.join(','),
            count: testCase.expected_analogs.toString()
          },
          headers: {
            'Authorization': `Bearer ${process.env.API_TOKEN || 'test-token-12345'}`
          }
        });

        const endTime = Date.now();
        const duration = endTime - startTime;
        
        expect(response.status()).toBe(200);
        
        const responseData: AnalogResponse = await response.json();
        await apiTestSuite.validateAnalogResponse(responseData);
        
        // Performance requirement: API p95 < 150ms
        expect(duration).toBeLessThan(150);
        
        apiTestSuite.recordPerformanceMetric('/api/analogs', duration, true);
        
        console.log(`✓ /api/analogs test passed for ${testCase.horizon} with ${testCase.variables.join(',')} (${duration}ms)`);
        
      } catch (error) {
        const duration = Date.now() - startTime;
        apiTestSuite.recordPerformanceMetric('/api/analogs', duration, false);
        throw error;
      }
    }
  });

  test('API-002: /forecast endpoint integration with transparency validation', async ({ request }) => {
    const testCases = [
      {
        horizon: '24h',
        vars: 't2m,u10,v10'
      },
      {
        horizon: '6h',
        vars: 't2m'
      },
      {
        horizon: '12h',
        vars: 't2m,u10,v10,cape'
      },
      {
        horizon: '48h',
        vars: 't2m,u10,v10,z500,t850'
      }
    ];

    for (const testCase of testCases) {
      const startTime = Date.now();
      
      try {
        const response = await request.get(`${baseURL}/forecast`, {
          params: testCase,
          headers: {
            'Authorization': `Bearer ${process.env.API_TOKEN || 'test-token-12345'}`
          }
        });

        const endTime = Date.now();
        const duration = endTime - startTime;
        
        expect(response.status()).toBe(200);
        
        const responseData: ForecastResponse = await response.json();
        await apiTestSuite.validateForecastResponse(responseData);
        
        // Performance requirement: API p95 < 150ms
        expect(duration).toBeLessThan(150);
        
        apiTestSuite.recordPerformanceMetric('/forecast', duration, true);
        
        console.log(`✓ /forecast test passed for ${testCase.horizon} with ${testCase.vars} (${duration}ms)`);
        
      } catch (error) {
        const duration = Date.now() - startTime;
        apiTestSuite.recordPerformanceMetric('/forecast', duration, false);
        throw error;
      }
    }
  });

  test('PERF-001: Performance benchmark validation', async ({ request }) => {
    // Warm up phase
    for (let i = 0; i < 10; i++) {
      await request.get(`${baseURL}/forecast`, {
        params: { horizon: '24h', vars: 't2m' },
        headers: { 'Authorization': `Bearer ${process.env.API_TOKEN || 'test-token-12345'}` }
      });
    }

    // Performance testing phase
    const performanceTests = [];
    
    for (let i = 0; i < 50; i++) {
      const testPromise = (async () => {
        const startTime = Date.now();
        
        const response = await request.get(`${baseURL}/api/analogs`, {
          params: {
            horizon: ['6h', '12h', '24h', '48h'][i % 4],
            variables: ['t2m', 't2m,u10,v10', 't2m,u10,v10,cape'][i % 3],
            count: '100'
          },
          headers: { 'Authorization': `Bearer ${process.env.API_TOKEN || 'test-token-12345'}` }
        });
        
        const duration = Date.now() - startTime;
        const success = response.status() === 200;
        
        if (success) {
          const data: AnalogResponse = await response.json();
          expect(data.search_stats.faiss_search_time_ms).toBeLessThan(1.0);
          expect(data.search_stats.fallback_used).toBe(false);
        }
        
        apiTestSuite.recordPerformanceMetric('/api/analogs', duration, success);
        return { duration, success };
      })();
      
      performanceTests.push(testPromise);
    }

    await Promise.all(performanceTests);

    // Validate performance requirements
    const analogsP95 = apiTestSuite.calculateP95Latency('/api/analogs');
    expect(analogsP95).toBeLessThan(150);
    
    console.log(`✓ Performance test completed - /api/analogs P95: ${analogsP95}ms`);
  });

  test('FAISS-001: FAISS health and performance validation', async ({ request }) => {
    const response = await request.get(`${baseURL}/health/faiss`, {
      headers: { 'Authorization': `Bearer ${process.env.API_TOKEN || 'test-token-12345'}` }
    });

    expect(response.status()).toBe(200);
    
    const healthData = await response.json();
    
    // Validate FAISS health
    expect(healthData.status).toBe('healthy');
    expect(healthData.indices_loaded).toBeGreaterThan(0);
    expect(healthData.memory_usage_mb).toBeGreaterThan(0);
    
    // Validate performance metrics
    expect(healthData.performance_stats.average_search_time_ms).toBeLessThan(1.0);
    expect(healthData.performance_stats.p95_search_time_ms).toBeLessThan(1.0);
    expect(healthData.performance_stats.fallback_rate).toBe(0);
    
    console.log(`✓ FAISS health validation passed - Avg search time: ${healthData.performance_stats.average_search_time_ms}ms`);
  });

  test('VAL-001: Zero fallback validation across all endpoints', async ({ request }) => {
    const endpoints = [
      { path: '/api/analogs', params: { horizon: '24h', variables: 't2m,u10,v10', count: '50' } },
      { path: '/forecast', params: { horizon: '24h', vars: 't2m,u10,v10' } }
    ];

    for (const endpoint of endpoints) {
      for (let i = 0; i < 20; i++) {
        const response = await request.get(`${baseURL}${endpoint.path}`, {
          params: endpoint.params,
          headers: { 'Authorization': `Bearer ${process.env.API_TOKEN || 'test-token-12345'}` }
        });

        expect(response.status()).toBe(200);
        
        const data = await response.json();
        
        // Check data source and fallback usage
        if (endpoint.path === '/api/analogs') {
          expect(data.search_stats.data_source).toBe('faiss');
          expect(data.search_stats.fallback_used).toBe(false);
        } else {
          expect(data.forecast.data_source).toBe('faiss');
          expect(data.performance_stats.fallback_used).toBe(false);
        }
      }
    }
    
    console.log('✓ Zero fallback validation passed for all endpoints');
  });

  test('MEM-001: Memory usage monitoring and validation', async ({ request }) => {
    // Get initial memory stats
    const initialResponse = await request.get(`${baseURL}/health/system`, {
      headers: { 'Authorization': `Bearer ${process.env.API_TOKEN || 'test-token-12345'}` }
    });

    expect(initialResponse.status()).toBe(200);
    const initialMemory = (await initialResponse.json()).memory_usage_mb;

    // Execute memory-intensive operations
    const operations = [];
    for (let i = 0; i < 25; i++) {
      operations.push(
        request.get(`${baseURL}/api/analogs`, {
          params: {
            horizon: '48h',
            variables: 't2m,u10,v10,z500,t850,q850,cape',
            count: '500'
          },
          headers: { 'Authorization': `Bearer ${process.env.API_TOKEN || 'test-token-12345'}` }
        })
      );
    }

    await Promise.all(operations);

    // Check memory usage after operations
    const finalResponse = await request.get(`${baseURL}/health/system`, {
      headers: { 'Authorization': `Bearer ${process.env.API_TOKEN || 'test-token-12345'}` }
    });

    const finalMemory = (await finalResponse.json()).memory_usage_mb;
    const memoryIncrease = finalMemory - initialMemory;

    // Memory usage should not increase by more than 500MB during operations
    expect(memoryIncrease).toBeLessThan(500);
    
    console.log(`✓ Memory validation passed - Increase: ${memoryIncrease}MB (initial: ${initialMemory}MB, final: ${finalMemory}MB)`);
  });

  test.afterAll(async () => {
    // Generate performance report
    const performanceReport = apiTestSuite.getPerformanceReport();
    
    console.log('\n=== TEST2 Performance Report ===');
    console.log(JSON.stringify(performanceReport, null, 2));
    
    // Validate overall performance requirements
    if (performanceReport['/api/analogs']) {
      expect(performanceReport['/api/analogs'].p95_latency_ms).toBeLessThan(150);
      expect(performanceReport['/api/analogs'].success_rate).toBeGreaterThan(0.99);
    }
    
    if (performanceReport['/forecast']) {
      expect(performanceReport['/forecast'].p95_latency_ms).toBeLessThan(150);
      expect(performanceReport['/forecast'].success_rate).toBeGreaterThan(0.99);
    }
    
    console.log('✓ All TEST2 integration and performance requirements met');
  });
});