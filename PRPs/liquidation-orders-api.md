name: "Liquidation Orders API Integration - Historical Data Enhancement"
description: |

## Purpose
Enhance the existing liquidation data stream by integrating historical liquidation orders from an external API to provide users with immediate context upon connection, mixing historical data with real-time WebSocket updates following the established trades pattern.

## Core Principles
1. **Context is King**: Follow OrderFox thin client architecture - backend handles all processing
2. **Validation Loops**: Comprehensive testing for API integration and data mixing
3. **Information Dense**: Use existing patterns from trade_service for historical+realtime data
4. **Progressive Success**: Start with API integration, validate, then mix with WebSocket
5. **Global rules**: Follow all rules in CLAUDE.md

---

## Goal
Integrate historical liquidation orders from an external API (liqui_api) to provide users with the last 50 liquidation orders immediately upon WebSocket connection, then seamlessly mix incoming real-time liquidations while maintaining a fixed list size of 50 entries.

## Why
- **User Experience**: Currently users see empty liquidation display until new liquidations occur
- **Context Enhancement**: Historical data provides immediate market context for traders
- **Feature Parity**: Matches the trades display which shows historical trades on connection
- **Market Insight**: 50 liquidations provide sufficient context for market sentiment analysis

## What
- Fetch last 50 liquidation orders from external API on WebSocket connection
- Calculate USDT values using same logic as real-time stream (quantity × average_price)
- Mix historical data with incoming real-time liquidations
- Maintain fixed list of 50 most recent liquidations (FIFO)
- Add configurable API base URL to backend .env file

### Success Criteria
- [ ] Historical liquidations appear immediately on WebSocket connection
- [ ] USDT calculations match real-time stream format
- [ ] List maintains exactly 50 items with proper FIFO behavior
- [ ] Seamless transition from historical to mixed historical+realtime data
- [ ] Proper error handling when API is unavailable
- [ ] No performance degradation from API calls

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://github.com/lazy-geeek/liqui_api
  why: External API documentation for fetching historical liquidations
  endpoints:
    - GET /api/liquidation-orders?symbol=BTCUSDT&limit=50
    - Returns array of liquidation orders with fields matching Binance format
  
- file: /home/bail/github/orderfox/backend/app/services/trade_service.py
  why: Pattern for mixing historical data with real-time streams
  critical: fetch_recent_trades() method shows API integration pattern
  
- file: /home/bail/github/orderfox/backend/app/api/v1/endpoints/trades_ws.py
  why: WebSocket pattern for sending historical data on connection
  critical: _stream_trades() shows deque usage and cache initialization
  
- file: /home/bail/github/orderfox/backend/app/services/liquidation_service.py
  why: Current liquidation service to enhance with API integration
  critical: format_liquidation() method for consistent data formatting
  
- file: /home/bail/github/orderfox/backend/app/core/config.py
  why: Pattern for adding new environment variables
  critical: Settings class pattern for typed configuration

- file: /home/bail/github/orderfox/backend/app/api/v1/endpoints/liquidations_ws.py
  why: Current WebSocket endpoint to enhance
  critical: liquidations_cache deque pattern already exists
```

### Current Codebase Structure
```bash
orderfox/backend/
├── app/
│   ├── api/v1/endpoints/
│   │   ├── liquidations_ws.py    # WebSocket endpoint (needs modification)
│   │   └── trades_ws.py          # Reference pattern for historical data
│   ├── services/
│   │   ├── liquidation_service.py # Service to enhance with API calls
│   │   └── trade_service.py       # Reference pattern for API integration
│   └── core/
│       └── config.py              # Add new env variable here
└── tests/
    └── services/
        └── test_liquidation_service.py # Update tests for new functionality
```

### Known Gotchas & Patterns
```python
# CRITICAL: Liquidation API returns different field names than Binance WebSocket
# API fields: order_trade_time, order_filled_accumulated_quantity, average_price
# WS fields: T (time), q (quantity), p (avgPrice)

# PATTERN: Use aiohttp for async HTTP calls (already in requirements)
# Example from codebase: No existing HTTP client pattern - need to establish

# CRITICAL: Symbol format differences
# API expects: BTCUSDT (uppercase)
# Need to validate and convert symbol format

# PATTERN: Deque with maxlen for fixed-size lists
# liquidations_cache = deque(maxlen=50)  # Already exists in liquidations_ws.py

