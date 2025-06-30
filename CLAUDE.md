# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OrderFox is a full-stack cryptocurrency trading application with:
- **Frontend**: Vanilla JavaScript with ES6 modules and Vite (Active - Migrated to PHP Backend)
- **Frontend Vanilla**: Original frontend implementation (Legacy - Preserved for reference)
- **Backend**: FastAPI + Python with WebSocket support (Legacy)
- **Backend PHP**: Slim Framework + PHP with Ratchet WebSocket support (Active)
- **Trading**: Binance API integration with paper trading mode
- **Real-time**: WebSocket connections for live market data

## Migration Status

The frontend has been successfully migrated from the FastAPI backend to the PHP backend:
- **Phase 0-4**: ✅ Complete - Frontend copied and fully migrated to PHP backend
- **Phase 5**: 🔄 In Progress - Documentation and cleanup
- **Legacy Preservation**: frontend_vanilla/ directory preserved untouched for reference

## Development Setup

### Prerequisites
- PHP 8.1+ with Composer
- Node.js 18+ with npm
- Valid Binance API credentials
- Git
- Docker (optional, for containerized deployment)
- Firebase CLI (optional, for Firebase integration)

### Initial Setup
1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd orderfox
   ```

2. **Setup environment variables**:
   ```bash
   # Copy and configure environment file
   cp .env.example .env
   # Edit .env with your configuration:
   # BINANCE_API_KEY=your_api_key
   # BINANCE_SECRET_KEY=your_secret_key
   # FIREBASE_PROJECT_ID=your_firebase_project_id (optional)
   # FIREBASE_CONFIG_JSON=path_to_firebase_service_account.json (optional)
   ```

3. **Install PHP backend dependencies**:
   ```bash
   cd backend_php
   composer install
   cd ..
   ```

4. **Install frontend dependencies**:
   ```bash
   cd frontend
   npm install
   cd ..
   ```

5. **Install root development dependencies**:
   ```bash
   npm install
   ```

6. **Install all dependencies at once (alternative)**:
   ```bash
   npm run install:all
   ```

### Development Commands

#### Quick Start (Recommended)
```bash
# Run both frontend and PHP backend concurrently
npm run dev
```
This command starts:
- PHP HTTP server on port 8000
- PHP WebSocket server on port 8080  
- Frontend development server on port 3000

#### Container Development Mode
```bash
# Run services in container-compatible mode (binds to 0.0.0.0)
npm run dev:container
```

#### Individual Services
```bash
# Run only backend services (PHP + WebSocket)
npm run dev:backend

# Run only frontend
npm run dev:frontend
```

#### Individual Services

### Backend PHP (Active)
```bash
# Run backend server
cd backend_php
php -S localhost:8000 -t public

# Run WebSocket server (in separate terminal)
cd backend_php
php websocket_server.php

# Run all tests
npm run test:backend

# Run unit tests only
npm run test:unit

# Run integration tests only
npm run test:integration

# Alternative: Direct PHPUnit commands
cd backend_php
./vendor/bin/phpunit tests/Unit/ --verbose
./vendor/bin/phpunit tests/Integration/ --verbose

# Install dependencies
cd backend_php
composer install
```

### Backend (FastAPI - Legacy)
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
# Run development server (uses PHP backend)
cd frontend
npm run dev

# Build for production
cd frontend
npm run build

# Install dependencies
cd frontend
npm install
```

### Frontend Vanilla (Original Implementation - Legacy)
```bash
# NOTE: This is the original frontend implementation preserved for reference
# The frontend_vanilla/ directory contains the original FastAPI-compatible frontend
# Use frontend/ for all new development (PHP backend compatible)
cd frontend_vanilla
npm run dev  # For legacy testing only
```

### Legacy Frontend (React - Deprecated)
```bash
# NOTE: This is legacy code for historical reference only
# The frontend/ directory now contains the PHP-compatible vanilla JS implementation
# Use frontend/ for all new development
```

