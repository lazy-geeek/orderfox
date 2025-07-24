/**
 * Centralized WebSocket connection management for OrderFox.
 * 
 * This module provides reusable functions for managing WebSocket connections
 * across different UI components, eliminating code duplication and ensuring
 * consistent connection handling patterns.
 */

import {
  state,
  clearOrderBook,
  clearTrades,
  setSelectedSymbol,
  setSelectedTimeframe,
  getSelectedBot,
} from '../store/store.js';

import { resetZoomState } from '../components/LightweightChart.js';

import {
  connectWebSocketStream,
  disconnectWebSocketStream,
  disconnectAllWebSockets,
  updateOrderBookParameters,
} from './websocketService.js';


/**
 * Get chart container width for backend calculation.
 * Backend will calculate optimal candle count based on this width.
 * 
 * @returns {number} Container width in pixels
 */
function getContainerWidth() {
  // Get chart container width (fallback to reasonable default if not available)
  const chartContainer = document.querySelector('.chart-container');
  
  // If container doesn't exist yet, return default
  if (!chartContainer) {
    return 800; // Default 800px
  }
  
  // Check if container is visible to avoid forced reflow on hidden elements
  if (chartContainer.offsetParent === null) {
    return 800; // Default for hidden elements
  }
  
  const containerWidth = chartContainer.clientWidth || 800;
  
  return containerWidth;
}

/**
 * WebSocket connection manager with centralized logic for common operations.
 * Now includes bot context support for trading operations.
 */
export class WebSocketManager {
  /**
   * Switch to a new trading symbol with full WebSocket reconnection.
   * Includes bot context validation.
   * 
   * @param {string} newSymbol - The new symbol to switch to
   * @param {boolean} validateBotContext - Whether to validate bot context (default: true)
   */
  static async switchSymbol(newSymbol, validateBotContext = true) {
    // Bot context validation
    if (validateBotContext) {
      const selectedBot = getSelectedBot();
      if (selectedBot && selectedBot.symbol !== newSymbol) {
        console.warn(`Symbol ${newSymbol} does not match selected bot symbol ${selectedBot.symbol}`);
        // Allow the switch but log the mismatch for debugging
      }
    }
    
    // CRITICAL: Clear any pending chart updates immediately
    if (typeof window !== 'undefined' && window.updateLatestCandleDirectly) {
      // Temporarily disable direct updates during symbol switch
      const originalUpdate = window.updateLatestCandleDirectly;
      window.updateLatestCandleDirectly = () => {
        // Ignore candle updates during symbol switch
      };
      
      // Restore after a short delay to allow WebSocket cleanup
      setTimeout(() => {
        window.updateLatestCandleDirectly = originalUpdate;
      }, 100);
    }

    // Update state first
    setSelectedSymbol(newSymbol);
    
    // Reset UI state
    resetZoomState();
    clearOrderBook();
    clearTrades();
    
    // CRITICAL: Clear current candles to prevent stale data
    if (typeof window !== 'undefined' && window.state && window.state.currentCandles) {
      window.state.currentCandles = [];
    }
    
    // CRITICAL: Reset chart data completely to prevent timestamp conflicts
    if (typeof window !== 'undefined' && window.resetChartData) {
      window.resetChartData();
    }
    
    // Disconnect all existing streams
    disconnectAllWebSockets();
    
    // Wait for connections to fully close to prevent race conditions
    // Backend processing can take up to 6+ seconds (seen in logs)
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Connect new WebSocket streams with container width for backend calculation
    const containerWidth = getContainerWidth();
    connectWebSocketStream(newSymbol, 'candles', state.selectedTimeframe, containerWidth);
    connectWebSocketStream(newSymbol, 'orderbook', null, state.displayDepth, state.selectedRounding);
    connectWebSocketStream(newSymbol, 'trades');
    // Connect both liquidation streams - one for orders (table) and one for volume (chart)
    connectWebSocketStream(newSymbol, 'liquidations'); // For orders table (without timeframe)
    connectWebSocketStream(newSymbol, 'liquidations', state.selectedTimeframe); // For volume chart (with timeframe)
    
    // Fetch liquidation volume data for new symbol
    this.fetchLiquidationVolumeData(newSymbol, state.selectedTimeframe);
  }

