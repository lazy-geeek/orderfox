/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { 
  state,
  setState,
  fetchBots,
  createBot,
  updateBotById,
  deleteBotById,
  toggleBotStatus,
  setSelectedBotId,
  getSelectedBot,
  setCurrentView
} from '../../src/store/store.js';
import { WebSocketManager } from '../../src/services/websocketManager.js';
import { createMainLayout } from '../../src/layouts/MainLayout.js';
import { createBotList, updateBotList, addBotListEventListeners } from '../../src/components/BotList.js';
import { createBotEditor, showBotEditor, hideBotEditor, addBotEditorEventListeners } from '../../src/components/BotEditor.js';
import { createBotNavigation, showSelectedBotInfo, addNavigationEventListeners } from '../../src/components/BotNavigation.js';

// Mock fetch
global.fetch = vi.fn();

// Mock WebSocketManager
vi.mock('../../src/services/websocketManager.js', () => ({
  WebSocketManager: {
    switchToBotContext: vi.fn(),
    initializeBotContext: vi.fn(),
    validateBotConnections: vi.fn(),
    getBotContext: vi.fn(),
    switchSymbol: vi.fn(),
    switchTimeframe: vi.fn(),
    initializeConnections: vi.fn()
  }
}));

describe('End-to-End Integration Tests', () => {
  let mockBots;
  let mockSymbols;
  let mainLayout;
  let botList;
  let botEditor;
  let botNavigation;

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
      symbolsList: [],
      selectedSymbol: null,
      selectedTimeframe: '1m'
    });
    
    // Reset mocks
    fetch.mockClear();
    vi.clearAllMocks();
    
    // Create mock data
    mockBots = [
      {
        id: 'bot1',
        name: 'Bitcoin Trader',
        symbol: 'BTCUSDT',
        isActive: true,
        description: 'Automated Bitcoin trading bot',
        createdAt: '2023-01-01T00:00:00Z'
      },
      {
        id: 'bot2',
        name: 'Ethereum Trader',
        symbol: 'ETHUSDT',
        isActive: false,
        description: 'Automated Ethereum trading bot',
        createdAt: '2023-01-02T00:00:00Z'
      }
    ];

    mockSymbols = [
      { id: 'BTCUSDT', uiName: 'BTC/USDT', volume24hFormatted: '1.2B' },
      { id: 'ETHUSDT', uiName: 'ETH/USDT', volume24hFormatted: '800M' },
      { id: 'ADAUSDT', uiName: 'ADA/USDT', volume24hFormatted: '400M' }
    ];

    // Create main layout
    mainLayout = createMainLayout();
    document.body.appendChild(mainLayout);
    
    // Create components
    botList = createBotList();
    botEditor = createBotEditor();
    botNavigation = createBotNavigation();
    
    // Add to DOM
    const botListPlaceholder = document.getElementById('bot-list-placeholder');
    if (botListPlaceholder) {
      botListPlaceholder.replaceWith(botList);
    }
    
    const botNavigationPlaceholder = document.getElementById('bot-navigation-placeholder');
    if (botNavigationPlaceholder) {
      botNavigationPlaceholder.replaceWith(botNavigation);
    }
    
    document.body.appendChild(botEditor);
    
    // Mock global functions
    global.window = {
      ...global.window,
      showBotManagementSection: vi.fn(),
      showTradingInterface: vi.fn(),
      showBotSelectionPrompt: vi.fn()
    };
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Complete Bot Management Flow', () => {
    it('should handle complete bot creation and management flow', async () => {
      // Step 1: Initial state - no bots
      expect(state.bots).toHaveLength(0);
      expect(state.selectedBotId).toBe(null);
      expect(state.currentView).toBe('bot-selection');
      
      // Step 2: Fetch initial bots (empty)
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ bots: [] })
      });
      
      await fetchBots();
      
      updateBotList(botList, state.bots, { loading: false });
      
      const emptyState = botList.querySelector('#bot-list-empty');
      expect(emptyState.classList.contains('hidden')).toBe(false);
      
      // Step 3: Create first bot
      const newBot = {
        id: 'bot1',
        name: 'My First Bot',
        symbol: 'BTCUSDT',
        isActive: true,
        description: 'First trading bot',
        createdAt: '2023-01-01T00:00:00Z'
      };
      
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => newBot
      });
      
      const createdBot = await createBot({
        name: 'My First Bot',
        symbol: 'BTCUSDT',
        isActive: true,
        description: 'First trading bot'
      });
      
      expect(createdBot.id).toBe('bot1');
      expect(createdBot.name).toBe('My First Bot');
      
      // Step 4: Update bot list with new bot
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ bots: [newBot] })
      });
      
      await fetchBots();
      
      updateBotList(botList, state.bots, { loading: false });
      
      const statsSection = botList.querySelector('#bot-stats');
      expect(statsSection.classList.contains('hidden')).toBe(false);
      
      const totalBots = botList.querySelector('#total-bots');
      expect(totalBots.textContent).toBe('1');
      
      // Step 5: Select the bot
      setSelectedBotId('bot1');
      const selectedBot = getSelectedBot();
      
      expect(selectedBot.id).toBe('bot1');
      expect(selectedBot.name).toBe('My First Bot');
      
      // Step 6: Show bot info in navigation
      showSelectedBotInfo(botNavigation, selectedBot);
      
      const botName = botNavigation.querySelector('#selected-bot-name');
      const botSymbol = botNavigation.querySelector('#selected-bot-symbol');
      
      expect(botName.textContent).toBe('My First Bot');
      expect(botSymbol.textContent).toBe('BTCUSDT');
      
      // Step 7: Switch to bot context
      WebSocketManager.switchToBotContext.mockResolvedValue();
      
      await WebSocketManager.switchToBotContext(selectedBot);
      
      expect(WebSocketManager.switchToBotContext).toHaveBeenCalledWith(selectedBot);
      
      // Step 8: Switch to trading view
      setCurrentView('trading');
      expect(state.currentView).toBe('trading');
    });

    it('should handle bot editing flow', async () => {
      // Setup: Bot already exists
      setState({ bots: mockBots, selectedBotId: 'bot1' });
      
      const botToEdit = mockBots[0];
      
      // Step 1: Show bot editor in edit mode
      showBotEditor(botEditor, {
        bot: botToEdit,
        symbols: mockSymbols,
        mode: 'edit'
      });
      
      expect(botEditor.classList.contains('modal-open')).toBe(true);
      
      const modalTitle = botEditor.querySelector('#modal-title');
      expect(modalTitle.textContent).toBe('Edit Bot: Bitcoin Trader');
      
      // Step 2: Update bot data
      const updatedBot = {
        ...botToEdit,
        name: 'Updated Bitcoin Trader',
        description: 'Updated description'
      };
      
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => updatedBot
      });
      
      const result = await updateBotById('bot1', {
        name: 'Updated Bitcoin Trader',
        description: 'Updated description'
      });
      
      expect(result.name).toBe('Updated Bitcoin Trader');
      expect(result.description).toBe('Updated description');
      
      // Step 3: Hide editor
      hideBotEditor(botEditor);
      expect(botEditor.classList.contains('modal-open')).toBe(false);
    });

    it('should handle bot deletion flow', async () => {
      // Setup: Bots exist
      setState({ bots: mockBots });
      
      // Step 1: Delete bot
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({})
      });
      
      await deleteBotById('bot1');
      
      expect(fetch).toHaveBeenCalledWith('/api/v1/bots/bot1', {
        method: 'DELETE',
      });
      
      // Step 2: Update bot list after deletion
      const remainingBots = mockBots.filter(bot => bot.id !== 'bot1');
      
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ bots: remainingBots })
      });
      
      await fetchBots();
      
      expect(state.bots).toHaveLength(1);
      expect(state.bots[0].id).toBe('bot2');
    });

    it('should handle bot status toggle flow', async () => {
      // Setup: Bot exists
      setState({ bots: mockBots });
      
      const botToToggle = mockBots[1]; // inactive bot
      
      // Step 1: Toggle bot status
      const toggledBot = {
        ...botToToggle,
        isActive: true
      };
      
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => toggledBot
      });
      
      const result = await toggleBotStatus('bot2');
      
      expect(result.isActive).toBe(true);
      expect(fetch).toHaveBeenCalledWith('/api/v1/bots/bot2/status?is_active=true', {
        method: 'PATCH',
      });
    });
  });

  describe('User Interface Integration', () => {
    it('should integrate bot list with event handlers', async () => {
      // Setup: Create event handlers
      const mockCallbacks = {
        onCreateBot: vi.fn(),
        onEditBot: vi.fn(),
        onDeleteBot: vi.fn(),
        onToggleBot: vi.fn(),
        onSelectBot: vi.fn(),
        onRetryLoad: vi.fn()
      };
      
      addBotListEventListeners(botList, mockCallbacks);
      
      // Step 1: Test create bot button
      const createBtn = botList.querySelector('#create-bot-btn');
      createBtn.click();
      
      expect(mockCallbacks.onCreateBot).toHaveBeenCalled();
      
      // Step 2: Add bots to list and test interactions
      updateBotList(botList, mockBots, { loading: false });
      
      const editBtn = botList.querySelector('.edit-bot-btn');
      editBtn.click();
      
      expect(mockCallbacks.onEditBot).toHaveBeenCalledWith('bot1');
      
      const selectBtn = botList.querySelector('.select-bot-btn');
      selectBtn.click();
      
      expect(mockCallbacks.onSelectBot).toHaveBeenCalledWith('bot1');
    });

    it('should integrate bot navigation with event handlers', async () => {
      const mockCallback = vi.fn();
      
      addNavigationEventListeners(botNavigation, mockCallback);
      
      // Test navigation clicks
      const botsItem = botNavigation.querySelector('[data-item-id="bots"]');
      botsItem.click();
      
      expect(mockCallback).toHaveBeenCalledWith('show-bot-list', 'bots');
      
      const createBotItem = botNavigation.querySelector('[data-item-id="create-bot"]');
      createBotItem.click();
      
      expect(mockCallback).toHaveBeenCalledWith('create-bot', 'create-bot');
    });

    it('should integrate bot editor with event handlers', async () => {
      const mockCallbacks = {
        onSave: vi.fn(),
        onCancel: vi.fn()
      };
      
      addBotEditorEventListeners(botEditor, mockCallbacks);
      
      // Test cancel button
      const cancelBtn = botEditor.querySelector('#cancel-btn');
      cancelBtn.click();
      
      expect(mockCallbacks.onCancel).toHaveBeenCalled();
      
      // Test form submission with valid data
      const nameInput = botEditor.querySelector('#bot-name');
      const symbolSelect = botEditor.querySelector('#bot-symbol');
      
      symbolSelect.innerHTML = '<option value="BTCUSDT">BTCUSDT</option>';
      nameInput.value = 'Test Bot';
      symbolSelect.value = 'BTCUSDT';
      
      const form = botEditor.querySelector('#bot-form');
      form.dispatchEvent(new Event('submit'));
      
      expect(mockCallbacks.onSave).toHaveBeenCalledWith({
        name: 'Test Bot',
        symbol: 'BTCUSDT',
        isActive: true,
        description: ''
      });
    });
  });

  describe('WebSocket Integration Flow', () => {
    it('should integrate WebSocket operations with bot management', async () => {
      // Setup: Initialize WebSocket manager
      WebSocketManager.initializeConnections.mockResolvedValue();
      WebSocketManager.switchToBotContext.mockResolvedValue();
      WebSocketManager.validateBotConnections.mockReturnValue(true);
      
      // Step 1: Initialize with first symbol
      await WebSocketManager.initializeConnections('BTCUSDT');
      
      expect(WebSocketManager.initializeConnections).toHaveBeenCalledWith('BTCUSDT');
      
      // Step 2: Setup bot context
      setState({ bots: mockBots, selectedBotId: 'bot1' });
      
      const selectedBot = getSelectedBot();
      
      // Step 3: Switch to bot context
      await WebSocketManager.switchToBotContext(selectedBot);
      
      expect(WebSocketManager.switchToBotContext).toHaveBeenCalledWith(selectedBot);
      
      // Step 4: Validate connections
      const isValid = WebSocketManager.validateBotConnections(selectedBot);
      expect(isValid).toBe(true);
    });

    it('should handle symbol switching in bot context', async () => {
      setState({ 
        bots: mockBots, 
        selectedBotId: 'bot1',
        selectedSymbol: 'BTCUSDT' 
      });
      
      WebSocketManager.switchSymbol.mockResolvedValue();
      
      // Switch to different symbol
      await WebSocketManager.switchSymbol('ETHUSDT', true);
      
      expect(WebSocketManager.switchSymbol).toHaveBeenCalledWith('ETHUSDT', true);
    });
  });

  describe('Error Handling Integration', () => {
    it('should handle API errors gracefully across components', async () => {
      // Mock API error for bot creation
      fetch.mockRejectedValueOnce(new Error('Network error'));
      
      // Test error handling in bot creation
      try {
        await createBot({
          name: 'Test Bot',
          symbol: 'BTCUSDT',
          isActive: true
        });
        expect.fail('Should have thrown an error');
      } catch (error) {
        expect(error.message).toBe('Network error');
      }
      
      // Mock API error for bot fetching
      fetch.mockRejectedValueOnce(new Error('Network error'));
      
      // Test error handling in bot fetching
      try {
        await fetchBots();
        expect.fail('Should have thrown an error');
      } catch (error) {
        expect(error.message).toBe('Network error');
      }
    });

    it('should handle WebSocket errors gracefully', async () => {
      WebSocketManager.switchToBotContext.mockRejectedValue(new Error('Connection failed'));
      
      setState({ bots: mockBots, selectedBotId: 'bot1' });
      const selectedBot = getSelectedBot();
      
      try {
        await WebSocketManager.switchToBotContext(selectedBot);
        expect.fail('Should have thrown an error');
      } catch (error) {
        expect(error.message).toBe('Connection failed');
      }
    });
  });

  describe('Performance Integration', () => {
    it('should handle large-scale operations efficiently', async () => {
      // Create large dataset
      const largeBotList = Array.from({ length: 50 }, (_, i) => ({
        id: `bot${i}`,
        name: `Bot ${i}`,
        symbol: 'BTCUSDT',
        isActive: i % 2 === 0,
        description: `Bot ${i} description`,
        createdAt: new Date().toISOString()
      }));
      
      // Mock API response
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ bots: largeBotList })
      });
      
      const startTime = performance.now();
      
      // Fetch large bot list
      await fetchBots();
      
      // Update UI with large list
      updateBotList(botList, state.bots, { loading: false });
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Should handle large datasets efficiently
      expect(duration).toBeLessThan(1000); // 1 second threshold
      expect(state.bots).toHaveLength(50);
      
      // Verify UI updates
      const totalBots = botList.querySelector('#total-bots');
      expect(totalBots.textContent).toBe('50');
    });

    it('should handle rapid user interactions efficiently', async () => {
      setState({ bots: mockBots });
      
      const startTime = performance.now();
      
      // Simulate rapid bot selections
      for (let i = 0; i < 10; i++) {
        setSelectedBotId('bot1');
        setSelectedBotId('bot2');
        setSelectedBotId(null);
      }
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Should handle rapid interactions efficiently
      expect(duration).toBeLessThan(100); // 100ms threshold
    });
  });

  describe('State Consistency Integration', () => {
    it('should maintain state consistency across components', async () => {
      // Step 1: Create bot
      const newBot = mockBots[0];
      setState({ bots: [newBot] });
      
      // Step 2: Select bot
      setSelectedBotId('bot1');
      
      // Step 3: Verify state consistency
      expect(state.selectedBotId).toBe('bot1');
      expect(getSelectedBot().id).toBe('bot1');
      
      // Step 4: Update bot list UI
      updateBotList(botList, state.bots, { loading: false });
      
      // Step 5: Update navigation UI
      showSelectedBotInfo(botNavigation, getSelectedBot());
      
      // Step 6: Verify UI reflects state
      const botName = botNavigation.querySelector('#selected-bot-name');
      expect(botName.textContent).toBe('Bitcoin Trader');
      
      const totalBots = botList.querySelector('#total-bots');
      expect(totalBots.textContent).toBe('1');
    });

    it('should handle state changes across view transitions', async () => {
      // Initial state
      expect(state.currentView).toBe('bot-selection');
      
      // Create bot and switch to management
      setState({ bots: mockBots });
      setCurrentView('bot-management');
      
      expect(state.currentView).toBe('bot-management');
      
      // Select bot and switch to trading
      setSelectedBotId('bot1');
      setCurrentView('trading');
      
      expect(state.currentView).toBe('trading');
      expect(state.selectedBotId).toBe('bot1');
    });
  });
});