
import './style.css';

import { createMainLayout } from './layouts/MainLayout.js';
import { createCandlestickChart, createTimeframeSelector, createVolumeToggleButton, updateCandlestickChart, updateLatestCandle, updateLiquidationVolume, toggleLiquidationVolume, resetZoomState, resetChartData } from './components/LightweightChart.js';
import { createOrderBookDisplay, updateOrderBookDisplay } from './components/OrderBookDisplay.js';
import { createLastTradesDisplay, updateLastTradesDisplay, updateTradesHeaders } from './components/LastTradesDisplay.js';
import { LiquidationDisplay } from './components/LiquidationDisplay.js';
import { createTradingModeToggle, updateTradingModeToggle } from './components/TradingModeToggle.js';
import { createThemeSwitcher, initializeTheme } from './components/ThemeSwitcher.js';
import { createBotNavigation, addNavigationEventListeners, showSelectedBotInfo } from './components/BotNavigation.js';
import { createBotList, updateBotList, addBotListEventListeners } from './components/BotList.js';
import { createBotEditor, showBotEditor, hideBotEditor, addBotEditorEventListeners, showFormError, setFormLoading } from './components/BotEditor.js';

import {
  state,
  subscribe,
  fetchSymbols,
  setTradingModeApi,
  setSelectedRounding,
  setDisplayDepth,
  notify,
  fetchBots,
  createBot,
  updateBotById,
  deleteBotById,
  toggleBotStatus,
  setSelectedBotId,
  getSelectedBot,
  setBotError,
  clearBotError,
  setCurrentView,
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
const candlestickChartPlaceholder = document.querySelector('#candlestick-chart-placeholder');
const orderBookPlaceholder = document.querySelector('#order-book-placeholder');
const lastTradesPlaceholder = document.querySelector('#last-trades-container');
const liquidationPlaceholder = document.querySelector('#liquidation-container');
const tradingModeTogglePlaceholder = document.querySelector('#trading-mode-toggle-placeholder');
const themeSwitcherPlaceholder = document.querySelector('#theme-switcher-placeholder');
const botNavigationPlaceholder = document.querySelector('#bot-navigation-placeholder');
const botListPlaceholder = document.querySelector('#bot-list-placeholder');

// Create and append the actual components
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

// Create bot navigation
const botNavigation = createBotNavigation();
botNavigationPlaceholder.replaceWith(botNavigation);

// Create bot list
const botList = createBotList();
botListPlaceholder.replaceWith(botList);

// Create bot editor modal
const botEditor = createBotEditor();
document.body.appendChild(botEditor);

// Add navigation event listeners
addNavigationEventListeners(botNavigation, (action, itemId) => {
  console.log('Navigation action:', action, 'Item:', itemId);
  
  switch (action) {
    case 'show-bot-list':
      setCurrentView('bot-management');
      window.showBotManagementSection();
      break;
    case 'create-bot':
      showBotEditor(botEditor, { 
        symbols: state.symbolsList,
        mode: 'create' 
      });
      break;
    case 'show-trading':
      setCurrentView('trading');
      window.showTradingInterface();
      break;
    default:
      console.log('Unknown navigation action:', action);
  }
});

// Add bot list event listeners
addBotListEventListeners(botList, {
  onCreateBot: () => {
    showBotEditor(botEditor, {
      symbols: state.symbolsList,
      mode: 'create'
    });
  },
  onEditBot: (botId) => {
    const bot = state.bots.find(b => b.id === botId);
    if (bot) {
      showBotEditor(botEditor, {
        bot,
        symbols: state.symbolsList,
        mode: 'edit'
      });
    }
  },
  onDeleteBot: async (botId) => {
    const bot = state.bots.find(b => b.id === botId);
    if (bot && confirm(`Are you sure you want to delete "${bot.name}"?`)) {
      try {
        await deleteBotById(botId);
        console.log('Bot deleted successfully');
      } catch (error) {
        console.error('Error deleting bot:', error);
        setBotError(error.message);
      }
    }
  },
  onToggleBot: async (botId) => {
    try {
      await toggleBotStatus(botId);
      console.log('Bot status toggled successfully');
    } catch (error) {
      console.error('Error toggling bot status:', error);
      setBotError(error.message);
    }
  },
  onSelectBot: async (botId) => {
    setSelectedBotId(botId);
    const selectedBot = getSelectedBot();
    
    if (selectedBot) {
      showSelectedBotInfo(botNavigation, selectedBot);
      
      // Use WebSocketManager to switch to bot context
      try {
        await WebSocketManager.switchToBotContext(selectedBot);
        setCurrentView('trading');
        window.showTradingInterface();
        console.log(`Successfully switched to bot context: ${selectedBot.name}`);
      } catch (error) {
        console.error('Error switching to bot context:', error);
        setBotError(`Failed to switch to bot context: ${error.message}`);
      }
    }
  },
  onRetryLoad: () => {
    fetchBots();
  }
});

// Add bot editor event listeners
addBotEditorEventListeners(botEditor, {
  onSave: async (formData) => {
    try {
      clearBotError();
      setFormLoading(botEditor, true);
      
      // Check if we're editing by looking at the modal title
      const modalTitle = botEditor.querySelector('#modal-title');
      const isEditing = modalTitle.textContent.includes('Edit Bot');
      
      if (isEditing) {
        // Extract bot ID from title - format: "Edit Bot: {name}"
        const botName = modalTitle.textContent.replace('Edit Bot: ', '');
        const currentBot = state.bots.find(b => b.name === botName);
        
        if (currentBot) {
          await updateBotById(currentBot.id, formData);
          console.log('Bot updated successfully');
        } else {
          throw new Error('Bot not found for editing');
        }
      } else {
        // Create new bot
        await createBot(formData);
        console.log('Bot created successfully');
      }
      
      // Success - close modal and refresh list
      hideBotEditor(botEditor);
      await fetchBots();
      
    } catch (error) {
      console.error('Error saving bot:', error);
      setBotError(error.message);
      
      // Show error in modal
      showFormError(botEditor, error.message);
      setFormLoading(botEditor, false);
      
      // Don't close modal on error - let user see the error and retry
    }
  },
  onCancel: () => {
    clearBotError();
    hideBotEditor(botEditor);
  }
});

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
    // Use the is_update flag from backend to determine if this is a real-time update
    const isRealTimeUpdate = data.is_update || false;
    console.log('Processing liquidation volume update, is_update:', isRealTimeUpdate, 'data points:', data.data.length);
    updateLiquidationVolume(data.data, isRealTimeUpdate);
  }
};

