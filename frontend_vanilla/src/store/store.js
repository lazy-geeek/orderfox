
import { API_BASE_URL } from '../config/env.js';

const state = {
  selectedSymbol: null,
  symbolsList: [],
  currentCandles: [],
  selectedTimeframe: '1m',
  candlesLoading: false,
  candlesError: null,
  candlesWsConnected: false,
  currentOrderBook: { bids: [], asks: [], symbol: '', timestamp: 0 },
  orderBookLoading: false,
  orderBookError: null,
  orderBookWsConnected: false,
  currentTicker: null,
  tickerWsConnected: false,
  selectedRounding: null,
  availableRoundingOptions: [],
  displayDepth: 10,
  tradingMode: 'paper',
  isSubmittingTrade: false,
  tradeError: null,
  openPositions: [],
  positionsLoading: false,
  positionsError: null,
  currentTheme: localStorage.getItem('theme') || 'dark',
};

const subscribers = [];

function subscribe(callback) {
  subscribers.push(callback);
}

function notify(key) {
  subscribers.forEach(callback => callback(key));
}

function setState(newState) {
  for (const key in newState) {
    if (state.hasOwnProperty(key)) {
      state[key] = newState[key];
      notify(key);
    }
  }
}

// Helper functions (from marketDataSlice.ts)
const validateAndFilterCandles = (candles) => {
  if (!Array.isArray(candles)) {
    console.warn('Invalid candles data: not an array', candles);
    return [];
  }

  return candles
    .map((candle, index) => {
      let timestamp;
      if (typeof candle.timestamp === 'number') {
        timestamp = candle.timestamp;
      } else if (typeof candle.timestamp === 'string') {
        const dateTimestamp = new Date(candle.timestamp).getTime();
        if (!isNaN(dateTimestamp)) {
          timestamp = dateTimestamp;
        } else {
          timestamp = parseInt(candle.timestamp, 10);
        }
      } else {
        console.warn(`Invalid timestamp format at index ${index}:`, candle.timestamp);
        return null;
      }
      
      const parsedCandle = {
        timestamp: timestamp,
        open: parseFloat(candle.open),
        high: parseFloat(candle.high),
        low: parseFloat(candle.low),
        close: parseFloat(candle.close),
        volume: parseFloat(candle.volume),
      };

      const isValid =
        typeof parsedCandle.timestamp === 'number' && !isNaN(parsedCandle.timestamp) && parsedCandle.timestamp > 0 &&
        typeof parsedCandle.open === 'number' && !isNaN(parsedCandle.open) && parsedCandle.open > 0 &&
        typeof parsedCandle.high === 'number' && !isNaN(parsedCandle.high) && parsedCandle.high > 0 &&
        typeof parsedCandle.low === 'number' && !isNaN(parsedCandle.low) && parsedCandle.low > 0 &&
        typeof parsedCandle.close === 'number' && !isNaN(parsedCandle.close) && parsedCandle.close > 0 &&
        typeof parsedCandle.volume === 'number' && !isNaN(parsedCandle.volume) && parsedCandle.volume >= 0;

      if (!isValid) {
        console.warn(`Skipping invalid candle data at index ${index} after parsing:`, candle, 'Parsed:', parsedCandle);
        return null;
      }
      return parsedCandle;
    })
    .filter(candle => candle !== null);
};

