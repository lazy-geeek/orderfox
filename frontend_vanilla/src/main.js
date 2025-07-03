
import './style.css';

import { createMainLayout } from './layouts/MainLayout.js';
import { createSymbolSelector, updateSymbolSelector } from './components/SymbolSelector.js';
import { createCandlestickChart, createTimeframeSelector, updateCandlestickChart } from './components/CandlestickChart.js';
import { createOrderBookDisplay, updateOrderBookDisplay } from './components/OrderBookDisplay.js';
import { createTradingModeToggle, updateTradingModeToggle } from './components/TradingModeToggle.js';
import { createThemeSwitcher, initializeTheme } from './components/ThemeSwitcher.js';

import {
  state,
  subscribe,
  setState,
  fetchSymbols,
  fetchCandles,
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

// Initial renders
updateSymbolSelector(symbolSelector, state.symbolsList, state.selectedSymbol);
updateCandlestickChart({ currentCandles: state.currentCandles, candlesWsConnected: state.candlesWsConnected }, state.selectedSymbol, state.selectedTimeframe);
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
    case 'selectedTimeframe':
      updateCandlestickChart({ currentCandles: state.currentCandles, candlesWsConnected: state.candlesWsConnected }, state.selectedSymbol, state.selectedTimeframe);
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
      // Update chart to reflect connection status
      updateCandlestickChart({ currentCandles: state.currentCandles, candlesWsConnected: state.candlesWsConnected }, state.selectedSymbol, state.selectedTimeframe);
      break;
    default:
      break;
  }
});

// Event Listeners
symbolSelector.addEventListener('change', (e) => {
  setSelectedSymbol(e.target.value);
  // Clear orderbook to show loading state
  clearOrderBook();
  // Re-fetch candles and restart websockets for new symbol
  fetchCandles(state.selectedSymbol, state.selectedTimeframe, 100);
  disconnectAllWebSockets(); // Disconnect all old streams
  
  // Introduce a delay to allow old WebSockets to fully close
  setTimeout(() => {
    connectWebSocketStream(state.selectedSymbol, 'candles', state.selectedTimeframe);
    connectWebSocketStream(state.selectedSymbol, 'orderbook', null, state.displayDepth, state.selectedRounding);
  }, 500); // 500ms delay
});

const timeframeSelector = createTimeframeSelector((newTimeframe) => {
  setSelectedTimeframe(newTimeframe);
  fetchCandles(state.selectedSymbol, newTimeframe, 100);
  disconnectWebSocketStream('candles', state.selectedSymbol, state.selectedTimeframe);
  
  // Introduce a delay to allow old WebSocket to fully close
  setTimeout(() => {
    connectWebSocketStream(state.selectedSymbol, 'candles', newTimeframe);
  }, 500); // 500ms delay
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
    
    // Clear orderbook to show loading state
    clearOrderBook();
    
    // Fetch initial candles for the selected symbol
    fetchCandles(firstSymbol.id, state.selectedTimeframe, 100);
    
    // Start WebSocket connections for the selected symbol
    // The orderbook WebSocket will send initial data immediately
    setTimeout(() => {
      connectWebSocketStream(firstSymbol.id, 'candles', state.selectedTimeframe);
      connectWebSocketStream(firstSymbol.id, 'orderbook', null, state.displayDepth, state.selectedRounding);
    }, 500);
  }
});

// Global cleanup on page unload
window.addEventListener('beforeunload', () => {
  disconnectAllWebSockets();
});