// Set up global function for liquidation volume toggle
window.toggleLiquidationVolume = () => {
  return toggleLiquidationVolume();
};

// Global functions for layout management
window.showBotSelectionPrompt = () => {
  document.getElementById('bot-selection-prompt').style.display = 'flex';
  document.getElementById('bot-management-section').style.display = 'none';
  document.getElementById('main-content').style.display = 'none';
};

window.showBotManagementSection = () => {
  document.getElementById('bot-selection-prompt').style.display = 'none';
  document.getElementById('bot-management-section').style.display = 'flex';
  document.getElementById('main-content').style.display = 'none';
};

window.showTradingInterface = () => {
  document.getElementById('bot-selection-prompt').style.display = 'none';
  document.getElementById('bot-management-section').style.display = 'none';
  document.getElementById('main-content').style.display = 'flex';
};

// Note: getOptimalCandleCount() function moved to WebSocketManager for centralization

// Initial renders
updateCandlestickChart({ currentCandles: state.currentCandles, candlesWsConnected: state.candlesWsConnected }, state.selectedSymbol, state.selectedTimeframe, true); // isInitialLoad = true
updateOrderBookDisplay(orderBookDisplay, state);
updateLastTradesDisplay(lastTradesDisplay, state);
updateTradingModeToggle(tradingModeToggle, state);

// Subscribe to state changes and update UI
subscribe((key) => {
  switch (key) {
    case 'bots':
    case 'botLoading':
    case 'botError':
      updateBotList(botList, state.bots, {
        loading: state.botLoading,
        error: state.botError
      });
      break;
    case 'selectedBotId':
      showSelectedBotInfo(botNavigation, getSelectedBot());
      break;
    case 'selectedSymbol': {
      const selectedSymbolData = state.symbolsList.find(s => s.id === state.selectedSymbol);
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
Promise.all([
  fetchSymbols(),
  fetchBots()
]).then(() => {
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
  
  // Initialize bot list display
  updateBotList(botList, state.bots, {
    loading: state.botLoading,
    error: state.botError
  });
  
  // Show initial view based on bot availability
  if (state.bots.length > 0) {
    setCurrentView('bot-management');
    window.showBotManagementSection();
  } else {
    setCurrentView('bot-selection');
    window.showBotSelectionPrompt();
  }
});

// Global cleanup on page unload
window.addEventListener('beforeunload', () => {
  disconnectAllWebSockets();
});
