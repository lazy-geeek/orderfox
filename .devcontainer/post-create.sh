#!/bin/bash

# OrderFox Dev Container Post-Create Script
# This script runs once after the container is created

set -e

echo "🚀 OrderFox Dev Container Post-Create Setup"

# Ensure we're in the workspace directory
cd /workspaces/orderfox

# Install Python backend dependencies
echo "📦 Installing Python backend dependencies..."
if [ -f "backend/requirements.txt" ]; then
    echo "   Installing from backend/requirements.txt..."
    pip install -r backend/requirements.txt
    # Install additional development tools
    pip install debugpy ipython black flake8 mypy pytest-asyncio
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
WORKSPACE_FOLDER=/workspace
EOF
    fi
else
    echo "✅ .env file already exists"
fi

# Make scripts executable
echo "🔧 Setting up script permissions..."
chmod +x .devcontainer/post-create.sh
chmod +x .devcontainer/docker-entrypoint.sh

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
                    "remoteRoot": "/workspace"
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
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
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
    "terminal.integrated.defaultProfile.linux": "bash",
    "terminal.integrated.profiles.linux": {
        "bash": {
            "path": "/bin/bash",
            "env": {
                "PYTHONPATH": "/workspace"
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

echo "✅ Post-create setup completed successfully!"
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
echo "   • supervisorctl status        - Check service status"
echo "   • supervisorctl restart all   - Restart all services"
echo "   • tail -f /var/log/supervisor/*.log - View logs"
echo ""