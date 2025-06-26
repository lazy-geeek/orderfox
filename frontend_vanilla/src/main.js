
import './style.css';

import { createMainLayout } from './layouts/MainLayout.js';
import { createSymbolSelector, updateSymbolSelector } from './components/SymbolSelector.js';
import { createCandlestickChart, createTimeframeSelector, updateCandlestickChart } from './components/CandlestickChart.js';
import { createOrderBookDisplay, updateOrderBookDisplay } from './components/OrderBookDisplay.js';
import { createTradingModeToggle, updateTradingModeToggle } from './components/TradingModeToggle.js';

import {
  state,
  subscribe,
  setState,
  fetchSymbols,
  fetchOrderBook,
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
  getValidOrderBookLimit,
} from './store/store.js';

import {
  connectWebSocketStream,
  disconnectWebSocketStream,
  disconnectAllWebSockets,
} from './services/websocketService.js';

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
  // Re-fetch data and restart websockets for new symbol
  fetchCandles(state.selectedSymbol, state.selectedTimeframe, 100);
  // Use dynamic limit for orderbook with valid Binance limit
  const dynamicLimit = (state.displayDepth || 10) * 5;
  const validLimit = getValidOrderBookLimit(dynamicLimit);
  fetchOrderBook(state.selectedSymbol, validLimit);
  disconnectAllWebSockets(); // Disconnect all old streams
  
  // Introduce a delay to allow old WebSockets to fully close
  setTimeout(() => {
    connectWebSocketStream(state.selectedSymbol, 'candles', state.selectedTimeframe);
    connectWebSocketStream(state.selectedSymbol, 'orderbook');
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
  setDisplayDepth(newDepth);
  // Calculate dynamic limit like React frontend: displayDepth * 5, then get valid Binance limit
  const dynamicLimit = newDepth * 5;
  const validLimit = getValidOrderBookLimit(dynamicLimit);
  // Re-fetch order book with valid limit to get enough data for aggregation
  fetchOrderBook(state.selectedSymbol, validLimit);
});

orderBookDisplay.querySelector('#rounding-select').addEventListener('change', (e) => {
  setSelectedRounding(Number(e.target.value));
  // When rounding changes, we need to re-fetch with current limit to ensure proper aggregation
  const dynamicLimit = (state.displayDepth || 10) * 5;
  const validLimit = getValidOrderBookLimit(dynamicLimit);
  fetchOrderBook(state.selectedSymbol, validLimit);
});


tradingModeToggle.querySelector('.mode-button').addEventListener('click', async () => {
  const newMode = state.tradingMode === 'paper' ? 'live' : 'paper';
  await setTradingModeApi(newMode);
});

// Initial data fetch
fetchSymbols().then(() => {
  // Removed automatic selection of the first symbol to allow "Select a symbol..." to persist
  // if (state.symbolsList.length > 0) {
  //   setSelectedSymbol(state.symbolsList[0].id); 
  // }
});

// Global cleanup on page unload
window.addEventListener('beforeunload', () => {
  disconnectAllWebSockets();
});
