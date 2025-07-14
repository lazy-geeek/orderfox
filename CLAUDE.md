# CLAUDE.md

This file provides global guidance to Claude Code when working with the OrderFox codebase. For specific frontend or backend guidance, see:
- Backend: `backend/CLAUDE.md`
- Frontend: `frontend_vanilla/CLAUDE.md`

## Project Overview

OrderFox is a cryptocurrency trading application with real-time market data and paper trading capabilities.

**Tech Stack:**
- Frontend: Vanilla JavaScript with Vite and TradingView Lightweight Charts
- Backend: FastAPI + Python with WebSocket support
- Trading: Binance API integration via ccxt
- Real-time: WebSocket connections for live market data
- Charts: TradingView Lightweight Charts for professional candlestick visualization

## Quick Start

```bash
# RECOMMENDED: Smart server management (from root)
npm run dev                    # Checks if servers are running, only starts if needed

# With Docker (from root directory)
docker-compose up --build
```

## Development Workflow

### Working Directory Management
- **Always work from root**: `/home/bail/github/orderfox`
- **Use absolute paths**: Prevents "no such file or directory" errors
- **Frontend path**: `frontend_vanilla/` (with trailing slash)
- **Backend path**: `backend/`

## Server Management

### How It Works
- **Smart detection**: Checks if servers are already running before starting
- **Auto-restart**: File changes trigger automatic server restarts
- **Persistent servers**: Once started, servers keep running between sessions
- **Port management**: Automatic cleanup and detection of existing processes

### For Manual Development

Use `npm run dev` for interactive development:

```bash
npm run dev               # Smart server management - checks if running, starts if needed
```

**Behavior:**
- **If servers not running**: Starts both with live output
- **If servers already running**: Shows status and monitoring mode
- **Use Ctrl+C**: Exit script (servers continue running)

### For Claude Code (Non-blocking)

Claude Code should use these commands to avoid blocking:

```bash
# 🤖 CLAUDE CODE SERVER MANAGEMENT (non-blocking)
npm run dev:bg          # Start servers in background (if not already running)
npm run dev:wait        # Wait for servers to be ready (returns quickly)
npm run dev:status      # Check if servers are running
npm run dev:stop        # Stop background servers
```

### Claude Code Workflow Pattern
```bash
# 1. Start servers (only if not already running - they auto-reload on changes)
npm run dev:bg

# 2. Wait for servers to be ready (returns immediately when ready)
npm run dev:wait

# 3. Do development work - servers auto-reload on file changes
# ... make changes to files ...

# 4. Check status if needed
npm run dev:status

# 5. Servers continue running for future tasks (no need to restart)
```

### Key Benefits for Claude Code
- **No blocking**: Commands return immediately, preventing 2-minute timeouts
- **Smart startup**: Only starts servers if they're not already running
- **Auto-reload preserved**: Servers still auto-reload on file changes
- **Persistent servers**: Servers remain running between tasks
- **Health checks**: `dev:wait` ensures servers are ready before proceeding

### When to Use Each Command
- **`npm run dev`**: For manual/human use only (blocks terminal)
- **`npm run dev:bg`**: Claude Code should use this to start servers
- **`npm run dev:wait`**: Use after `dev:bg` to ensure servers are ready
- **`npm run dev:status`**: Check server health anytime
- **`npm run dev:stop`**: Clean shutdown when needed

### Important Notes
- Servers only need to be started once per session
- They auto-reload on file changes (no restart needed)
- Check `logs/backend.log` and `logs/frontend.log` for debugging
- If ports are blocked, use `npm run dev:stop` first

## Environment Configuration

### Environment Variables
- **`.env` file**: Store local environment variables (git-ignored)
- **`.env.example`**: Template showing required variables (committed to repo)
- **No hardcoded URLs**: All URLs must be configurable via environment
- **Script loading**: Scripts automatically load `.env` if present
- **Override support**: `BACKEND_PORT=8001 ./scripts/check-servers.sh`

### Common Script Architecture
- **`scripts/common.sh`**: Centralized configuration for all scripts
- **Shared functionality**: Environment loading, port checks, health checks
- **DRY principle**: Eliminates ~90 lines of duplicate code across scripts
- **Consistent behavior**: All scripts use same configuration logic

### Required Environment Variables
```bash
# Backend Configuration
BACKEND_PORT=8000
BACKEND_URL=http://localhost:8000
BINANCE_WS_BASE_URL=wss://fstream.binance.com

# Frontend Configuration  
FRONTEND_PORT=3000
FRONTEND_URL=http://localhost:3000
VITE_APP_API_BASE_URL=http://localhost:8000/api/v1  # Production URL
VITE_APP_WS_BASE_URL=ws://localhost:8000/api/v1    # Production WebSocket

# API Keys (optional for demo mode)
BINANCE_API_KEY=your_key
BINANCE_SECRET_KEY=your_secret
```

