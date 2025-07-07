# PRP-018: Replace ECharts with TradingView Lightweight Charts (Merged)

## Overview

Replace the current Apache ECharts implementation with TradingView's Lightweight Charts library for candlestick chart display in the OrderFox frontend. This migration will provide a more modern, performant charting solution commonly used in crypto trading applications while preserving all existing functionality.

## Purpose & Why

- **Performance**: Lightweight Charts offers superior performance for large datasets and real-time updates
- **Industry Standard**: TradingView's library is the de facto standard in crypto trading interfaces  
- **Modern UI**: More authentic trading experience with professional-grade chart styling
- **Bundle Size**: Smaller bundle size compared to ECharts full library
- **API Optimization**: Opportunity to optimize backend data handling similar to orderbook improvements

## Core Principles

1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Follow all rules in CLAUDE.md

## Key Requirements

1. **Replace ECharts with Lightweight Charts** while maintaining:
   - Real-time candlestick updates via WebSocket
   - Symbol and timeframe switching
   - Dark/light theme support with smooth transitions
   - Connection status indicators
   - Zoom/pan state preservation
   - Current price line with label
   - Responsive chart sizing

2. **Optimize WebSocket communication** similar to orderbook implementation:
   - Send historical data with first WebSocket message
   - Stream only real-time updates thereafter
   - Reduce communication overhead

