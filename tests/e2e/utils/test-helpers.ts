import { Page, expect, Locator } from '@playwright/test';
import testData from '../fixtures/test-data.json';

/**
 * Comprehensive Test Helper Utilities
 * 
 * Provides reusable functions for common testing operations,
 * data validation, performance measurement, and test setup.
 */

export interface WeatherTestData {
  temperature?: number;
  windSpeed?: number;
  windDirection?: number;
  pressure?: number;
  cape?: number;
  humidity?: number;
}

export interface TestMetrics {
  loadTime: number;
  firstContentfulPaint: number;
  largestContentfulPaint: number;
  cumulativeLayoutShift: number;
  firstInputDelay: number;
}

export interface NetworkCondition {
  downloadThroughput: number;
  uploadThroughput: number;
  latency: number;
}

/**
 * Authentication and Session Management
 */
export class AuthHelper {
  constructor(private page: Page) {}
  
  async authenticateUser(token: string = testData.authentication.validToken): Promise<void> {
    await this.page.evaluate((apiToken) => {
      localStorage.setItem('weather-api-token', apiToken);
    }, token);
  }
  
  async clearAuthentication(): Promise<void> {
    await this.page.evaluate(() => {
      localStorage.removeItem('weather-api-token');
      localStorage.removeItem('user-preferences');
      sessionStorage.clear();
    });
  }
  
  async setUserPreferences(preferences: Record<string, any>): Promise<void> {
    await this.page.evaluate((prefs) => {
      localStorage.setItem('user-preferences', JSON.stringify(prefs));
    }, preferences);
  }
  
  async getUserPreferences(): Promise<Record<string, any>> {
    return await this.page.evaluate(() => {
      const prefs = localStorage.getItem('user-preferences');
      return prefs ? JSON.parse(prefs) : {};
    });
  }
  
  async isAuthenticated(): Promise<boolean> {
    return await this.page.evaluate(() => {
      return !!localStorage.getItem('weather-api-token');
    });
  }
}

/**
 * Data Validation Utilities
 */
export class DataValidator {
  /**
   * Validate weather data is within reasonable bounds
   */
  static validateWeatherData(data: WeatherTestData): void {
    if (data.temperature !== undefined) {
      expect(data.temperature).toBeGreaterThan(-50);
      expect(data.temperature).toBeLessThan(60);
    }
    
    if (data.windSpeed !== undefined) {
      expect(data.windSpeed).toBeGreaterThanOrEqual(0);
      expect(data.windSpeed).toBeLessThan(200);
    }
    
    if (data.windDirection !== undefined) {
      expect(data.windDirection).toBeGreaterThanOrEqual(0);
      expect(data.windDirection).toBeLessThan(360);
    }
    
    if (data.pressure !== undefined) {
      expect(data.pressure).toBeGreaterThan(800);
      expect(data.pressure).toBeLessThan(1100);
    }
    
    if (data.cape !== undefined) {
      expect(data.cape).toBeGreaterThanOrEqual(0);
      expect(data.cape).toBeLessThan(10000);
    }
    
    if (data.humidity !== undefined) {
      expect(data.humidity).toBeGreaterThanOrEqual(0);
      expect(data.humidity).toBeLessThanOrEqual(100);
    }
  }
  