### Run Both Frontend and PHP Backend Concurrently
```bash
# Run both frontend (PHP-compatible) and PHP backend concurrently from root
npm run dev
```

### Verification Commands
```bash
# Test PHP backend connectivity
curl http://localhost:8000/api/v1/market-data/symbols

# Test WebSocket server connectivity (requires wscat: npm install -g wscat)
wscat -c ws://localhost:8080/ws/ticker/BTCUSDT

# Run migration verification tests
cd frontend
npm run dev  # Verify frontend works with PHP backend

# Test all backend endpoints
curl http://localhost:8000/api/v1/market-data/symbols
curl http://localhost:8000/api/v1/market-data/orderbook/BTCUSDT?limit=10
curl http://localhost:8000/api/v1/market-data/candles/BTCUSDT/1m?limit=10
```

### Migration Status Check
```bash
# Verify frontend is using PHP backend
cd frontend/src/config
cat env.js  # Should show API_BASE_URL: 'http://localhost:8000' and WS_BASE_URL: 'ws://localhost:8080'

# Verify legacy frontend is preserved
ls -la frontend_vanilla/  # Should contain original implementation

# Check if services are running
curl -s http://localhost:8000/api/v1/market-data/symbols | jq '.success'  # Should return true
```

### Full Application Testing
```bash
# Run comprehensive paper trading test
python test_paper_trading.py
```

## Docker Integration

The project includes comprehensive Docker support with optimized .dockerignore configuration:

### Docker Features
- **Multi-stage builds**: Optimized for production deployments
- **Legacy exclusion**: Automatically excludes legacy directories (backend/, frontend_vanilla/)
- **Firebase ready**: Configured for Firebase integration with proper file exclusions
- **Development mode**: Container-compatible development environment

### Container Environment Variables
```bash
# Set these in .env for container deployment
CONTAINER_PHP_HOST=0.0.0.0
CONTAINER_PHP_PORT=8000
CONTAINER_WEBSOCKET_HOST=0.0.0.0
CONTAINER_WEBSOCKET_PORT=8080
CONTAINER_FRONTEND_HOST=0.0.0.0
CONTAINER_FRONTEND_PORT=3000
```

### Running in Container Mode
```bash
# Use container-compatible development mode
npm run dev:container
```

## Firebase Integration

The project includes Firebase configuration files and environment support:

### Firebase Files
- **firebase.json**: Firebase project configuration
- **firestore.rules**: Firestore security rules
- **firestore.indexes.json**: Firestore database indexes
- **backend_php/FIREBASE_INTEGRATION.md**: PHP backend Firebase integration guide
- **frontend/FIREBASE_INTEGRATION.md**: Frontend Firebase integration guide

### Firebase Environment Variables
```bash
# Firebase project configuration
FIREBASE_PROJECT_ID=your_firebase_project_id
FIREBASE_CONFIG_JSON=path_to_firebase_service_account.json

# Firebase Emulator configuration (for local development)
FIREBASE_EMULATOR_HOST=localhost
FIRESTORE_EMULATOR_PORT=8080
FIREBASE_AUTH_EMULATOR_PORT=9099
FIREBASE_FUNCTIONS_EMULATOR_PORT=5001
FIREBASE_HOSTING_EMULATOR_PORT=5000
```

### Firebase Setup
```bash
# Install Firebase CLI (if not already installed)
npm install -g firebase-tools

# Login to Firebase
firebase login

# Initialize Firebase in your project
firebase init

# Start Firebase emulators for local development
firebase emulators:start
```

## Architecture

