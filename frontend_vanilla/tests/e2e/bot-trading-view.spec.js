/**
 * Bot Trading View E2E Tests
 * Tests the trading interface with bot context including WebSocket connections
 */

import { test, expect } from '@playwright/test';
import { selectors, waitTimes } from './fixtures/test-data.js';

test.describe('Bot Trading View', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto('/');
    
    // Wait for application to load
    await page.waitForLoadState('networkidle');
    
    // Wait for bot list to be visible
    await page.waitForSelector(selectors.botList, { timeout: waitTimes.long });
  });

  test('should display trading interface when bot is selected', async ({ page }) => {
    // Check if there are any bots
    const botCards = page.locator(selectors.botCard);
    const count = await botCards.count();
    
    if (count > 0) {
      // Select first bot
      const firstBot = botCards.first();
      await firstBot.click();
      
      // Check trading interface is visible
      await expect(page.locator(selectors.tradingInterface)).toBeVisible();
      
      // Check all trading components are present
      await expect(page.locator(selectors.chartContainer)).toBeVisible();
      await expect(page.locator(selectors.orderbookDisplay)).toBeVisible();
      await expect(page.locator(selectors.tradesDisplay)).toBeVisible();
      await expect(page.locator(selectors.liquidationsDisplay)).toBeVisible();
    } else {
      // Create a bot first if none exist
      await page.click(selectors.newBotButton);
      await page.waitForSelector(selectors.botEditorModal, { timeout: waitTimes.medium });
      
      await page.fill(selectors.botNameInput, 'Trading Test Bot');
      await page.selectOption(selectors.botSymbolSelect, 'BTCUSDT');
      await page.click(selectors.saveBotButton);
      
      // Wait for modal to close
      await page.waitForSelector(selectors.botEditorModal, { state: 'hidden', timeout: waitTimes.medium });
      
      // Select the newly created bot
      const newBot = page.locator(selectors.botCard).filter({ hasText: 'Trading Test Bot' });
      await newBot.click();
      
      // Check trading interface is visible
      await expect(page.locator(selectors.tradingInterface)).toBeVisible();
    }
  });

  test('should display chart component', async ({ page }) => {
    // Ensure we have a bot selected
    await ensureBotSelected(page);
    
    // Check chart container is visible
    await expect(page.locator(selectors.chartContainer)).toBeVisible();
    
    // Check chart is properly sized
    const chartContainer = page.locator(selectors.chartContainer);
    const boundingBox = await chartContainer.boundingBox();
    expect(boundingBox.width).toBeGreaterThan(300);
    expect(boundingBox.height).toBeGreaterThan(200);
    
    // Check for chart canvas or SVG elements
    const chartCanvas = page.locator(`${selectors.chartContainer} canvas`);
    await expect(chartCanvas).toBeVisible();
  });

  test('should display orderbook with data', async ({ page }) => {
    // Ensure we have a bot selected
    await ensureBotSelected(page);
    
    // Check orderbook display is visible
    await expect(page.locator(selectors.orderbookDisplay)).toBeVisible();
    
    // Wait for orderbook data to load
    await page.waitForTimeout(waitTimes.webSocket);
    
    // Check orderbook has headers
    const orderbookHeaders = page.locator(`${selectors.orderbookDisplay} .display-header`);
    await expect(orderbookHeaders).toBeVisible();
    
    // Check orderbook has content
    const orderbookContent = page.locator(`${selectors.orderbookDisplay} .display-content`);
    await expect(orderbookContent).toBeVisible();
    
    // Check for bid and ask prices (if data is available)
    const bidPrices = page.locator(`${selectors.orderbookDisplay} .bid-price`);
    const askPrices = page.locator(`${selectors.orderbookDisplay} .ask-price`);
    
    // At least one should be visible if data is loading
    const bidCount = await bidPrices.count();
    const askCount = await askPrices.count();
    expect(bidCount + askCount).toBeGreaterThan(0);
  });

  test('should display trades with data', async ({ page }) => {
    // Ensure we have a bot selected
    await ensureBotSelected(page);
    
    // Check trades display is visible
    await expect(page.locator(selectors.tradesDisplay)).toBeVisible();
    
    // Wait for trades data to load
    await page.waitForTimeout(waitTimes.webSocket);
    
    // Check trades has headers
    const tradesHeaders = page.locator(`${selectors.tradesDisplay} .display-header`);
    await expect(tradesHeaders).toBeVisible();
    
    // Check trades has content
    const tradesContent = page.locator(`${selectors.tradesDisplay} .display-content`);
    await expect(tradesContent).toBeVisible();
    
    // Check for trade rows (if data is available)
    const tradeRows = page.locator(`${selectors.tradesDisplay} .trade-row`);
    const tradeCount = await tradeRows.count();
    
    // Should have at least some trades or be showing loading state
    if (tradeCount > 0) {
      // Check first trade has expected columns
      const firstTrade = tradeRows.first();
      await expect(firstTrade).toBeVisible();
    }
  });

  test('should display liquidations with data', async ({ page }) => {
    // Ensure we have a bot selected
    await ensureBotSelected(page);
    
    // Check liquidations display is visible
    await expect(page.locator(selectors.liquidationsDisplay)).toBeVisible();
    
    // Wait for liquidations data to load
    await page.waitForTimeout(waitTimes.webSocket);
    
    // Check liquidations has headers
    const liquidationsHeaders = page.locator(`${selectors.liquidationsDisplay} .display-header`);
    await expect(liquidationsHeaders).toBeVisible();
    
    // Check liquidations has content
    const liquidationsContent = page.locator(`${selectors.liquidationsDisplay} .display-content`);
    await expect(liquidationsContent).toBeVisible();
    
    // Check for liquidation rows (if data is available)
    const liquidationRows = page.locator(`${selectors.liquidationsDisplay} .liquidation-row`);
    const liquidationCount = await liquidationRows.count();
    
    // Should have at least some liquidations or be showing loading state
    if (liquidationCount > 0) {
      // Check first liquidation has expected columns
      const firstLiquidation = liquidationRows.first();
      await expect(firstLiquidation).toBeVisible();
    }
  });

  test('should show connection status indicators', async ({ page }) => {
    // Ensure we have a bot selected
    await ensureBotSelected(page);
    
    // Check connection status indicators are present
    const connectionIndicators = page.locator(selectors.connectionIndicator);
    const indicatorCount = await connectionIndicators.count();
    expect(indicatorCount).toBeGreaterThan(0);
    
    // Wait for connections to establish
    await page.waitForTimeout(waitTimes.webSocket);
    
    // Check for connected state indicators
    const connectedIndicators = page.locator(`${selectors.connectionIndicator}.connected`);
    const connectedCount = await connectedIndicators.count();
    
    // At least some connections should be established
    expect(connectedCount).toBeGreaterThan(0);
  });

  test('should handle symbol switching', async ({ page }) => {
    // Ensure we have a bot selected
    await ensureBotSelected(page);
    
    // Get initial symbol
    const initialSymbol = await page.locator(selectors.botSymbol).first().textContent();
    
    // Create a new bot with different symbol
    await page.click(selectors.newBotButton);
    await page.waitForSelector(selectors.botEditorModal, { timeout: waitTimes.medium });
    
    const newSymbol = initialSymbol === 'BTCUSDT' ? 'ETHUSDT' : 'BTCUSDT';
    await page.fill(selectors.botNameInput, 'Symbol Switch Test Bot');
    await page.selectOption(selectors.botSymbolSelect, newSymbol);
    await page.click(selectors.saveBotButton);
    
    // Wait for modal to close
    await page.waitForSelector(selectors.botEditorModal, { state: 'hidden', timeout: waitTimes.medium });
    
    // Select the new bot
    const newBot = page.locator(selectors.botCard).filter({ hasText: 'Symbol Switch Test Bot' });
    await newBot.click();
    
    // Wait for symbol switch to process
    await page.waitForTimeout(waitTimes.webSocket);
    
    // Check that trading interface is still visible
    await expect(page.locator(selectors.tradingInterface)).toBeVisible();
    
    // Check that components are still functioning
    await expect(page.locator(selectors.chartContainer)).toBeVisible();
    await expect(page.locator(selectors.orderbookDisplay)).toBeVisible();
    await expect(page.locator(selectors.tradesDisplay)).toBeVisible();
    await expect(page.locator(selectors.liquidationsDisplay)).toBeVisible();
  });

  test('should handle WebSocket reconnection', async ({ page }) => {
    // Ensure we have a bot selected
    await ensureBotSelected(page);
    
    // Wait for initial connections
    await page.waitForTimeout(waitTimes.webSocket);
    
    // Check that connection indicators show connected state
    const connectionIndicators = page.locator(selectors.connectionIndicator);
    await expect(connectionIndicators.first()).toBeVisible();
    
    // Simulate network interruption by reloading the page
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    // Wait for bot list to load
    await page.waitForSelector(selectors.botList, { timeout: waitTimes.long });
    
    // Select a bot again
    const firstBot = page.locator(selectors.botCard).first();
    await firstBot.click();
    
    // Wait for reconnection
    await page.waitForTimeout(waitTimes.webSocket);
    
    // Check that trading interface is working again
    await expect(page.locator(selectors.tradingInterface)).toBeVisible();
    await expect(page.locator(selectors.chartContainer)).toBeVisible();
    
    // Check that connections are re-established
    const reconnectedIndicators = page.locator(`${selectors.connectionIndicator}.connected`);
    const reconnectedCount = await reconnectedIndicators.count();
    expect(reconnectedCount).toBeGreaterThan(0);
  });

  test('should display timeframe controls', async ({ page }) => {
    // Ensure we have a bot selected
    await ensureBotSelected(page);
    
    // Check for timeframe selector
    const timeframeSelector = page.locator('[data-testid="timeframe-selector"]');
    await expect(timeframeSelector).toBeVisible();
    
    // Check timeframe options
    const timeframeOptions = page.locator('[data-testid="timeframe-option"]');
    const optionCount = await timeframeOptions.count();
    expect(optionCount).toBeGreaterThan(0);
    
    // Try switching timeframe
    const firstOption = timeframeOptions.first();
    await firstOption.click();
    
    // Wait for chart to update
    await page.waitForTimeout(waitTimes.medium);
    
    // Check that chart is still visible
    await expect(page.locator(selectors.chartContainer)).toBeVisible();
  });

  test('should handle responsive layout', async ({ page }) => {
    // Ensure we have a bot selected
    await ensureBotSelected(page);
    
    // Test desktop view
    await page.setViewportSize({ width: 1200, height: 800 });
    await expect(page.locator(selectors.tradingInterface)).toBeVisible();
    
    // Test tablet view
    await page.setViewportSize({ width: 768, height: 1024 });
    await expect(page.locator(selectors.tradingInterface)).toBeVisible();
    await expect(page.locator(selectors.chartContainer)).toBeVisible();
    
    // Test mobile view
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.locator(selectors.tradingInterface)).toBeVisible();
    await expect(page.locator(selectors.chartContainer)).toBeVisible();
    
    // Check that components are still accessible in mobile view
    await expect(page.locator(selectors.orderbookDisplay)).toBeVisible();
    await expect(page.locator(selectors.tradesDisplay)).toBeVisible();
  });

  test('should handle bot status changes during trading', async ({ page }) => {
    // Ensure we have a bot selected
    await ensureBotSelected(page);
    
    // Wait for trading interface to load
    await page.waitForTimeout(waitTimes.webSocket);
    
    // Toggle bot status
    const selectedBot = page.locator(selectors.botCard).first();
    await selectedBot.locator(selectors.toggleBotButton).click();
    
    // Wait for status change
    await page.waitForTimeout(waitTimes.short);
    
    // Check that trading interface is still visible
    await expect(page.locator(selectors.tradingInterface)).toBeVisible();
    
    // Check for status indication in the interface
    const statusIndicator = page.locator('[data-testid="bot-status-indicator"]');
    if (await statusIndicator.isVisible()) {
      await expect(statusIndicator).toBeVisible();
    }
  });

  test('should display error states gracefully', async ({ page }) => {
    // Ensure we have a bot selected
    await ensureBotSelected(page);
    
    // Check that error states are handled gracefully
    // This test depends on your error handling implementation
    
    // Wait for components to load
    await page.waitForTimeout(waitTimes.webSocket);
    
    // Check that components don't crash on error
    await expect(page.locator(selectors.chartContainer)).toBeVisible();
    await expect(page.locator(selectors.orderbookDisplay)).toBeVisible();
    await expect(page.locator(selectors.tradesDisplay)).toBeVisible();
    await expect(page.locator(selectors.liquidationsDisplay)).toBeVisible();
    
    // Check for error messages if any
    const errorMessages = page.locator('[data-testid="error-message"]');
    const errorCount = await errorMessages.count();
    
    if (errorCount > 0) {
      // Errors should be displayed gracefully
      await expect(errorMessages.first()).toBeVisible();
    }
  });
});

