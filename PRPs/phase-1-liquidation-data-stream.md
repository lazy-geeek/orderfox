# Phase 1: Liquidation Data Stream - Skeleton Implementation

## Overview
Implement a new data stream for Binance liquidation orders with direct WebSocket connection (not available in CCXT Pro). Display liquidations in a new table component positioned to the right of trades, below the chart.

## Context & Resources
- **Binance Liquidation Stream Docs**: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Liquidation-Order-Streams
- **WebSocket Base URL**: `wss://fstream.binance.com`
- **Stream Format**: `<symbol>@forceOrder`
- **Reference Implementation**: `backend/app/api/v1/endpoints/trades_ws.py` and `frontend_vanilla/src/components/LastTradesDisplay.js`

## Implementation Blueprint

### 1. Backend WebSocket Service
Create `backend/app/services/liquidation_service.py`:
```python
import asyncio
import json
import websockets
from typing import Optional, Dict, List
from datetime import datetime
import logging

class LiquidationService:
    """Service for connecting to Binance liquidation streams"""
    
    def __init__(self):
        self.base_url = "wss://fstream.binance.com"
        self.active_connections: Dict[str, asyncio.Task] = {}
        self.data_callbacks: Dict[str, List] = {}
        
    async def connect_to_liquidation_stream(self, symbol: str, callback):
        """
        Connect to Binance liquidation stream for a specific symbol
        
        TODO Phase 2:
        - Implement WebSocket connection logic
        - Handle ping/pong for keepalive
        - Process liquidation messages
        - Format data for frontend (thin client pattern)
        - Handle reconnection on disconnect
        """
        pass
        
    def format_liquidation_data(self, raw_data: Dict) -> Dict:
        """
        Format liquidation data for frontend display
        
        TODO Phase 2:
        - Extract order details from raw message
        - Calculate price in USDT (quantity * average price)
        - Format numbers with appropriate precision
        - Return camelCase fields for frontend
        
        Expected output format:
        {
            "symbol": "BTCUSDT",
            "side": "SELL",
            "quantity": "0.014",
            "priceUsdt": "138.74",  # Calculated: quantity * avgPrice
            "timestamp": 1568014460893,
            "displayTime": "14:27:40"
        }
        """
        pass
        
    async def disconnect_stream(self, symbol: str):
        """Disconnect from liquidation stream"""
        # TODO Phase 2: Implement disconnection logic
        pass

# Singleton instance
liquidation_service = LiquidationService()
```

### 2. Backend WebSocket Endpoint
Create `backend/app/api/v1/endpoints/liquidations_ws.py`:
```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.api.v1.endpoints.connection_manager import manager
from app.services.symbol_service import symbol_service
from app.services.liquidation_service import liquidation_service
import logging

router = APIRouter()

@router.websocket("/liquidations/{display_symbol}")
async def liquidation_stream(websocket: WebSocket, display_symbol: str):
    """
    WebSocket endpoint for liquidation data streaming
    
    TODO Phase 2:
    - Validate and convert symbol using symbol_service
    - Accept WebSocket connection
    - Send initial empty data with proper structure
    - Connect to Binance liquidation stream
    - Stream formatted liquidation data to frontend
    - Handle disconnection and cleanup
    """
    await manager.accept(websocket)
    
    try:
        # Symbol validation
        symbol = display_symbol  # TODO: Use symbol_service.resolve_symbol_to_exchange_format
        
        # Send initial data structure
        initial_data = {
            "type": "liquidations",
            "symbol": display_symbol,
            "data": [],
            "initial": True,
            "timestamp": None
        }
        await manager.send_json(websocket, initial_data)
        
        # TODO Phase 2: Connect to liquidation stream and process data
        
        # Keep connection alive
        await asyncio.Event().wait()
        
    except WebSocketDisconnect:
        logging.info(f"Liquidations WebSocket disconnected for {display_symbol}")
    except Exception as e:
        logging.error(f"Error in liquidations WebSocket: {e}")
    finally:
        # TODO: Cleanup liquidation stream connection
        pass
```

