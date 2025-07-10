#!/bin/bash

# Start OrderFox servers in background for Claude Code
# Only starts servers if they're not already running (they auto-reload on file changes)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Checking OrderFox server status...${NC}"

# Function to check if a port is in use
is_port_in_use() {
    lsof -i:$1 >/dev/null 2>&1
}

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/logs"

# Clean up log files when starting servers
echo -e "${YELLOW}Cleaning up log files...${NC}"
> "$PROJECT_ROOT/logs/backend.log"
> "$PROJECT_ROOT/logs/frontend.log"

SERVERS_STARTED=false

# Check backend server (port 8000)
if is_port_in_use 8000; then
    echo -e "${GREEN}✓ Backend server already running on port 8000 (auto-reloads on changes)${NC}"
else
    echo -e "${YELLOW}Starting backend server on port 8000...${NC}"
    cd "$PROJECT_ROOT/backend"
    # Activate conda environment and start backend
    nohup bash -c "source ~/miniconda3/etc/profile.d/conda.sh && conda activate orderfox && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" > "$PROJECT_ROOT/logs/backend.log" 2>&1 &
    BACKEND_PID=$!
    echo "$BACKEND_PID" > "$PROJECT_ROOT/logs/backend.pid"
    echo -e "${GREEN}✓ Backend server started (PID: $BACKEND_PID)${NC}"
    SERVERS_STARTED=true
fi

# Check frontend server (port 3000)
if is_port_in_use 3000; then
    echo -e "${GREEN}✓ Frontend server already running on port 3000 (auto-reloads on changes)${NC}"
else
    echo -e "${YELLOW}Starting frontend server on port 3000...${NC}"
    cd "$PROJECT_ROOT/frontend_vanilla"
    nohup npm run dev > "$PROJECT_ROOT/logs/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    echo "$FRONTEND_PID" > "$PROJECT_ROOT/logs/frontend.pid"
    echo -e "${GREEN}✓ Frontend server started (PID: $FRONTEND_PID)${NC}"
    SERVERS_STARTED=true
fi

echo ""
if [ "$SERVERS_STARTED" = true ]; then
    echo -e "${GREEN}Servers started successfully!${NC}"
    echo "They will auto-reload when you make changes to the code."
else
    echo -e "${GREEN}All servers are already running!${NC}"
    echo "No action needed - they auto-reload on file changes."
fi

echo ""
echo "Logs available at:"
echo "- Backend: $PROJECT_ROOT/logs/backend.log"
echo "- Frontend: $PROJECT_ROOT/logs/frontend.log"