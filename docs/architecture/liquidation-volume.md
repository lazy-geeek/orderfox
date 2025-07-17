# Liquidation Volume Architecture

## Overview

The liquidation volume system provides real-time and historical liquidation volume data aggregated by timeframe, displayed as a histogram overlay on TradingView charts. This document describes the architecture, data flow, and key design decisions.

## Architecture Components

### Backend Services

#### 1. Liquidation Service (`liquidation_service.py`)
- **Purpose**: Core service managing liquidation data streams and volume aggregation
- **Key Features**:
  - WebSocket connection to Binance @forceOrder stream
  - Real-time volume aggregation by timeframe
  - Fan-out pattern with reference counting
  - Persistent volume accumulation (not replacement)
  - Cache lifecycle management

#### 2. Liquidation WebSocket Endpoint (`liquidations_ws.py`)
- **Purpose**: WebSocket API endpoint for frontend connections
- **Key Features**:
  - Dual message types: `liquidation_order` and `liquidation_volume`
  - Global cache management for deduplication
  - Historical data integration on connection
  - Time range synchronization with chart data

### Frontend Components

#### 1. LightweightChart Component
- **Purpose**: TradingView chart integration with volume overlay
- **Key Features**:
  - Histogram series overlay for volume visualization
  - `update()` vs `setData()` pattern for data preservation
  - Chart initialization state management
  - Pending data buffering during initialization

#### 2. WebSocket Service
- **Purpose**: WebSocket connection management and message routing
- **Key Features**:
  - Message type discrimination
  - Real-time update flag handling
  - Connection lifecycle management

## Data Flow

### 1. Initial Connection Flow
```
Frontend → WebSocket Connect → Backend Endpoint
                                      ↓
                            Fetch Historical Data
                                      ↓
                            Send liquidation_order (table)
                                      ↓
                            Wait for Chart Time Range
                                      ↓
                            Send liquidation_volume (histogram)
```

### 2. Real-time Update Flow
```
Binance @forceOrder → Liquidation Service → Format Data
                                               ↓
                                    Distribute to Callbacks
                                               ↓
                            ┌──────────────────┴──────────────────┐
                            ↓                                     ↓
                    Table Callbacks                      Volume Callbacks
                    (liquidation_order)                  (liquidation_volume)
                            ↓                                     ↓
                    Frontend Table                        Chart Histogram
```

### 3. Volume Aggregation Flow
```
Raw Liquidation → Add to Buffer → Process Buffer (1s interval)
                                         ↓
                               Calculate Time Bucket
                                         ↓
                               Accumulate in accumulated_volumes
                                         ↓
                               Format Volume Data
                                         ↓
                               Notify Volume Callbacks
```

## Key Design Decisions

### 1. Message Type Separation
- **Problem**: Confusion between table and volume data
- **Solution**: Clear message types:
  - `liquidation_order`: Individual liquidations for table display
  - `liquidation_volume`: Aggregated volume for histogram display
- **Benefits**: Clear data routing, easier debugging

### 2. Volume Accumulation Pattern
- **Problem**: Historical data disappearing on updates
- **Solution**: 
  - Persistent `accumulated_volumes` dictionary
  - Accumulate instead of replace
  - Only send updated buckets in real-time
- **Benefits**: Complete data retention, efficient updates

### 3. TradingView Update Strategy
- **Problem**: `setData()` clears existing chart data
- **Solution**:
  - Use `setData()` only for initial load
  - Use `update()` for real-time updates
  - Check `is_update` flag from backend
- **Benefits**: Preserves zoom/pan state, maintains history

### 4. Cache Lifecycle Management
- **Problem**: Stale data persisting across reconnections
- **Solution**:
  - Clear caches on symbol disconnect
  - Reference counting for shared connections
  - Reset `historical_loaded` flags
- **Benefits**: Fresh data on reconnect, proper cleanup

### 5. Time Range Synchronization
- **Problem**: Volume data misaligned with visible candles
- **Solution**:
  - Chart service caches actual candle time range
  - Liquidation service polls for cached range
  - Uses same range for volume API calls
