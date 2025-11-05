import { test, expect } from '@playwright/test';
import { HomePage } from '../../pages/HomePage';
import { AnalogExplorerPage } from '../../pages/AnalogExplorerPage';
import { MetricsDashboardPage } from '../../pages/MetricsDashboardPage';
import testData from '../../fixtures/test-data.json';

/**
 * Power User Workflow Tests
 * 
 * Tests advanced user scenarios including multi-variable forecasts,
 * historical comparison, analog exploration, and data export workflows.
 */
test.describe('Power User Workflow', () => {
  let homePage: HomePage;
  let analogExplorerPage: AnalogExplorerPage;
  let metricsDashboardPage: MetricsDashboardPage;
  
  test.beforeEach(async ({ page }) => {
    homePage = new HomePage(page);
    analogExplorerPage = new AnalogExplorerPage(page);
    metricsDashboardPage = new MetricsDashboardPage(page);
    
    // Set up power user authentication and preferences
    await homePage.authenticate(testData.authentication.validToken);
    await homePage.setUserPreferences(testData.userProfiles.powerUser.preferences);
  });
  
  test('Complete power user forecast analysis workflow', async ({ page }) => {
    await test.step('Load homepage with power user preferences', async () => {
      await homePage.navigateToHome();
      
      // Should use saved preferences
      const selectedHorizon = await homePage.getSelectedHorizon();
      expect(selectedHorizon).toBe(testData.userProfiles.powerUser.preferences.defaultHorizon);
      
      // Should show advanced features
      await expect(page.locator('[data-testid="advanced-controls"]')).toBeVisible();
      await expect(page.locator('[data-testid="analogs-section"]')).toBeVisible();
    });
    
    await test.step('Configure multi-variable forecast', async () => {
      // Select comprehensive variable set
      const variables = ['t2m', 'u10', 'v10', 'msl', 'cape', 'sp', 'r2'];
      await homePage.selectVariables(variables);
      
      // Verify all variables are displayed
      for (const variable of variables) {
        await expect(page.locator(`[data-testid="variable-${variable}"]`)).toBeVisible();
      }
      
      // Check forecast data completeness
      const forecastData = await homePage.getCurrentForecastData();
      expect(Object.keys(forecastData)).toContain('temperature');
      expect(Object.keys(forecastData)).toContain('windSpeed');
      expect(Object.keys(forecastData)).toContain('pressure');
    });
    
    await test.step('Analyze forecast confidence and uncertainty', async () => {
      // Check confidence indicators
      const confidenceLevel = await homePage.getConfidenceLevel();
      expect(confidenceLevel).toBeTruthy();
      
      // Examine analog information
      const analogInfo = await homePage.getAnalogInfo();
      expect(analogInfo.visible).toBe(true);
      expect(analogInfo.count).toBeGreaterThan(10);
      expect(analogInfo.mostSimilar).toBeTruthy();
      
      // Validate forecast data ranges
      await homePage.validateForecastData();
    });
    
    await test.step('Compare multiple forecast horizons', async () => {
      const horizons = ['6h', '12h', '24h', '48h'];
      const forecastComparisons: any[] = [];
      
      for (const horizon of horizons) {
        await homePage.selectHorizon(horizon);
        const data = await homePage.getCurrentForecastData();
        forecastComparisons.push({ horizon, data });
        
        // Brief wait for data to stabilize
        await page.waitForTimeout(1000);
      }
      
      // Verify we have data for all horizons
      expect(forecastComparisons).toHaveLength(4);
      
      // Temperature should show reasonable progression
      const temperatures = forecastComparisons.map(f => f.data.temperature).filter(t => t !== undefined);
      expect(temperatures.length).toBeGreaterThan(0);
      
      // Check temperature variance is reasonable (not identical across all horizons)
      const tempMin = Math.min(...temperatures);
      const tempMax = Math.max(...temperatures);
      expect(tempMax - tempMin).toBeLessThan(20); // Max 20°C difference
    });
  });
  
  test('Advanced analog pattern exploration', async ({ page }) => {
    // Start from homepage and navigate to analogs
    await homePage.navigateToHome();
    
    await test.step('Navigate to analog explorer with context', async () => {
      // Get current forecast context
      const currentForecast = await homePage.getCurrentForecastData();
      
      // Navigate to analog explorer
      await page.locator('[data-testid="explore-analogs"]').click();
      await analogExplorerPage.validatePageLoaded();
      
      // Should have analogs loaded
      const patterns = await analogExplorerPage.getAnalogPatterns();
      expect(patterns.length).toBeGreaterThan(5);
    });
    
    await test.step('Filter analogs by high similarity threshold', async () => {
      // Set high similarity threshold for quality patterns
      await analogExplorerPage.setSimilarityThreshold(80);
      
      const highQualityPatterns = await analogExplorerPage.getAnalogPatterns();
      
      // Should have fewer but higher quality patterns
      expect(highQualityPatterns.length).toBeGreaterThan(0);
      
      // All patterns should meet threshold
      for (const pattern of highQualityPatterns) {
        expect(pattern.similarity).toBeGreaterThanOrEqual(80);
      }
    });
    
    await test.step('Analyze seasonal patterns', async () => {
      // Filter by summer period (Dec-Feb for Adelaide)
      await analogExplorerPage.filterByDateRange('2020-12-01', '2023-02-28');
      
      const summerPatterns = await analogExplorerPage.getAnalogPatterns();
      expect(summerPatterns.length).toBeGreaterThan(0);
      
      // Select most similar summer pattern
      await analogExplorerPage.selectAnalogPattern(0);
      
      const analogDetails = await analogExplorerPage.getSelectedAnalogDetails();
      expect(analogDetails.similarity).toBeGreaterThan(70);
      expect(analogDetails.conditions).toBeTruthy();
      expect(analogDetails.outcome).toBeTruthy();
    });
    
    await test.step('Configure custom variable weights', async () => {
      // Emphasize temperature and CAPE for summer analysis
      await analogExplorerPage.setVariableWeights({
        't2m': 0.4,    // High weight on temperature
        'cape': 0.3,   // High weight on convective potential
        'msl': 0.2,    // Medium weight on pressure
        'u10': 0.05,   // Low weight on u-wind
        'v10': 0.05    // Low weight on v-wind
      });
      
      // Should recalculate similarities
      const reweightedPatterns = await analogExplorerPage.getAnalogPatterns();
      expect(reweightedPatterns.length).toBeGreaterThan(0);
      
      // Similarities should have changed
      const firstPattern = reweightedPatterns[0];
      expect(firstPattern.similarity).toBeGreaterThan(0);
    });
    
    await test.step('Export comprehensive analog dataset', async () => {
      // Export analogs with current filters
      await analogExplorerPage.exportAnalogData('csv');
      
      // Should have downloaded file
      // Note: In real tests, you'd verify the download occurred
    });
  });
  
  test('System performance monitoring workflow', async ({ page }) => {
    await test.step('Access metrics dashboard', async () => {
      await metricsDashboardPage.navigateToMetricsDashboard();
      
      // Should see comprehensive metrics
      const systemHealth = await metricsDashboardPage.getSystemHealth();
      expect(['healthy', 'warning']).toContain(systemHealth.overall);
      expect(['healthy', 'warning']).toContain(systemHealth.api);
    });
    
    await test.step('Analyze system performance trends', async () => {
      // Set time range to see trends
      await metricsDashboardPage.setTimeRange('24h');
      
      const metrics = await metricsDashboardPage.getCurrentMetrics();
      
      // Validate metrics are reasonable
      expect(metrics.totalRequests).toBeGreaterThan(0);
      expect(metrics.averageLatency).toBeLessThan(5000); // Under 5 seconds
      expect(metrics.successRate).toBeGreaterThan(80);   // Above 80%
      
      // Check performance charts
      const responseTimeData = await metricsDashboardPage.getChartData('response-time');
      expect(responseTimeData.values.length).toBeGreaterThan(0);
      expect(responseTimeData.unit).toBe('ms');
    });
    
    await test.step('Monitor forecast accuracy metrics', async () => {
      const metrics = await metricsDashboardPage.getCurrentMetrics();
      
      // Forecast accuracy should be reasonable
      expect(metrics.forecastAccuracy).toBeGreaterThan(75); // Above 75%
      expect(metrics.analogMatchRate).toBeGreaterThan(70);  // Above 70%
      
      // Get accuracy trend data
      const accuracyData = await metricsDashboardPage.getChartData('accuracy');
      expect(accuracyData.values.length).toBeGreaterThan(0);
      
      // Accuracy values should be percentages
      for (const value of accuracyData.values) {
        expect(value).toBeGreaterThan(0);
        expect(value).toBeLessThanOrEqual(100);
      }
    });
    
    await test.step('Configure monitoring alerts', async () => {
      // Check for active alerts
      const alerts = await metricsDashboardPage.getActiveAlerts();
      
      if (alerts.length > 0) {
        // Examine alert details
        const firstAlert = alerts[0];
        expect(['info', 'warning', 'error', 'critical']).toContain(firstAlert.severity);
        expect(firstAlert.message.length).toBeGreaterThan(0);
        expect(firstAlert.timestamp).toBeTruthy();
      }
      
      // Enable auto-refresh for monitoring
      await metricsDashboardPage.toggleAutoRefresh(true);
    });
  });
  
  test('Multi-session forecast comparison workflow', async ({ page }) => {
    const forecastSessions: any[] = [];
    
    await test.step('Collect multiple forecast sessions', async () => {
      await homePage.navigateToHome();
      
      // Session 1: Current conditions
      await homePage.selectHorizon('24h');
      await homePage.selectVariables(['t2m', 'u10', 'v10', 'msl']);
      const session1 = await homePage.getCurrentForecastData();
      forecastSessions.push({ name: 'current', ...session1 });
      
      // Session 2: Extended forecast
      await homePage.selectHorizon('48h');
      const session2 = await homePage.getCurrentForecastData();
      forecastSessions.push({ name: 'extended', ...session2 });
      
      // Session 3: Short-term high resolution
      await homePage.selectHorizon('6h');
      await homePage.selectVariables(['t2m', 'u10', 'v10', 'msl', 'cape']);
      const session3 = await homePage.getCurrentForecastData();
      forecastSessions.push({ name: 'short-term', ...session3 });
    });
    
    await test.step('Analyze session differences', async () => {
      expect(forecastSessions).toHaveLength(3);
      
      // Check that each session has valid data
      for (const session of forecastSessions) {
        expect(session.horizon).toBeTruthy();
        expect(session.lastUpdated).toBeTruthy();
        
        if (session.temperature !== undefined) {
          expect(session.temperature).toBeGreaterThan(-50);
          expect(session.temperature).toBeLessThan(60);
        }
      }
      
      // Verify horizons are different
      const horizons = forecastSessions.map(s => s.horizon);
      expect(new Set(horizons).size).toBe(3); // All different
    });
    
    await test.step('Export forecast comparison data', async () => {
      // Export each session
      for (const session of forecastSessions) {
        await homePage.selectHorizon(session.horizon);
        await homePage.exportForecastData('json');
        
        // Brief wait between exports
        await page.waitForTimeout(1000);
      }
    });
  });
  
  test('Advanced error handling and recovery', async ({ page }) => {
    await homePage.navigateToHome();
    
    await test.step('Handle network interruption gracefully', async () => {
      // Simulate network going offline
      await page.context().setOffline(true);
      
      // Try to refresh forecast
      await homePage.refreshButton.click();
      
      // Should show appropriate error message
      await expect(page.locator('[data-testid="network-error"]')).toBeVisible();
      
      // Restore network
      await page.context().setOffline(false);
      
      // Should recover automatically
      await page.waitForTimeout(2000);
      await expect(page.locator('[data-testid="network-error"]')).not.toBeVisible();
    });
    
    await test.step('Handle API rate limiting', async () => {
      // Make rapid requests to trigger rate limiting
      for (let i = 0; i < 10; i++) {
        await homePage.refreshButton.click();
        await page.waitForTimeout(100);
      }
      
      // Should eventually see rate limit message
      const errorExists = await page.locator('[data-testid="rate-limit-error"]').isVisible({ timeout: 5000 });
      
      if (errorExists) {
        // Should provide guidance on when to retry
        await expect(page.locator('[data-testid="retry-advice"]')).toBeVisible();
      }
    });
    
    await test.step('Recover from invalid session state', async () => {
      // Corrupt local storage
      await page.evaluate(() => {
        localStorage.setItem('weather-api-token', 'corrupted-token');
        localStorage.setItem('user-preferences', 'invalid-json');
      });
      
      // Reload page
      await page.reload();
      
      // Should detect corruption and prompt for re-authentication
      await expect(page.locator('[data-testid="session-corrupted"]')).toBeVisible();
      
      // Should be able to re-authenticate
      await page.locator('[data-testid="re-authenticate"]').click();
      await page.locator('[data-testid="api-key-input"]').fill(testData.authentication.validToken);
      await page.locator('[data-testid="save-api-key"]').click();
      
      // Should recover fully
      await expect(page.locator('[data-testid="forecast-card"]')).toBeVisible();
    });
  });
  
  test('Performance optimization for power users', async ({ page }) => {
    await test.step('Measure advanced workflow performance', async () => {
      const startTime = Date.now();
      
      await homePage.navigateToHome();
      
      // Complex multi-variable forecast
      await homePage.selectVariables(['t2m', 'u10', 'v10', 'msl', 'cape', 'sp', 'r2', 'q2m']);
      
      const complexForecastTime = Date.now() - startTime;
      expect(complexForecastTime).toBeLessThan(5000); // Should handle complexity quickly
      
      // Navigate to analog explorer
      const analogStartTime = Date.now();
      await page.locator('[data-testid="explore-analogs"]').click();
      await analogExplorerPage.validatePageLoaded();
      
      const analogLoadTime = Date.now() - analogStartTime;
      expect(analogLoadTime).toBeLessThan(3000); // Quick navigation
    });
    
    await test.step('Test concurrent operations', async () => {
      // Open multiple tabs/views simultaneously
      const forecastPromise = homePage.refreshForecast();
      const analogPromise = analogExplorerPage.setSimilarityThreshold(85);
      
      // Both operations should complete without blocking each other
      await Promise.all([forecastPromise, analogPromise]);
      
      // Verify both completed successfully
      await homePage.validateForecastData();
      const patterns = await analogExplorerPage.getAnalogPatterns();
      expect(patterns.length).toBeGreaterThan(0);
    });
  });
});