## Root-Based Command Reference

Quick reference for optimized development workflow:

```bash
# 🚀 PRIMARY DEVELOPMENT COMMANDS (from root)
npm run dev                    # Smart server management (see Server Management section)
npm run dev:bg                 # Claude Code: Start servers in background
npm run dev:status             # Check server status
npm run lint                   # Frontend linting
npm run lint:fix              # Auto-fix frontend linting issues
npm run typecheck              # Backend type checking (Pylance)

# 📦 DEPENDENCY MANAGEMENT
cd /home/bail/github/orderfox/backend && pip install -r requirements.txt           # Backend dependencies
cd /home/bail/github/orderfox/frontend_vanilla && npm install                      # Frontend dependencies

# 🧪 TESTING (use absolute paths)
cd /home/bail/github/orderfox/backend && python -m pytest tests/ -v
cd /home/bail/github/orderfox/frontend_vanilla && npm run test:run

# 🔍 SPECIFIC TESTS
cd /home/bail/github/orderfox/backend && python -m pytest tests/services/test_trade_service.py -v
cd /home/bail/github/orderfox/frontend_vanilla && npm test -- LastTradesDisplay

# 🐳 DOCKER ALTERNATIVE (from root)
docker-compose up --build     # Alternative to npm run dev
```

## Project Structure

```
orderfox/
├── backend/                     # FastAPI backend (see backend/CLAUDE.md)
│   ├── app/
│   │   ├── main.py             # FastAPI entry point
│   │   ├── api/                # API endpoints
│   │   ├── services/           # Business logic
│   │   ├── models/             # Data models
│   │   └── core/               # Config, logging
│   └── tests/                  # Pytest test suite
├── frontend_vanilla/            # Vanilla JS frontend (see frontend_vanilla/CLAUDE.md)
│   ├── src/
│   │   ├── components/         # UI components
│   │   ├── services/           # API & WebSocket services
│   │   ├── config/             # Configuration
│   │   └── store/              # State management
│   ├── tests/                  # Vitest test suite
│   └── main.js                 # App entry point
└── scripts/
    ├── common.sh               # Shared configuration and functions
    ├── check-servers.sh        # Server status checking
    ├── start-servers-bg.sh     # Background server startup
    ├── start-servers-interactive.sh # Interactive server startup
    ├── wait-for-servers.sh     # Wait for servers to be ready
    └── stop-servers.sh         # Stop all servers
```

## Docker Development

```bash
docker-compose up --build    # Build and run both frontend and backend
docker-compose logs -f       # View logs from all containers
docker-compose down          # Stop and remove containers
```

## Configuration

Create `.env` file in root:
```
# API Keys (optional for demo mode)
BINANCE_API_KEY=your_key
BINANCE_SECRET_KEY=your_secret

# Optional settings
MAX_ORDERBOOK_LIMIT=50
DEBUG=true
CORS_ORIGINS=http://localhost:3000
LIQUIDATION_API_BASE_URL=https://api.example.com
```

See backend/CLAUDE.md and frontend_vanilla/CLAUDE.md for component-specific environment variables.

## Important Notes

### Development Tips
- **Smart Server Management**: `npm run dev` checks if servers are already running
- **Auto-restart**: Servers automatically reload when files change
- **Use Absolute Paths**: Always use `/home/bail/github/orderfox/` prefix for directory navigation
- **Debugging**: Check logs in `logs/` directory
- **Environment Variables**: Never hardcode URLs - use environment variables
- **Script Architecture**: All scripts source `common.sh` for shared functionality
- **Configuration Override**: Pass env vars before script: `BACKEND_PORT=8001 ./scripts/check-servers.sh`

### Architecture Principles
- **Thin Client Architecture**: All calculations and business logic in backend, frontend only displays
- **Backend Coordination**: Backend handles all timing, sequencing, and synchronization
- **No Frontend Calculations**: Time ranges, data aggregation, and formatting all happen server-side
- **WebSocket Connections**: Frontend can connect all WebSockets simultaneously, backend handles sequencing

### VS Code Dev Container

```bash
# Open in Dev Container
1. Install "Dev Containers" extension
2. Ctrl+Shift+P → "Dev Containers: Reopen in Container"
3. Services start automatically
```

Container uses `/workspaces/orderfox` as working directory.

**Note**: In Dev Container, replace `/home/bail/github/orderfox` with `/workspaces/orderfox` in all absolute path commands.

## Project Specific Rules

See @CLAUDE-RULES.md for detailed rules for this project.