- **Benefits**: Perfect alignment at all zoom levels

## WebSocket Message Formats

### Liquidation Order Message
```json
{
  "type": "liquidation_order",
  "symbol": "BTCUSDT",
  "data": [{
    "symbol": "BTCUSDT",
    "side": "BUY",
    "quantity": "0.100",
    "quantityFormatted": "0.100",
    "priceUsdt": "50000",
    "priceUsdtFormatted": "50,000",
    "timestamp": 1700000000000,
    "displayTime": "12:00:00",
    "baseAsset": "BTC"
  }],
  "initial": true,
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

### Liquidation Volume Message
```json
{
  "type": "liquidation_volume",
  "symbol": "BTCUSDT",
  "timeframe": "1m",
  "data": [{
    "time": 1700000000,
    "buy_volume": "10000",
    "sell_volume": "5000",
    "total_volume": "15000",
    "delta_volume": "5000",
    "buy_volume_formatted": "10K",
    "sell_volume_formatted": "5K",
    "total_volume_formatted": "15K",
    "delta_volume_formatted": "5K",
    "count": 10,
    "timestamp_ms": 1700000000000
  }],
  "is_update": false,
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

## Performance Metrics

### Load Test Results
- **1500 liquidations over 30 minutes**:
  - Average processing: 0.17ms
  - Max processing: 0.43ms
  - Memory growth: 0.75MB

- **5 concurrent symbols**:
  - Memory per symbol: <0.1MB
  - Concurrent processing: <2s total

- **WebSocket performance**:
  - Average send time: 1.08ms
  - Max send time: 1.37ms
  - Cache size maintained at 50

## Troubleshooting

### Common Issues

1. **Historical data disappears**
   - Check: `is_update` flag handling
   - Verify: Using `update()` for real-time
   - Debug: Enable volume logging

2. **Volume bars misaligned with candles**
   - Check: Time range cache availability
   - Verify: Chart initialized before volume
   - Debug: Log time ranges

3. **Stale data after reconnect**
   - Check: Cache clearing on disconnect
   - Verify: Reference counting logic
   - Debug: Log cache operations

4. **Missing volume updates**
   - Check: Volume callback registration
   - Verify: Timeframe parameter present
   - Debug: Log aggregation buffer processing

### Debug Logging

Enable debug logging for troubleshooting:

```python
# Backend
logger.debug(f"Processing aggregation buffer for {symbol} {timeframe}")
logger.debug(f"Volume aggregation: buy={buy_volume}, sell={sell_volume}")

# Frontend
console.debug('Volume data received:', volumeData.length, 'points');
console.debug('Using update() for real-time update');
```

## API Endpoints

### REST API
- `GET /api/v1/liquidation-volume/{symbol}/{timeframe}?start={start_ms}&end={end_ms}`
  - Historical volume data for specific time range

### WebSocket
- `ws://localhost:8000/api/v1/ws/liquidations/{symbol}`
  - Liquidation orders only (table data)
  
- `ws://localhost:8000/api/v1/ws/liquidations/{symbol}?timeframe={timeframe}`
  - Both liquidation orders and volume data

## Configuration

### Environment Variables
```bash
LIQUIDATION_API_BASE_URL=https://api.example.com  # External API for historical data
BINANCE_WS_BASE_URL=wss://fstream.binance.com    # Binance futures WebSocket
```

### Supported Timeframes
- 1m, 5m, 15m, 30m (minutes)
- 1h, 4h (hours)
- 1d (daily)

## Future Enhancements

1. **Volume Alerts**
   - Threshold-based notifications
   - Unusual volume detection

2. **Extended Timeframes**
   - Weekly/monthly aggregations
   - Custom timeframe support

3. **Performance Optimizations**
   - Redis caching for volume data
   - Batch WebSocket updates

4. **Analytics Features**
   - Volume trends analysis
   - Liquidation heatmaps
   - Historical comparisons