  /**
   * Validate forecast response structure
   */
  static validateForecastResponse(response: any): void {
    expect(response).toHaveProperty('horizon');
    expect(response).toHaveProperty('generated_at');
    expect(response).toHaveProperty('variables');
    expect(response).toHaveProperty('narrative');
    expect(response).toHaveProperty('risk_assessment');
    expect(response).toHaveProperty('analogs_summary');
    expect(response).toHaveProperty('latency_ms');
    
    // Validate variables structure
    const variables = response.variables;
    expect(typeof variables).toBe('object');
    
    for (const [varName, varData] of Object.entries(variables as any)) {
      expect(varData).toHaveProperty('available');
      expect(typeof varData.available).toBe('boolean');
      
      if (varData.available) {
        expect(varData).toHaveProperty('value');
        expect(varData).toHaveProperty('p05');
        expect(varData).toHaveProperty('p95');
        expect(varData).toHaveProperty('confidence');
        
        // Value should be between p05 and p95
        expect(varData.p05).toBeLessThanOrEqual(varData.value);
        expect(varData.value).toBeLessThanOrEqual(varData.p95);
        
        // Confidence should be between 0 and 1
        expect(varData.confidence).toBeGreaterThanOrEqual(0);
        expect(varData.confidence).toBeLessThanOrEqual(1);
      }
    }
    
    // Validate risk assessment
    const risks = response.risk_assessment;
    expect(risks).toHaveProperty('thunderstorm');
    expect(risks).toHaveProperty('heat_stress');
    expect(risks).toHaveProperty('wind_damage');
    expect(risks).toHaveProperty('precipitation');
    
    const validRiskLevels = ['minimal', 'low', 'moderate', 'high', 'extreme'];
    expect(validRiskLevels).toContain(risks.thunderstorm);
    expect(validRiskLevels).toContain(risks.heat_stress);
    expect(validRiskLevels).toContain(risks.wind_damage);
    expect(validRiskLevels).toContain(risks.precipitation);
    
    // Validate analogs summary
    const analogs = response.analogs_summary;
    expect(analogs).toHaveProperty('similarity_score');
    expect(analogs).toHaveProperty('analog_count');
    expect(analogs).toHaveProperty('outcome_description');
    
    expect(analogs.similarity_score).toBeGreaterThanOrEqual(0);
    expect(analogs.similarity_score).toBeLessThanOrEqual(1);
    expect(analogs.analog_count).toBeGreaterThan(0);
    expect(analogs.outcome_description.length).toBeGreaterThan(0);
  }
  
  /**
   * Validate API error response structure
   */
  static validateErrorResponse(response: any, expectedStatus: number): void {
    expect(response).toHaveProperty('error');
    expect(response.error).toHaveProperty('code');
    expect(response.error).toHaveProperty('message');
    expect(response.error).toHaveProperty('timestamp');
    
    expect(response.error.code).toBe(expectedStatus);
    expect(response.error.message.length).toBeGreaterThan(0);
    
    // Timestamp should be valid ISO date
    const timestamp = new Date(response.error.timestamp);
    expect(timestamp.getTime()).not.toBeNaN();
  }
}

/**
 * Performance Measurement Utilities
 */
export class PerformanceHelper {
  constructor(private page: Page) {}
  
  /**
   * Measure Core Web Vitals
   */
  async measureCoreWebVitals(): Promise<TestMetrics> {
    return await this.page.evaluate(() => {
      return new Promise((resolve) => {
        const metrics: any = {
          loadTime: 0,
          firstContentfulPaint: 0,
          largestContentfulPaint: 0,
          cumulativeLayoutShift: 0,
          firstInputDelay: 0
        };
        
        // Measure load time
        const perfData = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
        metrics.loadTime = perfData.loadEventEnd - perfData.loadEventStart;
        
        // Measure paint metrics
        const paintEntries = performance.getEntriesByType('paint');
        const fcp = paintEntries.find(entry => entry.name === 'first-contentful-paint');
        if (fcp) metrics.firstContentfulPaint = fcp.startTime;
        
        // LCP observer
        new PerformanceObserver((list) => {
          const entries = list.getEntries();
          if (entries.length > 0) {
            metrics.largestContentfulPaint = entries[entries.length - 1].startTime;
          }
        }).observe({ entryTypes: ['largest-contentful-paint'] });
        
        // FID observer
        new PerformanceObserver((list) => {
          const entries = list.getEntries();
          if (entries.length > 0) {
            const entry = entries[0] as any;
            metrics.firstInputDelay = entry.processingStart - entry.startTime;
          }
        }).observe({ entryTypes: ['first-input'] });
        
        // CLS observer
        new PerformanceObserver((list) => {
          const entries = list.getEntries();
          entries.forEach((entry: any) => {
            if (!entry.hadRecentInput) {
              metrics.cumulativeLayoutShift += entry.value;
            }
          });
        }).observe({ entryTypes: ['layout-shift'] });
        
        // Resolve after collecting metrics
        setTimeout(() => resolve(metrics), 3000);
      });
    });
  }
  
