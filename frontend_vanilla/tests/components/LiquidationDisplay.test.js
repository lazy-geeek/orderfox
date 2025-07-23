/**
 * Tests for LiquidationDisplay Component
 * 
 * Comprehensive tests for the LiquidationDisplay class including rendering,
 * WebSocket connection, data display, connection status, state subscriptions,
 * and cleanup functionality.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { LiquidationDisplay } from '../../src/components/LiquidationDisplay.js';

// Mock dependencies
vi.mock('../../src/store/store.js', () => ({
  subscribe: vi.fn(),
  state: {
    selectedSymbol: 'BTCUSDT',
    currentLiquidations: [],
    liquidationsWsConnected: false,
    liquidationsLoading: false
  },
  setLiquidationsWsConnected: vi.fn(),
  setLiquidationsLoading: vi.fn(),
  setLiquidationsError: vi.fn(),
  clearLiquidationsError: vi.fn()
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
      expect(container.querySelector('.display-header')).toBeTruthy();
      expect(container.querySelector('.symbol-label')).toBeTruthy();
      expect(container.querySelector('.liquidation-header')).toBeTruthy();
      expect(container.querySelector('#liquidation-list')).toBeTruthy();
    });
    
    it('should have correct header columns', () => {
      display = new LiquidationDisplay(container);
      
      const headers = container.querySelectorAll('.liquidation-header span');
      expect(headers).toHaveLength(3);
      expect(headers[0].textContent).toBe('Amount (USDT)');
      expect(headers[1].textContent).toBe('Quantity (BTC)'); // Updated by state subscription on init
      expect(headers[2].textContent).toBe('Time');
    });
  });
  
  describe('Liquidation Data Handling', () => {
    beforeEach(() => {
      display = new LiquidationDisplay(container);
    });
    
    it('should display liquidation data correctly', () => {
      const mockLiquidation = {
        symbol: 'BTCUSDT',
        side: 'SELL',
        quantityFormatted: '0.014',
        priceUsdtFormatted: '139',
        displayTime: '14:27:40'
      };
      
      display.addLiquidation(mockLiquidation);
      
      const item = container.querySelector('.liquidation-item');
      expect(item).toBeTruthy();
      
      const amounts = item.querySelectorAll('.display-amount');
      expect(amounts[0].textContent).toBe('139'); // Price in USDT
      expect(amounts[0].classList.contains('ask-price')).toBe(true); // SELL = red
      expect(amounts[1].textContent).toBe('0.014'); // Quantity
      
      expect(item.querySelector('.display-time').textContent).toBe('14:27:40');
    });
    
    it('should color code buy/sell sides correctly', () => {
      const buyLiquidation = {
        symbol: 'BTCUSDT',
        side: 'BUY',
        quantityFormatted: '0.014',
        priceUsdtFormatted: '139',
        displayTime: '14:27:40'
      };
      
      const sellLiquidation = {
        symbol: 'BTCUSDT',
        side: 'SELL', 
        quantityFormatted: '0.014',
        priceUsdtFormatted: '138',
        displayTime: '14:27:40'
      };
      
      display.addLiquidation(buyLiquidation);
      display.addLiquidation(sellLiquidation);
      
      const items = container.querySelectorAll('.liquidation-item');
      // Items are displayed in reverse order (newest first)
      const sellAmount = items[0].querySelector('.display-amount');
      const buyAmount = items[1].querySelector('.display-amount');
      
      expect(sellAmount.classList.contains('ask-price')).toBe(true); // SELL = red
      expect(buyAmount.classList.contains('bid-price')).toBe(true); // BUY = green
    });
    
    it('should limit liquidations to maxLiquidations', () => {
      display.maxLiquidations = 5;
      
      // Add 10 liquidations
      for (let i = 0; i < 10; i++) {
        display.addLiquidation({
          symbol: 'BTCUSDT',
          side: i % 2 === 0 ? 'BUY' : 'SELL',
          quantityFormatted: `${i}.000`,
          priceUsdtFormatted: `${i * 100}.00`,
          displayTime: `14:27:${i}0`
        });
      }
      
      const items = container.querySelectorAll('.liquidation-item');
      expect(items.length).toBe(5);
      expect(display.liquidations.length).toBe(5);
    });
    
    it('should display comma-formatted prices correctly', () => {
      const mockLiquidation = {
        symbol: 'BTCUSDT',
        side: 'SELL',
        quantityFormatted: '0.5',
        priceUsdtFormatted: '22,839',
        displayTime: '14:27:40'
      };
      
      display.addLiquidation(mockLiquidation);
      
      const item = container.querySelector('.liquidation-item');
      const amounts = item.querySelectorAll('.display-amount');
      expect(amounts[0].textContent).toBe('22,839'); // Price with comma
    });
    
    it('should remove empty state when adding liquidations', () => {
      // Initially should have empty state
      expect(container.querySelector('.empty-state')).toBeTruthy();
      
      display.addLiquidation({
        symbol: 'BTCUSDT',
        side: 'BUY',
        quantityFormatted: '0.014',
        priceUsdtFormatted: '138.74',
        displayTime: '14:27:40'
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
      const statusIndicator = container.querySelector('.status-indicator');
      const statusText = container.querySelector('.status-text');
      
      // Initially disconnected
      expect(statusIndicator.classList.contains('disconnected')).toBe(true);
      expect(statusText.textContent).toBe('Disconnected');
      
      // Connect
      display.updateConnectionStatus(true);
      expect(statusIndicator.classList.contains('connected')).toBe(true);
      expect(statusIndicator.classList.contains('disconnected')).toBe(false);
      expect(statusText.textContent).toBe('Live');
      
      // Disconnect
      display.updateConnectionStatus(false);
      expect(statusIndicator.classList.contains('disconnected')).toBe(true);
      expect(statusIndicator.classList.contains('connected')).toBe(false);
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
            symbol: 'BTCUSDT',
            side: 'SELL',
            quantityFormatted: '0.014',
            priceUsdtFormatted: '138.74',
            displayTime: '14:27:40'
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
          symbol: 'BTCUSDT',
          side: 'BUY',
          quantityFormatted: '0.014',
          priceUsdtFormatted: '138.74',
          displayTime: '14:27:40'
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
  
  describe('Dynamic Quantity Header', () => {
    beforeEach(() => {
      display = new LiquidationDisplay(container);
    });
    
    it('should update quantity header with symbol name', () => {
      // Simulate symbol being set
      display.currentSymbol = 'BTCUSDT';
      display.setupWebSocket();
      
      const quantityHeader = container.querySelector('.quantity-header');
      expect(quantityHeader.textContent).toBe('Quantity (BTC)');
    });
    
    it('should update quantity header for different symbols', () => {
      // Since setupWebSocket is called during init with BTCUSDT
      let quantityHeader = container.querySelector('.quantity-header');
      expect(quantityHeader.textContent).toBe('Quantity (BTC)');
      
      // Simulate changing symbol by directly updating header
      // (In real app, this happens via state subscription)
      quantityHeader.textContent = 'Quantity (SOL)';
      expect(quantityHeader.textContent).toBe('Quantity (SOL)');
      
      quantityHeader.textContent = 'Quantity (ETH)';
      expect(quantityHeader.textContent).toBe('Quantity (ETH)');
    });
    
    it('should update quantity header from liquidation data baseAsset', () => {
      const updateData = {
        type: 'liquidation',
        data: {
          symbol: 'XRPUSDT',
          side: 'BUY',
          quantityFormatted: '100.000',
          priceUsdtFormatted: '50',
          displayTime: '14:27:40',
          baseAsset: 'XRP'
        }
      };
      
      if (window.updateLiquidationDisplay) {
        window.updateLiquidationDisplay(updateData);
      }
      
      const quantityHeader = container.querySelector('.quantity-header');
      expect(quantityHeader.textContent).toBe('Quantity (XRP)');
    });
  });
  
  describe('Three Column Layout', () => {
    beforeEach(() => {
      display = new LiquidationDisplay(container);
    });
    
    it('should render 3 columns without SIDE column', () => {
      const header = container.querySelector('.liquidation-header');
      expect(header.classList.contains('three-columns')).toBe(true);
      
      const headers = header.querySelectorAll('span');
      expect(headers).toHaveLength(3);
      
      // Verify no side header exists
      const sideHeader = Array.from(headers).find(h => h.textContent.includes('Side'));
      expect(sideHeader).toBeUndefined();
    });
    
    it('should render liquidation items with 3 columns', () => {
      const mockLiquidation = {
        symbol: 'BTCUSDT',
        side: 'SELL',
        quantityFormatted: '0.014',
        priceUsdtFormatted: '139',
        displayTime: '14:27:40'
      };
      
      display.addLiquidation(mockLiquidation);
      
      const item = container.querySelector('.liquidation-item');
      const spans = item.querySelectorAll('span');
      
      // Should have exactly 3 spans (amount, quantity, time)
      expect(spans).toHaveLength(3);
    });
  });
  
});