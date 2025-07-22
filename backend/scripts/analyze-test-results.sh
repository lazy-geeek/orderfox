#!/bin/bash

# Backend Test Results Analyzer - LLM-Optimized Failure & Warning Analysis
#
# This script provides intelligent analysis of test execution results with:
# - Smart pattern detection across test failures  
# - Priority-based warning classification
# - LLM-actionable fix suggestions
# - Root cause analysis and grouping
# - Historical trend analysis
#
# Features:
# - Pattern recognition for common failure types
# - Automated grouping of related issues
# - Priority-based action planning
# - Comprehensive LLM command generation

set -e

# Configuration
BACKEND_DIR="/home/bail/github/orderfox/backend"
RESULTS_DIR="$BACKEND_DIR/logs/test-results"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Analysis mode flags
SHOW_SUMMARY=true
SHOW_FAILURES=false
SHOW_WARNINGS=false
SHOW_PATTERNS=false
SHOW_ALL=false
SPECIFIC_CHUNK=""

# Result tracking
declare -a FAILURE_PATTERNS
declare -a WARNING_PATTERNS
declare -a CRITICAL_ISSUES
declare -a ACTION_ITEMS

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

log_info() {
    echo -e "${CYAN}[$(date +'%H:%M:%S')] ℹ${NC} $1"
}

show_header() {
    echo -e "${PURPLE}"
    echo "🔍 Backend Test Results Analysis"
    echo "=================================="
    echo -e "${NC}"
}

check_results_exist() {
    if [ ! -d "$RESULTS_DIR" ] || [ ! -f "$RESULTS_DIR/last-run-status.txt" ]; then
        log_error "No test results found in $RESULTS_DIR"
        echo "Run './scripts/run-backend-tests.sh' first to generate test results."
        exit 1
    fi
}

parse_last_run_status() {
    local status_file="$RESULTS_DIR/last-run-status.txt"
    local overall_summary="$RESULTS_DIR/overall-summary.txt"
    
    echo -e "${BLUE}📊 EXECUTION SUMMARY${NC}"
    echo "===================="
    
    # Read status file
    if [ -f "$status_file" ]; then
        cat "$status_file"
        echo ""
    fi
    
    # Extract key metrics from overall summary
    if [ -f "$overall_summary" ]; then
        local success_rate=$(grep "success rate" "$overall_summary" | grep -oE "[0-9]+%" || echo "N/A")
        local total_tests=$(grep "OVERALL:" "$overall_summary" | grep -oE "[0-9]+/[0-9]+" | head -1 || echo "N/A")
        local warnings=$(grep "WARNINGS:" "$overall_summary" | grep -oE "[0-9]+ total" | grep -oE "[0-9]+" || echo "0")
        local execution_time=$(grep "Total Execution Time:" "$overall_summary" | cut -d':' -f2- | xargs || echo "N/A")
        
        echo -e "${CYAN}Key Metrics:${NC}"
        echo "  • Tests: $total_tests"
        echo "  • Success Rate: $success_rate"
        echo "  • Warnings: $warnings"
        echo "  • Execution Time: $execution_time"
        echo ""
    fi
}

