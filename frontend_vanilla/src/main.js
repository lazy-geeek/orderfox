
import './style.css';

import { createMainLayout } from './layouts/MainLayout.js';
import { createSymbolSelector, updateSymbolSelector } from './components/SymbolSelector.js';
import { createCandlestickChart, createTimeframeSelector, createVolumeToggleButton, updateCandlestickChart, updateLatestCandle, updateLiquidationVolume, toggleLiquidationVolume, resetZoomState, resetChartData } from './components/LightweightChart.js';
import { createOrderBookDisplay, updateOrderBookDisplay } from './components/OrderBookDisplay.js';
import { createLastTradesDisplay, updateLastTradesDisplay, updateTradesHeaders } from './components/LastTradesDisplay.js';
import { LiquidationDisplay } from './components/LiquidationDisplay.js';
import { createTradingModeToggle, updateTradingModeToggle } from './components/TradingModeToggle.js';
import { createThemeSwitcher, initializeTheme } from './components/ThemeSwitcher.js';

import {
  state,
  subscribe,
  fetchSymbols,
  setTradingModeApi,
  setSelectedRounding,
  setDisplayDepth,
  notify,
} from './store/store.js';

import {
  disconnectAllWebSockets,
  updateOrderBookParameters,
} from './services/websocketService.js';

import { WebSocketManager } from './services/websocketManager.js';

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
const lastTradesPlaceholder = document.querySelector('#last-trades-container');
const liquidationPlaceholder = document.querySelector('#liquidation-container');
const tradingModeTogglePlaceholder = document.querySelector('#trading-mode-toggle-placeholder');
const themeSwitcherPlaceholder = document.querySelector('#theme-switcher-placeholder');

// Create and append the actual components
const symbolSelector = createSymbolSelector();
symbolSelectorPlaceholder.replaceWith(symbolSelector);

const candlestickChartContainer = document.createElement('div');
candlestickChartPlaceholder.replaceWith(candlestickChartContainer);
createCandlestickChart(candlestickChartContainer);

// Volume toggle button will be created later with controls

const orderBookDisplay = createOrderBookDisplay();
orderBookPlaceholder.replaceWith(orderBookDisplay);

const lastTradesDisplay = createLastTradesDisplay();
lastTradesPlaceholder.replaceWith(lastTradesDisplay);

// Initialize liquidation display
const liquidationDisplay = new LiquidationDisplay(liquidationPlaceholder); // eslint-disable-line no-unused-vars

const tradingModeToggle = createTradingModeToggle();
tradingModeTogglePlaceholder.replaceWith(tradingModeToggle);

const themeSwitcher = createThemeSwitcher();
themeSwitcherPlaceholder.replaceWith(themeSwitcher);

// Set up global function for direct chart updates from WebSocket
window.updateLatestCandleDirectly = updateLatestCandle;

// CRITICAL: Expose state globally for chart symbol validation
window.state = state;

// CRITICAL: Expose notify globally for chart error recovery
window.notify = notify;

// CRITICAL: Expose resetChartData globally for timeframe switches
window.resetChartData = resetChartData;

// Set up global function for liquidation volume updates
window.updateLiquidationVolume = (data) => {
  if (data && data.data && Array.isArray(data.data)) {
    // Check if this is a real-time update (single data point) or historical data
    const isRealTimeUpdate = data.data.length === 1 && !data.initial;
    updateLiquidationVolume(data.data, isRealTimeUpdate);
  }
};

// Set up global function for liquidation volume toggle
window.toggleLiquidationVolume = () => {
  return toggleLiquidationVolume();
};

// Note: getOptimalCandleCount() function moved to WebSocketManager for centralization

// Initial renders
updateSymbolSelector(symbolSelector, state.symbolsList, state.selectedSymbol);
updateCandlestickChart({ currentCandles: state.currentCandles, candlesWsConnected: state.candlesWsConnected }, state.selectedSymbol, state.selectedTimeframe, true); // isInitialLoad = true
updateOrderBookDisplay(orderBookDisplay, state);
updateLastTradesDisplay(lastTradesDisplay, state);
updateTradingModeToggle(tradingModeToggle, state);

// Subscribe to state changes and update UI
subscribe((key) => {
  switch (key) {
    case 'symbolsList':
      updateSymbolSelector(symbolSelector, state.symbolsList, state.selectedSymbol);
      break;
    case 'selectedSymbol': {
      const selectedSymbolData = state.symbolsList.find(s => s.id === state.selectedSymbol);
      updateSymbolSelector(symbolSelector, state.symbolsList, state.selectedSymbol);
      // Pass symbol data when symbol changes - reset zoom and treat as initial load
      resetZoomState();
      updateCandlestickChart(
        { currentCandles: state.currentCandles, candlesWsConnected: state.candlesWsConnected },
        state.selectedSymbol,
        state.selectedTimeframe,
        true, // isInitialLoad
        selectedSymbolData // Pass symbol data for precision update
      );
      
      // Update trades headers with new symbol data
      if (selectedSymbolData) {
        updateTradesHeaders(selectedSymbolData);
      }
      break;
    }
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
    case 'currentTrades':
    case 'tradesWsConnected':
    case 'tradesLoading':
    case 'tradesError':
      updateLastTradesDisplay(lastTradesDisplay, state);
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
symbolSelector.addEventListener('change', async (e) => {
  try {
    await WebSocketManager.switchSymbol(e.target.value);
  } catch (error) {
    console.error('Error switching symbol:', error);
  }
});

const timeframeSelector = createTimeframeSelector((newTimeframe) => {
  WebSocketManager.switchTimeframe(newTimeframe);
});

const volumeToggleButton = createVolumeToggleButton();

// Create a controls container for chart controls
const chartControls = document.createElement('div');
chartControls.style.display = 'flex';
chartControls.style.gap = '1rem';
chartControls.style.marginBottom = '0.5rem';
chartControls.appendChild(timeframeSelector);
chartControls.appendChild(volumeToggleButton);

candlestickChartContainer.prepend(chartControls);

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
    WebSocketManager.initializeConnections(firstSymbol.id);
    // Initial chart update with symbol data for price precision
    updateCandlestickChart(
      { currentCandles: [], candlesWsConnected: false },
      firstSymbol.id,
      state.selectedTimeframe,
      true,
      firstSymbol // Pass full symbol object for precision
    );
    // Update trades headers with initial symbol data
    updateTradesHeaders(firstSymbol);
  }
});

// Global cleanup on page unload
window.addEventListener('beforeunload', () => {
  disconnectAllWebSockets();
});
