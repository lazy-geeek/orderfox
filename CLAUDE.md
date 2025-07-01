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
- **backend/app/main.py**: FastAPI application entry point with CORS, exception handling, and startup/shutdown events
- **backend/app/core/**: Core functionality (config, database, logging)
- **backend/app/api/v1/endpoints/**: API endpoints for market data (HTTP/WebSocket) and trading
  - **backend/app/api/v1/endpoints/market_data_ws.py**: WebSocket endpoints with proper Query parameter handling
  - **backend/app/api/v1/endpoints/connection_manager.py**: WebSocket connection management with dynamic limit updates
- **backend/app/services/**: Business logic services (exchange, symbol, trading engine)
- **backend/tests/**: Backend unit tests using pytest

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

### Configuration
- Environment variables loaded from .env file (multiple path detection)
- **Required**: BINANCE_API_KEY, BINANCE_SECRET_KEY
- **Optional**: FIREBASE_CONFIG_JSON, DEBUG, MAX_ORDERBOOK_LIMIT
- **Container Configuration**: DEVCONTAINER_MODE, CONTAINER, HOST, PORT
- **CORS Origins**: Configurable via CORS_ORIGINS environment variable
- **WebSocket URLs**: Configurable Binance API endpoints (BINANCE_WS_BASE_URL, BINANCE_API_BASE_URL)
- Trading mode defaults to paper trading for safety
- **Container Detection**: Automatic detection of Docker/Dev Container environments with adaptive configuration

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

### When Implementing New Features or Changing Code  
- Do not prompt to re-run the backend or frontend, as it is already running in the background and automatically restarts on file changes
- When working in containers, use the appropriate environment variables for container-specific URLs and ports
- Test endpoints are configured to use environment variables for backend URLs to support different deployment scenarios
