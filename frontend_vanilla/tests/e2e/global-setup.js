/**
 * Global setup for Playwright tests
 * Initializes test database and creates necessary test data
 */
import { chromium } from '@playwright/test';

async function globalSetup() {
  console.log('🔧 Setting up test environment...');
  
  // Wait for services to be ready
  await waitForServices();
  
  // Initialize test database
  await initializeTestDatabase();
  
  console.log('✅ Test environment ready');
}

async function waitForServices() {
  console.log('⏳ Waiting for services to be ready...');
  
  const maxRetries = 30;
  let retries = 0;
  
  while (retries < maxRetries) {
    try {
      // Check backend health
      const backendResponse = await fetch('http://localhost:8000/health');
      if (!backendResponse.ok) {
        throw new Error(`Backend health check failed: ${backendResponse.status}`);
      }
      
      // Check frontend
      const frontendResponse = await fetch('http://localhost:3000');
      if (!frontendResponse.ok) {
        throw new Error(`Frontend health check failed: ${frontendResponse.status}`);
      }
      
      console.log('✅ All services are ready');
      return;
    } catch (error) {
      retries++;
      console.log(`⏳ Attempt ${retries}/${maxRetries} - Services not ready yet: ${error.message}`);
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  }
  
  throw new Error('Services failed to start within timeout');
}

async function initializeTestDatabase() {
  console.log('🗄️ Initializing test database...');
  
  try {
    // Clear existing test data
    const clearResponse = await fetch('http://localhost:8000/api/v1/test/clear-database', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    
    if (!clearResponse.ok) {
      console.log('⚠️ Database clear endpoint not available (this is expected in production)');
    }
    
    // Create test bots
    const testBots = [
      {
        name: 'Test Bot 1',
        symbol: 'BTCUSDT',
        is_active: true
      },
      {
        name: 'Test Bot 2',
        symbol: 'ETHUSDT',
        is_active: false
      }
    ];
    
    for (const bot of testBots) {
      try {
        const response = await fetch('http://localhost:8000/api/v1/bots', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(bot)
        });
        
        if (response.ok) {
          console.log(`✅ Created test bot: ${bot.name}`);
        } else {
          console.log(`⚠️ Failed to create test bot: ${bot.name}`);
        }
      } catch (error) {
        console.log(`⚠️ Error creating test bot ${bot.name}: ${error.message}`);
      }
    }
    
    console.log('✅ Test database initialized');
  } catch (error) {
    console.log(`⚠️ Database initialization failed: ${error.message}`);
    // Continue with tests - database might be in a different state
  }
}

export default globalSetup;