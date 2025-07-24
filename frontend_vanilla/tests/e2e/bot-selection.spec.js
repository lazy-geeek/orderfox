/**
 * Bot Selection Test
 * This test runs in the 'trading-setup' project and prepares a bot for all trading tests
 * It ensures a bot is created and selected before any trading features are tested
 */

import { test, expect } from './fixtures/index.js';
import { selectors, waitForModalOpen } from './fixtures/test-data.js';

test.describe('Trading Setup - Bot Selection', () => {
  test('should create and select a bot for trading tests', async ({ selectedBot, pageWithBot }) => {
    // Setting up trading bot
    
    // The pageWithBot fixture should have already navigated and selected the bot
    // Now the trading interface should be in a modal
    
    // Wait for trading modal to be visible
    await waitForModalOpen(pageWithBot, selectors.tradingModal);
    
    // Check that trading modal is visible
    await expect(pageWithBot.locator(selectors.tradingModal)).toBeVisible();
    // Modal is open
    
    // Check that the modal close button is present
    await expect(pageWithBot.locator(selectors.modalCloseButton)).toBeVisible();
    
    // Check that bot list is still visible behind modal (not covered)
    const botList = pageWithBot.locator(selectors.botList);
    await expect(botList).toBeVisible();
    // Bot list remains visible in background
    
    // Check that trading interface container is visible inside modal
    const tradingContainer = pageWithBot.locator(selectors.tradingInterfaceContainer);
    await expect(tradingContainer).toBeVisible();
    
    // Check that chart container is visible inside modal
    const chartContainer = pageWithBot.locator(`${selectors.tradingModal} ${selectors.chartContainer}`);
    const chartCanvas = pageWithBot.locator(`${selectors.tradingModal} canvas`).first(); // TradingView uses canvas
    
    // Either the container with testid or the actual chart canvas should be visible within modal
    try {
      await expect(chartContainer).toBeVisible({ timeout: 2000 });
    } catch {
      await expect(chartCanvas).toBeVisible();
    }
    // Chart is visible in modal
    
    // Check that the selected bot info is displayed (outside modal)
    const selectedBotInfo = pageWithBot.locator('#selected-bot-name');
    await expect(selectedBotInfo).toBeVisible();
    await expect(selectedBotInfo).toContainText(selectedBot.name);
    // Bot is selected and displayed outside modal
    
    // Verify tabbed trading display is present inside modal
    const tabbedDisplay = pageWithBot.locator(`${selectors.tradingModal} .orderfox-tabbed-trading-display`);
    await expect(tabbedDisplay).toBeVisible();
    // Tabbed trading display is visible in modal
    
    // Check all three tabs are available inside modal
    // DaisyUI tabs use hidden radio inputs with visible labels
    const orderBookTab = pageWithBot.locator(`${selectors.tradingModal} input#tab-orderbook`);
    const tradesTab = pageWithBot.locator(`${selectors.tradingModal} input#tab-trades`);
    const liquidationsTab = pageWithBot.locator(`${selectors.tradingModal} input#tab-liquidations`);
    
    // Check the radio inputs exist (they may be visually hidden)
    await expect(orderBookTab).toBeAttached();
    await expect(tradesTab).toBeAttached();
    await expect(liquidationsTab).toBeAttached();
    
    // Check the tab labels are visible inside modal
    const orderBookLabel = pageWithBot.locator(`${selectors.tradingModal} label[for="tab-orderbook"]`);
    const tradesLabel = pageWithBot.locator(`${selectors.tradingModal} label[for="tab-trades"]`);
    const liquidationsLabel = pageWithBot.locator(`${selectors.tradingModal} label[for="tab-liquidations"]`);
    
    await expect(orderBookLabel).toBeVisible();
    await expect(tradesLabel).toBeVisible();
    await expect(liquidationsLabel).toBeVisible();
    
    // All trading tabs are available in modal
    
    // Modal UI components are verified - test complete
    
    // Trading modal setup complete
  });
});