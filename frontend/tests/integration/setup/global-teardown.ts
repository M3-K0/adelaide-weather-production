/**
 * Global Teardown for Integration Tests
 * Cleans up the global test environment after all tests complete
 */

export default async function globalTeardown() {
  // Reset environment variables
  delete process.env.NEXT_PUBLIC_ENABLE_MOCK_API;
  
  console.log('🧹 Integration Test Environment Cleaned Up');
}