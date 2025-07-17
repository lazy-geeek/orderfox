#!/bin/bash

# Restart OrderFox servers with clean logs
# This script stops all servers, cleans logs, and starts them again

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common configuration and functions
source "$SCRIPT_DIR/common.sh"

# Get current timestamp
RESTART_TIME=$(date '+%Y-%m-%d %H:%M:%S')

echo ""
echo -e "${YELLOW}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║           🔄 OrderFox Server Restart Tool 🔄           ║${NC}"
echo -e "${YELLOW}╚════════════════════════════════════════════════════════╝${NC}"
echo -e "${BLUE}📅 Restart initiated at: ${WHITE}$RESTART_TIME${NC}"
echo ""

# Step 1: Stop all servers
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${RED}🛑 Step 1: Stopping all servers...${NC}"
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
STOP_TIME=$(date '+%H:%M:%S')
echo -e "${BLUE}⏱️  Stop initiated at: ${WHITE}$STOP_TIME${NC}"
"$SCRIPT_DIR/stop-servers.sh"
echo ""

# Wait a moment to ensure processes are fully stopped
echo -e "${YELLOW}⏳ Waiting for processes to fully terminate...${NC}"
sleep 2

# Step 2: Clean up log files
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🧹 Step 2: Cleaning up log files...${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
clean_log_files
echo -e "${GREEN}✅ Log files cleaned successfully!${NC}"
echo ""

# Step 3: Start servers again
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🚀 Step 3: Starting servers...${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
START_TIME=$(date '+%H:%M:%S')
echo -e "${BLUE}⏱️  Start initiated at: ${WHITE}$START_TIME${NC}"
"$SCRIPT_DIR/start-servers-bg.sh"

# Calculate elapsed time
END_TIME=$(date '+%Y-%m-%d %H:%M:%S')
ELAPSED=$(($(date -d "$END_TIME" +%s) - $(date -d "$RESTART_TIME" +%s)))

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         ✨ Server Restart Complete! ✨                 ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo -e "${BLUE}📅 Restart completed at: ${WHITE}$END_TIME${NC}"
echo -e "${BLUE}⏱️  Total time elapsed: ${WHITE}${ELAPSED} seconds${NC}"
echo ""
echo -e "${GREEN}💡 The servers are now running with fresh log files.${NC}"
echo -e "${GREEN}🔄 They will auto-reload when you make changes to the code.${NC}"
echo -e "${GREEN}📊 Frontend: ${WHITE}$FRONTEND_URL${NC}"
echo -e "${GREEN}🔧 Backend API: ${WHITE}$BACKEND_URL${NC}"
echo ""