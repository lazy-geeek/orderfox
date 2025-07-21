/**
 * Smoke Tests
 * Basic tests to ensure the application loads and core functionality works
 */

import { test, expect } from '@playwright/test';
import { selectors, waitTimes } from './fixtures/test-data.js';

test.describe('Smoke Tests', () => {
  test('should load the application', async ({ page }) => {
    // Navigate to the application
    await page.goto('/');
    
    // Wait for application to load
    await page.waitForLoadState('networkidle');
    
    // Check that the page title is correct
    await expect(page).toHaveTitle(/OrderFox/);
    
    // Check that main elements are visible
    await expect(page.locator('body')).toBeVisible();
    await expect(page.locator('#app')).toBeVisible();
    
    // Wait a bit for the app to initialize
    await page.waitForTimeout(1000);
    
    // Check that the drawer layout is created
    await expect(page.locator('.drawer')).toBeVisible();
  });

  test('should have working navigation', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Check bot navigation is visible
    await expect(page.locator(selectors.botNavigation)).toBeVisible();
    
    // Check bot list is visible
    await expect(page.locator(selectors.botList)).toBeVisible();
  });

  test('should have working modal system', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Wait for bot list to load
    await page.waitForSelector(selectors.botList, { timeout: waitTimes.long });
    
    // Click new bot button
    await page.click(selectors.newBotButton);
    
    // Check modal opens
    await page.waitForSelector(selectors.botEditorModal, { timeout: waitTimes.medium });
    await expect(page.locator(selectors.botEditorModal)).toBeVisible();
    
    // Close modal
    await page.click(selectors.cancelBotButton);
    
    // Check modal closes
    await page.waitForSelector(selectors.botEditorModal, { state: 'hidden', timeout: waitTimes.medium });
    await expect(page.locator(selectors.botEditorModal)).not.toBeVisible();
  });

  test('should handle basic API connectivity', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Wait for bot list to load (which requires API connectivity)
    await page.waitForSelector(selectors.botList, { timeout: waitTimes.long });
    
    // Check that the bot list loaded without errors
    await expect(page.locator(selectors.botList)).toBeVisible();
    
    // Check that there are no critical error messages
    const errorAlerts = page.locator(selectors.errorAlert);
    const errorCount = await errorAlerts.count();
    
    // Should have no critical errors on initial load
    expect(errorCount).toBe(0);
  });

  test('should have responsive design', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Test desktop
    await page.setViewportSize({ width: 1200, height: 800 });
    await expect(page.locator(selectors.botNavigation)).toBeVisible();
    await expect(page.locator(selectors.botList)).toBeVisible();
    
    // Test tablet
    await page.setViewportSize({ width: 768, height: 1024 });
    await expect(page.locator(selectors.botNavigation)).toBeVisible();
    await expect(page.locator(selectors.botList)).toBeVisible();
    
    // Test mobile
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.locator(selectors.botNavigation)).toBeVisible();
    await expect(page.locator(selectors.botList)).toBeVisible();
  });

  test('should handle page refresh', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Wait for initial load
    await page.waitForSelector(selectors.botList, { timeout: waitTimes.long });
    
    // Refresh the page
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    // Check that the application still works
    await expect(page.locator(selectors.botNavigation)).toBeVisible();
    await expect(page.locator(selectors.botList)).toBeVisible();
  });

  test('should have proper accessibility', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Check for basic accessibility elements
    const buttons = page.locator('button');
    const buttonCount = await buttons.count();
    expect(buttonCount).toBeGreaterThan(0);
    
    // Check that buttons have proper attributes
    if (buttonCount > 0) {
      const firstButton = buttons.first();
      const hasAriaLabel = await firstButton.getAttribute('aria-label');
      const hasText = await firstButton.textContent();
      
      // Button should have either aria-label or text content
      expect(hasAriaLabel || hasText).toBeTruthy();
    }
    
    // Check for form labels
    const inputs = page.locator('input');
    const inputCount = await inputs.count();
    
    if (inputCount > 0) {
      // At least some inputs should have labels or aria-labels
      const labelsCount = await page.locator('label').count();
      const ariaLabelsCount = await page.locator('input[aria-label]').count();
      
      expect(labelsCount + ariaLabelsCount).toBeGreaterThan(0);
    }
  });

  test('should handle JavaScript errors gracefully', async ({ page }) => {
    const jsErrors = [];
    
    // Listen for JavaScript errors
    page.on('pageerror', (error) => {
      jsErrors.push(error.message);
    });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Wait for application to fully load
    await page.waitForSelector(selectors.botList, { timeout: waitTimes.long });
    
    // Interact with the application
    await page.click(selectors.newBotButton);
    await page.waitForSelector(selectors.botEditorModal, { timeout: waitTimes.medium });
    await page.click(selectors.cancelBotButton);
    
    // Check that no critical JavaScript errors occurred
    const criticalErrors = jsErrors.filter(error => 
      error.includes('ReferenceError') || 
      error.includes('TypeError') ||
      error.includes('SyntaxError')
    );
    
    expect(criticalErrors.length).toBe(0);
  });
});