
import './style.css';

import { createMainLayout } from './layouts/MainLayout.js';
import { createSymbolSelector, updateSymbolSelector } from './components/SymbolSelector.js';
import { createCandlestickChart, createTimeframeSelector, updateCandlestickChart, updateLatestCandle, resetZoomState } from './components/LightweightChart.js';
import { createOrderBookDisplay, updateOrderBookDisplay } from './components/OrderBookDisplay.js';
import { createTradingModeToggle, updateTradingModeToggle } from './components/TradingModeToggle.js';
import { createThemeSwitcher, initializeTheme } from './components/ThemeSwitcher.js';

import {
  state,
  subscribe,
  setState,
  fetchSymbols,
  fetchOpenPositions,
  executePaperTrade,
  executeLiveTrade,
  setTradingModeApi,
  setSelectedSymbol,
  setSelectedTimeframe,
  setSelectedRounding,
  setAvailableRoundingOptions,
  setShouldRestartWebSocketAfterFetch,
  setDisplayDepth,
  clearOrderBook,
  setCandlesWsConnected,
  setOrderBookWsConnected,
  setTickerWsConnected,
} from './store/store.js';

import {
  connectWebSocketStream,
  disconnectWebSocketStream,
  disconnectAllWebSockets,
  updateOrderBookParameters,
} from './services/websocketService.js';

// Initialize theme before rendering
initializeTheme();

// Get the app container
const app = document.querySelector('#app');

// Create and append the main layout
const mainLayout = createMainLayout();
app.appendChild(mainLayout);

// Get references to the component placeholders in the main layout
const symbolSelectorPlaceholder = document.querySelector('#symbol-selector-placeholder');
const candlestickChartPlaceholder = document.querySelector('#candlestick-chart-placeholder');
const orderBookPlaceholder = document.querySelector('#order-book-placeholder');
const tradingModeTogglePlaceholder = document.querySelector('#trading-mode-toggle-placeholder');
const themeSwitcherPlaceholder = document.querySelector('#theme-switcher-placeholder');

// Create and append the actual components
const symbolSelector = createSymbolSelector();
symbolSelectorPlaceholder.replaceWith(symbolSelector);

const candlestickChartContainer = document.createElement('div');
candlestickChartPlaceholder.replaceWith(candlestickChartContainer);
const candlestickChart = createCandlestickChart(candlestickChartContainer);

const orderBookDisplay = createOrderBookDisplay();
orderBookPlaceholder.replaceWith(orderBookDisplay);

const tradingModeToggle = createTradingModeToggle();
tradingModeTogglePlaceholder.replaceWith(tradingModeToggle);

const themeSwitcher = createThemeSwitcher();
themeSwitcherPlaceholder.replaceWith(themeSwitcher);

// Set up global function for direct chart updates from WebSocket
window.updateLatestCandleDirectly = updateLatestCandle;

// Calculate optimal number of candles to fetch based on chart viewport size
// This ensures the chart viewport is always fully populated with data
function getOptimalCandleCount() {
  // Get chart container width (fallback to reasonable default if not available)
  const chartContainer = document.querySelector('.chart-container');
  const containerWidth = chartContainer ? chartContainer.clientWidth : 800; // Default 800px
  
  // Lightweight Charts default bar spacing is ~6 pixels per candle
  const barSpacing = 6;
  
  // Calculate how many candles fit in viewport
  const candlesInViewport = Math.floor(containerWidth / barSpacing);
  
  // Add buffer for smooth scrolling and zooming (3x viewport)
  // Minimum 200, maximum 1000 for performance
  const optimalCount = Math.min(Math.max(candlesInViewport * 3, 200), 1000);
  
  console.log(`Chart width: ${containerWidth}px, Candles in viewport: ${candlesInViewport}, Fetching: ${optimalCount} candles`);
  
  return optimalCount;
}

// Initial renders
updateSymbolSelector(symbolSelector, state.symbolsList, state.selectedSymbol);
updateCandlestickChart({ currentCandles: state.currentCandles, candlesWsConnected: state.candlesWsConnected }, state.selectedSymbol, state.selectedTimeframe, true); // isInitialLoad = true
updateOrderBookDisplay(orderBookDisplay, state);
updateTradingModeToggle(tradingModeToggle, state);

