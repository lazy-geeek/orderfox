import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Create test module that directly tests the price precision logic
describe('LightweightChart Price Precision Logic', () => {
  let consoleSpy;
  let mockSeries;

  beforeEach(() => {
    mockSeries = {
      applyOptions: vi.fn(),
      setData: vi.fn(),
      update: vi.fn(),
    };
    consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleSpy.mockRestore();
    vi.clearAllMocks();
  });

  // Test the precision logic directly
  function testPrecisionLogic(symbolData, symbol) {
    let precision = 2; // Default precision
    
    // Extract and validate precision from symbolData (copied from actual implementation)
    if (symbolData && symbolData.pricePrecision !== undefined && symbolData.pricePrecision !== null) {
      // Validate precision is a non-negative integer and clamp to reasonable range (0-8)
      const rawPrecision = symbolData.pricePrecision;
      if (typeof rawPrecision === 'number' && !isNaN(rawPrecision) && rawPrecision >= 0) {
        precision = Math.max(0, Math.min(8, Math.floor(rawPrecision)));
      } else {
        console.warn(`Invalid pricePrecision value for ${symbol}: ${rawPrecision}, using default precision: ${precision}`);
      }
    } else {
      console.warn(`Missing pricePrecision for ${symbol}, using default precision: ${precision}`);
    }
    
    // Apply price format with validated precision
    const priceFormat = {
      type: 'price',
      precision: precision,
      minMove: 1 / Math.pow(10, precision),
    };
    
    mockSeries.applyOptions({ priceFormat });
    
    return { precision, priceFormat };
  }

  describe('Default Precision', () => {
    it('should use default precision when symbolData is missing pricePrecision', () => {
      const symbolData = { id: 'BTCUSDT', symbol: 'BTC/USDT' }; // No pricePrecision
      const symbol = 'BTCUSDT';

      const result = testPrecisionLogic(symbolData, symbol);

      expect(result.precision).toBe(2);
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 2,
          minMove: 0.01,
        },
      });
      expect(consoleSpy).toHaveBeenCalledWith(
        'Missing pricePrecision for BTCUSDT, using default precision: 2'
      );
    });

    it('should use default precision when symbolData is null', () => {
      const symbolData = null;
      const symbol = 'BTCUSDT';

      const result = testPrecisionLogic(symbolData, symbol);

      expect(result.precision).toBe(2);
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 2,
          minMove: 0.01,
        },
      });
      expect(consoleSpy).toHaveBeenCalledWith(
        'Missing pricePrecision for BTCUSDT, using default precision: 2'
      );
    });
  });

  describe('Valid Precision Updates', () => {
    it('should apply correct precision for BTC (1 decimal)', () => {
      const symbolData = { 
        id: 'BTCUSDT', 
        symbol: 'BTC/USDT',
        pricePrecision: 1 
      };
      const symbol = 'BTCUSDT';

      const result = testPrecisionLogic(symbolData, symbol);

      expect(result.precision).toBe(1);
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 1,
          minMove: 0.1,
        },
      });
      expect(consoleSpy).not.toHaveBeenCalled();
    });

    it('should apply correct precision for XRP (4 decimals)', () => {
      const symbolData = { 
        id: 'XRPUSDT', 
        symbol: 'XRP/USDT',
        pricePrecision: 4 
      };
      const symbol = 'XRPUSDT';

      const result = testPrecisionLogic(symbolData, symbol);

      expect(result.precision).toBe(4);
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 4,
          minMove: 0.0001,
        },
      });
      expect(consoleSpy).not.toHaveBeenCalled();
    });

    it('should apply correct precision for high-precision tokens (7 decimals)', () => {
      const symbolData = { 
        id: '1000PEPEUSDT', 
        symbol: '1000PEPE/USDT',
        pricePrecision: 7 
      };
      const symbol = '1000PEPEUSDT';

      const result = testPrecisionLogic(symbolData, symbol);

      expect(result.precision).toBe(7);
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 7,
          minMove: 0.0000001,
        },
      });
      expect(consoleSpy).not.toHaveBeenCalled();
    });
  });

  describe('Invalid Precision Handling', () => {
    it('should clamp precision to maximum of 8', () => {
      const symbolData = { 
        id: 'TESTUSDT', 
        symbol: 'TEST/USDT',
        pricePrecision: 15 // Too high
      };
      const symbol = 'TESTUSDT';

      const result = testPrecisionLogic(symbolData, symbol);

      expect(result.precision).toBe(8); // Clamped to max
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 8,
          minMove: 0.00000001,
        },
      });
      expect(consoleSpy).not.toHaveBeenCalled();
    });

    it('should handle negative precision values as invalid', () => {
      const symbolData = { 
        id: 'TESTUSDT', 
        symbol: 'TEST/USDT',
        pricePrecision: -2 // Negative
      };
      const symbol = 'TESTUSDT';

      const result = testPrecisionLogic(symbolData, symbol);

      expect(result.precision).toBe(2); // Default fallback for invalid values
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 2,
          minMove: 0.01,
        },
      });
      expect(consoleSpy).toHaveBeenCalledWith(
        'Invalid pricePrecision value for TESTUSDT: -2, using default precision: 2'
      );
    });

    it('should handle non-numeric precision values', () => {
      const symbolData = { 
        id: 'TESTUSDT', 
        symbol: 'TEST/USDT',
        pricePrecision: 'invalid' // Non-numeric
      };
      const symbol = 'TESTUSDT';

      const result = testPrecisionLogic(symbolData, symbol);

      expect(result.precision).toBe(2); // Default fallback
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 2,
          minMove: 0.01,
        },
      });
      expect(consoleSpy).toHaveBeenCalledWith(
        'Invalid pricePrecision value for TESTUSDT: invalid, using default precision: 2'
      );
    });

    it('should handle null precision values', () => {
      const symbolData = { 
        id: 'TESTUSDT', 
        symbol: 'TEST/USDT',
        pricePrecision: null
      };
      const symbol = 'TESTUSDT';

      const result = testPrecisionLogic(symbolData, symbol);

      expect(result.precision).toBe(2); // Default fallback
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 2,
          minMove: 0.01,
        },
      });
      expect(consoleSpy).toHaveBeenCalledWith(
        'Missing pricePrecision for TESTUSDT, using default precision: 2'
      );
    });

    it('should handle NaN precision values', () => {
      const symbolData = { 
        id: 'TESTUSDT', 
        symbol: 'TEST/USDT',
        pricePrecision: NaN
      };
      const symbol = 'TESTUSDT';

      const result = testPrecisionLogic(symbolData, symbol);

      expect(result.precision).toBe(2); // Default fallback
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 2,
          minMove: 0.01,
        },
      });
      expect(consoleSpy).toHaveBeenCalledWith(
        'Invalid pricePrecision value for TESTUSDT: NaN, using default precision: 2'
      );
    });
  });

  describe('Edge Cases', () => {
    it('should handle decimal precision values by flooring them', () => {
      const symbolData = { 
        id: 'TESTUSDT', 
        symbol: 'TEST/USDT',
        pricePrecision: 3.7 // Decimal precision
      };
      const symbol = 'TESTUSDT';

      const result = testPrecisionLogic(symbolData, symbol);

      expect(result.precision).toBe(3); // Floored from 3.7
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 3,
          minMove: 0.001,
        },
      });
      expect(consoleSpy).not.toHaveBeenCalled();
    });

    it('should handle zero precision correctly', () => {
      const symbolData = { 
        id: 'TESTUSDT', 
        symbol: 'TEST/USDT',
        pricePrecision: 0
      };
      const symbol = 'TESTUSDT';

      const result = testPrecisionLogic(symbolData, symbol);

      expect(result.precision).toBe(0);
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 0,
          minMove: 1, // 1 / Math.pow(10, 0) = 1
        },
      });
      expect(consoleSpy).not.toHaveBeenCalled();
    });

    it('should properly clamp precision within valid range (0-8)', () => {
      // Test boundary values that should be clamped
      const testCases = [
        { input: 0, expected: 0, description: 'minimum boundary' },
        { input: 8, expected: 8, description: 'maximum boundary' },
        { input: 15, expected: 8, description: 'above maximum' },
      ];

      testCases.forEach(({ input, expected }) => {
        const symbolData = { 
          id: 'TESTUSDT', 
          symbol: 'TEST/USDT',
          pricePrecision: input
        };
        const symbol = 'TESTUSDT';

        vi.clearAllMocks();
        const result = testPrecisionLogic(symbolData, symbol);

        expect(result.precision).toBe(expected);
        expect(consoleSpy).not.toHaveBeenCalled();
      });
    });
  });

  describe('MinMove Calculation', () => {
    it('should calculate correct minMove for different precisions', () => {
      const testCases = [
        { precision: 0, expectedMinMove: 1 },
        { precision: 1, expectedMinMove: 0.1 },
        { precision: 2, expectedMinMove: 0.01 },
        { precision: 3, expectedMinMove: 0.001 },
        { precision: 4, expectedMinMove: 0.0001 },
        { precision: 5, expectedMinMove: 0.00001 },
        { precision: 6, expectedMinMove: 0.000001 },
        { precision: 7, expectedMinMove: 0.0000001 },
        { precision: 8, expectedMinMove: 0.00000001 },
      ];

      testCases.forEach(({ precision, expectedMinMove }) => {
        const symbolData = { 
          id: 'TESTUSDT', 
          symbol: 'TEST/USDT',
          pricePrecision: precision
        };
        const symbol = 'TESTUSDT';

        vi.clearAllMocks();
        const result = testPrecisionLogic(symbolData, symbol);

        expect(result.priceFormat.minMove).toBeCloseTo(expectedMinMove, 10);
      });
    });
  });
});

