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

# Configure frontend environment for dev container
echo "🔧 Configuring frontend environment for dev container..."
if [ -f "frontend_vanilla/.env" ]; then
    # Update frontend .env to use relative URLs for Vite proxy (avoids CORS issues in dev container)
    cat > frontend_vanilla/.env << 'EOF'
# Frontend Configuration
# Environment variables must be prefixed with VITE_ to be accessible in the browser
# Use relative URLs to leverage Vite's proxy configuration and avoid CORS issues
VITE_APP_API_BASE_URL=/api/v1
VITE_APP_WS_BASE_URL=/api/v1
EOF
    echo "   ✅ Updated frontend_vanilla/.env for dev container proxy configuration"
else
    echo "⚠️  frontend_vanilla/.env not found, creating default configuration"
    cat > frontend_vanilla/.env << 'EOF'
# Frontend Configuration
# Environment variables must be prefixed with VITE_ to be accessible in the browser
# Use relative URLs to leverage Vite's proxy configuration and avoid CORS issues
VITE_APP_API_BASE_URL=/api/v1
VITE_APP_WS_BASE_URL=/api/v1
EOF
    echo "   ✅ Created frontend_vanilla/.env with dev container proxy configuration"
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

# Create .env file if it doesn't exist
echo "🔧 Setting up environment configuration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.docker.example" ]; then
        cp .env.docker.example .env
        echo "✅ Created .env from .env.docker.example"
    elif [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ Created .env from .env.example"
    else
        echo "⚠️  .env.docker.example not found, creating basic .env file"
        cat > .env << 'EOF'
# OrderFox Development Environment
NODE_ENV=development
DEVCONTAINER_MODE=true

# Binance API Configuration (Required for trading functionality)
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET_KEY=your_binance_secret_key_here

# Development Settings
DEBUG=true
MAX_ORDERBOOK_LIMIT=5000
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1

# Container-specific URLs
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
VITE_HOST=0.0.0.0
VITE_PORT=3000
WORKSPACE_FOLDER=/workspaces/orderfox
EOF
    fi
else
    echo "✅ .env file already exists"
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
echo "   • Frontend configured to use relative URLs (/api/v1) for Vite proxy"
echo "   • WebSocket connections routed through Vite proxy to avoid CORS issues"
echo "   • Environment variables set for Windows host → container connectivity"
echo "   • HMR (Hot Module Reload) optimized for container environment"
echo ""
echo "📋 Next steps:"
echo "1. Update .env file with your Binance API credentials"
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