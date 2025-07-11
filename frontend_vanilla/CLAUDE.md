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
```

### Frontend Test Coverage
- **Price Precision Logic**: 14 unit tests covering default precision, dynamic updates, error handling, and edge cases
- **Last Trades Component**: 14 unit tests covering component creation, trade updates, color coding, and state management
- **Integration Tests**: 4 tests validating main.js flow and performance optimization patterns
- **Framework**: Vitest with jsdom environment for DOM testing
- **Test Structure**: Mirrors backend structure with `/tests/components/` and `/tests/integration/`

## Architecture Patterns

### Thin Client Architecture
- **Zero Frontend Validation**: Frontend components directly assign backend data without validation or transformation
- **Performance Optimization**: Moving logic to backend reduces bundle size and improves client-side performance
- **Backend Trust**: Frontend trusts backend data completely - no client-side validation required
- **Direct Assignment**: State update functions simplified to direct assignment (`state.currentCandles = payload.data`)
- **No Data Processing**: All formatting, sorting, and calculations done by backend

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

## Vite Configuration

Key Vite settings:
- **Proxy**: Configured to route `/api` requests to backend
- **Hot Module Replacement**: Enabled for fast development
- **Build Optimization**: Rollup for production builds
- **Environment Variables**: Loaded from `.env` files