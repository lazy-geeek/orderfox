import { test, expect } from '@playwright/test';

test.describe('Tabbed Trading Interface', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto('http://localhost:3000');
    
    // Wait for the page to load completely
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000); // Give extra time for dynamic content
  });

  test('should load basic page structure', async ({ page }) => {
    // Verify the main layout loads
    const drawerWrapper = page.locator('.drawer');
    await expect(drawerWrapper).toBeVisible();
    
    // Verify navbar is present
    const navbar = page.locator('.navbar');
    await expect(navbar).toBeVisible();
    
    // Verify the app title/logo
    const logo = page.locator('.btn-ghost').filter({ hasText: 'OrderFox' });
    await expect(logo).toBeVisible();
    
    // Verify sidebar is present (may be collapsed on mobile)
    const sidebar = page.locator('.drawer-side');
    await expect(sidebar).toBeAttached();
  });

  test('should verify real-time data infrastructure', async ({ page }) => {
    // This test verifies that the backend infrastructure for real-time data is working
    // We validate the APIs that power WebSocket connections and data flow
    
    // Verify that the page has loaded successfully
    const drawerWrapper = page.locator('.drawer');
    await expect(drawerWrapper).toBeVisible();
    
    // Check that the symbols API is accessible (required for WebSocket data)
    const symbolsResponse = await page.request.get('http://localhost:8000/api/v1/symbols');
    expect(symbolsResponse.status()).toBe(200);
    
    const symbolsData = await symbolsResponse.json();
    expect(Array.isArray(symbolsData)).toBe(true);
    expect(symbolsData.length).toBeGreaterThan(0);
    
    // Check that bot API is accessible (required for WebSocket context)
    const botResponse = await page.request.get('http://localhost:8000/api/v1/bots');
    expect(botResponse.status()).toBe(200);
    
    const botData = await botResponse.json();
    expect(botData).toHaveProperty('bots');
    expect(Array.isArray(botData.bots)).toBe(true);
    
    // Verify that at least one symbol has the required fields for WebSocket data
    const firstSymbol = symbolsData[0];
    expect(firstSymbol).toHaveProperty('id');
    expect(firstSymbol).toHaveProperty('uiName');
    expect(firstSymbol).toHaveProperty('volume24hFormatted');
    
    // Check that the health endpoint indicates the system is ready
    const healthResponse = await page.request.get('http://localhost:8000/health');
    expect(healthResponse.status()).toBe(200);
    
    // Note: This test verifies the data infrastructure is in place and ready
    // The actual WebSocket connections are tested in integration tests
    // This validates that all the APIs needed for real-time data flow are working
  });

  test('should adapt layout for mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('http://localhost:3000');
    
    // Wait for page to load
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);
    
    // Verify mobile layout adaptations
    const drawerWrapper = page.locator('.drawer');
    await expect(drawerWrapper).toBeVisible();
    
    // Check that the main content area exists
    const mainContent = page.locator('#main-content');
    await expect(mainContent).toBeAttached();
    
    // Check that the trading content wrapper exists (even if hidden due to no bot selected)
    const tradingWrapper = page.locator('.trading-content-wrapper');
    await expect(tradingWrapper).toBeAttached();
    
    // Verify mobile navigation - drawer should be collapsible
    const mobileMenuBtn = page.locator('.drawer-button');
    await expect(mobileMenuBtn).toBeVisible();
    
    // Test different mobile breakpoints
    await page.setViewportSize({ width: 320, height: 568 }); // Small mobile
    await page.waitForTimeout(200);
    
    // Layout should still be functional
    await expect(drawerWrapper).toBeVisible();
    await expect(mobileMenuBtn).toBeVisible();
    
    // Test tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(200);
    
    // Layout should adapt to tablet size
    await expect(drawerWrapper).toBeVisible();
    
    // Test desktop viewport
    await page.setViewportSize({ width: 1024, height: 768 });
    await page.waitForTimeout(200);
    
    // On desktop, mobile menu button should be hidden
    await expect(mobileMenuBtn).toBeHidden();
    await expect(drawerWrapper).toBeVisible();
  });

  test('should maintain tab functionality across page interactions', async ({ page }) => {
    // Ensure bot is selected to make trading interface visible
    await ensureBotIsSelected(page);
    
    // Initial state - Order Book should be active
    const orderBookTab = page.getByRole('radio', { name: 'Order Book' });
    await expect(orderBookTab).toBeChecked();
    
    // Switch to Trades tab
    const tradesTab = page.getByRole('radio', { name: 'Trades' });
    await tradesTab.click();
    await expect(tradesTab).toBeChecked();
    
    // Interact with page elements (scroll, click elsewhere, etc.)
    await page.mouse.move(100, 100);
    await page.mouse.click(100, 100);
    
    // Tab selection should persist
    await expect(tradesTab).toBeChecked();
    
    // Switch to Liquidations
    const liquidationsTab = page.getByRole('radio', { name: 'Liquidations' });
    await liquidationsTab.click();
    await expect(liquidationsTab).toBeChecked();
    
    // Tab should remain selected after other interactions
    await page.keyboard.press('Tab');
    await expect(liquidationsTab).toBeChecked();
  });

  test('should handle rapid tab switching', async ({ page }) => {
    // Ensure bot is selected to make trading interface visible
    await ensureBotIsSelected(page);
    
    const orderBookTab = page.getByRole('radio', { name: 'Order Book' });
    const tradesTab = page.getByRole('radio', { name: 'Trades' });
    const liquidationsTab = page.getByRole('radio', { name: 'Liquidations' });
    
    // Rapidly switch between tabs
    for (let i = 0; i < 5; i++) {
      await tradesTab.click();
      await expect(tradesTab).toBeChecked();
      
      await liquidationsTab.click();
      await expect(liquidationsTab).toBeChecked();
      
      await orderBookTab.click();
      await expect(orderBookTab).toBeChecked();
    }
    
    // Final state should be Order Book
    await expect(orderBookTab).toBeChecked();
  });

  test('should display tab content containers', async ({ page }) => {
    // Ensure bot is selected to make trading interface visible
    await ensureBotIsSelected(page);
    
    // Verify all three tab content areas exist
    const tabContents = page.locator('.tab-content');
    await expect(tabContents).toHaveCount(3);
    
    // Each tab content should have proper structure
    for (let i = 0; i < 3; i++) {
      const tabContent = tabContents.nth(i);
      await expect(tabContent).toBeVisible();
    }
  });

  test('should support keyboard navigation', async ({ page }) => {
    // Ensure bot is selected to make trading interface visible
    await ensureBotIsSelected(page);
    
    const orderBookTab = page.getByRole('radio', { name: 'Order Book' });
    const tradesTab = page.getByRole('radio', { name: 'Trades' });
    const liquidationsTab = page.getByRole('radio', { name: 'Liquidations' });
    
    // Focus on first tab
    await orderBookTab.focus();
    await expect(orderBookTab).toBeFocused();
    
    // Use arrow keys to navigate (if supported by browser)
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('Space');
    // Note: Tab navigation behavior may vary by browser
    
    // Direct keyboard activation should work
    await tradesTab.focus();
    await page.keyboard.press('Space');
    await expect(tradesTab).toBeChecked();
    
    await liquidationsTab.focus();
    await page.keyboard.press('Space');
    await expect(liquidationsTab).toBeChecked();
  });

  test('should maintain tab state during component lazy loading', async ({ page }) => {
    // Ensure bot is selected to make trading interface visible
    await ensureBotIsSelected(page);
    
    // Start with Order Book (default)
    const orderBookTab = page.getByRole('radio', { name: 'Order Book' });
    await expect(orderBookTab).toBeChecked();
    
    // Switch to Trades tab and wait for lazy loading
    const tradesTab = page.getByRole('radio', { name: 'Trades' });
    await tradesTab.click();
    
    // Allow time for lazy loading to complete
    await page.waitForTimeout(200);
    
    // Tab should remain selected after lazy loading
    await expect(tradesTab).toBeChecked();
    
    // Switch to Liquidations tab and wait for lazy loading
    const liquidationsTab = page.getByRole('radio', { name: 'Liquidations' });
    await liquidationsTab.click();
    
    // Allow time for lazy loading to complete
    await page.waitForTimeout(200);
    
    // Tab should remain selected after lazy loading
    await expect(liquidationsTab).toBeChecked();
  });

  test('should handle tab labels and accessibility', async ({ page }) => {
    // Ensure bot is selected to make trading interface visible
    await ensureBotIsSelected(page);
    
    // Verify ARIA labels are present
    const orderBookTab = page.getByRole('radio', { name: 'Order Book' });
    const tradesTab = page.getByRole('radio', { name: 'Trades' });
    const liquidationsTab = page.getByRole('radio', { name: 'Liquidations' });
    
    // All tabs should be visible and have proper labels
    await expect(orderBookTab).toBeVisible();
    await expect(tradesTab).toBeVisible();
    await expect(liquidationsTab).toBeVisible();
    
    // Verify aria-label attributes
    await expect(orderBookTab).toHaveAttribute('aria-label', 'Order Book');
    await expect(tradesTab).toHaveAttribute('aria-label', 'Trades');
    await expect(liquidationsTab).toHaveAttribute('aria-label', 'Liquidations');
    
    // Verify radio button grouping
    await expect(orderBookTab).toHaveAttribute('name', 'trading_tabs');
    await expect(tradesTab).toHaveAttribute('name', 'trading_tabs');
    await expect(liquidationsTab).toHaveAttribute('name', 'trading_tabs');
  });

  test('should work with mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Ensure bot is selected to make trading interface visible
    await ensureBotIsSelected(page);
    
    // Tabs should still be functional on mobile
    const orderBookTab = page.getByRole('radio', { name: 'Order Book' });
    const tradesTab = page.getByRole('radio', { name: 'Trades' });
    const liquidationsTab = page.getByRole('radio', { name: 'Liquidations' });
    
    // Default state
    await expect(orderBookTab).toBeChecked();
    
    // Tab switching should work on mobile
    await tradesTab.click();
    await expect(tradesTab).toBeChecked();
    
    await liquidationsTab.click();
    await expect(liquidationsTab).toBeChecked();
    
    await orderBookTab.click();
    await expect(orderBookTab).toBeChecked();
  });

  test('should handle tab persistence during page resize', async ({ page }) => {
    // Start with desktop viewport
    await page.setViewportSize({ width: 1024, height: 768 });
    
    // Ensure bot is selected to make trading interface visible
    await ensureBotIsSelected(page);
    
    // Switch to Trades tab
    const tradesTab = page.getByRole('radio', { name: 'Trades' });
    await tradesTab.click();
    await expect(tradesTab).toBeChecked();
    
    // Resize to tablet
    await page.setViewportSize({ width: 768, height: 1024 });
    
    // Tab selection should persist
    await expect(tradesTab).toBeChecked();
    
    // Resize to mobile
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Tab selection should still persist
    await expect(tradesTab).toBeChecked();
    
    // Tab should still be functional after resize
    const liquidationsTab = page.getByRole('radio', { name: 'Liquidations' });
    await liquidationsTab.click();
    await expect(liquidationsTab).toBeChecked();
  });

  test('should maintain tab functionality with multiple rapid interactions', async ({ page }) => {
    // Ensure bot is selected to make trading interface visible
    await ensureBotIsSelected(page);
    
    const tabs = [
      page.getByRole('radio', { name: 'Order Book' }),
      page.getByRole('radio', { name: 'Trades' }),
      page.getByRole('radio', { name: 'Liquidations' })
    ];
    
    // Perform complex interaction sequence
    for (let round = 0; round < 3; round++) {
      for (let i = 0; i < tabs.length; i++) {
        await tabs[i].click();
        await expect(tabs[i]).toBeChecked();
        
        // Add small delay to simulate real user interaction
        await page.waitForTimeout(50);
      }
    }
    
    // Final verification - all tabs should still work
    for (let i = 0; i < tabs.length; i++) {
      await tabs[i].click();
      await expect(tabs[i]).toBeChecked();
      
      // Verify only one tab is checked at a time
      for (let j = 0; j < tabs.length; j++) {
        if (i !== j) {
          await expect(tabs[j]).not.toBeChecked();
        }
      }
    }
  });
});

