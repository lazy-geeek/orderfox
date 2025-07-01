# Binance Partial Depth Stream Specifications

## Overview
Binance partial depth streams provide real-time order book updates with a limited number of price levels. They are more efficient than full depth streams for applications that only need the top levels of the order book.

## Stream Types

### USDT-M Futures Partial Depth Streams
- **Stream Name**: `<symbol>@depth<levels>`
- **Available Levels**: 5, 10, 20
- **Update Speed**: 100ms or 250ms (configurable with @100ms suffix)
- **WebSocket URL**: `wss://fstream.binance.com/ws/<symbol>@depth<levels>`
- **Example**: `wss://fstream.binance.com/ws/btcusdt@depth10`

### Message Format
```json
{
  "e": "depthUpdate",      // Event type
  "E": 1640995200000,      // Event time
  "T": 1640995200000,      // Transaction time
  "s": "BTCUSDT",          // Symbol
  "U": 157,                // First update ID in event
  "u": 160,                // Final update ID in event
  "pu": 149,               // Previous final update ID
  "b": [                   // Bids to be updated
    ["7403.89", "0.002"],  // [price, quantity]
    ["7403.88", "3.100"]
  ],
  "a": [                   // Asks to be updated
    ["7405.96", "3.340"],  // [price, quantity]
    ["7406.63", "0.024"]
  ]
}
```

## Key Differences from Full Depth Streams

1. **Limited Levels**: Only provides top 5, 10, or 20 levels
2. **Snapshot Updates**: Each message contains the current snapshot of top levels
3. **No Accumulation**: Unlike full depth, partial depth messages are complete snapshots
4. **Lower Bandwidth**: Significantly reduces data transfer for common use cases

## Integration Considerations

### Advantages
- Lower bandwidth usage
- Faster processing (fewer levels to handle)
- Suitable for most trading displays
- Real-time updates at 100ms intervals

### Limitations
- Maximum 20 levels available
- Not suitable for deep market analysis
- Cannot build complete order book
- No historical depth beyond specified levels

## Current Implementation Issues

The current implementation in `connection_manager.py` has the following challenges:

1. **Library Mismatch**: Uses `websockets` library instead of `ccxtpro`
2. **Integration Complexity**: Different message handling compared to existing streams
3. **State Management**: Needs separate connection handling from ccxtpro streams
4. **Error Handling**: Requires additional error recovery logic

## Recommended Fix Approach

1. **Use ccxtpro**: Check if ccxtpro supports Binance partial depth streams natively
2. **Unified Connection**: Maintain single WebSocket connection approach
3. **Message Translation**: Ensure consistent message format across all streams
4. **Fallback Logic**: Implement smooth fallback to full depth when needed

## Testing Requirements

1. Test with various symbols (high/low volume pairs)
2. Verify data accuracy against full depth streams
3. Monitor connection stability
4. Measure bandwidth savings
5. Test error recovery scenarios