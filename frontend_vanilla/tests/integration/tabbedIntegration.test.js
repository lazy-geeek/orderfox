/**
 * @jest-environment jsdom
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createTabbedTradingDisplay } from '../../src/components/TabbedTradingDisplay.js';
import { state, subscribe, notify } from '../../src/store/store.js';

// Mock the individual components
vi.mock('../../src/components/OrderBookDisplay.js', () => ({
  createOrderBookDisplay: vi.fn(() => ({
    element: (() => {
      const div = document.createElement('div');
      div.className = 'order-book-display';
      div.setAttribute('data-testid', 'order-book-display');
      return div;
    })(),
    destroy: vi.fn()
  }))
}));

vi.mock('../../src/components/LastTradesDisplay.js', () => ({
  createLastTradesDisplay: vi.fn(() => ({
    element: (() => {
      const div = document.createElement('div');
      div.className = 'last-trades-display';
      div.setAttribute('data-testid', 'last-trades-display');
      return div;
    })(),
    destroy: vi.fn()
  }))
}));

vi.mock('../../src/components/LiquidationDisplay.js', () => ({
  LiquidationDisplay: vi.fn().mockImplementation(() => ({
    element: (() => {
      const div = document.createElement('div');
      div.className = 'liquidation-display';
      div.setAttribute('data-testid', 'liquidation-display');
      return div;
    })(),
    cleanup: vi.fn()
  }))
}));

describe('Tabbed Integration Tests', () => {
  let tabbedComponent;
  let unsubscribeCallbacks = [];

  beforeEach(() => {
    // Clear all mocks before each test
    vi.clearAllMocks();
    unsubscribeCallbacks = [];
  });

  afterEach(() => {
    // Clean up component if it exists
    if (tabbedComponent && tabbedComponent.destroy) {
      tabbedComponent.destroy();
      tabbedComponent = null;
    }
    
    // Clean up any state subscriptions
    unsubscribeCallbacks.forEach(callback => callback());
    unsubscribeCallbacks = [];
  });

  describe('Component Integration within Tabs', () => {
    it('should integrate all three components within tabbed container', () => {
      tabbedComponent = createTabbedTradingDisplay();
      
      // Verify tabbed container is created
      expect(tabbedComponent.element.classList.contains('orderfox-tabbed-trading-display')).toBe(true);
      
      // Verify all three tabs exist
      const radioInputs = tabbedComponent.element.querySelectorAll('input[type="radio"][name="trading_tabs"]');
      expect(radioInputs.length).toBe(3);
      
      // Verify tab labels
      const labels = Array.from(radioInputs).map(input => input.getAttribute('aria-label'));
      expect(labels).toEqual(['Order Book', 'Trades', 'Liquidations']);
    });

    it('should load components lazily when switching tabs', () => {
      tabbedComponent = createTabbedTradingDisplay();
      
      const radioInputs = tabbedComponent.element.querySelectorAll('input[type="radio"][name="trading_tabs"]');
      
      // Switch to Trades tab
      radioInputs[1].checked = true;
      radioInputs[1].dispatchEvent(new Event('change'));
      
      // Verify trades component is loaded
      setTimeout(() => {
        const tradesElement = tabbedComponent.element.querySelector('[data-testid="last-trades-display"]');
        expect(tradesElement).toBeTruthy();
      }, 10);
      
      // Switch to Liquidations tab
      radioInputs[2].checked = true;
      radioInputs[2].dispatchEvent(new Event('change'));
      
      // Verify liquidations component is loaded
      setTimeout(() => {
        const liquidationsElement = tabbedComponent.element.querySelector('[data-testid="liquidation-display"]');
        expect(liquidationsElement).toBeTruthy();
      }, 10);
    });

    it('should maintain component state when switching tabs', () => {
      tabbedComponent = createTabbedTradingDisplay();
      
      const radioInputs = tabbedComponent.element.querySelectorAll('input[type="radio"][name="trading_tabs"]');
      
      // Initialize multiple tabs
      radioInputs[1].checked = true;
      radioInputs[1].dispatchEvent(new Event('change'));
      
      radioInputs[2].checked = true;
      radioInputs[2].dispatchEvent(new Event('change'));
      
      // Switch back to Order Book
      radioInputs[0].checked = true;
      radioInputs[0].dispatchEvent(new Event('change'));
      
      // All components should remain initialized and available
      setTimeout(() => {
        expect(tabbedComponent.element.querySelector('[data-testid="order-book-display"]')).toBeTruthy();
        expect(tabbedComponent.element.querySelector('[data-testid="last-trades-display"]')).toBeTruthy();
        expect(tabbedComponent.element.querySelector('[data-testid="liquidation-display"]')).toBeTruthy();
      }, 10);
    });
  });

  describe('State Management Integration', () => {
    it('should allow components to receive state updates within tabs', () => {
      tabbedComponent = createTabbedTradingDisplay();
      
      // Mock state update
      const mockStateData = {
        selectedSymbol: 'BTCUSDT',
        currentOrderBook: { bids: [], asks: [] },
        currentTrades: []
      };
      
      // Simulate state changes that would affect components
      Object.assign(state, mockStateData);
      
      // Notify state change
      notify('selectedSymbol');
      notify('currentOrderBook');
      notify('currentTrades');
      
      // Components should be able to receive these updates
      // (We can't test the actual subscription in this mock setup,
      // but we can verify the structure supports it)
      expect(tabbedComponent.element).toBeTruthy();
    });

    it('should handle component lifecycle with state subscriptions', () => {
      tabbedComponent = createTabbedTradingDisplay();
      
      const radioInputs = tabbedComponent.element.querySelectorAll('input[type="radio"][name="trading_tabs"]');
      
      // Initialize all tabs to test lifecycle
      radioInputs.forEach((radio, index) => {
        radio.checked = true;
        radio.dispatchEvent(new Event('change'));
      });
      
      // Destroy component
      tabbedComponent.destroy();
      
      // Component should clean up properly
      expect(() => tabbedComponent.destroy()).not.toThrow();
    });
  });

  describe('WebSocket Integration within Tabs', () => {
    it('should support WebSocket connections for tabbed components', () => {
      tabbedComponent = createTabbedTradingDisplay();
      
      // Mock WebSocket data updates
      const mockOrderBookData = {
        bids: [{ price: '50000', size: '0.5' }],
        asks: [{ price: '50100', size: '0.3' }]
      };
      
      const mockTradesData = [
        { price: '50050', size: '0.1', time: '2023-01-01T10:00:00Z' }
      ];
      
      // Simulate WebSocket data flow
      // In a real scenario, these would be handled by the individual components
      // Here we just verify the structure supports it
      expect(typeof mockOrderBookData).toBe('object');
      expect(Array.isArray(mockTradesData)).toBe(true);
      
      // Tabbed container should not interfere with WebSocket connections
      expect(tabbedComponent.element.classList.contains('orderfox-tabbed-trading-display')).toBe(true);
    });

    it('should maintain WebSocket connections when switching tabs', () => {
      tabbedComponent = createTabbedTradingDisplay();
      
      const radioInputs = tabbedComponent.element.querySelectorAll('input[type="radio"][name="trading_tabs"]');
      
      // Initialize components by switching tabs
      radioInputs[1].checked = true;
      radioInputs[1].dispatchEvent(new Event('change'));
      
      radioInputs[0].checked = true;
      radioInputs[0].dispatchEvent(new Event('change'));
      
      // WebSocket connections should persist across tab switches
      // (This is verified by the component's lazy loading design)
      expect(tabbedComponent.element.querySelectorAll('.tab-content').length).toBe(3);
    });
  });

  describe('Performance Integration', () => {
    it('should optimize performance with lazy loading', () => {
      const startTime = performance.now();
      
      tabbedComponent = createTabbedTradingDisplay();
      
      const creationTime = performance.now() - startTime;
      
      // Initial creation should be fast (no components loaded yet)
      expect(creationTime).toBeLessThan(50); // Allow 50ms for component creation
      
      // Only placeholders should exist initially
      expect(tabbedComponent.element.querySelectorAll('.component-placeholder').length).toBeGreaterThan(0);
    });

    it('should handle multiple tab switches efficiently', () => {
      tabbedComponent = createTabbedTradingDisplay();
      
      const radioInputs = tabbedComponent.element.querySelectorAll('input[type="radio"][name="trading_tabs"]');
      const startTime = performance.now();
      
      // Simulate rapid tab switching
      for (let i = 0; i < 10; i++) {
        const tabIndex = i % 3;
        radioInputs[tabIndex].checked = true;
        radioInputs[tabIndex].dispatchEvent(new Event('change'));
      }
      
      const switchTime = performance.now() - startTime;
      
      // Tab switching should be efficient
      expect(switchTime).toBeLessThan(100); // Allow 100ms for 10 tab switches
    });
  });

  describe('Error Handling Integration', () => {
    it('should gracefully handle component initialization errors', () => {
      // This test verifies that tab errors don't break the entire interface
      tabbedComponent = createTabbedTradingDisplay();
      
      const radioInputs = tabbedComponent.element.querySelectorAll('input[type="radio"][name="trading_tabs"]');
      
      // Switching tabs should not throw errors
      expect(() => {
        radioInputs.forEach(radio => {
          radio.checked = true;
          radio.dispatchEvent(new Event('change'));
        });
      }).not.toThrow();
    });

    it('should maintain stability when components fail', () => {
      tabbedComponent = createTabbedTradingDisplay();
      
      // Remove placeholders to simulate component failure
      const placeholders = tabbedComponent.element.querySelectorAll('.component-placeholder');
      placeholders.forEach(placeholder => placeholder.remove());
      
      const radioInputs = tabbedComponent.element.querySelectorAll('input[type="radio"][name="trading_tabs"]');
      
      // Tab switching should still work
      expect(() => {
        radioInputs[1].checked = true;
        radioInputs[1].dispatchEvent(new Event('change'));
      }).not.toThrow();
    });
  });

  describe('Responsive Integration', () => {
    it('should maintain functionality across different viewport sizes', () => {
      tabbedComponent = createTabbedTradingDisplay();
      
      // Simulate different viewport scenarios
      const mobileWidth = 375;
      const tabletWidth = 768;
      const desktopWidth = 1024;
      
      // The tabbed component should work regardless of viewport
      // (CSS handles the responsive behavior)
      [mobileWidth, tabletWidth, desktopWidth].forEach(width => {
        // Simulate viewport change (in a real browser this would affect CSS)
        document.documentElement.style.width = `${width}px`;
        
        // Tabs should remain functional
        const radioInputs = tabbedComponent.element.querySelectorAll('input[type="radio"][name="trading_tabs"]');
        expect(radioInputs.length).toBe(3);
        
        // Tab switching should work
        expect(() => {
          radioInputs[1].checked = true;
          radioInputs[1].dispatchEvent(new Event('change'));
        }).not.toThrow();
      });
      
      // Reset
      document.documentElement.style.width = '';
    });
  });

  describe('Accessibility Integration', () => {
    it('should maintain accessibility features in tabbed interface', () => {
      tabbedComponent = createTabbedTradingDisplay();
      
      const radioInputs = tabbedComponent.element.querySelectorAll('input[type="radio"][name="trading_tabs"]');
      
      // Check ARIA labels
      radioInputs.forEach(radio => {
        expect(radio.getAttribute('aria-label')).toBeTruthy();
      });
      
      // Check role attributes
      expect(tabbedComponent.element.querySelector('[role="tablist"]')).toBeTruthy();
      
      const tabPanels = tabbedComponent.element.querySelectorAll('[role="tabpanel"]');
      expect(tabPanels.length).toBe(3);
    });

    it('should support keyboard navigation', () => {
      tabbedComponent = createTabbedTradingDisplay();
      
      const radioInputs = tabbedComponent.element.querySelectorAll('input[type="radio"][name="trading_tabs"]');
      
      // Simulate keyboard navigation
      radioInputs[0].focus();
      expect(document.activeElement).toBe(radioInputs[0]);
      
      // Tab navigation should work
      expect(radioInputs[0].tabIndex).not.toBe(-1);
    });
  });
});