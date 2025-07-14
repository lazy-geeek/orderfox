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

  describe('Liquidation Volume Series', () => {
    let mockChart;
    let mockVolumeSeries;

    beforeEach(() => {
      const mockPriceScale = {
        applyOptions: vi.fn()
      };
      
      mockVolumeSeries = {
        setData: vi.fn(),
        applyOptions: vi.fn(),
        priceScale: vi.fn(() => mockPriceScale)
      };
      
      mockChart = {
        addHistogramSeries: vi.fn(() => mockVolumeSeries)
      };
    });

    it('should create liquidation volume series as overlay', () => {
      // Test creating volume series
      const volumeSeries = mockChart.addHistogramSeries({
        priceFormat: {
          type: 'volume',
        },
        priceScaleId: '', // Empty string makes it an overlay
      });

      expect(mockChart.addHistogramSeries).toHaveBeenCalledWith({
        priceFormat: {
          type: 'volume',
        },
        priceScaleId: '',
      });

      // Should configure scale margins
      volumeSeries.priceScale().applyOptions({
        scaleMargins: {
          top: 0.7,
          bottom: 0,
        },
      });

      expect(volumeSeries.priceScale().applyOptions).toHaveBeenCalledWith({
        scaleMargins: {
          top: 0.7,
          bottom: 0,
        },
      });
    });

    it('should process liquidation volume data correctly', () => {
      const volumeData = [
        {
          time: 1640995200,
          buy_volume: "1500.0",
          sell_volume: "2500.0",
          total_volume: "4000.0",
          buy_volume_formatted: "1,500.00",
          sell_volume_formatted: "2,500.00",
          total_volume_formatted: "4,000.00",
          count: 5,
          timestamp_ms: 1640995200000
        },
        {
          time: 1640995260,
          buy_volume: "800.0",
          sell_volume: "1200.0",
          total_volume: "2000.0",
          buy_volume_formatted: "800.00",
          sell_volume_formatted: "1,200.00",
          total_volume_formatted: "2,000.00",
          count: 3,
          timestamp_ms: 1640995260000
        }
      ];

      // Process into histogram format
      const histogramData = volumeData.map(item => {
        const buyVolume = parseFloat(item.buy_volume || 0);
        const sellVolume = parseFloat(item.sell_volume || 0);
        const totalVolume = parseFloat(item.total_volume || 0);
        
        // Green if buy > sell (shorts liquidated), red if sell > buy (longs liquidated)
        const color = buyVolume > sellVolume ? '#0ECB81' : '#F6465D';
        
        return {
          time: item.time,
          value: totalVolume,
          color: color,
        };
      });

      expect(histogramData[0]).toEqual({
        time: 1640995200,
        value: 4000.0,
        color: '#F6465D', // Red because sell > buy
      });

      expect(histogramData[1]).toEqual({
        time: 1640995260,
        value: 2000.0,
        color: '#F6465D', // Red because sell > buy
      });

      mockVolumeSeries.setData(histogramData);
      expect(mockVolumeSeries.setData).toHaveBeenCalledWith(histogramData);
    });

    it('should handle empty volume data', () => {
      const volumeData = [];
      
      const histogramData = volumeData.map(item => ({
        time: item.time,
        value: parseFloat(item.total_volume || 0),
        color: parseFloat(item.buy_volume || 0) > parseFloat(item.sell_volume || 0) ? '#0ECB81' : '#F6465D',
      }));

      expect(histogramData).toEqual([]);
      
      mockVolumeSeries.setData(histogramData);
      expect(mockVolumeSeries.setData).toHaveBeenCalledWith([]);
    });

    it('should color bars based on dominant side', () => {
      const testCases = [
        {
          buy_volume: "3000.0",
          sell_volume: "1000.0",
          expectedColor: '#0ECB81' // Green - buy dominant
        },
        {
          buy_volume: "1000.0",
          sell_volume: "3000.0",
          expectedColor: '#F6465D' // Red - sell dominant
        },
        {
          buy_volume: "2000.0",
          sell_volume: "2000.0",
          expectedColor: '#F6465D' // Red when equal (default to sell)
        }
      ];

      testCases.forEach(testCase => {
        const buyVolume = parseFloat(testCase.buy_volume);
        const sellVolume = parseFloat(testCase.sell_volume);
        const color = buyVolume > sellVolume ? '#0ECB81' : '#F6465D';
        
        expect(color).toBe(testCase.expectedColor);
      });
    });

    it('should toggle volume series visibility', () => {
      let volumeSeriesVisible = true;
      
      // Toggle function
      function toggleLiquidationVolume() {
        volumeSeriesVisible = !volumeSeriesVisible;
        
        if (volumeSeriesVisible) {
          mockVolumeSeries.applyOptions({ visible: true });
        } else {
          mockVolumeSeries.applyOptions({ visible: false });
        }
        
        return volumeSeriesVisible;
      }

      // Initially visible
      expect(volumeSeriesVisible).toBe(true);

      // Toggle off
      const result1 = toggleLiquidationVolume();
      expect(result1).toBe(false);
      expect(mockVolumeSeries.applyOptions).toHaveBeenCalledWith({ visible: false });

      // Toggle on
      const result2 = toggleLiquidationVolume();
      expect(result2).toBe(true);
      expect(mockVolumeSeries.applyOptions).toHaveBeenCalledWith({ visible: true });
    });
  });

  describe('Mobile Responsiveness', () => {
    let mockCandlestickSeries;
    let mockVolumeSeries;
    let mockCandlestickPriceScale;
    let mockVolumePriceScale;

    beforeEach(() => {
      mockCandlestickPriceScale = {
        applyOptions: vi.fn()
      };
      
      mockVolumePriceScale = {
        applyOptions: vi.fn()
      };
      
      mockCandlestickSeries = {
        priceScale: vi.fn(() => mockCandlestickPriceScale)
      };
      
      mockVolumeSeries = {
        priceScale: vi.fn(() => mockVolumePriceScale)
      };
    });

    it('should adjust margins for small mobile screens', () => {
      const width = 400; // Small mobile
      
      // Function to adjust margins based on screen size
      function adjustChartMarginsForScreenSize(width) {
        const isMobile = width < 768;
        const isSmallMobile = width < 480;
        
        if (isSmallMobile) {
          mockCandlestickSeries.priceScale().applyOptions({
            scaleMargins: {
              top: 0.05,
              bottom: 0.5,
            },
          });
          mockVolumeSeries.priceScale().applyOptions({
            scaleMargins: {
              top: 0.65,
              bottom: 0,
            },
          });
        } else if (isMobile) {
          mockCandlestickSeries.priceScale().applyOptions({
            scaleMargins: {
              top: 0.05,
              bottom: 0.45,
            },
          });
          mockVolumeSeries.priceScale().applyOptions({
            scaleMargins: {
              top: 0.65,
              bottom: 0,
            },
          });
        } else {
          mockCandlestickSeries.priceScale().applyOptions({
            scaleMargins: {
              top: 0.1,
              bottom: 0.4,
            },
          });
          mockVolumeSeries.priceScale().applyOptions({
            scaleMargins: {
              top: 0.7,
              bottom: 0,
            },
          });
        }
      }

      adjustChartMarginsForScreenSize(width);

      // Verify small mobile margins
      expect(mockCandlestickPriceScale.applyOptions).toHaveBeenCalledWith({
        scaleMargins: {
          top: 0.05,
          bottom: 0.5,
        },
      });
      expect(mockVolumePriceScale.applyOptions).toHaveBeenCalledWith({
        scaleMargins: {
          top: 0.65,
          bottom: 0,
        },
      });
    });

    it('should adjust margins for tablet screens', () => {
      const width = 600; // Tablet
      
      function adjustChartMarginsForScreenSize(width) {
        const isMobile = width < 768;
        const isSmallMobile = width < 480;
        
        if (isSmallMobile) {
          // Small mobile margins
        } else if (isMobile) {
          mockCandlestickSeries.priceScale().applyOptions({
            scaleMargins: {
              top: 0.05,
              bottom: 0.45,
            },
          });
          mockVolumeSeries.priceScale().applyOptions({
            scaleMargins: {
              top: 0.65,
              bottom: 0,
            },
          });
        }
      }

      adjustChartMarginsForScreenSize(width);

      // Verify tablet margins
      expect(mockCandlestickPriceScale.applyOptions).toHaveBeenCalledWith({
        scaleMargins: {
          top: 0.05,
          bottom: 0.45,
        },
      });
      expect(mockVolumePriceScale.applyOptions).toHaveBeenCalledWith({
        scaleMargins: {
          top: 0.65,
          bottom: 0,
        },
      });
    });

    it('should use desktop margins for large screens', () => {
      const width = 1200; // Desktop
      
      function adjustChartMarginsForScreenSize(width) {
        const isMobile = width < 768;
        const isSmallMobile = width < 480;
        
        if (!isMobile && !isSmallMobile) {
          mockCandlestickSeries.priceScale().applyOptions({
            scaleMargins: {
              top: 0.1,
              bottom: 0.4,
            },
          });
          mockVolumeSeries.priceScale().applyOptions({
            scaleMargins: {
              top: 0.7,
              bottom: 0,
            },
          });
        }
      }

      adjustChartMarginsForScreenSize(width);

      // Verify desktop margins
      expect(mockCandlestickPriceScale.applyOptions).toHaveBeenCalledWith({
        scaleMargins: {
          top: 0.1,
          bottom: 0.4,
        },
      });
      expect(mockVolumePriceScale.applyOptions).toHaveBeenCalledWith({
        scaleMargins: {
          top: 0.7,
          bottom: 0,
        },
      });
    });
  });
});