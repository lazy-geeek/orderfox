# Frontend CLAUDE.md

This file provides frontend-specific guidance to Claude Code when working with the OrderFox frontend codebase.

## Frontend Architecture Overview

OrderFox frontend is built with vanilla JavaScript and Vite, providing a lightweight, performant trading interface with real-time data visualization.

**Tech Stack:**
- Build Tool: Vite for fast development and optimized production builds
- Charts: TradingView Lightweight Charts v5.0.8 for professional candlestick visualization
- WebSocket: Real-time data streaming with automatic reconnection
- State Management: Custom subscribe/notify pattern
- CSS: Custom properties for theming, semantic class architecture

## Code Quality Standards

### JavaScript/ESLint Requirements
- **Linting**: ESLint with no errors or warnings across all JavaScript files
- **File Coverage**: Source files, test files, and configuration files
- **Exclusions**: node_modules, dist, build directories excluded via .eslintignore
- **Run lint check**: `npm run lint`
- **Auto-fix issues**: `npm run lint:fix`
- **Style Guide**: Follow existing patterns in codebase
- **No TypeScript**: Pure JavaScript with JSDoc comments where helpful

## Testing

### Frontend Testing Commands
```bash
# Run all frontend tests (Vitest) - use absolute path
cd /home/bail/github/orderfox/frontend_vanilla && npm test

# Run tests once (CI mode)
cd /home/bail/github/orderfox/frontend_vanilla && npm run test:run

# Run tests with UI
cd /home/bail/github/orderfox/frontend_vanilla && npm run test:ui

# Test specific component
cd /home/bail/github/orderfox/frontend_vanilla && npm test -- LightweightChart
cd /home/bail/github/orderfox/frontend_vanilla && npm test -- LastTradesDisplay

# End-to-end browser tests (Playwright)
cd /home/bail/github/orderfox/frontend_vanilla && npm run test:e2e
cd /home/bail/github/orderfox/frontend_vanilla && npm run test:e2e:ui
cd /home/bail/github/orderfox/frontend_vanilla && npm run test:e2e:headed
cd /home/bail/github/orderfox/frontend_vanilla && npm run test:e2e:debug
```

### Frontend Test Coverage
- **Unit Tests (Vitest)**: 254 tests covering components, services, and integration
- **Bot Management Tests**: Complete CRUD operations testing
- **WebSocket Integration**: Connection management and real-time data flow
- **E2E Tests (Playwright)**: Browser automation testing for user workflows
- **Component Tests**: Individual component functionality and UI interactions
- **Framework**: Vitest with jsdom environment for DOM testing, Playwright for browser testing
- **Test Structure**: Mirrors backend structure with `/tests/components/`, `/tests/integration/`, and `/tests/e2e/`

## Architecture Patterns

### Thin Client Architecture
- **Zero Frontend Validation**: Frontend components directly assign backend data without validation or transformation
- **Performance Optimization**: Moving logic to backend reduces bundle size and improves client-side performance
- **Backend Trust**: Frontend trusts backend data completely - no client-side validation required
- **Direct Assignment**: State update functions simplified to direct assignment (`state.currentCandles = payload.data`)
- **No Data Processing**: All formatting, sorting, and calculations done by backend
- **No Time Calculations**: All time ranges and date calculations happen in backend
- **Backend Sequencing**: Backend handles coordination between data sources (e.g., candles and liquidation volume)

### CSS Architecture & Component Styling
- **Shared Base Classes**: Use `.orderfox-display-base` for all display components
- **Semantic Class Names**: Use semantic names like `.display-header`, `.display-content`, `.display-footer`
- **Component-Specific Overrides**: Keep only unique styles in component-specific classes
- **DRY Principle**: Avoid duplicating common styles like headers, footers, loading states
- **Naming Convention**: 
  - Base classes: `.orderfox-display-base`
  - Shared components: `.display-header`, `.display-content`, `.display-footer`
  - Component-specific: `.orderfox-[component]-display`
