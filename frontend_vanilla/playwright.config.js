import { defineConfig, devices } from '@playwright/test';

/**
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false, // Control parallelism per project
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['dot'],  // Minimal console output - just dots for progress
    ['json', { outputFile: 'test-results/playwright-results.json' }],
  ],
  use: {
    baseURL: process.env.FRONTEND_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure', // Screenshots for Claude Code analysis
    video: 'off', // NO VIDEO - can't be analyzed by LLM
  },

  projects: [
    // Independent: Basic functionality tests
    {
      name: 'smoke',
      testMatch: /smoke\.spec\.js/,
      fullyParallel: false,
      use: { ...devices['Desktop Chrome'] },
    },
    
    // Independent: Bot CRUD operations
    {
      name: 'bot-management',
      testMatch: /bot-management\.spec\.js|bot-paper-trading\.spec\.js/,
      fullyParallel: false,
      use: { ...devices['Desktop Chrome'] },
    },
    
    // Trading tests split into smaller groups to avoid timeouts and conflicts
    
    // Group 1: Bot selection - sets up bot for other tests
    {
      name: 'trading-setup',
      testMatch: /bot-selection\.spec\.js/,
      fullyParallel: false,
      use: { ...devices['Desktop Chrome'] },
    },
    
    // Group 2: Basic UI tests (2 tests)
    {
      name: 'trading-basic',
      testMatch: /bot-trading-view\.spec\.js/,
      fullyParallel: false,
      use: { ...devices['Desktop Chrome'] },
      grep: /should display trading interface when bot is selected|should display chart component/,
    },
    
    // Group 3: Tab display tests (3 tests)
    {
      name: 'trading-tabs-display',
      testMatch: /bot-trading-view\.spec\.js/,
      fullyParallel: false,
      use: { ...devices['Desktop Chrome'] },
      grep: /should display orderbook with data|should display trades with data|should display liquidations with data/,
    },
    
    // Group 4: UI controls tests (3 tests)
    {
      name: 'trading-controls',
      testMatch: /bot-trading-view\.spec\.js/,
      fullyParallel: false,
      use: { ...devices['Desktop Chrome'] },
      grep: /should display timeframe controls|should handle responsive layout|should handle bot status changes during trading/,
    },
    
    // Group 5: Connection tests (3 tests)
    {
      name: 'trading-connection',
      testMatch: /bot-trading-view\.spec\.js/,
      fullyParallel: false,
      use: { ...devices['Desktop Chrome'] },
      grep: /should show connection status indicators|should handle symbol switching|should handle WebSocket reconnection/,
    },
    
    // Group 6: Error handling tests (1 test)
    {
      name: 'trading-errors',
      testMatch: /bot-trading-view\.spec\.js/,
      fullyParallel: false,
      use: { ...devices['Desktop Chrome'] },
      grep: /should display error states gracefully/,
    },
    
    // Group 7: Tabbed interface tests (10 tests)
    {
      name: 'trading-tabs',
      testMatch: /tabbed-trading\.spec\.js/,
      fullyParallel: false,
      use: { ...devices['Desktop Chrome'] },
    },
    
    // Specialized functionality tests
    
    // Chart: TradingView Lightweight Charts v5 integration tests
    {
      name: 'chart-v5',
      testMatch: /chart-v5\.spec\.js/,
      fullyParallel: false,
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* Run your local dev server before starting the tests */
  webServer: [
    {
      // Use npm run dev:bg which starts both frontend and backend
      command: 'cd .. && npm run dev:bg && npm run dev:wait',
      url: process.env.FRONTEND_URL || 'http://localhost:3000',
      reuseExistingServer: !process.env.CI,
      timeout: 120 * 1000, // Increased timeout for both servers to start
    }
  ],

  /* Configure test timeout */
  timeout: 60 * 1000,  // Increased to 60 seconds for WebSocket connections
  expect: {
    timeout: 10 * 1000,  // Increased expect timeout to 10 seconds
  },

  /* Global setup for database initialization */
  globalSetup: './tests/e2e/global-setup.js',
  globalTeardown: './tests/e2e/global-teardown.js',
});