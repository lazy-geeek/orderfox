# CLAUDE.md

This file provides guidance to Claude Code when working with the OrderFox codebase.

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
# RECOMMENDED: Run both frontend and backend (from root)
npm run dev

# With Docker (from root directory)
docker-compose up --build
```

### ⚠️ Manual Server Management (STRONGLY DISCOURAGED)
```bash
# ❌ AVOID: These commands cause the 2-minute restart delays and navigation errors
# ❌ AVOID: Use only if npm run dev is broken - otherwise use npm run dev!
# Backend
cd /home/bail/github/orderfox/backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend  
cd /home/bail/github/orderfox/frontend_vanilla && npm run dev
```

**Why avoid manual server management?**
- Causes 2-minute restart delays when switching between tasks
- Requires managing two separate terminal sessions
- No automatic port cleanup - can cause port conflicts
- Increases chance of "no such file or directory" errors

## Development Workflow Optimization

**CRITICAL**: Follow these patterns to prevent 2-minute server restart delays and folder navigation errors:

### Working Directory Management
- **Always work from root**: `/home/bail/github/orderfox`
- **Use absolute paths**: Prevents "no such file or directory" errors
- **Frontend path**: `frontend_vanilla/` (with trailing slash)
- **Backend path**: `backend/`

### Server Management Best Practices
- **Primary rule**: Always use `npm run dev` from root - never manually restart servers
- **Auto-restart**: File changes trigger automatic server restarts for both backend and frontend
- **Port management**: Root command handles port cleanup (3000, 8000) automatically
- **Concurrent execution**: Both servers run simultaneously via `concurrently`

### Efficient Command Patterns
```bash
# ✅ CORRECT: Root-based development
npm run dev                    # Start both servers
npm run lint                   # Frontend linting
npm run lint:fix              # Auto-fix frontend issues

# ✅ CORRECT: Absolute path navigation
cd /home/bail/github/orderfox/frontend_vanilla && npm run test:run
cd /home/bail/github/orderfox/backend && python -m pytest tests/ -v

# ❌ WRONG: Manual server management
cd /home/bail/github/orderfox/backend && uvicorn app.main:app --reload  # Don't do this
cd /home/bail/github/orderfox/frontend_vanilla && npm run dev           # Don't do this
```

### Time-Saving Rules
- **Leverage auto-restart**: Don't manually restart servers - they restart automatically
- **Use parallel tool calls**: Execute multiple bash commands simultaneously
- **Verify paths with LS**: Check directory structure before navigation
- **Root package.json scripts**: Use existing infrastructure instead of manual commands

## Root-Based Command Reference

Quick reference for optimized development workflow:

```bash
# 🚀 PRIMARY DEVELOPMENT COMMANDS (from root)
npm run dev                    # Start both servers (MOST IMPORTANT)
npm run lint                   # Frontend linting
npm run lint:fix              # Auto-fix frontend linting issues

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

**Remember**: Always work from `/home/bail/github/orderfox/` and use `npm run dev` for development!

## Project Structure

```
orderfox/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── api/v1/endpoints/    # API endpoints
│   │   │   ├── trades_ws.py     # Real-time trades WebSocket endpoint
│   │   │   └── connection_manager.py # WebSocket connection management
│   │   ├── services/            # Business logic
│   │   │   ├── trade_service.py # Trade data processing and formatting
│   │   │   └── orderbook_aggregation_service.py # Order book processing
│   │   ├── models/              # Data models
│   │   └── core/                # Config, logging
│   └── tests/                   # Pytest test suite
│       └── services/
│           └── test_trade_service.py # Trade service unit tests
└── frontend_vanilla/
    ├── src/
    │   ├── components/          # UI components
    │   │   ├── LastTradesDisplay.js # Real-time trades display component
    │   │   └── OrderBookDisplay.js  # Order book display component
    │   ├── services/            # API, WebSocket & centralized managers
    │   │   ├── websocketManager.js  # Centralized WebSocket connection logic
    │   │   └── websocketService.js  # Low-level WebSocket operations
    │   └── store/               # State management
    ├── tests/                   # Vitest test suite
    │   ├── components/          # Component unit tests
    │   │   └── LastTradesDisplay.test.js # Last trades component tests
    │   ├── integration/         # Integration tests
    │   └── setup.js             # Test configuration
    └── main.js                  # App entry point
```