- **Theme Support**: All components inherit CSS custom properties for consistent theming
- **Grid Layouts**: 
  - Use `.three-columns` for 3-column layouts (e.g., liquidations)
  - Use `.four-columns` for 4-column layouts (e.g., order book)
- **Color Inheritance**: Amount values inherit color from `.bid-price` (green) and `.ask-price` (red) classes
- **Alignment**: Numeric columns use `text-align: right` for consistent visual alignment
- **Tab Connection Indicators**: 
  - Use `.tab-status-indicator` for connection status dots in tabs
  - `.connected` class shows green dots, `.disconnected` class shows red dots
  - Tab labels (`.tab-label`) use flexbox to align text and status indicators

### WebSocket Connection Management
- **Centralized Manager**: `WebSocketManager` class eliminates duplicate connection logic across UI components
- **DRY Principle**: Single source of truth for connection patterns (symbol switching, timeframe changes, initialization)
- **State Integration**: Seamless integration with state management and UI reset patterns
- **Auto-reconnection**: Built-in reconnection logic with exponential backoff
- **Message Handling**: `websocketService.js` handles low-level WebSocket operations
- **Liquidation Volume Integration**: Automatic fetching of historical volume data on symbol/timeframe changes
- **Connection Lifecycle Management**: Proper event handler nullification during shutdown prevents race conditions
- **Async Symbol Switching**: 500ms delay allows backend processing to complete before creating new connections
- **Graceful Disconnection**: Try-catch blocks handle WebSocket close errors during cleanup
- **State Validation**: Connection state checking before attempting to close or create connections
- **WebSocket URL Construction**: Automatic conversion of relative URLs to proper WebSocket URLs with protocol handling
- **CONNECTING State Handling**: WebSockets in CONNECTING state are removed but not forcefully closed to prevent "closed before established" errors
- **State-Aware Disconnection**: Only OPEN WebSockets are closed with proper close codes; CONNECTING sockets fail naturally

### State Management
- **Subscribe/Notify Pattern**: Custom lightweight state management
- **Component Updates**: Components subscribe to specific state changes
- **Direct Assignment**: State updates are simple assignments from backend data
- **No Transformations**: State contains exactly what backend sends

### Responsive Layout Architecture
- **Full-Width Chart**: Chart and timeframe selector span 100% width for better visibility
- **Stacked Layout**: Orderbook and trades positioned below chart in a responsive grid
- **Breakpoints**:
  - Desktop (>1024px): Orderbook and trades side-by-side
  - Tablet (768-1024px): Adjusted spacing, 50vh chart height
  - Mobile (<768px): Vertical stacking, 40vh chart height
  - Small Mobile (<480px): Wrapped header controls, 35vh chart height
- **Viewport-Based Sizing**: Chart height uses vh units (60vh default) with min/max constraints
- **Preserved Margins**: Display components maintain 10px margins for proper spacing from browser edges

## Component Guidelines

### Display Components
All display components (OrderBook, LastTrades, Liquidation, Chart) follow these patterns:

1. **HTML Structure**:
   ```html
   <div class="orderfox-display-base orderfox-[component]-display">
     <div class="display-header">
       <h3>Title</h3>
       <div class="connection-status"></div>
     </div>
     <div class="display-content">
       <!-- Component specific content -->
     </div>
     <div class="display-footer">
       <!-- Optional footer -->
     </div>
   </div>
   ```

2. **State Integration**:
   - Subscribe to relevant state updates in constructor
   - Unsubscribe in destroy method
   - Direct assignment of backend data

3. **WebSocket Integration**:
   - Use WebSocketManager for connections
   - Handle connection status updates
   - No data transformation on receive

