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

### Legacy Frontend (React - Removed)
```bash
# NOTE: The legacy React frontend has been completely removed
# Use frontend_vanilla/ for all development
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
  - **backend/app/services/orderbook_aggregation_service.py**: Backend order book aggregation logic with caching
  - **backend/app/services/orderbook_manager.py**: Singleton manager for order book lifecycle and connections
- **backend/app/models/**: Data models and schemas
  - **backend/app/models/orderbook.py**: Order book data model with sorted price levels and thread-safe operations
- **backend/tests/**: Comprehensive backend unit tests using pytest
  - **backend/tests/services/**: Unit tests for aggregation service, manager, caching, and connection tracking
  - **backend/tests/integration/**: Integration tests for full order book flow
  - **backend/tests/load/**: Load tests for performance validation

### Frontend Structure (Vanilla JavaScript - Active)
- **frontend_vanilla/src/store/**: State management with subscribe/notify pattern
- **frontend_vanilla/src/components/**: Modular components (OrderBookDisplay, CandlestickChart, etc.)
- **frontend_vanilla/src/services/**: WebSocket service and API client
- **frontend_vanilla/src/layouts/**: Layout components
- **frontend_vanilla/src/style.css**: Global styles with component-specific CSS
- **frontend_vanilla/main.js**: Application entry point with event handling

### Legacy Frontend Structure (React - Removed)
- The legacy React frontend has been completely removed from the codebase
- Historical reference: Previously contained Redux store, components, and services
- Use `frontend_vanilla/` for all development - the active vanilla JavaScript implementation

### Key Technical Details
- **State Management**: Custom state management with subscribe/notify pattern for reactive updates
- **Real-time Data**: WebSocket connections with automatic reconnection on parameter changes
- **Order Book Architecture**: Complete backend migration with advanced aggregation capabilities
  - **Backend Aggregation**: All order book processing moved to backend for better performance and consistency
  - **Dynamic Parameters**: WebSocket parameter updates (limit, rounding) without reconnection
  - **Caching System**: TTL-based caching with 10x+ performance improvements and >80% hit rates
  - **Thread-Safe Operations**: Async locks and concurrent access protection
  - **Memory Management**: Automatic cleanup and resource monitoring
- **API Integration**: Binance API through ccxt library with paper trading mode support
- **Error Handling**: Comprehensive exception handling in FastAPI with proper logging
- **Environment**: Configuration through .env files with automatic path detection

### Recent Improvements
- **Order Book Backend Migration**: Complete migration of order book processing from frontend to backend
  - **Backend Aggregation Service**: Ported all frontend aggregation logic to backend with performance optimizations
  - **Order Book Manager**: Singleton pattern for managing order book lifecycle and connections
  - **Dynamic WebSocket Parameters**: Support for updating limit and rounding parameters without reconnection
  - **Advanced Caching**: TTL-based caching system with cache warming and hit/miss metrics
  - **Thread-Safe Operations**: Async locks and concurrent access protection for order book operations
  - **Memory Management**: Automatic cleanup and resource monitoring for order book instances
  - **Frontend Simplification**: Removed all aggregation logic from frontend, now displays pre-aggregated data
  - **Enhanced WebSocket Protocol**: Message-based parameter updates with acknowledgments
  - **Comprehensive Testing**: Unit tests, integration tests, and load tests for all order book components
  - **Code Cleanup**: Removed legacy code including unused imports, commented blocks, and deprecated packages
- **Rounding Options Architecture**: Moved rounding calculations from orderbook aggregation to symbol service
  - **Symbol Service Enhancement**: Added `calculate_rounding_options` method with price precision and current price integration
  - **Backend Schema Updates**: Added `roundingOptions` and `defaultRounding` fields to `SymbolInfo`
  - **Frontend State Management**: Updated to use symbol-provided rounding options instead of WebSocket-derived options
  - **Proper Architecture Separation**: Symbol metadata handled at symbol level, aggregation focused on processing
- **Legacy Code Removal**: Eliminated outdated mock orderbook streaming methods that bypassed aggregation system
- **WebSocket Message Handling**: Enhanced frontend message routing to properly handle all message types
  - **Parameter Update Acknowledgments**: Added explicit handling for `params_updated` messages
  - **Message Type Safety**: Improved fallback routing to prevent incorrect message processing
  - **Error Message Handling**: Added proper handling for WebSocket error messages
  - **Debug Improvements**: Enhanced logging for unknown message types to aid development
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

### Configuration
- Environment variables loaded from .env file (multiple path detection)
- **Required**: BINANCE_API_KEY, BINANCE_SECRET_KEY
- **Optional**: FIREBASE_CONFIG_JSON, DEBUG, MAX_ORDERBOOK_LIMIT
- **Container Configuration**: DEVCONTAINER_MODE, CONTAINER, HOST, PORT
- **CORS Origins**: Configurable via CORS_ORIGINS environment variable
- **WebSocket URLs**: Configurable Binance API endpoints (BINANCE_WS_BASE_URL, BINANCE_API_BASE_URL)
- Trading mode defaults to paper trading for safety
- **Container Detection**: Automatic detection of Docker/Dev Container environments with adaptive configuration
- **Cross-Platform Connectivity**: Special configuration for Windows host to container access using Vite proxy to avoid CORS issues

### Known Limitations
- **Orderbook Depth**: Binance API limits orderbook to 5000 entries maximum, sourced from memory
- **Price Range Limitation**: Even with maximum entries, market depth may not span wide enough price ranges for large rounding values
- **Aggregation Reality**: With high rounding values (e.g., $1 for ETH at $3000), actual market orders may only exist within $1-3 price range
- **Not a Bug**: Insufficient orderbook levels at high rounding is a market limitation, not a technical issue
- **Solution**: Use smaller rounding values or accept fewer populated levels for high-value assets

### Testing Strategy
- **Backend**: Comprehensive pytest test suite with extensive coverage
  - **Unit Tests**: Test aggregation service, order book manager, caching, and connection tracking
    - `test_orderbook_aggregation_service.py`: 450+ lines covering rounding, aggregation, and edge cases
    - `test_orderbook_manager.py`: 400+ lines covering lifecycle, connections, and memory management
    - `test_connection_parameter_tracking.py`: 300+ lines covering WebSocket parameter updates
    - `test_caching_mechanism.py`: 500+ lines covering TTL, cleanup, metrics, and concurrency
  - **Integration Tests**: Test full order book flow from WebSocket to broadcast
    - `test_orderbook_full_flow.py`: 600+ lines covering end-to-end pipeline testing
  - **Load Tests**: Performance validation with specific requirements
    - `test_orderbook_performance.py`: 500+ lines validating latency (<100ms), throughput (100+ req/s), and cache hit rates (>80%)
  - **Test Coverage**: All order book components, WebSocket protocol, and parameter updates
- **Frontend**: Manual testing with comprehensive order book functionality
- **Integration**: Comprehensive paper trading test that validates full application flow

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

### Order Book WebSocket Protocol

The order book system uses an enhanced WebSocket protocol for real-time parameter updates:

#### Connection Format
```
ws://localhost:8000/api/v1/ws/orderbook?symbol=BTCUSDT&limit=20&rounding=0.25
```

#### Parameter Update Messages
```json
{
  "type": "update_params",
  "limit": 50,
  "rounding": 0.5
}
```

#### Acknowledgment Response
```json
{
  "type": "params_updated",
  "connection_id": "conn_123",
  "limit": 50,
  "rounding": 0.5,
  "status": "success"
}
```

#### Response Data Format
```json
{
  "type": "orderbook_update",
  "symbol": "BTCUSDT",
  "bids": [
    {
      "price": 50000.0,
      "quantity": 1.5,
      "cumulative": 1.5,
      "price_formatted": "50000.00",
      "amount_formatted": "1.50",
      "cumulative_formatted": "1.50"
    },
    {
      "price": 49999.5,
      "quantity": 0.8,
      "cumulative": 2.3,
      "price_formatted": "49999.50",
      "amount_formatted": "0.80",
      "cumulative_formatted": "2.30"
    }
  ],
  "asks": [
    {
      "price": 50000.5,
      "quantity": 1.2,
      "cumulative": 1.2,
      "price_formatted": "50000.50",
      "amount_formatted": "1.20",
      "cumulative_formatted": "1.20"
    },
    {
      "price": 50001.0,
      "quantity": 0.9,
      "cumulative": 2.1,
      "price_formatted": "50001.00",
      "amount_formatted": "0.90",
      "cumulative_formatted": "2.10"
    }
  ],
  "rounding": 0.25,
  "rounding_options": [0.01, 0.05, 0.1, 0.25, 0.5, 1.0],
  "timestamp": 1672531200000,
  "market_depth_info": {
    "sufficient_data": true,
    "raw_levels_count": 500,
    "requested_levels": 20
  }
}
```

**Note**: Each bid/ask level now includes both raw numeric values and pre-formatted string values. Frontend components use the formatted fields directly for display, eliminating client-side formatting logic.

### Order Book Aggregation

The backend aggregation service provides sophisticated order book processing:

#### Migration Benefits
- **Performance**: 10x+ improvement through caching and backend processing
- **Consistency**: Unified aggregation logic ensures consistent results across all clients
- **Scalability**: Backend caching allows serving multiple clients efficiently
- **Maintainability**: Single source of truth for aggregation logic
- **Real-time Updates**: Dynamic parameter changes without WebSocket reconnection
- **Memory Efficiency**: Automatic cleanup and resource monitoring

#### Key Features
- **Rounding Logic**: Precise rounding up for asks, down for bids
- **Level Aggregation**: Combines orders at same price level
- **Cumulative Totals**: Pre-calculated running totals for both sides
- **Zero Filtering**: Automatic removal of zero-quantity levels
- **Market Depth Analysis**: Warns when insufficient data for rounding level

#### Performance Optimizations
- **Caching**: TTL-based cache with 10x+ performance improvements
- **Cache Warming**: Pre-calculation of common parameter combinations
- **Memory Management**: Automatic cleanup of unused order book instances
- **Thread Safety**: Async locks for concurrent access protection

#### Usage Examples
```python
# Get aggregated order book
orderbook = await aggregation_service.aggregate_orderbook(
    raw_orderbook, 
    limit=20, 
    rounding=0.25
)

