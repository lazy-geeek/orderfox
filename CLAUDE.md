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

## Root-Based Command Reference

Quick reference for optimized development workflow:

```bash
# 🚀 PRIMARY DEVELOPMENT COMMANDS (from root)
npm run dev                    # Smart server management (see Server Management section)
npm run dev:bg                 # Claude Code: Start servers in background
npm run dev:status             # Check server status
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

#### Start Development
See "Server Management" section above for `npm run dev` behavior and Claude Code alternatives.

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
- `LIQUIDATION_API_BASE_URL`: External API for historical liquidation data

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
- **Component-Specific Overrides**: Keep only unique styles in component-specific classes (e.g., `.orderfox-order-book-display`, `.orderfox-last-trades-display`, `.orderfox-liquidation-display`)
- **DRY Principle**: Avoid duplicating common styles like headers, footers, loading states, and connection status
- **Naming Convention**: 
  - Base classes: `.orderfox-display-base`
  - Shared components: `.display-header`, `.display-content`, `.display-footer`
  - Component-specific: `.orderfox-[component]-display`
- **Theme Support**: All components inherit CSS custom properties for consistent theming
- **Grid Layouts**: 
  - Use `.three-columns` for 3-column layouts (e.g., liquidations)
  - Use `.four-columns` for 4-column layouts (e.g., order book)
- **Color Inheritance**: Amount values inherit color from `.bid-price` (green) and `.ask-price` (red) classes
- **Alignment**: Numeric columns use `text-align: right` for consistent visual alignment

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

### Liquidation Data Stream System
- **Binance Futures Integration**: Direct WebSocket connection to Binance @forceOrder stream for real-time liquidation data
- **Backend Processing**: Liquidation service handles WebSocket connections, data formatting, and symbol conversion
- **Historical Data Integration**: Fetches last 50 liquidations from external API on WebSocket connection
- **Display Components**: LiquidationDisplay component shows Amount (USDT), Quantity, and Time in a 3-column layout
- **Color Coding**: Amount column color-coded - green for buy liquidations, red for sell liquidations
- **Dynamic Headers**: Quantity header updates dynamically to show base asset (e.g., "Quantity (BTC)" for BTCUSDT)
- **Number Formatting**: 
  - Amount (USDT) rounded to whole numbers with comma thousand separators
  - Quantity formatted using `formatting_service` based on symbol's `amountPrecision`
  - Backend provides `baseAsset` field for dynamic header updates
- **Data Ordering**: Liquidations sorted with newest first using deque with appendleft for real-time data
- **Thin Client Architecture**: Backend provides formatted data with `quantityFormatted`, `priceUsdtFormatted`, and `displayTime`
- **WebSocket Management**: Integrated with existing WebSocket service patterns and connection lifecycle
- **Layout Integration**: Positioned right of trades display, below chart in responsive grid layout
- **Error Handling**: Graceful fallback and reconnection logic for Binance connection issues
- **API Integration**: Uses `fetch_historical_liquidations()` with configurable LIQUIDATION_API_BASE_URL

### Liquidation Orders API Architecture
- **External API Integration**: Fetches historical liquidation data from external API service
- **HTTP Client**: Uses aiohttp with 15-second timeout for reliable API calls
- **Data Conversion**: `_convert_api_to_ws_format()` ensures API data matches WebSocket format
- **Field Mapping**: Uses `order_filled_accumulated_quantity` field for actual liquidated amounts
- **Caching Strategy**: Historical data fetched once per symbol and stored in deque cache
- **Error Resilience**: Returns empty list on API failure, allowing WebSocket-only operation
- **Environment Configuration**: API URL configured via LIQUIDATION_API_BASE_URL environment variable
- **Integration Points**: 
  - `liquidation_service.fetch_historical_liquidations()` - API data fetching
  - `liquidations_ws.py` - Fetches historical data on WebSocket connection
  - Deque cache maintains last 50 liquidations per symbol
- **Data Flow**: API → Convert to WS format → Sort by timestamp → Store in cache → Send to frontend

### Exchange Service Patterns
- **CCXT Standard**: Regular CCXT exchange uses synchronous methods (`exchange.fetch_trades()`, `exchange.fetch_ohlcv()`)
- **CCXT Pro**: Pro version uses async methods for WebSocket streaming (`await exchange_pro.watch_trades()`)
- **Critical**: Never use `await` with standard CCXT methods - they return data directly, not Promises
- **Testing**: Use `Mock()` for standard CCXT, `AsyncMock()` only for CCXT Pro methods
- **Pattern**: Chart data service demonstrates correct synchronous usage in `get_initial_chart_data()`

### Symbol Service & Performance Optimization
- **Architecture Pattern**: Frontend → Backend API → Symbol Service → Exchange (proper layering)
- **Single Source of Truth**: Symbol Service is the centralized authority for all symbol operations
- **Performance Optimization**: Symbol caching with 5-minute TTL reduces API calls by 10x
- **Deduplication**: Only ONE `exchange.load_markets()` call during application startup
- **Exchange Call Monitoring**: Built-in monitoring tracks and prevents duplicate API calls
- **Centralized Business Logic**: All symbol filtering, processing, and formatting happens in Symbol Service
- **Error Resilience**: Graceful fallback to demo symbols when exchange is unavailable
- **HTTP Endpoint Pattern**: `/symbols` endpoint is thin wrapper around `symbol_service.get_all_symbols()`
- **Volume Formatting**: Backend provides `volume24h_formatted` field with K/M/B units (e.g., "12.59B", "456.78M")
- **TradingView Integration**: Backend generates complete `priceFormat` objects with precision and minMove for charts
- **camelCase Fields**: API returns JavaScript-friendly field names (`uiName`, `volume24hFormatted`, `pricePrecision`)
- **Testing Strategy**: Mock Symbol Service methods instead of direct exchange calls for better isolation
- **Cache Management**: Symbol caches with proper TTL and invalidation mechanisms
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

Connect to candles stream (container-width optimization):
```
ws://localhost:8000/api/v1/ws/candles/BTCUSDT?timeframe=1m&container_width=800
```

Connect to liquidations stream:
```
ws://localhost:8000/api/v1/ws/liquidations/BTCUSDT
```

**Available WebSocket Endpoints:**
- **Order Book**: Real-time aggregated order book with dynamic parameters
- **Trades**: Live trade stream with historical + real-time merge
- **Candles**: OHLCV data with container-width optimization
- **Liquidations**: Real-time liquidation orders from Binance futures with formatted display data

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

### Responsive Layout Architecture
- **Full-Width Chart**: Chart and timeframe selector span 100% width for better visibility
- **Stacked Layout**: Orderbook and trades positioned below chart in a responsive grid
- **Breakpoints**:
  - Desktop (>1024px): Orderbook and trades side-by-side
  - Tablet (768-1024px): Adjusted spacing, 50vh chart height
  - Mobile (<768px): Vertical stacking, 40vh chart height
  - Small Mobile (<480px): Wrapped header controls, 35vh chart height
- **Viewport-Based Sizing**: Chart height uses vh units (60vh default) with min/max constraints
- **Preserved Margins**: Display components maintain 10px margins for proper spacing from browser edges

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

### Modifying Liquidation Display
1. Backend: Update liquidation processing in `liquidation_service.py`
2. Backend: Adjust WebSocket endpoint in `liquidations_ws.py`
3. Frontend: Update display in `LiquidationDisplay.js`
4. Note: Uses Binance futures API directly, not CCXT, for @forceOrder stream

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
- **Dynamic parameter updates**: Supported without reconnection for order book streams
- **Testing**: Use `symbol_service` mocks for WebSocket tests, not `exchange_service`

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

# WebSocket API tests
cd /home/bail/github/orderfox/backend && python -m pytest tests/api/v1/test_market_data_ws.py -v

# Integration tests
cd /home/bail/github/orderfox/backend && python -m pytest tests/integration/ -v

# Performance tests
cd /home/bail/github/orderfox/backend && python -m pytest tests/load/ -v
```

**WebSocket Testing Guidelines:**
- **Mock Services**: Use `symbol_service` mocks for WebSocket tests, not `exchange_service`
- **Async Mocks**: Use `AsyncMock()` for async methods like `chart_data_service.get_initial_chart_data`
- **Method Signatures**: Update connection manager calls to use `display_symbol` parameter
- **Test Data**: Include `volume24h_formatted` and `priceFormat` fields in symbol mock data

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
- **Smart Server Management**: `npm run dev` checks if servers are already running
- **Auto-restart**: Servers automatically reload when files change
- **Use Absolute Paths**: Always use `/home/bail/github/orderfox/` prefix for directory navigation
- **Debugging**: Check logs in `logs/` directory, use browser DevTools for WebSocket debugging
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