### Chart Component
- **Library**: TradingView Lightweight Charts
- **Container Width**: Pass container width to backend for optimal data loading
- **Zoom Preservation**: User zoom/pan state preserved during updates
- **Real-time Updates**: Use `series.update()` for single candle updates
- **Auto-fitting**: Only on initial load or symbol/timeframe changes
- **Price Precision**: Automatically adjusts based on symbol (backend-provided)
- **Chart Initialization Tracking**: `chartInitialized` flag prevents premature liquidation volume updates before chart is ready
- **Pending Data Buffering**: Volume data is buffered in `pendingVolumeData` until chart is properly initialized
- **Graceful Error Handling**: Chart warnings only appear after initialization, not during initial loading

### Liquidation Volume Chart Overlay
- **Histogram Series**: TradingView histogram series as overlay (empty `priceScaleId`)
- **Scale Positioning**: Bottom 30% of chart (top: 0.7, bottom: 0)
- **Color Coding**: Green bars for buy-dominant periods, red for sell-dominant
- **Bar Height**: Total liquidation volume (buy + sell combined)
- **Timeframe Sync**: Automatically switches with chart timeframe
- **Toggle Control**: UI button to show/hide liquidation volume overlay
- **Service Integration**: `liquidationVolumeService.js` for API calls and caching
- **Real-time Updates**: WebSocket messages update volume data in real-time
- **Mobile Responsive**: Dynamic scale margins for different screen sizes
- **Performance**: Efficient volume data aggregation for large datasets

### Order Book Display
- **Four Columns**: Price, Size for both bids and asks
- **Color Coding**: Green for bids, red for asks
- **Dynamic Updates**: Supports parameter changes without reconnection
- **Backend Formatted**: All numbers come pre-formatted from backend

### Last Trades Display
- **Three Columns**: Price, Size, Time
- **Color Coding**: Green for buy trades, red for sell trades
- **Real-time Updates**: New trades appear at top
- **Historical Data**: Backend provides merged historical + real-time data

### Liquidation Display
- **Three Columns**: Amount (USDT), Quantity, Time
- **Color Coding**: Amount column colored by side (buy/sell)
- **Dynamic Headers**: Quantity header shows base asset
- **Newest First**: Liquidations sorted with newest at top

### TabbedTradingDisplay Component
The TabbedTradingDisplay component consolidates OrderBook, LastTrades, and Liquidations into a single tabbed interface using DaisyUI v5 tabs pattern.

#### Architecture
- **Lazy Initialization**: Components are only created when their tab is first selected, improving initial load performance
- **Mixed WebSocket Management**: OrderBook and LastTrades use external WebSocketManager, while Liquidations manages its own connections
- **State Persistence**: Tab selection state managed through DaisyUI radio inputs without JavaScript state management
- **Component Lifecycle**: Each integrated component maintains its own lifecycle and cleanup methods
- **Connection Status Integration**: Each tab displays real-time connection status indicators (green/red dots) without redundant text
- **Compact Design**: Individual component headers are hidden to reduce redundancy since tab labels clearly indicate content

#### Usage Pattern
```javascript
// Create tabbed display
const tabbedDisplay = createTabbedTradingDisplay();

// Append to container
container.appendChild(tabbedDisplay.element);

// Cleanup when needed
tabbedDisplay.destroy();
```

#### Tab Structure
- **Order Book Tab**: Default active tab, lazily initializes OrderBookDisplay
- **Trades Tab**: Lazily initializes LastTradesDisplay on first selection
- **Liquidations Tab**: Lazily initializes LiquidationDisplay class instance on first selection

#### WebSocket Integration
- **OrderBook**: Uses WebSocketManager for connection management and dynamic parameter updates
- **LastTrades**: Uses WebSocketManager for connection management and historical data merging
- **Liquidations**: Manages own WebSocket connections with internal connection pooling

#### Responsive Design
- **Desktop (>1024px)**: Tabbed display in right sidebar alongside chart
- **Tablet (768-1024px)**: Maintains tabbed layout with adjusted spacing
- **Mobile (<768px)**: Stacked below chart with optimized tab sizing

## Common Tasks

