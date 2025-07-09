name: "Last Trades Feature Implementation"
description: |

## Purpose
Implement a real-time Last Trades table for OrderFox that displays the most recent 100 trades for the selected cryptocurrency symbol. The feature follows the existing architecture patterns where all data processing happens on the backend and is streamed via WebSocket to the frontend for display.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in CLAUDE.md

---

## Goal
Build a real-time Last Trades table that:
- Displays below the order book with the last 100 trades
- Updates in real-time as new trades occur
- Switches data when symbol changes
- Matches the visual style of the order book
- Shows price, amount, and time columns with dynamic currency labels
- Colors trades based on buy/sell side (green/red)
- Column headers update to show base/quote currencies (e.g., "Price (USDT)", "Amount (BTC)")

## Why
- **Business value**: Provides traders with essential market activity information
- **User impact**: Helps users understand recent price movements and trading volume
- **Integration**: Complements existing order book and chart features
- **Problems solved**: Currently users cannot see recent trade history, which is critical for trading decisions

## What
**User-visible behavior:**
- Table showing last 100 trades below order book
- Real-time updates as trades occur
- Color-coded buy (green) and sell (red) trades
- Proper price/amount precision per symbol
- Scrollable if content exceeds view height
- Dark mode support

**Technical requirements:**
- Backend fetches historical trades via CCXT `fetch_trades()`
- Real-time trades via CCXT Pro `watch_trades()`
- WebSocket streaming with initial batch + updates
- Frontend displays pre-formatted data
- Symbol switching clears and reloads trades

### Success Criteria
- [ ] Last trades table displays below order book
- [ ] Shows 100 most recent trades with price, amount, time
- [ ] Real-time updates work smoothly
- [ ] Symbol switching updates trades correctly
- [ ] Buy/sell color coding works
- [ ] Dark mode styling applied
- [ ] All tests pass and linting succeeds

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://docs.ccxt.com/#/ccxt.pro.manual?id=watchTrades
  why: CCXT Pro watch_trades method for real-time trade streaming
  
- url: https://docs.ccxt.com/#/?id=public-api
  why: CCXT fetch_trades method for historical trades
  
- file: /home/bail/github/orderfox/backend/app/api/v1/endpoints/market_data_ws.py
  why: WebSocket endpoint patterns, symbol validation, error handling
  
- file: /home/bail/github/orderfox/backend/app/api/v1/endpoints/connection_manager.py
  why: Stream management patterns, broadcast mechanism, mock data fallback
  
- file: /home/bail/github/orderfox/frontend_vanilla/src/components/OrderBookDisplay.js
  why: Component structure pattern for similar table display

- file: /home/bail/github/orderfox/frontend_vanilla/src/services/websocketManager.js
  why: WebSocket connection management, symbol switching pattern

- file: /home/bail/github/orderfox/backend/app/services/formatting_service.py
  why: Price and amount formatting patterns
  
- doc: Trade data structure from CCXT
  critical: |
    {
        'id': '12345',            # Trade ID
        'timestamp': 1502962946216,  # Unix timestamp in ms
        'datetime': '2017-08-17 12:42:48.000',
        'symbol': 'ETH/BTC',     # Unified symbol
        'side': 'buy',           # 'buy' or 'sell'
        'price': 0.06917684,     # Price per unit
        'amount': 1.5,           # Amount in base currency
        'cost': 0.10376526       # Total cost
    }
```

### Current Codebase tree
```bash
orderfox/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── market_data_ws.py
│   │   │   │   └── connection_manager.py
│   │   │   └── schemas.py
│   │   └── services/
│   │       ├── exchange_service.py
│   │       ├── symbol_service.py
│   │       └── formatting_service.py
│   └── tests/
└── frontend_vanilla/
    ├── src/
    │   ├── components/
    │   │   ├── OrderBookDisplay.js
    │   │   └── MainLayout.js
    │   ├── services/
    │   │   ├── websocketManager.js
    │   │   └── websocketService.js
    │   └── store/
    │       └── store.js
    └── tests/
