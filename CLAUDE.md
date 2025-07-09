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
# Run both frontend and backend (from root)
npm run dev

# Or run separately:
# Backend
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend_vanilla && npm run dev

# With Docker
docker-compose up --build
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
```bash
# Install dependencies
cd backend && pip install -r requirements.txt
cd frontend_vanilla && npm install

# Linting & Type Checking
npm run lint              # Lint frontend JavaScript
npm run lint:fix          # Auto-fix frontend linting issues
npm run typecheck         # Use Pylance in VS Code for comprehensive Python checking
# Pylance handles all Python code quality: types, imports, unused vars, style
# All backend files should pass Pylance with zero diagnostics

# Run tests
cd backend && python -m pytest tests/ -v

# Frontend tests
cd frontend_vanilla && npm test

# Run frontend tests once (CI mode)
cd frontend_vanilla && npm run test:run

# Full application test
python test_paper_trading.py
```

### Code Quality & Linting
```bash
# Frontend linting (ESLint)
cd frontend_vanilla && npm run lint         # Check for linting errors
cd frontend_vanilla && npm run lint:fix     # Auto-fix linting issues

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
- **Optimal Candle Count**: Dynamic calculation based on chart viewport width (200-1000 range)
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

### WebSocket Protocol

Connect to order book:
```
ws://localhost:8000/api/v1/ws/orderbook?symbol=BTCUSDT&limit=20&rounding=0.25
```

Connect to trades stream:
```
ws://localhost:8000/api/v1/ws/trades/BTCUSDT
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
# Backend unit tests
cd backend && python -m pytest tests/ -v

# Specific test file
python -m pytest tests/services/test_orderbook_aggregation_service.py -v

# Chart data service tests
python -m pytest tests/services/test_chart_data_service.py -v

# Trade service tests
python -m pytest tests/services/test_trade_service.py -v

# Integration tests
python -m pytest tests/integration/ -v

# Performance tests
python -m pytest tests/load/ -v
```

### Frontend Testing
```bash
# Frontend unit tests (Vitest)
cd frontend_vanilla && npm test

# Run tests once (CI mode)
cd frontend_vanilla && npm run test:run

# Run tests with UI
cd frontend_vanilla && npm run test:ui

# Test specific component
cd frontend_vanilla && npm test -- LightweightChart
cd frontend_vanilla && npm test -- LastTradesDisplay
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
- Backend and frontend auto-restart on file changes
- Check logs for WebSocket connection issues
- Use browser DevTools for WebSocket debugging
- Symbol info cached for 5 minutes

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

## Project specific rules

See @CLAUDE-RULES.md for detailed rules for this project.