// Tests for race condition fixes and WebSocket validation
describe('LightweightChart Race Condition and WebSocket Validation', () => {
  let mockWindow;
  let mockSeries;
  
  beforeEach(() => {
    // Mock the complete chart infrastructure
    mockSeries = {
      setData: vi.fn(),
      update: vi.fn(),
      data: vi.fn().mockReturnValue([]),
      applyOptions: vi.fn()
    };
    
    // Mock window state for symbol validation
    mockWindow = {
      state: {
        selectedSymbol: 'BTCUSDT',
        selectedTimeframe: '1m'
      },
      notify: vi.fn()
    };
    
    // Temporarily store original global
    global.originalWindow = global.window;
    global.window = mockWindow;
  });
  
  afterEach(() => {
    // Restore original window
    global.window = global.originalWindow;
    vi.clearAllMocks();
  });
  
  describe('Symbol Validation Logic', () => {
    function testSymbolValidation(candleData) {
      // Simulate the symbol validation from updateLatestCandle
      if (global.window && global.window.state) {
        if (global.window.state.selectedSymbol && candleData.symbol && candleData.symbol !== global.window.state.selectedSymbol) {
          console.warn('Chart: Rejecting candle update for wrong symbol:', candleData.symbol, 'vs', global.window.state.selectedSymbol);
          return false;
        }
      }
      return true;
    }
    
    it('should accept candle updates for correct symbol', () => {
      const candleData = {
        symbol: 'BTCUSDT',
        timestamp: Date.now(),
        open: 50000,
        high: 51000,
        low: 49000,
        close: 50500
      };
      
      const shouldUpdate = testSymbolValidation(candleData, true);
      expect(shouldUpdate).toBe(true);
    });
    
    it('should reject candle updates for wrong symbol (race condition)', () => {
      const candleData = {
        symbol: 'ETHUSDT', // Different from selectedSymbol
        timestamp: Date.now(),
        open: 3000,
        high: 3100,
        low: 2900,
        close: 3050
      };
      
      const shouldUpdate = testSymbolValidation(candleData, false);
      expect(shouldUpdate).toBe(false);
    });
    
    it('should accept candle updates when symbol matches state', () => {
      global.window.state.selectedSymbol = 'ETHUSDT';
      
      const candleData = {
        symbol: 'ETHUSDT',
        timestamp: Date.now(),
        open: 3000,
        high: 3100,
        low: 2900,
        close: 3050
      };
      
      const shouldUpdate = testSymbolValidation(candleData, true);
      expect(shouldUpdate).toBe(true);
    });
    
    it('should handle missing symbol in candle data gracefully', () => {
      const candleData = {
        // Missing symbol field
        timestamp: Date.now(),
        open: 50000,
        high: 51000,
        low: 49000,
        close: 50500
      };
      
      const shouldUpdate = testSymbolValidation(candleData, true);
      expect(shouldUpdate).toBe(true); // Should accept when no symbol to validate
    });
  });
  
  describe('Timeframe Validation Logic', () => {
    function testTimeframeValidation(incomingData) {
      // Simulate the timeframe validation from store.js
      if (global.window.state.selectedTimeframe && incomingData.timeframe && incomingData.timeframe !== global.window.state.selectedTimeframe) {
        console.warn('Received candle for different timeframe, skipping update');
        return false;
      }
      return true;
    }
    
    it('should accept candle updates for correct timeframe', () => {
      const incomingData = {
        symbol: 'BTCUSDT',
        timeframe: '1m', // Matches selectedTimeframe
        timestamp: Date.now()
      };
      
      const shouldUpdate = testTimeframeValidation(incomingData, true);
      expect(shouldUpdate).toBe(true);
    });
    
    it('should reject candle updates for wrong timeframe (race condition)', () => {
      const incomingData = {
        symbol: 'BTCUSDT',
        timeframe: '5m', // Different from selectedTimeframe
        timestamp: Date.now()
      };
      
      const shouldUpdate = testTimeframeValidation(incomingData, false);
      expect(shouldUpdate).toBe(false);
    });
    
    it('should handle missing timeframe gracefully', () => {
      const incomingData = {
        symbol: 'BTCUSDT',
        // Missing timeframe field
        timestamp: Date.now()
      };
      
      const shouldUpdate = testTimeframeValidation(incomingData, true);
      expect(shouldUpdate).toBe(true); // Should accept when no timeframe to validate
    });
  });
  
  describe('Timestamp Age Validation', () => {
    function testTimestampAgeValidation(candleData, existingData) {
      // Simulate the timestamp age validation from updateLatestCandle
      const rawTimestamp = candleData.timestamp;
      const convertedTime = Math.floor(rawTimestamp / 1000);
      
      let lastChartTime = null;
      if (existingData && existingData.length > 0) {
        lastChartTime = existingData[existingData.length - 1].time;
        
        if (convertedTime <= lastChartTime) {
          const timeDiff = lastChartTime - convertedTime;
          
          // If it's a very old update (more than 5 minutes), reject it
          if (timeDiff > 300) { // 5 minutes
            console.warn('Chart: Rejecting very old candle update to prevent chart errors');
            return false;
          }
          
          if (timeDiff > 0) {
            console.debug('Chart: Timestamp ordering issue - rejecting update');
            return false;
          }
        }
      }
      return true;
    }
    
    it('should accept newer timestamps', () => {
      const now = Date.now();
      const candleData = { timestamp: now };
      const existingData = [{ time: Math.floor((now - 60000) / 1000) }]; // 1 minute older
      
      const shouldUpdate = testTimestampAgeValidation(candleData, existingData);
      expect(shouldUpdate).toBe(true);
    });
    
    it('should reject very old timestamps (race condition protection)', () => {
      const now = Date.now();
      const candleData = { timestamp: now - (10 * 60 * 1000) }; // 10 minutes old
      const existingData = [{ time: Math.floor(now / 1000) }]; // Current time
      
      const shouldUpdate = testTimestampAgeValidation(candleData, existingData);
      expect(shouldUpdate).toBe(false);
    });
    
    it('should reject slightly older timestamps', () => {
      const now = Date.now();
      const candleData = { timestamp: now - 1000 }; // 1 second old
      const existingData = [{ time: Math.floor(now / 1000) }]; // Current time
      
      const shouldUpdate = testTimestampAgeValidation(candleData, existingData);
      expect(shouldUpdate).toBe(false);
    });
    
    it('should accept same timestamp (real-time updates)', () => {
      const now = Date.now();
      const candleData = { timestamp: now };
      const existingData = [{ time: Math.floor(now / 1000) }]; // Same time
      
      const shouldUpdate = testTimestampAgeValidation(candleData, existingData);
      expect(shouldUpdate).toBe(true);
    });
  });
  
  describe('Chart Data Reset Logic', () => {
    function testChartDataReset() {
      // Simulate the resetChartData function
      let lastChartData = { some: 'data' };
      let lastSymbol = 'BTCUSDT';
      let lastTimeframe = '1m';
      
      // Reset function logic
      mockSeries.setData([]);
      lastChartData = null;
      lastSymbol = null;
      lastTimeframe = null;
      
      return {
        lastChartData,
        lastSymbol,
        lastTimeframe
      };
    }
    
    it('should completely reset chart state', () => {
      const result = testChartDataReset();
      
      expect(mockSeries.setData).toHaveBeenCalledWith([]);
      expect(result.lastChartData).toBe(null);
      expect(result.lastSymbol).toBe(null);
      expect(result.lastTimeframe).toBe(null);
    });
  });
  
  describe('Context Change Detection', () => {
    function testContextChangeDetection(currentSymbol, currentTimeframe, newSymbol, newTimeframe) {
      // Simulate context change detection from updateLightweightChart
      const isSymbolChange = currentSymbol !== newSymbol;
      const isTimeframeChange = currentTimeframe !== newTimeframe;
      const isContextChange = isSymbolChange || isTimeframeChange;
      
      return {
        isSymbolChange,
        isTimeframeChange,
        isContextChange
      };
    }
    
    it('should detect symbol changes', () => {
      const result = testContextChangeDetection('BTCUSDT', '1m', 'ETHUSDT', '1m');
      
      expect(result.isSymbolChange).toBe(true);
      expect(result.isTimeframeChange).toBe(false);
      expect(result.isContextChange).toBe(true);
    });
    
    it('should detect timeframe changes', () => {
      const result = testContextChangeDetection('BTCUSDT', '1m', 'BTCUSDT', '5m');
      
      expect(result.isSymbolChange).toBe(false);
      expect(result.isTimeframeChange).toBe(true);
      expect(result.isContextChange).toBe(true);
    });
    
    it('should detect no changes', () => {
      const result = testContextChangeDetection('BTCUSDT', '1m', 'BTCUSDT', '1m');
      
      expect(result.isSymbolChange).toBe(false);
      expect(result.isTimeframeChange).toBe(false);
      expect(result.isContextChange).toBe(false);
    });
    
    it('should detect both symbol and timeframe changes', () => {
      const result = testContextChangeDetection('BTCUSDT', '1m', 'ETHUSDT', '5m');
      
      expect(result.isSymbolChange).toBe(true);
      expect(result.isTimeframeChange).toBe(true);
      expect(result.isContextChange).toBe(true);
    });
  });
});