### Backend PHP Structure (Active)
- **backend_php/public/index.php**: Slim Framework application entry point with CORS and routing
- **backend_php/src/Core/**: Core functionality (config, logger)
- **backend_php/src/Api/V1/Controllers/**: REST API controllers for market data endpoints
- **backend_php/src/Api/V1/DTOs/**: Data Transfer Objects for structured responses
- **backend_php/src/Api/V1/Formatters/**: Response formatting utilities
- **backend_php/src/Services/**: Business logic services (exchange, symbol, connection manager)
- **backend_php/src/WebSocket/**: WebSocket server implementation with Ratchet
  - **backend_php/src/WebSocket/Handlers/**: WebSocket message handlers for different data types
- **backend_php/tests/Unit/**: PHPUnit unit tests for all components
- **backend_php/tests/Integration/**: PHPUnit integration tests for API and WebSocket functionality
- **backend_php/websocket_server.php**: WebSocket server entry point

### Backend Structure (FastAPI - Legacy)
- **backend/app/main.py**: FastAPI application entry point with CORS, exception handling, and startup/shutdown events
- **backend/app/core/**: Core functionality (config, database, logging)
- **backend/app/api/v1/endpoints/**: API endpoints for market data (HTTP/WebSocket) and trading
  - **backend/app/api/v1/endpoints/market_data_ws.py**: WebSocket endpoints with proper Query parameter handling
  - **backend/app/api/v1/endpoints/connection_manager.py**: WebSocket connection management with dynamic limit updates
- **backend/app/services/**: Business logic services (exchange, symbol, trading engine)
- **backend/tests/**: Backend unit tests using pytest

### Frontend Structure (Vanilla JavaScript - Active, PHP Backend Compatible)
- **frontend/src/store/**: State management with subscribe/notify pattern (migrated to PHP endpoints)
- **frontend/src/components/**: Modular components (OrderBookDisplay, CandlestickChart, etc.)
- **frontend/src/services/**: WebSocket service and API client (configured for PHP backend)
- **frontend/src/layouts/**: Layout components
- **frontend/src/config/**: Environment configuration (PHP backend URLs)
- **frontend/src/style.css**: Global styles with component-specific CSS
- **frontend/main.js**: Application entry point with event handling

### Frontend Vanilla Structure (Legacy - FastAPI Compatible)
- **frontend_vanilla/src/store/**: Original state management (FastAPI endpoints)
- **frontend_vanilla/src/components/**: Original modular components
- **frontend_vanilla/src/services/**: Original WebSocket service and API client (FastAPI backend)
- **frontend_vanilla/src/layouts/**: Original layout components
- **frontend_vanilla/src/style.css**: Original global styles
- **frontend_vanilla/main.js**: Original application entry point

### Legacy Frontend Structure (React - Deprecated)
- **frontend/src/store/**: Redux store configuration (LEGACY)
- **frontend/src/features/**: Redux slices for market data and trading state management (LEGACY)
- **frontend/src/components/**: React components (LEGACY)
- **frontend/src/services/**: API client and WebSocket service (LEGACY)

## Migration Details

### Frontend to PHP Backend Migration
The frontend has been successfully migrated from FastAPI to PHP backend while preserving the original implementation:

**Migration Phases Completed:**
- **Phase 0**: ✅ Frontend directory setup - Copied frontend_vanilla to frontend
- **Phase 1**: ✅ API endpoint migration - Updated all HTTP endpoints to PHP format
- **Phase 2**: ✅ WebSocket configuration - Migrated to PHP WebSocket server (port 8080)
- **Phase 3**: ✅ Message format alignment - Ensured compatibility between PHP and frontend
- **Phase 4**: ✅ Comprehensive testing - Verified all functionality works correctly
- **Phase 5**: 🔄 Documentation and cleanup - In progress

**Key Changes Made:**
- **API Endpoints**: Updated from `/api/v1/` to `/api/v1/market-data/` structure
- **Response Format**: Added handling for PHP backend response wrapper `{success, data, timestamp}`
- **WebSocket URLs**: Changed from port 8000 to port 8080, updated URL patterns
- **Environment Config**: Added separate WebSocket port configuration
- **Error Handling**: Enhanced error handling for PHP backend responses

**Migration Benefits:**
- ✅ Maintained full functionality with PHP backend
- ✅ Preserved original frontend_vanilla as legacy backup
- ✅ No performance regression detected
- ✅ Improved error handling and response structure
- ✅ Better separation of HTTP (8000) and WebSocket (8080) services

### Key Technical Details
- **State Management**: Custom state management with subscribe/notify pattern for reactive updates
- **Real-time Data**: WebSocket connections with automatic reconnection on parameter changes
- **Order Book**: Advanced aggregation with dynamic depth and rounding options
- **API Integration**: Binance API through ccxt library with paper trading mode support
- **Error Handling**: Comprehensive exception handling with proper logging (both FastAPI and PHP)
- **Environment**: Configuration through .env files with automatic path detection
- **Backend Compatibility**: Frontend supports both FastAPI (legacy) and PHP (active) backends

### Recent Improvements
- **WebSocket Parameter Handling**: Fixed backend Query parameter validation for WebSocket endpoints
- **Dynamic Limit Updates**: Connection manager now supports updating orderbook limits without full reconnection
- **Race Condition Prevention**: Frontend properly sequences disconnect → clear → fetch → reconnect operations
- **Data Aggregation**: Improved orderbook aggregation with sufficient raw data (50x multiplier, minimum 500 levels)
- **Automatic Symbol Selection**: First symbol (highest volume) is automatically selected on app load
- **Market Depth Awareness**: Added handling for Binance API orderbook depth limitations (max 5000 entries, limited price range)

### Configuration
- Environment variables loaded from .env file (multiple path detection)
- **Required**: BINANCE_API_KEY, BINANCE_SECRET_KEY
- **Optional**: 
  - FIREBASE_PROJECT_ID, FIREBASE_CONFIG_JSON (Firebase integration)
  - DEBUG, ENVIRONMENT, LOG_LEVEL (Development/logging)
  - MAX_ORDERBOOK_LIMIT (Trading limits)
  - Container variables (CONTAINER_*_HOST, CONTAINER_*_PORT)
  - Firebase Emulator variables (FIREBASE_*_EMULATOR_PORT)
- Trading mode defaults to paper trading for safety

### Known Limitations
- **Orderbook Depth**: Binance API limits orderbook to 5000 entries maximum, sourced from memory
- **Price Range Limitation**: Even with maximum entries, market depth may not span wide enough price ranges for large rounding values
- **Aggregation Reality**: With high rounding values (e.g., $1 for ETH at $3000), actual market orders may only exist within $1-3 price range
- **Not a Bug**: Insufficient orderbook levels at high rounding is a market limitation, not a technical issue
- **Solution**: Use smaller rounding values or accept fewer populated levels for high-value assets

## API Documentation

### PHP Backend Endpoints (Active)

#### HTTP REST API (Port 8000)
Base URL: `http://localhost:8000/api/v1/market-data/`

**Response Format:**
All PHP backend responses follow this structure:
```json
{
  "success": true,
  "data": { /* actual data */ },
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