# Update parameters dynamically
await connection_manager.update_connection_params(
    connection_id, 
    limit=50, 
    rounding=0.5
)
```

#### Files Cleaned Up During Migration
- **backend/app/services/orderbook_manager.py**: Removed unused `import weakref`
- **backend/app/api/v1/endpoints/market_data_http.py**: Removed unused `import re` and `from datetime import datetime`
- **backend/app/services/trading_engine_service.py**: Removed large blocks of commented legacy code
- **backend/requirements.txt**: Removed unused `python-binance==1.0.19` package
- **Frontend aggregation utilities**: Completely removed as processing moved to backend

### Backend Formatting System

The backend formatting system handles all number formatting for order book display, moving formatting logic from frontend to backend for consistency and performance.

#### Architecture Overview
- **FormattingService**: Singleton service handling all price, amount, and total formatting
- **Symbol Precision**: Extracts amount and price precision from CCXT exchange data
- **Pre-formatted Fields**: Backend sends pre-formatted strings to frontend
- **Zero Frontend Formatting**: Frontend displays formatted strings without any processing

#### Key Components

##### FormattingService (`backend/app/services/formatting_service.py`)
- **Singleton Pattern**: Single instance across application lifecycle
- **Thread-Safe**: Handles concurrent formatting requests
- **Symbol-Aware**: Uses exchange precision data for optimal formatting
- **Error Handling**: Graceful fallback for invalid data

##### Core Formatting Methods

**Price Formatting**: `format_price(value, symbol_info)`
- Uses price precision from symbol data
- Handles scientific notation for very small values (< 0.00001)
- Preserves exact precision for trading accuracy
- Example: `50000.12345` → `"50000.12"` (2 decimal places for BTCUSDT)

**Amount Formatting**: `format_amount(value, symbol_info)`
- Consistent precision per symbol based on symbol's amountPrecision (minimum 2 decimals for readability)
- Scientific notation for very small amounts (< 0.00001): `0.000001` → `"1.00e-06"`
- Compact notation for large amounts (fixed 2 decimals): `1500000` → `"1.50M"`, `2500` → `"2.50K"`
- All other amounts use consistent symbol precision: ETHUSDT (6 decimals) → `12.345678` → `"12.345678"`
- Zero precision symbols get minimum 2 decimals: SHIB (0 precision) → `123.456` → `"123.46"`

**Total Formatting**: `format_total(value, symbol_info)`
- Optimized for cumulative totals display
- More aggressive compact notation for large totals
- Consistent precision handling across all scenarios

#### Integration Points

##### Order Book Aggregation
- **Pre-formatting**: All order book levels receive formatted fields during aggregation
- **Formatted Fields**: Each level includes `price_formatted`, `amount_formatted`, `cumulative_formatted`
- **Symbol Context**: Symbol information passed through aggregation pipeline
- **Performance**: Formatting integrated into existing aggregation process

##### WebSocket Protocol
- **Enhanced Messages**: All WebSocket messages include formatted fields
- **Real-time Updates**: Formatted data sent with every order book update
- **Consistency**: Same formatting logic for all WebSocket clients
- **Zero Latency**: Pre-formatted strings avoid client-side processing

##### Frontend Integration
- **Direct Display**: Frontend uses formatted fields directly without processing
- **No Fallbacks**: All frontend formatting functions removed
- **Simplified Code**: Frontend components focused on display logic only
- **Performance**: Eliminates client-side formatting overhead

#### Formatting Rules and Thresholds

##### Amount Formatting Rules
```python
# Scientific notation for very small amounts
if abs(value) < 0.00001:
    return f"{value:.2e}"  # 1.00e-06

