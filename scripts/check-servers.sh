#!/bin/bash

# Check OrderFox server status

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}OrderFox Server Status${NC}"
echo "======================"

# Function to check if a port is in use
is_port_in_use() {
    lsof -i:$1 >/dev/null 2>&1
}

# Check backend
echo ""
echo "Backend Server (Port 8000):"
if is_port_in_use 8000; then
    echo -e "${GREEN}✓ Running${NC}"
    # Try to get process info
    BACKEND_INFO=$(lsof -i:8000 | grep LISTEN | head -1)
    if [ ! -z "$BACKEND_INFO" ]; then
        echo "  Process: $BACKEND_INFO"
    fi
else
    echo -e "${RED}✗ Not running${NC}"
fi

# Check frontend
echo ""
echo "Frontend Server (Port 3000):"
if is_port_in_use 3000; then
    echo -e "${GREEN}✓ Running${NC}"
    # Try to get process info
    FRONTEND_INFO=$(lsof -i:3000 | grep LISTEN | head -1)
    if [ ! -z "$FRONTEND_INFO" ]; then
        echo "  Process: $FRONTEND_INFO"
    fi
else
    echo -e "${RED}✗ Not running${NC}"
fi

# Check if servers are accessible
echo ""
echo "Server Health:"
# Backend health check
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health | grep -q "200"; then
    echo -e "${GREEN}✓ Backend API responding${NC}"
else
    echo -e "${YELLOW}⚠ Backend API not responding (may still be starting)${NC}"
fi

# Frontend health check
if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q "200"; then
    echo -e "${GREEN}✓ Frontend responding${NC}"
else
    echo -e "${YELLOW}⚠ Frontend not responding (may still be starting)${NC}"
fi

echo ""
echo "Logs available at:"
echo "- Backend: $PROJECT_ROOT/logs/backend.log"
echo "- Frontend: $PROJECT_ROOT/logs/frontend.log"