  /**
   * Measure API response time
   */
  async measureApiResponseTime(endpoint: string): Promise<number> {
    const startTime = Date.now();
    
    const responsePromise = this.page.waitForResponse(response => 
      response.url().includes(endpoint)
    );
    
    await responsePromise;
    
    return Date.now() - startTime;
  }
  
  /**
   * Validate performance thresholds
   */
  validatePerformanceThresholds(metrics: TestMetrics): void {
    const thresholds = testData.performanceThresholds.pageLoad;
    
    expect(metrics.firstContentfulPaint).toBeLessThan(thresholds.maxFirstContentfulPaint);
    expect(metrics.largestContentfulPaint).toBeLessThan(thresholds.maxLargestContentfulPaint);
    expect(metrics.cumulativeLayoutShift).toBeLessThan(thresholds.maxCumulativeLayoutShift);
    expect(metrics.firstInputDelay).toBeLessThan(thresholds.maxFirstInputDelay);
  }
}

/**
 * Network Simulation Utilities
 */
export class NetworkHelper {
  constructor(private page: Page) {}
  
  /**
   * Simulate network conditions
   */
  async setNetworkConditions(condition: 'fast' | 'slow3G' | 'offline'): Promise<void> {
    const conditions = testData.networkConditions[condition];
    
    if (condition === 'offline') {
      await this.page.context().setOffline(true);
    } else {
      await this.page.context().setOffline(false);
      // Note: Playwright doesn't have built-in network throttling like Puppeteer
      // This would need to be implemented via browser flags or network proxy
    }
  }
  
  /**
   * Simulate intermittent connectivity
   */
  async simulateIntermittentConnectivity(durationMs: number = 30000): Promise<void> {
    const pattern = testData.networkConditions.intermittent.pattern;
    let totalTime = 0;
    
    while (totalTime < durationMs) {
      for (const phase of pattern) {
        await this.page.context().setOffline(!phase.online);
        await this.page.waitForTimeout(Math.min(phase.duration, durationMs - totalTime));
        totalTime += phase.duration;
        
        if (totalTime >= durationMs) break;
      }
    }
    
    // Ensure we end online
    await this.page.context().setOffline(false);
  }
  
  /**
   * Monitor network requests
   */
  async monitorNetworkRequests(duration: number = 10000): Promise<{
    requests: number;
    responses: number;
    errors: number;
    avgLatency: number;
  }> {
    const metrics = {
      requests: 0,
      responses: 0,
      errors: 0,
      latencies: [] as number[]
    };
    
    const requestHandler = (request: any) => {
      metrics.requests++;
      request._startTime = Date.now();
    };
    
    const responseHandler = (response: any) => {
      metrics.responses++;
      if (response.request()._startTime) {
        const latency = Date.now() - response.request()._startTime;
        metrics.latencies.push(latency);
      }
      if (response.status() >= 400) {
        metrics.errors++;
      }
    };
    
    this.page.on('request', requestHandler);
    this.page.on('response', responseHandler);
    
    await this.page.waitForTimeout(duration);
    
    this.page.off('request', requestHandler);
    this.page.off('response', responseHandler);
    
    const avgLatency = metrics.latencies.length > 0 
      ? metrics.latencies.reduce((a, b) => a + b, 0) / metrics.latencies.length
      : 0;
    
    return {
      requests: metrics.requests,
      responses: metrics.responses,
      errors: metrics.errors,
      avgLatency
    };
  }
}

/**
 * Visual Testing Utilities
 */
export class VisualHelper {
  constructor(private page: Page) {}
  
  /**
   * Take screenshot with timestamp
   */
  async takeTimestampedScreenshot(name: string): Promise<string> {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `${name}-${timestamp}.png`;
    const path = `./tests/e2e/reports/screenshots/${filename}`;
    
    await this.page.screenshot({
      path,
      fullPage: true,
    });
    
    return path;
  }
  
  /**
   * Compare visual elements
   */
  async compareElement(selector: string, name: string): Promise<void> {
    const element = this.page.locator(selector);
    await expect(element).toHaveScreenshot(`${name}.png`);
  }
  
