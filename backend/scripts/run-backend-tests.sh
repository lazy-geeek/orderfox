#!/bin/bash

# Backend Test Suite Executor with Chunked Execution and Result Logging
#
# This script solves three critical issues:
# 1. Timeout Prevention: Runs tests in 8 logical chunks (<90 seconds each)
# 2. LLM Efficiency: Generates concise result files instead of verbose terminal output
# 3. Proactive Maintenance: Captures warnings and deprecations for code quality
#
# Features:
# - Sequential chunk execution following dependency order
# - Comprehensive result logging to files  
# - Warning and deprecation capture for LLM analysis
# - Quick status checks and failure analysis
# - Headless execution support
# - Progress tracking and historical results

set -e  # Exit on any error

# Configuration
BACKEND_DIR="/home/bail/github/orderfox/backend"
RESULTS_DIR="$BACKEND_DIR/logs/test-results"
TIMEOUT_PER_CHUNK=120  # 2 minutes max per chunk
MAX_RETRIES=1

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Chunk definitions (following logical dependency order)
declare -A CHUNKS
CHUNKS[1]="chunk1:Foundation tests - Database, config, utilities:30"
CHUNKS[2]="chunk2:Core services - Symbol, exchange, formatting, caching:45"  
CHUNKS[3]="chunk3:Business services - Bot, orderbook, chart data:60"
CHUNKS[4]="chunk4:Advanced services - Liquidation, trade, trading engine:60"
CHUNKS[5]="chunk5:REST API endpoints - Schema, bot, market data APIs:45"
CHUNKS[6]="chunk6:WebSocket API endpoints - Connection manager, market data, liquidations WS:75"
CHUNKS[7]="chunk7a:Bot Integration tests - Bot paper trading flows:45"
CHUNKS[8]="chunk7b:Data Flow Integration tests - E2E formatting, liquidation volume flows:60"
CHUNKS[9]="chunk7c:WebSocket Integration tests - Real WebSocket orderbook tests:90"
CHUNKS[10]="chunk8:Performance and load tests - Volume, load, advanced integration:90"

# Initialize result tracking
TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_ERRORS=0
TOTAL_WARNINGS=0
TOTAL_DEPRECATIONS=0
TOTAL_RUNTIME_ISSUES=0
TOTAL_PYTEST_WARNINGS=0
FAILED_CHUNKS=()
WARNING_CHUNKS=()
CHUNK_RESULTS=()

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] ✓${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ✗${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] ⚠${NC} $1"
}

