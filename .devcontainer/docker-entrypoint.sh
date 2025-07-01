#!/bin/bash

# Docker entrypoint script for OrderFox Dev Container
set -e

echo "🚀 Starting OrderFox Dev Container..."

# Create necessary directories
mkdir -p /var/log/supervisor
mkdir -p /var/run

# Set up environment
export PYTHONPATH="/workspaces/orderfox:$PYTHONPATH"
export WORKSPACE_FOLDER="/workspaces/orderfox"
export DEVCONTAINER_MODE="true"

# Handle environment setup
if [ -f "/workspaces/orderfox/.env" ]; then
    echo "📝 Loading environment variables from .env..."
    set -a
    source /workspaces/orderfox/.env
    set +a
else
    echo "⚠️  No .env file found, using defaults..."
fi

# Set default development environment variables
export FASTAPI_HOST="${FASTAPI_HOST:-0.0.0.0}"
export FASTAPI_PORT="${FASTAPI_PORT:-8000}"
export VITE_HOST="${VITE_HOST:-0.0.0.0}"
export VITE_PORT="${VITE_PORT:-3000}"
export PYTHONDONTWRITEBYTECODE="${PYTHONDONTWRITEBYTECODE:-1}"
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"
export NODE_ENV="${NODE_ENV:-development}"
export DEBUG="${DEBUG:-true}"

# Health check function
health_check() {
    echo "🔍 Running health checks..."
    
    # Check if ports are available
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  Port 8000 is already in use"
    fi
    
    if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  Port 3000 is already in use"
    fi
    
    # Check if workspace is mounted
    if [ ! -d "/workspaces/orderfox" ]; then
        echo "❌ Workspace directory not found!"
        exit 1
    fi
    
    # Check if backend directory exists
    if [ ! -d "/workspaces/orderfox/backend" ]; then
        echo "❌ Backend directory not found!"
        exit 1
    fi
    
    # Check if frontend directory exists
    if [ ! -d "/workspaces/orderfox/frontend_vanilla" ]; then
        echo "❌ Frontend vanilla directory not found!"
        exit 1
    fi
    
    echo "✅ Health checks passed"
}

# Setup logging
setup_logging() {
    echo "📋 Setting up logging configuration..."
    
    # Ensure log directories exist
    mkdir -p /var/log/supervisor
    
    # Set up log rotation (basic)
    if command -v logrotate &> /dev/null; then
        cat > /etc/logrotate.d/supervisor << EOF
/var/log/supervisor/*.log {
    daily
    missingok
    rotate 7
    compress
    notifempty
    create 644 root root
}
EOF
    fi
    
    echo "✅ Logging configured"
}

# Wait for dependencies function
wait_for_deps() {
    echo "⏳ Waiting for dependencies to be ready..."
    
    # Wait for Python dependencies to be installed
    while [ ! -f "/workspaces/orderfox/backend/requirements.txt" ] || [ ! -d "/usr/local/lib/python3.11/site-packages/fastapi" ]; do
        echo "   Waiting for Python dependencies..."
        sleep 2
    done
    
    # Wait for Node dependencies to be installed
    while [ ! -f "/workspaces/orderfox/frontend_vanilla/package.json" ] || [ ! -d "/workspaces/orderfox/frontend_vanilla/node_modules" ]; do
        echo "   Waiting for Node dependencies..."
        sleep 2
    done
    
    echo "✅ Dependencies ready"
}

# Main execution
main() {
    echo "🏁 Starting main execution..."
    
    # Run health checks
    health_check
    
    # Setup logging
    setup_logging
    
    # Change to workspace directory
    cd /workspaces/orderfox
    
    # Wait for dependencies if needed
    if [ "${WAIT_FOR_DEPS:-true}" = "true" ]; then
        wait_for_deps
    fi
    
    # Start supervisor
    echo "🎯 Starting supervisord..."
    exec /usr/bin/supervisord -c /workspaces/orderfox/.devcontainer/supervisord.conf
}

# Handle signals for graceful shutdown
cleanup() {
    echo "🛑 Received shutdown signal, cleaning up..."
    if [ -f "/var/run/supervisord.pid" ]; then
        kill -TERM $(cat /var/run/supervisord.pid) 2>/dev/null || true
    fi
    exit 0
}

trap cleanup SIGTERM SIGINT

# Execute main function
main "$@"