## Key Commands

### Development

#### Start Development (PRIMARY COMMAND)
```bash
npm run dev               # Starts both backend and frontend with auto-restart
```

#### Install Dependencies
```bash
# Install backend dependencies
cd /home/bail/github/orderfox/backend && pip install -r requirements.txt

# Install frontend dependencies  
cd /home/bail/github/orderfox/frontend_vanilla && npm install
```

#### Linting & Type Checking
```bash
npm run lint              # Lint frontend JavaScript
npm run lint:fix          # Auto-fix frontend linting issues
npm run typecheck         # Use Pylance in VS Code for comprehensive Python checking
# Pylance handles all Python code quality: types, imports, unused vars, style
# All backend files should pass Pylance with zero diagnostics
```

#### Testing (Use Absolute Paths)
```bash
# Backend tests
cd /home/bail/github/orderfox/backend && python -m pytest tests/ -v

# Frontend tests  
cd /home/bail/github/orderfox/frontend_vanilla && npm test
cd /home/bail/github/orderfox/frontend_vanilla && npm run test:run

```

### Code Quality & Linting
```bash
# Frontend linting (ESLint) - Use root commands
npm run lint         # Check for linting errors
npm run lint:fix     # Auto-fix linting issues

# Backend type checking (Pylance only)
# Use Pylance in VS Code for comprehensive type checking and linting
# All Python files should pass Pylance validation with zero diagnostics
# Pylance handles: type checking, import validation, unused variables, code style
```

**Code Quality Standards:**
- **Frontend**: ESLint with no errors or warnings
- **Backend**: Pylance type checking only (no flake8 or autopep8)
- **Type Safety**: All Python files must pass Pylance validation with zero diagnostics
- **Pylance Coverage**: Type hints, import management, unused variables, argument types
- **IDE Integration**: Use VS Code with Pylance extension or mcp__ide__getDiagnostics tool

### Docker Development
```bash
docker-compose up --build    # Build and run
docker-compose logs -f       # View logs
docker-compose down          # Stop containers
```

## Configuration

Create `.env` file in root:
```
BINANCE_API_KEY=your_key
BINANCE_SECRET_KEY=your_secret
```

Optional settings:
- `MAX_ORDERBOOK_LIMIT`: Max order book depth (default: 50)
- `DEBUG`: Enable debug logging (true/false)
- `CORS_ORIGINS`: Allowed CORS origins

## Architecture Highlights

### Thin Client Architecture (NEW - 2025)
- **Architecture Transformation**: OrderFox implements a thin client architecture where the frontend is a lightweight display layer that trusts backend data completely
- **Backend Data Contract**: Backend provides display-ready data with all formatting, validation, and business logic processed server-side
- **Zero Frontend Validation**: Frontend components directly assign backend data without validation or transformation
- **Performance Optimization**: Moving logic to backend reduces bundle size and improves client-side performance
- **camelCase API Convention**: Backend uses Pydantic `alias_generator=to_camel` for JavaScript-friendly field names (`uiName`, `volume24hFormatted`)
- **Container-Width Optimization**: Chart data service calculates optimal candle count based on container width: `min(max((containerWidth/6)*3, 200), 1000)`
- **Volume Display Formatting**: Backend provides formatted volume strings with K/M/B units (e.g., "12.59B", "456.78M")
- **Pre-sorted Data**: All data arrays (candles, trades, orderbook) are pre-sorted by backend before transmission
- **Dual Time Fields**: Chart data includes both `timestamp` (ms) and `time` (seconds) for TradingView compatibility
- **Complete Price Format**: Backend generates full TradingView `priceFormat` objects with precision and minMove calculated

