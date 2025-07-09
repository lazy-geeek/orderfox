#!/bin/bash

# Wait for OrderFox servers to be ready
# Returns immediately once both servers are responding

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Waiting for OrderFox servers to be ready...${NC}"

# Maximum wait time (30 seconds)
MAX_WAIT=30
WAIT_INTERVAL=1
ELAPSED=0

# Function to check if backend is ready
check_backend() {
    curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health | grep -q "200"
}

# Function to check if frontend is ready
check_frontend() {
    curl -s -o /dev/null http://localhost:3000 2>/dev/null
    return $?
}

# Wait for backend
echo -n "Waiting for backend (port 8000)..."
while ! check_backend && [ $ELAPSED -lt $MAX_WAIT ]; do
    echo -n "."
    sleep $WAIT_INTERVAL
    ELAPSED=$((ELAPSED + WAIT_INTERVAL))
done

if check_backend; then
    echo -e " ${GREEN}✓ Ready${NC}"
else
    echo -e " ${RED}✗ Timeout${NC}"
    echo "Backend server is not responding. Check logs at: $PROJECT_ROOT/logs/backend.log"
    exit 1
fi

# Reset timer for frontend
ELAPSED=0

# Wait for frontend
echo -n "Waiting for frontend (port 3000)..."
while ! check_frontend && [ $ELAPSED -lt $MAX_WAIT ]; do
    echo -n "."
    sleep $WAIT_INTERVAL
    ELAPSED=$((ELAPSED + WAIT_INTERVAL))
done

if check_frontend; then
    echo -e " ${GREEN}✓ Ready${NC}"
else
    echo -e " ${RED}✗ Timeout${NC}"
    echo "Frontend server is not responding. Check logs at: $PROJECT_ROOT/logs/frontend.log"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ All servers are ready!${NC}"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"