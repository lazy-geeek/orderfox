/**
 * Bot Selection Test
 * This test runs in the 'trading-setup' project and prepares a bot for all trading tests
 * It ensures a bot is created and selected before any trading features are tested
 */

import { test, expect } from './fixtures/index.js';
import { selectors } from './fixtures/test-data.js';

test.describe('Trading Setup - Bot Selection', () => {
  test('should create and select a bot for trading tests', async ({ selectedBot, pageWithBot }) => {
    // Setting up trading bot
    
    // The pageWithBot fixture should have already navigated and selected the bot
    // Let's verify it's properly selected
    
    // Check that trading interface is visible
    await expect(pageWithBot.locator(selectors.tradingInterface)).toBeVisible();
    
    // Check that chart container or chart content is visible
    const chartContainer = pageWithBot.locator(selectors.chartContainer);
    const chartCanvas = pageWithBot.locator('canvas').first(); // TradingView uses canvas
    
    // Either the container with testid or the actual chart canvas should be visible
    try {
      await expect(chartContainer).toBeVisible({ timeout: 2000 });
    } catch {
      await expect(chartCanvas).toBeVisible();
    }
    // Chart is visible
    
    // Check that the selected bot info is displayed
    const selectedBotInfo = pageWithBot.locator('#selected-bot-name');
    await expect(selectedBotInfo).toBeVisible();
    await expect(selectedBotInfo).toContainText(selectedBot.name);
    // Bot is selected
    
    // Verify tabbed trading display is present
    const tabbedDisplay = pageWithBot.locator('.orderfox-tabbed-trading-display');
    await expect(tabbedDisplay).toBeVisible();
    // Tabbed trading display is visible
    
    // Check all three tabs are available
    // DaisyUI tabs use hidden radio inputs with visible labels
    const orderBookTab = pageWithBot.locator('input#tab-orderbook');
    const tradesTab = pageWithBot.locator('input#tab-trades');
    const liquidationsTab = pageWithBot.locator('input#tab-liquidations');
    
    // Check the radio inputs exist (they may be visually hidden)
    await expect(orderBookTab).toBeAttached();
    await expect(tradesTab).toBeAttached();
    await expect(liquidationsTab).toBeAttached();
    
    // Check the tab labels are visible
    const orderBookLabel = pageWithBot.locator('label[for="tab-orderbook"]');
    const tradesLabel = pageWithBot.locator('label[for="tab-trades"]');
    const liquidationsLabel = pageWithBot.locator('label[for="tab-liquidations"]');
    
    await expect(orderBookLabel).toBeVisible();
    await expect(tradesLabel).toBeVisible();
    await expect(liquidationsLabel).toBeVisible();
    
    // All trading tabs are available
    
    // UI components are verified - test complete
    
    // Trading setup complete
  });
});