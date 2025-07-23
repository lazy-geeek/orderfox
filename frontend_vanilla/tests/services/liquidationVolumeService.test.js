import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock fetch globally
global.fetch = vi.fn();

// Mock config
vi.mock('../../src/config/env.js', () => ({
  API_BASE_URL: 'http://localhost:8000/api/v1'
}));

describe('LiquidationVolumeService', () => {
  let liquidationVolumeService;
  
  beforeEach(async () => {
    // Clear cache and mocks
    vi.clearAllMocks();
    global.fetch.mockClear();
    
    // Dynamically import to ensure fresh instance
    const module = await import('../../src/services/liquidationVolumeService.js');
    liquidationVolumeService = module.default;
    
    // Clear any existing cache
    liquidationVolumeService.clearCache();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchLiquidationVolume', () => {
    it('should fetch liquidation volume data successfully', async () => {
      const mockResponse = {
        symbol: 'BTCUSDT',
        timeframe: '1m',
        data: [
          {
            time: 1640995200,
            buy_volume: '1500.0',
            sell_volume: '2500.0',
            total_volume: '4000.0',
            buy_volume_formatted: '1,500.00',
            sell_volume_formatted: '2,500.00',
            total_volume_formatted: '4,000.00',
            count: 5,
            timestamp_ms: 1640995200000
          }
        ],
        start_time: 1640991600000,
        end_time: 1640995200000
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      });

      const result = await liquidationVolumeService.fetchLiquidationVolume('BTCUSDT', '1m');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/liquidation-volume/BTCUSDT/1m'
      );
      expect(result).toEqual(mockResponse.data);
    });

    it('should use time range parameters when provided', async () => {
      const mockResponse = {
        symbol: 'ETHUSDT',
        timeframe: '5m',
        data: [],
        start_time: 1640991600000,
        end_time: 1640995200000
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      });

      await liquidationVolumeService.fetchLiquidationVolume(
        'ETHUSDT', 
        '5m',
        1640991600000,
        1640995200000
      );

      const fetchCall = global.fetch.mock.calls[0];
      const url = new URL(fetchCall[0]);
      
      expect(url.searchParams.get('start_time')).toBe('1640991600000');
      expect(url.searchParams.get('end_time')).toBe('1640995200000');
    });

    it('should return cached data if available', async () => {
      const mockResponse = {
        symbol: 'BTCUSDT',
        timeframe: '1h',
        data: [
          {
            time: 1640995200,
            buy_volume: '5000.0',
            sell_volume: '3000.0',
            total_volume: '8000.0'
          }
        ]
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      });

      // First call - should fetch from API
      const result1 = await liquidationVolumeService.fetchLiquidationVolume('BTCUSDT', '1h');
      expect(global.fetch).toHaveBeenCalledTimes(1);
      expect(result1).toEqual(mockResponse.data);

      // Second call - should use cache
      const result2 = await liquidationVolumeService.fetchLiquidationVolume('BTCUSDT', '1h');
      expect(global.fetch).toHaveBeenCalledTimes(1); // No additional fetch
      expect(result2).toEqual(mockResponse.data);
    });

    it('should handle API errors gracefully', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error'
      });

      const result = await liquidationVolumeService.fetchLiquidationVolume('BTCUSDT', '1m');
      
      expect(result).toEqual([]);
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    it('should handle network errors', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      const result = await liquidationVolumeService.fetchLiquidationVolume('BTCUSDT', '1m');
      
      expect(result).toEqual([]);
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    it('should validate timeframe parameter', async () => {
      const validTimeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d'];
      
      for (const timeframe of validTimeframes) {
        global.fetch.mockResolvedValueOnce({
          ok: true,
          json: async () => ({ data: [] })
        });
        
        const result = await liquidationVolumeService.fetchLiquidationVolume('BTCUSDT', timeframe);
        expect(result).toBeDefined();
      }
      
      // Invalid timeframe should still make request (validated on backend)
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 400
      });
      
      const result = await liquidationVolumeService.fetchLiquidationVolume('BTCUSDT', 'invalid');
      expect(result).toEqual([]);
    });
  });

  describe('cache management', () => {
    it('should clear cache on clearCache()', async () => {
      const mockResponse = {
        symbol: 'BTCUSDT',
        timeframe: '1m',
        data: [{ time: 1640995200, total_volume: '1000.0' }]
      };

      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => mockResponse
      });

      // First call - populate cache
      await liquidationVolumeService.fetchLiquidationVolume('BTCUSDT', '1m');
      expect(global.fetch).toHaveBeenCalledTimes(1);

      // Clear cache
      liquidationVolumeService.clearCache();

      // Next call should fetch again
      await liquidationVolumeService.fetchLiquidationVolume('BTCUSDT', '1m');
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    it('should cache data separately for different symbols and timeframes', async () => {
      const mockResponses = {
        BTCUSDT_1m: { data: [{ time: 1, total_volume: '100' }] },
        BTCUSDT_5m: { data: [{ time: 2, total_volume: '200' }] },
        ETHUSDT_1m: { data: [{ time: 3, total_volume: '300' }] }
      };

      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ ...mockResponses.BTCUSDT_1m, symbol: 'BTCUSDT', timeframe: '1m' })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ ...mockResponses.BTCUSDT_5m, symbol: 'BTCUSDT', timeframe: '5m' })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ ...mockResponses.ETHUSDT_1m, symbol: 'ETHUSDT', timeframe: '1m' })
        });

      // Fetch different combinations
      const result1 = await liquidationVolumeService.fetchLiquidationVolume('BTCUSDT', '1m');
      const result2 = await liquidationVolumeService.fetchLiquidationVolume('BTCUSDT', '5m');
      const result3 = await liquidationVolumeService.fetchLiquidationVolume('ETHUSDT', '1m');

      expect(global.fetch).toHaveBeenCalledTimes(3);
      expect(result1).toEqual(mockResponses.BTCUSDT_1m.data);
      expect(result2).toEqual(mockResponses.BTCUSDT_5m.data);
      expect(result3).toEqual(mockResponses.ETHUSDT_1m.data);

      // Fetch again - should use cache
      await liquidationVolumeService.fetchLiquidationVolume('BTCUSDT', '1m');
      await liquidationVolumeService.fetchLiquidationVolume('BTCUSDT', '5m');
      await liquidationVolumeService.fetchLiquidationVolume('ETHUSDT', '1m');
      
      expect(global.fetch).toHaveBeenCalledTimes(3); // No additional calls
    });
  });

  describe('data transformation', () => {
    it('should handle empty data response', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          symbol: 'BTCUSDT',
          timeframe: '1m',
          data: []
        })
      });

      const result = await liquidationVolumeService.fetchLiquidationVolume('BTCUSDT', '1m');
      
      expect(result).toEqual([]);
    });

    it('should pass through volume data unchanged', async () => {
      const volumeData = [
        {
          time: 1640995200,
          buy_volume: '1234.56',
          sell_volume: '2345.67',
          total_volume: '3580.23',
          buy_volume_formatted: '1,234.56',
          sell_volume_formatted: '2,345.67',
          total_volume_formatted: '3,580.23',
          count: 10,
          timestamp_ms: 1640995200000
        }
      ];

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          symbol: 'BTCUSDT',
          timeframe: '15m',
          data: volumeData
        })
      });

      const result = await liquidationVolumeService.fetchLiquidationVolume('BTCUSDT', '15m');
      
      expect(result).toEqual(volumeData);
      // Verify data is not mutated
      expect(result[0]).toHaveProperty('time', 1640995200);
      expect(result[0]).toHaveProperty('buy_volume', '1234.56');
      expect(result[0]).toHaveProperty('total_volume_formatted', '3,580.23');
    });
  });
});