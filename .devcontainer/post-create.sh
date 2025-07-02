#!/bin/bash

# OrderFox Dev Container Post-Create Script
# This script runs once after the container is created

set -e

echo "🚀 OrderFox Dev Container Post-Create Setup"

# Ensure we're in the workspace directory
cd /workspaces/orderfox

# Install Python backend dependencies (prefer pre-built wheels to avoid compilation)
echo "📦 Installing Python backend dependencies..."
if [ -f "backend/requirements.txt" ]; then
    echo "   Installing from backend/requirements.txt (using pre-built wheels when possible)..."
    pip install --prefer-binary -r backend/requirements.txt
    # Install additional development tools
    pip install --prefer-binary debugpy ipython black pytest-asyncio
    echo "   ✅ Python dependencies installed"
else
    echo "⚠️  backend/requirements.txt not found, skipping Python dependency installation"
fi

# Install frontend dependencies  
echo "📦 Installing frontend dependencies..."
if [ -f "frontend_vanilla/package.json" ]; then
    cd frontend_vanilla
    npm install
    cd ..
    echo "   ✅ Frontend dependencies installed"
else
    echo "⚠️  frontend_vanilla/package.json not found, skipping frontend dependency installation"
fi

# Create frontend .env file
if [ ! -f "frontend_vanilla/.env" ]; then
    echo "Creating frontend_vanilla/.env file..."
    cat > frontend_vanilla/.env << 'EOF'
# =============================================================================
# FRONTEND-SPECIFIC CONFIGURATION
# Frontend service settings (all variables must be prefixed with VITE_)
# =============================================================================

# Backend API Configuration
# Use relative URLs to leverage Vite's proxy configuration and avoid CORS issues
VITE_APP_API_BASE_URL=/api/v1
VITE_APP_WS_BASE_URL=/api/v1

# Frontend Development Features
VITE_USE_BACKEND_AGGREGATION=true
VITE_DEBUG_LOGGING=false
EOF
    echo "   ✅ Created frontend_vanilla/.env for dev container proxy configuration"
else
    echo "   ✅ Frontend .env file already exists"
fi

# Ensure Vite config is properly set up for dev container
echo "🔧 Updating Vite configuration for dev container..."
if [ -f "frontend_vanilla/vite.config.js" ]; then
    # Check if the config already has the correct proxy setup
    if ! grep -q "/api/v1/ws" frontend_vanilla/vite.config.js; then
        echo "   ⚠️  Vite config may need manual WebSocket proxy update"
        echo "     Please ensure '/api/v1/ws' proxy is configured in vite.config.js"
    else
        echo "   ✅ Vite config appears to have correct proxy configuration"
    fi
else
    echo "⚠️  frontend_vanilla/vite.config.js not found"
fi

# Install root development dependencies
echo "📦 Installing root development dependencies..."
if [ -f "package.json" ]; then
    npm install
else
    echo "⚠️  package.json not found, skipping root dependency installation"
fi

# Create hierarchical .env files if they don't exist
echo "🔧 Setting up hierarchical environment configuration..."

# Create global .env file
if [ ! -f ".env" ]; then
    echo "Creating global .env file..."
    cat > .env << 'EOF'
# =============================================================================
# GLOBAL PROJECT CONFIGURATION
# Shared settings used across frontend, backend, and development tools
# =============================================================================

# Development Environment
NODE_ENV=development

# Container & Dev Container Configuration  
DEVCONTAINER_MODE=true
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
WORKSPACE_FOLDER=/workspaces/orderfox
PYTHONPATH=/workspaces/orderfox

# Service Ports (used by both frontend and backend)
FASTAPI_PORT=8000
VITE_PORT=3000

# Development Utilities
WAIT_FOR_DEPS=true
EOF
    echo "✅ Created global .env file"
else
    echo "✅ Global .env file already exists"
fi

# Create backend .env file
if [ ! -f "backend/.env" ]; then
    echo "Creating backend/.env file..."
    
    # Start with base configuration
    cat > backend/.env << 'EOF'
# =============================================================================
# BACKEND-SPECIFIC CONFIGURATION
# Backend service overrides and backend-only settings
# =============================================================================

# Server Configuration
FASTAPI_HOST=0.0.0.0
UVICORN_HOST=0.0.0.0
UVICORN_RELOAD=true
UVICORN_LOG_LEVEL=info

# Development Environment (backend-specific)
ENVIRONMENT=development

# Backend Logging & Debugging
DEBUG=false
LOG_LEVEL=INFO
CONSOLE_LOGGING=true
REQUEST_LOGGING=false

# Backend Features
USE_DEPTH_CACHE_MANAGER=true
SERVE_STATIC_FILES=true
STATIC_FILES_PATH=../frontend_vanilla/dist

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://0.0.0.0:3000

# WebSocket Configuration
WS_HEARTBEAT_INTERVAL=30
WS_TIMEOUT=60

# Binance API Configuration (backend-specific endpoints)
BINANCE_WS_BASE_URL=wss://fstream.binance.com
BINANCE_API_BASE_URL=https://fapi.binance.com

