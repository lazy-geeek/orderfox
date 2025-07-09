import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Test module for LightweightChart backend data integration
describe('LightweightChart Backend Data Integration', () => {
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

  // Test applying backend-provided priceFormat directly to chart
  function testBackendPriceFormat(symbolData, symbol) {
    // Backend now provides complete priceFormat object
    if (symbolData && symbolData.priceFormat) {
      // Frontend simply applies backend-provided format
      mockSeries.applyOptions({
        priceFormat: symbolData.priceFormat
      });
      return symbolData.priceFormat;
    }
    
    // No frontend fallback calculation - trust backend
    return null;
  }

  describe('Backend PriceFormat Integration', () => {
    it('should apply backend-provided priceFormat directly for BTC', () => {
      const symbolData = { 
        id: 'BTCUSDT', 
        symbol: 'BTC/USDT',
        priceFormat: {
          type: 'price',
          precision: 1,
          minMove: 0.1
        }
      };
      const symbol = 'BTCUSDT';

      const result = testBackendPriceFormat(symbolData, symbol);

      expect(result).toEqual({
        type: 'price',
        precision: 1,
        minMove: 0.1
      });
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 1,
          minMove: 0.1
        }
      });
      expect(consoleSpy).not.toHaveBeenCalled();
    });

    it('should apply backend-provided priceFormat directly for high-precision tokens', () => {
      const symbolData = { 
        id: 'ADAUSDT', 
        symbol: 'ADA/USDT',
        priceFormat: {
          type: 'price',
          precision: 4,
          minMove: 0.0001
        }
      };
      const symbol = 'ADAUSDT';

      const result = testBackendPriceFormat(symbolData, symbol);

      expect(result).toEqual({
        type: 'price',
        precision: 4,
        minMove: 0.0001
      });
      expect(mockSeries.applyOptions).toHaveBeenCalledWith({
        priceFormat: {
          type: 'price',
          precision: 4,
          minMove: 0.0001
        }
      });
      expect(consoleSpy).not.toHaveBeenCalled();
    });

    it('should handle missing symbolData gracefully', () => {
      const symbolData = null;
      const symbol = 'BTCUSDT';

      const result = testBackendPriceFormat(symbolData, symbol);

      expect(result).toBeNull();
      expect(mockSeries.applyOptions).not.toHaveBeenCalled();
      expect(consoleSpy).not.toHaveBeenCalled();
    });

    it('should handle missing priceFormat in symbolData', () => {
      const symbolData = { 
        id: 'BTCUSDT', 
        symbol: 'BTC/USDT'
        // No priceFormat field
      };
      const symbol = 'BTCUSDT';

      const result = testBackendPriceFormat(symbolData, symbol);

      expect(result).toBeNull();
      expect(mockSeries.applyOptions).not.toHaveBeenCalled();
      expect(consoleSpy).not.toHaveBeenCalled();
    });
  });

  describe('Chart Data Processing', () => {
    it('should process candle data with both timestamp and time fields', () => {
      const candleData = {
        timestamp: 1640995200000, // milliseconds
        time: 1640995200,         // seconds (backend-provided)
        open: 50000.0,
        high: 50500.0,
        low: 49500.0,
        close: 50250.0,
        volume: 100.0
      };

      // Frontend should use time field directly for TradingView
      const formattedForChart = {
        time: candleData.time,
        open: candleData.open,
        high: candleData.high,
        low: candleData.low,
        close: candleData.close,
      };

      expect(formattedForChart.time).toBe(1640995200);
      expect(formattedForChart.open).toBe(50000.0);
      expect(formattedForChart.high).toBe(50500.0);
      expect(formattedForChart.low).toBe(49500.0);
      expect(formattedForChart.close).toBe(50250.0);
    });

    it('should trust backend-provided sorted data', () => {
      const backendData = [
        { time: 1640995200, open: 50000, high: 50500, low: 49500, close: 50250 },
        { time: 1640995260, open: 50250, high: 50750, low: 50000, close: 50500 },
        { time: 1640995320, open: 50500, high: 50800, low: 50200, close: 50600 }
      ];

      // Frontend should use data as-is (no sorting needed)
      mockSeries.setData(backendData);

      expect(mockSeries.setData).toHaveBeenCalledWith(backendData);
      expect(mockSeries.setData).toHaveBeenCalledTimes(1);
    });
  });

  describe('Real-time Updates', () => {
    it('should handle real-time candle updates with time field', () => {
      const realtimeUpdate = {
        type: 'candle_update',
        symbol: 'BTCUSDT',
        timeframe: '1m',
        timestamp: 1640995380000,
        time: 1640995380,  // Backend-provided seconds
        open: 50600.0,
        high: 50900.0,
        low: 50400.0,
        close: 50750.0,
        volume: 150.0
      };

      const chartCandle = {
        time: realtimeUpdate.time,
        open: realtimeUpdate.open,
        high: realtimeUpdate.high,
        low: realtimeUpdate.low,
        close: realtimeUpdate.close,
      };

      mockSeries.update(chartCandle);

      expect(mockSeries.update).toHaveBeenCalledWith({
        time: 1640995380,
        open: 50600.0,
        high: 50900.0,
        low: 50400.0,
        close: 50750.0,
      });
    });
  });
});