  /**
   * Check element visibility in viewport
   */
  async isElementInViewport(selector: string): Promise<boolean> {
    return await this.page.locator(selector).evaluate(el => {
      const rect = el.getBoundingClientRect();
      return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
      );
    });
  }
  
  /**
   * Validate responsive design breakpoints
   */
  async validateResponsiveBreakpoints(selector: string): Promise<{
    mobile: boolean;
    tablet: boolean;
    desktop: boolean;
  }> {
    const results = { mobile: false, tablet: false, desktop: false };
    
    // Mobile (390x844)
    await this.page.setViewportSize({ width: 390, height: 844 });
    await this.page.waitForTimeout(500);
    results.mobile = await this.page.locator(selector).isVisible();
    
    // Tablet (768x1024)
    await this.page.setViewportSize({ width: 768, height: 1024 });
    await this.page.waitForTimeout(500);
    results.tablet = await this.page.locator(selector).isVisible();
    
    // Desktop (1920x1080)
    await this.page.setViewportSize({ width: 1920, height: 1080 });
    await this.page.waitForTimeout(500);
    results.desktop = await this.page.locator(selector).isVisible();
    
    return results;
  }
}

/**
 * Accessibility Testing Utilities
 */
export class AccessibilityHelper {
  constructor(private page: Page) {}
  
  /**
   * Check ARIA attributes
   */
  async validateAriaAttributes(selector: string): Promise<{
    hasRole: boolean;
    hasLabel: boolean;
    hasDescription: boolean;
    isKeyboardAccessible: boolean;
  }> {
    const element = this.page.locator(selector);
    
    const role = await element.getAttribute('role');
    const ariaLabel = await element.getAttribute('aria-label');
    const ariaLabelledBy = await element.getAttribute('aria-labelledby');
    const ariaDescribedBy = await element.getAttribute('aria-describedby');
    const tabIndex = await element.getAttribute('tabindex');
    const tagName = await element.evaluate(el => el.tagName.toLowerCase());
    
    const interactiveTags = ['button', 'input', 'select', 'textarea', 'a'];
    const isInteractive = interactiveTags.includes(tagName) || role === 'button' || role === 'link';
    
    return {
      hasRole: !!role,
      hasLabel: !!(ariaLabel || ariaLabelledBy),
      hasDescription: !!ariaDescribedBy,
      isKeyboardAccessible: isInteractive && (tabIndex !== '-1')
    };
  }
  
  /**
   * Test keyboard navigation
   */
  async testKeyboardNavigation(startSelector: string, targetSelector: string): Promise<boolean> {
    await this.page.locator(startSelector).focus();
    
    let attempts = 0;
    const maxAttempts = 20;
    
    while (attempts < maxAttempts) {
      await this.page.keyboard.press('Tab');
      
      const focusedElement = await this.page.evaluate(() => 
        document.activeElement?.getAttribute('data-testid') || 
        document.activeElement?.tagName?.toLowerCase()
      );
      
      if (focusedElement === targetSelector.replace('[data-testid="', '').replace('"]', '')) {
        return true;
      }
      
      attempts++;
    }
    
    return false;
  }
  
  /**
   * Check color contrast
   */
  async checkColorContrast(selector: string): Promise<{
    ratio: number;
    passes: boolean;
  }> {
    return await this.page.locator(selector).evaluate(el => {
      const style = window.getComputedStyle(el);
      const color = style.color;
      const backgroundColor = style.backgroundColor;
      
      // Simplified contrast check - in real implementation,
      // you'd use a proper color contrast library
      const colorLuminance = 0.5; // Placeholder
      const bgLuminance = 0.8;    // Placeholder
      
      const ratio = (Math.max(colorLuminance, bgLuminance) + 0.05) / 
                   (Math.min(colorLuminance, bgLuminance) + 0.05);
      
      return {
        ratio,
        passes: ratio >= 4.5 // WCAG AA standard
      };
    });
  }
}

/**
 * Wait and Retry Utilities
 */
export class WaitHelper {
  /**
   * Wait for condition with timeout and retry
   */
  static async waitForCondition(
    conditionFn: () => Promise<boolean>,
    timeoutMs: number = 10000,
    intervalMs: number = 500
  ): Promise<void> {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeoutMs) {
      if (await conditionFn()) {
        return;
      }
      
      await new Promise(resolve => setTimeout(resolve, intervalMs));
    }
    