**Endpoints:**

1. **GET /api/v1/market-data/symbols**
   - **Description**: Get all available trading symbols
   - **Response**: 
   ```json
   {
     "success": true,
     "data": {
       "symbols": [
         {"symbol": "BTCUSDT", "baseAsset": "BTC", "quoteAsset": "USDT"},
         {"symbol": "ETHUSDT", "baseAsset": "ETH", "quoteAsset": "USDT"}
       ]
     },
     "timestamp": "2024-01-01T12:00:00.000Z"
   }
   ```

2. **GET /api/v1/market-data/orderbook/{symbol}?limit={limit}**
   - **Description**: Get orderbook data for a symbol
   - **Parameters**: 
     - `symbol`: Trading pair (e.g., BTCUSDT)
     - `limit`: Number of levels (optional, default: 100)
   - **Response**:
   ```json
   {
     "success": true,
     "data": {
       "orderbook": {
         "symbol": "BTCUSDT",
         "bids": [["43000.00", "1.50000000"]],
         "asks": [["43100.00", "2.30000000"]],
         "lastUpdateId": 123456789
       }
     },
     "timestamp": "2024-01-01T12:00:00.000Z"
   }
   ```

3. **GET /api/v1/market-data/candles/{symbol}/{timeframe}?limit={limit}**
   - **Description**: Get candlestick data for a symbol
   - **Parameters**:
     - `symbol`: Trading pair (e.g., BTCUSDT)
     - `timeframe`: Time interval (1m, 5m, 15m, 1h, 4h, 1d)
     - `limit`: Number of candles (optional, default: 100)
   - **Response**:
   ```json
   {
     "success": true,
     "data": {
       "candles": [
         [1640995200000, "43000.00", "43500.00", "42800.00", "43200.00", "150.25000000"]
       ]
     },
     "timestamp": "2024-01-01T12:00:00.000Z"
   }
   ```

