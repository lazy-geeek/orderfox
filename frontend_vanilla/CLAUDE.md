# Frontend CLAUDE.md

Frontend-specific guidance for OrderFox vanilla JavaScript application.

## Tech Stack

- Build: Vite for fast development and optimized builds
- Charts: TradingView Lightweight Charts v5.0.8
- UI: DaisyUI v5 with TailwindCSS
- WebSocket: Real-time streaming with auto-reconnection
- State: Custom subscribe/notify pattern

## Code Quality

**All JavaScript must pass ESLint:**
```bash
npm run lint          # Check
npm run lint:fix      # Auto-fix
```

No TypeScript - pure JavaScript with JSDoc comments where helpful.

## Architecture Patterns

### Thin Client Architecture
- Zero validation - trust backend completely
- Direct state assignment: `state.currentCandles = payload.data`
- No data processing, formatting, or calculations
- Backend handles all timing and sequencing

### CSS Architecture
- Base class: `.orderfox-display-base` for all displays
- Semantic classes: `.display-header`, `.display-content`, `.display-footer`
- Component-specific: `.orderfox-[component]-display`
- Theme via CSS custom properties

### WebSocket Management
- Centralized `WebSocketManager` class
- Auto-reconnection with exponential backoff
- 500ms delay for symbol switching
- State-aware disconnection (only close OPEN connections)

### State Management
- Subscribe/notify pattern
- Direct assignment from backend
- No transformations

## Component Hierarchy

```
TradingModal (DaisyUI dialog)
└── Main Content (Side-by-side Layout)
    ├── Left Section (Chart Area)
    │   ├── TimeframeSelector
    │   ├── VolumeToggleButton  
    │   └── LightweightChart (with overlays)
    └── Right Section
        └── TabbedTradingDisplay
            ├── Order Book Tab (default)
            ├── Trades Tab
            └── Liquidations Tab
```

All tabs initialized immediately to prevent missing data.

## Display Components

**Common Structure:**
```html
<div class="orderfox-display-base orderfox-[component]-display">
  <div class="display-header">
    <h3>Title</h3>
    <div class="connection-status"></div>
  </div>
  <div class="display-content">
    <!-- Component content -->
  </div>
</div>
```

### SearchableDropdown Component
- Replaces select elements with searchable dropdowns
- Used in BotEditor for symbol selection
- Case-insensitive search with partial matching

### Chart Component
- Container width optimization
- Preserve zoom/pan during updates
- `series.update()` for real-time, `series.setData()` for initial
- Chart overlays: liquidation histogram, moving average line

### TradingView v5 Patterns
```javascript
import { createChart, CandlestickSeries, HistogramSeries, ColorType } from 'lightweight-charts';

// v5 API: chart.addSeries(SeriesType, options)
const candlestickSeries = chart.addSeries(CandlestickSeries, options);
```

**Critical Update Pattern:**
```javascript
// Real-time: single data point
if (data.is_update && data.data.length === 1) {
  series.update(data.data[0]);
} else {
  // Initial/full update
  series.setData(data.data);
}
```

### Chart Overlays
- **Liquidation Volume**: Histogram at bottom 30% of chart
- **Moving Average**: Yellow line overlay on volume
- **Tooltip Detection**: Only show in histogram area (bottom 30%)

### DaisyUI v5 Patterns
- Drawer for sidebar navigation
- Native `<dialog>` for modals
- Radio inputs for tab state (no JS needed)
- **Tab Testing**: Click labels, not hidden inputs

## Testing

```bash
# Unit tests
npm test
npm test -- ComponentName

# E2E tests (100% success rate)
./run-tests-minimal.sh complete

# Pure UI testing principles:
# - Test UI elements, not WebSocket data
# - No real-time data validation
# - Robust modal waiting patterns
# - Use helper functions for complex UI interactions (e.g., selectSymbol)
```

## Common Tasks

### Add Display Component
1. Create in `src/components/`
2. Use `.orderfox-display-base`
3. Integrate with WebSocketManager
4. Subscribe to state updates

### WebSocket Rules
1. Use WebSocketManager for all connections
2. Handle status updates in UI
3. Await symbol switching (async)
4. Check state before closing

## Environment Variables

```bash
FRONTEND_PORT=3000
FRONTEND_URL=http://localhost:3000
VITE_APP_API_BASE_URL=http://localhost:8000/api/v1
VITE_APP_WS_BASE_URL=ws://localhost:8000/api/v1
```

## Development Tips

- Use relative URLs in development
- Remove console.logs before committing
- Test with light and dark themes
- Direct DOM manipulation (no virtual DOM)

## Responsive Breakpoints

- Desktop: >1024px (side-by-side)
- Tablet: 768-1024px (50vh chart)
- Mobile: <768px (vertical stack, 40vh chart)
- Small: <480px (35vh chart)