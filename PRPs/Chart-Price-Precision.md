# PRP: Chart Price Scale Precision Implementation

## Overview
This PRP details the implementation of dynamic price scale precision for the TradingView Lightweight Charts component in OrderFox. The chart currently displays prices with only 2 decimal places, which is insufficient for many cryptocurrency assets. The solution involves configuring the chart to use the symbol's price precision already available from the backend.

## Context and Current State

### Backend Symbol Service
- The backend already provides `pricePrecision` for each symbol via `/api/v1/symbols` endpoint
- Price precision is extracted from exchange data: `market["precision"]["price"]`
- Data structure in frontend: `state.symbolsList[].pricePrecision`
- File: `backend/app/services/symbol_service.py` lines 70-110

### Frontend Current State
- Chart component: `frontend_vanilla/src/components/LightweightChart.js`
- Symbol data is stored in: `frontend_vanilla/src/store/store.js`
- Chart receives updates via `updateCandlestickChart()` function
- Currently NO price precision configuration in the chart

### Lightweight Charts API
The TradingView Lightweight Charts library supports price formatting through:
1. Series-level `priceFormat` option with `precision` property
2. Chart-level `localization.priceFormatter` for custom formatting
3. Price scale formatting options

Documentation: https://tradingview.github.io/lightweight-charts/docs/api

## Implementation Approach

### Key Insight: Price Precision is Symbol-Specific, Not Tick-Specific
Price precision is a property of the trading symbol itself and only needs to be set:
- Once during initial chart creation (with a default value)
- When the symbol changes

It does NOT need to be updated with every candle/tick update.

### 1. Set Default Precision in Chart Creation
Update `createCandlestickChart()` to include default price format:

```javascript
// In createCandlestickChart()
candlestickSeries = chart.addCandlestickSeries({
  upColor: isDark ? '#26a69a' : '#26a69a',
  downColor: isDark ? '#ef5350' : '#ef5350',
  // ... existing options ...
  priceFormat: {
    type: 'price',
    precision: 2, // Default precision
    minMove: 0.01, // Default minimum price movement
  },
});
```

### 2. Modify Chart Update Logic
Update the chart component to handle symbol-specific precision:

```javascript
// In main.js, only pass symbol data when it's actually needed:

// Case 1: Symbol change (need to update price precision)
case 'selectedSymbol':
  const selectedSymbolData = state.symbolsList.find(s => s.id === state.selectedSymbol);
  updateSymbolSelector(symbolSelector, state.symbolsList, state.selectedSymbol);
  // Pass symbol data when symbol changes
  updateCandlestickChart(
    { currentCandles: state.currentCandles, candlesWsConnected: state.candlesWsConnected },
    state.selectedSymbol,
    state.selectedTimeframe,
    true, // isInitialLoad
    selectedSymbolData // Pass symbol data for precision update
  );
  break;

// Case 2: Real-time candle updates (no need for symbol data)
case 'currentCandles':
  // Real-time updates - don't pass symbol data
  updateCandlestickChart(
    { currentCandles: state.currentCandles, candlesWsConnected: state.candlesWsConnected },
    state.selectedSymbol,
    state.selectedTimeframe,
    false // isInitialLoad
    // No symbol data needed for tick updates
  );
  break;
```

### 3. Update Chart Component Function
Modify `LightweightChart.js` to optionally accept symbol data:

```javascript
export function updateCandlestickChart(chartData, symbol, timeframe, isInitialLoad = false, symbolData = null) {
  // Only update price format when symbol data is provided (symbol change or initial load)
  if (symbolData && symbolData.pricePrecision !== undefined && candlestickSeries) {
    candlestickSeries.applyOptions({
      priceFormat: {
        type: 'price',
        precision: symbolData.pricePrecision,
        minMove: 1 / Math.pow(10, symbolData.pricePrecision),
      },
    });
  }
  
  // Rest of the update logic remains the same
  // ... existing candle update code ...
}
```

### 4. Handle Initial Load
Ensure price precision is set on initial symbol selection:

```javascript
// In main.js, after symbols are fetched
fetchSymbols().then(() => {
  if (state.symbolsList.length > 0) {
    const firstSymbol = state.symbolsList[0];
    WebSocketManager.initializeConnections(firstSymbol.id);
    // Initial chart update with symbol data
    updateCandlestickChart(
      { currentCandles: [], candlesWsConnected: false },
      firstSymbol.id,
      state.selectedTimeframe,
      true,
      firstSymbol // Pass full symbol object for precision
    );
  }
});
```

## Implementation Tasks

1. **Update LightweightChart.js - createCandlestickChart()**
   - Add `priceFormat` configuration to `addCandlestickSeries()` call
   - Set default precision of 2 decimal places
   - Calculate minMove based on precision