setup_results_directory() {
    log "Setting up results directory: $RESULTS_DIR"
    mkdir -p "$RESULTS_DIR"
    
    # Clean previous results
    rm -f "$RESULTS_DIR"/*.txt
    
    # Initialize execution log
    echo "BACKEND TEST EXECUTION LOG" > "$RESULTS_DIR/execution-log.txt"
    echo "=========================" >> "$RESULTS_DIR/execution-log.txt"
    echo "Started: $(date)" >> "$RESULTS_DIR/execution-log.txt"
    echo "" >> "$RESULTS_DIR/execution-log.txt"
}

run_chunk() {
    local chunk_num=$1
    local chunk_info=${CHUNKS[$chunk_num]}
    
    IFS=':' read -r chunk_name description estimated_time <<< "$chunk_info"
    
    log "Running $chunk_name ($description)"
    echo "[$chunk_name] Started: $(date)" >> "$RESULTS_DIR/execution-log.txt"
    
    local summary_file="$RESULTS_DIR/$chunk_name-summary.txt"
    local failures_file="$RESULTS_DIR/$chunk_name-failures.txt"
    local warnings_file="$RESULTS_DIR/$chunk_name-warnings.txt"
    local temp_output="$RESULTS_DIR/$chunk_name-temp.txt"
    
    # Initialize summary file
    cat > "$summary_file" << EOF
$chunk_name: $description
$(echo "$description" | sed 's/./=/g')
Executed: $(date)
Status: RUNNING...

EOF

    local start_time=$(date +%s)
    local success=false
    
    # Run pytest with timeout and capture ALL warnings, runtime errors, and logging issues
    if timeout ${TIMEOUT_PER_CHUNK}s python -m pytest -m "$chunk_name" \
        --tb=short --no-header --quiet -v \
        -W default::DeprecationWarning \
        -W default::PendingDeprecationWarning \
        -W default::UserWarning \
        -W default::RuntimeWarning \
        -W default::FutureWarning \
        -W default > "$temp_output" 2>&1; then
        success=true
        log_success "$chunk_name completed successfully"
        echo "[$chunk_name] Status: PASSED" >> "$RESULTS_DIR/execution-log.txt"
    else
        local exit_code=$?
        if [ $exit_code -eq 124 ]; then
            log_error "$chunk_name timed out after ${TIMEOUT_PER_CHUNK}s"
            echo "[$chunk_name] Status: TIMEOUT" >> "$RESULTS_DIR/execution-log.txt"
        else
            log_error "$chunk_name failed with exit code $exit_code"
            echo "[$chunk_name] Status: FAILED" >> "$RESULTS_DIR/execution-log.txt"
        fi
        FAILED_CHUNKS+=("$chunk_name")
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Parse pytest output for results
    local passed_count=0
    local failed_count=0
    local error_count=0
    local warning_count=0
    local deprecation_count=0
    local runtime_issues=0
    local logging_errors=0
    local task_warnings=0
    local pytest_warnings=0
    local test_files=()
    
    if [ -f "$temp_output" ]; then
        # Count results from pytest output - ensure numeric results
        passed_count=$(grep -c "PASSED" "$temp_output" 2>/dev/null) || passed_count=0
        failed_count=$(grep -c "FAILED" "$temp_output" 2>/dev/null) || failed_count=0
        error_count=$(grep -c "ERROR" "$temp_output" 2>/dev/null) || error_count=0
        
        # Count warnings and deprecations  
        deprecation_count=$(grep -c "DeprecationWarning\|PendingDeprecationWarning" "$temp_output" 2>/dev/null) || deprecation_count=0
        warning_count=$(grep -c "UserWarning\|RuntimeWarning\|FutureWarning" "$temp_output" 2>/dev/null) || warning_count=0
        
        # Count critical runtime issues
        logging_errors=$(grep -c "--- Logging error ---" "$temp_output" 2>/dev/null) || logging_errors=0
        task_warnings=$(grep -c "Task was destroyed but it is pending" "$temp_output" 2>/dev/null) || task_warnings=0
        runtime_issues=$(grep -c "ValueError: I/O operation on closed file\|asyncio.*error\|Connection.*closed" "$temp_output" 2>/dev/null) || runtime_issues=0
        
        # Extract pytest warning summary (e.g., "2 warnings in 12.34s")
        pytest_warnings=$(grep -oE "[0-9]+ warnings in [0-9]+\.[0-9]+s" "$temp_output" | grep -oE "^[0-9]+" | head -1) || pytest_warnings=0
        
        # Ensure variables are numeric (strip any whitespace/newlines)
        passed_count=${passed_count//[^0-9]/}
        failed_count=${failed_count//[^0-9]/}
        error_count=${error_count//[^0-9]/}
        deprecation_count=${deprecation_count//[^0-9]/}
        warning_count=${warning_count//[^0-9]/}
        logging_errors=${logging_errors//[^0-9]/}
        task_warnings=${task_warnings//[^0-9]/}
        runtime_issues=${runtime_issues//[^0-9]/}
        pytest_warnings=${pytest_warnings//[^0-9]/}
        
        # Default to 0 if empty
        passed_count=${passed_count:-0}
        failed_count=${failed_count:-0}
        error_count=${error_count:-0}
        deprecation_count=${deprecation_count:-0}
        warning_count=${warning_count:-0}
        logging_errors=${logging_errors:-0}
        task_warnings=${task_warnings:-0}
        runtime_issues=${runtime_issues:-0}
        pytest_warnings=${pytest_warnings:-0}
        
        # Extract test files
        while IFS= read -r line; do
            if [[ $line =~ ^([^:]+\.py)::.* ]]; then
                local test_file="${BASH_REMATCH[1]}"
                if [[ ! " ${test_files[@]} " =~ " ${test_file} " ]]; then
                    test_files+=("$test_file")
                fi
            fi
        done < "$temp_output"
    fi
    
    # Update summary file
    local status="PASSED"
    if [ "$success" = false ]; then
        status="FAILED"
    fi
    
    cat > "$summary_file" << EOF
$chunk_name: $description
$(echo "$description" | sed 's/./=/g')
Executed: $(date)
Duration: ${duration} seconds (estimated: ${estimated_time}s)
Status: $status

Results:
- PASSED: $passed_count tests
- FAILED: $failed_count tests  
- ERRORS: $error_count tests
- DEPRECATIONS: $deprecation_count warnings
- OTHER WARNINGS: $warning_count warnings
- RUNTIME ISSUES: $((logging_errors + task_warnings + runtime_issues)) critical
  - Logging errors: $logging_errors
  - Task warnings: $task_warnings  
  - I/O errors: $runtime_issues
- PYTEST WARNINGS: $pytest_warnings total

Test Files:
EOF

    # List test files with status
    for file in "${test_files[@]}"; do
        local file_passed=$(grep -c "${file}.*PASSED" "$temp_output" 2>/dev/null) || file_passed=0
        local file_failed=$(grep -c "${file}.*FAILED" "$temp_output" 2>/dev/null) || file_failed=0
        local file_errors=$(grep -c "${file}.*ERROR" "$temp_output" 2>/dev/null) || file_errors=0
        
        # Ensure numeric values
        file_passed=${file_passed//[^0-9]/}; file_passed=${file_passed:-0}
        file_failed=${file_failed//[^0-9]/}; file_failed=${file_failed:-0}
        file_errors=${file_errors//[^0-9]/}; file_errors=${file_errors:-0}
        
        if [ "$file_failed" -eq 0 ] && [ "$file_errors" -eq 0 ]; then
            echo "✓ $file ($file_passed passed)" >> "$summary_file"
        else
            echo "✗ $file ($file_passed passed, $file_failed failed, $file_errors errors)" >> "$summary_file"
        fi
    done
    
    # Create failures file if there are failures or errors
    if [ "$failed_count" -gt 0 ] || [ "$error_count" -gt 0 ]; then
        log_warning "Creating failure details for $chunk_name"
        
        cat > "$failures_file" << EOF
$chunk_name: FAILURE DETAILS
$(echo "$chunk_name: FAILURE DETAILS" | sed 's/./=/g')

EOF
        
        # Extract failure details from temp output
        grep -A 5 -B 1 "FAILED\|ERROR" "$temp_output" >> "$failures_file" 2>/dev/null || echo "No detailed failure info available" >> "$failures_file"
        
        # Add warnings section to failures file if there are warnings
        local total_warnings=$((deprecation_count + warning_count))
        if [ "$total_warnings" -gt 0 ]; then
            echo "" >> "$failures_file"
            echo "WARNINGS IN THIS CHUNK:" >> "$failures_file"
            echo "$(echo "WARNINGS IN THIS CHUNK:" | sed 's/./=/g')" >> "$failures_file"
            grep -E "(DeprecationWarning|PendingDeprecationWarning|UserWarning|RuntimeWarning|FutureWarning)" "$temp_output" >> "$failures_file" 2>/dev/null || echo "No detailed warning info available" >> "$failures_file"
        fi
    fi
    
    # Create warnings file if there are warnings, deprecations, or runtime issues
    local total_runtime_issues=$((logging_errors + task_warnings + runtime_issues))
    if [ "$deprecation_count" -gt 0 ] || [ "$warning_count" -gt 0 ] || [ "$total_runtime_issues" -gt 0 ] || [ "$pytest_warnings" -gt 0 ]; then
        log_warning "Creating warning details for $chunk_name"
        
        cat > "$warnings_file" << EOF
$chunk_name: COMPREHENSIVE WARNING & RUNTIME ISSUE ANALYSIS
$(echo "$chunk_name: COMPREHENSIVE WARNING & RUNTIME ISSUE ANALYSIS" | sed 's/./=/g')
Generated: $(date)

SUMMARY:
- Runtime Issues: $total_runtime_issues (🔴 CRITICAL - Resource leaks & cleanup problems)
- Deprecations: $deprecation_count (🟡 HIGH - Immediate action needed)
- Other Warnings: $warning_count (🔵 MEDIUM - Code quality improvements)
- Pytest Warnings: $pytest_warnings (🟢 INFO - General test warnings)

RUNTIME ISSUES BREAKDOWN:
- Logging errors: $logging_errors (File handle issues)
- Task warnings: $task_warnings (Async cleanup problems)
- I/O errors: $runtime_issues (Connection/resource leaks)

RUNTIME ISSUES (Priority: CRITICAL):
$(echo "RUNTIME ISSUES (Priority: CRITICAL):" | sed 's/./=/g')
EOF

        # Extract runtime issues
        if [ "$total_runtime_issues" -gt 0 ]; then
            if [ "$logging_errors" -gt 0 ]; then
                echo "  🔴 LOGGING ERRORS ($logging_errors found):" >> "$warnings_file"
                grep -A 3 -B 1 "--- Logging error ---" "$temp_output" | sed 's/^/    → /' >> "$warnings_file" 2>/dev/null || echo "    No logging error details available" >> "$warnings_file"
                echo "" >> "$warnings_file"
            fi
            
            if [ "$task_warnings" -gt 0 ]; then
                echo "  🔴 TASK DESTRUCTION WARNINGS ($task_warnings found):" >> "$warnings_file"
                grep "Task was destroyed but it is pending" "$temp_output" | sed 's/^/    → /' >> "$warnings_file" 2>/dev/null || echo "    No task warning details available" >> "$warnings_file"
                echo "" >> "$warnings_file"
            fi
            
            if [ "$runtime_issues" -gt 0 ]; then
                echo "  🔴 I/O & CONNECTION ERRORS ($runtime_issues found):" >> "$warnings_file"
                grep -E "(ValueError: I/O operation on closed file|asyncio.*error|Connection.*closed)" "$temp_output" | sed 's/^/    → /' >> "$warnings_file" 2>/dev/null || echo "    No I/O error details available" >> "$warnings_file"
                echo "" >> "$warnings_file"
            fi
        else
            echo "  ✓ No runtime issues found" >> "$warnings_file"
        fi
        
        echo "" >> "$warnings_file"
        echo "DEPRECATION WARNINGS (Priority: HIGH):" >> "$warnings_file"
        echo "$(echo "DEPRECATION WARNINGS (Priority: HIGH):" | sed 's/./=/g')" >> "$warnings_file"
        
        # Extract deprecation warnings
        if [ "$deprecation_count" -gt 0 ]; then
            grep -E "(DeprecationWarning|PendingDeprecationWarning)" "$temp_output" | \
                sed 's/^/  → /' >> "$warnings_file" 2>/dev/null || echo "  No deprecation details available" >> "$warnings_file"
        else
            echo "  ✓ No deprecation warnings found" >> "$warnings_file"
        fi
        
        echo "" >> "$warnings_file"
        echo "OTHER WARNINGS (Priority: MEDIUM):" >> "$warnings_file"
        echo "$(echo "OTHER WARNINGS (Priority: MEDIUM):" | sed 's/./=/g')" >> "$warnings_file"
        
        # Extract other warnings
        if [ "$warning_count" -gt 0 ]; then
            grep -E "(UserWarning|RuntimeWarning|FutureWarning)" "$temp_output" | \
                sed 's/^/  → /' >> "$warnings_file" 2>/dev/null || echo "  No warning details available" >> "$warnings_file"
        else
            echo "  ✓ No other warnings found" >> "$warnings_file"
        fi
        
        echo "" >> "$warnings_file"
        echo "PYTEST WARNINGS (Priority: INFO):" >> "$warnings_file"
        echo "$(echo "PYTEST WARNINGS (Priority: INFO):" | sed 's/./=/g')" >> "$warnings_file"
        
        # Extract pytest warnings section
        if [ "$pytest_warnings" -gt 0 ]; then
            # Extract the full warnings summary section from pytest output
            # Look for the section between "warnings summary" and final summary line
            if grep -q "warnings summary" "$temp_output" 2>/dev/null; then
                echo "  🟢 PYTEST TEST WARNINGS ($pytest_warnings found):" >> "$warnings_file"
                echo "" >> "$warnings_file"
                
                # Extract the warnings summary section
                sed -n '/====.*warnings summary.*====/,/====.*warnings in.*====/p' "$temp_output" | \
                    grep -v "====.*warnings summary.*====" | \
                    grep -v "====.*warnings in.*====" | \
                    grep -v "^-- Docs:" | \
                    sed 's/^/    → /' >> "$warnings_file" 2>/dev/null
                
                echo "" >> "$warnings_file"
                echo "  💡 ULTRATHINK ENHANCEMENT OPPORTUNITIES:" >> "$warnings_file"
                echo "     • Test configuration optimization - Review pytest.ini settings for warning filters" >> "$warnings_file"
                echo "     • Dependency updates - Check if warnings indicate outdated library usage patterns" >> "$warnings_file"
                echo "     • Test isolation improvements - Warnings may indicate test interdependencies" >> "$warnings_file"
                echo "     • Environment configuration - Review if warnings suggest missing test environment setup" >> "$warnings_file"
                echo "     • Code modernization - Warnings often highlight areas for code quality improvements" >> "$warnings_file"
            else
                echo "  🟢 PYTEST WARNINGS DETECTED: $pytest_warnings warnings found in summary" >> "$warnings_file"
                echo "     (Full warning details not captured in this run - run with -vv for details)" >> "$warnings_file"
            fi
        else
            echo "  ✓ No pytest warnings found" >> "$warnings_file"
        fi
        
        echo "" >> "$warnings_file"
        echo "LLM ACTION ITEMS:" >> "$warnings_file"
        echo "$(echo "LLM ACTION ITEMS:" | sed 's/./=/g')" >> "$warnings_file"
        
        local action_num=1
        
        if [ "$total_runtime_issues" -gt 0 ]; then
            echo "$action_num. 🔴 CRITICAL: Fix $total_runtime_issues runtime issues (resource leaks, task cleanup, I/O problems)" >> "$warnings_file"
            echo "   - These indicate serious resource management problems in connection_manager.py:659" >> "$warnings_file"
            echo "   - Focus on WebSocket connection cleanup and async task lifecycle management" >> "$warnings_file"
            ((action_num++))
        fi
        
        if [ "$deprecation_count" -gt 0 ]; then
            echo "$action_num. 🟡 URGENT: Fix $deprecation_count deprecation warnings to prevent future breaks" >> "$warnings_file"
            ((action_num++))
        fi
        
        if [ "$warning_count" -gt 0 ]; then
            echo "$action_num. 🔵 QUALITY: Address $warning_count code quality warnings" >> "$warnings_file"
            ((action_num++))
        fi
        
        if [ "$pytest_warnings" -gt 0 ]; then
            echo "$action_num. 🟢 OPTIMIZE: Analyze $pytest_warnings pytest warnings for test suite enhancement" >> "$warnings_file"
            echo "   - Review pytest.ini configuration to filter unnecessary warnings" >> "$warnings_file"
            echo "   - Check for outdated test patterns or deprecated testing practices" >> "$warnings_file"
            echo "   - Consider updating test dependencies or configuration" >> "$warnings_file"
            echo "   - Use warnings to identify opportunities for test modernization" >> "$warnings_file"
        fi
        
        # Track chunks with warnings
        WARNING_CHUNKS+=("$chunk_name")
    fi
    
    # Update global counters
    TOTAL_PASSED=$((TOTAL_PASSED + passed_count))
    TOTAL_FAILED=$((TOTAL_FAILED + failed_count))
    TOTAL_ERRORS=$((TOTAL_ERRORS + error_count))
    TOTAL_WARNINGS=$((TOTAL_WARNINGS + warning_count))
    TOTAL_DEPRECATIONS=$((TOTAL_DEPRECATIONS + deprecation_count))
    TOTAL_RUNTIME_ISSUES=$((TOTAL_RUNTIME_ISSUES + total_runtime_issues))
    TOTAL_PYTEST_WARNINGS=$((TOTAL_PYTEST_WARNINGS + pytest_warnings))
    
    # Store chunk result
    CHUNK_RESULTS+=("$chunk_name:$status:$passed_count:$failed_count:$error_count:$deprecation_count:$warning_count:$total_runtime_issues:$pytest_warnings:$duration")
    
    # Clean up temp file
    rm -f "$temp_output"
    
    echo "[$chunk_name] Duration: ${duration}s" >> "$RESULTS_DIR/execution-log.txt"
    echo "" >> "$RESULTS_DIR/execution-log.txt"
}

generate_overall_summary() {
    log "Generating overall summary..."
    
    local summary_file="$RESULTS_DIR/overall-summary.txt"
    local start_time_file="$RESULTS_DIR/.start_time"
    local total_duration="Unknown"
    
    if [ -f "$start_time_file" ]; then
        local start_time=$(cat "$start_time_file")
        local end_time=$(date +%s)
        total_duration="$((end_time - start_time)) seconds"
    fi
    
    cat > "$summary_file" << EOF
BACKEND TEST SUITE EXECUTION SUMMARY
=====================================
Total Execution Time: $total_duration
Start Time: $(head -n 3 "$RESULTS_DIR/execution-log.txt" | tail -n 1 | cut -d' ' -f2-)
End Time: $(date)

CHUNK RESULTS:
EOF

    # Add chunk results
    for result in "${CHUNK_RESULTS[@]}"; do
        IFS=':' read -r chunk_name status passed failed errors deprecations warnings runtime_issues pytest_warnings duration <<< "$result"
        local total_tests=$((passed + failed + errors))
        local total_warnings=$((deprecations + warnings))
        local total_issues=$((runtime_issues + deprecations + warnings + pytest_warnings))
        
        if [ "$status" = "PASSED" ]; then
            if [ "$runtime_issues" -gt 0 ]; then
                echo "✓ $chunk_name: $passed/$total_tests PASSED (${duration}s) 🔴 $runtime_issues critical issues" >> "$summary_file"
            elif [ "$total_warnings" -gt 0 ]; then
                echo "✓ $chunk_name: $passed/$total_tests PASSED (${duration}s) ⚠ $total_warnings warnings" >> "$summary_file"
            elif [ "$pytest_warnings" -gt 0 ]; then
                echo "✓ $chunk_name: $passed/$total_tests PASSED (${duration}s) ℹ $pytest_warnings pytest warnings" >> "$summary_file"
            else
                echo "✓ $chunk_name: $passed/$total_tests PASSED (${duration}s)" >> "$summary_file"
            fi
        else
            if [ "$runtime_issues" -gt 0 ]; then
                echo "✗ $chunk_name: $passed/$total_tests tests ($failed FAILED, $errors ERRORS) (${duration}s) 🔴 $runtime_issues critical issues" >> "$summary_file"
            elif [ "$total_warnings" -gt 0 ]; then
                echo "✗ $chunk_name: $passed/$total_tests tests ($failed FAILED, $errors ERRORS) (${duration}s) ⚠ $total_warnings warnings" >> "$summary_file"
            else
                echo "✗ $chunk_name: $passed/$total_tests tests ($failed FAILED, $errors ERRORS) (${duration}s)" >> "$summary_file"
            fi
        fi
    done
    
    local total_tests=$((TOTAL_PASSED + TOTAL_FAILED + TOTAL_ERRORS))
    local success_rate=0
    if [ $total_tests -gt 0 ]; then
        success_rate=$(( (TOTAL_PASSED * 100) / total_tests ))
    fi
    
    local total_all_warnings=$((TOTAL_DEPRECATIONS + TOTAL_WARNINGS))
    local total_all_issues=$((TOTAL_RUNTIME_ISSUES + TOTAL_DEPRECATIONS + TOTAL_WARNINGS + TOTAL_PYTEST_WARNINGS))
    
    cat >> "$summary_file" << EOF

OVERALL: $TOTAL_PASSED/$total_tests tests passed (${success_rate}% success rate)
RUNTIME ISSUES: $TOTAL_RUNTIME_ISSUES critical (resource leaks, task cleanup, I/O problems)
WARNINGS: $total_all_warnings total ($TOTAL_DEPRECATIONS deprecations, $TOTAL_WARNINGS other warnings)
PYTEST WARNINGS: $TOTAL_PYTEST_WARNINGS test framework warnings
EOF

    if [ ${#FAILED_CHUNKS[@]} -gt 0 ]; then
        cat >> "$summary_file" << EOF

FAILURES TO INVESTIGATE:
EOF
        for chunk in "${FAILED_CHUNKS[@]}"; do
            echo "- $chunk: Check ${chunk}-failures.txt for details" >> "$summary_file"
        done
    fi
    
    if [ ${#WARNING_CHUNKS[@]} -gt 0 ]; then
        cat >> "$summary_file" << EOF

WARNINGS TO ADDRESS (PROACTIVE MAINTENANCE):
EOF
        for chunk in "${WARNING_CHUNKS[@]}"; do
            echo "- $chunk: Check ${chunk}-warnings.txt for LLM-actionable items" >> "$summary_file"
        done
    fi
    
    # Add warning priority summary if there are warnings
    if [ "$TOTAL_DEPRECATIONS" -gt 0 ] || [ "$TOTAL_WARNINGS" -gt 0 ]; then
        cat >> "$summary_file" << EOF

WARNING PRIORITY GUIDE:
EOF
        if [ "$TOTAL_DEPRECATIONS" -gt 0 ]; then
            echo "🔴 HIGH: $TOTAL_DEPRECATIONS deprecation warnings (fix immediately to prevent future breaks)" >> "$summary_file"
        fi
        if [ "$TOTAL_WARNINGS" -gt 0 ]; then
            echo "🟡 MEDIUM: $TOTAL_WARNINGS other warnings (code quality improvements)" >> "$summary_file"
        fi
        
        cat >> "$summary_file" << EOF

LLM COMMANDS FOR WARNING ANALYSIS:
EOF
        for chunk in "${WARNING_CHUNKS[@]}"; do
            echo "  cat logs/test-results/${chunk}-warnings.txt" >> "$summary_file"
        done
    fi
    
    # Create quick status file
    local status_file="$RESULTS_DIR/last-run-status.txt"
    if [ ${#FAILED_CHUNKS[@]} -eq 0 ]; then
        if [ "$total_all_warnings" -gt 0 ]; then
            echo "✅ ALL TESTS PASSED ($TOTAL_PASSED/$total_tests) ⚠ $total_all_warnings warnings - $(date)" > "$status_file"
            echo "Warning chunks: ${WARNING_CHUNKS[*]}" >> "$status_file"
            if [ "$TOTAL_DEPRECATIONS" -gt 0 ]; then
                echo "🔴 URGENT: $TOTAL_DEPRECATIONS deprecation warnings need immediate attention" >> "$status_file"
            fi
        else
            echo "✅ ALL TESTS PASSED ($TOTAL_PASSED/$total_tests) - $(date)" > "$status_file"
        fi
    else
        if [ "$total_all_warnings" -gt 0 ]; then
            echo "❌ SOME TESTS FAILED ($TOTAL_PASSED/$total_tests) - ${#FAILED_CHUNKS[@]} chunks failed, $total_all_warnings warnings - $(date)" > "$status_file"
        else
            echo "❌ SOME TESTS FAILED ($TOTAL_PASSED/$total_tests) - ${#FAILED_CHUNKS[@]} chunks failed - $(date)" > "$status_file"
        fi
        echo "Failed chunks: ${FAILED_CHUNKS[*]}" >> "$status_file"
        if [ ${#WARNING_CHUNKS[@]} -gt 0 ]; then
            echo "Warning chunks: ${WARNING_CHUNKS[*]}" >> "$status_file"
        fi
    fi
}

parse_chunk_arguments() {
    local chunks_to_run=()
    
    if [ $# -eq 0 ]; then
        # No arguments - run all chunks
        chunks_to_run=(1 2 3 4 5 6 7 8 9 10)
    else
        # Parse chunk arguments (e.g., "7a", "7b", "7c", "8")
        for arg in "$@"; do
            case $arg in
                1) chunks_to_run+=(1) ;;
                2) chunks_to_run+=(2) ;;
                3) chunks_to_run+=(3) ;;
                4) chunks_to_run+=(4) ;;
                5) chunks_to_run+=(5) ;;
                6) chunks_to_run+=(6) ;;
                7a) chunks_to_run+=(7) ;;
                7b) chunks_to_run+=(8) ;;
                7c) chunks_to_run+=(9) ;;
                8) chunks_to_run+=(10) ;;
                *)
                    echo -e "${RED}❌ Invalid chunk: $arg${NC}"
                    echo "Valid chunks: 1, 2, 3, 4, 5, 6, 7a, 7b, 7c, 8"
                    exit 1
                    ;;
            esac
        done
    fi
    
    echo "${chunks_to_run[@]}"
}

show_usage() {
    echo "Usage: $0 [chunk1] [chunk2] ..."
    echo ""
    echo "Available chunks:"
    echo "  1   - Foundation tests"
    echo "  2   - Core services"  
    echo "  3   - Business services"
    echo "  4   - Advanced services"
    echo "  5   - REST API endpoints"
    echo "  6   - WebSocket API endpoints"
    echo "  7a  - Bot Integration tests"
    echo "  7b  - Data Flow Integration tests" 
    echo "  7c  - WebSocket Integration tests"
    echo "  8   - Performance and load tests"
    echo ""
    echo "Examples:"
    echo "  $0           # Run all chunks"
    echo "  $0 7a 7b 7c  # Run only split integration chunks"
    echo "  $0 8         # Run only performance tests"
    echo "  $0 1 2 3     # Run only foundation and service chunks"
}

main() {
    # Handle help flag
    if [[ "$1" == "-h" || "$1" == "--help" ]]; then
        show_usage
        exit 0
    fi
    
    echo -e "${BLUE}"
    echo "🚀 Backend Test Suite with Chunked Execution"
    echo "=============================================="
    echo -e "${NC}"
    
    # Parse which chunks to run
    chunks_array=($(parse_chunk_arguments "$@"))
    total_chunks=${#chunks_array[@]}
    
    # Change to backend directory
    cd "$BACKEND_DIR"
    
    setup_results_directory
    
    # Store start time after directory is created
    date +%s > "$RESULTS_DIR/.start_time"
    
    if [ $total_chunks -eq 10 ]; then
        log "Executing all 10 chunks in logical dependency order..."
    else
        log "Executing $total_chunks selected chunks..."
        chunk_names=()
        for chunk_idx in "${chunks_array[@]}"; do
            chunk_info=${CHUNKS[$chunk_idx]}
            chunk_name=$(echo "$chunk_info" | cut -d':' -f1)
            chunk_names+=("$chunk_name")
        done
        log "Selected chunks: ${chunk_names[*]}"
    fi
    echo ""
    
    # Run selected chunks
    current_chunk=1
    for chunk_idx in "${chunks_array[@]}"; do
        chunk_info=${CHUNKS[$chunk_idx]}
        chunk_name=$(echo "$chunk_info" | cut -d':' -f1)
        echo -e "${BLUE}━━━ CHUNK $current_chunk/$total_chunks ($chunk_name) ━━━${NC}"
        run_chunk $chunk_idx
        echo ""
        
        # Small delay between chunks to prevent resource conflicts
        sleep 2
        current_chunk=$((current_chunk + 1))
    done
    
    generate_overall_summary
    
    # Final status
    echo -e "${BLUE}━━━ EXECUTION COMPLETE ━━━${NC}"
    
    local total_all_warnings=$((TOTAL_DEPRECATIONS + TOTAL_WARNINGS))
    
    if [ ${#FAILED_CHUNKS[@]} -eq 0 ]; then
        if [ "$total_all_warnings" -gt 0 ]; then
            log_success "All $total_chunks chunks completed successfully! ($TOTAL_PASSED tests passed)"
            log_warning "Found $total_all_warnings warnings ($TOTAL_DEPRECATIONS deprecations, $TOTAL_WARNINGS other)"
            echo ""
            echo -e "${GREEN}🎉 100% SUCCESS RATE! All selected backend tests are passing!${NC}"
            if [ "$TOTAL_DEPRECATIONS" -gt 0 ]; then
                echo -e "${YELLOW}⚠️  WARNING: $TOTAL_DEPRECATIONS deprecation warnings need immediate attention${NC}"
            fi
            echo ""
            echo -e "${BLUE}📊 Warning Analysis:${NC}"
            for chunk in "${WARNING_CHUNKS[@]}"; do
                echo -e "  • ${chunk}: ${BLUE}cat logs/test-results/${chunk}-warnings.txt${NC}"
            done
        else
            log_success "All $total_chunks chunks completed successfully! ($TOTAL_PASSED tests passed)"
            echo ""
            echo -e "${GREEN}🎉 100% SUCCESS RATE! All selected backend tests are passing!${NC}"
        fi
        exit 0
    else
        if [ "$total_all_warnings" -gt 0 ]; then
            log_error "${#FAILED_CHUNKS[@]} of $total_chunks chunks failed (Passed: $TOTAL_PASSED, Failed: $TOTAL_FAILED, Errors: $TOTAL_ERRORS)"
            log_warning "Also found $total_all_warnings warnings ($TOTAL_DEPRECATIONS deprecations, $TOTAL_WARNINGS other)"
        else
            log_error "${#FAILED_CHUNKS[@]} of $total_chunks chunks failed (Passed: $TOTAL_PASSED, Failed: $TOTAL_FAILED, Errors: $TOTAL_ERRORS)"
        fi
        echo ""
        echo -e "${RED}📊 Results Summary:${NC}"
        echo -e "  • View details: ${BLUE}cat logs/test-results/overall-summary.txt${NC}"
        echo -e "  • Quick status: ${BLUE}cat logs/test-results/last-run-status.txt${NC}"
        echo -e "  • Analyze failures: ${BLUE}./scripts/analyze-test-results.sh${NC}"
        if [ ${#WARNING_CHUNKS[@]} -gt 0 ]; then
            echo ""
            echo -e "${YELLOW}⚠️  Warning Analysis:${NC}"
            for chunk in "${WARNING_CHUNKS[@]}"; do
                echo -e "  • ${chunk}: ${BLUE}cat logs/test-results/${chunk}-warnings.txt${NC}"
            done
        fi
        exit 1
    fi
}

# Handle Ctrl+C gracefully
trap 'echo -e "\n${RED}❌ Test execution interrupted${NC}"; exit 130' INT

# Run main function
main "$@"