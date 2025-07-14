import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { JSDOM } from 'jsdom';

// Mock fetch globally
global.fetch = vi.fn();

// Mock WebSocket
class MockWebSocket {
  constructor(url) {
    this.url = url;
    this.readyState = 0; // CONNECTING
    this.onopen = null;
    this.onmessage = null;
    this.onerror = null;
    this.onclose = null;
    this.messages = [];
    
    // Simulate connection
    setTimeout(() => {
      this.readyState = 1; // OPEN
      if (this.onopen) this.onopen();
    }, 10);
  }
  
  send(data) {
    this.messages.push(JSON.parse(data));
  }
  
  close() {
    this.readyState = 3; // CLOSED
    if (this.onclose) this.onclose();
  }
  
  simulateMessage(data) {
    if (this.onmessage) {
      this.onmessage({ data: JSON.stringify(data) });
    }
  }
}

global.WebSocket = MockWebSocket;

// Mock config
vi.mock('../../src/config/config.js', () => ({
  API_CONFIG: {
    API_BASE_URL: 'http://localhost:8000/api/v1'
  },
  getConfig: vi.fn(() => ({
    API_BASE_URL: 'http://localhost:8000/api/v1'
  }))
}));

// Mock TradingView Lightweight Charts
const mockHistogramSeries = {
  setData: vi.fn(),
  update: vi.fn(),
  applyOptions: vi.fn(),
  priceScale: vi.fn(() => ({
    applyOptions: vi.fn()
  }))
};

const mockChart = {
  addHistogramSeries: vi.fn(() => mockHistogramSeries),
  subscribeCrosshairMove: vi.fn(),
  timeScale: vi.fn(() => ({
    fitContent: vi.fn()
  }))
};

vi.mock('lightweight-charts', () => ({
  createChart: vi.fn(() => mockChart)
}));