3. **Preserve existing user experience**:
   - Same timeframe options (1m, 5m, 15m, 1h, 4h, 1d)
   - Same color scheme (green #0ECB81 for up, red #F6465D for down)
   - Same theme switching behavior

## Success Criteria

- [ ] Lightweight Charts displays candlestick data identical to current ECharts implementation
- [ ] Dark mode and light mode themes work correctly
- [ ] Symbol switching preserves all functionality
- [ ] Timeframe switching works with all supported intervals
- [ ] Real-time WebSocket updates work seamlessly
- [ ] Performance is improved over ECharts
- [ ] Backend sends optimized data structure
- [ ] All existing tests pass and new tests cover Lightweight Charts functionality

## Context and References

### Documentation & References

```yaml
# MUST READ - Include these in your context window
- url: https://tradingview.github.io/lightweight-charts/
  why: Official API documentation and configuration options
  
- url: https://github.com/tradingview/lightweight-charts/tree/master/website/tutorials
  why: Comprehensive tutorials for initialization, real-time updates, and theming
  
- url: https://github.com/tradingview/lightweight-charts/blob/master/website/tutorials/demos/realtime-updates.mdx
  why: Real-time data update patterns and WebSocket integration examples

- mcp: Use mcp__context7__get-library-docs with library ID /tradingview/lightweight-charts
  why: LLM-friendly documentation access
```

### Codebase Structure

```
orderfox/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── connection_manager.py      # WebSocket connection handling
│   │   │   │   ├── market_data_http.py        # HTTP endpoints for candles (line 220)
│   │   │   │   ├── market_data_ws.py          # WebSocket endpoints (candles: line 339)
│   │   │   │   └── trading.py
│   │   │   └── schemas.py                     # Data models (Candle schema)
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── connection_manager.py          # _stream_candles at line 765
│   │   │   └── logging_config.py
│   │   ├── services/
│   │   │   ├── exchange_service.py            # Exchange connectivity
│   │   │   ├── formatting_service.py          # Data formatting (for orderbook)
│   │   │   ├── orderbook_aggregation_service.py # Reference for optimization pattern
│   │   │   ├── orderbook_manager.py
│   │   │   └── symbol_service.py
│   │   └── main.py                            # FastAPI entry point
│   └── tests/
│       ├── api/v1/                            # API tests
│       ├── services/                          # Service tests
│       └── integration/                       # E2E tests
│
└── frontend_vanilla/
    ├── src/
    │   ├── components/
    │   │   ├── CandlestickChart.js           # Current ECharts implementation
    │   │   ├── OrderBookDisplay.js           # Reference for WebSocket patterns
    │   │   ├── SymbolSelector.js             # Symbol switching logic
    │   │   ├── ThemeSwitcher.js              # Theme switching implementation
    │   │   └── MainLayout.js                 # Chart container integration
    │   ├── services/
    │   │   ├── websocketService.js           # WebSocket connection service
    │   │   └── apiClient.js                  # HTTP API client
    │   ├── store/
    │   │   └── store.js                      # State management (candles: line 241-269)
    │   ├── config/
    │   │   └── env.js                        # Environment config
    │   └── main.js                           # App entry point
    ├── package.json                          # Dependencies (echarts: ^5.6.0)
    └── vite.config.js                        # Build configuration
```

### Current Implementation Analysis

1. **ECharts Setup**:
   - Uses `echarts.init()` with theme parameter
   - Candlestick series with custom colors
   - Responsive sizing with ResizeObserver
   - Zoom/dataZoom support
   - Theme re-initialization on change

2. **Data Format**:
   - Backend sends: `{ timestamp, open, high, low, close, volume }`
   - ECharts expects: `[timestamp, open, close, low, high]` array format

3. **WebSocket Flow**:
   - Connect to `/ws/candles/{symbol}/{timeframe}`
   - Receive `candle_update` messages
   - Update chart with new/updated candles

### Known Gotchas & Library Quirks

```javascript
// CRITICAL: Lightweight Charts uses different data format than ECharts
// ECharts: [timestamp, open, close, low, high, volume]
// Lightweight Charts: { time: timestamp, open: number, high: number, low: number, close: number }

// CRITICAL: Time format in Lightweight Charts
// Must be Unix timestamp in SECONDS (not milliseconds like ECharts)
// Use: Math.floor(timestamp / 1000)

// CRITICAL: Theme switching in Lightweight Charts
// No full disposal needed - use chart.applyOptions() for theme changes
// More efficient than ECharts theme switching

// CRITICAL: Real-time updates
// Use series.update() for updating latest candle
// Use series.setData() only for complete data replacement

// CRITICAL: Chart sizing
// Must call chart.resize() on window resize
// Use ResizeObserver for better performance

// CRITICAL: Color scheme preservation
// Dark background: #1E2329 (#161616 alternative), Light background: #FAFAFA (#ffffff alternative)
// Preserve existing colors: Green #0ECB81/#26a69a (up), Red #F6465D/#ef5350 (down)

// CRITICAL: Import pattern
// Use: import { createChart } from 'lightweight-charts';
// NOT: import * as LightweightCharts from 'lightweight-charts';
```

## Implementation Blueprint

### Data Models and Structure

```javascript
// Current ECharts format (what we receive from backend)
const echartsData = {
  timestamp: 1640995200000,  // milliseconds
  open: 49500.0,
  high: 50100.0,
  low: 49400.0,
  close: 50000.0,
  volume: 125.75
};

// Lightweight Charts required format
const lightweightData = {
  time: 1640995200,          // seconds (divide by 1000)
  open: 49500.0,
  high: 50100.0,
  low: 49400.0,
  close: 50000.0
  // Note: volume handled separately if needed
};

// Theme configuration structure
const themeConfig = {
  dark: {
    layout: {
      background: { color: '#1E2329' }, // or '#161616'
      textColor: '#EAECEF', // or '#d1d4dc'
    },
    grid: {
      vertLines: { color: '#2B3139' }, // or '#1f1f1f'
      horzLines: { color: '#2B3139' }, // or '#1f1f1f'
    },
    candlestick: {
      upColor: '#0ECB81', // or '#26a69a'
      downColor: '#F6465D', // or '#ef5350'
      borderVisible: false,
      wickUpColor: '#0ECB81', // or '#26a69a'
      wickDownColor: '#F6465D', // or '#ef5350'
    }
  },
  light: {
    layout: {
      background: { color: '#FAFAFA' }, // or '#ffffff'
      textColor: '#1A1A1A', // or '#191919'
    },
    grid: {
      vertLines: { color: '#EAECEF' }, // or '#f0f0f0'
      horzLines: { color: '#EAECEF' }, // or '#f0f0f0'
    },
    candlestick: {
      upColor: '#0ECB81', // or '#26a69a'
      downColor: '#F6465D', // or '#ef5350'
      borderVisible: false,
      wickUpColor: '#0ECB81', // or '#26a69a'
      wickDownColor: '#F6465D', // or '#ef5350'
    }
  }
};
```

### List of Tasks to be Completed

```yaml
Task 1: Update Dependencies and Configuration
MODIFY frontend_vanilla/package.json:
  - REMOVE: "echarts": "^5.6.0"
  - ADD: "lightweight-charts": "^4.2.0"
  - PRESERVE: All other dependencies

MODIFY frontend_vanilla/vite.config.js:
  - FIND: manualChunks: { vendor: ['echarts'] }
  - REPLACE: manualChunks: { vendor: ['lightweight-charts'] }
  - FIND: include: ['echarts']
  - REPLACE: include: ['lightweight-charts']

Task 2: Create Lightweight Charts Component
CREATE frontend_vanilla/src/components/LightweightChart.js:
  - MIRROR: Structure from CandlestickChart.js
  - REPLACE: ECharts API with Lightweight Charts API
  - PRESERVE: Theme switching logic pattern
  - PRESERVE: WebSocket integration pattern
  - PRESERVE: Symbol/timeframe switching pattern
  - IMPLEMENT: ResizeObserver for responsive sizing

Task 3: Update Chart Integration
MODIFY frontend_vanilla/src/components/MainLayout.js:
  - FIND: import and usage of CandlestickChart
  - REPLACE: with LightweightChart
  - PRESERVE: Container structure and styling

MODIFY frontend_vanilla/src/main.js:
  - FIND: CandlestickChart initialization
  - REPLACE: with LightweightChart initialization
  - PRESERVE: Event handlers and state management

Task 4: Update State Management
MODIFY frontend_vanilla/src/store/store.js:
  - FIND: chart data transformation for ECharts
  - REPLACE: with Lightweight Charts data format
  - PRESERVE: WebSocket data handling patterns
  - ADD: Data format conversion utilities

Task 5: Optimize Backend Data Structure
CREATE backend/app/services/chart_data_service.py:
  - PATTERN: Follow orderbook aggregation service structure
  - IMPLEMENT: Data preprocessing for Lightweight Charts format
  - IMPLEMENT: Initial data + real-time update optimization
  - PRESERVE: Existing data validation patterns

MODIFY backend/app/api/v1/endpoints/market_data_ws.py:
  - ENHANCE: Send initial historical data with first WebSocket message
  - ENHANCE: Optimize data structure for frontend consumption
  - PRESERVE: Connection management patterns

MODIFY backend/app/core/connection_manager.py:
  - UPDATE: _stream_candles method to support optimized flow
  - ADD: _fetch_historical_candles method
  - PRESERVE: Error handling and reconnection logic

Task 6: Update Tests
CREATE backend/tests/api/v1/test_chart_data_service.py:
  - PATTERN: Follow existing test patterns from orderbook tests
  - TEST: Data format conversion utilities
  - TEST: Initial data + real-time update flow
  - PRESERVE: Existing test validation patterns

MODIFY backend/tests/api/v1/test_market_data_ws.py:
  - UPDATE: Test data structures for optimized format
  - PRESERVE: WebSocket connection test patterns

CREATE frontend_vanilla/tests/components/test_lightweight_chart.js:
  - PATTERN: Follow existing component test patterns
  - TEST: Chart initialization and configuration
  - TEST: Theme switching functionality
  - TEST: Data update handling
  - TEST: Responsive behavior

Task 7: Remove ECharts Implementation
REMOVE frontend_vanilla/src/components/CandlestickChart.js:
  - ENSURE: All functionality migrated to LightweightChart.js
  - VERIFY: No remaining references in codebase

Task 8: Update Documentation
MODIFY README.md:
  - UPDATE: Chart library references
  - ADD: New chart library features
  - PRESERVE: All other documentation

MODIFY CLAUDE.md:
  - UPDATE: Chart implementation references
  - ADD: Lightweight Charts specific patterns
  - PRESERVE: All other project guidelines
```

### Per Task Pseudocode

```javascript
// Task 2: LightweightChart.js Implementation
import { createChart, CandlestickSeries } from 'lightweight-charts';

class LightweightChart {
  constructor(container) {
    this.container = container;
    this.chart = null;
    this.candlestickSeries = null;
    this.lastData = null;
    this.currentTheme = localStorage.getItem('theme') || 'dark';
    this.resizeObserver = null;
    
    this.init();
    this.setupEventListeners();
  }

  init() {
    const chartOptions = this.getChartOptions(this.currentTheme);
    this.chart = createChart(this.container, chartOptions);
    
    // CRITICAL: Add candlestick series with theme colors
    this.candlestickSeries = this.chart.addSeries(CandlestickSeries,
      this.getCandlestickOptions(this.currentTheme)
    );
    
    // PRESERVE: Responsive sizing with ResizeObserver
    this.setupResizeObserver();
  }

  setupResizeObserver() {
    this.resizeObserver = new ResizeObserver(entries => {
      if (entries.length === 0) return;
      const { width, height } = entries[0].contentRect;
      this.chart.resize(width, height);
    });
    this.resizeObserver.observe(this.container);
  }

  getChartOptions(theme) {
    const themes = {
      dark: {
        layout: {
          background: { color: '#161616' },
          textColor: '#d1d4dc',
        },
        grid: {
          vertLines: { color: '#1f1f1f' },
          horzLines: { color: '#1f1f1f' },
        },
        rightPriceScale: {
          borderColor: '#2a2a2a',
        },
        timeScale: {
          borderColor: '#2a2a2a',
          timeVisible: true,
          secondsVisible: false,
        },
      },
      light: {
        layout: {
          background: { color: '#ffffff' },
          textColor: '#191919',
        },
        grid: {
          vertLines: { color: '#f0f0f0' },
          horzLines: { color: '#f0f0f0' },
        },
        rightPriceScale: {
          borderColor: '#cccccc',
        },
        timeScale: {
          borderColor: '#cccccc',
          timeVisible: true,
          secondsVisible: false,
        },
      }
    };
    
    return {
      width: this.container.clientWidth,
      height: this.container.clientHeight,
      ...themes[theme],
      crosshair: {
        mode: 0, // Normal mode
      },
    };
  }

  getCandlestickOptions(theme) {
    return {
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    };
  }

  // PATTERN: Mirror ECharts data update pattern
  updateChart(candleData, symbol, timeframe) {
    // CRITICAL: Convert timestamp from milliseconds to seconds
    const formattedData = candleData.map(candle => ({
      time: Math.floor(candle.timestamp / 1000),
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close
    }));
    
    // PRESERVE: Chart title update pattern
    this.updateChartTitle(symbol, timeframe);
    
    // CRITICAL: Use setData for complete replacement
    this.candlestickSeries.setData(formattedData);
    
    // Fit content to visible area
    this.chart.timeScale().fitContent();
  }

  // PATTERN: Mirror ECharts theme switching
  switchTheme(newTheme) {
    this.currentTheme = newTheme;
    
    // CRITICAL: More efficient than ECharts - no disposal needed
    this.chart.applyOptions(this.getChartOptions(newTheme));
    // Candlestick colors remain the same for both themes
  }

  // PATTERN: Mirror ECharts real-time update pattern
  updateLatestCandle(candleData) {
    // CRITICAL: Use update() for latest candle modification
    const formattedCandle = {
      time: Math.floor(candleData.timestamp / 1000),
      open: candleData.open,
      high: candleData.high,
      low: candleData.low,
      close: candleData.close
    };
    
    this.candlestickSeries.update(formattedCandle);
    this.lastData = formattedCandle;
  }

  setupEventListeners() {
    // Listen for theme changes
    window.addEventListener('themechange', (event) => {
      this.switchTheme(event.detail.theme);
    });
  }

  dispose() {
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
    }
    if (this.chart) {
      this.chart.remove();
    }
  }
}

// Task 5: Backend Chart Data Service
class ChartDataService:
    def __init__(self, exchange_service):
        self.exchange_service = exchange_service
    
    async def get_initial_chart_data(self, symbol: str, timeframe: str, limit: int = 100):
        """
        Get initial historical data optimized for Lightweight Charts.
        PATTERN: Follow orderbook aggregation service structure
        """
        # CRITICAL: Fetch from exchange
        raw_data = await self.exchange_service.fetch_ohlcv(symbol, timeframe, limit)
        
        # CRITICAL: Convert to Lightweight Charts format
        formatted_data = []
        for candle in raw_data:
            formatted_data.append({
                'timestamp': candle[0],  # Keep milliseconds for backend
                'open': float(candle[1]),
                'high': float(candle[2]),
                'low': float(candle[3]),
                'close': float(candle[4]),
                'volume': float(candle[5])
            })
        
        return {
            'type': 'historical_candles',
            'symbol': symbol,
            'timeframe': timeframe,
            'data': formatted_data
        }
    
    async def format_realtime_update(self, candle_data: dict):
        """
        Format real-time candle update for WebSocket.
        PATTERN: Follow orderbook real-time update pattern
        """
        return {
            'type': 'candle_update',
            'symbol': candle_data['symbol'],
            'timeframe': candle_data['timeframe'],
            'timestamp': candle_data['timestamp'],
            'open': candle_data['open'],
            'high': candle_data['high'],
            'low': candle_data['low'],
            'close': candle_data['close'],
            'volume': candle_data['volume']
        }

# Update connection_manager.py
async def _stream_candles_optimized(self, websocket: WebSocket, symbol: str, timeframe: str):
    """Stream candles with initial historical data."""
    try:
        # Send initial historical candles
        chart_service = ChartDataService(self.exchange_service)
        historical_data = await chart_service.get_initial_chart_data(symbol, timeframe)
        await websocket.send_json(historical_data)
        
        # Then stream real-time updates
        exchange = await self._get_exchange()
        while True:
            try:
                ohlcv = await exchange.watch_ohlcv(symbol, timeframe)
                if ohlcv:
                    latest_candle = ohlcv[-1]
                    candle_data = {
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'timestamp': latest_candle[0],
                        'open': latest_candle[1],
                        'high': latest_candle[2],
                        'low': latest_candle[3],
                        'close': latest_candle[4],
                        'volume': latest_candle[5]
                    }
                    formatted_update = await chart_service.format_realtime_update(candle_data)
                    await websocket.send_json(formatted_update)
            except Exception as e:
                logger.error(f"Error streaming candles: {e}")
                await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"Fatal error in candle stream: {e}")
        raise
```

## Validation Loop

### Level 1: Syntax & Style

```bash
# Run these FIRST - fix any errors before proceeding
cd frontend_vanilla && npm run build     # Build frontend
cd backend && python -m pytest tests/ -v # Run backend tests

# Expected: No build errors, all tests pass
```

### Level 2: Unit Tests

```javascript
// Test Lightweight Charts integration
describe('LightweightChart', () => {
  test('initializes chart with correct theme', () => {
    const container = document.createElement('div');
    container.style.width = '800px';
    container.style.height = '400px';
    document.body.appendChild(container);
    
    const chart = new LightweightChart(container);
    
    expect(chart.chart).toBeDefined();
    expect(chart.candlestickSeries).toBeDefined();
    expect(chart.currentTheme).toBe('dark');
  });
  
  test('converts data format correctly', () => {
    const container = document.createElement('div');
    const chart = new LightweightChart(container);
    
    const testData = [{
      timestamp: 1640995200000,
      open: 49500.0,
      high: 50100.0,
      low: 49400.0,
      close: 50000.0,
      volume: 125.75
    }];
    
    chart.updateChart(testData, 'BTCUSDT', '1m');
    
    // Verify data was converted and set correctly
    const convertedData = chart.candlestickSeries.data();
    expect(convertedData[0].time).toBe(1640995200); // Seconds
  });
  
  test('switches theme without disposing chart', () => {
    const container = document.createElement('div');
    const chart = new LightweightChart(container);
    
    const originalChart = chart.chart;
    chart.switchTheme('light');
    
    // Should be same chart instance
    expect(chart.chart).toBe(originalChart);
    expect(chart.currentTheme).toBe('light');
  });
  
  test('handles real-time updates correctly', () => {
    const container = document.createElement('div');
    const chart = new LightweightChart(container);
    
    const update = {
      timestamp: 1640995260000,
      open: 50000.0,
      high: 50200.0,
      low: 49900.0,
      close: 50100.0,
      volume: 150.0
    };
    
    chart.updateLatestCandle(update);
    expect(chart.lastData.time).toBe(1640995260);
  });
});
```

```python
# Test backend chart data service
import pytest
from app.services.chart_data_service import ChartDataService

def test_chart_data_service_format_conversion():
    """Test data format conversion for Lightweight Charts"""
    service = ChartDataService(mock_exchange)
    
    raw_data = [
        [1640995200000, 49500.0, 50100.0, 49400.0, 50000.0, 125.75]
    ]
    
    result = service.format_for_lightweight_charts(raw_data)
    
    assert result[0]['timestamp'] == 1640995200000  # Keep milliseconds in backend
    assert result[0]['open'] == 49500.0
    assert result[0]['high'] == 50100.0
    assert result[0]['low'] == 49400.0
    assert result[0]['close'] == 50000.0
    assert result[0]['volume'] == 125.75

def test_websocket_initial_data_format():
    """Test WebSocket sends historical data first"""
    # Test implementation here
    pass
```

### Level 3: Integration Test

```bash
# Start the application
npm run dev

# Manual testing checklist:
# 1. Open http://localhost:3000
# 2. Verify chart displays with candlestick data
# 3. Test symbol switching (BTCUSDT, ETHUSDT, etc.)
# 4. Test timeframe switching (1m, 5m, 15m, 1h, 4h, 1d)
# 5. Test theme switching (toggle dark/light mode)
# 6. Verify WebSocket real-time updates
# 7. Test zoom and pan functionality
# 8. Check performance with large datasets
# 9. Verify responsive behavior on window resize
# 10. Check browser console for errors

# Expected: All functionality works identically to ECharts version
```

## Final Validation Checklist

- [ ] All tests pass: `cd backend && python -m pytest tests/ -v`
- [ ] No build errors: `cd frontend_vanilla && npm run build`
- [ ] No lint errors: `cd frontend_vanilla && npm run lint`
- [ ] Chart displays correctly in both themes
- [ ] Symbol switching works for all supported pairs
- [ ] Timeframe switching works for all intervals
- [ ] Real-time WebSocket updates work seamlessly
- [ ] Theme switching is smooth without chart disposal
- [ ] Performance is improved over ECharts
- [ ] No console errors in browser DevTools
- [ ] WebSocket connections manage properly
- [ ] Data format conversion works correctly
- [ ] Chart interactions (zoom, pan) work properly
- [ ] Responsive sizing works on window resize
- [ ] ECharts completely removed from codebase
- [ ] Memory leaks prevented (dispose methods work)

## Anti-Patterns to Avoid

- ❌ Don't use milliseconds for time in Lightweight Charts (use seconds)
- ❌ Don't dispose/recreate chart for theme switching
- ❌ Don't use setData() for real-time updates (use update())
- ❌ Don't forget to handle window resize events
- ❌ Don't mix ECharts and Lightweight Charts patterns
- ❌ Don't skip data format validation
- ❌ Don't hardcode theme colors - use configuration
- ❌ Don't remove WebSocket connection management patterns
- ❌ Don't change existing API contracts without backend coordination
- ❌ Don't forget to dispose chart and observers on component unmount
- ❌ Don't import entire library (use named imports)

## Success Metrics

1. Chart loads and displays data correctly
2. All existing features work as before
3. Performance is equal or better than ECharts
4. Theme switching is smooth without flicker
5. WebSocket updates work reliably
6. No memory leaks or performance degradation
7. Bundle size reduced compared to ECharts
8. Chart responsiveness improved

## References for Implementation

- Current Implementation: `frontend_vanilla/src/components/CandlestickChart.js`
- WebSocket Pattern: `frontend_vanilla/src/services/websocketService.js`
- Store Integration: `frontend_vanilla/src/store/store.js:241-269`
- Theme System: `frontend_vanilla/src/components/ThemeSwitcher.js`
- Backend WebSocket: `backend/app/api/v1/endpoints/market_data_ws.py:339`
- Connection Manager: `backend/app/core/connection_manager.py:765`
- OrderBook Optimization Pattern: `backend/app/services/orderbook_aggregation_service.py`

## Confidence Score: 9/10

High confidence due to:
- Comprehensive understanding of current ECharts implementation
- Detailed Lightweight Charts documentation and examples
- Clear migration path with preserved patterns
- Established WebSocket and state management patterns
- Solid backend architecture to build upon
- Complete context with all gotchas documented
- Validation loops at every level

Minor uncertainty on:
- Exact performance improvements (measurable after implementation)
- Potential edge cases in data format conversion

This merged PRP provides complete context for seamless migration while maintaining all existing functionality and improving performance.