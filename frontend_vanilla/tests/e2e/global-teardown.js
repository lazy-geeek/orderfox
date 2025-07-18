/**
 * Global teardown for Playwright tests
 * Cleans up test data and resources
 */

async function globalTeardown() {
  console.log('🧹 Cleaning up test environment...');
  
  try {
    // Clear test database
    const clearResponse = await fetch('http://localhost:8000/api/v1/test/clear-database', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    
    if (clearResponse.ok) {
      console.log('✅ Test database cleared');
    } else {
      console.log('⚠️ Database clear endpoint not available (this is expected in production)');
    }
  } catch (error) {
    console.log(`⚠️ Cleanup failed: ${error.message}`);
  }
  
  console.log('✅ Test environment cleaned up');
}

export default globalTeardown;