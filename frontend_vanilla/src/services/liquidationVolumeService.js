import { API_BASE_URL } from '../config/env.js';

class LiquidationVolumeService {
  constructor() {
    this.cache = new Map();
    this.cacheTimeout = 60000; // 1 minute cache
  }

  /**
   * Fetch liquidation volume data from the API
   * @param {string} symbol - Trading symbol (e.g., BTCUSDT)
   * @param {string} timeframe - Timeframe (1m, 5m, 15m, 1h, 4h, 1d)
   * @param {number} [startTime] - Start timestamp in milliseconds
   * @param {number} [endTime] - End timestamp in milliseconds
   * @returns {Promise<Array>} Array of liquidation volume data
   */
  async fetchLiquidationVolume(symbol, timeframe, startTime = null, endTime = null) {
    // Create cache key
    const cacheKey = `${symbol}:${timeframe}:${startTime}:${endTime}`;
    
    // Check cache
    const cached = this.cache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
      return cached.data;
    }
    
    try {
      const baseUrl = API_BASE_URL;
      
      // Build URL
      let url = `${baseUrl}/liquidation-volume/${symbol}/${timeframe}`;
      const params = new URLSearchParams();
      
      if (startTime) {
        params.append('start_time', startTime);
      }
      if (endTime) {
        params.append('end_time', endTime);
      }
      
      if (params.toString()) {
        url += `?${params.toString()}`;
      }
      
      // Fetch data
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch liquidation volume: ${response.statusText}`);
      }
      
      const result = await response.json();
      
      // Cache the result
      this.cache.set(cacheKey, {
        data: result.data || [],
        timestamp: Date.now()
      });
      
      return result.data || [];
      
    } catch (error) {
      console.error('Error fetching liquidation volume:', error);
      return [];
    }
  }
  
  /**
   * Invalidate cache for a specific symbol/timeframe
   * @param {string} symbol - Trading symbol
   * @param {string} [timeframe] - Timeframe (optional, invalidates all if not provided)
   */
  invalidateCache(symbol, timeframe = null) {
    if (timeframe) {
      // Remove specific entries
      for (const [key] of this.cache) {
        if (key.startsWith(`${symbol}:${timeframe}:`)) {
          this.cache.delete(key);
        }
      }
    } else {
      // Remove all entries for symbol
      for (const [key] of this.cache) {
        if (key.startsWith(`${symbol}:`)) {
          this.cache.delete(key);
        }
      }
    }
  }
  
  /**
   * Clear all cache
   */
  clearCache() {
    this.cache.clear();
  }
}

// Create singleton instance
const liquidationVolumeService = new LiquidationVolumeService();

export default liquidationVolumeService;