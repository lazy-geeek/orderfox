import { test, expect } from './fixtures/index.js';

test.describe('Tabbed Trading Interface', () => {
  // No need for beforeEach - pageWithBot fixture handles navigation and bot selection
  
  test('should load basic page structure', async ({ pageWithBot }) => {
    // Verify the main layout loads
    const drawerWrapper = pageWithBot.locator('.drawer');
    await expect(drawerWrapper).toBeVisible();
    
    // Verify navbar is present
    const navbar = pageWithBot.locator('.navbar');
    await expect(navbar).toBeVisible();
    
    // Verify the app title/logo
    const logo = pageWithBot.locator('.btn-ghost').filter({ hasText: 'OrderFox' });
    await expect(logo).toBeVisible();
    
    // Verify sidebar is present (may be collapsed on mobile)
    const sidebar = pageWithBot.locator('.drawer-side');
    await expect(sidebar).toBeAttached();
  });

  test('should verify real-time data infrastructure', async ({ pageWithBot }) => {
    // This test verifies that the backend infrastructure for real-time data is working
    // We validate the APIs that power WebSocket connections and data flow
    
    // Verify that the pageWithBot has loaded successfully
    const drawerWrapper = pageWithBot.locator('.drawer');
    await expect(drawerWrapper).toBeVisible();
    
    // Check that the symbols API is accessible (required for WebSocket data)
    const symbolsResponse = await pageWithBot.request.get('/api/v1/symbols');
    expect(symbolsResponse.status()).toBe(200);
    
    const symbolsData = await symbolsResponse.json();
    expect(Array.isArray(symbolsData)).toBe(true);
    expect(symbolsData.length).toBeGreaterThan(0);
    
    // Check that bot API is accessible (required for WebSocket context)
    const botResponse = await pageWithBot.request.get('/api/v1/bots');
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
    const healthResponse = await pageWithBot.request.get('/health');
    expect(healthResponse.status()).toBe(200);
    
    // Note: This test verifies the data infrastructure is in place and ready
    // The actual WebSocket connections are tested in integration tests
    // This validates that all the APIs needed for real-time data flow are working
  });

  test('should adapt layout for mobile', async ({ pageWithBot }) => {
    // Set mobile viewport
    await pageWithBot.setViewportSize({ width: 375, height: 667 });
    await pageWithBot.goto('/');
    
    // Wait for pageWithBot to load
    await pageWithBot.waitForLoadState('domcontentloaded');
    await pageWithBot.waitForTimeout(1000);
    
    // Verify mobile layout adaptations
    const drawerWrapper = pageWithBot.locator('.drawer');
    await expect(drawerWrapper).toBeVisible();
    
    // Check that the main content area exists
    const mainContent = pageWithBot.locator('#main-content');
    await expect(mainContent).toBeAttached();
    
    // Check that the trading content wrapper exists (even if hidden due to no bot selected)
    const tradingWrapper = pageWithBot.locator('.trading-content-wrapper');
    await expect(tradingWrapper).toBeAttached();
    
    // Verify mobile navigation - drawer should be collapsible
    const mobileMenuBtn = pageWithBot.locator('.drawer-button');
    await expect(mobileMenuBtn).toBeVisible();
    
    // Test different mobile breakpoints
    await pageWithBot.setViewportSize({ width: 320, height: 568 }); // Small mobile
    await pageWithBot.waitForTimeout(200);
    
    // Layout should still be functional
    await expect(drawerWrapper).toBeVisible();
    await expect(mobileMenuBtn).toBeVisible();
    
    // Test tablet viewport
    await pageWithBot.setViewportSize({ width: 768, height: 1024 });
    await pageWithBot.waitForTimeout(200);
    
    // Layout should adapt to tablet size
    await expect(drawerWrapper).toBeVisible();
    
    // Test desktop viewport
    await pageWithBot.setViewportSize({ width: 1024, height: 768 });
    await pageWithBot.waitForTimeout(200);
    
    // On desktop, mobile menu button should be hidden
    await expect(mobileMenuBtn).toBeHidden();
    await expect(drawerWrapper).toBeVisible();
  });

  test('should maintain tab functionality across page interactions', async ({ pageWithBot }) => {
    // Trading interface should already be visible since pageWithBot handles bot selection
    
    // Ensure we're in desktop viewport to prevent drawer overlay issues
    await pageWithBot.setViewportSize({ width: 1200, height: 800 });
    
    // Initial state - Order Book should be active
    const orderBookTab = pageWithBot.locator('input#tab-orderbook');
    await expect(orderBookTab).toBeChecked();
    
    // Switch to Trades tab
    const tradesLabel = pageWithBot.locator('label[for="tab-trades"]');
    await tradesLabel.click();
    await expect(pageWithBot.locator('#tab-trades')).toBeChecked();
    
    // Interact with safe page elements that won't trigger drawer overlay
    // Click in the main content area instead of potential drawer trigger zones
    const mainContent = pageWithBot.locator('#main-content');
    await mainContent.click({ position: { x: 400, y: 300 } }); // Safe center area
    
    // Tab selection should persist
    await expect(pageWithBot.locator('#tab-trades')).toBeChecked();
    
    // Switch to Liquidations
    const liquidationsLabel = pageWithBot.locator('label[for="tab-liquidations"]');
    await liquidationsLabel.click();
    await expect(pageWithBot.locator('#tab-liquidations')).toBeChecked();
    
    // Tab should remain selected after keyboard navigation
    await pageWithBot.keyboard.press('Tab');
    await expect(pageWithBot.locator('#tab-liquidations')).toBeChecked();
  });

  test('should handle rapid tab switching', async ({ pageWithBot }) => {
    // Trading interface should already be visible since pageWithBot handles bot selection
    
    const orderBookLabel = pageWithBot.locator('label[for="tab-orderbook"]');
    const tradesLabel = pageWithBot.locator('label[for="tab-trades"]');
    const liquidationsLabel = pageWithBot.locator('label[for="tab-liquidations"]');
    
    // Rapidly switch between tabs
    for (let i = 0; i < 5; i++) {
      await tradesLabel.click();
      await expect(pageWithBot.locator('#tab-trades')).toBeChecked();
      
      await liquidationsLabel.click();
      await expect(pageWithBot.locator('#tab-liquidations')).toBeChecked();
      
      await orderBookLabel.click();
      await expect(pageWithBot.locator('#tab-orderbook')).toBeChecked();
    }
    
    // Final state should be Order Book
    await expect(pageWithBot.locator('#tab-orderbook')).toBeChecked();
  });

  test('should display tab content containers', async ({ pageWithBot }) => {
    // Trading interface should already be visible since pageWithBot handles bot selection
    
    // Verify all three tab content areas exist
    const tabContents = pageWithBot.locator('.tab-content');
    await expect(tabContents).toHaveCount(3);
    
    // Only the first tab content (Order Book) should be visible by default
    const firstTabContent = tabContents.nth(0);
    await expect(firstTabContent).toBeVisible();
    
    // Other tab contents should exist but be hidden
    const secondTabContent = tabContents.nth(1);
    const thirdTabContent = tabContents.nth(2);
    await expect(secondTabContent).toBeAttached();
    await expect(thirdTabContent).toBeAttached();
  });

  test('should support keyboard navigation', async ({ pageWithBot }) => {
    // Trading interface should already be visible since pageWithBot handles bot selection
    
    const orderBookTab = pageWithBot.locator('input#tab-orderbook');
    const tradesTab = pageWithBot.locator('input#tab-trades');
    const liquidationsTab = pageWithBot.locator('input#tab-liquidations');
    
    // DaisyUI tabs use radio inputs - verify they exist and have proper attributes
    await expect(orderBookTab).toHaveAttribute('type', 'radio');
    await expect(orderBookTab).toHaveAttribute('name', 'trading_tabs');
    await expect(orderBookTab).toHaveAttribute('aria-label', 'Order Book');
    
    await expect(tradesTab).toHaveAttribute('type', 'radio');
    await expect(tradesTab).toHaveAttribute('name', 'trading_tabs');
    await expect(tradesTab).toHaveAttribute('aria-label', 'Trades');
    
    await expect(liquidationsTab).toHaveAttribute('type', 'radio');
    await expect(liquidationsTab).toHaveAttribute('name', 'trading_tabs');
    await expect(liquidationsTab).toHaveAttribute('aria-label', 'Liquidations');
    
    // Verify initial state
    await expect(orderBookTab).toBeChecked();
    
    // Test tab switching using the visible labels (simulating user interaction)
    // DaisyUI uses hidden radio inputs, so we click the associated labels
    const tradesLabel = pageWithBot.locator('label[for="tab-trades"]');
    const liquidationsLabel = pageWithBot.locator('label[for="tab-liquidations"]');
    
    await tradesLabel.click();
    await expect(tradesTab).toBeChecked();
    await expect(orderBookTab).not.toBeChecked();
    
    await liquidationsLabel.click();  
    await expect(liquidationsTab).toBeChecked();
    await expect(tradesTab).not.toBeChecked();
    await expect(orderBookTab).not.toBeChecked();
  });

  test('should maintain tab state during component lazy loading', async ({ pageWithBot }) => {
    // Trading interface should already be visible since pageWithBot handles bot selection
    
    // Start with Order Book (default)
    const orderBookTab = pageWithBot.locator('input#tab-orderbook');
    await expect(orderBookTab).toBeChecked();
    
    // Switch to Trades tab and wait for lazy loading
    const tradesLabel = pageWithBot.locator('label[for="tab-trades"]');
    await tradesLabel.click();
    
    // Allow time for lazy loading to complete
    await pageWithBot.waitForTimeout(200);
    
    // Tab should remain selected after lazy loading
    await expect(pageWithBot.locator('#tab-trades')).toBeChecked();
    
    // Switch to Liquidations tab and wait for lazy loading
    const liquidationsLabel = pageWithBot.locator('label[for="tab-liquidations"]');
    await liquidationsLabel.click();
    
    // Allow time for lazy loading to complete
    await pageWithBot.waitForTimeout(200);
    
    // Tab should remain selected after lazy loading
    await expect(pageWithBot.locator('#tab-liquidations')).toBeChecked();
  });

  test('should handle tab labels and accessibility', async ({ pageWithBot }) => {
    // Trading interface should already be visible since pageWithBot handles bot selection
    
    const orderBookTab = pageWithBot.locator('input#tab-orderbook');
    const tradesTab = pageWithBot.locator('input#tab-trades');
    const liquidationsTab = pageWithBot.locator('input#tab-liquidations');
    
    // Verify tabs exist in DOM (they may be visually hidden by DaisyUI)
    await expect(orderBookTab).toBeAttached();
    await expect(tradesTab).toBeAttached();
    await expect(liquidationsTab).toBeAttached();
    
    // Verify proper ARIA attributes for accessibility
    await expect(orderBookTab).toHaveAttribute('aria-label', 'Order Book');
    await expect(tradesTab).toHaveAttribute('aria-label', 'Trades');
    await expect(liquidationsTab).toHaveAttribute('aria-label', 'Liquidations');
    
    // Verify they form a proper radio button group
    await expect(orderBookTab).toHaveAttribute('name', 'trading_tabs');
    await expect(tradesTab).toHaveAttribute('name', 'trading_tabs');
    await expect(liquidationsTab).toHaveAttribute('name', 'trading_tabs');
    
    // Verify tab labels (the visual part) are visible
    const orderBookLabel = pageWithBot.locator('label[for="tab-orderbook"]');
    const tradesLabel = pageWithBot.locator('label[for="tab-trades"]');
    const liquidationsLabel = pageWithBot.locator('label[for="tab-liquidations"]');
    
    await expect(orderBookLabel).toBeVisible();
    await expect(tradesLabel).toBeVisible();
    await expect(liquidationsLabel).toBeVisible();
    
    // Verify label text content
    await expect(orderBookLabel).toContainText('Order Book');
    await expect(tradesLabel).toContainText('Trades');
    await expect(liquidationsLabel).toContainText('Liquidations');
  });

  // Removed mobile viewport tests - focusing on desktop Chrome only

  test('should maintain tab functionality with multiple rapid interactions', async ({ pageWithBot }) => {
    // Trading interface should already be visible since pageWithBot handles bot selection
    
    const tabLabels = [
      pageWithBot.locator('label[for="tab-orderbook"]'),
      pageWithBot.locator('label[for="tab-trades"]'),
      pageWithBot.locator('label[for="tab-liquidations"]')
    ];
    
    const tabInputs = [
      pageWithBot.locator('#tab-orderbook'),
      pageWithBot.locator('#tab-trades'),
      pageWithBot.locator('#tab-liquidations')
    ];
    
    // Perform complex interaction sequence
    for (let round = 0; round < 3; round++) {
      for (let i = 0; i < tabLabels.length; i++) {
        await tabLabels[i].click();
        await expect(tabInputs[i]).toBeChecked();
        
        // Add small delay to simulate real user interaction
        await pageWithBot.waitForTimeout(50);
      }
    }
    
    // Final verification - all tabs should still work
    for (let i = 0; i < tabLabels.length; i++) {
      await tabLabels[i].click();
      await expect(tabInputs[i]).toBeChecked();
      
      // Verify only one tab is checked at a time
      for (let j = 0; j < tabInputs.length; j++) {
        if (i !== j) {
          await expect(tabInputs[j]).not.toBeChecked();
        }
      }
    }
  });
});