/**
 * Tests for LiquidationDisplay Component
 * 
 * Comprehensive tests for the LiquidationDisplay class including rendering,
 * WebSocket connection, data display, connection status, state subscriptions,
 * and cleanup functionality.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { LiquidationDisplay, createLiquidationDisplay } from '../../src/components/LiquidationDisplay.js';

// Mock dependencies
vi.mock('../../src/store/store.js', () => ({
  subscribe: vi.fn(),
  state: {
    selectedSymbol: 'BTCUSDT',
    currentLiquidations: [],
    liquidationsWsConnected: false,
    liquidationsLoading: false
  }
}));

vi.mock('../../src/services/websocketService.js', () => ({
  connectWebSocketStream: vi.fn(),
  disconnectWebSocketStream: vi.fn()
}));

describe('LiquidationDisplay', () => {
  let container;
  let display;
  
  beforeEach(() => {
    // Setup DOM
    document.body.innerHTML = '';
    container = document.createElement('div');
    document.body.appendChild(container);
    
    // Clear global functions
    if (window.updateLiquidationDisplay) {
      delete window.updateLiquidationDisplay;
    }
  });
  
  afterEach(() => {
    // Cleanup
    if (display) {
      display.cleanup();
    }
    document.body.innerHTML = '';
  });
  
  describe('LiquidationDisplay Class', () => {
    it('should create liquidation display instance', () => {
      display = new LiquidationDisplay(container);
      
      expect(display).toBeDefined();
      expect(display.container).toBe(container);
      expect(display.liquidations).toEqual([]);
      expect(display.maxLiquidations).toBe(50);
      expect(display.isConnected).toBe(false);
    });
    
    it('should render liquidation display structure', () => {
      display = new LiquidationDisplay(container);
      
      expect(container.querySelector('.orderfox-liquidation-display')).toBeTruthy();
      expect(container.querySelector('.display-title').textContent).toBe('Liquidations');
      expect(container.querySelector('.liquidation-header')).toBeTruthy();
      expect(container.querySelector('#liquidation-list')).toBeTruthy();
    });
    
    it('should have correct header columns', () => {
      display = new LiquidationDisplay(container);
      
      const headers = container.querySelectorAll('.liquidation-header span');
      expect(headers).toHaveLength(4);
      expect(headers[0].textContent).toBe('Side');
      expect(headers[1].textContent).toBe('Quantity');
      expect(headers[2].textContent).toBe('Price (USDT)');
      expect(headers[3].textContent).toBe('Time');
    });
  });
  
  describe('Liquidation Data Handling', () => {
    beforeEach(() => {
      display = new LiquidationDisplay(container);
    });
    
    it('should display liquidation data correctly', () => {
      const mockLiquidation = {
        symbol: "BTCUSDT",
        side: "SELL",
        quantityFormatted: "0.014",
        priceUsdtFormatted: "138.74",
        displayTime: "14:27:40"
      };
      
      display.addLiquidation(mockLiquidation);
      
      const item = container.querySelector('.liquidation-item');
      expect(item).toBeTruthy();
      expect(item.querySelector('.liquidation-side').textContent).toBe('SELL');
      expect(item.querySelector('.ask-price')).toBeTruthy();
      expect(item.querySelector('.liquidation-quantity').textContent).toBe('0.014');
      expect(item.querySelector('.liquidation-price').textContent).toBe('138.74');
      expect(item.querySelector('.liquidation-time').textContent).toBe('14:27:40');
    });
    
    it('should color code buy/sell sides correctly', () => {
      const buyLiquidation = {
        symbol: "BTCUSDT",
        side: "BUY",
        quantityFormatted: "0.014",
        priceUsdtFormatted: "138.74",
        displayTime: "14:27:40"
      };
      
      const sellLiquidation = {
        symbol: "BTCUSDT",
        side: "SELL", 
        quantityFormatted: "0.014",
        priceUsdtFormatted: "138.74",
        displayTime: "14:27:40"
      };
      
      display.addLiquidation(buyLiquidation);
      display.addLiquidation(sellLiquidation);
      
      const items = container.querySelectorAll('.liquidation-item');
      expect(items[0].querySelector('.ask-price')).toBeTruthy(); // SELL (last added, first in list)
      expect(items[1].querySelector('.bid-price')).toBeTruthy(); // BUY
    });
    
    it('should limit liquidations to maxLiquidations', () => {
      display.maxLiquidations = 5;
      
      // Add 10 liquidations
      for (let i = 0; i < 10; i++) {
        display.addLiquidation({
          symbol: "BTCUSDT",
          side: i % 2 === 0 ? "BUY" : "SELL",
          quantityFormatted: `${i}.000`,
          priceUsdtFormatted: `${i * 100}.00`,
          displayTime: `14:27:${i}0`
        });
      }
      
      const items = container.querySelectorAll('.liquidation-item');
      expect(items.length).toBe(5);
      expect(display.liquidations.length).toBe(5);
    });
    
    it('should remove empty state when adding liquidations', () => {
      // Initially should have empty state
      expect(container.querySelector('.empty-state')).toBeTruthy();
      
      display.addLiquidation({
        symbol: "BTCUSDT",
        side: "BUY",
        quantityFormatted: "0.014",
        priceUsdtFormatted: "138.74",
        displayTime: "14:27:40"
      });
      
      expect(container.querySelector('.empty-state')).toBeFalsy();
      expect(container.querySelector('.liquidation-item')).toBeTruthy();
    });
  });
  
  describe('Connection Status', () => {
    beforeEach(() => {
      display = new LiquidationDisplay(container);
    });
    
    it('should update connection status correctly', () => {
      const statusEl = container.querySelector('.connection-status');
      const statusText = container.querySelector('.status-text');
      
      // Initially disconnected
      expect(statusEl.classList.contains('disconnected')).toBe(true);
      expect(statusText.textContent).toBe('Disconnected');
      
      // Connect
      display.updateConnectionStatus(true);
      expect(statusEl.classList.contains('connected')).toBe(true);
      expect(statusEl.classList.contains('disconnected')).toBe(false);
      expect(statusText.textContent).toBe('Connected');
      
      // Disconnect
      display.updateConnectionStatus(false);
      expect(statusEl.classList.contains('disconnected')).toBe(true);
      expect(statusEl.classList.contains('connected')).toBe(false);
      expect(statusText.textContent).toBe('Disconnected');
    });
  });
  
  describe('WebSocket Message Handling', () => {
    beforeEach(() => {
      display = new LiquidationDisplay(container);
    });
    
    it('should handle initial liquidations message', () => {
      const initialData = {
        type: 'liquidations',
        initial: true,
        data: [
          {
            symbol: "BTCUSDT",
            side: "SELL",
            quantityFormatted: "0.014",
            priceUsdtFormatted: "138.74",
            displayTime: "14:27:40"
          }
        ]
      };
      
      // Use the global function that gets set up
      if (window.updateLiquidationDisplay) {
        window.updateLiquidationDisplay(initialData);
      }
      
      expect(display.liquidations.length).toBe(1);
      expect(container.querySelector('.liquidation-item')).toBeTruthy();
    });
    
    it('should handle single liquidation updates', () => {
      const updateData = {
        type: 'liquidation',
        data: {
          symbol: "BTCUSDT",
          side: "BUY",
          quantityFormatted: "0.014",
          priceUsdtFormatted: "138.74",
          displayTime: "14:27:40"
        }
      };
      
      // Use the global function that gets set up
      if (window.updateLiquidationDisplay) {
        window.updateLiquidationDisplay(updateData);
      }
      
      expect(display.liquidations.length).toBe(1);
      expect(container.querySelector('.liquidation-item')).toBeTruthy();
    });
    
    it('should handle error messages', () => {
      const errorData = {
        type: 'error',
        message: 'Connection error'
      };
      
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      // Use the global function that gets set up
      if (window.updateLiquidationDisplay) {
        window.updateLiquidationDisplay(errorData);
      }
      
      expect(consoleSpy).toHaveBeenCalledWith('Liquidation stream error:', 'Connection error');
      consoleSpy.mockRestore();
    });
  });
  
  describe('Legacy Component Function', () => {
    it('should create liquidation display component', () => {
      const component = createLiquidationDisplay();
      
      expect(component).toBeDefined();
      expect(component.className).toContain('orderfox-display-base');
      expect(component.className).toContain('orderfox-liquidation-display');
    });
  });
});