#### WebSocket API (Port 8080)
Base URL: `ws://localhost:8080/ws/`

**Connection URLs:**
- **Orderbook**: `ws://localhost:8080/ws/orderbook/{symbol}?limit={limit}`
- **Candles**: `ws://localhost:8080/ws/candles/{symbol}/{timeframe}`
- **Ticker**: `ws://localhost:8080/ws/ticker/{symbol}`

**WebSocket Message Formats:**

1. **Orderbook Updates**:
   ```json
   {
     "type": "orderbook_update",
     "data": {
       "symbol": "BTCUSDT",
       "bids": [["43000.00", "1.50000000"]],
       "asks": [["43100.00", "2.30000000"]],
       "lastUpdateId": 123456789
     }
   }
   ```

2. **Candlestick Updates**:
   ```json
   {
     "type": "candle_update",
     "data": {
       "symbol": "BTCUSDT",
       "timeframe": "1m",
       "candle": [1640995200000, "43000.00", "43500.00", "42800.00", "43200.00", "150.25000000"]
     }
   }
   ```

3. **Ticker Updates**:
   ```json
   {
     "type": "ticker_update",
     "data": {
       "symbol": "BTCUSDT",
       "price": "43200.00",
       "priceChange": "200.00",
       "priceChangePercent": "0.46",
       "volume": "1250.50000000"
     }
   }
   ```

### FastAPI Backend Endpoints (Legacy)
Base URL: `http://localhost:8000/api/v1/`

**Note**: These endpoints are deprecated but preserved for reference.

**Response Format**: Direct data without wrapper
```json
[{"symbol": "BTCUSDT", "baseAsset": "BTC", "quoteAsset": "USDT"}]
```

**Legacy Endpoints:**
- GET `/api/v1/symbols`
- GET `/api/v1/orderbook/{symbol}`  
- GET `/api/v1/candles/{symbol}?timeframe={tf}`
- WebSocket: `ws://localhost:8000/api/v1/ws/...`

### Testing Strategy
- Backend PHP: PHPUnit with comprehensive unit and integration test coverage for all endpoints, services, and WebSocket functionality
- Backend (Legacy): pytest with test coverage for all endpoints and services
- Frontend: Manual testing with comprehensive order book functionality
- Integration: Comprehensive paper trading test that validates full application flow

## Migration Troubleshooting Guide

### Common Issues and Solutions

#### 1. PHP Backend Connection Issues

**Problem**: Frontend can't connect to PHP backend
```
Error: Network request failed
```

**Solutions**:
```bash
# Check if PHP backend is running
curl http://localhost:8000/api/v1/market-data/symbols

# If not running, start PHP backend
cd backend_php
php -S localhost:8000 -t public

# Check for port conflicts
netstat -tulpn | grep :8000
```

#### 2. WebSocket Connection Issues

**Problem**: WebSocket connections failing
```
WebSocket connection failed
```

