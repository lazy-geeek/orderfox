/**
 * Test data fixtures for E2E tests
 */

export const testBots = {
  activeBtcBot: {
    name: 'Active BTC Bot',
    symbol: 'BTCUSDT',
    is_active: true
  },
  inactiveEthBot: {
    name: 'Inactive ETH Bot',
    symbol: 'ETHUSDT',
    is_active: false
  },
  newTestBot: {
    name: 'New Test Bot',
    symbol: 'ADAUSDT',
    is_active: true
  }
};

export const testSymbols = [
  'BTCUSDT',
  'ETHUSDT',
  'ADAUSDT',
  'BNBUSDT',
  'SOLUSDT'
];

// Generate unique names with timestamp to prevent conflicts
const timestamp = Date.now();

export const testUserActions = {
  createBot: {
    name: `E2E Test Bot ${timestamp}`,
    symbol: 'BTCUSDT'
  },
  updateBot: {
    name: `Updated Test Bot ${timestamp}`,
    symbol: 'ETHUSDT'
  }
};

export const selectors = {
  // Navigation
  botNavigation: '[data-testid="bot-navigation"]',
  newBotButton: '[data-testid="new-bot-button"]',
  
  // Bot List
  botList: '[data-testid="bot-list"]',
  botCard: '[data-testid="bot-card"]',
  botName: '[data-testid="bot-name"]',
  botSymbol: '[data-testid="bot-symbol"]',
  botStatus: '[data-testid="bot-status"]',
  editBotButton: '[data-testid="edit-bot-button"]',
  deleteBotButton: '[data-testid="delete-bot-button"]',
  toggleBotButton: '[data-testid="toggle-bot-button"]',
  selectBotButton: '.select-bot-btn',
  
  // Bot Editor Modal
  botEditorModal: '[data-testid="bot-editor-modal"]',
  botNameInput: '[data-testid="bot-name-input"]',
  botSymbolSelect: '[data-testid="bot-symbol-select"]',
  saveBotButton: '[data-testid="save-bot-button"]',
  cancelBotButton: '[data-testid="cancel-bot-button"]',
  
  // Trading Interface
  tradingInterface: '[data-testid="trading-interface"]',
  chartContainer: '[data-testid="chart-container"]',
  orderbookDisplay: '[data-testid="orderbook-display"]',
  tradesDisplay: '[data-testid="trades-display"]',
  liquidationsDisplay: '[data-testid="liquidations-display"]',
  
  // Connection Status
  connectionStatus: '[data-testid="connection-status"]',
  connectionIndicator: '[data-testid="connection-indicator"]',
  
  // Alerts and Messages
  successAlert: '[data-testid="success-alert"]',
  errorAlert: '[data-testid="error-alert"]',
  loadingSpinner: '[data-testid="loading-spinner"]',
  
  // Modals
  confirmDialog: '[data-testid="confirm-dialog"]',
  confirmButton: '[data-testid="confirm-button"]',
  cancelButton: '[data-testid="cancel-button"]'
};

export const waitTimes = {
  short: 500,    // Reduced for UI responsiveness
  medium: 1000,  // Reduced for faster tests
  long: 3000,    // Reduced for reasonable wait times
  webSocket: 0,  // Removed - UI tests don't need to wait for WebSocket data
  // Bot management specific timeouts (involve API calls + DB operations)
  botOperation: 7000,  // Bot CRUD operations with API calls
  modalClose: 5000,    // Modal close after API operations (single project)
  modalCloseComplete: 10000,  // Extended timeout for complete suite runs
  listRefresh: 4000    // Bot list refresh after operations
};

export const testConfig = {
  baseURL: process.env.FRONTEND_URL || 'http://localhost:3000',
  apiURL: process.env.BACKEND_URL ? `${process.env.BACKEND_URL}/api/v1` : 'http://localhost:8000/api/v1',
  timeout: 30000,
  retries: 2
};

/**
 * Robust modal close waiting with retry logic for resource contention
 * @param {Page} page - Playwright page object
 * @param {string} modalSelector - CSS selector for the modal
 * @returns {Promise<void>}
 */
export async function waitForModalClose(page, modalSelector) {
  try {
    // First attempt with standard timeout
    await page.waitForSelector(modalSelector, { state: 'hidden', timeout: waitTimes.modalClose });
  } catch (error) {
    // If first attempt fails, try with extended timeout (for complete suite runs with resource contention)
    console.log('Modal close timeout - retrying with extended timeout for resource contention...');
    
    // Add a small delay to let any pending operations complete
    await page.waitForTimeout(waitTimes.short);
    
    // Extended retry with longer timeout
    await page.waitForSelector(modalSelector, { state: 'hidden', timeout: waitTimes.modalCloseComplete });
  }
}

/**
 * Robust list loading waiting with retry logic for resource contention
 * @param {Page} page - Playwright page object
 * @param {string} loadingSelector - CSS selector for the loading indicator
 * @returns {Promise<void>}
 */
export async function waitForListLoadingComplete(page, loadingSelector) {
  try {
    // First attempt with standard timeout
    await page.waitForSelector(loadingSelector, { state: 'hidden', timeout: waitTimes.listRefresh });
  } catch (error) {
    // If first attempt fails, try with extended timeout (for complete suite runs with resource contention)
    console.log('List loading timeout - retrying with extended timeout for resource contention...');
    
    // Add a small delay to let any pending operations complete
    await page.waitForTimeout(waitTimes.short);
    
    // Extended retry with longer timeout (8 seconds for bot list operations)
    await page.waitForSelector(loadingSelector, { state: 'hidden', timeout: 8000 });
  }
}