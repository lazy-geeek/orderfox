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

### Critical: Pyright CLI for Accurate Type Checking
**🚨 IMPORTANT DISCOVERY**: The VS Code IDE diagnostic tools may not catch all Pylance errors that users see in their IDE. Always use pyright CLI for comprehensive type checking.

**Recommended Pylance Validation Workflow:**
```bash
# 🎯 PRIMARY TYPE CHECKING METHOD - Matches VS Code Pylance exactly
pyright app/                                    # Check entire app directory
pyright app/core/database.py                    # Check specific file
pyright --pythonversion 3.11 app/              # Check with specific Python version

# 📊 Expected output for clean code:
# "0 errors, 0 warnings, 0 informations"
```

**Why Use Pyright CLI:**
- **Exact Match**: Reproduces the same errors users see in VS Code Pylance
- **Real Error Detection**: Catches `reportArgumentType`, `reportGeneralTypeIssues`, and other Pylance diagnostics
- **Comprehensive**: More thorough than IDE diagnostic tools
- **CI/CD Ready**: Can be integrated into automated workflows

**Common Error Types Caught:**
- `reportArgumentType`: Type mismatches in function arguments (e.g., `None` passed to `str` parameter)
- `reportGeneralTypeIssues`: Async/await mismatches (e.g., awaiting non-awaitable objects)
- Import errors and missing type annotations
- Type compatibility issues across the codebase

**Integration Pattern:**
```bash
# Before committing any Python changes:
pyright app/ && echo "✅ All Python files pass Pylance validation"
```

## Testing

### Recommended Test Execution Approach

**PREFERRED: Use Chunked Test Execution System**
```bash
# 🚀 PRIMARY TESTING METHOD - Enhanced Script with Warning Detection
./scripts/run-backend-tests.sh                    # Run all chunks (1-8)
./scripts/run-backend-tests.sh 1 2 3             # Run specific chunks
./scripts/run-backend-tests.sh 7a 7b 7c          # Run sub-chunks

# 📊 Results Analysis
./scripts/analyze-test-results.sh                 # Comprehensive failure analysis
cat logs/test-results/execution-log.txt          # Execution timeline
cat logs/test-results/chunk*-warnings.txt        # Warning details per chunk
```

**FALLBACK: Direct PyTest (for individual test debugging)**
```bash
# Use direct pytest ONLY for debugging specific test failures
cd /home/bail/github/orderfox/backend

# Specific test file debugging
python -m pytest tests/services/test_orderbook_aggregation_service.py -v

# Individual test debugging  
python -m pytest tests/services/test_bot_service.py::TestBotService::test_create_bot -v

# WebSocket tests (use real WebSocket approach - see guidelines below)
python -m pytest tests/integration/test_orderbook_websocket_real.py -v
```

### Test Architecture & Organization

**Chunk-Based Test Organization:**
- **chunk1**: Foundation (Database, config, utilities) - 73 tests
- **chunk2**: Core Services (Symbol, exchange, formatting) - 116 tests  
- **chunk3**: Business Services (Bot, orderbook, chart data) - 109 tests
- **chunk4**: Advanced Services (Liquidation, trade, trading engine) - 137 tests
- **chunk5**: REST APIs (Schema, bot, market data) - 81 tests
- **chunk6**: WebSocket APIs (Connection, market, liquidations) - 42 tests
- **chunk7a**: Bot Integration (Paper trading flows) - 2 tests
- **chunk7b**: Data Flow Integration (E2E formatting, liquidation volume) - 11 tests  
- **chunk7c**: WebSocket Integration (Real WebSocket tests) - 25 tests
- **chunk8a**: Integration & E2E Tests (End-to-end data flow validation) - 6 tests
- **chunk8b**: Performance Tests (Response times, throughput, memory efficiency) - 6 tests
- **chunk8d**: Basic Load Tests (Aggregation latency, throughput, cache performance) - 4 tests
- **chunk8e**: Connection & Memory Tests (Connection performance, memory scaling) - 4 tests
- **chunk8f**: Scalability & Concurrency Tests (System limits, sustained load) - 3 tests
- **chunk8g**: Extended Load Tests (High-volume scenarios, extended runtime) - 5 tests