const validateOrderBook = (orderBook) => {
  if (!orderBook || typeof orderBook !== 'object') {
    console.warn('Invalid order book data: not an object', orderBook);
    return null;
  }

  const bids = Array.isArray(orderBook.bids) ? orderBook.bids : [];
  const asks = Array.isArray(orderBook.asks) ? orderBook.asks : [];

  let timestamp;
  if (typeof orderBook.timestamp === 'number') {
    timestamp = orderBook.timestamp;
  } else if (typeof orderBook.timestamp === 'string') {
    const dateTimestamp = new Date(orderBook.timestamp).getTime();
    if (!isNaN(dateTimestamp)) {
      timestamp = dateTimestamp;
    } else {
      timestamp = Date.now();
    }
  } else {
    timestamp = Date.now();
  }

  // Check if this is a backend-aggregated order book
  const isAggregated = orderBook.aggregated === true;
  
  if (isAggregated) {
    // For aggregated data, bids/asks may already include cumulative totals
    // Validate structure but don't filter as heavily since backend has already processed
    const validatedBids = bids.filter((bid) =>
      bid && typeof bid.price === 'number' && typeof bid.amount === 'number' &&
      bid.price > 0 && bid.amount > 0
    );
    
    const validatedAsks = asks.filter((ask) =>
      ask && typeof ask.price === 'number' && typeof ask.amount === 'number' &&
      ask.price > 0 && ask.amount > 0
    );

    return {
      symbol: orderBook.symbol || '',
      bids: validatedBids,
      asks: validatedAsks,
      timestamp,
      aggregated: true,
      rounding: orderBook.rounding || null,
      source: orderBook.source || null,
      version: orderBook.version || '1.0'
    };
  } else {
    // Legacy format - existing validation logic
    return {
      symbol: orderBook.symbol || '',
      bids: bids.filter((bid) =>
        bid && typeof bid.price === 'number' && typeof bid.amount === 'number' &&
        bid.price > 0 && bid.amount > 0
      ),
      asks: asks.filter((ask) =>
        ask && typeof ask.price === 'number' && typeof ask.amount === 'number' &&
        ask.price > 0 && ask.amount > 0
      ),
      timestamp,
      aggregated: false
    };
  }
};

const validateTicker = (ticker) => {
  if (!ticker || typeof ticker !== 'object') {
    console.warn('Invalid ticker data: not an object', ticker);
    return null;
  }

  let timestamp;
  if (typeof ticker.timestamp === 'number') {
    timestamp = ticker.timestamp;
  } else if (typeof ticker.timestamp === 'string') {
    const dateTimestamp = new Date(ticker.timestamp).getTime();
    if (!isNaN(dateTimestamp)) {
      timestamp = dateTimestamp;
    } else {
      timestamp = Date.now();
    }
  } else {
    timestamp = Date.now();
  }

  const numericFields = ['last', 'bid', 'ask', 'high', 'low', 'open', 'close', 'change', 'percentage', 'volume', 'quote_volume'];
  const parsedTicker = { symbol: ticker.symbol || '', timestamp };

  const lastPrice = parseFloat(ticker.last);
  if (isNaN(lastPrice)) {
    console.warn(`❌ Invalid ticker data: 'last' price is required but not a valid number`, ticker.last, 'Full ticker:', ticker);
    return null;
  }

  for (const field of numericFields) {
    const value = parseFloat(ticker[field]);
    if (isNaN(value) || ticker[field] === null || ticker[field] === undefined) {
      if (field === 'last') {
        parsedTicker[field] = lastPrice;
      } else if (field === 'change') {
        parsedTicker[field] = 0;
      } else if (field === 'percentage') {
        parsedTicker[field] = 0;
      } else {
        parsedTicker[field] = lastPrice;
      }
    } else {
      parsedTicker[field] = value;
    }
  }

  return parsedTicker;
};

// Mutator functions (equivalent to Redux reducers and actions)
function calculateAndSetRoundingOptions(symbolId) {
  if (!symbolId) {
    setAvailableRoundingOptions([], null);
    return;
  }

  const selectedSymbolData = state.symbolsList.find(symbol => symbol.id === symbolId);
  if (!selectedSymbolData) {
    setAvailableRoundingOptions([], null);
    return;
  }

  // Calculate baseRounding from pricePrecision (same logic as React frontend)
  const baseRounding = 1 / (10 ** (selectedSymbolData.pricePrecision || 2));

  // Generate options array starting with baseRounding
  const options = [baseRounding];
  
  // Get current price for stopping condition (use highest bid, ticker, or estimate from symbol data)
  let currentPrice = state.currentOrderBook?.bids?.[0]?.price || 
                    state.currentTicker?.last ||
                    null;
  
  // If no price data available, use a conservative estimate based on symbol name patterns
  if (!currentPrice) {
    // For major pairs, use rough estimates to prevent excessive rounding options
    if (symbolId.includes('BTC')) currentPrice = 50000;
    else if (symbolId.includes('ETH')) currentPrice = 3000;
    else if (symbolId.includes('USDT') || symbolId.includes('USDC')) currentPrice = 10; // Conservative for altcoins
    else currentPrice = 100; // Default conservative estimate
  }
  
  // Generate additional options by multiplying by 10, with stricter price-based limits
  let nextOption = baseRounding;
  while (options.length < 7) { // Maximum 7 options as a sensible limit
    nextOption = nextOption * 10;
    
    // Much stricter condition: stop if rounding becomes more than 1/10th of current price
    // This ensures we don't show $100 rounding for a $2.7 token
    if (nextOption > currentPrice / 10) {
      break;
    }
    
    // Also keep the absolute maximum as a safety net
    if (nextOption > 1000) {
      break;
    }
    
    options.push(nextOption);
  }

  // Set the calculated options with third item as default (if available), or second, or first
  const defaultRounding = options.length >= 3 ? options[2] : 
                          options.length >= 2 ? options[1] : 
                          baseRounding;
  setAvailableRoundingOptions(options, defaultRounding);
}

