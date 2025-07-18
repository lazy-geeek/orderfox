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

export const testUserActions = {
  createBot: {
    name: 'E2E Test Bot',
    symbol: 'BTCUSDT'
  },
  updateBot: {
    name: 'Updated Test Bot',
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
  short: 1000,
  medium: 3000,
  long: 5000,
  webSocket: 10000
};

export const testConfig = {
  baseURL: 'http://localhost:3000',
  apiURL: 'http://localhost:8000/api/v1',
  timeout: 30000,
  retries: 2
};