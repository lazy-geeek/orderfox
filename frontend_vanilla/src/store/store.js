
import { API_BASE_URL } from '../config/env.js';

const state = {
  selectedSymbol: null,
  symbolsList: [],
  currentCandles: [],
  selectedTimeframe: '1m',
  candlesLoading: false,
  candlesError: null,
  candlesWsConnected: false,
  currentOrderBook: { bids: [], asks: [], symbol: '', timestamp: 0 }, // Pre-aggregated data from backend
  orderBookLoading: false,
  orderBookError: null,
  orderBookWsConnected: false,
  currentTicker: null,
  tickerWsConnected: false,
  currentTrades: [],
  tradesLoading: false,
  tradesError: null,
  tradesWsConnected: false,
  currentLiquidations: [],
  liquidationsLoading: false,
  liquidationsError: null,
  liquidationsWsConnected: false,
  liquidationVolume: [],
  liquidationVolumeLoading: false,
  liquidationVolumeError: null,
  selectedRounding: null,
  availableRoundingOptions: [], // Provided by backend
  displayDepth: 10,
  tradeError: null,
  openPositions: [],
  positionsLoading: false,
  positionsError: null,
  currentTheme: localStorage.getItem('theme') || 'dark',
  
  // Bot management state
  bots: [],
  selectedBotId: null,
  botLoading: false,
  botError: null,
  botStats: {
    total: 0,
    active: 0,
    inactive: 0
  },
  currentView: 'bot-selection', // 'bot-selection', 'bot-management', 'trading'
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
    if (Object.prototype.hasOwnProperty.call(state, key)) {
      state[key] = newState[key];
      notify(key);
    }
  }
}

// Helper functions - validation removed, backend provides display-ready data




// Mutator functions (equivalent to Redux reducers and actions)
// calculateAndSetRoundingOptions removed - now handled by backend

function setSelectedSymbol(symbol) {
  const previousSymbol = state.selectedSymbol;
  state.selectedSymbol = symbol;
  if (previousSymbol !== symbol) {
    state.currentOrderBook = { bids: [], asks: [], symbol: '', timestamp: 0 };
    state.currentCandles = [];
    state.currentTicker = null;
    state.currentTrades = [];
    state.currentLiquidations = [];
    state.liquidationVolume = [];
    state.candlesWsConnected = false;
    state.orderBookWsConnected = false;
    state.tickerWsConnected = false;
    state.tradesWsConnected = false;
    state.liquidationsWsConnected = false;
    
    // Set rounding options from symbol data
    const selectedSymbolData = state.symbolsList.find(s => s.id === symbol);
    if (selectedSymbolData && selectedSymbolData.roundingOptions) {
      state.availableRoundingOptions = selectedSymbolData.roundingOptions;
      state.selectedRounding = selectedSymbolData.defaultRounding || selectedSymbolData.roundingOptions[2] || selectedSymbolData.roundingOptions[0];
    } else {
      state.selectedRounding = null;
      state.availableRoundingOptions = [];
    }
  }
  notify('selectedSymbol');
  notify('currentOrderBook');
  notify('currentCandles');
  notify('currentTicker');
  notify('currentTrades');
  notify('currentLiquidations');
  notify('candlesWsConnected');
  notify('orderBookWsConnected');
  notify('tickerWsConnected');
  notify('tradesWsConnected');
  notify('liquidationsWsConnected');
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
  // Direct assignment - backend provides validated data
  if (state.selectedSymbol && payload.symbol === state.selectedSymbol) {
    state.currentOrderBook = payload;
    state.orderBookLoading = false;
    
    notify('currentOrderBook');
    notify('orderBookLoading');
  }
}

function updateCandlesFromWebSocket(payload) {
  // Direct assignment - backend provides validated data
  if (state.selectedSymbol && payload.symbol === state.selectedSymbol) {
    state.currentCandles = payload.candles || payload.data || [];
    
    // Direct chart update for performance
    if (typeof window !== 'undefined' && window.updateLatestCandleDirectly) {
      window.updateLatestCandleDirectly(payload);
    } else {
      notify('currentCandles');
    }
  }
}

function updateCandlesFromHistoricalData(payload) {
  // Direct assignment - backend provides validated data
  if (state.selectedSymbol && payload.symbol === state.selectedSymbol) {
    state.currentCandles = payload.data || [];
    state.candlesLoading = false;
    
    notify('currentCandles');
    notify('candlesLoading');
  }
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
  // Direct assignment - backend provides validated data
  if (state.selectedSymbol && payload.symbol === state.selectedSymbol) {
    state.currentTicker = payload;
    notify('currentTicker');
  }
}

function setTickerWsConnected(connected) {
  state.tickerWsConnected = connected;
  notify('tickerWsConnected');
}

function updateTradesFromWebSocket(payload) {
  // Direct assignment - backend provides validated data
  if (state.selectedSymbol && payload.symbol === state.selectedSymbol) {
    state.currentTrades = payload.trades || [];
    state.tradesLoading = false;
    
    notify('currentTrades');
    notify('tradesLoading');
  }
}