```

### Desired Codebase tree with files to be added
```bash
orderfox/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── trades_ws.py          # NEW: WebSocket endpoint for trades
│   │   │   │   └── connection_manager.py # MODIFY: Add trades streaming
│   │   │   └── schemas.py                # MODIFY: Add Trade schema
│   │   └── services/
│   │       └── trade_service.py          # NEW: Trade fetching and formatting
│   └── tests/
│       └── services/
│           └── test_trade_service.py     # NEW: Trade service tests
└── frontend_vanilla/
    ├── src/
    │   ├── components/
    │   │   └── LastTradesDisplay.js      # NEW: Trades table component
    │   ├── services/
    │   │   └── websocketManager.js       # MODIFY: Add trades connection
    │   └── store/
    │       └── store.js                  # MODIFY: Add trades state
    ├── tests/
    │   └── components/
    │       └── LastTradesDisplay.test.js # NEW: Component tests
    └── main.js                           # MODIFY: Initialize trades component
```

### Known Gotchas of our codebase & Library Quirks
```python
# CRITICAL: CCXT Pro requires checking if exchange supports watchTrades
# Example: if exchange.has['watchTrades']:

# CRITICAL: Binance futures symbol format differs from spot
# Spot: 'BTC/USDT', Futures: 'BTC/USDT:USDT'

# CRITICAL: CCXT trade timestamp is in milliseconds, not seconds

# CRITICAL: Backend must format all data - frontend only displays
# No calculations or formatting in frontend

# CRITICAL: WebSocket first message must contain 'initial': true flag

# CRITICAL: Symbol validation must use symbol_service.resolve_symbol_to_exchange_format()

# CRITICAL: Mock data must be realistic with proper timestamps

# CRITICAL: Don't send currency info with every trade update
# Frontend gets base/quote assets from state.symbolsList
```

## Implementation Blueprint

### Data models and structure

```python
# backend/app/api/v1/schemas.py - Add to existing file
class Trade(BaseModel):
    """Trade data structure"""
    id: str
    price: float
    amount: float
    side: Literal["buy", "sell"]
    timestamp: int  # Unix timestamp in milliseconds
    price_formatted: str
    amount_formatted: str
    time_formatted: str  # HH:MM:SS format

class TradesUpdate(BaseModel):
    """WebSocket trades update message"""
    type: Literal["trades_update"] = "trades_update"
    symbol: str
    trades: List[Trade]
    initial: bool = False  # True for first batch of historical trades
```

### List of tasks to be completed in order

```yaml
Task 1 - Create Trade Service:
CREATE backend/app/services/trade_service.py:
  - MIRROR pattern from: backend/app/services/orderbook_aggregation_service.py
  - Import exchange_service, symbol_service, formatting_service
  - Implement fetch_recent_trades(symbol, limit=100)
  - Implement format_trade(trade, symbol_info) method
  - Add proper error handling for network/exchange errors
  - Include mock trade generation for testing

Task 2 - Create WebSocket Endpoint:
CREATE backend/app/api/v1/endpoints/trades_ws.py:
  - MIRROR pattern from: backend/app/api/v1/endpoints/market_data_ws.py
  - Use @router.websocket("/ws/trades/{symbol}")
  - Validate symbol using symbol_service
  - Fetch initial trades with trade_service
  - Send initial batch with 'initial': true
  - Handle WebSocket lifecycle

Task 3 - Modify Connection Manager:
MODIFY backend/app/api/v1/endpoints/connection_manager.py:
  - ADD trades streaming support
  - FIND pattern: "async def _stream_ticker"
  - INJECT similar method: "_stream_trades"
  - Use stream key format: f"{symbol}:trades"
  - Implement mock trades streaming fallback

Task 4 - Update Schemas:
MODIFY backend/app/api/v1/schemas.py:
  - ADD Trade and TradesUpdate models as shown above
  - Ensure proper validation with Pydantic

Task 5 - Create Frontend Component:
CREATE frontend_vanilla/src/components/LastTradesDisplay.js:
  - MIRROR pattern from: OrderBookDisplay.js
  - Create table structure with Price, Amount, Time columns
  - Ensure column alignment matches orderbook (use same CSS classes)
  - Use existing .bid-price (green) and .ask-price (red) classes
  - Implement createLastTradesDisplay() and updateLastTradesDisplay()
  - Add connection status indicator
  - Make container scrollable with max-height

Task 6 - Update Frontend State:
MODIFY frontend_vanilla/src/store/store.js:
  - ADD to state object:
    currentTrades: [],
    tradesLoading: false,
    tradesError: null,
    tradesWsConnected: false
  - ADD computed property for selected symbol data:
    getSelectedSymbolData() - returns full symbol object from symbolsList
  - Add corresponding setter methods

