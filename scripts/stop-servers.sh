#!/bin/bash

# Stop OrderFox servers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common configuration and functions
source "$SCRIPT_DIR/common.sh"

echo -e "${YELLOW}Stopping OrderFox servers...${NC}"

# Kill processes by port
echo "Stopping processes on ports $FRONTEND_PORT and $BACKEND_PORT..."
npx kill-port $FRONTEND_PORT $BACKEND_PORT 2>/dev/null

# Also try to kill by PID if available
BACKEND_PID=$(get_pid "backend")
if [ ! -z "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID"
    echo -e "${GREEN}✓ Stopped backend server (PID: $BACKEND_PID)${NC}"
fi
remove_pid_file "backend"

FRONTEND_PID=$(get_pid "frontend")
if [ ! -z "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID"
    echo -e "${GREEN}✓ Stopped frontend server (PID: $FRONTEND_PID)${NC}"
fi
remove_pid_file "frontend"

# Kill any remaining uvicorn or vite processes
pkill -f "uvicorn.*app\.main:app" 2>/dev/null
pkill -f "vite.*serve" 2>/dev/null

echo -e "${GREEN}✓ All servers stopped${NC}"