/**
 * Setup for Pact consumer tests
 *
 * Configures the test environment for contract testing including
 * logging setup and common utilities.
 */

const path = require('path');
const fs = require('fs');

// Ensure logs directory exists
const logsDir = path.resolve(process.cwd(), 'logs');
if (!fs.existsSync(logsDir)) {
  fs.mkdirSync(logsDir, { recursive: true });
}

// Ensure pacts directory exists
const pactsDir = path.resolve(process.cwd(), 'pacts');
if (!fs.existsSync(pactsDir)) {
  fs.mkdirSync(pactsDir, { recursive: true });
}

// Configure global test timeout
jest.setTimeout(30000);

// Mock console.log for cleaner test output
const originalConsoleLog = console.log;
console.log = (...args) => {
  // Only log if it's not Pact internal logging
  if (!args.some(arg => typeof arg === 'string' && arg.includes('pact'))) {
    originalConsoleLog(...args);
  }
};

// Global error handler for unhandled rejections
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

// Helper function to setup axios with proper error handling
global.setupApiClient = baseURL => {
  const axios = require('axios');
  const client = axios.create({
    baseURL,
    timeout: 10000,
    headers: {
      'Content-Type': 'application/json'
    }
  });

  // Add request interceptor for logging
  client.interceptors.request.use(
    config => {
      console.log(
        `Making ${config.method.toUpperCase()} request to ${config.url}`
      );
      return config;
    },
    error => {
      console.error('Request error:', error);
      return Promise.reject(error);
    }
  );

  // Add response interceptor for logging
  client.interceptors.response.use(
    response => {
      console.log(
        `Received ${response.status} response from ${response.config.url}`
      );
      return response;
    },
    error => {
      if (error.response) {
        console.log(
          `Received ${error.response.status} error from ${error.response.config.url}`
        );
      } else {
        console.error('Network error:', error.message);
      }
      return Promise.reject(error);
    }
  );

  return client;
};