# High precision for small amounts  
elif abs(value) < 0.01:
    decimal_places = max(4, amount_precision)
    return f"{value:.{decimal_places}f}"  # 0.00123400

# Compact notation for large amounts
elif abs(value) >= 1000000:
    return f"{value / 1000000:.2f}M"  # 1.50M
elif abs(value) >= 1000:
    return f"{value / 1000:.2f}K"  # 2.50K

# Regular precision for normal amounts
else:
    decimal_places = max(2, amount_precision)
    return f"{value:.{decimal_places}f}"  # 12.35
```

##### Price Formatting Rules
```python
# Scientific notation for very small prices
if abs(value) < 0.00001:
    return f"{value:.2e}"  # 1.00e-06

# Use symbol price precision for all other prices
else:
    return f"{value:.{price_precision}f}"  # 50000.12
```

##### Total Formatting Rules
```python
# Compact notation for large totals
if abs(value) >= 1000000:
    return f"{value / 1000000:.2f}M"  # 1.50M
elif abs(value) >= 1000:
    return f"{value / 1000:.2f}K"  # 2.50K
    
# Scientific notation for very small totals
elif abs(value) < 0.00001:
    return f"{value:.2e}"  # 1.00e-06
    
# High precision for small totals
elif abs(value) < 0.01:
    return f"{value:.4f}"  # 0.0012
    
