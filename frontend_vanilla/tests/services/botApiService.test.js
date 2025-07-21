/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { 
  fetchBots,
  createBot,
  updateBot,
  deleteBot,
  toggleBotStatus,
  getBotById,
  getBotStats,
  validateBotData,
  formatBotDataForApi,
  handleApiError,
  isBotNameUnique,
  filterBotsByStatus,
  sortBotsByCreatedAt
} from '../../src/services/botApiService.js';

// Mock fetch
global.fetch = vi.fn();

describe('BotApiService', () => {
  let mockBots;
  let mockBot;

  beforeEach(() => {
    // Reset fetch mock
    fetch.mockClear();
    
    // Create mock data
    mockBots = [
      {
        id: 'bot1',
        name: 'Test Bot 1',
        symbol: 'BTCUSDT',
        isActive: true,
        description: 'Test description',
        createdAt: '2023-01-01T00:00:00Z'
      },
      {
        id: 'bot2',
        name: 'Test Bot 2',
        symbol: 'ETHUSDT',
        isActive: false,
        description: 'Another test bot',
        createdAt: '2023-01-02T00:00:00Z'
      }
    ];

    mockBot = mockBots[0];
  });

  describe('fetchBots', () => {
    it('should fetch bots successfully', async () => {
      const mockResponse = { bots: mockBots };
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      });

      const result = await fetchBots();

      expect(fetch).toHaveBeenCalledWith('/api/v1/bots', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      expect(result).toEqual(mockBots);
    });

    it('should handle empty bots response', async () => {
      const mockResponse = {};
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      });

      const result = await fetchBots();

      expect(result).toEqual([]);
    });

    it('should handle API errors', async () => {
      const mockErrorResponse = { detail: 'Server error' };
      fetch.mockResolvedValueOnce({
        ok: false,
        json: async () => mockErrorResponse
      });

      await expect(fetchBots()).rejects.toThrow('Server error');
    });

    it('should handle network errors', async () => {
      fetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(fetchBots()).rejects.toThrow('Network error');
    });
  });

  describe('createBot', () => {
    it('should create bot successfully', async () => {
      const botData = {
        name: 'New Bot',
        symbol: 'BTCUSDT',
        isActive: true,
        description: 'New bot description'
      };

      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockBot
      });

      const result = await createBot(botData);

      expect(fetch).toHaveBeenCalledWith('/api/v1/bots', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: 'New Bot',
          symbol: 'BTCUSDT',
          isActive: true,
          isPaperTrading: true,
          description: 'New bot description'
        })
      });
      expect(result).toEqual(mockBot);
    });

    it('should handle missing required fields', async () => {
      const botData = { name: '' };

      await expect(createBot(botData)).rejects.toThrow('Bot name and symbol are required');
    });

    it('should trim whitespace from strings', async () => {
      const botData = {
        name: '  Test Bot  ',
        symbol: 'BTCUSDT',
        isActive: true,
        description: '  Test description  '
      };

      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockBot
      });

      await createBot(botData);

      const callArgs = fetch.mock.calls[0][1];
      const bodyData = JSON.parse(callArgs.body);
      
      expect(bodyData.name).toBe('Test Bot');
      expect(bodyData.description).toBe('Test description');
      expect(bodyData.isPaperTrading).toBe(true);
    });
  });

  describe('updateBot', () => {
    it('should update bot successfully', async () => {
      const botId = 'bot1';
      const botData = {
        name: 'Updated Bot',
        symbol: 'ETHUSDT',
        isActive: false,
        description: 'Updated description'
      };

      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ...mockBot, ...botData })
      });

      const result = await updateBot(botId, botData);

      expect(fetch).toHaveBeenCalledWith('/api/v1/bots/bot1', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: 'Updated Bot',
          symbol: 'ETHUSDT',
          isActive: false,
          isPaperTrading: undefined,
          description: 'Updated description'
        })
      });
      expect(result.name).toBe('Updated Bot');
    });

    it('should handle missing bot ID', async () => {
      await expect(updateBot('', {})).rejects.toThrow('Bot ID is required');
    });
  });

  describe('deleteBot', () => {
    it('should delete bot successfully', async () => {
      const botId = 'bot1';

      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({})
      });

      await deleteBot(botId);

      expect(fetch).toHaveBeenCalledWith('/api/v1/bots/bot1', {
        method: 'DELETE',
      });
    });

    it('should handle missing bot ID', async () => {
      await expect(deleteBot('')).rejects.toThrow('Bot ID is required');
    });
  });

  describe('toggleBotStatus', () => {
    it('should toggle bot status successfully', async () => {
      const botId = 'bot1';
      const isActive = false;

      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ...mockBot, isActive })
      });

      const result = await toggleBotStatus(botId, isActive);

      expect(fetch).toHaveBeenCalledWith('/api/v1/bots/bot1/status?is_active=false', {
        method: 'PATCH',
      });
      expect(result.isActive).toBe(false);
    });

    it('should handle missing bot ID', async () => {
      await expect(toggleBotStatus('', true)).rejects.toThrow('Bot ID is required');
    });
  });

  describe('getBotById', () => {
    it('should get bot by ID successfully', async () => {
      const botId = 'bot1';

      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockBot
      });

      const result = await getBotById(botId);

      expect(fetch).toHaveBeenCalledWith('/api/v1/bots/bot1', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      expect(result).toEqual(mockBot);
    });

    it('should handle missing bot ID', async () => {
      await expect(getBotById('')).rejects.toThrow('Bot ID is required');
    });
  });

  describe('getBotStats', () => {
    it('should get bot stats successfully', async () => {
      const mockStats = {
        total: 5,
        active: 3,
        inactive: 2
      };

      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockStats
      });

      const result = await getBotStats();

      expect(fetch).toHaveBeenCalledWith('/api/v1/bots/stats', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      expect(result).toEqual(mockStats);
    });
  });

  describe('validateBotData', () => {
    it('should validate valid bot data', () => {
      const validData = {
        name: 'Test Bot',
        symbol: 'BTCUSDT',
        description: 'Test description'
      };

      const result = validateBotData(validData);

      expect(result.isValid).toBe(true);
      expect(Object.keys(result.errors)).toHaveLength(0);
    });

    it('should validate required fields', () => {
      const invalidData = {
        name: '',
        symbol: '',
        description: ''
      };

      const result = validateBotData(invalidData);

      expect(result.isValid).toBe(false);
      expect(result.errors.name).toBe('Bot name is required');
      expect(result.errors.symbol).toBe('Trading symbol is required');
    });

    it('should validate name length', () => {
      const shortName = {
        name: 'Ab',
        symbol: 'BTCUSDT'
      };

      const result = validateBotData(shortName);

      expect(result.isValid).toBe(false);
      expect(result.errors.name).toBe('Bot name must be at least 3 characters');
    });

    it('should validate long name', () => {
      const longName = {
        name: 'A'.repeat(51),
        symbol: 'BTCUSDT'
      };

      const result = validateBotData(longName);

      expect(result.isValid).toBe(false);
      expect(result.errors.name).toBe('Bot name must be less than 50 characters');
    });

    it('should validate description length', () => {
      const longDescription = {
        name: 'Test Bot',
        symbol: 'BTCUSDT',
        description: 'A'.repeat(201)
      };

      const result = validateBotData(longDescription);

      expect(result.isValid).toBe(false);
      expect(result.errors.description).toBe('Description must be less than 200 characters');
    });
  });

  describe('formatBotDataForApi', () => {
    it('should format bot data correctly', () => {
      const rawData = {
        name: '  Test Bot  ',
        symbol: 'BTCUSDT',
        isActive: true,
        isPaperTrading: true,
        description: '  Test description  '
      };

      const result = formatBotDataForApi(rawData);

      expect(result).toEqual({
        name: 'Test Bot',
        symbol: 'BTCUSDT',
        isActive: true,
        isPaperTrading: true,
        description: 'Test description'
      });
    });

    it('should handle missing fields', () => {
      const rawData = {
        name: 'Test Bot'
      };

      const result = formatBotDataForApi(rawData);

      expect(result).toEqual({
        name: 'Test Bot',
        symbol: '',
        isActive: true,
        isPaperTrading: true,
        description: null
      });
    });
  });

  describe('handleApiError', () => {
    it('should handle error with message', () => {
      const error = new Error('Test error');
      const result = handleApiError(error);
      expect(result).toBe('Test error');
    });

    it('should handle error without message', () => {
      const error = {};
      const result = handleApiError(error);
      expect(result).toBe('An unexpected error occurred');
    });

    it('should handle response error', () => {
      const error = {
        response: {
          data: {
            detail: 'Server error'
          }
        }
      };
      const result = handleApiError(error);
      expect(result).toBe('Server error');
    });
  });

  describe('isBotNameUnique', () => {
    it('should return true for unique name', () => {
      const result = isBotNameUnique('Unique Bot', mockBots);
      expect(result).toBe(true);
    });

    it('should return false for existing name', () => {
      const result = isBotNameUnique('Test Bot 1', mockBots);
      expect(result).toBe(false);
    });

    it('should be case insensitive', () => {
      const result = isBotNameUnique('test bot 1', mockBots);
      expect(result).toBe(false);
    });

    it('should exclude specific bot ID', () => {
      const result = isBotNameUnique('Test Bot 1', mockBots, 'bot1');
      expect(result).toBe(true);
    });

    it('should handle empty input', () => {
      const result = isBotNameUnique('', mockBots);
      expect(result).toBe(false);
    });
  });

  describe('filterBotsByStatus', () => {
    it('should filter active bots', () => {
      const result = filterBotsByStatus(mockBots, true);
      expect(result).toHaveLength(1);
      expect(result[0].id).toBe('bot1');
    });

    it('should filter inactive bots', () => {
      const result = filterBotsByStatus(mockBots, false);
      expect(result).toHaveLength(1);
      expect(result[0].id).toBe('bot2');
    });

    it('should handle invalid input', () => {
      const result = filterBotsByStatus(null, true);
      expect(result).toEqual([]);
    });
  });

  describe('sortBotsByCreatedAt', () => {
    it('should sort bots by creation date (newest first)', () => {
      const result = sortBotsByCreatedAt(mockBots);
      expect(result).toHaveLength(2);
      expect(result[0].id).toBe('bot2'); // created later
      expect(result[1].id).toBe('bot1'); // created earlier
    });

    it('should handle invalid input', () => {
      const result = sortBotsByCreatedAt(null);
      expect(result).toEqual([]);
    });

    it('should not mutate original array', () => {
      const originalOrder = mockBots.map(bot => bot.id);
      sortBotsByCreatedAt(mockBots);
      const currentOrder = mockBots.map(bot => bot.id);
      expect(currentOrder).toEqual(originalOrder);
    });
  });
});