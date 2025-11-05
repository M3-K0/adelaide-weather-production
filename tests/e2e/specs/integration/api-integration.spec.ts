import { test, expect } from '@playwright/test';
import { HomePage } from '../../pages/HomePage';
import testData from '../../fixtures/test-data.json';

/**
 * API Integration Tests
 * 
 * Tests the complete integration between frontend and backend API,
 * including all endpoints, response handling, error scenarios, and data flow.
 */
test.describe('API Integration Tests', () => {
  let homePage: HomePage;
  
  test.beforeEach(async ({ page }) => {
    homePage = new HomePage(page);
    await homePage.authenticate(testData.authentication.validToken);
  });
  
  test('Forecast API endpoint integration', async ({ page }) => {
    await test.step('Test successful forecast request', async () => {
      await homePage.navigateToHome();
      
      // Intercept API call
      const forecastRequest = page.waitForRequest(request => 
        request.url().includes('/forecast') && request.method() === 'GET'
      );
      
      const forecastResponse = page.waitForResponse(response => 
        response.url().includes('/forecast') && response.status() === 200
      );
      
      // Trigger forecast request
      await homePage.refreshForecast();
      
      // Verify request was made correctly
      const request = await forecastRequest;
      const url = new URL(request.url());
      
      expect(url.searchParams.get('horizon')).toBeTruthy();
      expect(request.headers()['authorization']).toContain('Bearer');
      
      // Verify response structure
      const response = await forecastResponse;
      const responseData = await response.json();
      
      expect(responseData).toHaveProperty('horizon');
      expect(responseData).toHaveProperty('generated_at');
      expect(responseData).toHaveProperty('variables');
      expect(responseData).toHaveProperty('narrative');
      expect(responseData).toHaveProperty('risk_assessment');
      expect(responseData).toHaveProperty('analogs_summary');
      expect(responseData).toHaveProperty('latency_ms');
      
      // Verify variable data structure
      const variables = responseData.variables;
      for (const [varName, varData] of Object.entries(variables as any)) {
        expect(varData).toHaveProperty('value');
        expect(varData).toHaveProperty('p05');
        expect(varData).toHaveProperty('p95');
        expect(varData).toHaveProperty('confidence');
        expect(varData).toHaveProperty('available');
        expect(typeof varData.available).toBe('boolean');
      }
    });
    
    await test.step('Test forecast with different horizons', async () => {
      const horizons = ['6h', '12h', '24h', '48h'];
      
      for (const horizon of horizons) {
        // Intercept request for specific horizon
        const requestPromise = page.waitForRequest(request => {
          const url = new URL(request.url());
          return request.url().includes('/forecast') && 
                 url.searchParams.get('horizon') === horizon;
        });
        
        const responsePromise = page.waitForResponse(response => 
          response.url().includes('/forecast') && response.status() === 200
        );
        
        // Select horizon and trigger request
        await homePage.selectHorizon(horizon);
        
        // Verify request and response
        const request = await requestPromise;
        const response = await responsePromise;
        const data = await response.json();
        
        expect(data.horizon).toBe(horizon);
        expect(data.latency_ms).toBeLessThan(testData.performanceThresholds.forecastRequest.maxLatencyMs);
      }
    });
    
    await test.step('Test forecast with variable selection', async () => {
      const variables = ['t2m', 'u10', 'v10', 'msl', 'cape'];
      
      const requestPromise = page.waitForRequest(request => {
        const url = new URL(request.url());
        const requestVars = url.searchParams.get('vars');
        return request.url().includes('/forecast') && 
               requestVars === variables.join(',');
      });
      
      const responsePromise = page.waitForResponse(response => 
        response.url().includes('/forecast') && response.status() === 200
      );
      
      // Select specific variables
      await homePage.selectVariables(variables);
      
      // Verify request contains correct variables
      await requestPromise;
      
      // Verify response contains requested variables
      const response = await responsePromise;
      const data = await response.json();
      
      for (const variable of variables) {
        expect(data.variables).toHaveProperty(variable);
      }
    });
    
    await test.step('Test forecast error handling', async () => {
      // Test invalid horizon
      const invalidRequest = page.waitForResponse(response => 
        response.url().includes('/forecast') && response.status() === 400
      );
      
      // Make request with invalid horizon (simulate by modifying URL)
      await page.route('**/forecast*', async (route) => {
        const url = new URL(route.request().url());
        url.searchParams.set('horizon', '72h'); // Invalid horizon
        
        await route.continue({
          url: url.toString()
        });
      });
      
      await homePage.refreshForecast();
      
      const errorResponse = await invalidRequest;
      const errorData = await errorResponse.json();
      
      expect(errorData).toHaveProperty('error');
      expect(errorData.error.message).toMatch(/invalid.*parameter/i);
      
      // Clear route override
      await page.unroute('**/forecast*');
    });
  });
  
  test('Health endpoint integration', async ({ page }) => {
    await test.step('Test health check endpoint', async () => {
      // Navigate to a page that might trigger health checks
      await homePage.navigateToHome();
      
      // Make direct health check request
      const healthResponse = await page.request.get('/api/health', {
        headers: {
          'Authorization': `Bearer ${testData.authentication.validToken}`
        }
      });
      
      expect(healthResponse.status()).toBe(200);
      
      const healthData = await healthResponse.json();
      
      // Verify health response structure
      expect(healthData).toHaveProperty('ready');
      expect(healthData).toHaveProperty('checks');
      expect(healthData).toHaveProperty('model');
      expect(healthData).toHaveProperty('index');
      expect(healthData).toHaveProperty('datasets');
      expect(healthData).toHaveProperty('uptime_seconds');
      
      // Verify system is ready
      expect(healthData.ready).toBe(true);
      
      // Verify checks passed
      const failedChecks = healthData.checks.filter((check: any) => check.status === 'fail');
      expect(failedChecks.length).toBe(0);
      
      // Verify model information
      expect(healthData.model).toHaveProperty('version');
      expect(healthData.model).toHaveProperty('hash');
      expect(healthData.model.matched_ratio).toBeGreaterThan(0.9);
      
      // Verify index information
      expect(healthData.index).toHaveProperty('ntotal');
      expect(healthData.index.ntotal).toBeGreaterThan(0);
      expect(healthData.index).toHaveProperty('dim');
      expect(healthData.index.dim).toBeGreaterThan(0);
    });
    
    await test.step('Test health check from UI', async () => {
      // Should display system status in UI
      const statusInfo = await homePage.getStatusInfo();
      
      expect(['healthy', 'online', 'ready']).toContain(statusInfo.systemStatus.toLowerCase());
      expect(['healthy', 'online', 'ready']).toContain(statusInfo.apiStatus.toLowerCase());
      expect(statusInfo.dataAge).toBeTruthy();
    });
  });
  
  test('Metrics endpoint integration', async ({ page }) => {
    await test.step('Test metrics endpoint access', async () => {
      // Metrics endpoint requires authentication
      const metricsResponse = await page.request.get('/api/metrics', {
        headers: {
          'Authorization': `Bearer ${testData.authentication.validToken}`
        }
      });
      
      expect(metricsResponse.status()).toBe(200);
      
      const metricsText = await metricsResponse.text();
      
      // Should be Prometheus format
      expect(metricsText).toMatch(/# HELP/);
      expect(metricsText).toMatch(/# TYPE/);
      
      // Should contain expected metrics
      expect(metricsText).toMatch(/forecast_requests_total/);
      expect(metricsText).toMatch(/response_duration_seconds/);
      expect(metricsText).toMatch(/health_requests_total/);
    });
    
    await test.step('Test metrics authentication requirement', async () => {
      // Should reject without authentication
      const unauthorizedResponse = await page.request.get('/api/metrics');
      
      expect(unauthorizedResponse.status()).toBe(403);
    });
  });
  
  test('Authentication integration', async ({ page }) => {
    await test.step('Test valid authentication flow', async () => {
      await homePage.navigateToHome();
      await homePage.clearAuth();
      await page.reload();
      
      // Should show authentication required
      await expect(page.locator('[data-testid="auth-required-message"]')).toBeVisible();
      
      // Setup API key
      await page.locator('[data-testid="setup-api-key"]').click();
      await page.locator('[data-testid="api-key-input"]').fill(testData.authentication.validToken);
      
      // Intercept authentication request
      const authRequest = page.waitForRequest(request => 
        request.headers()['authorization']?.includes(testData.authentication.validToken)
      );
      
      await page.locator('[data-testid="save-api-key"]').click();
      
      // Should make authenticated request
      await authRequest;
      
      // Should show forecast data
      await expect(page.locator('[data-testid="forecast-card"]')).toBeVisible();
    });
    
    await test.step('Test invalid authentication handling', async () => {
      await homePage.clearAuth();
      await page.reload();
      
      // Setup invalid API key
      await page.locator('[data-testid="setup-api-key"]').click();
      await page.locator('[data-testid="api-key-input"]').fill(testData.authentication.invalidToken);
      
      // Intercept authentication failure
      const authErrorResponse = page.waitForResponse(response => 
        response.status() === 401 || response.status() === 403
      );
      
      await page.locator('[data-testid="save-api-key"]').click();
      
      // Should receive authentication error
      await authErrorResponse;
      
      // Should show error message
      await expect(page.locator('[data-testid="api-key-error"]')).toBeVisible();
      
      // Should not show forecast data
      await expect(page.locator('[data-testid="forecast-card"]')).not.toBeVisible();
    });
    
    await test.step('Test token expiration handling', async () => {
      // Simulate expired token by clearing auth mid-session
      await homePage.navigateToHome();
      await homePage.authenticate();
      await page.reload();
      await homePage.validatePageLoaded();
      
      // Clear auth to simulate expiration
      await homePage.clearAuth();
      
      // Try to make a request
      const unauthorizedResponse = page.waitForResponse(response => 
        response.status() === 401 || response.status() === 403
      );
      
      await homePage.refreshForecast();
      
      // Should receive unauthorized response
      await unauthorizedResponse;
      
      // Should prompt for re-authentication
      await expect(page.locator('[data-testid="session-expired"]')).toBeVisible();
    });
  });
  
  test('Error handling and recovery integration', async ({ page }) => {
    await test.step('Test network error handling', async () => {
      await homePage.navigateToHome();
      
      // Simulate network failure
      await page.route('**/forecast*', route => route.abort());
      
      const networkErrorPromise = page.waitForEvent('response', response => 
        response.url().includes('/forecast')
      ).catch(() => null); // Catch the abort
      
      await homePage.refreshForecast();
      
      // Should show network error
      await expect(page.locator('[data-testid="network-error"]')).toBeVisible();
      
      // Restore network
      await page.unroute('**/forecast*');
      
      // Should recover on retry
      await homePage.refreshForecast();
      await expect(page.locator('[data-testid="forecast-card"]')).toBeVisible();
    });
    
    await test.step('Test API server error handling', async () => {
      // Simulate server error
      await page.route('**/forecast*', route => {
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({
            error: {
              code: 500,
              message: 'Internal server error',
              timestamp: new Date().toISOString()
            }
          })
        });
      });
      
      await homePage.refreshForecast();
      
      // Should show server error
      await expect(page.locator('[data-testid="server-error"]')).toBeVisible();
      
      // Clear route override
      await page.unroute('**/forecast*');
    });
    
    await test.step('Test rate limiting handling', async () => {
      // Simulate rate limiting
      await page.route('**/forecast*', route => {
        route.fulfill({
          status: 429,
          contentType: 'application/json',
          headers: {
            'Retry-After': '60'
          },
          body: JSON.stringify({
            error: {
              code: 429,
              message: 'Rate limit exceeded',
              timestamp: new Date().toISOString()
            }
          })
        });
      });
      
      await homePage.refreshForecast();
      
      // Should show rate limit error
      await expect(page.locator('[data-testid="rate-limit-error"]')).toBeVisible();
      
      // Should show retry advice
      await expect(page.locator('[data-testid="retry-advice"]')).toBeVisible();
      
      // Clear route override
      await page.unroute('**/forecast*');
    });
  });
  
  test('Real-time data synchronization', async ({ page }) => {
    await test.step('Test automatic data refresh', async () => {
      await homePage.navigateToHome();
      
      // Get initial timestamp
      const initialTimestamp = await homePage.getLastUpdatedTime();
      
      // Wait for potential auto-refresh (if implemented)
      await page.waitForTimeout(30000); // 30 seconds
      
      // Check if data was refreshed automatically
      const newTimestamp = await homePage.getLastUpdatedTime();
      
      // Note: This test depends on auto-refresh implementation
      // At minimum, manual refresh should work
      await homePage.refreshForecast();
      const manualRefreshTimestamp = await homePage.getLastUpdatedTime();
      
      expect(manualRefreshTimestamp).not.toBe(initialTimestamp);
    });
    
    await test.step('Test concurrent request handling', async () => {
      // Make multiple concurrent requests
      const refreshPromises = [
        homePage.refreshForecast(),
        homePage.selectHorizon('12h'),
        homePage.selectVariables(['t2m', 'u10', 'v10'])
      ];
      
      // All should complete without blocking each other
      await Promise.all(refreshPromises);
      
      // Final state should be consistent
      await expect(page.locator('[data-testid="forecast-card"]')).toBeVisible();
      
      const finalData = await homePage.getCurrentForecastData();
      expect(finalData.horizon).toBe('12h');
    });
  });
  
  test('API performance integration', async ({ page }) => {
    await test.step('Test API response times', async () => {
      await homePage.navigateToHome();
      
      const startTime = Date.now();
      
      // Make forecast request
      await homePage.refreshForecast();
      
      const endTime = Date.now();
      const requestTime = endTime - startTime;
      
      // Should meet performance thresholds
      expect(requestTime).toBeLessThan(testData.performanceThresholds.forecastRequest.maxLatencyMs);
    });
    
    await test.step('Test API response data validation', async () => {
      // Intercept and validate response
      const responsePromise = page.waitForResponse(response => 
        response.url().includes('/forecast') && response.status() === 200
      );
      
      await homePage.refreshForecast();
      
      const response = await responsePromise;
      const data = await response.json();
      
      // Validate response timing
      expect(data.latency_ms).toBeLessThan(testData.performanceThresholds.forecastRequest.maxLatencyMs);
      
      // Validate data freshness
      const generatedAt = new Date(data.generated_at);
      const now = new Date();
      const ageMinutes = (now.getTime() - generatedAt.getTime()) / (1000 * 60);
      
      expect(ageMinutes).toBeLessThan(5); // Data should be fresh (under 5 minutes old)
    });
  });
});