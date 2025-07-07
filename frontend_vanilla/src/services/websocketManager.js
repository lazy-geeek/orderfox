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
 * Calculate optimal number of candles to fetch based on chart viewport size.
 * This ensures the chart viewport is always fully populated with data.
 * 
 * @returns {number} Optimal candle count (200-1000 range)
 */
function getOptimalCandleCount() {
  // Get chart container width (fallback to reasonable default if not available)
  const chartContainer = document.querySelector('.chart-container');
  const containerWidth = chartContainer ? chartContainer.clientWidth : 800; // Default 800px
  
  // Lightweight Charts default bar spacing is ~6 pixels per candle
  const barSpacing = 6;
  
  // Calculate how many candles fit in viewport
  const candlesInViewport = Math.floor(containerWidth / barSpacing);
  
  // Add buffer for smooth scrolling and zooming (3x viewport)
  // Minimum 200, maximum 1000 for performance
  const optimalCount = Math.min(Math.max(candlesInViewport * 3, 200), 1000);
  
  console.log(`Chart width: ${containerWidth}px, Candles in viewport: ${candlesInViewport}, Fetching: ${optimalCount} candles`);
  
  return optimalCount;
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
    // Update state first
    setSelectedSymbol(newSymbol);
    
    // Reset UI state
    resetZoomState();
    clearOrderBook();
    
    // Disconnect all existing streams
    disconnectAllWebSockets();
    
    // Connect new WebSocket streams with optimal parameters
    const optimalCandleCount = getOptimalCandleCount();
    connectWebSocketStream(newSymbol, 'candles', state.selectedTimeframe, optimalCandleCount);
    connectWebSocketStream(newSymbol, 'orderbook', null, state.displayDepth, state.selectedRounding);
  }

  /**
   * Switch to a new timeframe with targeted candles stream reconnection.
   * 
   * @param {string} newTimeframe - The new timeframe to switch to
   */
  static async switchTimeframe(newTimeframe) {
    // Update state first
    setSelectedTimeframe(newTimeframe);
    
    // Reset zoom state for timeframe changes
    resetZoomState();
    
    // Disconnect only the candles stream for the current timeframe
    disconnectWebSocketStream('candles', state.selectedSymbol, state.selectedTimeframe);
    
    // Connect new candles stream with optimal count
    const optimalCandleCount = getOptimalCandleCount();
    connectWebSocketStream(state.selectedSymbol, 'candles', newTimeframe, optimalCandleCount);
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
    
    // Start WebSocket connections for the selected symbol
    const optimalCandleCount = getOptimalCandleCount();
    connectWebSocketStream(symbol, 'candles', state.selectedTimeframe, optimalCandleCount);
    connectWebSocketStream(symbol, 'orderbook', null, state.displayDepth, state.selectedRounding);
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
   * Get optimal candle count for external use.
   * 
   * @returns {number} Optimal candle count
   */
  static getOptimalCandleCount() {
    return getOptimalCandleCount();
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
    
    // For candles streams, always use optimal candle count
    if (streamType === 'candles') {
      return {
        ...baseParams,
        limit: getOptimalCandleCount()
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