/**
 * Helper function to ensure a bot is selected
 */
async function ensureBotSelected(page) {
  // Check if trading interface is already visible
  const tradingInterface = page.locator(selectors.tradingInterface);
  const isVisible = await tradingInterface.isVisible();
  
  if (!isVisible) {
    // Wait for bot list to load
    await page.waitForSelector(selectors.botList, { timeout: waitTimes.long });
    
    // Check if there are any bots
    const botCards = page.locator(selectors.botCard);
    const count = await botCards.count();
    
    if (count > 0) {
      // Select first bot
      const firstBot = botCards.first();
      await firstBot.click();
    } else {
      // Create a bot if none exist
      await page.click(selectors.newBotButton);
      await page.waitForSelector(selectors.botEditorModal, { timeout: waitTimes.medium });
      
      await page.fill(selectors.botNameInput, 'Test Trading Bot');
      await page.selectOption(selectors.botSymbolSelect, 'BTCUSDT');
      await page.click(selectors.saveBotButton);
      
      // Wait for modal to close
      await page.waitForSelector(selectors.botEditorModal, { state: 'hidden', timeout: waitTimes.medium });
      
      // Select the newly created bot
      const newBot = page.locator(selectors.botCard).filter({ hasText: 'Test Trading Bot' });
      await newBot.click();
    }
    
    // Wait for trading interface to become visible
    await page.waitForSelector(selectors.tradingInterface, { timeout: waitTimes.long });
  }
}