function setTradesWsConnected(connected) {
  state.tradesWsConnected = connected;
  notify('tradesWsConnected');
}

function setTradesLoading(loading) {
  state.tradesLoading = loading;
  notify('tradesLoading');
}

function setTradesError(error) {
  state.tradesError = error;
  notify('tradesError');
}

function clearTradesError() {
  state.tradesError = null;
  notify('tradesError');
}

function clearTrades() {
  state.currentTrades = [];
  state.tradesWsConnected = false;
  state.tradesLoading = true; // Indicate transition state
  notify('currentTrades');
  notify('tradesWsConnected');
  notify('tradesLoading');
}

function updateLiquidationsFromWebSocket(payload) {
  // Direct assignment - backend provides validated data
  if (state.selectedSymbol && payload.symbol === state.selectedSymbol) {
    state.currentLiquidations = payload.liquidations || payload.data || [];
    state.liquidationsLoading = false;
    
    notify('currentLiquidations');
    notify('liquidationsLoading');
  }
}

function updateLiquidationVolume(volumeData) {
  // Update liquidation volume data
  state.liquidationVolume = volumeData || [];
  state.liquidationVolumeLoading = false;
  
  notify('liquidationVolume');
  notify('liquidationVolumeLoading');
}

function setLiquidationVolumeLoading(loading) {
  state.liquidationVolumeLoading = loading;
  notify('liquidationVolumeLoading');
}

function setLiquidationVolumeError(error) {
  state.liquidationVolumeError = error;
  notify('liquidationVolumeError');
}

function getLiquidationVolume() {
  return state.liquidationVolume;
}

function setLiquidationsWsConnected(connected) {
  state.liquidationsWsConnected = connected;
  notify('liquidationsWsConnected');
}

function setLiquidationsLoading(loading) {
  state.liquidationsLoading = loading;
  notify('liquidationsLoading');
}

function setLiquidationsError(error) {
  state.liquidationsError = error;
  notify('liquidationsError');
}

function clearLiquidationsError() {
  state.liquidationsError = null;
  notify('liquidationsError');
}

function clearLiquidations() {
  state.currentLiquidations = [];
  state.liquidationsWsConnected = false;
  state.liquidationsLoading = true; // Indicate transition state
  notify('currentLiquidations');
  notify('liquidationsWsConnected');
  notify('liquidationsLoading');
}

function clearError() {
  state.candlesError = null;
  state.orderBookError = null;
  state.symbolsError = null;
  state.tickerError = null;
  state.tradesError = null;
  state.liquidationsError = null;
  notify('candlesError');
  notify('orderBookError');
  notify('symbolsError');
  notify('tickerError');
  notify('tradesError');
  notify('liquidationsError');
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

function getSelectedSymbolData() {
  if (!state.selectedSymbol || !state.symbolsList) {
    return null;
  }
  
  return state.symbolsList.find(symbol => symbol.id === state.selectedSymbol) || null;
}

function clearOrderBook() {
  state.currentOrderBook = { bids: [], asks: [], symbol: '', timestamp: 0 };
  state.orderBookWsConnected = false;
  state.orderBookLoading = true; // Indicate transition state
  notify('currentOrderBook');
  notify('orderBookWsConnected');
  notify('orderBookLoading');
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

// Backend handles all orderbook depth validation and limits

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
    // Send raw limit - backend handles validation and closest valid limit
    const params = limit ? `?limit=${limit}` : '';
    const response = await fetch(`${API_BASE_URL}/orderbook/${symbol}${params}`);
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || errorData.message || 'Failed to fetch order book');
    }
    const data = await response.json();
    // Trust backend data - no validation needed
    state.currentOrderBook = data;
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
  state.tradeError = null;
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
  } catch (error) {
    state.tradeError = error.message;
    notify('tradeError');
  }
}

async function executePaperTrade(tradeDetails) {
  await executeTrade(tradeDetails, 'paper');
}

async function executeLiveTrade(tradeDetails) {
  await executeTrade(tradeDetails, 'live');
}

// Trading mode removed - now a per-bot setting

// Bot management functions
function setBots(bots) {
  state.bots = bots;
  updateBotStats();
  notify('bots');
  notify('botStats');
}

function addBot(bot) {
  state.bots.push(bot);
  updateBotStats();
  notify('bots');
  notify('botStats');
}

function updateBot(botId, updatedBot) {
  const index = state.bots.findIndex(bot => bot.id === botId);
  if (index !== -1) {
    state.bots[index] = updatedBot;
    updateBotStats();
    notify('bots');
    notify('botStats');
  }
}

function removeBot(botId) {
  state.bots = state.bots.filter(bot => bot.id !== botId);
  if (state.selectedBotId === botId) {
    state.selectedBotId = null;
    notify('selectedBotId');
  }
  updateBotStats();
  notify('bots');
  notify('botStats');
}