### Adding a New Display Component
1. Create component in `frontend_vanilla/src/components/`
2. Use `.orderfox-display-base` as base class in HTML
3. Use semantic class names: `.display-header`, `.display-content`, `.display-footer`
4. Add only component-specific styles to `style.css`
5. Follow existing patterns for connection status, loading states
6. Test with both light and dark themes
7. Integrate with WebSocketManager for data
8. Subscribe to relevant state updates

### Working with Tabbed Components
When working with the consolidated tabbed trading interface:

1. **Accessing Components**: Individual components (OrderBook, LastTrades, Liquidations) are now inside the TabbedTradingDisplay
2. **Lazy Loading**: Components are only initialized when their tab is first selected
3. **WebSocket Management**: 
   - OrderBook and LastTrades: Use external WebSocketManager
   - Liquidations: Uses internal WebSocket management with `window.updateLiquidationDisplay`
4. **Connection Status**: Each component must update global state (`setLiquidationsWsConnected`, etc.) to reflect tab indicator status
5. **Header Management**: Individual component headers are hidden (`display: none`) since tabs provide clear labeling
6. **Testing**: E2E tests must switch to appropriate tabs before checking component content and account for hidden radio inputs
7. **Layout Integration**: Tabbed display fits in right section of side-by-side layout

#### Integration Example
```javascript
// In main.js - create and integrate tabbed display
import { createTabbedTradingDisplay } from './components/TabbedTradingDisplay.js';

// Create tabbed display
const tabbedTradingDisplay = createTabbedTradingDisplay();

// Add to right section of layout
const rightSection = document.querySelector('.right-section');
rightSection.appendChild(tabbedTradingDisplay.element);
```

#### Tab State Management
- **No JavaScript State**: Tab state managed entirely through DaisyUI radio inputs
- **CSS-Only Transitions**: Smooth tab switching without JavaScript interference
- **Accessibility**: Full keyboard navigation and screen reader support
- **Persistence**: Tab selection persists across page interactions

#### Connection Status Implementation
- **Real-time Indicators**: Each tab displays connection status with colored dots (● for connected, ○ for disconnected)
- **Global State Integration**: Components must call state setters (`setLiquidationsWsConnected`, etc.) to update tab indicators
- **Color Coding**: Green dots for active connections, red dots for disconnected states
- **Compact Design**: No text labels ("Live"/"Disconnected") in tabs - only colored indicators
- **State Synchronization**: Tab indicators automatically update when WebSocket connection state changes

#### Component Integration Patterns
- **Consistent Lifecycle**: TabbedTradingDisplay wraps component DOM elements in objects with `element` and `destroy` properties
- **Factory vs Class**: OrderBook/LastTrades use factory functions returning DOM elements, while LiquidationDisplay is a class requiring container in constructor
- **State Subscriptions**: The store's `subscribe` function doesn't return an unsubscribe method - design components accordingly
- **Component Wrapping**: When integrating disparate component patterns, wrap them in a consistent interface for uniform handling

## Component Hierarchy

### Updated Trading Interface Architecture

```
MainLayout
├── Navbar (Bot Selection, Theme Toggle)
├── Sidebar (Navigation, Selected Bot Info)
└── Main Content (Side-by-side Layout)
    ├── Left Section (Chart Area)
    │   ├── TimeframeSelector
    │   ├── VolumeToggleButton  
    │   └── LightweightChart
    └── Right Section (Consolidated Trading Tables)
        └── TabbedTradingDisplay ⭐ NEW
            ├── Tab Controls (DaisyUI Radio Inputs)
            │   ├── Order Book Tab (default active)
            │   ├── Trades Tab
            │   └── Liquidations Tab
            └── Tab Content Areas (Lazy Initialized)
                ├── OrderBookDisplay (WebSocketManager) 🔄
                ├── LastTradesDisplay (WebSocketManager) 🔄  
                └── LiquidationDisplay (Internal WebSocket) 🔄

Legend:
⭐ = New consolidated component
🔄 = Lazy initialization (created on first tab selection)
```

### Key Architectural Changes

