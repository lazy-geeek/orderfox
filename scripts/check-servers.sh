#!/bin/bash

# Check OrderFox server status

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common configuration and functions
source "$SCRIPT_DIR/common.sh"

echo -e "${YELLOW}OrderFox Server Status${NC}"
echo "======================"

# Check backend and frontend status
print_server_status "Backend" $BACKEND_PORT
print_server_status "Frontend" $FRONTEND_PORT

# Check server health
print_health_status

# Show log paths
print_log_paths