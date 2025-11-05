/**
 * Jest configuration for Pact consumer tests
 *
 * This configuration ensures Pact tests run in the correct environment
 * with proper setup and teardown for contract generation.
 */

module.exports = {
  displayName: 'Pact Consumer Tests',
  testMatch: ['<rootDir>/pact/consumer/**/*.test.js'],
  testEnvironment: 'node',
  setupFilesAfterEnv: ['<rootDir>/pact/consumer/setup.js'],
  testTimeout: 30000, // Pact tests may take longer due to mock server setup
  collectCoverageFrom: [
    'pact/consumer/**/*.js',
    '!pact/consumer/jest.config.js',
    '!pact/consumer/setup.js'
  ],
  globalSetup: '<rootDir>/pact/consumer/global-setup.js',
  globalTeardown: '<rootDir>/pact/consumer/global-teardown.js',
  verbose: true,
  bail: false, // Continue running tests even if some fail
  maxWorkers: 1 // Run tests sequentially to avoid port conflicts
};