function setSelectedSymbol(symbol) {
  const previousSymbol = state.selectedSymbol;
  state.selectedSymbol = symbol;
  if (previousSymbol !== symbol) {
    state.currentOrderBook = { bids: [], asks: [], symbol: '', timestamp: 0 };
    state.currentCandles = [];
    state.currentTicker = null;
    state.candlesWsConnected = false;
    state.orderBookWsConnected = false;
    state.tickerWsConnected = false;
    state.selectedRounding = null;
    state.availableRoundingOptions = [];
    
    // Rounding options will be calculated after fetchOrderBook provides current price data
  }
  notify('selectedSymbol');
  notify('currentOrderBook');
  notify('currentCandles');
  notify('currentTicker');
  notify('candlesWsConnected');
  notify('orderBookWsConnected');
  notify('tickerWsConnected');
  notify('selectedRounding');
  notify('availableRoundingOptions');
}

function setSelectedTimeframe(timeframe) {
  state.selectedTimeframe = timeframe;
  state.currentCandles = [];
  notify('selectedTimeframe');
  notify('currentCandles');
}

function updateOrderBookFromWebSocket(payload) {
  const validatedOrderBook = validateOrderBook(payload);
  if (validatedOrderBook) {
    if (state.selectedSymbol && validatedOrderBook.symbol === state.selectedSymbol) {
      state.currentOrderBook = validatedOrderBook;
      notify('currentOrderBook');
    } else {
      console.warn('Received order book for different symbol, skipping update:', validatedOrderBook.symbol, 'vs', state.selectedSymbol);
    }
  }
}

function updateCandlesFromWebSocket(payload) {
  const incomingData = payload;
  if (state.selectedSymbol && incomingData.symbol && incomingData.symbol !== state.selectedSymbol) {
    console.warn('Received candle for different symbol, skipping update:', incomingData.symbol, 'vs', state.selectedSymbol);
    return;
  }

  const [newCandle] = validateAndFilterCandles([incomingData]);
  
  if (!newCandle) {
    console.warn('Received invalid candle from WebSocket, skipping update:', incomingData);
    return;
  }

  const existingIndex = state.currentCandles.findIndex(
    candle => candle.timestamp === newCandle.timestamp
  );
  
  if (existingIndex >= 0) {
    state.currentCandles[existingIndex] = newCandle;
  } else {
    state.currentCandles.push(newCandle);
    if (state.currentCandles.length > 100) {
      state.currentCandles = state.currentCandles.slice(-100);
    }
    state.currentCandles.sort((a, b) => a.timestamp - b.timestamp);
  }
  notify('currentCandles');
}

function setCandlesWsConnected(connected) {
  state.candlesWsConnected = connected;
  notify('candlesWsConnected');
}

function setOrderBookWsConnected(connected) {
  state.orderBookWsConnected = connected;
  notify('orderBookWsConnected');
}

function updateTickerFromWebSocket(payload) {
  const validatedTicker = validateTicker(payload);
  if (validatedTicker) {
    if (state.selectedSymbol && validatedTicker.symbol === state.selectedSymbol) {
      state.currentTicker = validatedTicker;
      notify('currentTicker');
    } else {
      console.warn('Received ticker for different symbol, skipping update:', validatedTicker.symbol, 'vs', state.selectedSymbol);
    }
  }
}

