# Backend CLAUDE.md

This file provides backend-specific guidance to Claude Code when working with the OrderFox backend codebase.

## Backend Architecture Overview

OrderFox backend is built with FastAPI and Python, providing real-time market data and trading capabilities through WebSocket connections and RESTful APIs.

**Tech Stack:**
- Framework: FastAPI with async/await support
- WebSocket: Real-time data streaming with connection management
- Exchange Integration: Binance API via ccxt and ccxt pro
- Data Processing: Pandas for aggregation, custom formatting services
- Testing: Pytest with async support

## Code Quality Standards

### Python/Pylance Requirements
- **Type Checking**: Use Pylance in VS Code for comprehensive type checking
- **All Python files must pass Pylance validation with zero diagnostics**
- **Pylance handles**: Type checking, import validation, unused variables, code style
- **No flake8 or autopep8**: Pylance is the only linting tool used
- **Type Hints**: All functions should have proper type annotations

## Testing

### Backend Testing Commands
```bash
# Run all backend tests (use absolute path)
cd /home/bail/github/orderfox/backend && python -m pytest tests/ -v

# Specific test file
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

### WebSocket Testing Guidelines
- **Mock Services**: Use `symbol_service` mocks for WebSocket tests, not `exchange_service`
- **Async Mocks**: Use `AsyncMock()` for async methods like `chart_data_service.get_initial_chart_data`
- **Method Signatures**: Update connection manager calls to use `display_symbol` parameter
- **Test Data**: Include `volume24h_formatted` and `priceFormat` fields in symbol mock data

## Architecture Patterns

### Thin Client Architecture
- **Backend Data Contract**: Backend provides display-ready data with all formatting, validation, and business logic processed server-side
- **camelCase API Convention**: Backend uses Pydantic `alias_generator=to_camel` for JavaScript-friendly field names (`uiName`, `volume24hFormatted`)
- **Pre-formatted Data**: All numerical values include formatted string versions (e.g., `volume24hFormatted`, `priceUsdtFormatted`)
- **Pre-sorted Data**: All data arrays (candles, trades, orderbook) are pre-sorted before transmission
- **Complete Objects**: Backend generates full objects for frontend consumption (e.g., TradingView `priceFormat`)

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

## Service Implementations

### Order Book System
- **Backend Aggregation**: All order book processing happens server-side in `orderbook_aggregation_service.py`
- **WebSocket Updates**: Real-time data with dynamic parameter updates
- **Caching**: TTL-based caching for performance (10x improvement)
- **Pre-formatted Data**: Backend sends formatted strings to frontend
- **Dynamic Parameters**: Support for limit and rounding adjustments without reconnection

### Last Trades System
- **Real-time Streaming**: Live trade data via WebSocket with CCXT Pro integration
- **Backend Processing**: Trade data formatting and validation in `trade_service.py`
- **Historical + Real-time Merge**: Backend maintains unified trade history
- **Exchange Data Only**: No mock data fallbacks - proper error handling when exchange unavailable
- **WebSocket Endpoint**: Implemented in `trades_ws.py`

### Liquidation Data Stream System
- **Binance Futures Integration**: Direct WebSocket connection to Binance @forceOrder stream
- **Backend Processing**: `liquidation_service.py` handles WebSocket connections, data formatting, and symbol conversion
- **Historical Data Integration**: Fetches last 50 liquidations from external API on WebSocket connection
- **Number Formatting**: 
  - Amount (USDT) rounded to whole numbers with comma thousand separators
  - Quantity formatted using `formatting_service` based on symbol's `amountPrecision`
  - Backend provides `baseAsset` field for dynamic header updates
- **Data Ordering**: Liquidations sorted with newest first using deque with appendleft for real-time data
- **Thin Client Architecture**: Backend provides formatted data with `quantityFormatted`, `priceUsdtFormatted`, and `displayTime`
- **API Integration**: Uses `fetch_historical_liquidations()` with configurable LIQUIDATION_API_BASE_URL
- **Fan-out Architecture**: Single Binance connection per symbol shared between multiple frontend subscribers (table + chart)
- **Connection Reference Counting**: `disconnect_stream(symbol, callback)` removes specific callbacks, only closes Binance connection when no subscribers remain
- **Deduplication System**: Prevents duplicate liquidation entries using `timestamp + amount + side` as unique keys
- **Global Cache Management**: `historical_loaded` flag ensures historical data fetched only once per symbol across all connections
- **Connection Sharing Logging**: Backend logs show "Adding callback to existing stream" when multiple components subscribe to same symbol

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

### Liquidation Volume Aggregation System
- **REST API Endpoint**: `/api/v1/liquidation-volume/{symbol}/{timeframe}` for historical volume data
- **WebSocket Integration**: Timeframe parameter support for liquidation streams
- **Data Aggregation**: `aggregate_liquidations_for_timeframe()` method groups liquidations by time buckets
- **Timeframe Support**: 1m, 5m, 15m, 30m, 1h, 4h, 1d timeframes for volume aggregation
- **Volume Calculation**: Separates buy volume (shorts liquidated) and sell volume (longs liquidated)
- **Historical Data**: `fetch_historical_liquidations_by_timeframe()` with time range parameters
- **Real-time Aggregation**: Maintains aggregation buffers for live volume updates
- **Data Models**: `LiquidationVolume` and `LiquidationVolumeResponse` Pydantic models
- **WebSocket Messages**: Sends `liquidation_volume` type messages with aggregated data
- **Chart Integration**: Provides formatted volume data for TradingView histogram overlays
- **Performance**: Efficient time bucket calculations with proper caching

### Chart Data Service
- **Container-Width Optimization**: Calculates optimal candle count based on container width: `min(max((containerWidth/6)*3, 200), 1000)`
- **Dual Time Fields**: Chart data includes both `timestamp` (ms) and `time` (seconds) for TradingView compatibility
- **Dynamic Price Precision**: Automatically adjusts decimal places based on symbol precision
- **Synchronous CCXT Usage**: Uses standard CCXT methods without await for chart data fetching

## WebSocket Protocol

### Available Endpoints

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

Connect to liquidations stream with volume aggregation:
```
ws://localhost:8000/api/v1/ws/liquidations/BTCUSDT?timeframe=1m
```

### Dynamic Parameter Updates
Update parameters without reconnecting (order book only):
```json
{
  "type": "update_params",
  "limit": 50,
  "rounding": 0.5
}
```

### Connection Management
- **Backend**: Connection management in `connection_manager.py`
- **Automatic Cleanup**: Handles disconnections and resource cleanup
- **Error Handling**: Graceful error handling with proper WebSocket close codes

## Common Tasks

### Adding a New API Endpoint
1. Create endpoint in `backend/app/api/v1/endpoints/`
2. Add to router in `backend/app/api/v1/api.py`
3. Create service logic in `backend/app/services/`
4. Add tests in `backend/tests/`
5. Follow FastAPI patterns and use dependency injection

### Modifying Order Book Processing
1. Update aggregation logic in `orderbook_aggregation_service.py`
2. Adjust formatting in `formatting_service.py`
3. Update WebSocket endpoint in `orderbook_ws.py` if needed
4. Add/update tests for aggregation logic

### Modifying Trade Processing
1. Update trade processing in `trade_service.py`
2. Adjust WebSocket streaming in `trades_ws.py`
3. Ensure historical and real-time data merge correctly
4. Update tests for trade formatting

### Modifying Liquidation Processing
1. Update liquidation processing in `liquidation_service.py`
2. Adjust WebSocket endpoint in `liquidations_ws.py`
3. Note: Uses Binance futures API directly, not CCXT, for @forceOrder stream
4. Ensure API data conversion matches WebSocket format

### Modifying Chart Data
1. Update chart data processing in `chart_data_service.py`
2. Adjust WebSocket data streaming in `market_data_ws.py`
3. Ensure container width calculations are correct
4. Verify time field formats for TradingView compatibility

### Working with Symbol Service (CRITICAL)
1. **Always use Symbol Service**: Never call exchange directly for symbol operations
2. **Get all symbols**: Use `symbol_service.get_all_symbols()` for symbol lists
3. **Symbol validation**: Use `symbol_service.validate_symbol_exists(symbol_id)`
4. **Symbol conversion**: Use `symbol_service.resolve_symbol_to_exchange_format(symbol_id)`
5. **Testing**: Mock `symbol_service.get_all_symbols()` instead of exchange methods
6. **Performance**: Symbol Service automatically handles caching and deduplication
7. **Error handling**: Symbol Service provides graceful fallbacks to demo symbols
8. **HTTP endpoints**: Use Symbol Service methods, not direct exchange calls

## Error Handling

- **Exception Handling**: Comprehensive exception handling in FastAPI with proper HTTP status codes
- **WebSocket Errors**: Graceful WebSocket error handling with reconnection support
- **Logging**: Structured logs with request timing and correlation IDs
- **Health Check**: GET /health endpoint for monitoring
- **Exchange Errors**: Proper handling of exchange API errors with fallbacks
- **Connection Lifecycle**: Proper handling of "Cannot call 'send' once a close message has been sent" errors during frontend disconnection
- **Race Condition Prevention**: Backend waits for proper WebSocket cleanup before processing new connections

## Environment Variables

Backend-specific environment variables:
```bash
# Backend Configuration
BACKEND_PORT=8000
BACKEND_URL=http://localhost:8000
BINANCE_WS_BASE_URL=wss://fstream.binance.com

# Exchange API
BINANCE_API_KEY=your_key
BINANCE_SECRET_KEY=your_secret

# Optional Backend Settings
MAX_ORDERBOOK_LIMIT=50
DEBUG=true/false
CORS_ORIGINS=http://localhost:3000
LIQUIDATION_API_BASE_URL=https://api.example.com
```

## Performance Considerations

- **Caching**: Use TTL-based caching for expensive operations
- **Connection Pooling**: Reuse WebSocket connections where possible
- **Async Operations**: Use async/await for I/O operations
- **Batch Processing**: Process data in batches for efficiency
- **Memory Management**: Use deque for fixed-size collections