**Total: 617 tests across 37 test files**

### Enhanced Warning Detection & Proactive Maintenance

The test execution system includes comprehensive warning detection:

**Warning Categories Captured:**
- 🔴 **Runtime Issues**: Resource leaks, task cleanup, I/O errors
- 🟡 **Deprecation Warnings**: API deprecations requiring immediate action
- 🔵 **Code Quality Warnings**: General code improvement opportunities  
- 🟢 **Pytest Warnings**: Test configuration and optimization insights

**Warning Analysis Files:**
```bash
# View warning analysis for any chunk
cat logs/test-results/chunk*-warnings.txt

# LLM-actionable insights include:
# - Specific deprecation fixes (e.g., datetime.utcnow() → datetime.now(datetime.UTC))
# - Runtime issue resolution (WebSocket cleanup, async task management)
# - Test modernization opportunities
# - Configuration optimization recommendations
```

### Critical WebSocket Testing Breakthrough

**🚨 CRITICAL DISCOVERY: Use Real WebSocket Testing, NOT Mocks**

**Problem with Mock-Based WebSocket Tests:**
- Mock WebSocket tests fail due to message delivery issues
- Async lifecycle management problems in test environments
- Hanging tests and race conditions

**SOLUTION: Real WebSocket Testing Pattern**
```python
# ✅ CORRECT: Real WebSocket Testing with FastAPI TestClient
from fastapi.testclient import TestClient
from app.main import app

def test_real_websocket_connection():
    client = TestClient(app)
    with client.websocket_connect("/api/v1/ws/orderbook?symbol=BTCUSDT") as websocket:
        # Send real messages
        websocket.send_json({"type": "update_params", "limit": 50})
        
        # Receive real responses
        data = websocket.receive_json()
        assert data["type"] == "orderbook_update"
        
        # Real connection lifecycle management
        websocket.close()
```

**WebSocket Testing Guidelines:**
- **Real Connections**: Always use `TestClient.websocket_connect()` for WebSocket tests
- **Exchange Service Mocking**: Mock `exchange_service` for WebSocket tests, NOT `symbol_service`
- **Async Lifecycle**: Real WebSockets handle async cleanup properly
- **Resource Management**: Real connections prevent hanging and race conditions
- **Integration Testing**: Real WebSocket tests verify the complete connection pipeline

**Key Pattern for WebSocket Tests:**
```python
# Mock exchange_service to prevent external API calls
@pytest.fixture
def mock_exchange_service():
    with patch('app.services.exchange_service.get_exchange') as mock:
        exchange_mock = Mock()
        exchange_mock.fetch_order_book.return_value = {
            'bids': [[50000, 1.0]], 'asks': [[50001, 1.0]]
        }
        mock.return_value = exchange_mock
        yield mock

# Use real WebSocket connection with mocked data sources
def test_websocket_with_real_connection(mock_exchange_service):
    client = TestClient(app)
    with client.websocket_connect("/api/v1/ws/orderbook?symbol=BTCUSDT") as websocket:
        # Test real WebSocket communication with mocked data
```

### Test Execution Performance

**Optimized Execution Times:**
- Average chunk execution: 8-14 seconds (vs 45-90s estimates)
- Total suite execution: ~5-8 minutes for all chunks
- Enhanced with timeout handling and graceful failure recovery
- Real-time progress tracking and warning capture

**Benefits of Chunked Execution:**
- ✅ **Zero test failures** across all 617 tests (when properly executed)
- ✅ **Comprehensive warning detection** for proactive maintenance
- ✅ **Isolated chunk execution** prevents test interdependencies  
- ✅ **Enhanced error analysis** with pattern detection
- ✅ **Real-time progress monitoring** and result logging

### Test Infrastructure & Maintenance Workflow

