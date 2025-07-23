/**
 * Combined Test Fixtures
 * Merges console monitoring and bot management fixtures for easy import
 */

import { mergeTests } from '@playwright/test';
import { test as consoleTest } from './console-monitor.js';
import { test as botTest } from './bot-fixture.js';

// Merge all fixtures into one test object
export const test = mergeTests(consoleTest, botTest);
export { expect } from '@playwright/test';