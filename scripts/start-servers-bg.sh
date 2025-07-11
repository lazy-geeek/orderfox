#!/bin/bash

# Start OrderFox servers in background for Claude Code
# Only starts servers if they're not already running (they auto-reload on file changes)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common configuration and functions
source "$SCRIPT_DIR/common.sh"

echo -e "${YELLOW}Checking OrderFox server status...${NC}"

# Clean up log files when starting servers
echo -e "${YELLOW}Cleaning up log files...${NC}"
clean_log_files

SERVERS_STARTED=false

# Check backend server (port $BACKEND_PORT)
if is_port_in_use $BACKEND_PORT; then
    echo -e "${GREEN}✓ Backend server already running on port $BACKEND_PORT (auto-reloads on changes)${NC}"
else
    echo -e "${YELLOW}Starting backend server on port $BACKEND_PORT...${NC}"
    cd "$PROJECT_ROOT/backend"
    # Activate conda environment and start backend
    nohup bash -c "source ~/miniconda3/etc/profile.d/conda.sh && conda activate orderfox && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port $BACKEND_PORT" > "$PROJECT_ROOT/logs/backend.log" 2>&1 &
    BACKEND_PID=$!
    save_pid "backend" $BACKEND_PID
    echo -e "${GREEN}✓ Backend server started (PID: $BACKEND_PID)${NC}"
    SERVERS_STARTED=true
fi

# Check frontend server (port $FRONTEND_PORT)
if is_port_in_use $FRONTEND_PORT; then
    echo -e "${GREEN}✓ Frontend server already running on port $FRONTEND_PORT (auto-reloads on changes)${NC}"
else
    echo -e "${YELLOW}Starting frontend server on port $FRONTEND_PORT...${NC}"
    cd "$PROJECT_ROOT/frontend_vanilla"
    nohup npm run dev > "$PROJECT_ROOT/logs/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    save_pid "frontend" $FRONTEND_PID
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

print_log_paths