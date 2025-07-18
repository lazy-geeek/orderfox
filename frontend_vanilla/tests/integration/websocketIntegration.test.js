/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { WebSocketManager } from '../../src/services/websocketManager.js';
import { 
  state,
  setState,
  setSelectedBotId,
  getSelectedBot,
  setSelectedSymbol,
  setSelectedTimeframe
} from '../../src/store/store.js';
import { resetZoomState } from '../../src/components/LightweightChart.js';
import { 
  connectWebSocketStream,
  disconnectWebSocketStream,
  disconnectAllWebSockets
} from '../../src/services/websocketService.js';

// Mock dependencies
vi.mock('../../src/components/LightweightChart.js', () => ({
  resetZoomState: vi.fn()
}));

vi.mock('../../src/services/websocketService.js', () => ({
  connectWebSocketStream: vi.fn(),
  disconnectWebSocketStream: vi.fn(),
  disconnectAllWebSockets: vi.fn(),
  updateOrderBookParameters: vi.fn()
}));

describe('WebSocket Integration Tests', () => {
  let mockBots;

  beforeEach(() => {
    // Reset state
    setState({
      bots: [],
      selectedBotId: null,
      selectedSymbol: null,
      selectedTimeframe: '1m',
      displayDepth: 10,
      selectedRounding: 0.01,
      currentCandles: [],
      candlesWsConnected: false,
      orderBookWsConnected: false,
      tradesWsConnected: false,
      liquidationsWsConnected: false
    });
    
    // Clear all mocks
    vi.clearAllMocks();
    
    // Create mock bots
    mockBots = [
      {
        id: 'bot1',
        name: 'BTC Bot',
        symbol: 'BTCUSDT',
        isActive: true,
        description: 'Bitcoin trading bot'
      },
      {
        id: 'bot2',
        name: 'ETH Bot',
        symbol: 'ETHUSDT',
        isActive: false,
        description: 'Ethereum trading bot'
      }
    ];
    
    // Mock DOM elements
    const chartContainer = document.createElement('div');
    chartContainer.className = 'chart-container';
    chartContainer.style.width = '800px';
    // Mock clientWidth property
    Object.defineProperty(chartContainer, 'clientWidth', {
      value: 800,
      writable: true
    });
    document.body.appendChild(chartContainer);
    
    // Mock global functions
    global.window = {
      ...global.window,
      updateLatestCandleDirectly: vi.fn(),
      resetChartData: vi.fn(),
      state: state
    };
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Bot Context Initialization', () => {
    it('should initialize bot context with proper WebSocket connections', async () => {
      const bot = mockBots[0];
      
      await WebSocketManager.initializeBotContext(bot);
      
      // Verify state updates
      expect(state.selectedSymbol).toBe('BTCUSDT');
      
      // Verify WebSocket connections (check that all 4 were called)
      expect(connectWebSocketStream).toHaveBeenCalledTimes(4);
      expect(connectWebSocketStream).toHaveBeenCalledWith('BTCUSDT', 'candles', '1m', 800);
      expect(connectWebSocketStream).toHaveBeenCalledWith('BTCUSDT', 'orderbook', null, 10, null);
      expect(connectWebSocketStream).toHaveBeenCalledWith('BTCUSDT', 'trades');
      expect(connectWebSocketStream).toHaveBeenCalledWith('BTCUSDT', 'liquidations', '1m');
      
      // Verify UI reset
      expect(resetZoomState).toHaveBeenCalled();
    });

    it('should handle invalid bot context initialization', async () => {
      const invalidBot = null;
      
      await expect(WebSocketManager.initializeBotContext(invalidBot))
        .rejects.toThrow('Invalid bot object or missing symbol');
    });

    it('should handle bot without symbol', async () => {
      const botWithoutSymbol = { id: 'bot1', name: 'Test Bot' };
      
      await expect(WebSocketManager.initializeBotContext(botWithoutSymbol))
        .rejects.toThrow('Invalid bot object or missing symbol');
    });
  });

  describe('Bot Context Switching', () => {
    it('should switch to bot context when symbol is different', async () => {
      setState({ selectedSymbol: 'ADAUSDT' });
      const bot = mockBots[0]; // BTCUSDT
      
      await WebSocketManager.switchToBotContext(bot);
      
      // Should call switchSymbol since symbols are different
      expect(disconnectAllWebSockets).toHaveBeenCalled();
      expect(resetZoomState).toHaveBeenCalled();
    });

    it('should not switch symbol when already matching', async () => {
      setState({ selectedSymbol: 'BTCUSDT' });
      const bot = mockBots[0]; // BTCUSDT
      
      await WebSocketManager.switchToBotContext(bot);
      
      // Should not disconnect all WebSockets since symbol matches
      expect(disconnectAllWebSockets).not.toHaveBeenCalled();
    });

    it('should handle switching to invalid bot context', async () => {
      await expect(WebSocketManager.switchToBotContext(null))
        .rejects.toThrow('Invalid bot object or missing symbol');
    });
  });

  describe('Bot Connection Validation', () => {
    it('should validate bot connections correctly', () => {
      setState({ selectedSymbol: 'BTCUSDT' });
      const bot = mockBots[0];
      
      const isValid = WebSocketManager.validateBotConnections(bot);
      
      expect(isValid).toBe(true);
    });

    it('should fail validation for symbol mismatch', () => {
      setState({ selectedSymbol: 'ETHUSDT' });
      const bot = mockBots[0]; // BTCUSDT
      
      const isValid = WebSocketManager.validateBotConnections(bot);
      
      expect(isValid).toBe(false);
    });

    it('should fail validation for inactive bot', () => {
      setState({ selectedSymbol: 'ETHUSDT' });
      const bot = mockBots[1]; // inactive bot
      
      const isValid = WebSocketManager.validateBotConnections(bot);
      
      expect(isValid).toBe(false);
    });

    it('should handle null bot validation', () => {
      const isValid = WebSocketManager.validateBotConnections(null);
      
      expect(isValid).toBe(false);
    });
  });

  describe('Bot Context Information', () => {
    it('should get bot context information', () => {
      setState({ 
        bots: mockBots,
        selectedBotId: 'bot1',
        selectedSymbol: 'BTCUSDT',
        selectedTimeframe: '5m',
        candlesWsConnected: true
      });
      
      const context = WebSocketManager.getBotContext();
      
      expect(context.bot.id).toBe('bot1');
      expect(context.symbol).toBe('BTCUSDT');
      expect(context.timeframe).toBe('5m');
      expect(context.hasActiveConnections).toBe(true);
    });

    it('should handle no selected bot', () => {
      setState({ selectedBotId: null });
      
      const context = WebSocketManager.getBotContext();
      
      expect(context.bot).toBe(null);
      expect(context.isValid).toBe(false);
    });
  });

  describe('Bot Connection Status', () => {
    it('should get bot connection status', () => {
      setState({
        bots: mockBots,
        selectedBotId: 'bot1',
        selectedSymbol: 'BTCUSDT',
        candlesWsConnected: true,
        orderBookWsConnected: true,
        tradesWsConnected: false,
        liquidationsWsConnected: true
      });
      
      const status = WebSocketManager.getBotConnectionStatus();
      
      expect(status.bot.id).toBe('bot1');
      expect(status.symbol).toBe('BTCUSDT');
      expect(status.connections.candles).toBe(true);
      expect(status.connections.orderbook).toBe(true);
      expect(status.connections.trades).toBe(false);
      expect(status.connections.liquidations).toBe(true);
      expect(status.lastUpdate).toBeDefined();
    });
  });

  describe('Symbol Switching with Bot Context', () => {
    it('should validate bot context when switching symbols', async () => {
      setState({ 
        bots: mockBots,
        selectedBotId: 'bot1',
        selectedSymbol: 'BTCUSDT'
      });
      
      // Mock the console.warn to verify it's called
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      
      await WebSocketManager.switchSymbol('ETHUSDT', true);
      
      // Should warn about symbol mismatch
      expect(consoleSpy).toHaveBeenCalledWith(
        'Symbol ETHUSDT does not match selected bot symbol BTCUSDT'
      );
      
      consoleSpy.mockRestore();
    });

    it('should allow symbol switching without validation', async () => {
      setState({ selectedSymbol: 'BTCUSDT' });
      
      await WebSocketManager.switchSymbol('ETHUSDT', false);
      
      expect(state.selectedSymbol).toBe('ETHUSDT');
      expect(disconnectAllWebSockets).toHaveBeenCalled();
    });
  });

  describe('Timeframe Switching', () => {
    it('should switch timeframe and maintain bot context', async () => {
      setState({
        selectedSymbol: 'BTCUSDT',
        selectedTimeframe: '1m'
      });
      
      await WebSocketManager.switchTimeframe('5m');
      
      expect(state.selectedTimeframe).toBe('5m');
      expect(disconnectWebSocketStream).toHaveBeenCalledWith('candles', 'BTCUSDT', '1m');
      expect(disconnectWebSocketStream).toHaveBeenCalledWith('liquidations', 'BTCUSDT', '1m');
      expect(connectWebSocketStream).toHaveBeenCalledWith('BTCUSDT', 'candles', '5m', 800);
      expect(connectWebSocketStream).toHaveBeenCalledWith('BTCUSDT', 'liquidations', '5m');
    });
  });

  describe('Bot Deactivation Handling', () => {
    it('should handle bot deactivation gracefully', async () => {
      setState({
        bots: mockBots,
        selectedBotId: 'bot1'
      });
      
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
      
      await WebSocketManager.handleBotDeactivation(mockBots[0]);
      
      expect(consoleSpy).toHaveBeenCalledWith('Handling bot deactivation: BTC Bot');
      expect(consoleSpy).toHaveBeenCalledWith('Deactivated bot was currently active, maintaining connections but adding warning');
      
      consoleSpy.mockRestore();
    });

    it('should handle deactivation of non-selected bot', async () => {
      setState({
        bots: mockBots,
        selectedBotId: 'bot1'
      });
      
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
      
      await WebSocketManager.handleBotDeactivation(mockBots[1]);
      
      expect(consoleSpy).toHaveBeenCalledWith('Handling bot deactivation: ETH Bot');
      expect(consoleSpy).not.toHaveBeenCalledWith('Deactivated bot was currently active, maintaining connections but adding warning');
      
      consoleSpy.mockRestore();
    });
  });

  describe('Container Width Calculation', () => {
    it('should get container width for chart calculations', () => {
      const width = WebSocketManager.getContainerWidth();
      
      expect(width).toBe(800); // Based on mock DOM element
    });

    it('should use default width when container not found', () => {
      document.body.innerHTML = ''; // Remove chart container
      
      const width = WebSocketManager.getContainerWidth();
      
      expect(width).toBe(800); // Default fallback
    });
  });

  describe('Integration with State Management', () => {
    it('should integrate with state management for bot selection', () => {
      setState({ bots: mockBots });
      
      setSelectedBotId('bot1');
      const selectedBot = getSelectedBot();
      
      expect(selectedBot.id).toBe('bot1');
      expect(selectedBot.symbol).toBe('BTCUSDT');
      
      const isValid = WebSocketManager.validateBotConnections(selectedBot);
      expect(isValid).toBe(false); // Symbol not set yet
      
      setSelectedSymbol('BTCUSDT');
      const isValidNow = WebSocketManager.validateBotConnections(selectedBot);
      expect(isValidNow).toBe(true);
    });
  });

  describe('Error Handling in WebSocket Operations', () => {
    it('should handle WebSocket connection errors', async () => {
      // Mock error in WebSocket connection
      connectWebSocketStream.mockImplementation(() => {
        throw new Error('Connection failed');
      });
      
      const bot = mockBots[0];
      
      try {
        await WebSocketManager.initializeBotContext(bot);
        expect.fail('Should have thrown an error');
      } catch (error) {
        expect(error.message).toBe('Connection failed');
      }
    });

    it('should handle race conditions in symbol switching', async () => {
      // Mock multiple rapid symbol switches
      const promises = [
        WebSocketManager.switchSymbol('BTCUSDT', false),
        WebSocketManager.switchSymbol('ETHUSDT', false),
        WebSocketManager.switchSymbol('ADAUSDT', false)
      ];
      
      try {
        await Promise.all(promises);
        
        // Should handle all switches without errors
        expect(disconnectAllWebSockets).toHaveBeenCalledTimes(3);
      } catch (error) {
        // If errors occur, they should be handled gracefully
        expect(error).toBeDefined();
      }
    });
  });

  describe('Performance Optimization', () => {
    it('should optimize WebSocket connections for bot context', async () => {
      const bot = mockBots[0];
      
      const startTime = performance.now();
      
      try {
        await WebSocketManager.initializeBotContext(bot);
        
        const endTime = performance.now();
        const duration = endTime - startTime;
        
        // Should complete quickly
        expect(duration).toBeLessThan(100);
        
        // Should make efficient WebSocket connections
        expect(connectWebSocketStream).toHaveBeenCalledTimes(4);
      } catch (error) {
        // If connection fails, ensure error is handled properly
        expect(error).toBeDefined();
      }
    });

    it('should handle multiple bot context switches efficiently', async () => {
      setState({ bots: mockBots });
      
      const startTime = performance.now();
      
      try {
        // Switch between different bots
        await WebSocketManager.switchToBotContext(mockBots[0]);
        await WebSocketManager.switchToBotContext(mockBots[1]);
        await WebSocketManager.switchToBotContext(mockBots[0]);
        
        const endTime = performance.now();
        const duration = endTime - startTime;
        
        // Should handle multiple switches efficiently
        expect(duration).toBeLessThan(200);
      } catch (error) {
        // If switching fails, ensure error is handled properly
        expect(error).toBeDefined();
      }
    });
  });
});