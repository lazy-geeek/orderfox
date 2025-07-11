#!/bin/bash

# Start OrderFox servers for manual/interactive use
# Uses smart detection but shows live output for manual development

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common configuration and functions
source "$SCRIPT_DIR/common.sh"

echo -e "${BLUE}=== OrderFox Development Server ===${NC}"
echo -e "${YELLOW}Checking server status...${NC}"

# Clean up log files when starting servers
echo -e "${YELLOW}Cleaning up log files...${NC}"
clean_log_files

NEED_TO_START=false

# Check backend server (port $BACKEND_PORT)
if is_port_in_use $BACKEND_PORT; then
    echo -e "${GREEN}✓ Backend server already running on port $BACKEND_PORT${NC}"
else
    echo -e "${YELLOW}→ Backend server needs to start${NC}"
    NEED_TO_START=true
fi

# Check frontend server (port $FRONTEND_PORT)
if is_port_in_use $FRONTEND_PORT; then
    echo -e "${GREEN}✓ Frontend server already running on port $FRONTEND_PORT${NC}"
else
    echo -e "${YELLOW}→ Frontend server needs to start${NC}"
    NEED_TO_START=true
fi

if [ "$NEED_TO_START" = false ]; then
    echo ""
    echo -e "${GREEN}✓ All servers are already running!${NC}"
    echo -e "${BLUE}Servers auto-reload on file changes - you're ready to develop!${NC}"
    echo ""
    echo "🌐 Frontend: $FRONTEND_URL"
    echo "🔧 Backend API: $BACKEND_URL"
    echo "📊 Backend Health: $BACKEND_URL/health"
    echo ""
    echo "💡 Use Ctrl+C to stop this script (servers will keep running)"
    echo "💡 Use 'npm run dev:stop' to stop servers"
    echo "💡 Check logs: npm run dev:status"
    echo ""
    
    # Keep script running for user experience (they can Ctrl+C)
    echo "Press Ctrl+C to exit (servers will continue running)..."
    trap 'echo -e "\n${GREEN}Exiting script - servers continue running${NC}"; exit 0' INT
    while true; do
        sleep 1
    done
else
    echo ""
    echo -e "${YELLOW}Starting servers...${NC}"
    
    # Clean up any stuck processes first
    npx kill-port $FRONTEND_PORT $BACKEND_PORT 2>/dev/null || true
    
    # Start servers using concurrently for interactive display
    echo -e "${BLUE}Starting with live output (Ctrl+C to stop)...${NC}"
    echo ""
    
    cd "$PROJECT_ROOT"
    concurrently \
        --names "BACKEND,FRONTEND" \
        --prefix "[{name}]" \
        --prefix-colors "blue,green" \
        "cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port $BACKEND_PORT" \
        "cd frontend_vanilla && npm run dev"
fi