// @ts-check
import { test } from '@playwright/test';

test.describe('Debug Console Errors', () => {
  test('should capture JavaScript console errors', async ({ page }) => {
    const consoleMessages = [];
    
    // Capture all console messages
    page.on('console', msg => {
      consoleMessages.push({
        type: msg.type(),
        text: msg.text(),
        location: msg.location()
      });
    });

    // Capture page errors
    const pageErrors = [];
    page.on('pageerror', error => {
      pageErrors.push({
        message: error.message,
        stack: error.stack
      });
    });

    // Navigate to the application
    await page.goto('/');
    
    // Wait a moment for any errors to occur
    await page.waitForTimeout(5000);

    // Log all console messages
    console.log('=== CONSOLE MESSAGES ===');
    consoleMessages.forEach((msg, index) => {
      console.log(`${index + 1}. [${msg.type.toUpperCase()}] ${msg.text}`);
      if (msg.location) {
        console.log(`   Location: ${msg.location.url}:${msg.location.lineNumber}:${msg.location.columnNumber}`);
      }
    });

    // Log all page errors
    console.log('=== PAGE ERRORS ===');
    pageErrors.forEach((error, index) => {
      console.log(`${index + 1}. ${error.message}`);
      console.log(`   Stack: ${error.stack}`);
    });

    // Take a screenshot for debugging
    await page.screenshot({ path: 'debug-screenshot.png', fullPage: true });

    // The test should fail if there are critical errors
    const criticalErrors = [
      ...consoleMessages.filter(msg => msg.type === 'error'),
      ...pageErrors
    ];

    if (criticalErrors.length > 0) {
      console.log(`Found ${criticalErrors.length} critical error(s)`);
      // Don't fail the test, we want to see the errors
    }
  });
});