1. **Before**: Three separate components in bottom grid layout
   ```
   MainLayout
   ├── Chart (top section)
   └── Bottom Section (3-column grid)
       ├── OrderBookDisplay
       ├── LastTradesDisplay  
       └── LiquidationDisplay
   ```

2. **After**: Single tabbed component in side-by-side layout
   ```
   MainLayout
   ├── Left: Chart (flexible width)
   └── Right: TabbedTradingDisplay (fixed width)
   ```

### Lazy Initialization Flow

```
User loads page → TabbedTradingDisplay created → Only "Order Book" tab initialized
                                                  ↓
User clicks "Trades" → LastTradesDisplay created and WebSocket connected
                                                  ↓
User clicks "Liquidations" → LiquidationDisplay instantiated with internal WebSocket

Benefits:
✅ Faster initial page load
✅ Reduced memory usage  
✅ Better user experience
✅ Preserved existing functionality
```

### Working with Bot Management
1. **Bot Components**: Use `BotNavigation`, `BotList`, and `BotEditor` components
2. **Bot State**: Bot data managed in `store/store.js` with subscribe/notify pattern
3. **Bot API**: All bot operations go through `botApiService.js`
4. **Bot Context**: WebSocket connections contextualized to selected bot
5. **Testing**: Unit tests for bot components and E2E tests for bot workflows

### DaisyUI v5 Patterns
1. **Drawer Component**: Main layout uses DaisyUI drawer for sidebar navigation
2. **Default Open State**: Drawer toggle is checked by default for better UX (`drawerToggle.checked = true`)
3. **Navigation Links**: Sidebar links use DaisyUI menu component with emoji icons
4. **Modal Dialogs**: Bot editor uses DaisyUI modal with form controls
5. **Dropdown Menus**: Bot actions use DaisyUI dropdown pattern for edit/delete/toggle operations
6. **Button Variants**: Consistent use of btn-primary, btn-secondary, btn-ghost classes
7. **Loading States**: DaisyUI loading spinner for async operations
8. **Tabbed Interface**: TabbedTradingDisplay uses DaisyUI radio input tabs pattern for state management without JavaScript
   - **Important**: Each radio input must be immediately followed by its corresponding `tab-content` div
   - Do not group all inputs together and then all content divs separately

### Modifying Chart Display
1. Update chart component in `LightweightChart.js`
2. Ensure container width is passed to backend
3. Preserve zoom/pan state during updates
4. Use TradingView Lightweight Charts API documentation

### Working with WebSockets
1. Use `WebSocketManager` class for all WebSocket connections
2. Don't create direct WebSocket connections
3. Handle connection status updates in UI
4. Let WebSocketManager handle reconnection logic
5. Always await `WebSocketManager.switchSymbol()` since it's async
6. Use 500ms delay minimum when switching symbols to prevent race conditions
7. Implement proper error handling for WebSocket close operations
8. Check connection state before attempting to close or modify connections
9. Never force-close WebSockets in CONNECTING state - remove them from tracking and let them fail naturally
10. Clear event handlers before any close operation to prevent race condition callbacks

### State Management Updates
1. Keep state updates as direct assignments
2. Don't transform data from backend
3. Use subscribe/notify pattern for component updates
4. Clean up subscriptions in destroy methods

## Environment Variables

Frontend-specific environment variables:
```bash
# Frontend Configuration  
FRONTEND_PORT=3000
FRONTEND_URL=http://localhost:3000
VITE_APP_API_BASE_URL=http://localhost:8000/api/v1  # Production URL
VITE_APP_WS_BASE_URL=ws://localhost:8000/api/v1    # Production WebSocket
```

## Development Tips

### URLs and Routing
- Always use relative URLs (`/api/v1`) in development
- Vite proxy handles routing to backend
- WebSocket URLs also use relative paths
- Environment variables override defaults

### Performance Optimization
- **Bundle Size**: Thin client architecture reduces JavaScript bundle
- **Lazy Loading**: Components loaded on demand
- **Efficient Updates**: Direct DOM manipulation, no virtual DOM
- **WebSocket Efficiency**: Single connection per data type

