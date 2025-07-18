/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { 
  createBotNavigation,
  updateNavigationState,
  showSelectedBotInfo,
  addNavigationEventListeners
} from '../../src/components/BotNavigation.js';

describe('BotNavigation Component', () => {
  let navigation;
  let mockBot;

  beforeEach(() => {
    // Clean up DOM
    document.body.innerHTML = '';
    
    // Create mock bot data
    mockBot = {
      id: 'bot1',
      name: 'Test Bot',
      symbol: 'BTCUSDT',
      isActive: true,
      description: 'Test description'
    };

    // Create navigation
    navigation = createBotNavigation();
    document.body.appendChild(navigation);
  });

  describe('createBotNavigation', () => {
    it('should create navigation with proper structure', () => {
      expect(navigation).toBeTruthy();
      expect(navigation.className).toBe('flex flex-col h-full');
      
      // Check for header
      const header = navigation.querySelector('.flex.items-center.gap-3');
      expect(header).toBeTruthy();
      expect(header.innerHTML).toContain('🤖');
      expect(header.innerHTML).toContain('Bot Management');
      
      // Check for menu
      const menu = navigation.querySelector('.menu.menu-md');
      expect(menu).toBeTruthy();
      
      // Check for bot info section
      const botInfo = navigation.querySelector('#selected-bot-info');
      expect(botInfo).toBeTruthy();
      expect(botInfo.classList.contains('hidden')).toBe(true);
      
      // Check for footer
      const footer = navigation.querySelector('.mt-auto.pt-4');
      expect(footer).toBeTruthy();
    });

    it('should have correct menu items', () => {
      const menuItems = navigation.querySelectorAll('[data-action]');
      
      expect(menuItems.length).toBe(3);
      
      // Check menu item actions
      const actions = Array.from(menuItems).map(item => item.getAttribute('data-action'));
      expect(actions).toEqual(['show-bot-list', 'create-bot', 'show-trading']);
      
      // Check menu item IDs
      const itemIds = Array.from(menuItems).map(item => item.getAttribute('data-item-id'));
      expect(itemIds).toEqual(['bots', 'create-bot', 'trading-view']);
    });

    it('should have correct initial menu item states', () => {
      const botsItem = navigation.querySelector('[data-item-id="bots"]');
      const tradingItem = navigation.querySelector('[data-item-id="trading-view"]');
      
      expect(botsItem.classList.contains('active')).toBe(true);
      expect(tradingItem.classList.contains('disabled')).toBe(true);
      expect(tradingItem.hasAttribute('disabled')).toBe(true);
    });
  });

  describe('updateNavigationState', () => {
    it('should update active state correctly', () => {
      const botsItem = navigation.querySelector('[data-item-id="bots"]');
      const createBotItem = navigation.querySelector('[data-item-id="create-bot"]');
      
      // Initially, bots should be active
      expect(botsItem.classList.contains('active')).toBe(true);
      expect(createBotItem.classList.contains('active')).toBe(false);
      
      // Update to make create-bot active
      updateNavigationState(navigation, 'create-bot');
      
      expect(botsItem.classList.contains('active')).toBe(false);
      expect(createBotItem.classList.contains('active')).toBe(true);
    });

    it('should handle invalid item ID gracefully', () => {
      expect(() => {
        updateNavigationState(navigation, 'non-existent-item');
      }).not.toThrow();
    });
  });

  describe('showSelectedBotInfo', () => {
    it('should show bot info when bot is provided', () => {
      showSelectedBotInfo(navigation, mockBot);
      
      const botInfo = navigation.querySelector('#selected-bot-info');
      const botName = navigation.querySelector('#selected-bot-name');
      const botSymbol = navigation.querySelector('#selected-bot-symbol');
      const botStatus = navigation.querySelector('#selected-bot-status');
      
      expect(botInfo.classList.contains('hidden')).toBe(false);
      expect(botName.textContent).toBe(mockBot.name);
      expect(botSymbol.textContent).toBe(mockBot.symbol);
      expect(botStatus.textContent).toBe('Active');
      expect(botStatus.classList.contains('text-success')).toBe(true);
    });

    it('should show inactive status for inactive bot', () => {
      const inactiveBot = { ...mockBot, isActive: false };
      
      showSelectedBotInfo(navigation, inactiveBot);
      
      const botStatus = navigation.querySelector('#selected-bot-status');
      const statusDot = navigation.querySelector('.w-2.h-2');
      
      expect(botStatus.textContent).toBe('Inactive');
      expect(botStatus.classList.contains('text-warning')).toBe(true);
      expect(statusDot.classList.contains('bg-warning')).toBe(true);
    });

    it('should enable trading view when bot is selected', () => {
      showSelectedBotInfo(navigation, mockBot);
      
      const tradingViewItem = navigation.querySelector('[data-item-id="trading-view"]');
      
      expect(tradingViewItem.classList.contains('disabled')).toBe(false);
      expect(tradingViewItem.hasAttribute('disabled')).toBe(false);
    });

    it('should hide bot info when no bot is provided', () => {
      // First show a bot
      showSelectedBotInfo(navigation, mockBot);
      expect(navigation.querySelector('#selected-bot-info').classList.contains('hidden')).toBe(false);
      
      // Then hide it
      showSelectedBotInfo(navigation, null);
      
      const botInfo = navigation.querySelector('#selected-bot-info');
      const tradingViewItem = navigation.querySelector('[data-item-id="trading-view"]');
      
      expect(botInfo.classList.contains('hidden')).toBe(true);
      expect(tradingViewItem.classList.contains('disabled')).toBe(true);
      expect(tradingViewItem.hasAttribute('disabled')).toBe(true);
    });
  });

  describe('addNavigationEventListeners', () => {
    it('should handle navigation click events', () => {
      const mockCallback = vi.fn();
      
      addNavigationEventListeners(navigation, mockCallback);
      
      const botsItem = navigation.querySelector('[data-item-id="bots"]');
      botsItem.click();
      
      expect(mockCallback).toHaveBeenCalledWith('show-bot-list', 'bots');
    });

    it('should update active state on navigation click', () => {
      const mockCallback = vi.fn();
      
      addNavigationEventListeners(navigation, mockCallback);
      
      const createBotItem = navigation.querySelector('[data-item-id="create-bot"]');
      const botsItem = navigation.querySelector('[data-item-id="bots"]');
      
      // Initially, bots should be active
      expect(botsItem.classList.contains('active')).toBe(true);
      expect(createBotItem.classList.contains('active')).toBe(false);
      
      // Click on create-bot
      createBotItem.click();
      
      // Active state should update
      expect(botsItem.classList.contains('active')).toBe(false);
      expect(createBotItem.classList.contains('active')).toBe(true);
    });

    it('should not handle clicks on disabled items', () => {
      const mockCallback = vi.fn();
      
      addNavigationEventListeners(navigation, mockCallback);
      
      const tradingViewItem = navigation.querySelector('[data-item-id="trading-view"]');
      
      // Trading view should be disabled initially
      expect(tradingViewItem.hasAttribute('disabled')).toBe(true);
      
      tradingViewItem.click();
      
      expect(mockCallback).not.toHaveBeenCalled();
    });

    it('should handle clicks on enabled trading view after bot selection', () => {
      const mockCallback = vi.fn();
      
      addNavigationEventListeners(navigation, mockCallback);
      
      // First enable trading view by showing bot info
      showSelectedBotInfo(navigation, mockBot);
      
      const tradingViewItem = navigation.querySelector('[data-item-id="trading-view"]');
      
      // Now it should be enabled
      expect(tradingViewItem.hasAttribute('disabled')).toBe(false);
      
      tradingViewItem.click();
      
      expect(mockCallback).toHaveBeenCalledWith('show-trading', 'trading-view');
    });

    it('should handle clicks on nested elements', () => {
      const mockCallback = vi.fn();
      
      addNavigationEventListeners(navigation, mockCallback);
      
      const botsItem = navigation.querySelector('[data-item-id="bots"]');
      const iconSpan = botsItem.querySelector('span');
      
      // Click on the icon inside the menu item
      iconSpan.click();
      
      expect(mockCallback).toHaveBeenCalledWith('show-bot-list', 'bots');
    });
  });

  describe('bot info display', () => {
    it('should display correct bot information structure', () => {
      const botInfo = navigation.querySelector('#selected-bot-info');
      
      expect(botInfo.querySelector('#selected-bot-name')).toBeTruthy();
      expect(botInfo.querySelector('#selected-bot-symbol')).toBeTruthy();
      expect(botInfo.querySelector('#selected-bot-status')).toBeTruthy();
      expect(botInfo.querySelector('.w-2.h-2')).toBeTruthy(); // Status dot
    });

    it('should have correct initial bot info state', () => {
      const botName = navigation.querySelector('#selected-bot-name');
      const botSymbol = navigation.querySelector('#selected-bot-symbol');
      const botStatus = navigation.querySelector('#selected-bot-status');
      
      expect(botName.textContent).toBe('No bot selected');
      expect(botSymbol.textContent).toBe('-');
      expect(botStatus.textContent).toBe('-');
    });
  });

  describe('footer section', () => {
    it('should have settings and help links', () => {
      const footer = navigation.querySelector('.mt-auto.pt-4');
      const links = footer.querySelectorAll('a');
      
      expect(links.length).toBe(2);
      
      const linkTexts = Array.from(links).map(link => {
        const textContent = link.textContent.trim();
        // Remove emoji and extra whitespace
        return textContent.replace(/[^\w\s]/g, '').replace(/\s+/g, ' ').trim();
      });
      expect(linkTexts).toContain('Settings');
      expect(linkTexts).toContain('Help');
    });
  });
});