**Enhanced Test Scripts:**
```bash
# Primary test execution system
./scripts/run-backend-tests.sh           # Main test execution with warning capture
./scripts/analyze-test-results.sh        # Intelligent failure and warning analysis
./scripts/add-test-markers.py            # Pytest marker management

# Test result structure
logs/test-results/
├── execution-log.txt                    # Complete execution timeline
├── chunk*-summary.txt                   # Per-chunk test results and metrics
├── chunk*-warnings.txt                  # LLM-actionable warning analysis
├── overall-summary.txt                  # Final comprehensive summary
└── last-run-status.txt                  # Execution status tracking
```

**Proactive Maintenance Workflow:**
1. **Regular Test Execution**: Run full test suite with `./scripts/run-backend-tests.sh`
2. **Warning Analysis**: Review generated warning files for deprecations and issues
3. **LLM-Driven Fixes**: Use warning files as input for targeted code improvements
4. **Trend Monitoring**: Track warning counts and patterns over time
5. **Test Modernization**: Apply pytest warnings insights for test suite optimization

**Test Marker System:**
```python
# Pytest markers for organized execution
@pytest.mark.chunk1     # Foundation tests
@pytest.mark.chunk2     # Core services  
@pytest.mark.chunk3     # Business services
@pytest.mark.chunk4     # Advanced services
@pytest.mark.chunk5     # REST APIs
@pytest.mark.chunk6     # WebSocket APIs
@pytest.mark.chunk7a    # Bot integration
@pytest.mark.chunk7b    # Data flow integration
@pytest.mark.chunk7c    # WebSocket integration
@pytest.mark.chunk8     # Performance tests
```

**Warning Categories & Actions:**
- **🔴 Runtime Issues (CRITICAL)**: Immediate fixes required - resource leaks, connection cleanup
- **🟡 Deprecations (HIGH)**: Update deprecated API usage before next Python/library version
- **🔵 Code Quality (MEDIUM)**: Improve code patterns and eliminate technical debt
- **🟢 Pytest Warnings (INFO)**: Optimize test configuration and modernize patterns

**Test Quality Metrics:**
- Test Success Rate: 100% (617/617 tests passing)
- Average Execution Time: 8-14 seconds per chunk
- Warning Detection: Comprehensive capture of all warning types
- Coverage: 37 test files across complete backend functionality

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

### FastAPI/Starlette Routing Patterns
- **Trailing Slash Behavior**: FastAPI/Starlette requires exact path matching including trailing slashes
- **Route Definition Rule**: If a route is defined WITH a trailing slash, requests MUST include it. If defined WITHOUT, requests must NOT include it
- **GET vs POST/PATCH/DELETE**: GET requests handle path mismatches more gracefully than other HTTP methods
- **Recommended Pattern**: Define all routes WITHOUT trailing slashes for consistency
- **Frontend Integration**: Ensure all frontend API calls match the exact path defined in backend routes
- **Common Error**: 405 Method Not Allowed often indicates trailing slash mismatch on POST/PATCH/DELETE requests
- **Example**:
  ```python
  # Good - consistent no trailing slashes
  @router.post("", response_model=BotPublic)  # POST /api/v1/bots
  @router.get("", response_model=BotList)     # GET /api/v1/bots
  
  # Bad - inconsistent trailing slashes
  @router.post("/", response_model=BotPublic)  # POST /api/v1/bots/
  @router.get("", response_model=BotList)      # GET /api/v1/bots
  ```

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
- **Delta Volume**: Backend calculates `delta_volume = buy_volume - sell_volume` for histogram display
- **Time Range Synchronization**: Uses exact same time range as candle data via cache coordination
- **Backend Coordination**: Liquidation WebSocket waits for candle time range to be cached before fetching data
- **Historical Data**: `fetch_historical_liquidations_by_timeframe()` with time range parameters
- **Real-time Aggregation**: Maintains aggregation buffers for live volume updates
- **Data Models**: `LiquidationVolume` and `LiquidationVolumeResponse` Pydantic models
- **WebSocket Messages**: Sends `liquidation_volume` type messages with aggregated data
- **Chart Integration**: Provides formatted volume data for TradingView histogram overlays
- **Performance**: Efficient time bucket calculations with proper caching
- **Accumulation Pattern**: Volume data accumulates in `accumulated_volumes` dictionary - NEVER replaced, only added to
- **Cache Lifecycle**: Global caches (`liquidations_cache`, `historical_loaded`) cleared when last subscriber disconnects
- **Message Type Separation**: 
  - `liquidation_order`: Individual liquidations for table display
  - `liquidation_volume`: Aggregated volume data for histogram display
