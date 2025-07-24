/**
 * Bot Fixture
 * Manages bot creation, selection, and state persistence across test projects
 */

import { test as base } from '@playwright/test';
import fs from 'fs/promises';
import path from 'path';
import { selectors, waitTimes } from '../fixtures/test-data.js';

// Helper to setup console logging for debugging
async function setupConsoleLogging(page) {
  // Disable verbose console logging to reduce output
  // Only log page errors
  page.on('pageerror', error => {
    console.error(`[Page Error] ${error.message}`);
  });
}

// Removed WebSocket connection waiting - UI tests don't need to wait for backend data
/* async function waitForWebSocketConnections(page, maxRetries = 3, retryDelay = 2000) {
  for (let i = 0; i < maxRetries; i++) {
    if (i > 0) {
      console.log(`Retry ${i}/${maxRetries} - waiting ${retryDelay}ms before retry...`);
      await page.waitForTimeout(retryDelay);
    }
    
    try {
      // Check for actual WebSocket connections by looking at connection indicators
      await page.waitForFunction(
        () => {
          // Check if any connection status indicators show connected state
          const indicators = document.querySelectorAll('.tab-status-indicator.connected');
          return indicators.length > 0;
        },
        { timeout: 5000 }
      );
      return true;
    } catch (error) {
      // Silent retry
    }
  }
  
  return false;
} */

// Removed WebSocket connection establishment - UI automatically handles this
/*
async function establishWebSocketConnections(page, bot) {
  try {
    // Execute WebSocket initialization in browser context
    const result = await page.evaluate(async (botData) => {
      try {
        // First, ensure the bot is set as selected in the store
        if (typeof window.setSelectedBotId === 'function' && botData.id) {
          window.setSelectedBotId(botData.id);
          // Set selected bot ID
        }
        
        // Check if WebSocketManager is available
        if (typeof window.WebSocketManager !== 'undefined') {
          // Establishing WebSocket connections
          
          // Create a bot object that matches what the frontend expects
          const botObject = {
            id: botData.id,
            name: botData.name,
            symbol: botData.symbol,
            isActive: botData.is_active || botData.isActive || true
          };
          
          // Call switchToBotContext which properly establishes all WebSocket connections
          await window.WebSocketManager.switchToBotContext(botObject);
          
          // Connections initiated
          return { success: true };
        } else {
          // WebSocketManager not found
          return { success: false, error: 'WebSocketManager not found' };
        }
      } catch (error) {
        // Error in establishWebSocketConnections
        return { success: false, error: error.message };
      }
    }, bot);
    
    if (!result.success) {
      return false;
    }
    
    // Wait a bit for connections to establish
    await page.waitForTimeout(1000);
    
    return true;
  } catch (error) {
    // Failed to establish connections
    return false;
  }
} */

// Helper to get state file path
function getStateFilePath(testInfo) {
  return path.join(testInfo.project.outputDir || 'test-results', 'selected-bot.json');
}

// Helper to create a test bot via UI
async function createTestBot(page, name, symbol) {
  // Click new bot button
  await page.click(selectors.newBotButton);
  
  // Wait for modal
  await page.waitForSelector(selectors.botEditorModal, { timeout: waitTimes.long });
  
  // Fill bot details
  await page.fill(selectors.botNameInput, name);
  await page.selectOption(selectors.botSymbolSelect, symbol);
  
  // Save bot
  await page.click(selectors.saveBotButton);
  
  // Wait for modal to close
  await page.waitForSelector(selectors.botEditorModal, { state: 'hidden', timeout: waitTimes.long });
  
  // Wait for bot list to update
  await page.waitForTimeout(1000);
  
  // Find the created bot and get its ID
  const botCard = page.locator(selectors.botCard).filter({ hasText: name });
  await botCard.waitFor({ timeout: waitTimes.long });
  
  // Extract bot info
  const botInfo = {
    name,
    symbol,
    element: botCard
  };
  
  return botInfo;
}

// Helper to create a test bot via API (faster for independent tests)
async function createTestBotViaAPI(page, name, symbol) {
  const response = await page.request.post('/api/v1/bots', {
    data: {
      name,
      symbol,
      isActive: true,
      paperTrading: true
    }
  });
  
  if (!response.ok()) {
    throw new Error(`Failed to create bot via API: ${response.status()}`);
  }
  
  const botData = await response.json();
  return {
    name: botData.name,
    symbol: botData.symbol,
    id: botData.id
  };
}

// Helper to select a bot
async function selectBot(page, botName) {
  // Find the bot card
  const botCard = page.locator(selectors.botCard).filter({ hasText: botName });
  await botCard.waitFor({ timeout: waitTimes.long });
  
  // Click the select button
  const selectButton = botCard.locator(selectors.selectBotButton);
  await selectButton.click();
  
  // Wait for trading modal to appear
  await page.waitForSelector(selectors.tradingModal, { timeout: waitTimes.botOperation });
  
  // Wait for the trading modal to be visible (dialog.open should be true)
  await page.waitForFunction(
    selector => {
      const modal = document.querySelector(selector);
      return modal && modal.open === true;
    },
    selectors.tradingModal,
    { timeout: waitTimes.botOperation }
  );
  
  // Wait for chart container to be created and visible
  await page.waitForSelector(selectors.chartContainer, { 
    state: 'visible',
    timeout: 10000 
  });
  
  // Wait for tabbed trading display to be visible
  await page.waitForSelector('.orderfox-tabbed-trading-display', { 
    state: 'visible',
    timeout: 10000 
  });
  
  // Additional wait for WebSocket connections to initialize
  // This is necessary because WebSocket connections may take time to establish
  // especially through Vite's proxy in the test environment
  // Waiting for WebSocket connections...
  
  // Initial wait to allow UI to update
  // Small delay for UI to settle
  await page.waitForTimeout(waitTimes.short);
  
  // UI will automatically handle WebSocket connections
}

