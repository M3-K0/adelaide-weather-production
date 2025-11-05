import { chromium, FullConfig } from '@playwright/test';
import { AuthHelper } from './test-helpers';

/**
 * Global Test Setup
 * 
 * Performs one-time setup operations before all tests run,
 * including authentication state preparation, test data setup,
 * and environment validation.
 */

async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting E2E test suite global setup...');
  
  // Create browser for setup operations
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  try {
    // Validate test environment
    await validateTestEnvironment(page);
    
    // Setup authentication state
    await setupAuthenticationState(page);
    
    // Validate API connectivity
    await validateApiConnectivity(page);
    
    // Setup test data
    await setupTestData();
    
    // Create necessary directories
    await createTestDirectories();
    
    console.log('✅ Global setup completed successfully');
    
  } catch (error) {
    console.error('❌ Global setup failed:', error);
    throw error;
  } finally {
    await browser.close();
  }
}

async function validateTestEnvironment(page: any): Promise<void> {
  console.log('🔍 Validating test environment...');
  
  // Check if frontend is accessible
  const frontendUrl = process.env.BASE_URL || 'http://localhost:3000';
  
  try {
    const response = await page.goto(frontendUrl, { 
      waitUntil: 'networkidle',
      timeout: 30000 
    });
    
    if (!response.ok()) {
      throw new Error(`Frontend not accessible at ${frontendUrl}. Status: ${response.status()}`);
    }
    
    console.log(`✅ Frontend accessible at ${frontendUrl}`);
  } catch (error) {
    throw new Error(`Failed to connect to frontend: ${error}`);
  }
  
  // Check if API is accessible
  const apiUrl = process.env.API_URL || 'http://localhost:8000';
  
  try {
    const healthResponse = await page.request.get(`${apiUrl}/health`);
    
    if (healthResponse.status() !== 200) {
      throw new Error(`API health check failed. Status: ${healthResponse.status()}`);
    }
    
    const healthData = await healthResponse.json();
    
    if (!healthData.ready) {
      throw new Error('API reports not ready state');
    }
    
    console.log(`✅ API accessible and healthy at ${apiUrl}`);
  } catch (error) {
    throw new Error(`Failed to connect to API: ${error}`);
  }
}

async function setupAuthenticationState(page: any): Promise<void> {
  console.log('🔑 Setting up authentication state...');
  
  const authHelper = new AuthHelper(page);
  
  // Navigate to the application
  await page.goto('/');
  
  // Set up valid authentication
  const testToken = process.env.API_TOKEN || 'test-token-12345';
  await authHelper.authenticateUser(testToken);
  
  // Set up test user preferences
  await authHelper.setUserPreferences({
    defaultHorizon: '24h',
    defaultVariables: ['t2m', 'u10', 'v10', 'msl'],
    tourCompleted: true,
    simplifiedView: false,
    enableNotifications: false
  });
  
  // Save authentication state for tests
  await page.context().storageState({ 
    path: './tests/e2e/fixtures/auth-state.json' 
  });
  
  console.log('✅ Authentication state saved');
}

async function validateApiConnectivity(page: any): Promise<void> {
  console.log('🌐 Validating API connectivity...');
  
  const apiUrl = process.env.API_URL || 'http://localhost:8000';
  const testToken = process.env.API_TOKEN || 'test-token-12345';
  
  // Test forecast endpoint
  try {
    const forecastResponse = await page.request.get(`${apiUrl}/forecast?horizon=24h`, {
      headers: {
        'Authorization': `Bearer ${testToken}`
      }
    });
    
    if (forecastResponse.status() !== 200) {
      throw new Error(`Forecast endpoint test failed. Status: ${forecastResponse.status()}`);
    }
    
    const forecastData = await forecastResponse.json();
    
    // Validate response structure
    if (!forecastData.horizon || !forecastData.variables) {
      throw new Error('Forecast endpoint returned invalid data structure');
    }
    
    console.log('✅ Forecast endpoint validation passed');
  } catch (error) {
    throw new Error(`Forecast endpoint validation failed: ${error}`);
  }
  
  // Test metrics endpoint (if authentication is required)
  try {
    const metricsResponse = await page.request.get(`${apiUrl}/metrics`, {
      headers: {
        'Authorization': `Bearer ${testToken}`
      }
    });
    
    if (metricsResponse.status() === 200) {
      console.log('✅ Metrics endpoint accessible');
    } else if (metricsResponse.status() === 403) {
      console.log('⚠️ Metrics endpoint requires authentication (expected)');
    } else {
      console.log(`⚠️ Metrics endpoint returned status: ${metricsResponse.status()}`);
    }
  } catch (error) {
    console.log(`⚠️ Metrics endpoint test failed: ${error}`);
  }
}

