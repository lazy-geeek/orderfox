# Backend CLAUDE.md

Backend-specific guidance for OrderFox FastAPI application.

## Tech Stack

- Framework: FastAPI with async/await
- WebSocket: Real-time streaming with connection management
- Exchange: Binance API via ccxt and ccxt pro
- Data Processing: Pandas, custom formatting services
- Testing: Pytest with async support

## Code Quality

**All Python files must pass Pylance/pyright with zero errors:**
```bash
cd backend && pyright app/                  # Check all files
cd backend && pyright app/services/bot_service.py  # Check specific file
```

Expected output: `0 errors, 0 warnings, 0 informations`

## Architecture Patterns

### Thin Client Architecture
- Backend provides display-ready data (formatted, sorted, validated)
- camelCase fields via Pydantic `alias_generator=to_camel`
- Pre-formatted strings: `volume24hFormatted`, `priceUsdtFormatted`
- Complete objects for frontend (e.g., TradingView `priceFormat`)

### Exchange Service Patterns
- **Standard CCXT**: Synchronous methods (`exchange.fetch_trades()`)
- **CCXT Pro**: Async methods for WebSocket (`await exchange_pro.watch_trades()`)
- **Critical**: Never use `await` with standard CCXT methods
- **Testing**: Use `Mock()` for CCXT, `AsyncMock()` for CCXT Pro

### Symbol Service (Critical)
- **Single source of truth** for all symbol operations
- **Never bypass**: Always use `symbol_service.get_all_symbols()`
- **5-minute cache TTL** reduces API calls by 10x
- **Methods**:
  - `get_all_symbols()` - Symbol list with formatting
  - `validate_symbol_exists(symbol_id)` - Validation
  - `resolve_symbol_to_exchange_format(symbol_id)` - Conversion

### FastAPI Routing
- Define routes WITHOUT trailing slashes for consistency
- Exact path matching required (405 errors indicate mismatch)

## Service Implementations

### Order Book
- Aggregation in `orderbook_aggregation_service.py`
- Dynamic parameter updates via WebSocket messages
- TTL caching for 10x performance improvement

### Trades
- CCXT Pro for real-time streaming
- Historical + real-time merge in backend
- Formatting in `trade_service.py`

### Liquidations
- Direct Binance @forceOrder WebSocket stream
- Fan-out pattern for multiple subscribers
- Deduplication using timestamp + amount + side
- Volume aggregation for chart histogram

### Chart Data
- Container-width optimization: `min(max((width/6)*3, 200), 1000)`
- Time range caching for liquidation sync
- Dual time fields: `timestamp` (ms) and `time` (seconds)

### Moving Average
- `MovingAverageCalculator` class with O(1) operations
- 50-period SMA on non-zero liquidation volumes
- Performance targets: <1ms historical, <5ms real-time

## WebSocket Endpoints

```
ws://localhost:8000/api/v1/ws/orderbook?symbol=BTCUSDT&limit=20&rounding=0.25
ws://localhost:8000/api/v1/ws/trades/BTCUSDT
ws://localhost:8000/api/v1/ws/candles/BTCUSDT?timeframe=1m&container_width=800
ws://localhost:8000/api/v1/ws/liquidations/BTCUSDT
ws://localhost:8000/api/v1/ws/liquidations/BTCUSDT?timeframe=1m  # With volume
```

**Dynamic Updates (orderbook only):**
```json
{"type": "update_params", "limit": 50, "rounding": 0.5}
```

## Testing

```bash
# Run all tests with warning detection
./scripts/run-backend-tests.sh

# Debug specific test
python -m pytest tests/services/test_bot_service.py -v

# Real WebSocket testing pattern (not mocks)
from fastapi.testclient import TestClient
with TestClient(app).websocket_connect("/api/v1/ws/...") as websocket:
    # Test real WebSocket communication
```

## Common Tasks

### Add API Endpoint
1. Create in `app/api/v1/endpoints/`
2. Add to router in `app/api/v1/api.py`
3. Service logic in `app/services/`
4. Tests in `tests/`

### Modify Services
- Order Book: `orderbook_aggregation_service.py`
- Trades: `trade_service.py` 
- Liquidations: `liquidation_service.py`
- Chart: `chart_data_service.py`

## Environment Variables

```bash
BACKEND_PORT=8000
BACKEND_URL=http://localhost:8000
DATABASE_URL=postgresql://user:pass@localhost:5432/orderfox_db
BINANCE_API_KEY=your_key
BINANCE_SECRET_KEY=your_secret
BINANCE_WS_BASE_URL=wss://fstream.binance.com
LIQUIDATION_API_BASE_URL=https://api.example.com
```

## Performance Guidelines

- Use deque for fixed-size collections
- TTL caching for expensive operations
- Batch processing where possible
- Connection pooling for WebSockets
- Async/await for all I/O operations