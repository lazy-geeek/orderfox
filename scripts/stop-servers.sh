#!/bin/bash

# Stop OrderFox servers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping OrderFox servers...${NC}"

# Kill processes by port
echo "Stopping processes on ports 3000 and 8000..."
npx kill-port 3000 8000 2>/dev/null

# Also try to kill by PID if available
if [ -f "$PROJECT_ROOT/logs/backend.pid" ]; then
    BACKEND_PID=$(cat "$PROJECT_ROOT/logs/backend.pid")
    if kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID"
        echo -e "${GREEN}✓ Stopped backend server (PID: $BACKEND_PID)${NC}"
    fi
    rm -f "$PROJECT_ROOT/logs/backend.pid"
fi

if [ -f "$PROJECT_ROOT/logs/frontend.pid" ]; then
    FRONTEND_PID=$(cat "$PROJECT_ROOT/logs/frontend.pid")
    if kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID"
        echo -e "${GREEN}✓ Stopped frontend server (PID: $FRONTEND_PID)${NC}"
    fi
    rm -f "$PROJECT_ROOT/logs/frontend.pid"
fi

# Kill any remaining uvicorn or vite processes
pkill -f "uvicorn.*app\.main:app" 2>/dev/null
pkill -f "vite.*serve" 2>/dev/null

echo -e "${GREEN}✓ All servers stopped${NC}"