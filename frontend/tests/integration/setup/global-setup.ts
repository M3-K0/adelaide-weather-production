/**
 * Global Setup for Integration Tests
 * Configures the global test environment before all tests run
 */

export default async function globalSetup() {
  // Set up environment variables for testing
  process.env.NODE_ENV = 'test';
  process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
  process.env.NEXT_PUBLIC_ENABLE_MOCK_API = 'true';
  
  // Suppress console warnings during test runs
  const originalWarn = console.warn;
  console.warn = (...args: any[]) => {
    // Filter out known warnings from dependencies
    if (typeof args[0] === 'string' && 
        (args[0].includes('componentWillReceiveProps') ||
         args[0].includes('componentWillUpdate') ||
         args[0].includes('ReactDOM.render'))) {
      return;
    }
    originalWarn.apply(console, args);
  };

  console.log('🧪 Integration Test Environment Initialized');
  console.log('📊 API URL:', process.env.NEXT_PUBLIC_API_URL);
  console.log('🎭 Mock API Enabled:', process.env.NEXT_PUBLIC_ENABLE_MOCK_API);
}