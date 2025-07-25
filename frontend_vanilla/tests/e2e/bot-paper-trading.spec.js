import { test, expect } from '@playwright/test';

// Helper function to select a symbol using the searchable dropdown
async function selectSymbol(page, symbol) {
  // Click on the dropdown button to open it
  const symbolDropdown = page.locator('[data-testid="bot-symbol-dropdown"]');
  await symbolDropdown.locator('[role="button"]').click();
  
  // Wait for dropdown to be visible
  await expect(symbolDropdown.locator('.dropdown-container')).toBeVisible();
  
  // Type the symbol in the search input
  const searchInput = symbolDropdown.locator('input[type="text"]');
  await searchInput.fill(symbol);
  
  // Wait for debounce
  await page.waitForTimeout(100);
  
  // Click on the first matching result
  const results = symbolDropdown.locator('li:not(.menu-item-disabled)');
  await results.first().locator('a').click();
  
  // Verify dropdown closed
  await expect(symbolDropdown.locator('.dropdown-container')).not.toBeVisible();
}

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
    await selectSymbol(page, 'BTCUSDT');
    
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
    await selectSymbol(page, 'ETHUSDT');
    
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
    await selectSymbol(page, 'ADAUSDT');
    
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

test.describe('Searchable Symbol Dropdown', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('http://localhost:3000');
    
    // Wait for the app to load
    await page.waitForSelector('#bot-navigation-placeholder', { state: 'hidden' });
    
    // Navigate to bot management and open create bot modal
    await page.click('text=Bot Management');
    await page.waitForSelector('#bot-management-section', { state: 'visible' });
    await page.click('text=Create Bot');
    await page.waitForSelector('#bot-editor-modal.modal-open');
  });
  
  test('should support case-insensitive search', async ({ page }) => {
    const symbolDropdown = page.locator('[data-testid="bot-symbol-dropdown"]');
    
    // Open dropdown
    await symbolDropdown.locator('[role="button"]').click();
    
    // Search with lowercase
    const searchInput = symbolDropdown.locator('input[type="text"]');
    await searchInput.fill('btc');
    await page.waitForTimeout(100);
    
    // Verify results contain BTCUSDT
    const results = symbolDropdown.locator('li:not(.menu-item-disabled)');
    const firstResult = results.first();
    await expect(firstResult).toContainText('BTC');
    
    // Clear and search with uppercase
    await searchInput.clear();
    await searchInput.fill('BTC');
    await page.waitForTimeout(100);
    
    // Should get same results
    await expect(firstResult).toContainText('BTC');
  });
  
  test('should support partial matching anywhere in symbol', async ({ page }) => {
    const symbolDropdown = page.locator('[data-testid="bot-symbol-dropdown"]');
    
    // Open dropdown
    await symbolDropdown.locator('[role="button"]').click();
    
    // Search for 'usdt' which appears at the end of many symbols
    const searchInput = symbolDropdown.locator('input[type="text"]');
    await searchInput.fill('usdt');
    await page.waitForTimeout(100);
    
    // Verify multiple results
    const results = symbolDropdown.locator('li:not(.menu-item-disabled)');
    const count = await results.count();
    expect(count).toBeGreaterThan(5); // Should find many USDT pairs
  });
  
  test('should navigate with keyboard arrows and select with Enter', async ({ page }) => {
    const symbolDropdown = page.locator('[data-testid="bot-symbol-dropdown"]');
    
    // Open dropdown by clicking (to ensure it's open for keyboard testing)
    await symbolDropdown.locator('[role="button"]').click();
    await expect(symbolDropdown.locator('.dropdown-container')).toBeVisible();
    
    // Type search in the search input
    const searchInput = symbolDropdown.locator('input[type="text"]');
    await searchInput.fill('eth');
    await page.waitForTimeout(100);
    
    // Navigate with arrow keys
    await searchInput.press('ArrowDown');
    await searchInput.press('ArrowDown');
    
    // Select with Enter
    await searchInput.press('Enter');
    
    // Wait for dropdown to close
    await page.waitForTimeout(300);
    
    // Verify dropdown closed and value selected
    await expect(symbolDropdown.locator('.dropdown-container')).not.toBeVisible();
    await expect(symbolDropdown.locator('.searchable-dropdown-display-text')).toContainText('ETH');
  });
  
  test('should clear search with clear button', async ({ page }) => {
    const symbolDropdown = page.locator('[data-testid="bot-symbol-dropdown"]');
    
    // Open dropdown
    await symbolDropdown.locator('[role="button"]').click();
    
    const searchInput = symbolDropdown.locator('input[type="text"]');
    const clearButton = symbolDropdown.locator('.btn-ghost.btn-xs');
    
    // Initially clear button should not be visible
    await expect(clearButton).not.toBeVisible();
    
    // Type search
    await searchInput.fill('btc');
    await page.waitForTimeout(100);
    
    // Clear button should appear
    await expect(clearButton).toBeVisible();
    
    // Get initial result count
    const results = symbolDropdown.locator('li:not(.menu-item-disabled)');
    const filteredCount = await results.count();
    
    // Click clear
    await clearButton.click();
    
    // Wait for clear action to complete
    await page.waitForTimeout(50);
    
    // Verify search cleared and all results shown
    expect(await searchInput.inputValue()).toBe('');
    await expect(clearButton).not.toBeVisible();
    
    await page.waitForTimeout(100);
    const allCount = await results.count();
    expect(allCount).toBeGreaterThan(filteredCount);
  });
  
  test('should show "No results found" for non-matching search', async ({ page }) => {
    const symbolDropdown = page.locator('[data-testid="bot-symbol-dropdown"]');
    
    // Open dropdown
    await symbolDropdown.locator('[role="button"]').click();
    
    // Search for non-existent symbol
    const searchInput = symbolDropdown.locator('input[type="text"]');
    await searchInput.fill('xyz123');
    await page.waitForTimeout(100);
    
    // Should show no results message
    const noResultsMessage = symbolDropdown.locator('.menu-item-disabled');
    await expect(noResultsMessage).toBeVisible();
    await expect(noResultsMessage).toHaveText('No results found');
  });
  
  test('should start with empty symbol when creating new bot', async ({ page }) => {
    const symbolDropdown = page.locator('[data-testid="bot-symbol-dropdown"]');
    
    // Verify dropdown shows placeholder text
    const displayText = symbolDropdown.locator('.searchable-dropdown-display-text');
    await expect(displayText).toHaveText('Select a trading pair');
    await expect(displayText).toHaveClass(/text-base-content\/60/);
    
    // Verify hidden input is empty
    const hiddenInput = symbolDropdown.locator('input[type="hidden"]');
    await expect(hiddenInput).toHaveValue('');
  });
  
  test('should not retain symbol when creating multiple bots', async ({ page }) => {
    const timestamp = Date.now();
    const firstBotName = `First Bot ${timestamp}`;
    
    // Create first bot with BTCUSDT
    await page.fill('#bot-name', firstBotName);
    await selectSymbol(page, 'BTCUSDT');
    await page.click('button[type="submit"]');
    await page.waitForSelector('#bot-editor-modal.modal-open', { state: 'hidden' });
    
    // Verify first bot was created
    await expect(page.locator(`[data-testid="bot-card"]:has-text("${firstBotName}")`)).toBeVisible();
    
    // Click Create Bot again for second bot
    await page.click('text=Create Bot');
    await page.waitForSelector('#bot-editor-modal.modal-open');
    
    // Verify symbol field is empty for second bot creation
    const symbolDropdown = page.locator('[data-testid="bot-symbol-dropdown"]');
    const displayText = symbolDropdown.locator('.searchable-dropdown-display-text');
    await expect(displayText).toHaveText('Select a trading pair');
    await expect(displayText).toHaveClass(/text-base-content\/60/);
    
    // Also verify hidden input is empty
    const hiddenInput = symbolDropdown.locator('input[type="hidden"]');
    await expect(hiddenInput).toHaveValue('');
  });
  
  test('should clear symbol after editing a bot and then creating new bot', async ({ page }) => {
    const timestamp = Date.now();
    const existingBotName = `Existing Bot ${timestamp}`;
    
    // First create a bot to edit
    await page.fill('#bot-name', existingBotName);
    await selectSymbol(page, 'ETHUSDT');
    await page.click('button[type="submit"]');
    await page.waitForSelector('#bot-editor-modal.modal-open', { state: 'hidden' });
    
    // Edit the bot
    const botCard = page.locator(`[data-testid="bot-card"]:has-text("${existingBotName}")`);
    await botCard.locator('[data-testid="bot-menu-button"]').click();
    await botCard.locator('[data-testid="edit-bot-button"]').click();
    await page.waitForSelector('#bot-editor-modal.modal-open');
    
    // Verify symbol is populated in edit mode
    const symbolDropdown = page.locator('[data-testid="bot-symbol-dropdown"]');
    await expect(symbolDropdown.locator('.searchable-dropdown-display-text')).toContainText('ETH');
    
    // Close edit modal without saving
    await page.click('#cancel-btn');
    await page.waitForSelector('#bot-editor-modal.modal-open', { state: 'hidden' });
    
    // Now click Create Bot
    await page.click('text=Create Bot');
    await page.waitForSelector('#bot-editor-modal.modal-open');
    
    // Verify symbol field is empty
    const displayText = symbolDropdown.locator('.searchable-dropdown-display-text');
    await expect(displayText).toHaveText('Select a trading pair');
    await expect(displayText).toHaveClass(/text-base-content\/60/);
  });
});