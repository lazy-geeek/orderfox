/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { 
  createBotList, 
  updateBotList, 
  createBotCard, 
  addBotListEventListeners,
  getBotCardById,
  updateBotCardStatus,
  removeBotCard
} from '../../src/components/BotList.js';

describe('BotList Component', () => {
  let container;
  let mockBots;

  beforeEach(() => {
    // Clean up DOM
    document.body.innerHTML = '';
    
    // Create mock bots data
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

    // Create container
    container = createBotList();
    document.body.appendChild(container);
  });

  describe('createBotList', () => {
    it('should create bot list container with proper structure', () => {
      expect(container).toBeTruthy();
      expect(container.className).toBe('w-full');
      
      // Check for header
      const header = container.querySelector('.flex.justify-between.items-center');
      expect(header).toBeTruthy();
      
      // Check for create button
      const createBtn = container.querySelector('#create-bot-btn');
      expect(createBtn).toBeTruthy();
      expect(createBtn.textContent).toContain('New Bot');
      
      // Check for loading state
      const loadingState = container.querySelector('#bot-list-loading');
      expect(loadingState).toBeTruthy();
      
      // Check for empty state
      const emptyState = container.querySelector('#bot-list-empty');
      expect(emptyState).toBeTruthy();
      
      // Check for bot grid
      const botGrid = container.querySelector('#bot-grid');
      expect(botGrid).toBeTruthy();
      
      // Check for stats section
      const statsSection = container.querySelector('#bot-stats');
      expect(statsSection).toBeTruthy();
    });

    it('should have correct initial state visibility', () => {
      const loadingState = container.querySelector('#bot-list-loading');
      const emptyState = container.querySelector('#bot-list-empty');
      const botGrid = container.querySelector('#bot-grid');
      const statsSection = container.querySelector('#bot-stats');
      
      expect(loadingState.classList.contains('hidden')).toBe(false);
      expect(emptyState.classList.contains('hidden')).toBe(true);
      expect(botGrid.classList.contains('hidden')).toBe(true);
      expect(statsSection.classList.contains('hidden')).toBe(true);
    });
  });

  describe('createBotCard', () => {
    it('should create a bot card with correct structure', () => {
      const bot = mockBots[0];
      const card = createBotCard(bot);
      
      expect(card).toBeTruthy();
      expect(card.className).toContain('card');
      expect(card.getAttribute('data-bot-id')).toBe(bot.id);
      
      // Check for bot name
      const cardTitle = card.querySelector('.card-title');
      expect(cardTitle.textContent).toBe(bot.name);
      
      // Check for symbol
      const symbolBadge = card.querySelector('.badge-outline');
      expect(symbolBadge.textContent).toBe(bot.symbol);
      
      // Check for status
      const statusBadge = card.querySelector('.badge-success');
      expect(statusBadge).toBeTruthy();
      expect(statusBadge.textContent).toBe('Active');
    });

    it('should show inactive status for inactive bots', () => {
      const bot = mockBots[1]; // inactive bot
      const card = createBotCard(bot);
      
      const statusBadge = card.querySelector('.badge-warning');
      expect(statusBadge).toBeTruthy();
      expect(statusBadge.textContent).toBe('Inactive');
    });

    it('should include action buttons', () => {
      const bot = mockBots[0];
      const card = createBotCard(bot);
      
      const selectBtn = card.querySelector('.select-bot-btn');
      expect(selectBtn).toBeTruthy();
      expect(selectBtn.getAttribute('data-bot-id')).toBe(bot.id);
      
      const editBtn = card.querySelector('.edit-bot-btn');
      expect(editBtn).toBeTruthy();
      expect(editBtn.getAttribute('data-bot-id')).toBe(bot.id);
    });
  });

  describe('updateBotList', () => {
    it('should show loading state when loading is true', () => {
      updateBotList(container, [], { loading: true });
      
      const loadingState = container.querySelector('#bot-list-loading');
      const emptyState = container.querySelector('#bot-list-empty');
      const botGrid = container.querySelector('#bot-grid');
      
      expect(loadingState.classList.contains('hidden')).toBe(false);
      expect(emptyState.classList.contains('hidden')).toBe(true);
      expect(botGrid.classList.contains('hidden')).toBe(true);
    });

    it('should show empty state when no bots are provided', () => {
      updateBotList(container, [], { loading: false });
      
      const loadingState = container.querySelector('#bot-list-loading');
      const emptyState = container.querySelector('#bot-list-empty');
      const botGrid = container.querySelector('#bot-grid');
      
      expect(loadingState.classList.contains('hidden')).toBe(true);
      expect(emptyState.classList.contains('hidden')).toBe(false);
      expect(botGrid.classList.contains('hidden')).toBe(true);
    });

    it('should show error state when error is provided', () => {
      updateBotList(container, [], { loading: false, error: 'Test error' });
      
      const emptyState = container.querySelector('#bot-list-empty');
      expect(emptyState.classList.contains('hidden')).toBe(false);
      expect(emptyState.innerHTML).toContain('Error loading bots');
      expect(emptyState.innerHTML).toContain('Test error');
    });

    it('should display bots and stats when bots are provided', () => {
      updateBotList(container, mockBots, { loading: false });
      
      const loadingState = container.querySelector('#bot-list-loading');
      const emptyState = container.querySelector('#bot-list-empty');
      const botGrid = container.querySelector('#bot-grid');
      const statsSection = container.querySelector('#bot-stats');
      
      expect(loadingState.classList.contains('hidden')).toBe(true);
      expect(emptyState.classList.contains('hidden')).toBe(true);
      expect(botGrid.classList.contains('hidden')).toBe(false);
      expect(statsSection.classList.contains('hidden')).toBe(false);
      
      // Check stats
      const totalBots = container.querySelector('#total-bots');
      const activeBots = container.querySelector('#active-bots');
      const inactiveBots = container.querySelector('#inactive-bots');
      
      expect(totalBots.textContent).toBe('2');
      expect(activeBots.textContent).toBe('1');
      expect(inactiveBots.textContent).toBe('1');
      
      // Check bot cards - the botGrid should have been populated
      const botCards = botGrid.children;
      expect(botCards.length).toBe(2);
    });
  });

  describe('addBotListEventListeners', () => {
    it('should handle create bot button click', () => {
      const mockCallbacks = {
        onCreateBot: vi.fn(),
        onEditBot: vi.fn(),
        onDeleteBot: vi.fn(),
        onToggleBot: vi.fn(),
        onSelectBot: vi.fn(),
        onRetryLoad: vi.fn()
      };

      addBotListEventListeners(container, mockCallbacks);
      
      const createBtn = container.querySelector('#create-bot-btn');
      createBtn.click();
      
      expect(mockCallbacks.onCreateBot).toHaveBeenCalledTimes(1);
    });

    it('should handle bot card actions', () => {
      // First add bots to the container
      updateBotList(container, mockBots, { loading: false });
      
      const mockCallbacks = {
        onCreateBot: vi.fn(),
        onEditBot: vi.fn(),
        onDeleteBot: vi.fn(),
        onToggleBot: vi.fn(),
        onSelectBot: vi.fn(),
        onRetryLoad: vi.fn()
      };

      addBotListEventListeners(container, mockCallbacks);
      
      // Test select bot
      const selectBtn = container.querySelector('.select-bot-btn');
      selectBtn.click();
      expect(mockCallbacks.onSelectBot).toHaveBeenCalledWith('bot1');
      
      // Test edit bot
      const editBtn = container.querySelector('.edit-bot-btn');
      editBtn.click();
      expect(mockCallbacks.onEditBot).toHaveBeenCalledWith('bot1');
    });
  });

  describe('getBotCardById', () => {
    it('should find bot card by ID', () => {
      updateBotList(container, mockBots, { loading: false });
      
      const botCard = getBotCardById(container, 'bot1');
      expect(botCard).toBeTruthy();
      expect(botCard.getAttribute('data-bot-id')).toBe('bot1');
    });

    it('should return null for non-existent bot ID', () => {
      updateBotList(container, mockBots, { loading: false });
      
      const botCard = getBotCardById(container, 'non-existent');
      expect(botCard).toBe(null);
    });
  });

  describe('updateBotCardStatus', () => {
    it('should update bot card status correctly', () => {
      updateBotList(container, mockBots, { loading: false });
      
      // Update first bot (currently active) to inactive
      updateBotCardStatus(container, 'bot1', false);
      
      const botCard = getBotCardById(container, 'bot1');
      const statusBadge = botCard.querySelector('.badge');
      const statusIcon = botCard.querySelector('.text-lg');
      
      expect(statusBadge.textContent).toBe('Inactive');
      expect(statusBadge.classList.contains('badge-warning')).toBe(true);
      expect(statusIcon.textContent).toBe('🟡');
    });
  });

  describe('removeBotCard', () => {
    it('should remove bot card from container', () => {
      updateBotList(container, mockBots, { loading: false });
      
      expect(getBotCardById(container, 'bot1')).toBeTruthy();
      
      removeBotCard(container, 'bot1');
      
      expect(getBotCardById(container, 'bot1')).toBe(null);
    });

    it('should handle removal of non-existent bot card', () => {
      updateBotList(container, mockBots, { loading: false });
      
      // Should not throw error
      expect(() => removeBotCard(container, 'non-existent')).not.toThrow();
    });
  });
});