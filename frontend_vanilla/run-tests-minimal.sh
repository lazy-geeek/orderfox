#!/bin/bash

# Run E2E tests with minimal console output
# Uses dot reporter for progress dots and JSON for results

echo "═══════════════════════════════════════════════════════"
echo "  Trading E2E Tests - Minimal Output"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "Configuration:"
echo "  - Timeout: 60 seconds per test"
echo "  - Reporter: dot (console) + json (file)"
echo "  - JSON output: test-results/playwright-results.json"
echo ""

# Clean up old results
rm -f test-results/playwright-results.json

# Run specific test group or all trading tests
GROUP=${1:-all}

case $GROUP in
    "setup")
        echo "Running trading-setup tests..."
        npm run test:e2e -- --project=trading-setup
        ;;
    "basic")
        echo "Running trading-basic tests..."
        npm run test:e2e -- --project=trading-basic
        ;;
    "tabs-display")
        echo "Running trading-tabs-display tests..."
        npm run test:e2e -- --project=trading-tabs-display
        ;;
    "controls")
        echo "Running trading-controls tests..."
        npm run test:e2e -- --project=trading-controls
        ;;
    "connection")
        echo "Running trading-connection tests..."
        npm run test:e2e -- --project=trading-connection
        ;;
    "errors")
        echo "Running trading-errors tests..."
        npm run test:e2e -- --project=trading-errors
        ;;
    "tabs")
        echo "Running trading-tabs tests..."
        npm run test:e2e -- --project=trading-tabs
        ;;
    "all")
        echo "Running all trading tests..."
        npm run test:e2e -- --project=trading-setup --project=trading-basic --project=trading-tabs-display --project=trading-controls --project=trading-connection --project=trading-errors --project=trading-tabs
        ;;
    "chart-v5")
        echo "Running chart-v5 tests..."
        npm run test:e2e -- --project=chart-v5
        ;;
    "complete")
        echo "Running ALL E2E tests (including independent projects)..."
        npm run test:e2e -- --project=smoke --project=bot-management --project=trading-setup --project=trading-basic --project=trading-tabs-display --project=trading-controls --project=trading-connection --project=trading-errors --project=trading-tabs --project=chart-v5
        ;;
    *)
        echo "Unknown group: $GROUP"
        echo "Usage: $0 [setup|basic|tabs-display|controls|connection|errors|tabs|all|chart-v5|complete]"
        exit 1
        ;;
esac

EXIT_CODE=$?

# Parse JSON results if available
if [ -f "test-results/playwright-results.json" ]; then
    echo ""
    echo "═══════════════════════════════════════════════════════"
    echo "  Test Results Summary"
    echo "═══════════════════════════════════════════════════════"
    
    node -e "
    try {
        const data = require('./test-results/playwright-results.json');
        if (data.stats) {
            const total = data.stats.expected || 0;
            const failed = data.stats.unexpected || 0;
            const passed = total - failed - (data.stats.skipped || 0);
            const duration = ((data.stats.duration || 0) / 1000).toFixed(1);
            
            console.log('');
            console.log('  Total tests: ' + total);
            console.log('  Passed: ' + passed);
            console.log('  Failed: ' + failed);
            console.log('  Duration: ' + duration + 's');
            
            if (failed > 0) {
                console.log('');
                process.exit(1);
            }
        }
    } catch (e) {
        console.log('  Could not parse test results');
    }
    " || true
fi

echo ""
exit $EXIT_CODE