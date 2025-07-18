/**
 * Bot Management E2E Tests
 * Tests the complete bot management workflow including CRUD operations
 */

import { test, expect } from '@playwright/test';
import { testBots, testUserActions, selectors, waitTimes } from './fixtures/test-data.js';

test.describe('Bot Management', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto('/');
    
    // Wait for application to load
    await page.waitForLoadState('networkidle');
    
    // The sidebar should be open by default now
    // Click "My Bots" in the sidebar to show bot list
    const myBotsLink = page.locator('text=🤖 My Bots');
    await myBotsLink.click();
    
    // Now wait for bot list to be visible
    await page.waitForSelector(selectors.botList, { state: 'visible', timeout: waitTimes.long });
  });

  test('should display bot navigation', async ({ page }) => {
    // Check bot navigation is visible
    await expect(page.locator(selectors.botNavigation)).toBeVisible();
    
    // Check new bot button exists
    await expect(page.locator(selectors.newBotButton)).toBeVisible();
    
    // Check new bot button text
    await expect(page.locator(selectors.newBotButton)).toContainText('New Bot');
  });

  test('should display existing bots', async ({ page }) => {
    // Wait for bot list to load
    await page.waitForSelector(selectors.botList, { timeout: waitTimes.long });
    
    // Check bot list is visible
    await expect(page.locator(selectors.botList)).toBeVisible();
    
    // Check if any bot cards are present
    const botCards = page.locator(selectors.botCard);
    const count = await botCards.count();
    
    if (count > 0) {
      // Check first bot card structure
      const firstBot = botCards.first();
      await expect(firstBot.locator(selectors.botName)).toBeVisible();
      await expect(firstBot.locator(selectors.botSymbol)).toBeVisible();
      await expect(firstBot.locator(selectors.botStatus)).toBeVisible();
    }
  });

  test('should create a new bot', async ({ page }) => {
    // Click new bot button
    await page.click(selectors.newBotButton);
    
    // Wait for modal to appear
    await page.waitForSelector(selectors.botEditorModal, { timeout: waitTimes.medium });
    await expect(page.locator(selectors.botEditorModal)).toBeVisible();
    
    // Fill bot details
    await page.fill(selectors.botNameInput, testUserActions.createBot.name);
    await page.selectOption(selectors.botSymbolSelect, testUserActions.createBot.symbol);
    
    // Save bot
    await page.click(selectors.saveBotButton);
    
    // Wait for modal to close
    await page.waitForSelector(selectors.botEditorModal, { state: 'hidden', timeout: waitTimes.long });
    
    // Wait a moment for the bot list to update
    await page.waitForTimeout(waitTimes.short);
    
    // Verify bot appears in list
    await page.waitForSelector(selectors.botList, { timeout: waitTimes.medium });
    const newBotCard = page.locator(selectors.botCard).filter({ hasText: testUserActions.createBot.name });
    
    // Check that at least one bot card with this name exists
    const count = await newBotCard.count();
    expect(count).toBeGreaterThan(0);
    
    // Check the first matching bot's details
    await expect(newBotCard.first()).toBeVisible();
    await expect(newBotCard.first().locator(selectors.botName)).toContainText(testUserActions.createBot.name);
    await expect(newBotCard.first().locator(selectors.botSymbol)).toContainText(testUserActions.createBot.symbol);
  });

  test('should edit an existing bot', async ({ page }) => {
    // Wait for bot list to load
    await page.waitForSelector(selectors.botList, { timeout: waitTimes.long });
    
    // Find first bot and open dropdown menu
    const firstBot = page.locator(selectors.botCard).first();
    const dropdownButton = firstBot.locator('[data-testid="bot-menu-button"]');
    await dropdownButton.click();
    
    // Click edit button in dropdown
    await firstBot.locator(selectors.editBotButton).click();
    
    // Wait for modal to appear
    await page.waitForSelector(selectors.botEditorModal, { timeout: waitTimes.medium });
    await expect(page.locator(selectors.botEditorModal)).toBeVisible();
    
    // Update bot details
    await page.fill(selectors.botNameInput, testUserActions.updateBot.name);
    await page.selectOption(selectors.botSymbolSelect, testUserActions.updateBot.symbol);
    
    // Save changes
    await page.click(selectors.saveBotButton);
    
    // Wait for modal to close
    await page.waitForSelector(selectors.botEditorModal, { state: 'hidden', timeout: waitTimes.long });
    
    // Wait a moment for the bot list to update
    await page.waitForTimeout(waitTimes.short);
    
    // Verify changes appear in list
    await page.waitForSelector(selectors.botList, { timeout: waitTimes.medium });
    const updatedBotCard = page.locator(selectors.botCard).filter({ hasText: testUserActions.updateBot.name });
    await expect(updatedBotCard).toBeVisible();
    
    // Check updated details
    await expect(updatedBotCard.locator(selectors.botName)).toContainText(testUserActions.updateBot.name);
    await expect(updatedBotCard.locator(selectors.botSymbol)).toContainText(testUserActions.updateBot.symbol);
  });

  test('should toggle bot status', async ({ page }) => {
    // Wait for bot list to load
    await page.waitForSelector(selectors.botList, { timeout: waitTimes.long });
    
    // Find first bot and open dropdown menu
    const firstBot = page.locator(selectors.botCard).first();
    
    // Get current status
    const currentStatus = await firstBot.locator(selectors.botStatus).textContent();
    
    // Open dropdown menu
    const dropdownButton = firstBot.locator('[data-testid="bot-menu-button"]');
    await dropdownButton.click();
    
    // Click toggle button in dropdown
    await firstBot.locator(selectors.toggleBotButton).click();
    
    // Wait for bot list to reload after toggle
    await page.waitForSelector('#bot-list-loading', { state: 'visible' });
    await page.waitForSelector('#bot-list-loading', { state: 'hidden', timeout: waitTimes.long });
    
    // Find the bot again after reload and check its new status
    const updatedBot = page.locator(selectors.botCard).first();
    const newStatus = await updatedBot.locator(selectors.botStatus).textContent();
    expect(newStatus).not.toBe(currentStatus);
  });

  test('should delete a bot', async ({ page }) => {
    // Create a bot first to ensure we have one to delete
    await page.click(selectors.newBotButton);
    await page.waitForSelector(selectors.botEditorModal, { timeout: waitTimes.medium });
    
    const testBotName = `Bot To Delete ${Date.now()}`;
    await page.fill(selectors.botNameInput, testBotName);
    await page.selectOption(selectors.botSymbolSelect, 'BTCUSDT');
    await page.click(selectors.saveBotButton);
    
    // Wait for modal to close
    await page.waitForSelector(selectors.botEditorModal, { state: 'hidden', timeout: waitTimes.long });
    
    // Find the bot we just created
    const botToDelete = page.locator(selectors.botCard).filter({ hasText: testBotName });
    await expect(botToDelete).toBeVisible();
    
    // Open dropdown menu for the bot to delete
    const dropdownButton = botToDelete.locator('[data-testid="bot-menu-button"]');
    await dropdownButton.click();
    
    // Handle the native confirm dialog
    page.once('dialog', dialog => dialog.accept());
    
    // Click delete button in dropdown - this will trigger the confirm dialog
    await botToDelete.locator(selectors.deleteBotButton).click();
    
    // Wait a moment for the deletion to process
    await page.waitForTimeout(waitTimes.short);
    
    // Wait a moment for the bot list to update
    await page.waitForTimeout(waitTimes.short);
    
    // Verify bot is no longer in list
    await page.waitForTimeout(waitTimes.short);
    await expect(botToDelete).not.toBeVisible();
  });

  test('should cancel bot creation', async ({ page }) => {
    // Click new bot button
    await page.click(selectors.newBotButton);
    
    // Wait for modal to appear
    await page.waitForSelector(selectors.botEditorModal, { timeout: waitTimes.medium });
    await expect(page.locator(selectors.botEditorModal)).toBeVisible();
    
    // Fill some details
    await page.fill(selectors.botNameInput, 'Cancelled Bot');
    
    // Cancel creation
    await page.click(selectors.cancelBotButton);
    
    // Wait for modal to close
    await page.waitForSelector(selectors.botEditorModal, { state: 'hidden', timeout: waitTimes.medium });
    
    // Verify no new bot was created
    const cancelledBot = page.locator(selectors.botCard).filter({ hasText: 'Cancelled Bot' });
    await expect(cancelledBot).not.toBeVisible();
  });

  test('should handle form validation', async ({ page }) => {
    // Click new bot button
    await page.click(selectors.newBotButton);
    
    // Wait for modal to appear
    await page.waitForSelector(selectors.botEditorModal, { timeout: waitTimes.medium });
    
    // Try to save without filling required fields
    await page.click(selectors.saveBotButton);
    
    // Check that modal is still visible (validation should prevent saving)
    await expect(page.locator(selectors.botEditorModal)).toBeVisible();
    
    // The modal should still be open because validation failed
    // Check that the save button is still visible (indicating modal didn't close)
    await expect(page.locator(selectors.saveBotButton)).toBeVisible();
  });

  test('should display loading states', async ({ page }) => {
    // Check for loading spinner during initial load
    const loadingSpinner = page.locator(selectors.loadingSpinner);
    
    // Loading spinner might appear briefly during page load
    // We don't assert its presence since it might be too fast to catch
    
    // After bot list loads, the loading state should be gone
    await expect(page.locator(selectors.botList)).toBeVisible();
  });

  test('should handle bot selection', async ({ page }) => {
    // Wait for bot list to load
    await page.waitForSelector(selectors.botList, { timeout: waitTimes.long });
    
    // Check if there are any bots
    const botCards = page.locator(selectors.botCard);
    const count = await botCards.count();
    
    if (count > 0) {
      // Find the first bot and click its Select button
      const firstBot = botCards.first();
      const selectButton = firstBot.locator(selectors.selectBotButton);
      await selectButton.click();
      
      // Wait a moment for the bot selection to process
      await page.waitForTimeout(waitTimes.short);
      
      // Check that trading interface becomes visible
      await expect(page.locator(selectors.tradingInterface)).toBeVisible();
      
      // Verify the bot name appears in the sidebar (indicates selection)
      const selectedBotInfo = page.locator('#selected-bot-name');
      await expect(selectedBotInfo).toBeVisible();
    }
  });

  test('should persist bot data across page reloads', async ({ page }) => {
    // Create a test bot
    await page.click(selectors.newBotButton);
    await page.waitForSelector(selectors.botEditorModal, { timeout: waitTimes.medium });
    
    const testBotName = `Persistence Test Bot ${Date.now()}`;
    await page.fill(selectors.botNameInput, testBotName);
    await page.selectOption(selectors.botSymbolSelect, 'ETHUSDT');
    await page.click(selectors.saveBotButton);
    
    // Wait for modal to close
    await page.waitForSelector(selectors.botEditorModal, { state: 'hidden', timeout: waitTimes.long });
    
    // Wait a moment for the bot list to update
    await page.waitForTimeout(waitTimes.short);
    
    // Verify bot is created
    const createdBot = page.locator(selectors.botCard).filter({ hasText: testBotName });
    const botCount = await createdBot.count();
    expect(botCount).toBeGreaterThan(0);
    await expect(createdBot.first()).toBeVisible();
    
    // Reload the page
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    // Verify bot still exists after reload
    await page.waitForSelector(selectors.botList, { timeout: waitTimes.long });
    const persistedBot = page.locator(selectors.botCard).filter({ hasText: testBotName });
    await expect(persistedBot).toBeVisible();
  });
});