# GOTCHA: Calculate USDT value consistently
# amount_usdt = float(quantity) * float(average_price)

# PATTERN: Environment variables with defaults
# LIQUIDATION_API_BASE_URL: str = os.getenv("LIQUIDATION_API_BASE_URL", "")
```

## Implementation Blueprint

### Data Models and Structure

```python
# Existing liquidation format (keep unchanged for backwards compatibility)
{
    "symbol": "BTCUSDT",
    "side": "SELL",
    "quantity": "0.014",
    "quantityFormatted": "0.014000",
    "priceUsdt": "138.74",
    "priceUsdtFormatted": "138",
    "timestamp": 1568014460893,
    "displayTime": "14:27:40",
    "avgPrice": "9910",
    "baseAsset": "BTC"
}

# API Response format (from liqui_api)
{
    "symbol": "BTCUSDT",
    "side": "sell",  # lowercase - needs conversion
    "order_type": "LIMIT",
    "time_in_force": "GTC", 
    "original_quantity": "0.5",  # NOT USED - use order_filled_accumulated_quantity
    "price": "45000.00",
    "average_price": "45000.00",
    "order_status": "FILLED",
    "order_last_filled_quantity": "0.5",
    "order_filled_accumulated_quantity": "0.5",  # USE THIS for quantity
    "order_trade_time": 1609459200000
}
```

### List of tasks to be completed in order

```yaml
Task 1 - Add Environment Variable:
MODIFY backend/app/core/config.py:
  - FIND pattern: "BINANCE_API_BASE_URL"
  - ADD after: LIQUIDATION_API_BASE_URL configuration
  - PATTERN: Use same Optional[str] pattern with empty string default

Task 2 - Enhance Liquidation Service with API Integration:
MODIFY backend/app/services/liquidation_service.py:
  - ADD: aiohttp client session initialization
  - ADD: fetch_historical_liquidations() method
  - PATTERN: Follow trade_service.py structure for API calls
  - ADD: _convert_api_to_ws_format() helper method
  - ENSURE: Proper error handling with fallback to empty list

Task 3 - Update WebSocket Endpoint:
MODIFY backend/app/api/v1/endpoints/liquidations_ws.py:
  - MODIFY: _stream_liquidations() to fetch historical on connection
  - PATTERN: Follow trades_ws.py pattern for cache initialization
  - ENSURE: Only fetch historical once per connection
  - PRESERVE: Existing deque(maxlen=50) behavior

Task 4 - Add Tests:
MODIFY backend/tests/services/test_liquidation_service.py:
  - ADD: Test for fetch_historical_liquidations()
  - ADD: Test for API format conversion
  - ADD: Test for API error handling
  - PATTERN: Mock aiohttp responses

Task 5 - Update Backend .env:
MODIFY backend/.env:
  - ADD: LIQUIDATION_API_BASE_URL= (empty for user to fill)
  - ADD: Comment explaining the variable purpose
```

### Task 1: Add Environment Variable
```python
# In backend/app/core/config.py, after BINANCE_API_BASE_URL
LIQUIDATION_API_BASE_URL: Optional[str] = os.getenv("LIQUIDATION_API_BASE_URL", "")

# Add validation in __post_init__
if self.LIQUIDATION_API_BASE_URL:
    logger.info(f"Liquidation API configured: {self.LIQUIDATION_API_BASE_URL}")
else:
    logger.warning("LIQUIDATION_API_BASE_URL not set - historical liquidations disabled")
```

### Task 2: Liquidation Service Enhancement
```python
# Pseudocode for liquidation_service.py additions
import aiohttp
from typing import List, Optional

