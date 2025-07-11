#!/bin/bash

# Wait for OrderFox servers to be ready
# Returns immediately once both servers are responding

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common configuration and functions
source "$SCRIPT_DIR/common.sh"

echo -e "${YELLOW}Waiting for OrderFox servers to be ready...${NC}"

# Maximum wait time (30 seconds)
MAX_WAIT=30
WAIT_INTERVAL=1
ELAPSED=0

# Wrapper functions for compatibility
check_backend() {
    check_backend_health
}

check_frontend() {
    check_frontend_health
}

# Wait for backend
echo -n "Waiting for backend (port $BACKEND_PORT)..."
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
echo -n "Waiting for frontend (port $FRONTEND_PORT)..."
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
echo "Backend: $BACKEND_URL"
echo "Frontend: $FRONTEND_URL"