# Trading Configuration (backend business logic)
PAPER_TRADING=true
MAX_ORDERBOOK_LIMIT=5000

# Firebase Configuration (backend-only)
FIREBASE_PROJECT_ID=orderfox-dev
FIREBASE_CONFIG_JSON=

# Development/Testing API Keys (will be overridden by .env.local if it exists)
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET_KEY=your_binance_secret_key_here
EOF

    # If backend/.env.local exists, append real API keys from it
    if [ -f "backend/.env.local" ]; then
        echo "🔑 Found backend/.env.local file, extracting API keys..."
        
        # Extract API keys from backend/.env.local and update backend/.env
        if grep -q "BINANCE_API_KEY=" backend/.env.local; then
            API_KEY=$(grep "^BINANCE_API_KEY=" backend/.env.local | cut -d'=' -f2-)
            sed -i "s/BINANCE_API_KEY=.*/BINANCE_API_KEY=${API_KEY}/" backend/.env
            echo "   ✅ Updated BINANCE_API_KEY from backend/.env.local"
        fi
        
        if grep -q "BINANCE_SECRET_KEY=" backend/.env.local; then
            SECRET_KEY=$(grep "^BINANCE_SECRET_KEY=" backend/.env.local | cut -d'=' -f2-)
            sed -i "s/BINANCE_SECRET_KEY=.*/BINANCE_SECRET_KEY=${SECRET_KEY}/" backend/.env
            echo "   ✅ Updated BINANCE_SECRET_KEY from backend/.env.local"
        fi
        
        # Also apply any other backend overrides from backend/.env.local
        echo "" >> backend/.env
        echo "# Local overrides from backend/.env.local" >> backend/.env
        while IFS= read -r line; do
            if [[ $line =~ ^[A-Z_]+=.* ]] && [[ ! $line =~ ^BINANCE_(API_KEY|SECRET_KEY)= ]]; then
                echo "$line" >> backend/.env
                echo "   ✅ Applied backend override: $(echo $line | cut -d'=' -f1)"
            fi
        done < backend/.env.local
        
    else
        echo "⚠️  backend/.env.local not found - using placeholder API keys"
        echo "   Create backend/.env.local with real API keys (see backend/.env.local.example)"
    fi
    
    echo "✅ Created backend/.env file"
else
    echo "✅ Backend .env file already exists"
fi

# Make scripts executable
echo "🔧 Setting up script permissions..."
chmod +x .devcontainer/post-create.sh
chmod +x .devcontainer/docker-entrypoint.sh
chmod +x .devcontainer/setup-zsh.sh

# Setup zsh configuration to match WSL
echo "🐚 Setting up zsh configuration..."
bash .devcontainer/setup-zsh.sh

# Create temp directories for development
echo "📁 Creating development directories..."
mkdir -p logs
mkdir -p data
mkdir -p tmp

# Set up VS Code debugging configuration
echo "🐛 Setting up VS Code debugging configuration..."
mkdir -p .vscode

# Create launch.json for debugging
cat > .vscode/launch.json << 'EOF'
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "backend.app.main:app",
                "--host", "0.0.0.0",
                "--port", "8000",
                "--reload"
            ],
            "cwd": "${workspaceFolder}",
            "env": {
                "PYTHONPATH": "${workspaceFolder}",
                "DEVCONTAINER_MODE": "true"
            },
            "console": "integratedTerminal",
            "justMyCode": false
        },
        {
            "name": "Python: Attach to FastAPI",
            "type": "python", 
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5678
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "/workspaces/orderfox"
                }
            ]
        },
        {
            "name": "Frontend: Vite",
            "type": "chrome",
            "request": "launch",
            "url": "http://localhost:3000",
            "webRoot": "${workspaceFolder}/frontend_vanilla",
            "sourceMaps": true,
            "userDataDir": "${workspaceFolder}/.vscode/chrome-debug-profile"
        },
        {
            "name": "Debug Vite Dev Server",
            "type": "node",
            "request": "launch",
            "program": "${workspaceFolder}/frontend_vanilla/node_modules/.bin/vite",
            "args": ["dev", "--host", "0.0.0.0", "--port", "3000"],
            "cwd": "${workspaceFolder}/frontend_vanilla",
            "env": {
                "NODE_ENV": "development"
            },
            "console": "integratedTerminal",
            "skipFiles": [
                "<node_internals>/**"
            ]
        },
        {
            "name": "Attach to Chrome (Frontend)",
            "type": "chrome",
            "request": "attach",
            "port": 9222,
            "url": "http://localhost:3000",
            "webRoot": "${workspaceFolder}/frontend_vanilla"
        }
    ],
    "compounds": [
        {
            "name": "Full Stack Debug",
            "configurations": [
                "Python: FastAPI",
                "Debug Vite Dev Server"
            ]
        }
    ]
}
EOF

echo "✅ Created .vscode/launch.json with Python FastAPI and JavaScript debugging configurations"