class LiquidationService:
    def __init__(self):
        # ... existing code ...
        self._http_session: Optional[aiohttp.ClientSession] = None
        
    async def _get_http_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session for API calls"""
        if not self._http_session:
            self._http_session = aiohttp.ClientSession()
        return self._http_session
        
    async def fetch_historical_liquidations(self, symbol: str, limit: int = 50) -> List[Dict]:
        """Fetch historical liquidations from external API"""
        if not settings.LIQUIDATION_API_BASE_URL:
            return []
            
        try:
            session = await self._get_http_session()
            url = f"{settings.LIQUIDATION_API_BASE_URL}/api/liquidation-orders"
            params = {"symbol": symbol.upper(), "limit": limit}
            
            async with session.get(url, params=params, timeout=5) as response:
                if response.status != 200:
                    logger.warning(f"API returned {response.status}")
                    return []
                    
                data = await response.json()
                # Convert API format to our WebSocket format
                return [self._convert_api_to_ws_format(item) for item in data]
                
        except Exception as e:
            logger.error(f"Failed to fetch historical liquidations: {e}")
            return []
            
    def _convert_api_to_ws_format(self, api_data: Dict) -> Dict:
        """Convert API response to match WebSocket format"""
        # Calculate USDT value using filled quantity
        quantity = float(api_data.get("order_filled_accumulated_quantity", 0))
        avg_price = float(api_data.get("average_price", 0))
        amount_usdt = quantity * avg_price
        
        # Get symbol info for formatting
        symbol_info = self._get_symbol_info(api_data["symbol"])
        
        # Format using existing format_liquidation pattern
        return {
            "symbol": api_data["symbol"],
            "side": api_data["side"].upper(),  # API returns lowercase
            "quantity": str(quantity),
            "quantityFormatted": self._format_quantity(quantity, symbol_info),
            "priceUsdt": str(amount_usdt),
            "priceUsdtFormatted": f"{int(amount_usdt):,}",
            "timestamp": api_data["order_trade_time"],
            "displayTime": self._format_time(api_data["order_trade_time"]),
            "avgPrice": api_data["average_price"],
            "baseAsset": symbol_info.get("baseAsset", "")
        }
```

### Task 3: WebSocket Endpoint Update
```python
# Modifications to liquidations_ws.py
async def _stream_liquidations(self, websocket, display_symbol: str):
    """Stream liquidations with historical data on connection"""
    # ... existing validation ...
    
    # Initialize cache with historical data (only once)
    if display_symbol not in self._liquidations_cache:
        self._liquidations_cache[display_symbol] = deque(maxlen=50)
        
        # Fetch historical liquidations
        historical = await liquidation_service.fetch_historical_liquidations(
            exchange_symbol, limit=50
        )
        
        # Add to cache (oldest first so newest are at front after real-time arrives)
        for liquidation in reversed(historical):
            self._liquidations_cache[display_symbol].append(liquidation)
            
        # Send initial historical data
        if historical:
            await websocket.send_json({
                "type": "liquidations",
                "data": list(self._liquidations_cache[display_symbol])
            })
    
    # ... rest of existing streaming logic ...
```

### Integration Points
```yaml
CONFIG:
  - add to: backend/app/core/config.py
  - pattern: "LIQUIDATION_API_BASE_URL: Optional[str] = os.getenv('LIQUIDATION_API_BASE_URL', '')"
  
ENV:
  - add to: backend/.env
  - content: |
      # External Liquidation API Configuration
      # Base URL for historical liquidation data (e.g., https://api.example.com)
      LIQUIDATION_API_BASE_URL=
  
DEPENDENCIES:
  - verify: aiohttp already in requirements.txt
  - no new dependencies needed
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run from backend directory
cd /home/bail/github/orderfox/backend

# Python linting and type checking
python -m mypy app/services/liquidation_service.py
python -m mypy app/api/v1/endpoints/liquidations_ws.py

# Expected: No errors
```

### Level 2: Unit Tests
```python
# Add to test_liquidation_service.py
@pytest.mark.asyncio
async def test_fetch_historical_liquidations_success():
    """Test successful API call for historical liquidations"""
    service = LiquidationService()
    
    # Mock API response (using HYPERUSDT for testing)
    mock_response = [{
        "symbol": "HYPERUSDT",
        "side": "sell",
        "order_filled_accumulated_quantity": "1000",
        "average_price": "0.2500",
        "order_trade_time": 1609459200000
        # ... other fields
    }]
    
    with aioresponses() as mocked:
        mocked.get(
            f"{settings.LIQUIDATION_API_BASE_URL}/api/liquidation-orders",
            payload=mock_response
        )
        
        result = await service.fetch_historical_liquidations("HYPERUSDT")
        
        assert len(result) == 1
        assert result[0]["symbol"] == "HYPERUSDT"
        assert result[0]["side"] == "SELL"  # Uppercase
        assert result[0]["priceUsdt"] == "250.0"  # 1000 * 0.25

@pytest.mark.asyncio
async def test_fetch_historical_liquidations_api_error():
    """Test graceful handling of API errors"""
    service = LiquidationService()
    
    with aioresponses() as mocked:
        mocked.get(
            f"{settings.LIQUIDATION_API_BASE_URL}/api/liquidation-orders",
            status=500
        )
        
        result = await service.fetch_historical_liquidations("HYPERUSDT")
        assert result == []  # Empty list on error

def test_convert_api_to_ws_format():
    """Test API response format conversion"""
    service = LiquidationService()
    
    api_data = {
        "symbol": "HYPERUSDT",
        "side": "buy",
        "order_filled_accumulated_quantity": "500",
        "average_price": "0.3000",
        "order_trade_time": 1609459200000
    }
    
    result = service._convert_api_to_ws_format(api_data)
    
    assert result["side"] == "BUY"
    assert result["priceUsdt"] == "150.0"
    assert result["priceUsdtFormatted"] == "150"
    assert "displayTime" in result
```

```bash
# Run tests
cd /home/bail/github/orderfox/backend
python -m pytest tests/services/test_liquidation_service.py -v -k "historical"
```

### Level 3: Integration Test
```bash
# Start backend (API URL should be set in .env file)
cd /home/bail/github/orderfox/backend
python -m uvicorn app.main:app --reload

# Test WebSocket connection (using HYPERUSDT for more liquidation activity)
wscat -c ws://localhost:8000/api/v1/ws/liquidations/HYPERUSDT

# Expected initial message with historical data:
# {"type": "liquidations", "data": [...50 historical liquidations...]}

# Then real-time updates:
# {"type": "liquidation", "data": {...new liquidation...}}
```

### Manual Testing Script
```python
# test_liquidation_integration.py
import asyncio
import websockets
import json

async def test_liquidation_stream():
    uri = "ws://localhost:8000/api/v1/ws/liquidations/HYPERUSDT"
    
    async with websockets.connect(uri) as websocket:
        # Should receive historical data immediately
        first_message = await websocket.recv()
        data = json.loads(first_message)
        
        assert data["type"] == "liquidations"
        assert len(data["data"]) <= 50
        print(f"Received {len(data['data'])} historical liquidations")
        
        # Check format of first liquidation
        if data["data"]:
            first = data["data"][0]
            assert all(key in first for key in [
                "symbol", "side", "quantityFormatted", 
                "priceUsdtFormatted", "displayTime"
            ])
            print("Format validation passed")

asyncio.run(test_liquidation_stream())
```

## Final Validation Checklist
- [ ] All backend tests pass: `cd /home/bail/github/orderfox/backend && python -m pytest tests/ -v`
- [ ] No linting errors: `npm run lint` (from root)
- [ ] No type errors: `mcp__ide__getDiagnostics` shows zero diagnostics
- [ ] Historical liquidations appear on WebSocket connection
- [ ] USDT calculations are correct and formatted properly
- [ ] List maintains exactly 50 items with FIFO behavior
- [ ] API errors handled gracefully (empty list fallback)
- [ ] Performance: API call completes within 5 seconds
- [ ] Environment variable documented in .env file

## Anti-Patterns to Avoid
- ❌ Don't fetch historical data on every WebSocket message
- ❌ Don't block WebSocket connection while fetching API data
- ❌ Don't mix different formatting patterns - use existing format_liquidation
- ❌ Don't forget to handle API timeouts and errors
- ❌ Don't hardcode API URL - use environment variable
- ❌ Don't create new WebSocket message types - use existing "liquidations" and "liquidation"
- ❌ Don't modify frontend - it already handles the expected data format

---

## Implementation Notes

1. **Performance Consideration**: The API call happens once per WebSocket connection, not on every reconnect or symbol change.

2. **Error Resilience**: If the API fails, the stream continues with real-time data only (graceful degradation).

3. **Data Consistency**: The same formatting logic is used for both historical and real-time data to ensure consistency.

4. **Testing Strategy**: Mock the external API in tests to avoid dependencies and ensure reliable test execution.

5. **Security**: The API base URL is configurable via environment variable, allowing different endpoints for dev/staging/prod.

## Confidence Score: 9/10

This PRP provides comprehensive context for one-pass implementation. The only uncertainty is the exact response format from the liqui_api (the documentation shows examples but not complete schemas), but the error handling and conversion logic should handle variations gracefully.