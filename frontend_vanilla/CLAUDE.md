# Frontend CLAUDE.md

This file provides frontend-specific guidance to Claude Code when working with the OrderFox frontend codebase.

## Frontend Architecture Overview

OrderFox frontend is built with vanilla JavaScript and Vite, providing a lightweight, performant trading interface with real-time data visualization.

**Tech Stack:**
- Build Tool: Vite for fast development and optimized production builds
- Charts: TradingView Lightweight Charts for professional candlestick visualization
- WebSocket: Real-time data streaming with automatic reconnection
- State Management: Custom subscribe/notify pattern
- CSS: Custom properties for theming, semantic class architecture

## Code Quality Standards

### JavaScript/ESLint Requirements
- **Linting**: ESLint with no errors or warnings
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

## Vite Configuration

Key Vite settings:
- **Proxy**: Configured to route `/api` requests to backend
- **Hot Module Replacement**: Enabled for fast development
- **Build Optimization**: Rollup for production builds
- **Environment Variables**: Loaded from `.env` files