Task 7 - Update WebSocket Manager:
MODIFY frontend_vanilla/src/services/websocketManager.js:
  - ADD trades WebSocket handling
  - FIND pattern: "initializeConnections" method
  - ADD trades connection initialization
  - Handle trades in switchSymbol() method

Task 8 - Update Main Layout:
MODIFY frontend_vanilla/src/components/MainLayout.js:
  - ADD placeholder div for trades below orderbook
  - Use id="last-trades-container"

Task 9 - Initialize Component:
MODIFY frontend_vanilla/main.js:
  - Import LastTradesDisplay component
  - Initialize after OrderBookDisplay
  - Subscribe to state changes
  - On selectedSymbol change:
    - Get symbol data from state.symbolsList
    - Call updateTradesHeaders(symbolData)
  - On trades update: call updateLastTradesDisplay

Task 10 - Create Tests:
CREATE backend/tests/services/test_trade_service.py:
  - Test fetch_recent_trades with mock data
  - Test format_trade with various precisions
  - Test error handling

CREATE frontend_vanilla/tests/components/LastTradesDisplay.test.js:
  - Test component creation
  - Test trade updates
  - Test color coding logic

Task 11 - Update API Router:
MODIFY backend/app/api/v1/api.py:
  - Import trades_ws router
  - Include router with prefix="/trades"
```

### Per task pseudocode

```javascript
// Task 9 - main.js integration
import { createLastTradesDisplay, updateLastTradesDisplay, updateTradesHeaders } from './components/LastTradesDisplay';

// Initialize trades display
createLastTradesDisplay();

// Subscribe to symbol changes
store.subscribe('selectedSymbol', () => {
    const symbol = store.getState().selectedSymbol;
    const symbolData = store.getState().symbolsList.find(s => s.id === symbol);
    
    if (symbolData) {
        // Update column headers with new currency labels
        updateTradesHeaders(symbolData);
    }
});

// Subscribe to trades updates
store.subscribe('currentTrades', () => {
    const trades = store.getState().currentTrades;
    updateLastTradesDisplay(trades);
});
```

```python
# Task 1 - Trade Service
class TradeService:
    async def fetch_recent_trades(self, symbol: str, limit: int = 100):
        # Validate symbol exists
        symbol_info = symbol_service.get_symbol_info(symbol)
        if not symbol_info:
            raise ValueError(f"Unknown symbol: {symbol}")
        
        # Get exchange instance
        exchange = exchange_service.get_exchange()
        
        try:
            # Fetch trades from exchange
            trades = await exchange.fetch_trades(symbol, limit=limit)
            
            # Format each trade
            formatted_trades = []
            for trade in trades:
                formatted_trade = self.format_trade(trade, symbol_info)
                formatted_trades.append(formatted_trade)
            
            # Return most recent trades first (newest at top)
            # Limit to 100 trades max
            return formatted_trades[-100:][::-1]
            
        except ccxt.NetworkError as e:
            logger.error(f"Network error fetching trades: {str(e)}")
            raise HTTPException(status_code=503, detail="Network error")
    
    def format_trade(self, trade: dict, symbol_info: dict) -> Trade:
        # Extract precision from symbol info
        price_precision = symbol_info.get('pricePrecision', 2)
        amount_precision = symbol_info.get('amountPrecision', 8)
        
        # Format price and amount
        price_formatted = formatting_service.format_price(
            trade['price'], 
            precision=price_precision
        )
        amount_formatted = formatting_service.format_amount(
            trade['amount'],
            precision=amount_precision
        )
        
        # Format time as HH:MM:SS (local time)
        dt = datetime.fromtimestamp(trade['timestamp'] / 1000)
        time_formatted = dt.strftime('%H:%M:%S')
        
        return Trade(
            id=str(trade['id']),
            price=trade['price'],
            amount=trade['amount'],
            side=trade['side'],
            timestamp=trade['timestamp'],
            price_formatted=price_formatted,
            amount_formatted=amount_formatted,
            time_formatted=time_formatted
        )