function setTickerWsConnected(connected) {
  state.tickerWsConnected = connected;
  notify('tickerWsConnected');
}

function clearError() {
  state.candlesError = null;
  state.orderBookError = null;
  state.symbolsError = null;
  state.tickerError = null;
  notify('candlesError');
  notify('orderBookError');
  notify('symbolsError');
  notify('tickerError');
}

function setSelectedRounding(rounding) {
  state.selectedRounding = rounding;
  notify('selectedRounding');
}

function setAvailableRoundingOptions(options, defaultRounding) {
  state.availableRoundingOptions = options;
  state.selectedRounding = defaultRounding;
  notify('availableRoundingOptions');
  notify('selectedRounding');
}

function setShouldRestartWebSocketAfterFetch(value) {
  state.shouldRestartWebSocketAfterFetch = value;
  notify('shouldRestartWebSocketAfterFetch');
}

function setDisplayDepth(depth) {
  state.displayDepth = depth;
  notify('displayDepth');
}

function clearOrderBook() {
  state.currentOrderBook = { bids: [], asks: [], symbol: '', timestamp: 0 };
  state.orderBookWsConnected = false;
  state.orderBookLoading = true; // Indicate transition state
  notify('currentOrderBook');
  notify('orderBookWsConnected');
  notify('orderBookLoading');
}

function setTradingMode(mode) {
  state.tradingMode = mode;
  notify('tradingMode');
}

function clearTradeError() {
  state.tradeError = null;
  notify('tradeError');
}

function clearPositionsError() {
  state.positionsError = null;
  notify('positionsError');
}

function setTheme(theme) {
  state.currentTheme = theme;
  localStorage.setItem('theme', theme);
  document.documentElement.setAttribute('data-theme', theme);
  notify('currentTheme');
}

function addToTradeHistory(trade) {
  state.tradeHistory.unshift(trade);
  if (state.tradeHistory.length > 100) {
    state.tradeHistory = state.tradeHistory.slice(0, 100);
  }
  notify('tradeHistory');
}

// Helper function to get valid Binance orderbook limit
function getValidOrderBookLimit(desiredLimit) {
  // Binance API supports: 5, 10, 20, 50, 100, 500, 1000 (max for futures)
  const validLimits = [5, 10, 20, 50, 100, 500, 1000];
  
  // For higher rounding values, use maximum depth (1000) to get best market coverage
  // This helps address market depth limitations at wider price ranges
  const minimumLimit = Math.max(100, desiredLimit * 50); // Use aggressive multiplier for depth
  
  // Find the smallest valid limit that's >= minimum limit
  for (const limit of validLimits) {
    if (limit >= minimumLimit) {
      return limit;
    }
  }
  
  // Always return maximum limit (1000) for best market depth coverage
  return 1000;
}

// Async functions (equivalent to Redux thunks)
async function fetchSymbols() {
  state.symbolsLoading = true;
  state.symbolsError = null;
  notify('symbolsLoading');
  notify('symbolsError');
  try {
    const response = await fetch(`${API_BASE_URL}/symbols`);
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || errorData.message || 'Failed to fetch symbols');
    }
    const data = await response.json();
    state.symbolsList = data.map(symbol => ({
      ...symbol,
      pricePrecision: symbol.pricePrecision ?? undefined,
    }));
    state.symbolsLoading = false;
    notify('symbolsList');
    notify('symbolsLoading');
  } catch (error) {
    state.symbolsLoading = false;
    state.symbolsError = error.message;
    notify('symbolsLoading');
    notify('symbolsError');
  }
}