# Create workspace settings
cat > .vscode/settings.json << 'EOF'
{
    "python.defaultInterpreterPath": "/usr/local/bin/python",
    "python.analysis.typeCheckingMode": "basic",
    "python.analysis.typeCheckingMode": "basic",
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length", "88"],
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "python.testing.pytestArgs": [
        "backend/tests"
    ],
    "typescript.preferences.quoteStyle": "single",
    "javascript.preferences.quoteStyle": "single",
    "javascript.format.semicolons": "remove",
    "typescript.format.semicolons": "remove",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.fixAll.eslint": "explicit",
        "source.organizeImports": "explicit"
    },
    "files.associations": {
        "*.py": "python",
        "*.js": "javascript",
        "*.json": "jsonc",
        "*.md": "markdown"
    },
    "terminal.integrated.defaultProfile.linux": "zsh",
    "terminal.integrated.profiles.linux": {
        "zsh": {
            "path": "/usr/bin/zsh",
            "env": {
                "PYTHONPATH": "/workspaces/orderfox"
            }
        },
        "bash": {
            "path": "/bin/bash",
            "env": {
                "PYTHONPATH": "/workspaces/orderfox"
            }
        }
    },
    "emmet.includeLanguages": {
        "javascript": "javascriptreact"
    },
    "[python]": {
        "editor.defaultFormatter": "ms-python.black-formatter",
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.organizeImports": "explicit"
        }
    },
    "[javascript]": {
        "editor.defaultFormatter": "esbenp.prettier-vscode"
    },
    "[json]": {
        "editor.defaultFormatter": "esbenp.prettier-vscode"
    },
    "python.terminal.activateEnvironment": true,
    "python.envFile": "${workspaceFolder}/.env"
}
EOF

echo "✅ Created .vscode/settings.json with Python and JavaScript language server configuration"

# Verify Python installation
echo "🔍 Verifying Python installation..."
python --version
pip --version

# Verify Node.js installation
echo "🔍 Verifying Node.js installation..."
node --version
npm --version

# Install Claude Code CLI via npm (pre-compiled binary)
echo "🤖 Installing Claude Code CLI..."
# Set up user-writable npm prefix to avoid permissions issues
mkdir -p ~/.npm-global
npm config set prefix ~/.npm-global
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.zshrc
export PATH=~/.npm-global/bin:$PATH
npm install -g @anthropic-ai/claude-code
echo "✅ Claude Code CLI installed"

# Install any VS Code extensions that may have failed during initial setup
echo "🔧 Installing any missing VS Code extensions..."
if command -v code >/dev/null 2>&1; then
    # Extensions that commonly fail during bulk installation
    EXTENSIONS=(
        "ms-vscode.vscode-json"
        "anthropic.claude-vscode" 
        "oleg-shilo.linesight"
        "ethanfann.restore-terminals"
    )
    
    for ext in "${EXTENSIONS[@]}"; do
        if ! code --list-extensions | grep -q "$ext"; then
            echo "Installing missing extension: $ext"
            code --install-extension "$ext" --force || echo "Failed to install $ext (will retry on VS Code startup)"
        fi
    done
else
    echo "VS Code CLI not available in container - extensions will install on VS Code startup"
fi

echo "✅ Post-create setup completed successfully!"
echo ""
echo "🔧 Dev Container Configuration Applied:"
echo "   • Hierarchical .env configuration: global (.env), backend (backend/.env), frontend (frontend_vanilla/.env)"
echo "   • Frontend configured to use relative URLs (/api/v1) for Vite proxy"
echo "   • WebSocket connections routed through Vite proxy to avoid CORS issues"
echo "   • Environment variables set for Windows host → container connectivity"
echo "   • HMR (Hot Module Reload) optimized for container environment"
echo ""
echo "📋 Next steps:"
echo "1. (Optional) Create backend/.env.local with real API keys (see backend/.env.local.example)"
echo "2. Services will start automatically via supervisord"
echo "3. Access the application:"
echo "   • Frontend: http://localhost:3000"
echo "   • Backend API: http://localhost:8000"
echo "   • API Documentation: http://localhost:8000/docs"
echo ""
echo "🎯 Useful commands:"
echo "   • npm run dev                 - Start both frontend and backend"
echo "   • supervisorctl status        - Check service status"
echo "   • supervisorctl restart all   - Restart all services"
echo "   • tail -f /var/log/supervisor/*.log - View logs"
echo "   • claude                      - Launch Claude Code CLI"
echo ""
echo "🌐 Network Configuration:"
echo "   • Frontend uses Vite proxy for API calls to avoid CORS issues"
echo "   • All requests from browser go through localhost:3000"
echo "   • Vite automatically forwards API requests to backend (localhost:8000)"
echo "   • WebSocket connections also proxied through Vite server"
echo ""
echo "🔑 API Key Management:"
echo "   • Create backend/.env.local for real API keys (excluded from git)"
echo "   • backend/.env.local.example shows the format"
echo "   • Dev container automatically applies keys from backend/.env.local if present"
echo "   • Fallback to placeholder keys if backend/.env.local doesn't exist"
echo ""