
import './style.css';

import { createMainLayout } from './layouts/MainLayout.js';
// Chart components are now managed by TradingModal - no direct imports needed
// import { createCandlestickChart, createTimeframeSelector, createVolumeToggleButton, updateCandlestickChart, updateLatestCandle, updateLiquidationVolume, toggleLiquidationVolume, resetZoomState, resetChartData } from './components/LightweightChart.js';
import { updateTradesHeaders } from './components/LastTradesDisplay.js';
import { createTabbedTradingDisplay } from './components/TabbedTradingDisplay.js';
import { createTradingModal } from './components/TradingModal.js';
import { createThemeSwitcher, initializeTheme } from './components/ThemeSwitcher.js';
import { createBotNavigation, addNavigationEventListeners, showSelectedBotInfo } from './components/BotNavigation.js';
import { createBotList, updateBotList, addBotListEventListeners } from './components/BotList.js';
import { createBotEditor, showBotEditor, hideBotEditor, addBotEditorEventListeners, showFormError, setFormLoading } from './components/BotEditor.js';

import {
  state,
  subscribe,
  fetchSymbols,
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
const themeSwitcherPlaceholder = document.querySelector('#theme-switcher-placeholder');
const botNavigationPlaceholder = document.querySelector('#bot-navigation-placeholder');
const botListPlaceholder = document.querySelector('#bot-list-placeholder');

// Create trading modal (lazy initialization)
const tradingModal = createTradingModal();
document.body.appendChild(tradingModal.element);

// Add modal reference to global scope for easy access
window.tradingModal = tradingModal;


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
    case 'show-trading': {
      // Open trading modal if bot is selected
      const selectedBot = getSelectedBot();
      if (selectedBot) {
        tradingModal.open().catch(error => {
          console.error('Error opening trading modal:', error);
          setBotError(`Failed to open trading modal: ${error.message}`);
        });
      } else {
        console.log('No bot selected for trading');
      }
      break;
    }
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
      
      // Check if modal is already open
      if (tradingModal.isOpen()) {
        // Modal is already open - switch bot context without closing
        try {
          await tradingModal.switchBotContext(selectedBot);
          console.log(`Successfully switched to bot context in open modal: ${selectedBot.name}`);
        } catch (error) {
          console.error('Error switching bot context in modal:', error);
          setBotError(`Failed to switch bot context: ${error.message}`);
        }
      } else {
        // Modal is closed - open it for the selected bot
        try {
          await tradingModal.open();
          console.log(`Successfully opened trading modal for bot: ${selectedBot.name}`);
        } catch (error) {
          console.error('Error opening trading modal:', error);
          setBotError(`Failed to open trading modal: ${error.message}`);
        }
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
      
      // Success - reset loading state before closing modal
      setFormLoading(botEditor, false);
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

// IMPORTANT: Global chart functions are now set up by TradingModal when it initializes
// This prevents chart updates from being processed before the chart is ready
// The modal will set up these functions when it creates the chart:
// - window.updateLatestCandleDirectly
// - window.state
// - window.notify
// - window.resetChartData
// - window.updateLiquidationVolume
// - window.toggleLiquidationVolume

// Global functions for layout management (simplified for modal paradigm)
window.showBotSelectionPrompt = () => {
  document.getElementById('bot-selection-prompt').style.display = 'flex';
  document.getElementById('bot-management-section').style.display = 'none';
};

window.showBotManagementSection = () => {
  document.getElementById('bot-selection-prompt').style.display = 'none';
  document.getElementById('bot-management-section').style.display = 'flex';
};

// Note: getOptimalCandleCount() function moved to WebSocketManager for centralization

// Trading interface components are now managed by TradingModal

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
      
      // Update trades headers with new symbol data
      if (selectedSymbolData) {
        updateTradesHeaders(selectedSymbolData);
      }
      break;
    }
    // Chart and trading interface state updates are now handled by TradingModal components
    case 'currentCandles':
    case 'selectedTimeframe':
    case 'currentOrderBook':
    case 'orderBookWsConnected':
    case 'selectedRounding':
    case 'availableRoundingOptions':
    case 'displayDepth':
    case 'orderBookLoading':
    case 'currentTrades':
    case 'tradesWsConnected':
    case 'tradesLoading':
    case 'tradesError':
    case 'candlesWsConnected':
      // These will be handled by components within TradingModal
      break;
    case 'tradingMode':
      break;
    default:
      break;
  }
});

// Chart controls and event listeners are now managed within TradingModal


// Trading mode toggle removed - now a per-bot setting

// Initial data fetch
Promise.all([
  fetchSymbols(),
  fetchBots()
]).then(() => {
  // IMPORTANT: WebSocket connections are now managed by TradingModal
  // Don't initialize connections here to prevent consuming historical data before modal opens
  // if (state.symbolsList.length > 0) {
  //   const firstSymbol = state.symbolsList[0];
  //   WebSocketManager.initializeConnections(firstSymbol.id);
  //   // Update trades headers with initial symbol data
  //   updateTradesHeaders(firstSymbol);
  // }
  
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