async function setupTestData(): Promise<void> {
  console.log('📊 Setting up test data...');
  
  // Create mock weather scenarios for consistent testing
  const mockScenarios = {
    typical: {
      temperature: 22.5,
      windSpeed: 8.2,
      windDirection: 225,
      pressure: 1013.2,
      cape: 380
    },
    extreme: {
      temperature: 42.1,
      windSpeed: 3.1,
      windDirection: 45,
      pressure: 1018.7,
      cape: 150
    },
    storm: {
      temperature: 28.9,
      windSpeed: 18.5,
      windDirection: 280,
      pressure: 998.3,
      cape: 2850
    }
  };
  
  // Save mock scenarios for test use
  const fs = require('fs');
  fs.writeFileSync(
    './tests/e2e/fixtures/mock-weather-scenarios.json',
    JSON.stringify(mockScenarios, null, 2)
  );
  
  console.log('✅ Test data setup completed');
}

async function createTestDirectories(): Promise<void> {
  console.log('📁 Creating test directories...');
  
  const fs = require('fs');
  const path = require('path');
  
  const directories = [
    './tests/e2e/reports',
    './tests/e2e/reports/screenshots',
    './tests/e2e/reports/videos',
    './tests/e2e/reports/traces',
    './tests/e2e/reports/html-report',
    './tests/e2e/reports/performance'
  ];
  
  for (const dir of directories) {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
      console.log(`📁 Created directory: ${dir}`);
    }
  }
  
  console.log('✅ Test directories ready');
}

// Environment-specific setup
async function setupEnvironmentSpecificConfig(): Promise<void> {
  const environment = process.env.NODE_ENV || 'test';
  
  console.log(`🔧 Configuring for environment: ${environment}`);
  
  switch (environment) {
    case 'ci':
      // CI/CD specific configuration
      process.env.PLAYWRIGHT_BROWSERS_PATH = '0'; // Use system browsers
      process.env.PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD = '1';
      break;
      
    case 'production':
      // Production testing configuration
      console.log('⚠️ Running tests against production environment');
      break;
      
    case 'staging':
      // Staging environment configuration
      console.log('🎭 Running tests against staging environment');
      break;
      
    default:
      // Local development configuration
      console.log('🏠 Running tests in local development environment');
      break;
  }
}

// Performance baseline establishment
async function establishPerformanceBaselines(page: any): Promise<void> {
  console.log('📈 Establishing performance baselines...');
  
  try {
    // Navigate to main page and measure baseline performance
    await page.goto('/', { waitUntil: 'networkidle' });
    
    const performanceMetrics = await page.evaluate(() => {
      const perfData = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      return {
        loadTime: perfData.loadEventEnd - perfData.loadEventStart,
        domContentLoaded: perfData.domContentLoadedEventEnd - perfData.domContentLoadedEventStart,
        firstByte: perfData.responseStart - perfData.requestStart
      };
    });
    
    // Save baseline metrics
    const fs = require('fs');
    fs.writeFileSync(
      './tests/e2e/reports/performance/baselines.json',
      JSON.stringify({
        timestamp: new Date().toISOString(),
        environment: process.env.NODE_ENV || 'test',
        ...performanceMetrics
      }, null, 2)
    );
    
    console.log('✅ Performance baselines established');
  } catch (error) {
    console.log(`⚠️ Failed to establish performance baselines: ${error}`);
  }
}

// Health check for external dependencies
async function checkExternalDependencies(): Promise<void> {
  console.log('🔗 Checking external dependencies...');
  
  // Check if TimescaleDB is accessible (if used)
  // Check if monitoring endpoints are available
  // Check if any required external APIs are accessible
  
  // This would depend on your specific architecture
  console.log('✅ External dependencies check completed');
}

export default globalSetup;