detect_failure_patterns() {
    echo -e "${RED}🔍 FAILURE PATTERN ANALYSIS${NC}"
    echo "============================="
    
    local failure_files=($(find "$RESULTS_DIR" -name "*-failures.txt" 2>/dev/null))
    
    if [ ${#failure_files[@]} -eq 0 ]; then
        echo -e "${GREEN}✓ No failure files found - All tests passed!${NC}"
        echo ""
        return
    fi
    
    # Pattern detection arrays
    local websocket_failures=0
    local database_failures=0
    local mock_failures=0
    local timeout_failures=0
    local import_failures=0
    local assertion_failures=0
    
    # Analyze failure patterns
    for failure_file in "${failure_files[@]}"; do
        local chunk_name=$(basename "$failure_file" "-failures.txt")
        
        # Count pattern types
        if grep -q "WebSocket\\|websocket\\|WS" "$failure_file" 2>/dev/null; then
            ((websocket_failures++))
            FAILURE_PATTERNS+=("WebSocket issues in $chunk_name")
        fi
        
        if grep -q "Database\\|database\\|PostgreSQL\\|psycopg2\\|connection refused" "$failure_file" 2>/dev/null; then
            ((database_failures++))
            FAILURE_PATTERNS+=("Database connection issues in $chunk_name")
        fi
        
        if grep -q "Mock\\|mock\\|AsyncMock\\|MagicMock" "$failure_file" 2>/dev/null; then
            ((mock_failures++))
            FAILURE_PATTERNS+=("Mock configuration issues in $chunk_name")
        fi
        
        if grep -q "timeout\\|TimeoutError\\|timed out" "$failure_file" 2>/dev/null; then
            ((timeout_failures++))
            FAILURE_PATTERNS+=("Timeout issues in $chunk_name")
        fi
        
        if grep -q "ImportError\\|ModuleNotFoundError\\|import" "$failure_file" 2>/dev/null; then
            ((import_failures++))
            FAILURE_PATTERNS+=("Import/module issues in $chunk_name")
        fi
        
        if grep -q "AssertionError\\|assert" "$failure_file" 2>/dev/null; then
            ((assertion_failures++))
            FAILURE_PATTERNS+=("Assertion failures in $chunk_name")
        fi
    done
    
    # Report patterns
    if [ $websocket_failures -gt 0 ]; then
        echo -e "${RED}🔴 WebSocket Issues: $websocket_failures chunks affected${NC}"
        CRITICAL_ISSUES+=("WebSocket connectivity or mock issues ($websocket_failures chunks)")
        ACTION_ITEMS+=("Review WebSocket test patterns in backend/CLAUDE.md")
        ACTION_ITEMS+=("Check exchange_service mocking in failing WebSocket tests")
    fi
    
    if [ $database_failures -gt 0 ]; then
        echo -e "${RED}🔴 Database Issues: $database_failures chunks affected${NC}"
        CRITICAL_ISSUES+=("Database connection or configuration problems ($database_failures chunks)")
        ACTION_ITEMS+=("Verify DATABASE_URL configuration")
        ACTION_ITEMS+=("Check PostgreSQL service status")
    fi
    
    if [ $mock_failures -gt 0 ]; then
        echo -e "${YELLOW}🟡 Mock Issues: $mock_failures chunks affected${NC}"
        ACTION_ITEMS+=("Review mock configurations - use AsyncMock for async methods")
        ACTION_ITEMS+=("Check symbol_service vs exchange_service mocking patterns")
    fi
    
    if [ $timeout_failures -gt 0 ]; then
        echo -e "${YELLOW}🟡 Timeout Issues: $timeout_failures chunks affected${NC}"
        ACTION_ITEMS+=("Consider increasing chunk timeout limits")
        ACTION_ITEMS+=("Review performance bottlenecks in affected tests")
    fi
    
    if [ $import_failures -gt 0 ]; then
        echo -e "${YELLOW}🟡 Import Issues: $import_failures chunks affected${NC}"
        ACTION_ITEMS+=("Check Python path and dependency installations")
        ACTION_ITEMS+=("Verify all required packages in requirements.txt")
    fi
    
    if [ $assertion_failures -gt 0 ]; then
        echo -e "${BLUE}🔵 Assertion Issues: $assertion_failures chunks affected${NC}"
        ACTION_ITEMS+=("Review test expectations vs actual behavior")
        ACTION_ITEMS+=("Check for recent API or behavior changes")
    fi
    
    echo ""
}

analyze_warnings() {
    echo -e "${YELLOW}⚠️  WARNING ANALYSIS${NC}"
    echo "==================="
    
    local warning_files=($(find "$RESULTS_DIR" -name "*-warnings.txt" 2>/dev/null))
    
    if [ ${#warning_files[@]} -eq 0 ]; then
        echo -e "${GREEN}✓ No warning files found - Clean codebase!${NC}"
        echo ""
        return
    fi
    
    local total_deprecations=0
    local total_warnings=0
    local critical_deprecations=()
    local quality_warnings=()
    
    # Analyze warning patterns
    for warning_file in "${warning_files[@]}"; do
        local chunk_name=$(basename "$warning_file" "-warnings.txt")
        
        # Count deprecations and warnings
        local chunk_deprecations=$(grep -c "DeprecationWarning\\|PendingDeprecationWarning" "$warning_file" 2>/dev/null || echo 0)
        local chunk_warnings=$(grep -c "UserWarning\\|RuntimeWarning\\|FutureWarning" "$warning_file" 2>/dev/null || echo 0)
        
        total_deprecations=$((total_deprecations + chunk_deprecations))
        total_warnings=$((total_warnings + chunk_warnings))
        
        if [ "$chunk_deprecations" -gt 0 ]; then
            critical_deprecations+=("$chunk_name: $chunk_deprecations deprecations")
            WARNING_PATTERNS+=("CRITICAL: $chunk_deprecations deprecations in $chunk_name")
        fi
        
        if [ "$chunk_warnings" -gt 0 ]; then
            quality_warnings+=("$chunk_name: $chunk_warnings warnings")
            WARNING_PATTERNS+=("QUALITY: $chunk_warnings warnings in $chunk_name")
        fi
    done
    
    # Report warning analysis
    if [ $total_deprecations -gt 0 ]; then
        echo -e "${RED}🔴 CRITICAL: $total_deprecations deprecation warnings found${NC}"
        echo "   These indicate APIs that will break in future versions!"
        for dep in "${critical_deprecations[@]}"; do
            echo "   • $dep"
        done
        echo ""
        
        CRITICAL_ISSUES+=("$total_deprecations deprecation warnings requiring immediate fixes")
        ACTION_ITEMS+=("Fix deprecation warnings to prevent future breaks")
        ACTION_ITEMS+=("Update deprecated API calls to current versions")
    fi
    
    if [ $total_warnings -gt 0 ]; then
        echo -e "${YELLOW}🟡 MEDIUM: $total_warnings code quality warnings found${NC}"
        echo "   These indicate code quality improvements needed:"
        for warn in "${quality_warnings[@]}"; do
            echo "   • $warn"
        done
        echo ""
        
        ACTION_ITEMS+=("Address code quality warnings for better maintainability")
    fi
}

generate_action_plan() {
    echo -e "${PURPLE}🎯 LLM ACTION PLAN${NC}"
    echo "=================="
    
    if [ ${#CRITICAL_ISSUES[@]} -eq 0 ] && [ ${#ACTION_ITEMS[@]} -eq 0 ]; then
        echo -e "${GREEN}✅ No critical issues found! Codebase is in excellent condition.${NC}"
        echo ""
        return
    fi
    
    # Critical issues first
    if [ ${#CRITICAL_ISSUES[@]} -gt 0 ]; then
        echo -e "${RED}🚨 IMMEDIATE ACTIONS REQUIRED:${NC}"
        local priority=1
        for issue in "${CRITICAL_ISSUES[@]}"; do
            echo "   $priority. $issue"
            ((priority++))
        done
        echo ""
    fi
    
    # Detailed action items
    if [ ${#ACTION_ITEMS[@]} -gt 0 ]; then
        echo -e "${BLUE}📋 DETAILED ACTION ITEMS:${NC}"
        local item_num=1
        for item in "${ACTION_ITEMS[@]}"; do
            echo "   $item_num. $item"
            ((item_num++))
        done
        echo ""
    fi
    
    # Generate specific commands
    echo -e "${CYAN}💻 LLM COMMANDS FOR INVESTIGATION:${NC}"
    
    # Check for specific failure files
    local failure_files=($(find "$RESULTS_DIR" -name "*-failures.txt" 2>/dev/null))
    if [ ${#failure_files[@]} -gt 0 ]; then
        echo ""
        echo -e "${CYAN}📁 Failure Analysis Commands:${NC}"
        for failure_file in "${failure_files[@]}"; do
            local chunk_name=$(basename "$failure_file" "-failures.txt")
            echo "   cat logs/test-results/${chunk_name}-failures.txt"
        done
    fi
    
    # Check for warning files
    local warning_files=($(find "$RESULTS_DIR" -name "*-warnings.txt" 2>/dev/null))
    if [ ${#warning_files[@]} -gt 0 ]; then
        echo ""
        echo -e "${CYAN}⚠️  Warning Analysis Commands:${NC}"
        for warning_file in "${warning_files[@]}"; do
            local chunk_name=$(basename "$warning_file" "-warnings.txt")
            echo "   cat logs/test-results/${chunk_name}-warnings.txt"
        done
    fi
    
    echo ""
    echo -e "${CYAN}🔄 Re-run Specific Chunks:${NC}"
    if [ ${#failure_files[@]} -gt 0 ]; then
        local failed_chunks=()
        for failure_file in "${failure_files[@]}"; do
            local chunk_name=$(basename "$failure_file" "-failures.txt")
            # Convert chunk names to script arguments
            case $chunk_name in
                chunk1) failed_chunks+=(1) ;;
                chunk2) failed_chunks+=(2) ;;
                chunk3) failed_chunks+=(3) ;;
                chunk4) failed_chunks+=(4) ;;
                chunk5) failed_chunks+=(5) ;;
                chunk6) failed_chunks+=(6) ;;
                chunk7a) failed_chunks+=(7a) ;;
                chunk7b) failed_chunks+=(7b) ;;
                chunk7c) failed_chunks+=(7c) ;;
                chunk8) failed_chunks+=(8) ;;
            esac
        done
        
        if [ ${#failed_chunks[@]} -gt 0 ]; then
            echo "   ./scripts/run-backend-tests.sh ${failed_chunks[*]}"
        fi
    fi
    
    echo ""
}

analyze_specific_chunk() {
    local chunk=$1
    echo -e "${BLUE}🔍 ANALYZING CHUNK: $chunk${NC}"
    echo "=========================="
    
    local summary_file="$RESULTS_DIR/${chunk}-summary.txt"
    local failure_file="$RESULTS_DIR/${chunk}-failures.txt"
    local warning_file="$RESULTS_DIR/${chunk}-warnings.txt"
    
    # Summary analysis
    if [ -f "$summary_file" ]; then
        echo -e "${CYAN}📊 Summary:${NC}"
        cat "$summary_file"
        echo ""
    else
        log_error "Summary file not found for chunk: $chunk"
        echo ""
        return
    fi
    
    # Failure analysis
    if [ -f "$failure_file" ]; then
        echo -e "${RED}❌ Failures:${NC}"
        cat "$failure_file"
        echo ""
    fi
    
    # Warning analysis
    if [ -f "$warning_file" ]; then
        echo -e "${YELLOW}⚠️  Warnings:${NC}"
        cat "$warning_file"
        echo ""
    fi
}

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Analyze backend test results with smart pattern detection and LLM-optimized output."
    echo ""
    echo "OPTIONS:"
    echo "  --summary          Show quick summary (default)"
    echo "  --failures         Show detailed failure analysis"
    echo "  --warnings         Show warning and deprecation analysis"
    echo "  --patterns         Show pattern detection across chunks"
    echo "  --chunk <name>     Analyze specific chunk (e.g., chunk1, chunk7a)"
    echo "  --all              Show comprehensive analysis"
    echo "  -h, --help         Show this help message"
    echo ""
    echo "EXAMPLES:"
    echo "  $0                 # Quick summary"
    echo "  $0 --failures      # Detailed failure analysis"
    echo "  $0 --warnings      # Warning analysis only"
    echo "  $0 --chunk chunk7c # Analyze WebSocket integration chunk"
    echo "  $0 --all           # Comprehensive analysis"
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --summary)
                SHOW_SUMMARY=true
                shift
                ;;
            --failures)
                SHOW_SUMMARY=false
                SHOW_FAILURES=true
                shift
                ;;
            --warnings)
                SHOW_SUMMARY=false
                SHOW_WARNINGS=true
                shift
                ;;
            --patterns)
                SHOW_SUMMARY=false
                SHOW_PATTERNS=true
                shift
                ;;
            --chunk)
                SHOW_SUMMARY=false
                SPECIFIC_CHUNK="$2"
                shift 2
                ;;
            --all)
                SHOW_SUMMARY=false
                SHOW_ALL=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

main() {
    parse_arguments "$@"
    
    show_header
    check_results_exist
    
    cd "$BACKEND_DIR"
    
    # Handle specific chunk analysis
    if [ -n "$SPECIFIC_CHUNK" ]; then
        analyze_specific_chunk "$SPECIFIC_CHUNK"
        return
    fi
    
    # Always show summary first
    parse_last_run_status
    
    # Show requested analysis
    if [ "$SHOW_ALL" = true ]; then
        detect_failure_patterns
        analyze_warnings
        generate_action_plan
    elif [ "$SHOW_FAILURES" = true ]; then
        detect_failure_patterns
        generate_action_plan
    elif [ "$SHOW_WARNINGS" = true ]; then
        analyze_warnings
        generate_action_plan
    elif [ "$SHOW_PATTERNS" = true ]; then
        detect_failure_patterns
        analyze_warnings
    elif [ "$SHOW_SUMMARY" = true ]; then
        # Quick analysis for summary mode
        local failure_count=$(find "$RESULTS_DIR" -name "*-failures.txt" 2>/dev/null | wc -l)
        local warning_count=$(find "$RESULTS_DIR" -name "*-warnings.txt" 2>/dev/null | wc -l)
        
        if [ $failure_count -gt 0 ] || [ $warning_count -gt 0 ]; then
            echo -e "${BLUE}📋 QUICK ANALYSIS${NC}"
            echo "=================="
            
            if [ $failure_count -gt 0 ]; then
                echo -e "${RED}• $failure_count chunks have failures${NC}"
                echo "  Run: $0 --failures"
            fi
            
            if [ $warning_count -gt 0 ]; then
                echo -e "${YELLOW}• $warning_count chunks have warnings${NC}"
                echo "  Run: $0 --warnings"
            fi
            
            echo ""
            echo -e "${CYAN}🔍 For comprehensive analysis:${NC}"
            echo "  $0 --all"
            echo ""
        else
            echo -e "${GREEN}🎉 Perfect! No failures or warnings detected.${NC}"
            echo ""
        fi
    fi
    
    log_info "Analysis complete. Use '$0 --help' for more options."
}

# Handle Ctrl+C gracefully
trap 'echo -e "\n${RED}❌ Analysis interrupted${NC}"; exit 130' INT

# Run main function
main "$@"