**Solutions**:
```bash
# Check if WebSocket server is running
netstat -tulpn | grep :8080

# Start WebSocket server if not running
cd backend_php
php websocket_server.php

# Test WebSocket connectivity
wscat -c ws://localhost:8080/ws/ticker/BTCUSDT
```

#### 3. Environment Configuration Issues

**Problem**: API endpoints returning 404 or wrong data format

**Solutions**:
```bash
# Verify frontend configuration
cd frontend/src/config
cat env.js  # Should have:
# API_BASE_URL: 'http://localhost:8000'
# WS_BASE_URL: 'ws://localhost:8080'

# Check if using correct directory (not frontend_vanilla)
pwd  # Should be in /path/to/orderfox/frontend
```

#### 4. Binance API Issues

**Problem**: No market data or API errors

**Solutions**:
```bash
# Check environment variables
grep BINANCE .env

# Test Binance connectivity directly
curl -X GET "https://api.binance.com/api/v3/exchangeInfo" | jq '.symbols[0]'

# Check API key permissions (not needed for market data, but verify if set)
```

#### 5. Migration State Issues

**Problem**: Mixed state between old and new frontend

**Solutions**:
```bash
# Verify which frontend is running
ps aux | grep node  # Check running processes

# Stop all processes and restart
pkill -f "node.*frontend"
npm run dev  # This should start the migrated frontend

# Clear browser cache and reload
# Check browser console for errors
```

#### 6. Dependencies Issues

**Problem**: Module not found or version conflicts

**Solutions**:
```bash
# Reinstall frontend dependencies
cd frontend
rm -rf node_modules package-lock.json
npm install

# Reinstall PHP dependencies
cd backend_php
rm -rf vendor composer.lock
composer install

# Check Node.js and PHP versions
node --version  # Should be 18+
php --version   # Should be 8.1+
```

### Rollback Procedures

#### Quick Rollback to Legacy Frontend
```bash
# If migration is causing issues, temporarily use legacy frontend
cd frontend_vanilla
npm run dev  # Run on different port if needed

# Update development script to use legacy
# Edit package.json root "dev" script temporarily
```

#### Complete Rollback
```bash
# Remove migrated frontend if needed
rm -rf frontend

# Rename legacy back (NOT RECOMMENDED - migration should be fixed instead)
# cp -r frontend_vanilla frontend  # Only as last resort
```

### Debugging Commands

```bash
# Check all running services
netstat -tulpn | grep -E "(8000|8080|3000)"

# Monitor PHP backend logs
cd backend_php
php -S localhost:8000 -t public  # Shows request logs

# Monitor WebSocket server
cd backend_php
php websocket_server.php  # Shows connection logs

# Check frontend console
# Open browser dev tools, look for:
# - Network tab for failed requests
# - Console tab for JavaScript errors
# - WebSocket tab for connection issues
```

### Performance Monitoring

```bash
# Check response times
time curl http://localhost:8000/api/v1/market-data/symbols

# Monitor memory usage
ps aux | grep -E "(php|node)" | awk '{print $2, $4, $11}'

# Check WebSocket message frequency
# Use browser dev tools WebSocket tab
```

### When to Contact Support

Contact support if:
- Migration completed but performance is significantly degraded
- Data integrity issues (incorrect market data)
- Persistent connection issues after following troubleshooting
- Security concerns with API endpoints

### Tool usage
- Use context7 mcp server for researching documentation and code examples for used modules when planning new features or changes and you need further information you don't have.

### Model usage
- Use Opus model when in planning mode.
- Use Sonnet model when coding.

### When Implementing New Features or Changing Code
- Do not prompt to re-run the backend or frontend, as it is already running in the background and automatically restarts on file changes.
- If you want to create temporary test files, then please create a temp subfolder in the affected project tree position and put the files there (e.g. frontend/temp), so it doesn't interfere with the existing code. Delete any temporary test files you have created after testing is complete and task is done.