### 3. Frontend Display Component
Create `frontend_vanilla/src/components/LiquidationDisplay.js`:
```javascript
import { subscribeToState } from '../store/stateManager.js';
import { WebSocketManager } from '../services/websocketManager.js';

export class LiquidationDisplay {
    constructor(container) {
        this.container = container;
        this.wsManager = null;
        this.isConnected = false;
        this.liquidations = [];
        this.maxLiquidations = 50;
        
        this.init();
    }
    
    init() {
        this.render();
        this.setupStateSubscriptions();
        this.setupWebSocket();
    }
    
    render() {
        // TODO Phase 2: Implement full HTML structure
        // Follow LastTradesDisplay pattern with:
        // - orderfox-display-base class
        // - Header with "Liquidations" title and connection status
        // - Table with Side, Quantity, Price (USDT) columns
        // - Scrollable content area
        
        this.container.innerHTML = `
            <div class="orderfox-liquidation-display orderfox-display-base">
                <div class="display-header">
                    <span class="display-title">Liquidations</span>
                    <div class="connection-status disconnected">
                        <span class="status-dot"></span>
                        <span class="status-text">Disconnected</span>
                    </div>
                </div>
                <div class="display-content">
                    <table class="liquidation-table">
                        <thead>
                            <tr>
                                <th>Side</th>
                                <th>Quantity</th>
                                <th>Price (USDT)</th>
                            </tr>
                        </thead>
                        <tbody id="liquidation-list">
                            <!-- Liquidations will be added here -->
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }
    
    setupWebSocket() {
        // TODO Phase 2: Implement WebSocket connection
        // - Use WebSocketManager for connection management
        // - Connect to /ws/liquidations/{symbol} endpoint
        // - Handle incoming liquidation data
        // - Update display with new liquidations
    }
    
    addLiquidation(liquidation) {
        // TODO Phase 2: Add new liquidation to display
        // - Create table row with proper styling
        // - Apply bid-price (green) or ask-price (red) class based on side
        // - Maintain maximum number of liquidations
        // - Add animation for new entries
    }
    
    updateConnectionStatus(connected) {
        // TODO Phase 2: Update connection indicator
        // Follow LastTradesDisplay pattern
    }
    
    setupStateSubscriptions() {
        // TODO Phase 2: Subscribe to symbol changes
        // Reconnect WebSocket when symbol changes
    }
    
    cleanup() {
        // TODO Phase 2: Cleanup WebSocket connections
        if (this.wsManager) {
            this.wsManager.disconnect();
        }
    }
}
```

### 4. Layout Updates
Update `frontend_vanilla/src/layouts/MainLayout.js`:
```javascript
// TODO Phase 2: Update grid layout to accommodate three components
// Modify .bottom-section CSS grid to:
// - Desktop: 3 columns (orderbook | trades | liquidations)
// - Tablet: 2 columns with liquidations below
// - Mobile: Stack all three vertically
```

### 5. CSS Styles
Add to `frontend_vanilla/styles.css`:
```css
/* Liquidation Display Styles */
.orderfox-liquidation-display {
    /* Inherits from .orderfox-display-base */
}

.liquidation-table {
    /* TODO Phase 2: Style similar to trades table */
}

/* Update grid layout for three components */
@media (min-width: 1024px) {
    .bottom-section {
        grid-template-columns: 1fr 1fr 1fr;
        /* TODO Phase 2: Adjust spacing */
    }
}
```

### 6. State Management
Update `frontend_vanilla/src/store/stateManager.js`:
```javascript
// Add liquidation-related state
const state = {
    // ... existing state
    liquidationsWsConnected: false,
    currentLiquidations: []
};

// Add update functions
export function setLiquidationsWsConnected(connected) {
    // TODO Phase 2: Implement
}

export function updateLiquidations(liquidations) {
    // TODO Phase 2: Implement
}
```

### 7. Testing Structure

#### Backend Tests
Create `backend/tests/services/test_liquidation_service.py`:
```python
# TODO Phase 2: Test liquidation service
# - Test WebSocket connection
# - Test data formatting
# - Test error handling
```

Create `backend/tests/api/v1/test_liquidations_ws.py`:
```python
# TODO Phase 2: Test WebSocket endpoint
# - Test connection acceptance
# - Test symbol validation
# - Test data streaming
```

#### Frontend Tests
Create `frontend_vanilla/tests/components/LiquidationDisplay.test.js`:
```python
# TODO Phase 2: Test component
# - Test rendering
# - Test WebSocket connection
# - Test data display
# - Test connection status
```

## Implementation Tasks (Phase 1)

1. ✅ Create skeleton `liquidation_service.py` with method signatures
2. ✅ Create skeleton `liquidations_ws.py` endpoint
3. ✅ Create skeleton `LiquidationDisplay.js` component
4. ✅ Add liquidation display container to MainLayout
5. ✅ Add basic CSS structure
6. ✅ Update state management with liquidation fields
7. ✅ Create test file structures

## Phase 2 Implementation Guide

1. **Backend Service Implementation**:
   - Use `websockets` library for async WebSocket client
   - Implement reconnection with exponential backoff
   - Format all data server-side (thin client pattern)
   - Handle symbol format conversion

2. **WebSocket Endpoint**:
   - Follow `trades_ws.py` pattern exactly
   - Use connection manager for WebSocket handling
   - Send proper initial data structure

3. **Frontend Component**:
   - Copy LastTradesDisplay patterns
   - Use WebSocketManager for connections
   - Trust backend data completely (no validation)

4. **Testing**:
   - Mock Binance WebSocket responses
   - Test reconnection scenarios
   - Verify data formatting

## Validation Gates

```bash
# Backend
cd /home/bail/github/orderfox/backend && python -m pytest tests/services/test_liquidation_service.py -v
cd /home/bail/github/orderfox/backend && python -m pytest tests/api/v1/test_liquidations_ws.py -v

# Frontend  
cd /home/bail/github/orderfox/frontend_vanilla && npm test -- LiquidationDisplay

# Linting
npm run lint
npm run typecheck
```

## Dependencies
- Backend: `websockets>=12.0` or `aiohttp>=3.9.0`
- Frontend: No new dependencies (uses existing WebSocket infrastructure)

## References
- Binance Liquidation Stream: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Liquidation-Order-Streams
- WebSocket Implementation: `/home/bail/github/orderfox/PRPs/research/binance-liquidation-stream/`
- Pattern Reference: `backend/app/api/v1/endpoints/trades_ws.py`

## Success Metrics
- Skeleton code structure in place
- All files created with proper imports
- Method signatures defined with clear TODOs
- Tests structure ready for Phase 2

**Confidence Score: 9/10** - Clear patterns to follow, detailed research completed