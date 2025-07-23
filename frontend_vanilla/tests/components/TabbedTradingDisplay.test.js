/**
 * @jest-environment jsdom
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createTabbedTradingDisplay } from '../../src/components/TabbedTradingDisplay.js';

// Mock the individual components
vi.mock('../../src/components/OrderBookDisplay.js', () => ({
  createOrderBookDisplay: vi.fn(() => {
    const div = document.createElement('div');
    div.className = 'order-book-display';
    return div;
  }),
  updateOrderBookDisplay: vi.fn()
}));

vi.mock('../../src/components/LastTradesDisplay.js', () => ({
  createLastTradesDisplay: vi.fn(() => {
    const div = document.createElement('div');
    div.className = 'last-trades-display';
    return div;
  }),
  updateLastTradesDisplay: vi.fn(),
  updateTradesHeaders: vi.fn(),
  updateLastTradesData: vi.fn(),
  updateTradesConnectionStatus: vi.fn()
}));

vi.mock('../../src/components/LiquidationDisplay.js', () => ({
  LiquidationDisplay: vi.fn().mockImplementation(() => ({
    element: document.createElement('div'),
    cleanup: vi.fn()
  }))
}));

describe('TabbedTradingDisplay', () => {
  let component;

  beforeEach(() => {
    // Clear all mocks before each test
    vi.clearAllMocks();
  });

  afterEach(() => {
    // Clean up component if it exists
    if (component && component.destroy) {
      component.destroy();
      component = null;
    }
  });

  describe('Component Creation', () => {
    it('should create component with correct DOM structure', () => {
      component = createTabbedTradingDisplay();
      
      expect(component).toBeDefined();
      expect(component.element).toBeInstanceOf(HTMLElement);
      expect(component.destroy).toBeInstanceOf(Function);
    });

    it('should have correct CSS classes', () => {
      component = createTabbedTradingDisplay();
      
      expect(component.element.classList.contains('orderfox-display-base')).toBe(true);
      expect(component.element.classList.contains('orderfox-tabbed-trading-display')).toBe(true);
    });

    it('should create three radio input tabs', () => {
      component = createTabbedTradingDisplay();
      
      const radioInputs = component.element.querySelectorAll('input[type="radio"][name="trading_tabs"]');
      expect(radioInputs.length).toBe(3);
    });

    it('should have correct aria-labels for tabs', () => {
      component = createTabbedTradingDisplay();
      
      const radioInputs = component.element.querySelectorAll('input[type="radio"][name="trading_tabs"]');
      const labels = Array.from(radioInputs).map(input => input.getAttribute('aria-label'));
      
      expect(labels).toEqual(['Order Book', 'Trades', 'Liquidations']);
    });

    it('should have first tab (Order Book) checked by default', () => {
      component = createTabbedTradingDisplay();
      
      const radioInputs = component.element.querySelectorAll('input[type="radio"][name="trading_tabs"]');
      expect(radioInputs[0].checked).toBe(true);
      expect(radioInputs[1].checked).toBe(false);
      expect(radioInputs[2].checked).toBe(false);
    });

    it('should create three tab-content divs', () => {
      component = createTabbedTradingDisplay();
      
      const tabContents = component.element.querySelectorAll('.tab-content');
      expect(tabContents.length).toBe(3);
    });

    it('should create placeholder divs with correct IDs', () => {
      component = createTabbedTradingDisplay();
      
      expect(component.element.querySelector('#orderbook-placeholder')).toBeTruthy();
      expect(component.element.querySelector('#trades-placeholder')).toBeTruthy();
      expect(component.element.querySelector('#liquidations-placeholder')).toBeTruthy();
    });
  });

  describe('Tab Switching Functionality', () => {
    it('should switch tabs when radio input is changed', () => {
      component = createTabbedTradingDisplay();
      
      const radioInputs = component.element.querySelectorAll('input[type="radio"][name="trading_tabs"]');
      
      // Switch to Trades tab
      radioInputs[1].checked = true;
      radioInputs[1].dispatchEvent(new Event('change'));
      
      expect(radioInputs[1].checked).toBe(true);
    });
  });

  describe('Destroy Method Cleanup', () => {
    it('should have destroy method', () => {
      component = createTabbedTradingDisplay();
      expect(component.destroy).toBeInstanceOf(Function);
    });

    it('should not throw when destroy is called', () => {
      component = createTabbedTradingDisplay();
      
      expect(() => {
        component.destroy();
      }).not.toThrow();
    });
  });

  describe('Error Handling', () => {
    it('should handle unknown tab names gracefully', () => {
      component = createTabbedTradingDisplay();
      
      // Create a fake radio input with unknown tab name
      const fakeRadio = document.createElement('input');
      fakeRadio.type = 'radio';
      fakeRadio.name = 'trading_tabs';
      fakeRadio.setAttribute('aria-label', 'Unknown Tab');
      
      expect(() => {
        fakeRadio.dispatchEvent(new Event('change'));
      }).not.toThrow();
    });

    it('should handle missing placeholders gracefully', () => {
      component = createTabbedTradingDisplay();
      
      // Remove all placeholders
      const placeholders = component.element.querySelectorAll('.component-placeholder');
      placeholders.forEach(placeholder => placeholder.remove());
      
      const radioInputs = component.element.querySelectorAll('input[type="radio"][name="trading_tabs"]');
      
      expect(() => {
        radioInputs[1].checked = true;
        radioInputs[1].dispatchEvent(new Event('change'));
      }).not.toThrow();
    });
  });

  describe('Integration', () => {
    it('should maintain component isolation', () => {
      const component1 = createTabbedTradingDisplay();
      const component2 = createTabbedTradingDisplay();
      
      // Components should be independent
      expect(component1.element).not.toBe(component2.element);
      
      component1.destroy();
      component2.destroy();
    });

    it('should work with multiple instances', () => {
      const components = [];
      
      for (let i = 0; i < 3; i++) {
        components.push(createTabbedTradingDisplay());
      }
      
      // All components should be functional
      components.forEach(comp => {
        expect(comp.element).toBeInstanceOf(HTMLElement);
        expect(comp.destroy).toBeInstanceOf(Function);
      });
      
      // Clean up
      components.forEach(comp => comp.destroy());
    });
  });
});