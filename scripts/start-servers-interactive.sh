#!/bin/bash

# Start OrderFox servers for manual/interactive use
# Uses smart detection but shows live output for manual development

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== OrderFox Development Server ===${NC}"
echo -e "${YELLOW}Checking server status...${NC}"

# Function to check if a port is in use
is_port_in_use() {
    lsof -i:$1 >/dev/null 2>&1
}

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/logs"

NEED_TO_START=false

# Check backend server (port 8000)
if is_port_in_use 8000; then
    echo -e "${GREEN}✓ Backend server already running on port 8000${NC}"
else
    echo -e "${YELLOW}→ Backend server needs to start${NC}"
    NEED_TO_START=true
fi

# Check frontend server (port 3000)
if is_port_in_use 3000; then
    echo -e "${GREEN}✓ Frontend server already running on port 3000${NC}"
else
    echo -e "${YELLOW}→ Frontend server needs to start${NC}"
    NEED_TO_START=true
fi

if [ "$NEED_TO_START" = false ]; then
    echo ""
    echo -e "${GREEN}✓ All servers are already running!${NC}"
    echo -e "${BLUE}Servers auto-reload on file changes - you're ready to develop!${NC}"
    echo ""
    echo "🌐 Frontend: http://localhost:3000"
    echo "🔧 Backend API: http://localhost:8000"
    echo "📊 Backend Health: http://localhost:8000/health"
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
    npx kill-port 3000 8000 2>/dev/null || true
    
    # Start servers using concurrently for interactive display
    echo -e "${BLUE}Starting with live output (Ctrl+C to stop)...${NC}"
    echo ""
    
    cd "$PROJECT_ROOT"
    concurrently \
        --names "BACKEND,FRONTEND" \
        --prefix "[{name}]" \
        --prefix-colors "blue,green" \
        "cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" \
        "cd frontend_vanilla && npm run dev"
fi