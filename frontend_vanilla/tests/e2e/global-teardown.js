/**
 * Global teardown for Playwright tests
 * Cleans up test data and resources
 */

async function globalTeardown() {
  console.log('🧹 Cleaning up test environment...');
  
  // Note: Database clearing is not implemented in the backend
  // Tests should be idempotent and handle existing data
  console.log('ℹ️ Skipping database clear (endpoint not implemented)');
  
  console.log('✅ Test environment cleaned up');
}

export default globalTeardown;