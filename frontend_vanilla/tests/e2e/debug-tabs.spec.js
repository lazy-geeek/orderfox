import { test, expect } from '@playwright/test';

test.describe('Debug Tabbed Interface', () => {
  test('should capture console errors when using tabs', async ({ page }) => {
    // Capture all console messages
    const consoleMessages = [];
    const consoleErrors = [];
    
    page.on('console', msg => {
      const type = msg.type();
      const text = msg.text();
      
      if (type === 'error') {
        consoleErrors.push(text);
        console.error('Browser Error:', text);
      } else {
        consoleMessages.push({ type, text });
      }
    });

    // Navigate to the application
    await page.goto('http://localhost:3000');
    
    // Wait for the page to load
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);
    
    // Try to find a bot or create one to enable trading interface
    try {
      // Click on My Bots
      const myBotsLink = page.locator('text=🤖 My Bots');
      await myBotsLink.click();
      
      // Wait for bot list
      await page.waitForSelector('[data-testid="bot-list"]', { timeout: 5000 });
      
      // Check if there are any bots
      const botCards = page.locator('[data-testid="bot-card"]');
      const count = await botCards.count();
      
      if (count > 0) {
        // Select the first bot
        const firstBot = botCards.first();
        const selectButton = firstBot.locator('.select-bot-btn');
        await selectButton.click();
        
        // Wait for bot selection
        await page.waitForTimeout(2000);
      } else {
        console.log('No bots found, creating one...');
        
        // Create a bot
        await page.click('[data-testid="new-bot-button"]');
        await page.waitForSelector('[data-testid="bot-editor-modal"]');
        
        await page.fill('[data-testid="bot-name-input"]', 'Debug Test Bot');
        await page.selectOption('[data-testid="bot-symbol-select"]', 'BTCUSDT');
        await page.click('[data-testid="save-bot-button"]');
        
        // Wait for save and then select the bot
        await page.waitForTimeout(2000);
        
        const newBot = page.locator('[data-testid="bot-card"]').first();
        const selectButton = newBot.locator('.select-bot-btn');
        await selectButton.click();
        
        await page.waitForTimeout(2000);
      }
      
      // Now check if the tabbed interface is visible
      const tabbedInterface = page.locator('.orderfox-tabbed-trading-display');
      const isVisible = await tabbedInterface.isVisible();
      
      console.log('Tabbed interface visible:', isVisible);
      
      if (isVisible) {
        // Try clicking on each tab
        console.log('Testing Order Book tab...');
        const orderBookTab = page.getByRole('radio', { name: 'Order Book' });
        await orderBookTab.click();
        await page.waitForTimeout(1000);
        
        console.log('Testing Trades tab...');
        const tradesTab = page.getByRole('radio', { name: 'Trades' });
        await tradesTab.click();
        await page.waitForTimeout(1000);
        
        console.log('Testing Liquidations tab...');
        const liquidationsTab = page.getByRole('radio', { name: 'Liquidations' });
        await liquidationsTab.click();
        await page.waitForTimeout(1000);
      }
      
    } catch (error) {
      console.error('Error during test:', error);
    }
    
    // Take a screenshot
    await page.screenshot({ path: 'debug-tabs-screenshot.png', fullPage: true });
    
    // Print all console errors
    console.log('\n=== CONSOLE ERRORS ===');
    consoleErrors.forEach((err, index) => {
      console.log(`Error ${index + 1}:`, err);
    });
    
    // Fail the test if there were any console errors
    expect(consoleErrors).toHaveLength(0);
  });
});