#!/usr/bin/env node

/**
 * Comprehensive E2E Test Results Analyzer
 * Analyzes Playwright test results JSON and generates statistical summary
 */

import fs from 'fs';
import path from 'path';

const RESULTS_FILE = 'test-results/playwright-results.json';

function analyzeTestResults() {
  console.log('📊 E2E Test Results Analysis\n');
  
  if (!fs.existsSync(RESULTS_FILE)) {
    console.error(`❌ Results file not found: ${RESULTS_FILE}`);
    process.exit(1);
  }
  
  const results = JSON.parse(fs.readFileSync(RESULTS_FILE, 'utf8'));
  
  // Overall statistics
  const stats = {
    projects: {},
    totalTests: 0,
    totalPassed: 0,
    totalFailed: 0,
    totalSkipped: 0,
    totalTimedOut: 0,
    duration: results.stats?.duration || 0
  };
  
  // Analyze each test
  function processTests(suite, parentTitle = '') {
    if (suite.specs) {
      for (const spec of suite.specs) {
        if (spec.tests) {
          for (const test of spec.tests) {
            const projectName = test.projectName;
            const status = test.results?.[0]?.status || 'unknown';
            const duration = test.results?.[0]?.duration || 0;
            
            // Initialize project stats if needed
            if (!stats.projects[projectName]) {
              stats.projects[projectName] = {
                total: 0,
                passed: 0,
                failed: 0,
                skipped: 0,
                timedOut: 0,
                duration: 0,
                failedTests: []
              };
            }
            
            stats.projects[projectName].total++;
            stats.projects[projectName].duration += duration;
            stats.totalTests++;
            
            const testTitle = `${parentTitle}${spec.title} > ${test.title}`.trim();
            
            switch (status) {
              case 'passed':
              case 'expected':
                stats.projects[projectName].passed++;
                stats.totalPassed++;
                break;
              case 'failed':
              case 'unexpected':
                stats.projects[projectName].failed++;
                stats.totalFailed++;
                stats.projects[projectName].failedTests.push({
                  title: testTitle,
                  error: test.results?.[0]?.error?.message || 'Unknown error',
                  duration: duration
                });
                break;
              case 'skipped':
                stats.projects[projectName].skipped++;
                stats.totalSkipped++;
                break;
              case 'timedOut':
                stats.projects[projectName].timedOut++;
                stats.totalTimedOut++;
                stats.projects[projectName].failedTests.push({
                  title: testTitle,
                  error: 'Test timed out',
                  duration: duration
                });
                break;
            }
          }
        }
      }
    }
    
    // Process nested suites
    if (suite.suites) {
      for (const nestedSuite of suite.suites) {
        const newParentTitle = parentTitle ? `${parentTitle} > ${suite.title}` : suite.title;
        processTests(nestedSuite, newParentTitle);
      }
    }
  }
  
  // Process all test suites
  if (results.suites) {
    for (const suite of results.suites) {
      processTests(suite);
    }
  }
  
  // Generate report
  console.log('='.repeat(80));
  console.log('🎯 OVERALL SUMMARY');
  console.log('='.repeat(80));
  console.log(`Total Tests:    ${stats.totalTests}`);
  console.log(`✅ Passed:      ${stats.totalPassed} (${((stats.totalPassed/stats.totalTests)*100).toFixed(1)}%)`);
  console.log(`❌ Failed:      ${stats.totalFailed} (${((stats.totalFailed/stats.totalTests)*100).toFixed(1)}%)`);
  console.log(`⏰ Timed Out:   ${stats.totalTimedOut} (${((stats.totalTimedOut/stats.totalTests)*100).toFixed(1)}%)`);
  console.log(`⏭️  Skipped:     ${stats.totalSkipped} (${((stats.totalSkipped/stats.totalTests)*100).toFixed(1)}%)`);
  console.log(`⏱️  Duration:    ${(stats.duration/1000).toFixed(1)}s`);
  
  console.log('\n' + '='.repeat(80));
  console.log('📋 PROJECT BREAKDOWN');
  console.log('='.repeat(80));
  
  for (const [projectName, projectStats] of Object.entries(stats.projects)) {
    const successRate = ((projectStats.passed / projectStats.total) * 100).toFixed(1);
    const avgDuration = (projectStats.duration / projectStats.total / 1000).toFixed(1);
    
    console.log(`\n🎪 ${projectName.toUpperCase()} PROJECT:`);
    console.log(`   Total Tests:  ${projectStats.total}`);
    console.log(`   ✅ Passed:    ${projectStats.passed} (${successRate}%)`);
    console.log(`   ❌ Failed:    ${projectStats.failed}`);
    console.log(`   ⏰ Timed Out: ${projectStats.timedOut}`);
    console.log(`   ⏭️ Skipped:   ${projectStats.skipped}`);
    console.log(`   ⏱️ Avg Time:  ${avgDuration}s per test`);
    console.log(`   📊 Duration:  ${(projectStats.duration/1000).toFixed(1)}s total`);
    
    if (projectStats.failedTests.length > 0) {
      console.log(`   \n❌ Failed Tests (${projectStats.failedTests.length}):`);
      projectStats.failedTests.forEach((test, index) => {
        console.log(`      ${index + 1}. ${test.title}`);
        console.log(`         Error: ${test.error.split('\n')[0]}`);
        console.log(`         Duration: ${(test.duration/1000).toFixed(1)}s`);
      });
    }
  }
  
  // Summary recommendations
  console.log('\n' + '='.repeat(80));
  console.log('💡 RECOMMENDATIONS');
  console.log('='.repeat(80));
  
  const overallSuccessRate = (stats.totalPassed / stats.totalTests) * 100;
  
  if (overallSuccessRate >= 90) {
    console.log('🟢 Excellent: Test suite is in great shape!');
  } else if (overallSuccessRate >= 75) {
    console.log('🟡 Good: Test suite needs minor improvements.');
  } else if (overallSuccessRate >= 50) {
    console.log('🟠 Needs Work: Significant test failures detected.');
  } else {
    console.log('🔴 Critical: Major test suite issues need immediate attention.');
  }
  
  // Identify common failure patterns
  const allFailedTests = Object.values(stats.projects).flatMap(p => p.failedTests);
  const timeoutCount = allFailedTests.filter(t => t.error.includes('timeout') || t.error.includes('Timeout')).length;
  const websocketErrors = allFailedTests.filter(t => t.error.toLowerCase().includes('websocket')).length;
  
  if (timeoutCount > 0) {
    console.log(`⏰ ${timeoutCount} tests failed due to timeouts - consider increasing timeout values`);
  }
  
  if (websocketErrors > 0) {
    console.log(`🔌 ${websocketErrors} tests failed due to WebSocket issues - check connection handling`);
  }
  
  console.log('\n' + '='.repeat(80));
  console.log('📊 Test Results Analysis Complete');
  console.log('='.repeat(80));
}

try {
  analyzeTestResults();
} catch (error) {
  console.error('❌ Error analyzing test results:', error.message);
  process.exit(1);
}