# Regular precision for normal totals
else:
    return f"{value:.2f}"  # 12.35
```

#### Real-World Examples

##### BTC/USDT (High Price, Small Amounts)
- **Price**: `67432.50000000` → `"67432.50"`
- **Amount**: `0.00123456` → `"0.00123456"`
- **Total**: `83.25789012` → `"83.26"`

##### ETH/USDT (Medium Price, Medium Amounts)  
- **Price**: `3456.78900000` → `"3456.79"`
- **Amount**: `1.23456789` → `"1.2346"`
- **Total**: `4267.89123456` → `"4.27K"`

##### SHIB/USDT (Low Price, Large Amounts)
- **Price**: `0.00000876` → `"8.76e-06"`
- **Amount**: `12345678.90` → `"12.35M"`
- **Total**: `108.07654321` → `"108.08"`

#### Performance Characteristics

##### Benchmarks
- **Formatting Speed**: 23 comprehensive test cases pass in <100ms
- **Memory Usage**: Minimal overhead with singleton pattern
- **Concurrency**: Thread-safe operations with async locks
- **Integration**: Zero additional latency in order book pipeline

##### Test Coverage
- **Unit Tests**: 23 test cases covering all formatting scenarios
- **Integration Tests**: 4 end-to-end pipeline tests
- **Performance Tests**: Large dataset validation (1000+ levels)
- **Real Data Tests**: Actual exchange data validation

#### Migration Benefits

##### Problem Solved
- **Original Issue**: Small amounts (0.001234) displayed as "0.00" due to frontend 2-decimal limitation
- **Secondary Issue**: Inconsistent decimal places within same symbol (3 vs 4 decimals for different amounts)
- **Solution**: Backend consistent precision per symbol eliminates visual inconsistency
- **Architecture**: Complete elimination of frontend formatting logic
- **Consistency**: All clients receive identical formatted data with consistent decimal places per symbol

##### Key Improvements
- **Precision**: Consistent decimal places per symbol based on exchange precision data
- **Performance**: Backend pre-formatting eliminates client-side processing
- **Visual Consistency**: Same number of decimal places for all amounts within a symbol
- **Maintainability**: Centralized formatting rules and thresholds
- **Scalability**: Singleton pattern supports multiple concurrent clients

#### Future Enhancements
- **User Preferences**: Configurable decimal places per user
- **Locale Support**: Locale-specific number formatting
- **A/B Testing**: Different format styles for user experience optimization
- **Performance Monitoring**: Formatting performance metrics and optimization

### Decimal Arithmetic and Precision

The application uses centralized decimal utilities to avoid floating-point precision issues common in financial applications:

#### DecimalUtils Class (`backend/app/utils/decimal_utils.py`)
- **Purpose**: Centralized precise decimal arithmetic operations
- **Key Methods**:
  - `round_down(value, multiple)`: Round value down to nearest multiple using decimal arithmetic
  - `round_up(value, multiple)`: Round value up to nearest multiple using decimal arithmetic  
  - `generate_power_of_10_options(base_precision, max_options, max_value)`: Generate clean rounding options without floating-point errors
- **Integration**: Used by symbol service for rounding options and aggregation service for price rounding
- **Benefits**: Eliminates floating-point precision errors like `9.999999999999999e-06` → clean `0.00001`

#### Rounding-Aware Price Formatting
- **FormattingService Enhancement**: `format_price()` method now accepts optional `rounding` parameter
- **Logic**: Formats prices according to selected rounding level rather than just symbol precision
- **Examples**:
  - `108980.0` with `rounding=10` → `"108980"` (clean integer)
  - `108983.45` with `rounding=0.1` → `"108983.4"` (appropriate decimals)
  - Fallback to symbol precision when no rounding provided
- **Cache Integration**: Cache keys include rounding parameter for proper cache separation
- **Backward Compatibility**: Existing calls without rounding parameter continue to work

#### Architecture Integration
- **Symbol Service**: Uses `DecimalUtils.generate_power_of_10_options()` for clean rounding option generation
- **Aggregation Service**: Uses `DecimalUtils` rounding functions and passes rounding to formatting
- **Frontend Display**: Receives properly formatted prices that match selected rounding level
- **Performance**: Caching system enhanced to handle rounding-specific formatting

#### Common Issues Resolved
- **Floating-Point Precision**: High-precision symbols (SHIBUSDT, etc.) now show clean rounding options
- **Display Consistency**: Price formatting matches user-selected rounding level
- **Professional Appearance**: No more unnecessary decimals in large rounding scenarios
- **Maintainability**: Single source of truth for decimal arithmetic operations

### MCP Server
- Use context7 to understand a module, package, library or API in more depth if you don't have enough information yourself.

### When Implementing New Features or Changing Code  
- Do not prompt to re-run the backend or frontend, as it is already running in the background and automatically restarts on file changes
- Always write unit tests for new features. For changes to existing code, ensure that existing tests are updated accordingly.
- All python files must pass Pylance linting and type checking and all JavaScript files must pass ESLint linting and type checking.

### Container Management 
- When working in containers, use the appropriate environment variables for container-specific URLs and ports
- **IMPORTANT**: Always use relative URLs (`/api/v1`) in development mode, not absolute URLs (`http://localhost:8000/api/v1`)
- Test endpoints are configured to use environment variables for backend URLs to support different deployment scenarios
- If experiencing CORS issues, verify that frontend is using Vite proxy configuration with relative URLs
