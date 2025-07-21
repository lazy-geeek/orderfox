import { test, expect } from '@playwright/test';

test.describe('Bot Paper Trading Toggle', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('http://localhost:3000');
    
    // Wait for the app to load
    await page.waitForSelector('#bot-navigation-placeholder', { state: 'hidden' });
  });

  test('should create bot with paper trading enabled by default', async ({ page }) => {
    const timestamp = Date.now();
    const botName = `Test Paper Bot ${timestamp}`;
    
    // Navigate to bot management
    await page.click('text=Bot Management');
    
    // Wait for bot management section to be visible
    await page.waitForSelector('#bot-management-section', { state: 'visible' });
    
    // Click create bot button
    await page.click('text=Create Bot');
    
    // Wait for modal to open
    await page.waitForSelector('#bot-editor-modal.modal-open');
    
    // Fill form
    await page.fill('#bot-name', botName);
    await page.selectOption('#bot-symbol', 'BTCUSDT');
    
    // Verify paper trading toggle is checked by default
    const paperToggle = page.locator('#bot-paper-trading');
    await expect(paperToggle).toBeChecked();
    
    // Verify the text shows paper trading mode
    const paperText = page.locator('#paper-trading-text');
    await expect(paperText).toHaveText('Paper trading mode (simulated trades)');
    
    // Submit form
    await page.click('button[type="submit"]');
    
    // Wait for modal to close
    await page.waitForSelector('#bot-editor-modal.modal-open', { state: 'hidden' });
    
    // Verify bot card shows paper trading badge
    await expect(page.locator(`text=${botName}`)).toBeVisible();
    await expect(page.locator(`[data-testid="bot-card"]:has-text("${botName}") .badge:has-text("📝 Paper")`)).toBeVisible();
  });

  test('should create bot with live trading mode', async ({ page }) => {
    const timestamp = Date.now();
    const botName = `Test Live Bot ${timestamp}`;
    
    // Navigate to bot management
    await page.click('text=Bot Management');
    
    // Wait for bot management section
    await page.waitForSelector('#bot-management-section', { state: 'visible' });
    
    // Click create bot button
    await page.click('text=Create Bot');
    
    // Wait for modal
    await page.waitForSelector('#bot-editor-modal.modal-open');
    
    // Fill form
    await page.fill('#bot-name', botName);
    await page.selectOption('#bot-symbol', 'ETHUSDT');
    
    // Uncheck paper trading toggle
    const paperToggle = page.locator('#bot-paper-trading');
    await paperToggle.uncheck();
    
    // Verify the text shows live trading mode
    const paperText = page.locator('#paper-trading-text');
    await expect(paperText).toHaveText('Live trading mode (real trades)');
    
    // Submit form
    await page.click('button[type="submit"]');
    
    // Wait for modal to close
    await page.waitForSelector('#bot-editor-modal.modal-open', { state: 'hidden' });
    
    // Verify bot card shows live trading badge
    await expect(page.locator(`text=${botName}`)).toBeVisible();
    await expect(page.locator(`[data-testid="bot-card"]:has-text("${botName}") .badge:has-text("💰 Live")`)).toBeVisible();
  });

  test('should toggle paper trading mode when editing bot', async ({ page }) => {
    const timestamp = Date.now();
    const botName = `Toggle Test Bot ${timestamp}`;
    
    // First create a bot
    await page.click('text=Bot Management');
    await page.waitForSelector('#bot-management-section', { state: 'visible' });
    await page.click('text=Create Bot');
    await page.waitForSelector('#bot-editor-modal.modal-open');
    
    await page.fill('#bot-name', botName);
    await page.selectOption('#bot-symbol', 'BTCUSDT');
    await page.click('button[type="submit"]');
    await page.waitForSelector('#bot-editor-modal.modal-open', { state: 'hidden' });
    
    // Find the bot card
    const botCard = page.locator(`[data-testid="bot-card"]:has-text("${botName}")`);
    await expect(botCard).toBeVisible();
    
    // Verify initial state is paper trading
    await expect(botCard.locator('.badge:has-text("📝 Paper")')).toBeVisible();
    
    // Open bot menu and click edit
    await botCard.locator('[data-testid="bot-menu-button"]').click();
    await botCard.locator('[data-testid="edit-bot-button"]').click();
    
    // Wait for modal to open
    await page.waitForSelector('#bot-editor-modal.modal-open');
    
    // Verify toggle is checked (paper trading)
    const paperToggle = page.locator('#bot-paper-trading');
    await expect(paperToggle).toBeChecked();
    
    // Toggle to live trading
    await paperToggle.uncheck();
    
    // Verify text updated
    const paperText = page.locator('#paper-trading-text');
    await expect(paperText).toHaveText('Live trading mode (real trades)');
    
    // Save changes
    await page.click('button[type="submit"]');
    
    // Wait for modal to close
    await page.waitForSelector('#bot-editor-modal.modal-open', { state: 'hidden' });
    
    // Verify bot card now shows live trading
    await expect(botCard.locator('.badge:has-text("💰 Live")')).toBeVisible();
    
    // Edit again and toggle back to paper
    await botCard.locator('[data-testid="bot-menu-button"]').click();
    await botCard.locator('[data-testid="edit-bot-button"]').click();
    await page.waitForSelector('#bot-editor-modal.modal-open');
    
    // Verify toggle is unchecked (live trading)
    await expect(paperToggle).not.toBeChecked();
    
    // Toggle back to paper trading
    await paperToggle.check();
    await expect(paperText).toHaveText('Paper trading mode (simulated trades)');
    
    // Save changes
    await page.click('button[type="submit"]');
    await page.waitForSelector('#bot-editor-modal.modal-open', { state: 'hidden' });
    
    // Verify bot card shows paper trading again
    await expect(botCard.locator('.badge:has-text("📝 Paper")')).toBeVisible();
  });

  test('should maintain paper trading state when updating other fields', async ({ page }) => {
    const timestamp = Date.now();
    const botName = `Persistence Test Bot ${timestamp}`;
    const updatedBotName = `Updated Persistence Bot ${timestamp}`;
    
    // Create a bot with live trading
    await page.click('text=Bot Management');
    await page.waitForSelector('#bot-management-section', { state: 'visible' });
    await page.click('text=Create Bot');
    await page.waitForSelector('#bot-editor-modal.modal-open');
    
    await page.fill('#bot-name', botName);
    await page.selectOption('#bot-symbol', 'ADAUSDT');
    
    // Set to live trading
    const paperToggle = page.locator('#bot-paper-trading');
    await paperToggle.uncheck();
    
    await page.click('button[type="submit"]');
    await page.waitForSelector('#bot-editor-modal.modal-open', { state: 'hidden' });
    
    // Find the bot card
    const botCard = page.locator(`[data-testid="bot-card"]:has-text("${botName}")`);
    await expect(botCard).toBeVisible();
    await expect(botCard.locator('.badge:has-text("💰 Live")')).toBeVisible();
    
    // Edit bot and change only the name
    await botCard.locator('[data-testid="bot-menu-button"]').click();
    await botCard.locator('[data-testid="edit-bot-button"]').click();
    await page.waitForSelector('#bot-editor-modal.modal-open');
    
    // Verify paper trading toggle is still unchecked
    await expect(paperToggle).not.toBeChecked();
    
    // Change only the name
    await page.fill('#bot-name', updatedBotName);
    
    // Save without touching the paper trading toggle
    await page.click('button[type="submit"]');
    await page.waitForSelector('#bot-editor-modal.modal-open', { state: 'hidden' });
    
    // Verify bot still shows live trading
    const updatedBotCard = page.locator(`[data-testid="bot-card"]:has-text("${updatedBotName}")`);
    await expect(updatedBotCard).toBeVisible();
    await expect(updatedBotCard.locator('.badge:has-text("💰 Live")')).toBeVisible();
  });

  test('should show correct paper trading status for multiple bots', async ({ page }) => {
    const timestamp = Date.now();
    const paperBot1Name = `Paper Bot 1 ${timestamp}`;
    const liveBot1Name = `Live Bot 1 ${timestamp}`;  
    const paperBot2Name = `Paper Bot 2 ${timestamp}`;
    
    // Navigate to bot management
    await page.click('text=Bot Management');
    await page.waitForSelector('#bot-management-section', { state: 'visible' });
    
    // Create first bot (paper trading)
    await page.click('text=Create Bot');
    await page.waitForSelector('#bot-editor-modal.modal-open');
    await page.fill('#bot-name', paperBot1Name);
    await page.selectOption('#bot-symbol', 'BTCUSDT');
    await page.click('button[type="submit"]');
    await page.waitForSelector('#bot-editor-modal.modal-open', { state: 'hidden' });
    
    // Create second bot (live trading)
    await page.click('text=Create Bot');
    await page.waitForSelector('#bot-editor-modal.modal-open');
    await page.fill('#bot-name', liveBot1Name);
    await page.selectOption('#bot-symbol', 'ETHUSDT');
    await page.locator('#bot-paper-trading').uncheck();
    await page.click('button[type="submit"]');
    await page.waitForSelector('#bot-editor-modal.modal-open', { state: 'hidden' });
    
    // Create third bot (paper trading)
    await page.click('text=Create Bot');
    await page.waitForSelector('#bot-editor-modal.modal-open');
    await page.fill('#bot-name', paperBot2Name);
    await page.selectOption('#bot-symbol', 'ADAUSDT');
    await page.click('button[type="submit"]');
    await page.waitForSelector('#bot-editor-modal.modal-open', { state: 'hidden' });
    
    // Verify all bots show correct trading mode
    await expect(page.locator(`[data-testid="bot-card"]:has-text("${paperBot1Name}") .badge:has-text("📝 Paper")`)).toBeVisible();
    await expect(page.locator(`[data-testid="bot-card"]:has-text("${liveBot1Name}") .badge:has-text("💰 Live")`)).toBeVisible();
    await expect(page.locator(`[data-testid="bot-card"]:has-text("${paperBot2Name}") .badge:has-text("📝 Paper")`)).toBeVisible();
  });
});