    throw new Error(`Condition not met within ${timeoutMs}ms`);
  }
  
  /**
   * Retry operation with exponential backoff
   */
  static async retryOperation<T>(
    operation: () => Promise<T>,
    maxRetries: number = 3,
    baseDelayMs: number = 1000
  ): Promise<T> {
    let lastError: Error;
    
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error as Error;
        
        if (attempt < maxRetries) {
          const delay = baseDelayMs * Math.pow(2, attempt);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }
    
    throw lastError!;
  }
}

/**
 * Test Data Generators
 */
export class TestDataGenerator {
  /**
   * Generate realistic weather test data
   */
  static generateWeatherData(scenario: 'typical' | 'extreme' | 'storm' = 'typical'): WeatherTestData {
    switch (scenario) {
      case 'extreme':
        return {
          temperature: 45 + Math.random() * 10,
          windSpeed: 15 + Math.random() * 10,
          windDirection: Math.random() * 360,
          pressure: 1000 + Math.random() * 50,
          cape: 2000 + Math.random() * 2000
        };
      
      case 'storm':
        return {
          temperature: 20 + Math.random() * 15,
          windSpeed: 20 + Math.random() * 20,
          windDirection: Math.random() * 360,
          pressure: 980 + Math.random() * 40,
          cape: 1500 + Math.random() * 3000
        };
      
      default: // typical
        return {
          temperature: 15 + Math.random() * 20,
          windSpeed: Math.random() * 15,
          windDirection: Math.random() * 360,
          pressure: 1000 + Math.random() * 30,
          cape: Math.random() * 1000
        };
    }
  }
  
  /**
   * Generate test API responses
   */
  static generateForecastResponse(data: WeatherTestData): any {
    return {
      horizon: '24h',
      generated_at: new Date().toISOString(),
      variables: {
        t2m: {
          value: data.temperature || 20,
          p05: (data.temperature || 20) - 5,
          p95: (data.temperature || 20) + 5,
          confidence: 0.8,
          available: true,
          analog_count: 35
        },
        u10: {
          value: -(data.windSpeed || 5) * Math.cos((data.windDirection || 0) * Math.PI / 180),
          p05: -(data.windSpeed || 5) * Math.cos((data.windDirection || 0) * Math.PI / 180) - 2,
          p95: -(data.windSpeed || 5) * Math.cos((data.windDirection || 0) * Math.PI / 180) + 2,
          confidence: 0.7,
          available: true,
          analog_count: 35
        },
        v10: {
          value: -(data.windSpeed || 5) * Math.sin((data.windDirection || 0) * Math.PI / 180),
          p05: -(data.windSpeed || 5) * Math.sin((data.windDirection || 0) * Math.PI / 180) - 2,
          p95: -(data.windSpeed || 5) * Math.sin((data.windDirection || 0) * Math.PI / 180) + 2,
          confidence: 0.7,
          available: true,
          analog_count: 35
        },
        msl: {
          value: (data.pressure || 1013) * 100,
          p05: ((data.pressure || 1013) - 10) * 100,
          p95: ((data.pressure || 1013) + 10) * 100,
          confidence: 0.9,
          available: true,
          analog_count: 35
        }
      },
      narrative: `Forecast shows ${data.temperature ? 'warm' : 'mild'} conditions`,
      risk_assessment: {
        thunderstorm: data.cape && data.cape > 1000 ? 'high' : 'low',
        heat_stress: data.temperature && data.temperature > 35 ? 'high' : 'minimal',
        wind_damage: data.windSpeed && data.windSpeed > 15 ? 'moderate' : 'minimal',
        precipitation: 'low'
      },
      analogs_summary: {
        most_similar_date: '2023-03-15T12:00:00Z',
        similarity_score: 0.85,
        analog_count: 35,
        outcome_description: 'Similar patterns resulted in stable conditions',
        confidence_explanation: 'High confidence based on 35 analog matches'
      },
      confidence_explanation: 'High confidence forecast',
      versions: {
        model: 'v1.0.0',
        index: 'v1.0.0',
        datasets: 'v1.0.0',
        api_schema: 'v1.1.0'
      },
      hashes: {
        model: 'a7c3f92',
        index: '2e8b4d1',
        datasets: 'd4f8a91'
      },
      latency_ms: 150 + Math.random() * 100
    };
  }
}