# Task 3 - Connection Manager modifications
async def _stream_trades(self, symbol: str, websocket: WebSocket):
    """Stream real-time trades via CCXT Pro"""
    exchange_pro = self.exchange_service.get_exchange_pro()
    
    if not exchange_pro or not exchange_pro.has.get('watchTrades'):
        # Fallback to mock trades
        await self._stream_mock_trades(symbol, websocket)
        return
    
    # Keep last 100 trades
    trades_cache = deque(maxlen=100)
    
    while True:
        try:
            # Watch for new trades
            new_trades = await exchange_pro.watch_trades(symbol)
            
            # Format and add to cache
            symbol_info = self.symbol_service.get_symbol_info(symbol)
            for trade in new_trades:
                formatted = self.trade_service.format_trade(trade, symbol_info)
                trades_cache.appendleft(formatted)
            
            # Send update
            update = TradesUpdate(
                symbol=symbol,
                trades=list(trades_cache),
                initial=False
            )
            
            await self.broadcast_to_stream(
                f"{symbol}:trades",
                update.dict()
            )
            
        except Exception as e:
            logger.error(f"Error streaming trades: {str(e)}")
            break

# Task 5 - Frontend Component
export function createLastTradesDisplay() {
    const container = document.getElementById('last-trades-container');
    if (!container) return;
    
    container.innerHTML = `
        <div class="orderbook-container">
            <div class="orderbook-header">
                <span class="orderbook-title">Trades</span>
                <span class="connection-status" id="trades-connection-status">
                    <span class="status-dot"></span>
                </span>
            </div>
            <div class="orderbook-content trades-container">
                <table class="orderbook-table">
                    <thead>
                        <tr>
                            <th class="price-header" id="trades-price-header">Price</th>
                            <th class="amount-header" id="trades-amount-header">Amount</th>
                            <th class="time-header">Time</th>
                        </tr>
                    </thead>
                    <tbody id="trades-tbody">
                        <!-- Trades will be inserted here -->
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

export function updateLastTradesDisplay(trades) {
    const tbody = document.getElementById('trades-tbody');
    if (!tbody) return;
    
    // Clear existing trades
    tbody.innerHTML = '';
    
    // Add each trade
    trades.forEach(trade => {
        const row = document.createElement('tr');
        const sideClass = trade.side === 'buy' ? 'bid-price' : 'ask-price';
        
        row.innerHTML = `
            <td class="${sideClass}">${trade.price_formatted}</td>
            <td class="${sideClass}">${trade.amount_formatted}</td>
            <td>${trade.time_formatted}</td>
        `;
        
        tbody.appendChild(row);
    });
}

export function updateTradesHeaders(symbolData) {
    // Update column headers with currency labels
    const priceHeader = document.getElementById('trades-price-header');
    const amountHeader = document.getElementById('trades-amount-header');
    
    if (priceHeader && symbolData?.quote_asset) {
        priceHeader.textContent = `Price (${symbolData.quote_asset})`;
    }
    
    if (amountHeader && symbolData?.base_asset) {
        amountHeader.textContent = `Amount (${symbolData.base_asset})`;
    }
}
```

### Integration Points
```yaml
DATABASE:
  - No database changes required (real-time data only)
  
CONFIG:
  - No new config needed (uses existing exchange config)
  
ROUTES:
  - add to: backend/app/api/v1/api.py
  - pattern: "api_router.include_router(trades_ws.router, prefix='/trades')"
  
WEBSOCKET:
  - endpoint: "/ws/trades/{symbol}" (prefixed to /api/v1/ws/trades/{symbol})
  - message format: TradesUpdate schema
  
STATE:
  - add to: frontend_vanilla/src/store/store.js
  - properties: currentTrades, tradesLoading, tradesError, tradesWsConnected
  
CSS:
  - add to: frontend_vanilla/src/style.css
  - classes: Use existing .bid-price for buy trades (green)
  - classes: Use existing .ask-price for sell trades (red)
  - container: .trades-container { max-height: 400px; overflow-y: auto; }
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Backend - Run these FIRST
cd backend
# Pylance will handle all Python validation in VS Code
# Use mcp__ide__getDiagnostics to check for any issues

# Frontend
cd frontend_vanilla
npm run lint              # ESLint check
npm run lint:fix          # Auto-fix issues

# Expected: No errors. If errors, READ and fix.
```

### Level 2: Unit Tests
```python
# CREATE backend/tests/services/test_trade_service.py
import pytest
from app.services.trade_service import TradeService

@pytest.mark.asyncio
async def test_fetch_recent_trades_success():
    """Test fetching trades returns formatted data"""
    service = TradeService()
    trades = await service.fetch_recent_trades("BTCUSDT", limit=10)
    
    assert len(trades) <= 10
    assert all(hasattr(t, 'price_formatted') for t in trades)
    assert all(hasattr(t, 'time_formatted') for t in trades)

@pytest.mark.asyncio
async def test_fetch_recent_trades_invalid_symbol():
    """Test invalid symbol raises appropriate error"""
    service = TradeService()
    with pytest.raises(ValueError, match="Unknown symbol"):
        await service.fetch_recent_trades("INVALID", limit=10)

def test_format_trade():
    """Test trade formatting with different precisions"""
    service = TradeService()
    trade = {
        'id': '123',
        'price': 108905.123456,
        'amount': 0.12345678,
        'side': 'buy',
        'timestamp': 1736267157000
    }
    symbol_info = {
        'pricePrecision': 1,
        'amountPrecision': 3
    }
    
    formatted = service.format_trade(trade, symbol_info)
    assert formatted.price_formatted == "108,905.1"
    assert formatted.amount_formatted == "0.123"
    assert ':' in formatted.time_formatted
```

```javascript
// CREATE frontend_vanilla/tests/components/LastTradesDisplay.test.js
import { describe, it, expect, beforeEach } from 'vitest';
import { createLastTradesDisplay, updateLastTradesDisplay } from '../../src/components/LastTradesDisplay';

describe('LastTradesDisplay', () => {
    beforeEach(() => {
        document.body.innerHTML = '<div id="last-trades-container"></div>';
    });

    it('should create trades display structure', () => {
        createLastTradesDisplay();
        
        const container = document.querySelector('.orderbook-container');
        expect(container).toBeTruthy();
        
        const headers = document.querySelectorAll('th');
        expect(headers).toHaveLength(3);
        expect(headers[0].textContent).toBe('Price (USDT)');
    });

    it('should update trades with correct colors', () => {
        createLastTradesDisplay();
        
        const trades = [
            {
                id: '1',
                side: 'buy',
                price_formatted: '108,905.1',
                amount_formatted: '0.240',
                time_formatted: '13:25:57'
            },
            {
                id: '2',
                side: 'sell',
                price_formatted: '108,904.0',
                amount_formatted: '0.100',
                time_formatted: '13:25:56'
            }
        ];
        
        updateLastTradesDisplay(trades);
        
        const rows = document.querySelectorAll('tbody tr');
        expect(rows).toHaveLength(2);
        
        const buyTrade = rows[0].querySelector('.trade-buy');
        expect(buyTrade).toBeTruthy();
        
        const sellTrade = rows[1].querySelector('.trade-sell');
        expect(sellTrade).toBeTruthy();
    });
});
```

```bash
# Run backend tests
cd backend
python -m pytest tests/services/test_trade_service.py -v

# Run frontend tests
cd frontend_vanilla
npm run test:run
```

### Level 3: Integration Test
```bash
# Start the application
npm run dev

# Test the WebSocket endpoint
wscat -c ws://localhost:8000/api/v1/ws/trades/BTCUSDT

# Expected: Initial batch of trades with "initial": true
# Then continuous updates as trades occur

# Test symbol switching
# 1. Connect to BTCUSDT trades
# 2. Disconnect
# 3. Connect to ETHUSDT trades
# Expected: Different trade data for each symbol
```

## Final validation Checklist
- [ ] All tests pass: `cd backend && python -m pytest tests/ -v`
- [ ] No backend diagnostics: Use Pylance in VS Code
- [ ] No frontend linting errors: `cd frontend_vanilla && npm run lint`
- [ ] WebSocket connection works: Test with wscat
- [ ] Symbol switching works correctly
- [ ] Buy trades show in green, sell trades in red
- [ ] Dark mode styling applied correctly
- [ ] Trades table shows below order book
- [ ] Real-time updates work smoothly
- [ ] Documentation updated in CLAUDE.md if needed

---

## Anti-Patterns to Avoid
- ❌ Don't format prices/amounts in frontend - backend only
- ❌ Don't fetch trades directly from frontend - use WebSocket
- ❌ Don't create new WebSocket patterns - follow existing
- ❌ Don't skip symbol validation - always validate
- ❌ Don't ignore CCXT Pro capabilities check
- ❌ Don't hardcode precision values - use symbol info

## Confidence Score: 9/10

The PRP is comprehensive with clear implementation steps following existing patterns. The only minor uncertainty is around specific CCXT Pro behavior for trade streaming, but the mock fallback pattern ensures the feature will work regardless.