/**
 * Helper function to ensure a bot is selected for trading interface visibility
 */
async function ensureBotIsSelected(page) {
  // Check if trading interface is already visible
  const tradingInterface = page.locator('[data-testid="trading-interface"]');
  const isVisible = await tradingInterface.isVisible();
  
  if (!isVisible) {
    // Navigate to My Bots first 
    const myBotsLink = page.locator('text=🤖 My Bots');
    await myBotsLink.click();
    
    // Wait for bot list to load
    await page.waitForSelector('[data-testid="bot-list"]', { timeout: 10000 });
    
    // Check if there are any bots
    const botCards = page.locator('[data-testid="bot-card"]');
    const count = await botCards.count();
    
    if (count > 0) {
      // Click on the Select button for the first bot
      const firstBot = botCards.first();
      const selectButton = firstBot.locator('.select-bot-btn');
      await selectButton.click();
      
      // Wait for bot selection to process
      await page.waitForTimeout(1000);
    } else {
      // Create a bot if none exist
      await page.click('[data-testid="new-bot-button"]');
      await page.waitForSelector('[data-testid="bot-editor-modal"]', { timeout: 3000 });
      
      await page.fill('[data-testid="bot-name-input"]', 'Test Trading Bot');
      await page.selectOption('[data-testid="bot-symbol-select"]', 'BTCUSDT');
      await page.click('[data-testid="save-bot-button"]');
      
      // Wait for modal to close
      await page.waitForSelector('[data-testid="bot-editor-modal"]', { state: 'hidden', timeout: 3000 });
      
      // Select the newly created bot
      const newBot = page.locator('[data-testid="bot-card"]').filter({ hasText: 'Test Trading Bot' });
      const selectButton = newBot.locator('.select-bot-btn');
      await selectButton.click();
      
      // Wait for bot selection to process
      await page.waitForTimeout(1000);
    }
    
    // Wait for trading interface to become visible
    await page.waitForSelector('[data-testid="trading-interface"]', { timeout: 10000 });
  }
}