export const test = base.extend({
  // Worker-scoped fixture for bot state
  selectedBot: [async ({ browser }, use, testInfo) => {
    const stateFile = getStateFilePath(testInfo);
    const isBotSelectionTest = testInfo.file?.includes('bot-selection.spec.js');
    
    if (isBotSelectionTest) {
      // Create and select bot for trading tests (bot-selection.spec.js)
      const page = await browser.newPage();
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      
      // Navigate to bot management
      const myBotsLink = page.locator('text=🤖 My Bots');
      await myBotsLink.click();
      await page.waitForSelector(selectors.botList, { timeout: waitTimes.long });
      
      // Create a test bot specifically for trading tests
      const timestamp = Date.now();
      const botInfo = await createTestBot(
        page,
        `Trading Test Bot ${timestamp}`,
        'BTCUSDT'
      );
      
      // Select the bot
      await selectBot(page, botInfo.name);
      
      // Save bot info to state file
      const botState = {
        name: botInfo.name,
        symbol: botInfo.symbol,
        timestamp,
        createdBy: 'bot-selection-test'
      };
      
      await fs.mkdir(path.dirname(stateFile), { recursive: true });
      await fs.writeFile(stateFile, JSON.stringify(botState, null, 2));
      
      await page.close();
      await use(botState);
    } else {
      // Read bot from state file, or create via API if independent
      try {
        const botStateJson = await fs.readFile(stateFile, 'utf-8');
        const botState = JSON.parse(botStateJson);
        await use(botState);
      } catch (error) {
        // If no state file exists, create a bot via API for independent test execution
        // No bot state file found, creating bot via API
        const page = await browser.newPage();
        
        const timestamp = Date.now();
        const botName = `Independent Test Bot ${timestamp}`;
        
        try {
          const botInfo = await createTestBotViaAPI(page, botName, 'BTCUSDT');
          
          // Wait for backend to process bot creation
          // Bot created via API
          await page.waitForTimeout(waitTimes.short);
          
          const botState = {
            name: botInfo.name,
            symbol: botInfo.symbol,
            id: botInfo.id,
            timestamp,
            createdBy: 'independent-api'
          };
          
          // Save to state file for subsequent tests in this run
          await fs.mkdir(path.dirname(stateFile), { recursive: true });
          await fs.writeFile(stateFile, JSON.stringify(botState, null, 2));
          
          await page.close();
          await use(botState);
        } catch (apiError) {
          console.error('Failed to create bot via API:', apiError);
          await page.close();
          // Fallback to default bot info
          await use({
            name: 'Fallback Test Bot',
            symbol: 'BTCUSDT',
            timestamp: Date.now(),
            createdBy: 'fallback'
          });
        }
      }
    }
  }, { scope: 'worker' }],
  
  // Page fixture that ensures bot is selected
  pageWithBot: async ({ page, selectedBot }, use) => {
    // Setup console logging for debugging WebSocket issues
    await setupConsoleLogging(page);
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Wait for initial data to be loaded (bots and symbols)
    await page.waitForFunction(
      () => {
        // Check if bots have been loaded into the store
        return window.state && Array.isArray(window.state.bots) && !window.state.botLoading;
      },
      { timeout: 10000 }
    );
    
    // Check if trading modal is already visible
    const tradingModal = page.locator(selectors.tradingModal);
    const isVisible = await tradingModal.isVisible();
    
    if (!isVisible) {
      // Navigate to bot management
      const myBotsLink = page.locator('text=🤖 My Bots');
      await myBotsLink.click();
      await page.waitForSelector(selectors.botList, { timeout: waitTimes.long });
      
      // Select the bot
      await selectBot(page, selectedBot.name);
    } else {
      // Trading interface is visible but we need to ensure WebSocket connections are established
      // This happens when the bot was created via API
      // Trading interface already visible, establishing connections...
      
      // First, ensure the bot is in the frontend store
      const botExists = await page.evaluate((botData) => {
        // Check if bot already exists in the store
        const existingBot = window.state.bots.find(b => b.id === botData.id || b.name === botData.name);
        if (existingBot) {
          console.log('Bot already exists in store:', existingBot);
          return true;
        }
        
        // Add bot to the store if it doesn't exist
        if (typeof window.addBot === 'function') {
          // Convert to the format expected by the frontend
          const bot = {
            id: botData.id,
            name: botData.name,
            symbol: botData.symbol,
            isActive: botData.is_active || botData.isActive || true,
            paperTrading: true,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
          };
          window.addBot(bot);
          console.log('Added bot to frontend store:', bot);
          return true;
        }
        return false;
      }, selectedBot);
      
      if (!botExists) {
        console.error('Failed to ensure bot exists in frontend store');
      }
      
      // UI handles connections automatically
    }
    
    // Verify trading modal is visible
    await page.waitForSelector(selectors.tradingModal, { timeout: waitTimes.botOperation });
    
    await use(page);
  }
});

export { expect } from '@playwright/test';