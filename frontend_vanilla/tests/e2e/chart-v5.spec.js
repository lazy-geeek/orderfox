// @ts-check
import { test, expect } from '@playwright/test';

test.describe('Lightweight Charts v5 Integration', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto('/');
    
    // Wait for application to load
    await page.waitForLoadState('networkidle');
    
    // Click "My Bots" in the sidebar to show bot list
    const myBotsLink = page.locator('text=🤖 My Bots');
    await myBotsLink.click();
    
    // Wait for bot list to be visible
    await page.waitForSelector('[data-testid="bot-list"]', { state: 'visible', timeout: 10000 });
    
    // Select the first available bot
    await page.click('.select-bot-btn');
    
    // Wait for chart container to be visible (chart only shows after bot selection)
    await page.waitForSelector('.chart-container', { state: 'visible', timeout: 10000 });
  });

  test('should initialize chart with v5 API after bot selection', async ({ page }) => {
    // Wait for chart to be fully initialized
    await page.waitForTimeout(2000);
    
    // Check for JavaScript errors in console
    const errors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    // Verify chart container exists and has proper dimensions
    const chartContainer = await page.locator('.chart-container');
    await expect(chartContainer).toBeVisible();
    
    const boundingBox = await chartContainer.boundingBox();
    expect(boundingBox?.width).toBeGreaterThan(300);
    expect(boundingBox?.height).toBeGreaterThan(200);

    // Check that no critical errors occurred during chart initialization
    await page.waitForTimeout(3000);
    const criticalErrors = errors.filter(error => 
      error.includes('lightweight-charts') || 
      error.includes('Cannot read properties') ||
      error.includes('TypeError')
    );
    
    if (criticalErrors.length > 0) {
      console.log('Critical errors found:', criticalErrors);
    }
    expect(criticalErrors.length).toBe(0);
  });

  test('should handle symbol switching with v5 chart', async ({ page }) => {
    // Wait for initial chart load
    await page.waitForTimeout(2000);
    
    // Get the symbol selector (assuming it exists)
    const symbolSelector = await page.locator('[data-testid="symbol-selector"]');
    if (await symbolSelector.count() > 0) {
      // Select a different symbol if selector exists
      await symbolSelector.selectOption('ETHUSDT');
      
      // Wait for chart to update
      await page.waitForTimeout(2000);
      
      // Verify chart is still visible and functional
      const chartContainer = await page.locator('.chart-container');
      await expect(chartContainer).toBeVisible();
    }
  });

  test('should handle timeframe switching with v5 chart', async ({ page }) => {
    // Wait for initial chart load
    await page.waitForTimeout(2000);
    
    // Look for timeframe buttons (use exact text match)
    const timeframe5m = await page.locator('button:has-text("5m"):not(:has-text("15m"))');
    if (await timeframe5m.count() > 0) {
      await timeframe5m.click();
      
      // Wait for chart to update
      await page.waitForTimeout(2000);
      
      // Verify chart is still functional
      const chartContainer = await page.locator('.chart-container');
      await expect(chartContainer).toBeVisible();
    }
  });

  test('should handle theme switching with v5 chart', async ({ page }) => {
    // Wait for initial chart load
    await page.waitForTimeout(2000);
    
    // Look for theme toggle button
    const themeToggle = await page.locator('[data-testid="theme-toggle"]');
    if (await themeToggle.count() > 0) {
      await themeToggle.click();
      
      // Wait for theme change
      await page.waitForTimeout(1000);
      
      // Verify chart is still visible after theme change
      const chartContainer = await page.locator('.chart-container');
      await expect(chartContainer).toBeVisible();
    }
  });

  test('should handle liquidation volume toggle with v5 chart', async ({ page }) => {
    // Wait for initial chart load
    await page.waitForTimeout(2000);
    
    // Look for volume toggle button
    const volumeToggle = await page.locator('button:has-text("Volume")');
    if (await volumeToggle.count() > 0) {
      // Toggle volume display
      await volumeToggle.click();
      await page.waitForTimeout(1000);
      
      // Toggle it back
      await volumeToggle.click();
      await page.waitForTimeout(1000);
      
      // Verify chart is still functional
      const chartContainer = await page.locator('.chart-container');
      await expect(chartContainer).toBeVisible();
    }
  });

  test('should not have JavaScript errors with v5 API', async ({ page }) => {
    // Collect console errors
    const errors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    // Wait for chart to fully initialize
    await page.waitForTimeout(5000);

    // Filter out non-critical errors
    const criticalErrors = errors.filter(error => 
      error.includes('lightweight-charts') || 
      error.includes('addCandlestickSeries') ||
      error.includes('addHistogramSeries') ||
      error.includes('ColorType') ||
      error.includes('TypeError') ||
      error.includes('Cannot read properties')
    );

    // Log all errors for debugging
    if (errors.length > 0) {
      console.log('All console errors:', errors);
    }

    // Should have no critical chart-related errors
    expect(criticalErrors.length).toBe(0);
  });

  test('should display symbol overlay in chart after bot selection', async ({ page }) => {
    // Test is already set up with bot selection in beforeEach
    
    // Wait for symbol overlay to be visible
    const symbolOverlay = page.locator('[data-testid="chart-symbol-overlay"]');
    await expect(symbolOverlay).toBeVisible({ timeout: 5000 });
    
    // Verify the overlay contains a symbol (e.g., BTCUSDT, ETHUSDT, etc.)
    const symbolText = await symbolOverlay.textContent();
    expect(symbolText).toMatch(/^[A-Z]+USDT$/); // Matches patterns like BTCUSDT, ETHUSDT
  });

  test('should update symbol overlay when switching between bots', async ({ page }) => {
    // Get initial symbol
    const symbolOverlay = page.locator('[data-testid="chart-symbol-overlay"]');
    await expect(symbolOverlay).toBeVisible({ timeout: 5000 });
    
    // Navigate back to bot list
    await page.click('text=🤖 My Bots');
    await page.waitForSelector('[data-testid="bot-list"]', { state: 'visible' });
    
    // Select a different bot (if available)
    const selectButtons = page.locator('.select-bot-btn');
    const buttonCount = await selectButtons.count();
    
    if (buttonCount > 1) {
      // Click the second bot
      await selectButtons.nth(1).click();
      
      // Wait for chart to update
      await page.waitForTimeout(2000);
      
      // Verify overlay is still visible with valid symbol
      await expect(symbolOverlay).toBeVisible({ timeout: 5000 });
      const newSymbol = await symbolOverlay.textContent();
      // Note: Symbol might be the same if both bots trade the same symbol, so we just check visibility
      expect(newSymbol).toMatch(/^[A-Z]+USDT$/);
    }
  });

  test('should maintain overlay visibility when switching themes', async ({ page }) => {
    const symbolOverlay = page.locator('[data-testid="chart-symbol-overlay"]');
    
    // Verify overlay is visible in initial theme
    await expect(symbolOverlay).toBeVisible({ timeout: 5000 });
    const initialSymbol = await symbolOverlay.textContent();
    
    // Switch theme
    const themeSwitcher = page.locator('[data-testid="theme-switcher"]');
    if (await themeSwitcher.count() > 0) {
      await themeSwitcher.click();
      
      // Wait for theme transition
      await page.waitForTimeout(500);
      
      // Verify overlay is still visible with same symbol
      await expect(symbolOverlay).toBeVisible();
      const symbolAfterThemeSwitch = await symbolOverlay.textContent();
      expect(symbolAfterThemeSwitch).toBe(initialSymbol);
    }
  });

  test('should not interfere with chart interactions', async ({ page }) => {
    // Verify overlay is visible
    const symbolOverlay = page.locator('[data-testid="chart-symbol-overlay"]');
    await expect(symbolOverlay).toBeVisible({ timeout: 5000 });
    
    // Get overlay position
    const overlayBox = await symbolOverlay.boundingBox();
    
    if (overlayBox) {
      // Try to click through the overlay area (chart should receive the click)
      await page.mouse.click(overlayBox.x + 5, overlayBox.y + 5);
      
      // Verify no errors occurred (chart should handle the click normally)
      const consoleErrors = [];
      page.on('console', msg => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text());
        }
      });
      
      await page.waitForTimeout(1000);
      expect(consoleErrors.length).toBe(0);
    }
  });
});