async function fetchOrderBook(symbol, limit) {
  state.orderBookLoading = true;
  state.orderBookError = null;
  notify('orderBookLoading');
  notify('orderBookError');
  try {
    // Use valid Binance limit if limit is provided
    const validLimit = limit ? getValidOrderBookLimit(limit) : null;
    const params = validLimit ? `?limit=${validLimit}` : '';
    const response = await fetch(`${API_BASE_URL}/orderbook/${symbol}${params}`);
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || errorData.message || 'Failed to fetch order book');
    }
    const data = await response.json();
    const validatedOrderBook = validateOrderBook(data);
    if (validatedOrderBook) {
      state.currentOrderBook = validatedOrderBook;
      
      // Calculate rounding options now that we have current price data from orderbook
      if (symbol === state.selectedSymbol && state.availableRoundingOptions.length === 0) {
        calculateAndSetRoundingOptions(symbol);
        // Notify orderbook update again so display refreshes with new rounding selection
        notify('currentOrderBook');
      }
    } else {
      state.orderBookError = 'Received invalid order book data from server';
    }
    state.orderBookLoading = false;
    notify('currentOrderBook');
    notify('orderBookLoading');
    notify('orderBookError');
  } catch (error) {
    state.orderBookLoading = false;
    state.orderBookError = error.message;
    notify('orderBookLoading');
    notify('orderBookError');
  }
}

async function fetchCandles(symbol, timeframe = '1m', limit = 100) {
  state.candlesLoading = true;
  state.candlesError = null;
  notify('candlesLoading');
  notify('candlesError');
  try {
    const response = await fetch(`${API_BASE_URL}/candles/${symbol}?timeframe=${timeframe}&limit=${limit}`);
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || errorData.message || 'Failed to fetch candles');
    }
    const data = await response.json();
    state.currentCandles = validateAndFilterCandles(data);
    state.candlesLoading = false;
    notify('currentCandles');
    notify('candlesLoading');
  } catch (error) {
    state.candlesLoading = false;
    state.candlesError = error.message;
    notify('candlesLoading');
    notify('candlesError');
  }
}

async function fetchOpenPositions() {
  state.positionsLoading = true;
  state.positionsError = null;
  notify('positionsLoading');
  notify('positionsError');
  try {
    const response = await fetch(`${API_BASE_URL}/positions`);
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || errorData.message || 'Could not load your positions.');
    }
    const data = await response.json();
    state.openPositions = data;
    state.positionsLoading = false;
    notify('openPositions');
    notify('positionsLoading');
  } catch (error) {
    state.positionsLoading = false;
    state.positionsError = error.message;
    notify('positionsLoading');
    notify('positionsError');
  }
}

async function executeTrade(tradeDetails, mode) {
  state.isSubmittingTrade = true;
  state.tradeError = null;
  notify('isSubmittingTrade');
  notify('tradeError');
  try {
    const response = await fetch(`${API_BASE_URL}/trade`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ ...tradeDetails, mode }),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || errorData.message || `Could not execute ${mode} trade.`);
    }
    const data = await response.json();
    addToTradeHistory(data);
    await fetchOpenPositions(); // Re-fetch positions after successful trade
    state.isSubmittingTrade = false;
    notify('isSubmittingTrade');
  } catch (error) {
    state.isSubmittingTrade = false;
    state.tradeError = error.message;
    notify('isSubmittingTrade');
    notify('tradeError');
  }
}

async function executePaperTrade(tradeDetails) {
  await executeTrade(tradeDetails, 'paper');
}

async function executeLiveTrade(tradeDetails) {
  await executeTrade(tradeDetails, 'live');
}

async function setTradingModeApi(mode) {
  try {
    const response = await fetch(`${API_BASE_URL}/set_trading_mode`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ mode }),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || errorData.message || 'Could not change trading mode.');
    }
    state.tradingMode = mode;
    notify('tradingMode');
  } catch (error) {
    state.tradeError = error.message;
    notify('tradeError');
  }
}

export { 
  state, 
  subscribe, 
  setState,
  setSelectedSymbol,
  setSelectedTimeframe,
  updateOrderBookFromWebSocket,
  updateCandlesFromWebSocket,
  setCandlesWsConnected,
  setOrderBookWsConnected,
  updateTickerFromWebSocket,
  setTickerWsConnected,
  clearError,
  setSelectedRounding,
  setAvailableRoundingOptions,
  setShouldRestartWebSocketAfterFetch,
  setDisplayDepth,
  clearOrderBook,
  fetchSymbols,
  fetchOrderBook,
  fetchCandles,
  setTradingMode,
  clearTradeError,
  clearPositionsError,
  setTheme,
  addToTradeHistory,
  fetchOpenPositions,
  executePaperTrade,
  executeLiveTrade,
  setTradingModeApi,
  getValidOrderBookLimit
};
