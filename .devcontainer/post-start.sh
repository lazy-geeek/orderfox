#!/bin/bash

# OrderFox Dev Container Post-Start Script
# This script runs every time the container starts

set -e

echo "🔄 OrderFox Dev Container Post-Start Setup"

# Ensure we're in the workspace directory
cd /workspaces/orderfox

# Clear any VS Code workspace state to ensure folder mode
echo "🔧 Configuring VS Code to open as folder..."
if [ -d "/home/vscode/.vscode-server" ] || [ -d "/home/vscode/.vscode-server-insiders" ]; then
    # Remove any cached workspace references
    find /home/vscode/.vscode-server* -name "workspace.json" -type f -exec rm -f {} \; 2>/dev/null || true
    find /home/vscode/.vscode-server* -name "*.code-workspace" -type f -exec rm -f {} \; 2>/dev/null || true
    
    # Remove any workspace storage that might contain workspace references
    rm -rf /home/vscode/.vscode-server*/data/User/workspaceStorage/*orderfox* 2>/dev/null || true
    rm -rf /home/vscode/.vscode-server*/data/User/globalStorage/*orderfox* 2>/dev/null || true
    
    echo "   ✅ Cleared VS Code workspace cache"
fi

# Remove any workspace files that might exist in the project
find /workspaces/orderfox -name "*.code-workspace" -type f -exec rm -f {} \; 2>/dev/null || true
if [ $? -eq 0 ]; then
    echo "   ✅ Removed any workspace files from project"
fi

# Create a .gitignore entry to prevent workspace files from being created
if ! grep -q "*.code-workspace" /workspaces/orderfox/.gitignore 2>/dev/null; then
    echo "*.code-workspace" >> /workspaces/orderfox/.gitignore
    echo "   ✅ Added *.code-workspace to .gitignore"
fi

# Set VS Code to prefer opening folders
if [ -d "/home/vscode/.vscode-server" ] || [ -d "/home/vscode/.vscode-server-insiders" ]; then
    # Create VS Code user settings to disable workspace trust prompt
    mkdir -p /home/vscode/.vscode-server/data/Machine 2>/dev/null || true
    mkdir -p /home/vscode/.vscode-server-insiders/data/Machine 2>/dev/null || true
    
    # Add settings to prevent workspace mode
    echo '{"security.workspace.trust.enabled": false}' > /home/vscode/.vscode-server/data/Machine/settings.json 2>/dev/null || true
    echo '{"security.workspace.trust.enabled": false}' > /home/vscode/.vscode-server-insiders/data/Machine/settings.json 2>/dev/null || true
fi

# Check if services are already running
echo "🔍 Checking service status..."

# Function to check if a port is in use
check_port() {
    local port=$1
    local service=$2
    if netstat -tuln | grep -q ":$port "; then
        echo "✅ $service is running on port $port"
        return 0
    else
        echo "❌ $service is not running on port $port"
        return 1
    fi
}

# Check service ports
check_port 8000 "FastAPI Backend" || echo "   Will be started by supervisord"
check_port 3000 "Vite Dev Server" || echo "   Will be started by supervisord"

# Check supervisord status
echo ""
echo "🔍 Supervisord service status:"
if command -v supervisorctl &> /dev/null; then
    supervisorctl status 2>/dev/null || echo "   Supervisord not yet running (will start with docker-entrypoint.sh)"
else
    echo "   Supervisord not available yet"
fi

# Display helpful information
echo ""
echo "🎯 OrderFox Development Environment Ready!"
echo ""
echo "📊 Available Services:"
echo "  • Frontend (Vite):     http://localhost:3000"
echo "  • FastAPI Backend:     http://localhost:8000"
echo "  • API Documentation:   http://localhost:8000/docs"
echo "  • WebSocket Endpoint:  ws://localhost:8000/ws"
echo ""
echo "🚀 Quick Start Commands:"
echo "  supervisorctl status           # Check service status"
echo "  supervisorctl restart all      # Restart all services"
echo "  supervisorctl restart fastapi  # Restart backend only"
echo "  supervisorctl restart frontend # Restart frontend only"
echo "  cd backend && python -m pytest tests/ -v  # Run Python tests"
echo ""
echo "🔧 Development Tools:"
echo "  • Python:     $(python --version 2>/dev/null || echo 'Not available yet')"
echo "  • Node.js:    $(node --version 2>/dev/null || echo 'Not available yet')"
echo "  • pip:        $(pip --version 2>/dev/null | head -n1 || echo 'Not available yet')"
echo ""
echo "📋 Log Files:"
echo "  • Supervisord:  /var/log/supervisord.log"
echo "  • FastAPI:      /var/log/supervisor/fastapi.log"
echo "  • Frontend:     /var/log/supervisor/frontend.log"
echo ""
echo "💡 Tips:"
echo "  • All source code changes will be automatically reflected"
echo "  • Use the integrated terminal for running commands"
echo "  • Services auto-restart on code changes"
echo "  • Update .env file with your Binance API credentials"
echo "  • Use 'tail -f /var/log/supervisor/*.log' to follow logs"
echo ""

# Create log files if they don't exist (supervisord will create them, but good to have)
mkdir -p logs
mkdir -p /var/log/supervisor 2>/dev/null || true

echo "✅ Post-start setup completed!"