import { defineConfig, devices } from '@playwright/test';

/**
 * Adelaide Weather Forecasting E2E Test Configuration
 * 
 * Comprehensive Playwright configuration for cross-browser, cross-platform testing
 * with advanced features for performance, accessibility, and user journey validation.
 */
export default defineConfig({
  // Test configuration
  testDir: './specs',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  
  // Global test settings
  timeout: 60 * 1000, // 60 seconds per test
  expect: {
    timeout: 10 * 1000, // 10 seconds for assertions
  },
  
  // Reporter configuration with multiple outputs
  reporter: [
    ['html', { 
      outputFolder: './reports/html-report',
      open: 'never' 
    }],
    ['json', { 
      outputFile: './reports/test-results.json' 
    }],
    ['junit', { 
      outputFile: './reports/junit-results.xml' 
    }],
    ['line'],
    // Custom reporters for specialized metrics
    ['./utils/performance-reporter.ts'],
    ['./utils/accessibility-reporter.ts'],
  ],
  
  // Global test configuration
  use: {
    // Base URL for the application
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    
    // Browser context settings
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    
    // Network configuration
    ignoreHTTPSErrors: true,
    
    // Viewport settings (will be overridden by devices)
    viewport: { width: 1280, height: 720 },
    
    // Authentication state
    storageState: './fixtures/auth-state.json',
    
    // Additional context options
    permissions: ['geolocation'],
    geolocation: { latitude: -34.9285, longitude: 138.6007 }, // Adelaide coordinates
    locale: 'en-AU',
    timezoneId: 'Australia/Adelaide',
  },

  // Project configuration for different browsers and devices
  projects: [
    // Desktop browsers
    {
      name: 'chromium-desktop',
      use: { 
        ...devices['Desktop Chrome'],
        channel: 'chrome',
      },
    },
    {
      name: 'firefox-desktop',
      use: { 
        ...devices['Desktop Firefox'] 
      },
    },
    {
      name: 'webkit-desktop',
      use: { 
        ...devices['Desktop Safari'] 
      },
    },
    
    // Mobile devices
    {
      name: 'mobile-chrome',
      use: { 
        ...devices['Pixel 5'] 
      },
    },
    {
      name: 'mobile-safari',
      use: { 
        ...devices['iPhone 12'] 
      },
    },
    {
      name: 'tablet',
      use: { 
        ...devices['iPad Pro'] 
      },
    },
    
    // High-DPI displays
    {
      name: 'high-dpi',
      use: {
        ...devices['Desktop Chrome'],
        deviceScaleFactor: 2,
        viewport: { width: 1920, height: 1080 },
      },
    },
    
    // Accessibility testing with screen reader simulation
    {
      name: 'accessibility',
      use: {
        ...devices['Desktop Chrome'],
        // Enable accessibility tree snapshots
        extraHTTPHeaders: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 AccessibilityTest/1.0'
        },
      },
    },
    
    // Performance testing
    {
      name: 'performance',
      use: {
        ...devices['Desktop Chrome'],
        // Enable performance monitoring
        extraHTTPHeaders: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 PerformanceTest/1.0'
        },
      },
    },
    
    // Slow network simulation
    {
      name: 'slow-network',
      use: {
        ...devices['Desktop Chrome'],
        // Simulate slow 3G connection
        launchOptions: {
          args: ['--force-effective-connection-type=3g']
        },
      },
    },
  ],

  // Web server configuration for local development
  webServer: [
    {
      command: 'npm run dev',
      port: 3000,
      cwd: '../frontend',
      reuseExistingServer: !process.env.CI,
      env: {
        NODE_ENV: 'test',
        NEXT_PUBLIC_API_URL: 'http://localhost:8000',
      },
    },
    {
      command: 'python -m uvicorn api.main:app --host 0.0.0.0 --port 8000',
      port: 8000,
      cwd: '..',
      reuseExistingServer: !process.env.CI,
      env: {
        ENVIRONMENT: 'test',
        API_TOKEN: 'test-token-12345',
        CORS_ORIGINS: 'http://localhost:3000',
      },
    },
  ],

  // Global setup and teardown
  globalSetup: './utils/global-setup.ts',
  globalTeardown: './utils/global-teardown.ts',
});