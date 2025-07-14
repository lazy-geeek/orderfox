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
  const containerWidth = chartContainer ? chartContainer.clientWidth : 800; // Default 800px
  
  return containerWidth;
}

/**
 * WebSocket connection manager with centralized logic for common operations.
 */
export class WebSocketManager {
  /**
   * Switch to a new trading symbol with full WebSocket reconnection.
   * 
   * @param {string} newSymbol - The new symbol to switch to
   */
  static async switchSymbol(newSymbol) {
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
    connectWebSocketStream(newSymbol, 'liquidations', state.selectedTimeframe);
    
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
    connectWebSocketStream(symbol, 'liquidations', state.selectedTimeframe);
    
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