### Browser Compatibility
- **Target**: Modern browsers with ES6 support
- **No Polyfills**: Assume modern JavaScript features
- **Testing**: Test in Chrome, Firefox, Safari, Edge

### Debugging
- **DevTools**: Use browser DevTools for debugging
- **WebSocket Inspector**: Monitor WebSocket messages in Network tab
- **Console Logging**: Remove console.logs before committing
- **Source Maps**: Enabled in development for debugging

## Chart Performance & UX Features
- **Zoom Preservation**: User zoom/pan state is preserved during real-time updates
- **Viewport-Based Data Loading**: Automatically calculates optimal candle count based on chart size
- **Efficient Real-time Updates**: Uses `series.update()` for single candle updates to maintain performance
- **Smart Auto-fitting**: Only calls `fitContent()` on initial load or symbol/timeframe changes
- **Dynamic Price Precision**: Charts automatically adjust decimal places based on symbol precision
- **Performance Optimization**: Price precision updates only on symbol changes, not during real-time data updates

## Real-time Data Update Patterns

### TradingView Lightweight Charts Update Strategy
When working with TradingView Lightweight Charts series (candlesticks, histograms, etc.), it's crucial to use the correct update method:

1. **Initial/Historical Data**: Use `setData()` 
   - Replaces all existing data
   - Used when loading historical data or switching symbols/timeframes
   - Example: `candlestickSeries.setData(formattedData)`

2. **Real-time Updates**: Use `update()` 
   - Preserves existing data and adds/updates specific data points
   - Much more performant than `setData()` for live updates
   - Example: `candlestickSeries.update(formattedCandle)`

### Implementation Pattern
```javascript
function updateChartSeries(data, isRealTimeUpdate = false) {
  if (isRealTimeUpdate && data.length === 1) {
    // Real-time update - use update() to preserve existing data
    series.update(data[0]);
  } else {
    // Initial load or full update - use setData()
    series.setData(data);
  }
}
```

### Detecting Real-time Updates
In the WebSocket message handler or global update function:
```javascript
window.updateChartData = (data) => {
  // Check if this is a real-time update (single data point and not marked as initial)
  const isRealTimeUpdate = data.data.length === 1 && !data.initial;
  updateChartSeries(data.data, isRealTimeUpdate);
};
```

### Example: Liquidation Volume Implementation
The liquidation volume histogram follows this pattern:
- Historical volume data arrives as an array → uses `setData()`
- Individual liquidation updates arrive as single items → uses `update()`
- This prevents historical data from disappearing when new liquidations occur
- The same pattern applies to candlestick updates and any other chart series
- **Critical**: Check `is_update` flag from backend to determine update method
- **Chart Initialization**: Buffer volume data in `pendingVolumeData` if chart not ready
- **State Preservation**: Maintain `currentVolumeData` array for tooltips and state
- **Troubleshooting**: If historical data disappears, verify `is_update` flag handling

### TradingView Lightweight Charts v5.0 Patterns
- **Version**: Using TradingView Lightweight Charts v5.0.8 (migrated from v4.2)
- **Unified Series API**: Use `chart.addSeries(SeriesType, options)` instead of `chart.add[Type]Series()`
- **Series Types**: Import `CandlestickSeries` and `HistogramSeries` explicitly
- **Background Colors**: Use `{ type: ColorType.Solid, color: value }` format
- **Import Pattern**: `import { createChart, CandlestickSeries, HistogramSeries, ColorType } from 'lightweight-charts';`
- **Migration Complete**: All chart functionality verified working with v5.0 API
- **Breaking Changes**: Series creation methods unified, ColorType required for backgrounds
- **Compatibility**: All existing WebSocket updates, real-time data, and performance optimizations preserved

## Vite Configuration

Key Vite settings:
- **Proxy**: Configured to route `/api` requests to backend
- **Hot Module Replacement**: Enabled for fast development
- **Build Optimization**: Rollup for production builds
- **Environment Variables**: Loaded from `.env` files