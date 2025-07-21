/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { 
  state,
  setState,
  fetchBots,
  createBot,
  setSelectedBotId,
  getSelectedBot,
  clearBotError,
  setBotError,
  setCurrentView
} from '../../src/store/store.js';
import { WebSocketManager } from '../../src/services/websocketManager.js';
import { createBotList, updateBotList } from '../../src/components/BotList.js';
import { createBotEditor, showBotEditor, getFormData } from '../../src/components/BotEditor.js';
import { createBotNavigation, showSelectedBotInfo } from '../../src/components/BotNavigation.js';

// Mock fetch
global.fetch = vi.fn();

// Mock WebSocketManager
vi.mock('../../src/services/websocketManager.js', () => ({
  WebSocketManager: {
    switchToBotContext: vi.fn(),
    initializeBotContext: vi.fn(),
    validateBotConnections: vi.fn(),
    getBotContext: vi.fn(),
    getBotConnectionStatus: vi.fn()
  }
}));

describe('Bot Flow Integration Tests', () => {
  let mockBots;
  let mockSymbols;

  beforeEach(() => {
    // Clean up DOM
    document.body.innerHTML = '';
    
    // Reset state
    setState({
      bots: [],
      selectedBotId: null,
      botLoading: false,
      botError: null,
      currentView: 'bot-selection',
      symbolsList: []
    });
    
    // Reset fetch mock
    fetch.mockClear();
    
    // Reset WebSocketManager mocks
    vi.clearAllMocks();
    
    // Create mock data
    mockBots = [
      {
        id: 'bot1',
        name: 'Test Bot 1',
        symbol: 'BTCUSDT',
        isActive: true,
        isPaperTrading: true,
        description: 'Test bot for BTC trading',
        createdAt: '2023-01-01T00:00:00Z'
      },
      {
        id: 'bot2',
        name: 'Test Bot 2',
        symbol: 'ETHUSDT',
        isActive: false,
        isPaperTrading: true,
        description: 'Test bot for ETH trading',
        createdAt: '2023-01-02T00:00:00Z'
      }
    ];

    mockSymbols = [
      { id: 'BTCUSDT', uiName: 'BTC/USDT', volume24hFormatted: '1.2B' },
      { id: 'ETHUSDT', uiName: 'ETH/USDT', volume24hFormatted: '800M' }
    ];
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Bot Creation Flow', () => {
    it('should create a new bot end-to-end', async () => {
      // Mock successful bot creation
      const newBot = {
        id: 'bot3',
        name: 'New Test Bot',
        symbol: 'ADAUSDT',
        isActive: true,
        isPaperTrading: true,
        description: 'New bot description',
        createdAt: '2023-01-03T00:00:00Z'
      };

      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => newBot
      });

      // Mock fetch bots response
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ bots: [...mockBots, newBot] })
      });

      // Step 1: Create bot editor
      const botEditor = createBotEditor();
      document.body.appendChild(botEditor);
      
      // Step 2: Show bot editor in create mode
      showBotEditor(botEditor, { symbols: mockSymbols, mode: 'create' });
      
      // Step 3: Fill form data
      const nameInput = botEditor.querySelector('#bot-name');
      const symbolSelect = botEditor.querySelector('#bot-symbol');
      const descriptionTextarea = botEditor.querySelector('#bot-description');
      
      symbolSelect.innerHTML = '<option value="ADAUSDT">ADAUSDT</option>';
      nameInput.value = 'New Test Bot';
      symbolSelect.value = 'ADAUSDT';
      descriptionTextarea.value = 'New bot description';
      
      // Step 4: Get form data
      const formData = getFormData(botEditor);
      
      expect(formData.name).toBe('New Test Bot');
      expect(formData.symbol).toBe('ADAUSDT');
      expect(formData.description).toBe('New bot description');
      
      // Step 5: Create bot
      const createdBot = await createBot(formData);
      
      expect(fetch).toHaveBeenCalledWith('/api/v1/bots', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: 'New Test Bot',
          symbol: 'ADAUSDT',
          isActive: true,
          isPaperTrading: true,
          description: 'New bot description'
        })
      });
      
      expect(createdBot.id).toBe('bot3');
      expect(createdBot.name).toBe('New Test Bot');
      
      // Step 6: Fetch updated bot list
      await fetchBots();
      
      expect(state.bots).toHaveLength(3);
      expect(state.bots[2].name).toBe('New Test Bot');
    });

    it('should handle bot creation errors', async () => {
      // Mock failed bot creation
      fetch.mockRejectedValueOnce(new Error('Server error'));
      
      const botEditor = createBotEditor();
      document.body.appendChild(botEditor);
      
      const formData = {
        name: 'Test Bot',
        symbol: 'BTCUSDT',
        isActive: true,
        description: 'Test'
      };
      
      await expect(createBot(formData)).rejects.toThrow('Server error');
    });
  });

  describe('Bot Selection Flow', () => {
    it('should select a bot and switch to trading interface', async () => {
      // Step 1: Set up initial state with bots
      setState({ bots: mockBots, symbolsList: mockSymbols });
      
      // Mock WebSocketManager methods
      WebSocketManager.switchToBotContext.mockResolvedValue();
      WebSocketManager.validateBotConnections.mockReturnValue(true);
      WebSocketManager.getBotContext.mockReturnValue({
        bot: mockBots[0],
        symbol: 'BTCUSDT',
        isValid: true
      });
      
      // Step 2: Create bot navigation
      const botNavigation = createBotNavigation();
      document.body.appendChild(botNavigation);
      
      // Step 3: Select bot
      setSelectedBotId('bot1');
      const selectedBot = getSelectedBot();
      
      expect(selectedBot.id).toBe('bot1');
      expect(selectedBot.symbol).toBe('BTCUSDT');
      
      // Step 4: Show selected bot info
      showSelectedBotInfo(botNavigation, selectedBot);
      
      const botName = botNavigation.querySelector('#selected-bot-name');
      const botSymbol = botNavigation.querySelector('#selected-bot-symbol');
      const botStatus = botNavigation.querySelector('#selected-bot-status');
      
      expect(botName.textContent).toBe('Test Bot 1');
      expect(botSymbol.textContent).toBe('BTCUSDT');
      expect(botStatus.textContent).toBe('Active');
      
      // Step 5: Switch to bot context
      await WebSocketManager.switchToBotContext(selectedBot);
      
      expect(WebSocketManager.switchToBotContext).toHaveBeenCalledWith(selectedBot);
      
      // Step 6: Verify trading view is enabled
      const tradingViewItem = botNavigation.querySelector('[data-item-id="trading-view"]');
      expect(tradingViewItem.classList.contains('disabled')).toBe(false);
    });

    it('should handle bot selection errors', async () => {
      setState({ bots: mockBots });
      
      // Mock WebSocketManager error
      WebSocketManager.switchToBotContext.mockRejectedValue(new Error('Connection failed'));
      
      setSelectedBotId('bot1');
      const selectedBot = getSelectedBot();
      
      await expect(WebSocketManager.switchToBotContext(selectedBot)).rejects.toThrow('Connection failed');
    });
  });

  describe('Bot List Display Flow', () => {
    it('should display bot list with statistics', async () => {
      // Mock fetch bots response
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ bots: mockBots })
      });
      
      // Step 1: Create bot list
      const botList = createBotList();
      document.body.appendChild(botList);
      
      // Step 2: Fetch bots
      await fetchBots();
      
      // Step 3: Update bot list display
      updateBotList(botList, state.bots, {
        loading: false,
        error: null
      });
      
      // Step 4: Verify statistics
      const totalBots = botList.querySelector('#total-bots');
      const activeBots = botList.querySelector('#active-bots');
      const inactiveBots = botList.querySelector('#inactive-bots');
      
      expect(totalBots.textContent).toBe('2');
      expect(activeBots.textContent).toBe('1');
      expect(inactiveBots.textContent).toBe('1');
      
      // Step 5: Verify bot cards
      const botGrid = botList.querySelector('#bot-grid');
      const botCards = botGrid.children;
      expect(botCards.length).toBe(2);
      
      const firstCard = botCards[0];
      expect(firstCard.getAttribute('data-bot-id')).toBe('bot1');
      expect(firstCard.querySelector('.card-title').textContent).toBe('Test Bot 1');
    });

    it('should handle empty bot list', async () => {
      // Mock empty bots response
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ bots: [] })
      });
      
      const botList = createBotList();
      document.body.appendChild(botList);
      
      await fetchBots();
      
      updateBotList(botList, state.bots, {
        loading: false,
        error: null
      });
      
      const emptyState = botList.querySelector('#bot-list-empty');
      expect(emptyState.classList.contains('hidden')).toBe(false);
      expect(emptyState.textContent).toContain('No bots yet');
    });
  });

  describe('Bot Context Validation Flow', () => {
    it('should validate bot context when switching symbols', async () => {
      // Step 1: Set up bot context
      setState({ bots: mockBots, selectedBotId: 'bot1' });
      
      const selectedBot = getSelectedBot();
      expect(selectedBot.symbol).toBe('BTCUSDT');
      
      // Step 2: Mock WebSocketManager validation
      WebSocketManager.validateBotConnections.mockReturnValue(true);
      WebSocketManager.getBotContext.mockReturnValue({
        bot: selectedBot,
        symbol: 'BTCUSDT',
        isValid: true,
        hasActiveConnections: true
      });
      
      // Step 3: Validate bot connections
      const isValid = WebSocketManager.validateBotConnections(selectedBot);
      expect(isValid).toBe(true);
      
      // Step 4: Get bot context
      const botContext = WebSocketManager.getBotContext();
      expect(botContext.bot).toBe(selectedBot);
      expect(botContext.symbol).toBe('BTCUSDT');
      expect(botContext.isValid).toBe(true);
    });

    it('should handle invalid bot context', async () => {
      setState({ bots: mockBots, selectedBotId: 'bot2' });
      
      const selectedBot = getSelectedBot();
      expect(selectedBot.isActive).toBe(false);
      
      // Mock validation failure
      WebSocketManager.validateBotConnections.mockReturnValue(false);
      WebSocketManager.getBotContext.mockReturnValue({
        bot: selectedBot,
        symbol: 'ETHUSDT',
        isValid: false,
        hasActiveConnections: false
      });
      
      const isValid = WebSocketManager.validateBotConnections(selectedBot);
      expect(isValid).toBe(false);
    });
  });

  describe('Error Handling Flow', () => {
    it('should handle network errors in bot operations', async () => {
      // Mock network error
      fetch.mockRejectedValueOnce(new Error('Network error'));
      
      try {
        await fetchBots();
        expect.fail('Should have thrown an error');
      } catch (error) {
        expect(error.message).toBe('Network error');
      }
    });

    it('should handle API errors in bot operations', async () => {
      // Mock API error
      fetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Server error' })
      });
      
      try {
        await fetchBots();
        expect.fail('Should have thrown an error');
      } catch (error) {
        expect(error.message).toBe('Server error');
      }
    });

    it('should manage error state properly', async () => {
      // Set error state
      setBotError('Test error');
      expect(state.botError).toBe('Test error');
      
      // Clear error state
      clearBotError();
      expect(state.botError).toBe(null);
    });
  });

  describe('State Management Flow', () => {
    it('should manage view state transitions correctly', () => {
      // Initial state
      expect(state.currentView).toBe('bot-selection');
      
      // Switch to bot management
      setCurrentView('bot-management');
      expect(state.currentView).toBe('bot-management');
      
      // Switch to trading
      setCurrentView('trading');
      expect(state.currentView).toBe('trading');
    });

    it('should handle bot selection state changes', () => {
      setState({ bots: mockBots });
      
      // No bot selected initially
      expect(state.selectedBotId).toBe(null);
      expect(getSelectedBot()).toBe(null);
      
      // Select first bot
      setSelectedBotId('bot1');
      expect(state.selectedBotId).toBe('bot1');
      
      const selectedBot = getSelectedBot();
      expect(selectedBot.id).toBe('bot1');
      expect(selectedBot.name).toBe('Test Bot 1');
    });
  });

  describe('Performance and Resource Management', () => {
    it('should handle multiple bot operations efficiently', async () => {
      // Mock multiple bot operations
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ bots: mockBots })
      });
      
      const startTime = performance.now();
      
      // Fetch bots
      await fetchBots();
      
      // Update state multiple times
      setSelectedBotId('bot1');
      setSelectedBotId('bot2');
      setSelectedBotId('bot1');
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Should complete within reasonable time
      expect(duration).toBeLessThan(100); // 100ms threshold
      
      // Final state should be correct
      expect(state.selectedBotId).toBe('bot1');
      expect(state.bots).toHaveLength(2);
    });

    it('should handle large bot lists efficiently', async () => {
      // Create large bot list
      const largeBotList = Array.from({ length: 100 }, (_, i) => ({
        id: `bot${i}`,
        name: `Bot ${i}`,
        symbol: 'BTCUSDT',
        isActive: i % 2 === 0,
        description: `Bot ${i} description`,
        createdAt: new Date().toISOString()
      }));
      
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ bots: largeBotList })
      });
      
      const startTime = performance.now();
      
      await fetchBots();
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Should handle large datasets efficiently
      expect(duration).toBeLessThan(500); // 500ms threshold
      expect(state.bots).toHaveLength(100);
    });
  });
});