2. **Update LightweightChart.js - updateCandlestickChart()**
   - Add optional `symbolData` parameter
   - Apply new price format when symbol data is provided
   - Keep existing candle update logic unchanged

3. **Update main.js - Symbol Change Handler**
   - Modify the 'selectedSymbol' case in state subscription
   - Find selected symbol data from symbolsList
   - Pass symbol data to updateCandlestickChart()

4. **Update main.js - Initial Load**
   - Pass symbol data during initial chart setup
   - Ensure first symbol's precision is applied

5. **Keep Real-time Updates Lightweight**
   - Don't modify the 'currentCandles' case
   - Real-time updates continue without symbol data
   - Maintains performance for high-frequency updates

## Error Handling

1. **Missing Price Precision**
   - Default to 2 decimal places if `pricePrecision` is null/undefined
   - Log warning to console for debugging
   - Chart continues to function with default precision

2. **Invalid Precision Values**
   - Validate precision is a non-negative integer
   - Clamp to reasonable range (0-8)
   - Use Math.max(0, Math.min(8, precision))

## Testing Strategy

### Unit Tests
Create tests in `frontend_vanilla/tests/` (following backend pattern):
- Test default precision is applied on chart creation
- Test precision updates on symbol change
- Test real-time updates don't affect precision
- Test handling of missing/invalid precision values

### Manual Testing Checklist
1. **Initial Load**
   - Load page with default symbol
   - Verify price scale shows correct decimal places
   - Check crosshair tooltip precision matches

2. **Symbol Switching**
   - Switch from BTC/USDT (2 decimals) to SHIB/USDT (8 decimals)
   - Verify price scale updates immediately
   - Switch back and verify precision reverts

3. **Real-time Updates**
   - Watch live price updates for 30 seconds
   - Verify precision remains constant
   - Check no console errors about precision

4. **Edge Cases**
   - Test symbol with 0 decimals (if available)
   - Test symbol with missing precision data
   - Test rapid symbol switching

### Integration Testing
- Verify price precision matches order book display
- Ensure both components show same decimal places
- Test theme switching doesn't affect precision

## Code Examples from Lightweight Charts Docs

### Series Price Format Configuration
```javascript
// From lightweight-charts documentation
series.applyOptions({
    priceFormat: {
        type: 'price',
        precision: 4,
        minMove: 0.0001,
    }
});
```

### Alternative: Custom Price Formatter
```javascript
// For future enhancement - custom formatter
const myPriceFormatter = (price) => {
    return price.toFixed(symbolPrecision);
};

chart.applyOptions({
    localization: {
        priceFormatter: myPriceFormatter,
    },
});
```

## Validation Gates

```bash
# Frontend validation
cd frontend_vanilla
npm run lint
npm run build

# Full application test
cd ..
npm run dev

# Manual verification steps:
# 1. Open browser console to check for errors
# 2. Load BTC/USDT - should show 2 decimal places
# 3. Switch to SHIB/USDT - should show 8 decimal places
# 4. Monitor real-time updates - precision should remain stable
# 5. Check crosshair tooltip matches price scale precision
```

## Success Criteria

1. ✓ Price scale displays correct decimal places based on symbol's `pricePrecision`
2. ✓ Default precision (2) is set during chart creation
3. ✓ Price precision updates only on symbol changes, not during real-time updates
4. ✓ Crosshair tooltip shows prices with correct precision
5. ✓ No performance degradation from unnecessary precision updates
6. ✓ Graceful handling of missing precision data (fallback to default)
7. ✓ Console shows no errors during normal operation

## Implementation Order

1. First, update `createCandlestickChart()` to set default price format
2. Then, update `updateCandlestickChart()` to accept and handle symbol data
3. Finally, update `main.js` to pass symbol data on symbol changes
4. Test each step incrementally

## References

- Lightweight Charts Price Format API: https://tradingview.github.io/lightweight-charts/docs/api/interfaces/PriceFormat
- Lightweight Charts Series Options: https://tradingview.github.io/lightweight-charts/docs/api/interfaces/CandlestickSeriesOptions
- Context7 Library ID: `/tradingview/lightweight-charts`
- Backend Symbol Service: `backend/app/services/symbol_service.py`
- Frontend Chart Component: `frontend_vanilla/src/components/LightweightChart.js`
- Frontend State Management: `frontend_vanilla/src/store/store.js`
- Frontend Main App: `frontend_vanilla/src/main.js`

## Confidence Score: 9/10

The implementation is straightforward with clear API documentation and existing patterns to follow. The separation of concerns (precision updates only on symbol change vs. real-time data updates) aligns with performance best practices. The only minor complexity is ensuring proper data flow from store to chart component, which follows established patterns in the codebase.