- **Reference Counting**: Fan-out pattern tracks callbacks per symbol, only closes Binance connection when no subscribers remain
- **Debug Logging**: Use `logger.debug()` to track volume aggregation flow, cache operations, and message routing

### Chart Data Service
- **Container-Width Optimization**: Calculates optimal candle count based on container width: `min(max((containerWidth/6)*3, 200), 1000)`
- **Dual Time Fields**: Chart data includes both `timestamp` (ms) and `time` (seconds) for TradingView compatibility
- **Dynamic Price Precision**: Automatically adjusts decimal places based on symbol precision
- **Synchronous CCXT Usage**: Uses standard CCXT methods without await for chart data fetching
- **Time Range Caching**: Stores actual candle time ranges in `time_range_cache` for coordination with other services
- **Cache Key Format**: `{exchange_symbol}:{timeframe}` (e.g., "BTC/USDT:USDT:1m")
- **Time Range Data**: Includes `start_ms`, `end_ms`, `start`, and `end` fields for flexibility

### Time Range Synchronization System
- **Purpose**: Ensures liquidation volume data uses exact same time range as displayed candles
- **Implementation**: 
  - `ChartDataService` caches time range when fetching candles
  - Liquidation WebSocket polls cache for up to 10 seconds (100ms intervals)
  - Uses cached range for liquidation volume API call
  - Falls back to 24-hour range if cache unavailable
- **Backend Coordination**: All timing logic handled server-side, frontend just connects WebSockets
- **Benefits**: Perfect alignment between candles and liquidation volume at all zoom levels

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

### Working with Bot Management
1. **Bot CRUD Operations**: Use `bot_service.py` for all bot database operations
2. **Database Models**: Bot models defined in `backend/app/models/bot.py`
3. **API Endpoints**: Bot endpoints in `backend/app/api/v1/endpoints/bots.py`
4. **Testing**: Bot tests in `backend/tests/api/v1/test_bots.py` and `backend/tests/services/test_bot_service.py`
5. **Database Sessions**: Use dependency injection for database sessions

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

# Database Configuration
DATABASE_URL=postgresql://orderfox_user:orderfox_password@localhost:5432/orderfox_db

# Exchange API
BINANCE_API_KEY=your_key
BINANCE_SECRET_KEY=your_secret

# Optional Backend Settings
MAX_ORDERBOOK_LIMIT=50
DEBUG=true/false
CORS_ORIGINS=http://localhost:3000
LIQUIDATION_API_BASE_URL=https://api.example.com
```

### Database Configuration
- **Single DATABASE_URL**: Use one environment variable that gets configured based on environment
- **Development**: Use main database (e.g., `orderfox_db`)
- **Testing**: Set different DATABASE_URL for tests (e.g., `orderfox_test_db`)
- **Production**: Use production database URL
- **Async URL**: Automatically generated by replacing `postgresql://` with `postgresql+asyncpg://`

### Why Single DATABASE_URL?
- **Simplicity**: One variable instead of multiple confusing variables
- **Environment-based**: Different environments use different database URLs
- **Standard Practice**: Follows standard deployment patterns (Heroku, Railway, etc.)
- **No Duplication**: No need for separate sync/async URLs

### Environment-based Configuration Examples
```bash
# Development (.env)
DATABASE_URL=postgresql://orderfox_user:orderfox_password@localhost:5432/orderfox_db

# Testing
DATABASE_URL=postgresql://orderfox_test_user:orderfox_test_password@localhost:5433/orderfox_test_db

# Production
DATABASE_URL=postgresql://prod_user:prod_password@db.example.com:5432/orderfox_prod
```

## Performance Considerations

- **Caching**: Use TTL-based caching for expensive operations
- **Connection Pooling**: Reuse WebSocket connections where possible
- **Async Operations**: Use async/await for I/O operations
- **Batch Processing**: Process data in batches for efficiency
- **Memory Management**: Use deque for fixed-size collections