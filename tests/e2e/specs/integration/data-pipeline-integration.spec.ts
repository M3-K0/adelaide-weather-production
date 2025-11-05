import { test, expect } from '@playwright/test';
import { HomePage } from '../../pages/HomePage';
import { AnalogExplorerPage } from '../../pages/AnalogExplorerPage';
import testData from '../../fixtures/test-data.json';

/**
 * Data Pipeline Integration Tests
 * 
 * Tests the complete data flow from weather data ingestion through
 * processing, model prediction, and UI display validation.
 */
test.describe('Data Pipeline Integration Tests', () => {
  let homePage: HomePage;
  let analogExplorerPage: AnalogExplorerPage;
  
  test.beforeEach(async ({ page }) => {
    homePage = new HomePage(page);
    analogExplorerPage = new AnalogExplorerPage(page);
    await homePage.authenticate(testData.authentication.validToken);
  });
  
  test('Weather data ingestion to forecast display pipeline', async ({ page }) => {
    await test.step('Verify fresh data ingestion indicators', async () => {
      await homePage.navigateToHome();
      
      // Check that data age indicators show recent ingestion
      const statusInfo = await homePage.getStatusInfo();
      expect(statusInfo.dataAge).toBeTruthy();
      
      // Data age should indicate recent updates
      expect(statusInfo.dataAge).toMatch(/(minutes?|hour|recent|fresh)/i);
      
      // System status should indicate healthy data pipeline
      expect(['healthy', 'online', 'ready']).toContain(statusInfo.systemStatus.toLowerCase());
    });
    
    await test.step('Validate data consistency across horizons', async () => {
      const horizonData: any[] = [];
      const horizons = ['6h', '12h', '24h', '48h'];
      
      for (const horizon of horizons) {
        await homePage.selectHorizon(horizon);
        const data = await homePage.getCurrentForecastData();
        horizonData.push({ horizon, ...data });
        
        // Brief wait for data stabilization
        await page.waitForTimeout(1000);
      }
      
      // Verify data progression makes meteorological sense
      const temperatures = horizonData
        .map(d => d.temperature)
        .filter(t => t !== undefined);
      
      if (temperatures.length > 1) {
        // Temperature variance should be reasonable across horizons
        const tempMin = Math.min(...temperatures);
        const tempMax = Math.max(...temperatures);
        const tempRange = tempMax - tempMin;
        
        // Should not have extreme variations (>25°C) across horizons
        expect(tempRange).toBeLessThan(25);
        
        // All temperatures should be within reasonable bounds
        temperatures.forEach(temp => {
          expect(temp).toBeGreaterThan(-50);
          expect(temp).toBeLessThan(60);
        });
      }
    });
    
    await test.step('Verify weather variable interdependencies', async () => {
      await homePage.selectVariables(['t2m', 'u10', 'v10', 'msl', 'cape']);
      await homePage.selectHorizon('24h');
      
      const forecastData = await homePage.getCurrentForecastData();
      
      // Wind speed should be calculated from u and v components
      if (forecastData.windSpeed !== undefined) {
        expect(forecastData.windSpeed).toBeGreaterThanOrEqual(0);
        expect(forecastData.windSpeed).toBeLessThan(200); // Max reasonable wind speed
      }
      
      // Wind direction should be in valid range
      if (forecastData.windDirection !== undefined) {
        expect(forecastData.windDirection).toBeGreaterThanOrEqual(0);
        expect(forecastData.windDirection).toBeLessThan(360);
      }
      
      // Pressure should be in reasonable range for Adelaide
      if (forecastData.pressure !== undefined) {
        expect(forecastData.pressure).toBeGreaterThan(950);  // Low pressure system
        expect(forecastData.pressure).toBeLessThan(1050);    // High pressure system
      }
      
      // CAPE values should be non-negative
      if (forecastData.cape !== undefined) {
        expect(forecastData.cape).toBeGreaterThanOrEqual(0);
        expect(forecastData.cape).toBeLessThan(10000); // Max reasonable CAPE
      }
    });
    
    await test.step('Test data temporal consistency', async () => {
      // Get forecast at current time
      const initialForecast = await homePage.getCurrentForecastData();
      const initialTimestamp = initialForecast.lastUpdated;
      
      // Wait and refresh
      await page.waitForTimeout(5000);
      await homePage.refreshForecast();
      
      const refreshedForecast = await homePage.getCurrentForecastData();
      const refreshedTimestamp = refreshedForecast.lastUpdated;
      
      // Timestamp should have updated
      expect(refreshedTimestamp).not.toBe(initialTimestamp);
      
      // Data should be consistent (within reasonable bounds)
      if (initialForecast.temperature && refreshedForecast.temperature) {
        const tempDiff = Math.abs(refreshedForecast.temperature - initialForecast.temperature);
        expect(tempDiff).toBeLessThan(5); // Temperature shouldn't change drastically in 5 seconds
      }
    });
  });
  
  test('Analog pattern matching pipeline validation', async ({ page }) => {
    await test.step('Navigate to analog explorer and verify data loading', async () => {
      await analogExplorerPage.navigateToAnalogExplorer();
      
      // Should load historical analog patterns
      const patterns = await analogExplorerPage.getAnalogPatterns();
      expect(patterns.length).toBeGreaterThan(5);
      
      // Patterns should have valid similarity scores
      for (const pattern of patterns) {
        expect(pattern.similarity).toBeGreaterThan(0);
        expect(pattern.similarity).toBeLessThanOrEqual(100);
        
        // Date should be valid
        const date = new Date(pattern.date);
        expect(date.getTime()).not.toBeNaN();
        expect(date.getFullYear()).toBeGreaterThan(2000);
        expect(date.getFullYear()).toBeLessThanOrEqual(new Date().getFullYear());
      }
    });
    
    await test.step('Verify analog pattern data consistency', async () => {
      // Select a high-similarity pattern
      await analogExplorerPage.setSimilarityThreshold(75);
      const highQualityPatterns = await analogExplorerPage.getAnalogPatterns();
      
      expect(highQualityPatterns.length).toBeGreaterThan(0);
      
      // Select the first pattern for detailed analysis
      await analogExplorerPage.selectAnalogPattern(0);
      const analogDetails = await analogExplorerPage.getSelectedAnalogDetails();
      
      // Verify analog details are complete
      expect(analogDetails.similarity).toBeGreaterThan(75);
      expect(analogDetails.conditions).toBeTruthy();
      expect(Object.keys(analogDetails.conditions).length).toBeGreaterThan(0);
      expect(analogDetails.outcome).toBeTruthy();
      expect(analogDetails.confidence).toBeGreaterThan(0);
      
      // Weather conditions should be realistic
      const conditions = analogDetails.conditions;
      
      if (conditions.t2m) {
        expect(conditions.t2m).toBeGreaterThan(-50);
        expect(conditions.t2m).toBeLessThan(60);
      }
      
      if (conditions.msl) {
        expect(conditions.msl).toBeGreaterThan(95000);  // ~950 hPa
        expect(conditions.msl).toBeLessThan(105000);    // ~1050 hPa
      }
    });
    
    await test.step('Test analog pattern temporal filtering', async () => {
      // Filter by date range (summer in Adelaide: Dec-Feb)
      await analogExplorerPage.filterByDateRange('2020-12-01', '2023-02-28');
      
      const summerPatterns = await analogExplorerPage.getAnalogPatterns();
      expect(summerPatterns.length).toBeGreaterThan(0);
      
      // Verify dates are within specified range
      for (const pattern of summerPatterns) {
        const patternDate = new Date(pattern.date);
        const month = patternDate.getMonth() + 1; // JavaScript months are 0-based
        
        // Should be December (12), January (1), or February (2)
        expect([12, 1, 2]).toContain(month);
      }
    });
    
    await test.step('Validate analog similarity calculations', async () => {
      // Test custom variable weighting
      await analogExplorerPage.setVariableWeights({
        't2m': 0.5,   // High weight on temperature
        'msl': 0.3,   // Medium weight on pressure  
        'u10': 0.1,   // Low weight on wind components
        'v10': 0.1
      });
      
      const reweightedPatterns = await analogExplorerPage.getAnalogPatterns();
      expect(reweightedPatterns.length).toBeGreaterThan(0);
      
      // Similarities should have changed due to reweighting
      const firstPattern = reweightedPatterns[0];
      expect(firstPattern.similarity).toBeGreaterThan(0);
      expect(firstPattern.similarity).toBeLessThanOrEqual(100);
      
      // Patterns should be sorted by similarity (descending)
      for (let i = 1; i < Math.min(reweightedPatterns.length, 5); i++) {
        expect(reweightedPatterns[i].similarity).toBeLessThanOrEqual(reweightedPatterns[i-1].similarity);
      }
    });
  });
  
  test('Model prediction pipeline validation', async ({ page }) => {
    await test.step('Verify model prediction confidence indicators', async () => {
      await homePage.navigateToHome();
      
      // Check confidence level display
      const confidenceLevel = await homePage.getConfidenceLevel();
      expect(confidenceLevel).toBeTruthy();
      
      // Confidence should be expressed as percentage or descriptive term
      const isPercentage = confidenceLevel.includes('%');
      const isDescriptive = /high|medium|low|good|poor/i.test(confidenceLevel);
      
      expect(isPercentage || isDescriptive).toBe(true);
      
      // Check analog information that supports confidence
      const analogInfo = await homePage.getAnalogInfo();
      expect(analogInfo.visible).toBe(true);
      expect(analogInfo.count).toBeGreaterThan(5); // Should have reasonable analog count
    });
    
    await test.step('Test model uncertainty quantification', async () => {
      // Intercept forecast response to examine uncertainty bounds
      const responsePromise = page.waitForResponse(response => 
        response.url().includes('/forecast') && response.status() === 200
      );
      
      await homePage.refreshForecast();
      
      const response = await responsePromise;
      const forecastData = await response.json();
      
      // Verify uncertainty bounds exist and are reasonable
      const variables = forecastData.variables;
      
      for (const [varName, varData] of Object.entries(variables as any)) {
        if (varData.available) {
          expect(varData.value).toBeDefined();
          expect(varData.p05).toBeDefined(); // 5th percentile
          expect(varData.p95).toBeDefined(); // 95th percentile
          expect(varData.confidence).toBeDefined();
          
          // P05 should be less than value, which should be less than P95
          expect(varData.p05).toBeLessThanOrEqual(varData.value);
          expect(varData.value).toBeLessThanOrEqual(varData.p95);
          
          // Confidence should be between 0 and 1
          expect(varData.confidence).toBeGreaterThanOrEqual(0);
          expect(varData.confidence).toBeLessThanOrEqual(1);
          
          // Uncertainty range should be reasonable
          const uncertainty = varData.p95 - varData.p05;
          expect(uncertainty).toBeGreaterThan(0);
          
          // For temperature, uncertainty should not be extreme
          if (varName === 't2m') {
            expect(uncertainty).toBeLessThan(30); // Max 30°C uncertainty range
          }
        }
      }
    });
    
    await test.step('Validate model ensemble processing', async () => {
      // Check that analog count indicates ensemble processing
      const analogInfo = await homePage.getAnalogInfo();
      
      // Should have multiple analogs for ensemble prediction
      expect(analogInfo.count).toBeGreaterThan(10);
      expect(analogInfo.count).toBeLessThan(200); // Not too many to be computationally excessive
      
      // Most similar pattern should have high similarity
      if (analogInfo.mostSimilar) {
        expect(analogInfo.mostSimilar).toMatch(/\d{4}-\d{2}-\d{2}/); // Valid date format
      }
    });
  });
  
  test('Real-time data processing pipeline', async ({ page }) => {
    await test.step('Test data freshness monitoring', async () => {
      await homePage.navigateToHome();
      
      // Check last updated timestamp
      const lastUpdated = await homePage.getLastUpdatedTime();
      expect(lastUpdated).toBeTruthy();
      
      // Parse timestamp to verify it's recent
      const updateTime = new Date(lastUpdated);
      const now = new Date();
      const ageMinutes = (now.getTime() - updateTime.getTime()) / (1000 * 60);
      
      // Data should be relatively fresh (within last 2 hours)
      expect(ageMinutes).toBeLessThan(120);
    });
    
    await test.step('Test data processing status indicators', async () => {
      const statusInfo = await homePage.getStatusInfo();
      
      // System should indicate healthy data processing
      expect(['healthy', 'online', 'ready', 'operational']).toContain(
        statusInfo.systemStatus.toLowerCase()
      );
      
      // API should be responsive
      expect(['healthy', 'online', 'ready', 'operational']).toContain(
        statusInfo.apiStatus.toLowerCase()
      );
      
      // Data age should be reported
      expect(statusInfo.dataAge).toBeTruthy();
      expect(statusInfo.dataAge.length).toBeGreaterThan(0);
    });
    
    await test.step('Validate processing latency', async () => {
      // Measure forecast request latency
      const startTime = Date.now();
      
      await homePage.refreshForecast();
      
      const endTime = Date.now();
      const processingTime = endTime - startTime;
      
      // Should meet performance thresholds
      expect(processingTime).toBeLessThan(
        testData.performanceThresholds.forecastRequest.maxLatencyMs
      );
      
      // Verify latency is also reported in API response
      const responsePromise = page.waitForResponse(response => 
        response.url().includes('/forecast') && response.status() === 200
      );
      
      await homePage.refreshForecast();
      
      const response = await responsePromise;
      const data = await response.json();
      
      expect(data.latency_ms).toBeDefined();
      expect(data.latency_ms).toBeLessThan(
        testData.performanceThresholds.forecastRequest.maxLatencyMs
      );
    });
  });
  
  test('Data quality validation pipeline', async ({ page }) => {
    await test.step('Verify data quality indicators', async () => {
      await homePage.navigateToHome();
      
      // Check forecast data quality
      await homePage.validateForecastData();
      
      // All displayed values should be within reasonable ranges
      const forecastData = await homePage.getCurrentForecastData();
      
      // Temperature bounds check
      if (forecastData.temperature !== undefined) {
        expect(forecastData.temperature).toBeGreaterThan(-50);
        expect(forecastData.temperature).toBeLessThan(60);
      }
      
      // Wind speed bounds check
      if (forecastData.windSpeed !== undefined) {
        expect(forecastData.windSpeed).toBeGreaterThanOrEqual(0);
        expect(forecastData.windSpeed).toBeLessThan(200);
      }
      
      // Pressure bounds check
      if (forecastData.pressure !== undefined) {
        expect(forecastData.pressure).toBeGreaterThan(800);
        expect(forecastData.pressure).toBeLessThan(1100);
      }
    });
    
    await test.step('Test data completeness validation', async () => {
      // Request comprehensive variable set
      const allVariables = ['t2m', 'u10', 'v10', 'msl', 'cape', 'sp', 'r2'];
      await homePage.selectVariables(allVariables);
      
      // Intercept response to check data completeness
      const responsePromise = page.waitForResponse(response => 
        response.url().includes('/forecast') && response.status() === 200
      );
      
      await homePage.refreshForecast();
      
      const response = await responsePromise;
      const data = await response.json();
      
      // Check that all requested variables are present
      for (const variable of allVariables) {
        expect(data.variables).toHaveProperty(variable);
        
        const varData = data.variables[variable];
        expect(varData).toHaveProperty('available');
        
        // If available, should have all required fields
        if (varData.available) {
          expect(varData).toHaveProperty('value');
          expect(varData).toHaveProperty('p05');
          expect(varData).toHaveProperty('p95');
          expect(varData).toHaveProperty('confidence');
          expect(varData).toHaveProperty('analog_count');
        }
      }
    });
    
    await test.step('Validate error detection and handling', async () => {
      // Test with invalid variable to trigger error detection
      await page.route('**/forecast*', async (route) => {
        const url = new URL(route.request().url());
        url.searchParams.set('vars', 'invalid_variable');
        
        await route.continue({
          url: url.toString()
        });
      });
      
      const errorResponse = page.waitForResponse(response => 
        response.url().includes('/forecast') && response.status() === 400
      );
      
      await homePage.refreshForecast();
      
      // Should receive validation error
      const error = await errorResponse;
      const errorData = await error.json();
      
      expect(errorData).toHaveProperty('error');
      expect(errorData.error.message).toMatch(/invalid.*parameter/i);
      
      // Clear route override
      await page.unroute('**/forecast*');
    });
  });
  
  test('End-to-end data lineage validation', async ({ page }) => {
    await test.step('Trace data from source to display', async () => {
      await homePage.navigateToHome();
      
      // Get forecast data from UI
      const uiData = await homePage.getCurrentForecastData();
      
      // Get corresponding data from API
      const apiResponse = await page.request.get('/api/forecast?horizon=24h&vars=t2m,u10,v10,msl', {
        headers: {
          'Authorization': `Bearer ${testData.authentication.validToken}`
        }
      });
      
      expect(apiResponse.status()).toBe(200);
      const apiData = await apiResponse.json();
      
      // UI and API data should be consistent
      expect(uiData.horizon).toBe(apiData.horizon);
      
      // Temperature values should match (within rounding)
      if (uiData.temperature && apiData.variables.t2m?.value) {
        const tempDiff = Math.abs(uiData.temperature - apiData.variables.t2m.value);
        expect(tempDiff).toBeLessThan(0.1); // Allow for rounding differences
      }
      
      // Wind data should be consistent
      if (uiData.windSpeed && apiData.variables.u10?.value && apiData.variables.v10?.value) {
        const expectedSpeed = Math.sqrt(
          Math.pow(apiData.variables.u10.value, 2) + 
          Math.pow(apiData.variables.v10.value, 2)
        );
        const speedDiff = Math.abs(uiData.windSpeed - expectedSpeed);
        expect(speedDiff).toBeLessThan(0.1);
      }
    });
    
    await test.step('Verify data versioning and provenance', async () => {
      // API response should include versioning information
      const apiResponse = await page.request.get('/api/forecast?horizon=24h', {
        headers: {
          'Authorization': `Bearer ${testData.authentication.validToken}`
        }
      });
      
      const apiData = await apiResponse.json();
      
      // Should have version information
      expect(apiData).toHaveProperty('versions');
      expect(apiData.versions).toHaveProperty('model');
      expect(apiData.versions).toHaveProperty('index');
      expect(apiData.versions).toHaveProperty('datasets');
      expect(apiData.versions).toHaveProperty('api_schema');
      
      // Should have hash information for reproducibility
      expect(apiData).toHaveProperty('hashes');
      expect(apiData.hashes).toHaveProperty('model');
      expect(apiData.hashes).toHaveProperty('index');
      expect(apiData.hashes).toHaveProperty('datasets');
      
      // Hashes should be valid (non-empty strings)
      expect(apiData.hashes.model).toBeTruthy();
      expect(apiData.hashes.index).toBeTruthy();
      expect(apiData.hashes.datasets).toBeTruthy();
    });
  });
});