### CSS Architecture & Component Styling
- **Shared Base Classes**: Use `.orderfox-display-base` for all display components (order book, trades, charts)
- **Semantic Class Names**: Use semantic names like `.display-header`, `.display-content`, `.display-footer` instead of component-specific names
- **Component-Specific Overrides**: Keep only unique styles in component-specific classes (e.g., `.orderfox-order-book-display`, `.orderfox-last-trades-display`)
- **DRY Principle**: Avoid duplicating common styles like headers, footers, loading states, and connection status
- **Naming Convention**: 
  - Base classes: `.orderfox-display-base`
  - Shared components: `.display-header`, `.display-content`, `.display-footer`
  - Component-specific: `.orderfox-[component]-display`
- **Theme Support**: All components inherit CSS custom properties for consistent theming

### WebSocket Connection Management
- **Centralized Manager**: `WebSocketManager` class eliminates duplicate connection logic across UI components
- **DRY Principle**: Single source of truth for connection patterns (symbol switching, timeframe changes, initialization)
- **Container-Width Parameter**: WebSocket candles endpoint accepts `container_width` instead of `limit` for optimal data loading
- **Backend Processing**: All WebSocket data is processed and formatted server-side before transmission
- **State Integration**: Seamless integration with state management and UI reset patterns

### Order Book System
- **Backend Aggregation**: All order book processing happens server-side
- **WebSocket Updates**: Real-time data with dynamic parameter updates
- **Caching**: TTL-based caching for performance (10x improvement)
- **Pre-formatted Data**: Backend sends formatted strings to frontend

### Last Trades System
- **Real-time Streaming**: Live trade data via WebSocket with CCXT Pro integration
- **Backend Processing**: Trade data formatting and validation server-side
- **Color-coded Display**: Buy trades (green) and sell trades (red) with proper styling
- **Exchange Data Only**: No mock data fallbacks - proper error handling when exchange unavailable
- **Historical + Real-time Merge**: Backend maintains unified trade history combining historical data with live streaming
- **Component Architecture**: Follows OrderBookDisplay patterns for consistency

### Exchange Service Patterns
- **CCXT Standard**: Regular CCXT exchange uses synchronous methods (`exchange.fetch_trades()`, `exchange.fetch_ohlcv()`)
- **CCXT Pro**: Pro version uses async methods for WebSocket streaming (`await exchange_pro.watch_trades()`)
- **Critical**: Never use `await` with standard CCXT methods - they return data directly, not Promises
- **Testing**: Use `Mock()` for standard CCXT, `AsyncMock()` only for CCXT Pro methods
- **Pattern**: Chart data service demonstrates correct synchronous usage in `get_initial_chart_data()`

### Symbol Service & Performance Optimization
- **Architecture Pattern**: Frontend → Backend API → Symbol Service → Exchange (proper layering)
- **Single Source of Truth**: Symbol Service is the centralized authority for all symbol operations
- **Performance Optimization**: Ticker caching with 5-minute TTL reduces API calls by 10x
- **Deduplication**: Only ONE `exchange.load_markets()` call during application startup
- **Exchange Call Monitoring**: Built-in monitoring tracks and prevents duplicate API calls
- **Centralized Business Logic**: All symbol filtering, processing, and formatting happens in Symbol Service
- **Error Resilience**: Graceful fallback to demo symbols when exchange is unavailable
- **HTTP Endpoint Pattern**: `/symbols` endpoint is thin wrapper around `symbol_service.get_all_symbols()`
- **Volume Formatting**: Backend provides `volume24h_formatted` field with K/M/B units (e.g., "12.59B", "456.78M")
- **TradingView Integration**: Backend generates complete `priceFormat` objects with precision and minMove for charts
- **camelCase Fields**: API returns JavaScript-friendly field names (`uiName`, `volume24hFormatted`, `pricePrecision`)
- **Testing Strategy**: Mock Symbol Service methods instead of direct exchange calls for better isolation
- **Cache Management**: Symbol and ticker caches with proper TTL and invalidation mechanisms
- **Critical Rule**: Never bypass Symbol Service - always use it for symbol-related operations