// Subscribe to state changes and update UI
subscribe((key) => {
  switch (key) {
    case 'symbolsList':
    case 'selectedSymbol':
      updateSymbolSelector(symbolSelector, state.symbolsList, state.selectedSymbol);
      break;
    case 'currentCandles':
      // Real-time updates - don't reset zoom
      updateCandlestickChart({ currentCandles: state.currentCandles, candlesWsConnected: state.candlesWsConnected }, state.selectedSymbol, state.selectedTimeframe, false); // isInitialLoad = false
      break;
    case 'selectedTimeframe':
      // Timeframe change - reset zoom and treat as initial load
      resetZoomState();
      updateCandlestickChart({ currentCandles: state.currentCandles, candlesWsConnected: state.candlesWsConnected }, state.selectedSymbol, state.selectedTimeframe, true); // isInitialLoad = true
      break;
    case 'currentOrderBook':
    case 'orderBookWsConnected':
    case 'selectedRounding':
    case 'availableRoundingOptions':
    case 'displayDepth':
    case 'orderBookLoading':
      updateOrderBookDisplay(orderBookDisplay, state);
      break;
    case 'tradingMode':
      updateTradingModeToggle(tradingModeToggle, state);
      break;
    case 'candlesWsConnected':
      // Update chart to reflect connection status - don't reset zoom
      updateCandlestickChart({ currentCandles: state.currentCandles, candlesWsConnected: state.candlesWsConnected }, state.selectedSymbol, state.selectedTimeframe, false); // isInitialLoad = false
      break;
    default:
      break;
  }
});

// Event Listeners
symbolSelector.addEventListener('change', (e) => {
  setSelectedSymbol(e.target.value);
  // Reset zoom state when symbol changes
  resetZoomState();
  // Clear orderbook to show loading state
  clearOrderBook();
  // Restart websockets for new symbol (WebSocket will provide historical data)
  disconnectAllWebSockets(); // Disconnect all old streams
  
  // Connect new WebSocket streams immediately (no delay needed)
  const optimalCandleCount = getOptimalCandleCount();
  connectWebSocketStream(state.selectedSymbol, 'candles', state.selectedTimeframe, optimalCandleCount);
  connectWebSocketStream(state.selectedSymbol, 'orderbook', null, state.displayDepth, state.selectedRounding);
});

const timeframeSelector = createTimeframeSelector((newTimeframe) => {
  setSelectedTimeframe(newTimeframe);
  // Reset zoom state when timeframe changes  
  resetZoomState();
  // WebSocket will provide historical data on reconnection
  disconnectWebSocketStream('candles', state.selectedSymbol, state.selectedTimeframe);
  
  // Connect new WebSocket stream immediately (no delay needed)
  const optimalCandleCount = getOptimalCandleCount();
  connectWebSocketStream(state.selectedSymbol, 'candles', newTimeframe, optimalCandleCount);
});
candlestickChartContainer.prepend(timeframeSelector);

orderBookDisplay.querySelector('#depth-select').addEventListener('change', (e) => {
  const newDepth = Number(e.target.value);
  
  // Send parameter update via WebSocket first
  const success = updateOrderBookParameters(state.selectedSymbol, newDepth, state.selectedRounding);
  if (success) {
    setDisplayDepth(newDepth);
  } else {
    console.error('Failed to update orderbook depth - WebSocket not connected');
    // Reset selector to previous value
    e.target.value = state.displayDepth;
  }
});

orderBookDisplay.querySelector('#rounding-select').addEventListener('change', (e) => {
  const newRounding = Number(e.target.value);
  
  // Send parameter update via WebSocket first  
  const success = updateOrderBookParameters(state.selectedSymbol, state.displayDepth, newRounding);
  if (success) {
    setSelectedRounding(newRounding);
  } else {
    console.error('Failed to update orderbook rounding - WebSocket not connected');
    // Reset selector to previous value
    e.target.value = state.selectedRounding;
  }
});


tradingModeToggle.querySelector('.mode-button').addEventListener('click', async () => {
  const newMode = state.tradingMode === 'paper' ? 'live' : 'paper';
  await setTradingModeApi(newMode);
});

// Initial data fetch
fetchSymbols().then(() => {
  // Automatically select the first symbol (highest volume) after symbols are fetched
  if (state.symbolsList.length > 0) {
    const firstSymbol = state.symbolsList[0];
    setSelectedSymbol(firstSymbol.id);
    
    // Reset zoom state for initial symbol load
    resetZoomState();
    
    // Clear orderbook to show loading state
    clearOrderBook();
    
    // Start WebSocket connections for the selected symbol
    // The WebSocket will send initial historical chart data immediately
    const optimalCandleCount = getOptimalCandleCount();
    connectWebSocketStream(firstSymbol.id, 'candles', state.selectedTimeframe, optimalCandleCount);
    connectWebSocketStream(firstSymbol.id, 'orderbook', null, state.displayDepth, state.selectedRounding);
  }
});

// Global cleanup on page unload
window.addEventListener('beforeunload', () => {
  disconnectAllWebSockets();
});