  /**
   * Switch to a new timeframe with targeted candles stream reconnection.
   * 
   * @param {string} newTimeframe - The new timeframe to switch to
   */
  static async switchTimeframe(newTimeframe) {
    // CRITICAL: Store old timeframe before updating state
    const oldTimeframe = state.selectedTimeframe;
    
    // CRITICAL: Clear any pending chart updates immediately
    if (typeof window !== 'undefined' && window.updateLatestCandleDirectly) {
      // Temporarily disable direct updates during timeframe switch
      const originalUpdate = window.updateLatestCandleDirectly;
      window.updateLatestCandleDirectly = () => {
        // Ignore candle updates during timeframe switch
      };
      
      // Restore after a delay to allow WebSocket cleanup
      setTimeout(() => {
        window.updateLatestCandleDirectly = originalUpdate;
      }, 200);
    }
    
    // Update state after storing old value
    setSelectedTimeframe(newTimeframe);
    
    // Reset zoom state for timeframe changes
    resetZoomState();
    
    // CRITICAL: Clear current candles to prevent stale data
    if (typeof window !== 'undefined' && window.state && window.state.currentCandles) {
      window.state.currentCandles = [];
    }
    
    // CRITICAL: Reset chart data completely to prevent timestamp conflicts
    if (typeof window !== 'undefined' && window.resetChartData) {
      window.resetChartData();
    }
    
    // CRITICAL: Disconnect streams using the OLD timeframe, not the new one
    disconnectWebSocketStream('candles', state.selectedSymbol, oldTimeframe);
    disconnectWebSocketStream('liquidations', state.selectedSymbol, oldTimeframe);
    
    // Small delay to ensure cleanup completes
    await new Promise(resolve => setTimeout(resolve, 50));
    
    // Connect new streams with new timeframe
    const containerWidth = getContainerWidth();
    connectWebSocketStream(state.selectedSymbol, 'candles', newTimeframe, containerWidth);
    connectWebSocketStream(state.selectedSymbol, 'liquidations', newTimeframe);
    
    // Fetch liquidation volume data for new timeframe
    this.fetchLiquidationVolumeData(state.selectedSymbol, newTimeframe);
  }

  /**
   * Initialize WebSocket connections for application startup.
   * 
   * @param {string} symbol - The initial symbol to connect to
   */
  static async initializeConnections(symbol) {
    // Update state first
    setSelectedSymbol(symbol);
    
    // Reset UI state for initial load
    resetZoomState();
    clearOrderBook();
    clearTrades();
    
    // Start WebSocket connections for the selected symbol
    const containerWidth = getContainerWidth();
    connectWebSocketStream(symbol, 'candles', state.selectedTimeframe, containerWidth);
    connectWebSocketStream(symbol, 'orderbook', null, state.displayDepth, state.selectedRounding);
    connectWebSocketStream(symbol, 'trades');
    // Note: LiquidationDisplay component creates its own connection without timeframe
    // connectWebSocketStream(symbol, 'liquidations'); // Handled by component
    connectWebSocketStream(symbol, 'liquidations', state.selectedTimeframe); // For volume with timeframe
    
    // Fetch initial liquidation volume data
    this.fetchLiquidationVolumeData(symbol, state.selectedTimeframe);
  }

  /**
   * Update order book parameters without full reconnection.
   * 
   * @param {string} symbol - The current symbol
   * @param {number} newDepth - New display depth
   * @param {number} newRounding - New rounding value
   * @returns {boolean} Success status
   */
  static updateOrderBookParams(symbol, newDepth, newRounding) {
    return updateOrderBookParameters(symbol, newDepth, newRounding);
  }

  /**
   * Get container width for external use.
   * 
   * @returns {number} Container width in pixels
   */
  static getContainerWidth() {
    return getContainerWidth();
  }

  /**
   * Fetch and initialize liquidation volume data.
   * 
   * @param {string} symbol - Trading symbol
   * @param {string} timeframe - Chart timeframe
   */
  static async fetchLiquidationVolumeData(symbol, timeframe) {
    try {
      // The backend will now handle time range calculation based on actual candle data
      // We just need to connect the WebSocket, which will send the properly aligned data
      console.log(`Liquidation volume will be fetched via WebSocket for ${symbol}/${timeframe}`);
      
      // The liquidation WebSocket with timeframe parameter will handle fetching
      // historical volume data that matches the candle time range
    } catch (error) {
      console.warn('Failed to initialize liquidation volume:', error);
    }
  }

  /**
   * Initialize connections for a specific bot context.
   * This method ensures the symbol and bot are properly synchronized.
   * 
   * @param {Object} bot - Bot object with symbol and configuration
   */
  static async initializeBotContext(bot) {
    if (!bot || !bot.symbol) {
      throw new Error('Invalid bot object or missing symbol');
    }

    console.log(`Initializing bot context for ${bot.name} (${bot.symbol})`);
    
    // Update state with bot's symbol
    setSelectedSymbol(bot.symbol);
    
    // Reset UI state for bot context
    resetZoomState();
    clearOrderBook();
    clearTrades();
    
    // Start WebSocket connections for the bot's symbol
    const containerWidth = getContainerWidth();
    connectWebSocketStream(bot.symbol, 'candles', state.selectedTimeframe, containerWidth);
    connectWebSocketStream(bot.symbol, 'orderbook', null, state.displayDepth, state.selectedRounding);
    connectWebSocketStream(bot.symbol, 'trades');
    // Connect both liquidation streams - one for orders (table) and one for volume (chart)
    connectWebSocketStream(bot.symbol, 'liquidations'); // For orders table (without timeframe)
    connectWebSocketStream(bot.symbol, 'liquidations', state.selectedTimeframe); // For volume chart (with timeframe)
    
    // Fetch initial liquidation volume data
    this.fetchLiquidationVolumeData(bot.symbol, state.selectedTimeframe);
  }

