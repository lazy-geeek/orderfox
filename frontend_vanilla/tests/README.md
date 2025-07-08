# Frontend Tests for Price Precision Feature

This directory contains unit and integration tests for the dynamic price precision feature implemented for TradingView Lightweight Charts.

## Test Structure

```
tests/
├── components/
│   └── LightweightChart.test.js    # Unit tests for price precision and race condition fixes
├── services/
│   └── websocketManager.test.js    # Unit tests for WebSocket manager race condition fixes
├── integration/
│   └── price-precision.test.js     # Integration tests for main.js flow
├── setup.js                        # Global test setup and mocks
└── README.md                       # This file
```

## Test Coverage

### Unit Tests (LightweightChart.test.js)

Tests the core price precision logic and race condition fixes:

✅ **Default Precision Tests**
- Default precision when symbolData is missing pricePrecision
- Default precision when symbolData is null

✅ **Valid Precision Tests**
- BTC/USDT (1 decimal)
- XRP/USDT (4 decimals) 
- High-precision tokens (7 decimals)

✅ **Invalid Precision Handling**
- Clamping to maximum of 8
- Handling negative values as invalid
- Non-numeric values fallback
- Null values fallback
- NaN values fallback

✅ **Edge Cases**
- Decimal precision values (floored)
- Zero precision handling
- Boundary value clamping (0-8)

✅ **MinMove Calculation**
- Correct minMove for all precision levels (0-8)

✅ **Race Condition and WebSocket Validation**
- Symbol validation logic (prevents wrong symbol updates)
- Timeframe validation logic (prevents wrong timeframe updates)
- Timestamp age validation (prevents old data updates)
- Chart data reset logic (complete state cleanup)
- Context change detection (symbol/timeframe switches)

### Integration Tests (price-precision.test.js)

Tests the complete flow from symbol data selection to precision application:

✅ **Symbol Data Flow**
- Symbol selection from symbolsList array
- Different precision levels per symbol
- Missing precision handling

✅ **Performance Optimization Validation**
- Real-time updates don't pass symbol data
- Symbol changes do pass symbol data
- Performance pattern validation

### Unit Tests (websocketManager.test.js)

Tests WebSocket manager race condition fixes and connection management:

✅ **TimeFrame Switching Bug Fix**
- Critical bug fix: Store old timeframe before updating state
- Handle multiple rapid timeframe switches correctly
- Demonstrate old buggy behavior vs fixed behavior
- Handle edge case with same timeframe selection

✅ **Symbol Switching Race Condition Prevention**
- Reject candles for old symbol after switch
- Handle candles without symbol field gracefully

✅ **Stream Key Management**
- Generate correct stream keys for different combinations
- Create unique stream keys for different symbol/timeframe combinations

✅ **Connection State Management**
- Handle connection state transitions correctly (connecting, connected, disconnected, error)

## Running Tests

```bash
# Run all tests
npm test

# Run tests once (CI mode)
npm run test:run

# Run tests with UI
npm run test:ui
```

## Test Framework

- **Framework**: Vitest (Vite's testing framework)
- **Environment**: jsdom
- **Mocking**: vi (Vitest's mocking utilities)
- **Assertions**: expect (Vitest's assertion library)

## Key Testing Principles

1. **Logic Testing**: Tests extract and test the exact precision logic from the implementation
2. **Error Handling**: Comprehensive testing of edge cases and invalid inputs
3. **Performance Validation**: Ensures real-time updates don't include unnecessary precision data
4. **Integration Validation**: Tests the complete flow from main.js pattern

## Test Results

All 43 tests pass, validating:
- ✅ Default precision application (2 decimals)
- ✅ Dynamic precision based on symbol data
- ✅ Robust error handling with fallbacks
- ✅ Performance optimization patterns
- ✅ Complete precision range (0-8 decimals)
- ✅ MinMove calculation accuracy
- ✅ Race condition prevention in symbol/timeframe switching
- ✅ WebSocket connection isolation and management
- ✅ Timestamp validation and ordering protection
- ✅ Chart state reset and context change detection