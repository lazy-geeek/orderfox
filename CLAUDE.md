# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OrderFox is a full-stack cryptocurrency trading application with:
- **Frontend**: Vanilla JavaScript with ES6 modules and Vite (Active)
- **Backend**: FastAPI + Python with WebSocket support
- **Trading**: Binance API integration with paper trading mode
- **Real-time**: WebSocket connections for live market data
- **Container Support**: Docker and VS Code Dev Container configuration

## Development Commands

### Backend (FastAPI)
```bash
# Run backend server
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run backend tests
cd backend
python -m pytest tests/ -v

# Install dependencies
cd backend
pip install -r requirements.txt
```

### Frontend (Vanilla JavaScript - Active)
```bash
# Run development server
cd frontend_vanilla
npm run dev

# Build for production
cd frontend_vanilla
npm run build

# Install dependencies
cd frontend_vanilla
npm install
```

### Legacy Frontend (React - Deprecated)
```bash
# NOTE: This is legacy code for historical reference only
# The frontend/ directory contains the old React implementation
# Use frontend_vanilla/ for all new development
```

### Run Both Frontend and Backend Concurrently
```bash
# Run both frontend and backend concurrently from root
npm run dev
```

### Docker Development
```bash
# Build and run with Docker Compose (recommended for consistent environment)
docker-compose up --build

# Run in detached mode
docker-compose up -d

# Stop containers
docker-compose down

# View logs
docker-compose logs -f
```

### VS Code Dev Container
```bash
# Open in VS Code Dev Container (if using VS Code)
# 1. Install the "Dev Containers" extension
# 2. Open Command Palette (Ctrl+Shift+P)
# 3. Select "Dev Containers: Reopen in Container"
# The container will automatically install dependencies and configure the environment
```

### Full Application Testing
```bash
# Run comprehensive paper trading test
python test_paper_trading.py
```

## Architecture