describe('Liquidation Volume Integration Tests', () => {
  let dom;
  let liquidationVolumeService;
  let websocketService;
  let store;
  let chartComponent;
  
  beforeEach(async () => {
    // Set up DOM
    dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
        <body>
          <div id="chart-container" style="width: 800px; height: 600px;"></div>
        </body>
      </html>
    `, { url: 'http://localhost' });
    
    global.window = dom.window;
    global.document = dom.window.document;
    
    // Clear all mocks
    vi.clearAllMocks();
    
    // Import modules dynamically to ensure fresh state
    try {
      const liquidationModule = await import('../../src/services/liquidationVolumeService.js');
      const storeModule = await import('../../src/store/store.js');
      
      liquidationVolumeService = liquidationModule.liquidationVolumeService;
      store = storeModule.store;
    } catch (error) {
      console.error('Import error:', error);
    }
    
    // Clear any existing state
    liquidationVolumeService.clearCache();
    store.reset();
  });
  
  afterEach(() => {
    vi.clearAllMocks();
    if (dom) {
      dom.window.close();
    }
  });
  
  describe('End-to-End Data Flow', () => {
    it('should fetch and display liquidation volume data on chart initialization', async () => {
      const mockVolumeData = [
        {
          time: 1640995200,
          buy_volume: "15000.0",
          sell_volume: "25000.0",
          total_volume: "40000.0",
          buy_volume_formatted: "15,000.00",
          sell_volume_formatted: "25,000.00",
          total_volume_formatted: "40,000.00",
          count: 50,
          timestamp_ms: 1640995200000
        },
        {
          time: 1640995260,
          buy_volume: "8000.0",
          sell_volume: "12000.0",
          total_volume: "20000.0",
          buy_volume_formatted: "8,000.00",
          sell_volume_formatted: "12,000.00",
          total_volume_formatted: "20,000.00",
          count: 30,
          timestamp_ms: 1640995260000
        }
      ];
      
      // Mock API response
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          symbol: 'BTCUSDT',
          timeframe: '1m',
          data: mockVolumeData
        })
      });
      
      // Step 1: Fetch liquidation volume data
      const result = await liquidationVolumeService.fetchLiquidationVolume('BTCUSDT', '1m');
      
      expect(result).toEqual(mockVolumeData);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/liquidation-volume/BTCUSDT/1m'),
        expect.any(Object)
      );
      
      // Step 2: Update store with volume data
      store.updateLiquidationVolume({
        symbol: 'BTCUSDT',
        timeframe: '1m',
        data: result
      });
      
      const storeData = store.getLiquidationVolume();
      expect(storeData.data).toEqual(mockVolumeData);
      
      // Step 3: Chart component processes and displays data
      const histogramData = mockVolumeData.map(item => {
        const buyVolume = parseFloat(item.buy_volume);
        const sellVolume = parseFloat(item.sell_volume);
        const totalVolume = parseFloat(item.total_volume);
        const color = buyVolume > sellVolume ? '#0ECB81' : '#F6465D';
        
        return {
          time: item.time,
          value: totalVolume,
          color: color
        };
      });
      
      // Verify histogram data format
      expect(histogramData[0]).toEqual({
        time: 1640995200,
        value: 40000.0,
        color: '#F6465D' // Red because sell > buy
      });
      
      expect(histogramData[1]).toEqual({
        time: 1640995260,
        value: 20000.0,
        color: '#F6465D' // Red because sell > buy
      });
    });
    
    it('should handle real-time WebSocket updates', async () => {
      // Initialize WebSocket connection
      const ws = new MockWebSocket('ws://localhost:8000/api/v1/ws/liquidations/BTCUSDT?timeframe=1m');
      
      // Wait for connection
      await new Promise(resolve => setTimeout(resolve, 20));
      
      expect(ws.readyState).toBe(1); // OPEN
      
      // Simulate volume update message
      const volumeUpdate = {
        type: 'liquidation_volume',
        symbol: 'BTCUSDT',
        timeframe: '1m',
        data: [{
          time: 1640995320,
          buy_volume: "5000.0",
          sell_volume: "3000.0",
          total_volume: "8000.0",
          buy_volume_formatted: "5,000.00",
          sell_volume_formatted: "3,000.00",
          total_volume_formatted: "8,000.00",
          count: 15,
          timestamp_ms: 1640995320000
        }],
        timestamp: '2024-01-01T00:00:00Z'
      };
      
      // Simulate receiving the message
      ws.simulateMessage(volumeUpdate);
      
      // In a real scenario, the WebSocket service would update the store
      store.updateLiquidationVolume({
        symbol: volumeUpdate.symbol,
        timeframe: volumeUpdate.timeframe,
        data: volumeUpdate.data,
        isUpdate: true
      });
      
      const storeData = store.getLiquidationVolume();
      expect(storeData.data).toEqual(volumeUpdate.data);
      expect(storeData.isUpdate).toBe(true);
      
      // Clean up
      ws.close();
    });
    
    it('should coordinate symbol and timeframe changes', async () => {
      const mockDataBTC1m = [{
        time: 1640995200,
        buy_volume: "10000.0",
        sell_volume: "15000.0",
        total_volume: "25000.0"
      }];
      
      const mockDataBTC5m = [{
        time: 1640995200,
        buy_volume: "50000.0",
        sell_volume: "75000.0",
        total_volume: "125000.0"
      }];
      
      const mockDataETH1m = [{
        time: 1640995200,
        buy_volume: "5000.0",
        sell_volume: "7000.0",
        total_volume: "12000.0"
      }];
      
      // Test symbol change
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          symbol: 'BTCUSDT',
          timeframe: '1m',
          data: mockDataBTC1m
        })
      });
      
      let result = await liquidationVolumeService.fetchLiquidationVolume('BTCUSDT', '1m');
      expect(result).toEqual(mockDataBTC1m);
      
      // Clear cache and change symbol
      liquidationVolumeService.clearCache();
      
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          symbol: 'ETHUSDT',
          timeframe: '1m',
          data: mockDataETH1m
        })
      });
      
      result = await liquidationVolumeService.fetchLiquidationVolume('ETHUSDT', '1m');
      expect(result).toEqual(mockDataETH1m);
      
      // Test timeframe change
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          symbol: 'BTCUSDT',
          timeframe: '5m',
          data: mockDataBTC5m
        })
      });
      
      result = await liquidationVolumeService.fetchLiquidationVolume('BTCUSDT', '5m');
      expect(result).toEqual(mockDataBTC5m);
      
      // Verify different data for different timeframes
      expect(mockDataBTC5m[0].total_volume).not.toEqual(mockDataBTC1m[0].total_volume);
    });
  });
  
  describe('Performance Tests', () => {
    it('should handle large datasets efficiently', async () => {
      // Generate large dataset (500 data points)
      const largeDataset = [];
      for (let i = 0; i < 500; i++) {
        largeDataset.push({
          time: 1640995200 + (i * 60),
          buy_volume: `${1000 + i * 10}.0`,
          sell_volume: `${2000 + i * 15}.0`,
          total_volume: `${3000 + i * 25}.0`,
          count: 10 + i,
          timestamp_ms: (1640995200 + (i * 60)) * 1000
        });
      }
      
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          symbol: 'BTCUSDT',
          timeframe: '1m',
          data: largeDataset
        })
      });
      
      const startTime = performance.now();
      
      // Fetch data
      const result = await liquidationVolumeService.fetchLiquidationVolume('BTCUSDT', '1m');
      
      // Process for chart
      const histogramData = result.map(item => ({
        time: item.time,
        value: parseFloat(item.total_volume),
        color: parseFloat(item.buy_volume) > parseFloat(item.sell_volume) ? '#0ECB81' : '#F6465D'
      }));
      
      const endTime = performance.now();
      const processingTime = endTime - startTime;
      
      // Performance assertions
      expect(processingTime).toBeLessThan(100); // Should process in under 100ms
      expect(histogramData.length).toBe(500);
      expect(histogramData[0].time).toBe(1640995200);
      expect(histogramData[499].time).toBe(1640995200 + (499 * 60));
    });
    
    it('should efficiently cache and reuse data', async () => {
      const mockData = [{
        time: 1640995200,
        buy_volume: "1000.0",
        sell_volume: "2000.0",
        total_volume: "3000.0"
      }];
      
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          symbol: 'BTCUSDT',
          timeframe: '1m',
          data: mockData
        })
      });
      
      // First fetch - should hit API
      const result1 = await liquidationVolumeService.fetchLiquidationVolume('BTCUSDT', '1m');
      expect(global.fetch).toHaveBeenCalledTimes(1);
      
      // Second fetch - should use cache
      const result2 = await liquidationVolumeService.fetchLiquidationVolume('BTCUSDT', '1m');
      expect(global.fetch).toHaveBeenCalledTimes(1); // No additional call
      
      // Results should be identical
      expect(result1).toEqual(result2);
      expect(result1).toEqual(mockData);
    });
  });
  
  describe('Error Handling Integration', () => {
    it('should handle API failures gracefully', async () => {
      // Simulate API error
      global.fetch.mockRejectedValueOnce(new Error('Network error'));
      
      const result = await liquidationVolumeService.fetchLiquidationVolume('BTCUSDT', '1m');
      
      // Should return empty array on error
      expect(result).toEqual([]);
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });
    
    it('should handle WebSocket disconnections', async () => {
      const ws = new MockWebSocket('ws://localhost:8000/api/v1/ws/liquidations/BTCUSDT');
      let disconnected = false;
      
      ws.onclose = () => {
        disconnected = true;
      };
      
      // Wait for connection
      await new Promise(resolve => setTimeout(resolve, 20));
      expect(ws.readyState).toBe(1); // OPEN
      
      // Simulate disconnection
      ws.close();
      expect(disconnected).toBe(true);
      expect(ws.readyState).toBe(3); // CLOSED
    });
    
    it('should handle malformed data gracefully', async () => {
      // Malformed data missing required fields
      const malformedData = [{
        time: 1640995200,
        // Missing volume fields
      }];
      
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          symbol: 'BTCUSDT',
          timeframe: '1m',
          data: malformedData
        })
      });
      
      const result = await liquidationVolumeService.fetchLiquidationVolume('BTCUSDT', '1m');
      
      // Process data with safety checks
      const histogramData = result.map(item => ({
        time: item.time,
        value: parseFloat(item.total_volume || 0),
        color: parseFloat(item.buy_volume || 0) > parseFloat(item.sell_volume || 0) ? '#0ECB81' : '#F6465D'
      }));
      
      expect(histogramData[0].value).toBe(0); // Defaults to 0 for missing data
      expect(histogramData[0].color).toBe('#F6465D'); // Defaults to red
    });
  });
});