### WebSocket Protocol

Connect to order book:
```
ws://localhost:8000/api/v1/ws/orderbook?symbol=BTCUSDT&limit=20&rounding=0.25
```

Connect to trades stream:
```
ws://localhost:8000/api/v1/ws/trades/BTCUSDT
```

Connect to candles stream (NEW - container-width optimization):
```
ws://localhost:8000/api/v1/ws/candles/BTCUSDT?timeframe=1m&container_width=800
```

Update parameters without reconnecting:
```json
{
  "type": "update_params",
  "limit": 50,
  "rounding": 0.5
}
```

### State Management
- Frontend uses custom subscribe/notify pattern
- WebSocket service handles automatic reconnection
- Backend manages all data aggregation and formatting
- **Thin Client Pattern**: Frontend directly assigns backend data without validation or transformation
- **Zero Processing**: State update functions simplified to direct assignment (`state.currentCandles = payload.data`)
- **Backend Trust**: Frontend trusts backend data completely - no client-side validation required

## Common Tasks

### Adding a New API Endpoint
1. Create endpoint in `backend/app/api/v1/endpoints/`
2. Add to router in `backend/app/api/v1/api.py`
3. Create service logic in `backend/app/services/`
4. Add tests in `backend/tests/`

### Adding a New Display Component
1. Create component in `frontend_vanilla/src/components/`
2. Use `.orderfox-display-base` as base class in HTML
3. Use semantic class names: `.display-header`, `.display-content`, `.display-footer`
4. Add only component-specific styles to `style.css`
5. Follow existing patterns for connection status, loading states, etc.
6. Test with both light and dark themes

### Modifying Order Book Display
1. Backend: Update aggregation in `orderbook_aggregation_service.py`
2. Backend: Adjust formatting in `formatting_service.py`
3. Frontend: Update display in `OrderBookDisplay.js`

### Modifying Last Trades Display
1. Backend: Update trade processing in `trade_service.py`
2. Backend: Adjust WebSocket streaming in `trades_ws.py`
3. Frontend: Update display in `LastTradesDisplay.js`
4. Note: Follows OrderBookDisplay patterns for consistency

### Modifying Chart Display
1. Backend: Update chart data processing in `chart_data_service.py`
2. Backend: Adjust WebSocket data streaming in `market_data_ws.py`
3. Frontend: Update chart component in `LightweightChart.js`
4. Note: Uses TradingView Lightweight Charts API, not ECharts

### Working with Symbol Service (CRITICAL)
1. **Always use Symbol Service**: Never call exchange directly for symbol operations
2. **Get all symbols**: Use `symbol_service.get_all_symbols()` for symbol lists
3. **Symbol validation**: Use `symbol_service.validate_symbol_exists(symbol_id)`
4. **Symbol conversion**: Use `symbol_service.resolve_symbol_to_exchange_format(symbol_id)`
5. **Testing**: Mock `symbol_service.get_all_symbols()` instead of exchange methods
6. **Performance**: Symbol Service automatically handles caching and deduplication
7. **Error handling**: Symbol Service provides graceful fallbacks to demo symbols
8. **HTTP endpoints**: Use Symbol Service methods, not direct exchange calls

### Chart Performance & UX Features
- **Zoom Preservation**: User zoom/pan state is preserved during real-time updates
- **Viewport-Based Data Loading**: Automatically calculates optimal candle count based on chart size
- **Efficient Real-time Updates**: Uses `series.update()` for single candle updates to maintain performance
- **Smart Auto-fitting**: Only calls `fitContent()` on initial load or symbol/timeframe changes
- **Dynamic Price Precision**: Charts automatically adjust decimal places based on symbol precision (BTC: 1 decimal, XRP: 4 decimals, high-precision tokens: 6-7 decimals)
- **Performance Optimization**: Price precision updates only on symbol changes, not during real-time data updates