### Backend Structure
- **backend/app/main.py**: FastAPI application entry point with CORS, exception handling, monitoring, and startup/shutdown events
- **backend/app/core/**: Core functionality (config, database, logging)
- **backend/app/api/v1/endpoints/**: API endpoints for market data (HTTP/WebSocket), trading, and monitoring
  - **backend/app/api/v1/endpoints/market_data_ws.py**: WebSocket endpoints with proper Query parameter handling
  - **backend/app/api/v1/endpoints/connection_manager.py**: WebSocket connection management with dynamic limit updates and backend aggregation
  - **backend/app/api/v1/endpoints/monitoring.py**: Health checks, metrics export (Prometheus/JSON), and performance stats
- **backend/app/services/**: Business logic services including:
  - **orderbook_processor.py**: Server-side order book aggregation with caching
  - **orderbook_manager.py**: Order book lifecycle management and memory optimization
  - **depth_cache_service.py**: Binance DepthCacheManager integration for 500+ depth levels
  - **delta_update_service.py**: Delta compression for bandwidth optimization
  - **batch_update_service.py**: Batching rapid updates for performance
  - **message_serialization_service.py**: JSON/MessagePack serialization with compression
  - **monitoring_service.py**: Comprehensive metrics collection and alerts
  - **exchange_service.py**: Exchange integration with ccxt
  - **symbol_service.py**: Symbol management and validation
  - **trading_engine_service.py**: Paper and live trading execution
- **backend/tests/**: Comprehensive test suite with unit, integration, load, and performance tests

### Frontend Structure (Vanilla JavaScript - Active)
- **frontend_vanilla/src/store/**: State management with subscribe/notify pattern
- **frontend_vanilla/src/components/**: Modular components (OrderBookDisplay, CandlestickChart, etc.)
- **frontend_vanilla/src/services/**: WebSocket service and API client
- **frontend_vanilla/src/layouts/**: Layout components
- **frontend_vanilla/src/style.css**: Global styles with component-specific CSS
- **frontend_vanilla/main.js**: Application entry point with event handling

### Legacy Frontend Structure (React - Deprecated)
- **frontend/src/store/**: Redux store configuration (LEGACY)
- **frontend/src/features/**: Redux slices for market data and trading state management (LEGACY)
- **frontend/src/components/**: React components (LEGACY)
- **frontend/src/services/**: API client and WebSocket service (LEGACY)

### Key Technical Details
- **State Management**: Custom state management with subscribe/notify pattern for reactive updates
- **Real-time Data**: WebSocket connections with automatic reconnection on parameter changes
- **Order Book**: Advanced aggregation with dynamic depth and rounding options
- **API Integration**: Binance API through ccxt library with paper trading mode support
- **Error Handling**: Comprehensive exception handling in FastAPI with proper logging
- **Environment**: Configuration through .env files with automatic path detection

### Recent Improvements
- **WebSocket Parameter Handling**: Fixed backend Query parameter validation for WebSocket endpoints
- **Dynamic Limit Updates**: Connection manager now supports updating orderbook limits without full reconnection
- **Race Condition Prevention**: Frontend properly sequences disconnect → clear → fetch → reconnect operations
- **Data Aggregation**: Improved orderbook aggregation with sufficient raw data (50x multiplier, minimum 500 levels)
- **Automatic Symbol Selection**: First symbol (highest volume) is automatically selected on app load
- **Market Depth Awareness**: Added handling for Binance API orderbook depth limitations (max 5000 entries, limited price range)
- **Docker Integration**: Full Docker and Docker Compose support with multi-stage builds and container orchestration
- **Dev Container Support**: VS Code Dev Container configuration with automatic environment setup and debugging
- **Container-Aware Configuration**: Automatic detection and configuration for Docker/container environments
- **Enhanced Logging**: Structured logging with environment-specific log levels and request timing
- **Static File Serving**: Development mode serves frontend files directly from backend for simplified setup
- **Health Checks**: Container health check endpoints for orchestration and monitoring
- **Dev Container Path Fix**: Fixed inconsistent workspace paths from `/workspace` to `/workspaces/orderfox` for VS Code compatibility
- **Node.js Version Update**: Upgraded from Node.js 18 to Node.js 20 for Vite 7.0.0+ support
- **Script Path Consistency**: Updated all supervisord, post-create, and entrypoint scripts to use consistent paths
- **Windows Host to Container Connectivity**: Implemented Vite proxy configuration to resolve CORS issues when accessing dev container from Windows host browser
- **Frontend Proxy Configuration**: Updated frontend to use relative URLs (`/api/v1`) instead of absolute URLs to leverage Vite's built-in proxy
- **WebSocket Proxy Support**: Added WebSocket proxy configuration for `/api/v1/ws` endpoints to ensure real-time data works across container boundaries
- **VS Code Theme Configuration**: Set Visual Studio Dark as default theme in Dev Container configuration for consistent IDE experience
- **Enhanced Dev Container Documentation**: Comprehensive troubleshooting guide in `.devcontainer/README.md` covering service startup, performance optimization, permission issues, and VS Code extension problems
- **Complete Development Workflow Testing**: Validated full Dev Container functionality including container builds, service startup, hot-reload capabilities, debugging setup, WebSocket connections, and API functionality
- **Server-Side Order Book Aggregation**: Implemented backend aggregation with caching, reducing frontend CPU usage and bandwidth
- **DepthCacheManager Integration**: Added Binance DepthCacheManager for 500+ order book depth levels with automatic synchronization
- **Delta Update Support**: Implemented delta compression to reduce bandwidth usage by 80%+ for order book updates
- **Message Batching**: Added batch update service to optimize rapid order book updates
- **Advanced Serialization**: Support for MessagePack and compression (gzip/zstd) for efficient data transmission
- **Comprehensive Monitoring**: Full monitoring service with Prometheus export, system metrics, alerts, and performance tracking
- **Feature Flags**: Added backend aggregation feature flags for gradual rollout and A/B testing
- **Memory Management**: Implemented order book lifecycle management with LRU eviction and memory limits
- **Performance Validation**: Created performance tests comparing backend vs frontend aggregation, showing significant improvements

### Configuration

Environment variables are organized in a hierarchical structure for clear separation of concerns:

#### .env File Structure
- **Global `.env`**: Project-wide shared settings (API keys, ports, business logic)
- **Backend `backend/.env`**: Backend-specific overrides and settings
- **Frontend `frontend_vanilla/.env`**: Frontend-specific settings (all VITE_ prefixed)

#### Configuration Loading
- **Backend**: Loads global `.env` first, then `backend/.env` for overrides
- **Frontend**: Vite automatically loads `frontend_vanilla/.env` with VITE_ prefix requirement
- **Precedence**: Local settings override global settings

#### Key Variables
- **Global Shared**: FASTAPI_PORT, VITE_PORT, NODE_ENV, DEVCONTAINER_MODE, PYTHONPATH, WORKSPACE_FOLDER
- **Backend Specific**: BINANCE_API_KEY, BINANCE_SECRET_KEY, DEBUG, LOG_LEVEL, CORS_ORIGINS, USE_DEPTH_CACHE_MANAGER, MAX_ORDERBOOK_LIMIT, PAPER_TRADING
- **Frontend Specific**: VITE_APP_API_BASE_URL, VITE_USE_BACKEND_AGGREGATION, VITE_DEBUG_LOGGING
- **Optional Shared**: FIREBASE_PROJECT_ID, FIREBASE_CONFIG_JSON

#### Features
- **Container Detection**: Automatic detection of Docker/Dev Container environments with adaptive configuration
- **Cross-Platform Connectivity**: Special configuration for Windows host to container access using Vite proxy to avoid CORS issues
- **Hierarchical Loading**: Backend loads both global and local .env files for maximum flexibility
- **Trading Safety**: Defaults to paper trading mode for safety

### Known Limitations
- **Orderbook Depth**: Binance API limits orderbook to 5000 entries maximum, sourced from memory
- **Price Range Limitation**: Even with maximum entries, market depth may not span wide enough price ranges for large rounding values
- **Aggregation Reality**: With high rounding values (e.g., $1 for ETH at $3000), actual market orders may only exist within $1-3 price range
- **Not a Bug**: Insufficient orderbook levels at high rounding is a market limitation, not a technical issue
- **Solution**: Use smaller rounding values or accept fewer populated levels for high-value assets

### Testing Strategy
- Backend: pytest with test coverage for all endpoints and services
- Frontend: Manual testing with comprehensive order book functionality
- Integration: Comprehensive paper trading test that validates full application flow

### Model usage
- Use Opus model when in planning mode.
- Use Sonnet model when coding.

### Development Environment Notes
- **Auto-restart**: Backend and frontend automatically restart on file changes in development mode
- **Container Development**: When using Docker or Dev Containers, all services are configured for hot-reload
- **Debugging**: VS Code Dev Container includes debugpy configuration for Python debugging
- **Environment Files**: Use .env.local for local overrides, .env.docker.example for container-specific configuration
- **Static Files**: In development, backend serves frontend static files for simplified single-server setup
- **Container Paths**: Dev Container uses `/workspaces/orderfox` as the working directory (VS Code standard)
- **Node.js Version**: Container uses Node.js 20+ for Vite 7.0.0+ compatibility
- **Path Consistency**: All scripts and configuration files use consistent `/workspaces/orderfox` paths

### Container Connectivity (Windows Host to Dev Container)
- **Problem**: Accessing dev container from Windows host browser causes CORS issues when frontend tries to directly connect to backend
- **Solution**: Vite proxy configuration routes all API and WebSocket requests through the frontend dev server
- **Frontend Configuration**: 
  - `frontend_vanilla/.env` uses relative URLs: `VITE_APP_API_BASE_URL=/api/v1` and `VITE_APP_WS_BASE_URL=/api/v1`
  - `frontend_vanilla/vite.config.js` configures proxy rules for `/api` and `/api/v1/ws` endpoints
- **Network Flow**: Windows Browser → localhost:3000 (Vite) → localhost:8000 (FastAPI backend inside container)
- **Benefits**: Eliminates CORS issues, enables WebSocket connections, maintains hot reload functionality
- **Auto-Configuration**: Dev container post-create script automatically configures frontend for proxy usage

### When Implementing New Features or Changing Code  
- Use context7 mcp server for researching and understanding used modules, libraries, packages and APIs
- Do not prompt to re-run the backend or frontend, as it is already running in the background and automatically restarts on file changes
- Always write unit tests for new features or update them when changing existing functionality

### Container Management
- When working in containers, use the appropriate environment variables for container-specific URLs and ports
- **IMPORTANT**: Always use relative URLs (`/api/v1`) in development mode, not absolute URLs (`http://localhost:8000/api/v1`)
- Test endpoints are configured to use environment variables for backend URLs to support different deployment scenarios
- If experiencing CORS issues, verify that frontend is using Vite proxy configuration with relative URLs
