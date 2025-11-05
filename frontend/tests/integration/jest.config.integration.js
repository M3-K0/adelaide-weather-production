/**
 * Jest Configuration for Component Integration Tests
 * Specialized configuration for testing component interactions, state management,
 * API integration, and cross-component communication patterns.
 */

const nextJest = require('next/jest');

const createJestConfig = nextJest({
  dir: '../../'
});

const integrationJestConfig = {
  displayName: 'Integration Tests',
  testEnvironment: 'jest-environment-jsdom',
  
  // Setup files for integration testing environment
  setupFilesAfterEnv: [
    '<rootDir>/setup/test-environment.ts'
  ],
  
  // Test file patterns specific to integration tests
  testMatch: [
    '<rootDir>/components/**/*.integration.test.tsx',
    '<rootDir>/workflows/**/*.integration.test.tsx',
    '<rootDir>/**/*.integration.test.{js,jsx,ts,tsx}'
  ],
  
  // Module resolution for integration tests
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/../../$1',
    '^@/components/(.*)$': '<rootDir>/../../components/$1',
    '^@/lib/(.*)$': '<rootDir>/../../lib/$1',
    '^@/types/(.*)$': '<rootDir>/../../types/$1',
    '^@/app/(.*)$': '<rootDir>/../../app/$1',
    '^@integration/(.*)$': '<rootDir>/$1',
    '^@mocks/(.*)$': '<rootDir>/mocks/$1',
    '^@fixtures/(.*)$': '<rootDir>/fixtures/$1'
  },
  
  // Coverage configuration for integration tests
  collectCoverageFrom: [
    '<rootDir>/../../components/**/*.{js,jsx,ts,tsx}',
    '<rootDir>/../../lib/**/*.{js,jsx,ts,tsx}',
    '<rootDir>/../../app/**/*.{js,jsx,ts,tsx}',
    '!**/*.d.ts',
    '!**/node_modules/**',
    '!**/.next/**',
    '!**/coverage/**',
    '!**/*.stories.{js,jsx,ts,tsx}',
    '!**/*.config.{js,ts}',
    '!**/index.ts'
  ],
  
  // Integration test specific coverage thresholds
  coverageThreshold: {
    global: {
      branches: 90,
      functions: 90,
      lines: 90,
      statements: 90
    }
  },
  
  // Coverage reporting for integration tests
  coverageReporters: [
    'text',
    'text-summary',
    'html',
    'lcov',
    'json-summary'
  ],
  coverageDirectory: '<rootDir>/reports/coverage',
  
  // Timeout for integration tests (longer than unit tests)
  testTimeout: 15000,
  
  // Setup files for polyfills and global test configuration
  setupFiles: [
    '<rootDir>/../../jest.polyfills.js'
  ],
  
  // Test environment options
  testEnvironmentOptions: {
    url: 'http://localhost:3000'
  },
  
  // Clear mocks between test suites
  clearMocks: true,
  restoreMocks: true,
  resetMocks: true,
  
  // Verbose output for integration test debugging
  verbose: true,
  
  // Transform configuration for TypeScript and JSX
  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': ['babel-jest', { presets: ['next/babel'] }]
  },
  
  // Module file extensions
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],
  
  // Ignore patterns
  testPathIgnorePatterns: [
    '<rootDir>/node_modules/',
    '<rootDir>/.next/',
    '<rootDir>/coverage/'
  ],
  
  // Transform ignore patterns
  transformIgnorePatterns: [
    'node_modules/(?!(.*\\.mjs$|@radix-ui|framer-motion|date-fns))'
  ],
  
  // Global setup and teardown for integration tests
  globalSetup: '<rootDir>/setup/global-setup.ts',
  globalTeardown: '<rootDir>/setup/global-teardown.ts',
  
  // Reporter configuration for integration test results
  reporters: [
    'default',
    [
      'jest-html-reporters',
      {
        publicPath: '<rootDir>/reports',
        filename: 'integration-test-report.html',
        expand: true,
        hideIcon: false,
        pageTitle: 'Component Integration Test Report',
        logoImgPath: undefined,
        includeFailureMsg: true,
        includeSuiteFailure: true
      }
    ],
    [
      'jest-junit',
      {
        outputDirectory: '<rootDir>/reports',
        outputName: 'integration-test-results.xml',
        suiteName: 'Component Integration Tests',
        includeConsoleOutput: true,
        usePathForSuiteName: true
      }
    ]
  ],
  
  // Test sequence configuration
  maxWorkers: process.env.CI ? 2 : '50%',
  
  // Watch plugins for development
  watchPlugins: [
    'jest-watch-typeahead/filename',
    'jest-watch-typeahead/testname'
  ]
};

module.exports = createJestConfig(integrationJestConfig);