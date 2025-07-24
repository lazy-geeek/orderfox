/**
 * Trading Modal Test
 * Tests specific to the modal-based trading interface functionality
 */

import { test, expect } from './fixtures/index.js';
import { selectors, waitForModalOpen, waitForModalClose } from './fixtures/test-data.js';

test.describe('Trading Modal Functionality', () => {
  test('should close modal with ESC key', async ({ selectedBot, pageWithBot }) => {
    // Modal should already be open from the fixture
    await expect(pageWithBot.locator(selectors.tradingModal)).toBeVisible();
    
    // Press ESC key to close modal
    await pageWithBot.keyboard.press('Escape');
    
    // Wait for modal to close
    await waitForModalClose(pageWithBot, selectors.tradingModal);
    
    // Verify modal is closed
    await expect(pageWithBot.locator(selectors.tradingModal)).toBeHidden();
    
    // Verify bot list is still visible
    await expect(pageWithBot.locator(selectors.botList)).toBeVisible();
    
    // ESC key closes modal successfully
  });

  test('should close modal with X button', async ({ selectedBot, pageWithBot }) => {
    // Modal should already be open from the fixture
    await expect(pageWithBot.locator(selectors.tradingModal)).toBeVisible();
    
    // Click the X close button
    await pageWithBot.click(selectors.modalCloseButton);
    
    // Wait for modal to close
    await waitForModalClose(pageWithBot, selectors.tradingModal);
    
    // Verify modal is closed
    await expect(pageWithBot.locator(selectors.tradingModal)).toBeHidden();
    
    // Verify bot list is still visible
    await expect(pageWithBot.locator(selectors.botList)).toBeVisible();
    
    // X button closes modal successfully
  });

  test('should NOT close modal with backdrop click', async ({ selectedBot, pageWithBot }) => {
    // Modal should already be open from the fixture
    await expect(pageWithBot.locator(selectors.tradingModal)).toBeVisible();
    
    // Click on the modal backdrop (dialog element itself, but not the modal-box)
    // We need to click on the modal but outside the modal-box content
    const modalBox = pageWithBot.locator(`${selectors.tradingModal} .modal-box`);
    const modalBoxBoundingBox = await modalBox.boundingBox();
    
    // Click somewhere outside the modal box but inside the modal dialog
    await pageWithBot.click(selectors.tradingModal, {
      position: { 
        x: modalBoxBoundingBox.x - 50, 
        y: modalBoxBoundingBox.y + 50 
      }
    });
    
    // Wait a moment to ensure no closing animation starts
    await pageWithBot.waitForTimeout(1000);
    
    // Verify modal is still open
    await expect(pageWithBot.locator(selectors.tradingModal)).toBeVisible();
    
    // Backdrop click does NOT close modal (as intended)
  });

  test('should verify bot list remains visible behind modal', async ({ selectedBot, pageWithBot }) => {
    // Modal should already be open from the fixture
    await expect(pageWithBot.locator(selectors.tradingModal)).toBeVisible();
    
    // Verify bot list is still visible behind the modal
    const botList = pageWithBot.locator(selectors.botList);
    await expect(botList).toBeVisible();
    
    // Verify bot cards are still accessible
    const botCards = pageWithBot.locator(selectors.botCard);
    const botCardCount = await botCards.count();
    expect(botCardCount).toBeGreaterThan(0);
    
    // Verify the selected bot info is displayed
    const selectedBotInfo = pageWithBot.locator('#selected-bot-name');
    await expect(selectedBotInfo).toBeVisible();
    await expect(selectedBotInfo).toContainText(selectedBot.name);
    
    // Bot list remains visible and functional behind modal
  });

  test('should display modal opening animations', async ({ page }) => {
    // Start on main page without modal open
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Navigate to bot management
    const myBotsLink = page.locator('text=🤖 My Bots');
    await myBotsLink.click();
    await page.waitForSelector(selectors.botList, { timeout: 5000 });
    
    // Click a bot to open modal
    const firstBotCard = page.locator(selectors.botCard).first();
    const selectButton = firstBotCard.locator(selectors.selectBotButton);
    
    // Verify modal is not visible initially
    await expect(page.locator(selectors.tradingModal)).toBeHidden();
    
    // Click to open modal
    await selectButton.click();
    
    // Wait for modal to appear with animation
    await waitForModalOpen(page, selectors.tradingModal);
    
    // Verify modal is now visible
    await expect(page.locator(selectors.tradingModal)).toBeVisible();
    
    // Verify modal content is loaded
    await expect(page.locator(selectors.tradingInterfaceContainer)).toBeVisible();
    
    // Modal opens with proper animations
  });

  test('should handle error states within modal gracefully', async ({ selectedBot, pageWithBot }) => {
    // Modal should already be open from the fixture
    await expect(pageWithBot.locator(selectors.tradingModal)).toBeVisible();
    
    // Verify modal content is present
    await expect(pageWithBot.locator(selectors.tradingInterfaceContainer)).toBeVisible();
    
    // Check for any JavaScript errors in console (basic error state test)
    const consoleErrors = [];
    pageWithBot.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    
    // Wait a moment for any initial errors to surface
    await pageWithBot.waitForTimeout(2000);
    
    // Check that there are no critical errors that would break the modal
    const criticalErrors = consoleErrors.filter(error => 
      error.includes('Cannot read') || 
      error.includes('is not a function') ||
      error.includes('Maximum call stack')
    );
    
    expect(criticalErrors.length).toBe(0);
    
    // Modal handles errors gracefully without critical failures
  });
});