function setSelectedBotId(botId) {
  state.selectedBotId = botId;
  notify('selectedBotId');
}

function getSelectedBot() {
  if (!state.selectedBotId) return null;
  return state.bots.find(bot => bot.id === state.selectedBotId) || null;
}

function setBotLoading(loading) {
  state.botLoading = loading;
  notify('botLoading');
}

function setBotError(error) {
  state.botError = error;
  notify('botError');
}

function clearBotError() {
  state.botError = null;
  notify('botError');
}

function setCurrentView(view) {
  state.currentView = view;
  notify('currentView');
}

function updateBotStats() {
  const total = state.bots.length;
  const active = state.bots.filter(bot => bot.isActive).length;
  const inactive = total - active;
  
  state.botStats = {
    total,
    active,
    inactive
  };
}

// Bot API functions
async function fetchBots() {
  setBotLoading(true);
  clearBotError();
  
  try {
    const response = await fetch(`${API_BASE_URL}/bots`);
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || errorData.message || 'Failed to fetch bots');
    }
    const data = await response.json();
    setBots(data.bots || []);
    setBotLoading(false);
  } catch (error) {
    setBotLoading(false);
    setBotError(error.message);
    throw error;
  }
}

async function createBot(botData) {
  setBotLoading(true);
  clearBotError();
  
  try {
    const response = await fetch(`${API_BASE_URL}/bots`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(botData),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || errorData.message || 'Failed to create bot');
    }
    
    const newBot = await response.json();
    addBot(newBot);
    setBotLoading(false);
    return newBot;
  } catch (error) {
    setBotLoading(false);
    setBotError(error.message);
    throw error;
  }
}

async function updateBotById(botId, botData) {
  setBotLoading(true);
  clearBotError();
  
  try {
    const response = await fetch(`${API_BASE_URL}/bots/${botId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(botData),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || errorData.message || 'Failed to update bot');
    }
    
    const updatedBot = await response.json();
    updateBot(botId, updatedBot);
    setBotLoading(false);
    return updatedBot;
  } catch (error) {
    setBotLoading(false);
    setBotError(error.message);
    throw error;
  }
}

async function deleteBotById(botId) {
  setBotLoading(true);
  clearBotError();
  
  try {
    const response = await fetch(`${API_BASE_URL}/bots/${botId}`, {
      method: 'DELETE',
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || errorData.message || 'Failed to delete bot');
    }
    
    removeBot(botId);
    setBotLoading(false);
  } catch (error) {
    setBotLoading(false);
    setBotError(error.message);
    throw error;
  }
}

async function toggleBotStatus(botId) {
  const bot = state.bots.find(b => b.id === botId);
  if (!bot) {
    throw new Error('Bot not found');
  }
  
  setBotLoading(true);
  clearBotError();
  
  try {
    const response = await fetch(`${API_BASE_URL}/bots/${botId}/status?is_active=${!bot.isActive}`, {
      method: 'PATCH',
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || errorData.message || 'Failed to toggle bot status');
    }
    
    const updatedBot = await response.json();
    updateBot(botId, updatedBot);
    setBotLoading(false);
    return updatedBot;
  } catch (error) {
    setBotLoading(false);
    setBotError(error.message);
    throw error;
  }
}

export { 
  state, 
  subscribe, 
  notify,
  setState,
  setSelectedSymbol,
  setSelectedTimeframe,
  updateOrderBookFromWebSocket,
  updateCandlesFromWebSocket,
  updateCandlesFromHistoricalData,
  setCandlesWsConnected,
  setOrderBookWsConnected,
  updateTickerFromWebSocket,
  setTickerWsConnected,
  updateTradesFromWebSocket,
  setTradesWsConnected,
  setTradesLoading,
  setTradesError,
  clearTradesError,
  clearTrades,
  updateLiquidationsFromWebSocket,
  setLiquidationsWsConnected,
  setLiquidationsLoading,
  setLiquidationsError,
  clearLiquidationsError,
  clearLiquidations,
  updateLiquidationVolume,
  setLiquidationVolumeLoading,
  setLiquidationVolumeError,
  getLiquidationVolume,
  clearError,
  setSelectedRounding,
  setAvailableRoundingOptions,
  setShouldRestartWebSocketAfterFetch,
  setDisplayDepth,
  getSelectedSymbolData,
  clearOrderBook,
  fetchSymbols,
  fetchOrderBook,
  clearTradeError,
  clearPositionsError,
  setTheme,
  addToTradeHistory,
  fetchOpenPositions,
  executePaperTrade,
  executeLiveTrade,
  // Bot management functions
  setBots,
  addBot,
  updateBot,
  removeBot,
  setSelectedBotId,
  getSelectedBot,
  setBotLoading,
  setBotError,
  clearBotError,
  setCurrentView,
  // Bot API functions
  fetchBots,
  createBot,
  updateBotById,
  deleteBotById,
  toggleBotStatus
};
