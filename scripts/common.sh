#!/bin/bash

# Common configuration and functions for OrderFox scripts
# This file should be sourced by other scripts

# Script initialization
# SCRIPT_DIR is set by the calling script
if [ -z "$SCRIPT_DIR" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables from .env file if it exists
# Only load variables that aren't already set in the environment
load_env() {
    if [ -f "$PROJECT_ROOT/.env" ]; then
        while IFS='=' read -r key value; do
            # Skip comments and empty lines
            [[ $key =~ ^#.*$ ]] && continue
            [[ -z $key ]] && continue
            
            # Only set if variable is not already set
            if [ -z "${!key}" ]; then
                export "$key=$value"
            fi
        done < "$PROJECT_ROOT/.env"
    fi
}

# Load environment on sourcing
load_env

# Configuration from environment with defaults
BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-3000}
BACKEND_URL=${BACKEND_URL:-http://localhost:$BACKEND_PORT}
FRONTEND_URL=${FRONTEND_URL:-http://localhost:$FRONTEND_PORT}

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Common functions

# Check if a port is in use
is_port_in_use() {
    lsof -i:$1 >/dev/null 2>&1
}

# Check if backend is healthy
check_backend_health() {
    curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/health" | grep -q "200"
}

# Check if frontend is responding
check_frontend_health() {
    curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL" | grep -q "200"
}

# Create logs directory if it doesn't exist
ensure_logs_directory() {
    mkdir -p "$PROJECT_ROOT/logs"
}

# Clean up log files
clean_log_files() {
    ensure_logs_directory
    > "$PROJECT_ROOT/logs/backend.log"
    > "$PROJECT_ROOT/logs/frontend.log"
}

# Get process info for a port
get_process_info() {
    local port=$1
    lsof -i:$port | grep LISTEN | head -1
}

# Print server status
print_server_status() {
    local server_name=$1
    local port=$2
    
    echo ""
    echo "$server_name Server (Port $port):"
    if is_port_in_use $port; then
        echo -e "${GREEN}✓ Running${NC}"
        # Try to get process info
        local process_info=$(get_process_info $port)
        if [ ! -z "$process_info" ]; then
            echo "  Process: $process_info"
        fi
    else
        echo -e "${RED}✗ Not running${NC}"
    fi
}

# Print health check status
print_health_status() {
    echo ""
    echo "Server Health:"
    
    # Backend health check
    if check_backend_health; then
        echo -e "${GREEN}✓ Backend API responding${NC}"
    else
        echo -e "${YELLOW}⚠ Backend API not responding (may still be starting)${NC}"
    fi
    
    # Frontend health check
    if check_frontend_health; then
        echo -e "${GREEN}✓ Frontend responding${NC}"
    else
        echo -e "${YELLOW}⚠ Frontend not responding (may still be starting)${NC}"
    fi
}

# Print log paths
print_log_paths() {
    echo ""
    echo "Logs available at:"
    echo "- Backend: $PROJECT_ROOT/logs/backend.log"
    echo "- Frontend: $PROJECT_ROOT/logs/frontend.log"
}

# Save PID to file
save_pid() {
    local service=$1
    local pid=$2
    echo "$pid" > "$PROJECT_ROOT/logs/$service.pid"
}

# Get PID from file
get_pid() {
    local service=$1
    local pid_file="$PROJECT_ROOT/logs/$service.pid"
    if [ -f "$pid_file" ]; then
        cat "$pid_file"
    fi
}

# Remove PID file
remove_pid_file() {
    local service=$1
    rm -f "$PROJECT_ROOT/logs/$service.pid"
}