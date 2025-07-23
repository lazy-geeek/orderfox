#!/usr/bin/env node

/**
 * Playwright Test Results Analyzer
 * Parses JSON test results and provides actionable insights for Claude Code
 */

import fs from 'fs/promises';
import path from 'path';

async function analyzeTestResults() {
  const resultsPath = 'test-results/playwright-results.json';
  
  try {
    // Read the test results
    const resultsJson = await fs.readFile(resultsPath, 'utf-8');
    const results = JSON.parse(resultsJson);
    
    const analysis = {
      timestamp: new Date().toISOString(),
      summary: {
        total: 0,
        passed: 0,
        failed: 0,
        flaky: 0,
        skipped: 0,
        duration: 0
      },
      consoleErrors: [],
      failurePatterns: [],
      slowTests: [],
      failedTestsWithScreenshots: [],
      projectSummary: {},
      recommendations: []
    };
    
    // Process each suite
    if (results.suites) {
      results.suites.forEach(suite => {
        processSuite(suite, analysis);
      });
    }
    
    // Calculate total duration
    analysis.summary.duration = Math.round(analysis.summary.duration / 1000); // Convert to seconds
    
    // Generate recommendations
    generateRecommendations(analysis);
    
    // Output analysis
    console.log(JSON.stringify(analysis, null, 2));
    
    // Also save to file
    await fs.writeFile('test-analysis.json', JSON.stringify(analysis, null, 2));
    
  } catch (error) {
    console.error(JSON.stringify({
      error: 'Failed to analyze test results',
      message: error.message,
      resultsPath
    }, null, 2));
    process.exit(1);
  }
}

function processSuite(suite, analysis) {
  if (suite.suites) {
    suite.suites.forEach(s => processSuite(s, analysis));
  }
  
  if (suite.specs) {
    suite.specs.forEach(spec => {
      spec.tests?.forEach(test => {
        processTest(test, spec, suite, analysis);
      });
    });
  }
}

function processTest(test, spec, suite, analysis) {
  // Update summary
  analysis.summary.total++;
  analysis.summary[test.status]++;
  analysis.summary.duration += test.duration || 0;
  
  // Track by project
  const projectName = test.projectName || 'default';
  if (!analysis.projectSummary[projectName]) {
    analysis.projectSummary[projectName] = {
      total: 0,
      passed: 0,
      failed: 0,
      duration: 0
    };
  }
  analysis.projectSummary[projectName].total++;
  analysis.projectSummary[projectName][test.status]++;
  analysis.projectSummary[projectName].duration += test.duration || 0;
  
  // Check for slow tests (> 10 seconds)
  if (test.duration > 10000) {
    analysis.slowTests.push({
      title: test.title,
      duration: Math.round(test.duration / 1000),
      file: path.basename(spec.file || suite.file || 'unknown'),
      project: projectName
    });
  }
  
  // Process failed tests
  if (test.status === 'failed') {
    const failure = {
      title: test.title,
      file: path.basename(spec.file || suite.file || 'unknown'),
      project: projectName,
      error: test.error?.message || 'Unknown error',
      retries: test.retry || 0
    };
    
    // Categorize failure patterns
    categorizeFailure(failure, analysis);
  }
  
  // Process attachments
  test.attachments?.forEach(attachment => {
    if (attachment.name === 'console-logs') {
      processConsoleLog(attachment, test, spec, suite, analysis);
    } else if (attachment.name === 'screenshot' && test.status === 'failed') {
      analysis.failedTestsWithScreenshots.push({
        title: test.title,
        file: path.basename(spec.file || suite.file || 'unknown'),
        screenshotPath: attachment.path,
        project: projectName
      });
    }
  });
}

async function processConsoleLog(attachment, test, spec, suite, analysis) {
  try {
    const logsJson = await fs.readFile(attachment.path, 'utf-8');
    const logs = JSON.parse(logsJson);
    
    if (logs.errors.length > 0 || logs.warnings.length > 0) {
      analysis.consoleErrors.push({
        test: test.title,
        file: path.basename(spec.file || suite.file || 'unknown'),
        errors: logs.errors.length,
        warnings: logs.warnings.length,
        firstError: logs.errors[0]?.text || null,
        project: test.projectName || 'default'
      });
    }
  } catch (error) {
    // Log attachment might not exist
  }
}

function categorizeFailure(failure, analysis) {
  const error = failure.error.toLowerCase();
  
  let category = 'Other';
  if (error.includes('timeout')) {
    category = 'Timeout';
  } else if (error.includes('element not found') || error.includes('no element matching')) {
    category = 'Element Not Found';
  } else if (error.includes('network') || error.includes('request')) {
    category = 'Network Error';
  } else if (error.includes('expected') && error.includes('received')) {
    category = 'Assertion Failed';
  }
  
  let pattern = analysis.failurePatterns.find(p => p.category === category);
  if (!pattern) {
    pattern = { category, count: 0, tests: [] };
    analysis.failurePatterns.push(pattern);
  }
  
  pattern.count++;
  pattern.tests.push({
    title: failure.title,
    file: failure.file,
    project: failure.project
  });
}

function generateRecommendations(analysis) {
  // Project execution order
  if (Object.keys(analysis.projectSummary).length > 1) {
    const projectOrder = Object.keys(analysis.projectSummary);
    analysis.recommendations.push({
      type: 'info',
      message: `Tests executed in project order: ${projectOrder.join(' → ')}`
    });
  }
  
  // Console errors
  if (analysis.consoleErrors.length > 0) {
    analysis.recommendations.push({
      type: 'critical',
      message: `Fix console errors in ${analysis.consoleErrors.length} tests`,
      details: analysis.consoleErrors.map(e => `${e.test}: ${e.errors} errors, ${e.warnings} warnings`)
    });
  }
  
  // Slow tests
  if (analysis.slowTests.length > 0) {
    analysis.recommendations.push({
      type: 'performance',
      message: `Optimize ${analysis.slowTests.length} slow tests (>10s)`,
      details: analysis.slowTests.map(t => `${t.title}: ${t.duration}s`)
    });
  }
  
  // Failure patterns
  if (analysis.failurePatterns.length > 0) {
    const mostCommon = analysis.failurePatterns.sort((a, b) => b.count - a.count)[0];
    analysis.recommendations.push({
      type: 'reliability',
      message: `Most common failure: ${mostCommon.category} (${mostCommon.count} tests)`,
      details: mostCommon.tests.map(t => t.title)
    });
  }
  
  // Screenshots
  if (analysis.failedTestsWithScreenshots.length > 0) {
    analysis.recommendations.push({
      type: 'debug',
      message: `Review ${analysis.failedTestsWithScreenshots.length} screenshots for visual debugging`,
      screenshots: analysis.failedTestsWithScreenshots.map(t => ({
        test: t.title,
        path: t.screenshotPath
      }))
    });
  }
  
  // Success rate
  const successRate = (analysis.summary.passed / analysis.summary.total * 100).toFixed(1);
  if (successRate < 95) {
    analysis.recommendations.push({
      type: 'stability',
      message: `Test success rate is ${successRate}% - aim for >95%`
    });
  }
  
  // Bot selection verification
  const tradingTests = Object.entries(analysis.projectSummary)
    .filter(([name]) => name === 'trading-features')
    .reduce((acc, [, summary]) => acc + summary.total, 0);
    
  if (tradingTests > 0) {
    analysis.recommendations.push({
      type: 'info',
      message: `${tradingTests} trading tests executed with pre-selected bot`
    });
  }
}

// Run the analyzer
analyzeTestResults();