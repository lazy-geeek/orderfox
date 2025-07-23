/**
 * Console Monitor Fixture
 * Automatically captures console errors, warnings, and info messages during tests
 * Outputs to JSON for LLM analysis
 */

import { test as base } from '@playwright/test';
import fs from 'fs/promises';
import path from 'path';

export const test = base.extend({
  consoleMonitor: [async ({ page }, use, testInfo) => {
    const logs = {
      errors: [],
      warnings: [],
      info: [],
      testFile: path.basename(testInfo.file),
      testTitle: testInfo.title,
      project: testInfo.project.name
    };
    
    // Capture console messages
    page.on('console', msg => {
      const entry = {
        type: msg.type(),
        text: msg.text(),
        location: msg.location(),
        timestamp: new Date().toISOString()
      };
      
      switch (msg.type()) {
        case 'error':
          logs.errors.push(entry);
          break;
        case 'warning':
          logs.warnings.push(entry);
          break;
        case 'info':
        case 'log':
          logs.info.push(entry);
          break;
      }
    });
    
    // Capture page errors (uncaught exceptions)
    page.on('pageerror', error => {
      logs.errors.push({
        type: 'pageerror',
        text: error.message,
        stack: error.stack,
        timestamp: new Date().toISOString()
      });
    });
    
    // Capture request failures
    page.on('requestfailed', request => {
      // Only log non-cancelled requests as errors
      if (request.failure() && !request.failure().errorText.includes('net::ERR_ABORTED')) {
        logs.errors.push({
          type: 'requestfailed',
          text: `Request failed: ${request.url()}`,
          error: request.failure().errorText,
          timestamp: new Date().toISOString()
        });
      }
    });
    
    await use(logs);
    
    // After test, save console logs to JSON if there are any errors/warnings
    if (logs.errors.length > 0 || logs.warnings.length > 0) {
      const outputPath = testInfo.outputPath('console-logs.json');
      await fs.writeFile(outputPath, JSON.stringify(logs, null, 2));
      
      testInfo.attachments.push({
        name: 'console-logs',
        contentType: 'application/json',
        path: outputPath
      });
      
      // Log summary to console for immediate visibility
      console.log(`\n📊 Console Monitor Summary for "${testInfo.title}":`);
      console.log(`   🔴 Errors: ${logs.errors.length}`);
      console.log(`   🟡 Warnings: ${logs.warnings.length}`);
      console.log(`   🔵 Info: ${logs.info.length}`);
      
      if (logs.errors.length > 0) {
        console.log('\n   First error:', logs.errors[0].text);
      }
    }
  }, { auto: true }] // Auto fixture - runs for every test
});

export { expect } from '@playwright/test';