### Working with WebSockets
- **Backend**: Connection management in `connection_manager.py`
- **Frontend**: Centralized WebSocket management via `WebSocketManager` class
- **Low-level operations**: `websocketService.js` handles message processing
- Dynamic parameter updates supported without reconnection

## Testing

### Backend Testing
```bash
# Backend unit tests (use absolute path)
cd /home/bail/github/orderfox/backend && python -m pytest tests/ -v

# Specific test file (from backend directory)
cd /home/bail/github/orderfox/backend && python -m pytest tests/services/test_orderbook_aggregation_service.py -v

# Chart data service tests
cd /home/bail/github/orderfox/backend && python -m pytest tests/services/test_chart_data_service.py -v

# Trade service tests
cd /home/bail/github/orderfox/backend && python -m pytest tests/services/test_trade_service.py -v

# Integration tests
cd /home/bail/github/orderfox/backend && python -m pytest tests/integration/ -v

# Performance tests
cd /home/bail/github/orderfox/backend && python -m pytest tests/load/ -v
```

### Frontend Testing
```bash
# Frontend unit tests (Vitest) - use absolute path
cd /home/bail/github/orderfox/frontend_vanilla && npm test

# Run tests once (CI mode)
cd /home/bail/github/orderfox/frontend_vanilla && npm run test:run

# Run tests with UI
cd /home/bail/github/orderfox/frontend_vanilla && npm run test:ui

# Test specific component
cd /home/bail/github/orderfox/frontend_vanilla && npm test -- LightweightChart
cd /home/bail/github/orderfox/frontend_vanilla && npm test -- LastTradesDisplay
```

**Frontend Test Coverage:**
- **Price Precision Logic**: 14 unit tests covering default precision, dynamic updates, error handling, and edge cases
- **Last Trades Component**: 14 unit tests covering component creation, trade updates, color coding, and state management
- **Integration Tests**: 4 tests validating main.js flow and performance optimization patterns
- **Framework**: Vitest with jsdom environment for DOM testing
- **Test Structure**: Mirrors backend structure with `/tests/components/` and `/tests/integration/`

## Important Notes

### Frontend URLs
- Always use relative URLs (`/api/v1`) in development
- Vite proxy handles routing to backend
- WebSocket URLs also use relative paths

### Order Book Limitations
- Binance API limits: max 5000 entries
- Limited price range for high rounding values
- This is a market limitation, not a bug

### Development Tips
- **Primary Command**: Always use `npm run dev` from root - handles both servers with auto-restart
- **No Manual Restarts**: Backend and frontend auto-restart on file changes via `npm run dev`
- **Use Absolute Paths**: Always use `/home/bail/github/orderfox/` prefix for directory navigation
- **Port Management**: Root command automatically cleans up ports 3000 and 8000
- **Debugging**: Check logs for WebSocket connection issues, use browser DevTools for WebSocket debugging
- **Caching**: Symbol info cached for 5 minutes

## Error Handling

- Backend: Comprehensive exception handling in FastAPI
- Frontend: WebSocket auto-reconnection on disconnect
- Logging: Structured logs with request timing
- Health check: GET /health endpoint

## VS Code Dev Container

```bash
# Open in Dev Container
1. Install "Dev Containers" extension
2. Ctrl+Shift+P → "Dev Containers: Reopen in Container"
3. Services start automatically
```

Container uses `/workspaces/orderfox` as working directory.

**Note**: In Dev Container, replace `/home/bail/github/orderfox` with `/workspaces/orderfox` in all absolute path commands.

## Project specific rules

See @CLAUDE-RULES.md for detailed rules for this project.