  /**
   * Switch to a bot's trading context with full validation.
   * This is the preferred method for bot-based trading.
   * 
   * @param {Object} bot - Bot object to switch to
   */
  static async switchToBotContext(bot) {
    if (!bot || !bot.symbol) {
      throw new Error('Invalid bot object or missing symbol');
    }

    // If the bot's symbol is different from current, switch to it
    if (bot.symbol !== state.selectedSymbol) {
      console.log(`Switching to bot context: ${bot.name} (${bot.symbol})`);
      await this.switchSymbol(bot.symbol, false); // Don't validate bot context since we're setting it
    }
    
    // Additional bot-specific setup could go here
    // For example, setting up bot-specific trading parameters
    console.log(`Bot context active: ${bot.name} (${bot.isActive ? 'Active' : 'Inactive'})`);
  }

  /**
   * Validate current WebSocket connections against bot context.
   * 
   * @param {Object} bot - Bot object to validate against
   * @returns {boolean} True if connections are valid for bot context
   */
  static validateBotConnections(bot) {
    if (!bot || !bot.symbol) {
      return false;
    }

    // Check if current symbol matches bot symbol
    if (state.selectedSymbol !== bot.symbol) {
      console.warn(`Connection validation failed: Symbol mismatch (${state.selectedSymbol} vs ${bot.symbol})`);
      return false;
    }

    // Additional validation could be added here
    // For example, checking if bot is still active
    if (!bot.isActive) {
      console.warn(`Bot ${bot.name} is not active`);
      return false;
    }

    return true;
  }

  /**
   * Get current bot context information.
   * 
   * @returns {Object} Bot context info
   */
  static getBotContext() {
    const selectedBot = getSelectedBot();
    return {
      bot: selectedBot,
      symbol: state.selectedSymbol,
      timeframe: state.selectedTimeframe,
      isValid: selectedBot ? this.validateBotConnections(selectedBot) : false,
      hasActiveConnections: state.candlesWsConnected || state.orderBookWsConnected || state.tradesWsConnected
    };
  }

  /**
   * Handle bot deactivation by cleaning up connections.
   * 
   * @param {Object} bot - Bot that was deactivated
   */
  static async handleBotDeactivation(bot) {
    if (!bot) return;

    console.log(`Handling bot deactivation: ${bot.name}`);
    
    // If this is the currently active bot, we might want to disconnect
    const currentBot = getSelectedBot();
    if (currentBot && currentBot.id === bot.id) {
      console.log('Deactivated bot was currently active, maintaining connections but adding warning');
      // We could disconnect here, but for now just log the warning
      // In a future version, we might want to switch to a different bot or show a warning
    }
  }

  /**
   * Get connection status for bot context.
   * 
   * @returns {Object} Connection status object
   */
  static getBotConnectionStatus() {
    const selectedBot = getSelectedBot();
    return {
      bot: selectedBot,
      symbol: state.selectedSymbol,
      connections: {
        candles: state.candlesWsConnected,
        orderbook: state.orderBookWsConnected,
        trades: state.tradesWsConnected,
        liquidations: state.liquidationsWsConnected
      },
      isValid: selectedBot ? this.validateBotConnections(selectedBot) : false,
      lastUpdate: new Date().toISOString()
    };
  }

  /**
   * Disconnect all WebSocket connections.
   * Wrapper around the websocketService function for consistency.
   */
  static disconnectAllWebSockets() {
    disconnectAllWebSockets();
  }
}

/**
 * Connection utilities for consistent parameter handling.
 */
export const ConnectionUtils = {
  /**
   * Get standardized connection parameters for a stream type.
   * 
   * @param {string} symbol - Trading symbol
   * @param {string} streamType - Type of stream ('candles', 'orderbook', 'ticker')
   * @param {string|null} timeframe - Timeframe for candles streams
   * @param {number|null} limit - Limit parameter
   * @param {number|null} rounding - Rounding parameter for orderbook
   * @returns {object} Standardized connection parameters
   */
  getConnectionParams(symbol, streamType, timeframe = null, limit = null, rounding = null) {
    const baseParams = { symbol, streamType, timeframe, limit, rounding };
    
    // For candles streams, always use container width
    if (streamType === 'candles') {
      return {
        ...baseParams,
        limit: getContainerWidth()
      };
    }
    
    return baseParams;
  },

  /**
   * Check if two connection parameter sets are equivalent.
   * 
   * @param {object} params1 - First parameter set
   * @param {object} params2 - Second parameter set
   * @returns {boolean} True if parameters are equivalent
   */
  areParamsEquivalent(params1, params2) {
    const keys = ['symbol', 'streamType', 'timeframe', 'limit', 'rounding'];
    return keys.every(key => params1[key] === params2[key]);
  }
};