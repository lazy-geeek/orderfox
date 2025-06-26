
import { createMainLayout } from './layouts/MainLayout.js';
import { createSymbolSelector, updateSymbolSelector } from './components/SymbolSelector.js';
import { createCandlestickChart, createTimeframeSelector, updateCandlestickChart } from './components/CandlestickChart.js';
import { createOrderBookDisplay, updateOrderBookDisplay } from './components/OrderBookDisplay.js';
import { createManualTradeForm, updateManualTradeForm } from './components/ManualTradeForm.js';
import { createPositionsTable, updatePositionsTable } from './components/PositionsTable.js';
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
const manualTradeFormPlaceholder = document.querySelector('#manual-trade-form-placeholder');
const positionsTablePlaceholder = document.querySelector('#positions-table-placeholder');
const tradingModeTogglePlaceholder = document.querySelector('#trading-mode-toggle-placeholder');

// Create and append the actual components
const symbolSelector = createSymbolSelector();
symbolSelectorPlaceholder.replaceWith(symbolSelector);

const candlestickChartContainer = document.createElement('div');
candlestickChartPlaceholder.replaceWith(candlestickChartContainer);
const candlestickChart = createCandlestickChart(candlestickChartContainer);

const orderBookDisplay = createOrderBookDisplay();
orderBookPlaceholder.replaceWith(orderBookDisplay);

const manualTradeForm = createManualTradeForm();
manualTradeFormPlaceholder.replaceWith(manualTradeForm);

const positionsTable = createPositionsTable();
positionsTablePlaceholder.replaceWith(positionsTable);

const tradingModeToggle = createTradingModeToggle();
tradingModeTogglePlaceholder.replaceWith(tradingModeToggle);

// Initial renders
updateSymbolSelector(symbolSelector, state.symbolsList, state.selectedSymbol);
updateCandlestickChart({ currentCandles: state.currentCandles, candlesWsConnected: state.candlesWsConnected }, state.selectedSymbol, state.selectedTimeframe);
updateOrderBookDisplay(orderBookDisplay, state);
updateManualTradeForm(manualTradeForm, state);
updatePositionsTable(positionsTable, state);
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
      updateOrderBookDisplay(orderBookDisplay, state);
      break;
    case 'tradingMode':
    case 'isSubmittingTrade':
    case 'tradeError':
      updateManualTradeForm(manualTradeForm, state);
      updateTradingModeToggle(tradingModeToggle, state);
      break;
    case 'openPositions':
    case 'positionsLoading':
    case 'positionsError':
      updatePositionsTable(positionsTable, state);
      break;
    case 'candlesWsConnected':
    case 'tickerWsConnected':
      // Update chart and order book to reflect connection status
      updateCandlestickChart({ currentCandles: state.currentCandles, candlesWsConnected: state.candlesWsConnected }, state.selectedSymbol, state.selectedTimeframe);
      updateOrderBookDisplay(orderBookDisplay, state);
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
  fetchOrderBook(state.selectedSymbol);
  disconnectAllWebSockets(); // Disconnect all old streams
  
  // Introduce a delay to allow old WebSockets to fully close
  setTimeout(() => {
    connectWebSocketStream(state.selectedSymbol, 'candles', state.selectedTimeframe);
    connectWebSocketStream(state.selectedSymbol, 'orderbook');
    connectWebSocketStream(state.selectedSymbol, 'ticker');
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
  setDisplayDepth(Number(e.target.value));
  // Re-fetch order book with new depth, which will trigger WS restart
  fetchOrderBook(state.selectedSymbol, state.displayDepth);
});

orderBookDisplay.querySelector('#rounding-select').addEventListener('change', (e) => {
  setSelectedRounding(Number(e.target.value));
  // Re-fetch order book with new rounding, which will trigger WS restart
  fetchOrderBook(state.selectedSymbol, state.displayDepth);
});

manualTradeForm.querySelector('.trade-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const formData = new FormData(e.target);
  const tradeDetails = {
    symbol: formData.get('symbol'),
    side: formData.get('side'),
    amount: parseFloat(formData.get('amount')),
    type: formData.get('type'),
    price: formData.get('type') === 'limit' ? parseFloat(formData.get('price')) : undefined,
  };

  if (state.tradingMode === 'paper') {
    await executePaperTrade(tradeDetails);
  } else {
    await executeLiveTrade(tradeDetails);
  }
});

positionsTable.addEventListener('click', async (e) => {
  if (e.target.classList.contains('close-button')) {
    const row = e.target.closest('tr');
    const symbol = row.querySelector('.symbol').textContent;
    const side = row.querySelector('.side').textContent.toLowerCase();
    const size = parseFloat(row.querySelector('.size').textContent);

    const tradeDetails = {
      symbol,
      side: side === 'long' ? 'sell' : 'buy', // Close long with sell, close short with buy
      amount: size,
      type: 'market',
    };

    if (state.tradingMode === 'paper') {
      await executePaperTrade(tradeDetails);
    } else {
      await executeLiveTrade(tradeDetails);
    }
  }
});

tradingModeToggle.querySelector('.mode-button').addEventListener('click', async () => {
  const newMode = state.tradingMode === 'paper' ? 'live' : 'paper';
  await setTradingModeApi(newMode);
  fetchOpenPositions(); // Refresh positions after mode change
});

// Initial data fetch
fetchSymbols().then(() => {
  // Removed automatic selection of the first symbol to allow "Select a symbol..." to persist
  // if (state.symbolsList.length > 0) {
  //   setSelectedSymbol(state.symbolsList[0].id); 
  // }
});
fetchOpenPositions();

// Global cleanup on page unload
window.addEventListener('beforeunload', () => {
  disconnectAllWebSockets();
});
