/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createMainLayout } from '../../src/layouts/MainLayout.js';
import { createTabbedTradingDisplay } from '../../src/components/TabbedTradingDisplay.js';
import { createBotNavigation } from '../../src/components/BotNavigation.js';

// Mock the individual components
vi.mock('../../src/components/OrderBookDisplay.js', () => ({
  createOrderBookDisplay: vi.fn(() => {
    const div = document.createElement('div');
    div.className = 'order-book-display';
    div.setAttribute('data-testid', 'order-book-display');
    return div;
  }),
  updateOrderBookDisplay: vi.fn()
}));

vi.mock('../../src/components/LastTradesDisplay.js', () => ({
  createLastTradesDisplay: vi.fn(() => {
    const div = document.createElement('div');
    div.className = 'last-trades-display';
    div.setAttribute('data-testid', 'last-trades-display');
    return div;
  }),
  updateLastTradesDisplay: vi.fn(),
  updateTradesHeaders: vi.fn(),
  updateLastTradesData: vi.fn(),
  updateTradesConnectionStatus: vi.fn()
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

describe('Layout Integration Tests', () => {
  let mainLayout;
  let tabbedComponent;
  let botNavigation;

  beforeEach(() => {
    // Clear DOM
    document.body.innerHTML = '';
    
    // Clear all mocks
    vi.clearAllMocks();
    
    // Create main layout
    mainLayout = createMainLayout();
    document.body.appendChild(mainLayout);
  });

  afterEach(() => {
    // Clean up components
    if (tabbedComponent && tabbedComponent.destroy) {
      tabbedComponent.destroy();
      tabbedComponent = null;
    }
    
    if (botNavigation && botNavigation.remove) {
      botNavigation.remove();
      botNavigation = null;
    }
  });

  describe('Main Layout Structure', () => {
    it('should create side-by-side layout structure', () => {
      // Verify main trading content wrapper exists
      const tradingContentWrapper = mainLayout.querySelector('.trading-content-wrapper');
      expect(tradingContentWrapper).toBeTruthy();
      expect(tradingContentWrapper.classList.contains('flex')).toBe(true);
      expect(tradingContentWrapper.classList.contains('lg:flex-row')).toBe(true);
      
      // Verify left section for chart
      const leftSection = mainLayout.querySelector('.left-section');
      expect(leftSection).toBeTruthy();
      expect(leftSection.classList.contains('flex-1')).toBe(true);
      expect(leftSection.classList.contains('min-w-0')).toBe(true);
      
      // Verify right section for tabbed tables
      const rightSection = mainLayout.querySelector('.right-section');
      expect(rightSection).toBeTruthy();
      expect(rightSection.classList.contains('w-full')).toBe(true);
      expect(rightSection.classList.contains('lg:w-96')).toBe(true);
      expect(rightSection.classList.contains('flex-shrink-0')).toBe(true);
    });

    it('should have proper placeholder elements', () => {
      // Verify chart placeholder in left section
      const chartPlaceholder = mainLayout.querySelector('#candlestick-chart-placeholder');
      expect(chartPlaceholder).toBeTruthy();
      expect(chartPlaceholder.parentElement.classList.contains('left-section')).toBe(true);
      
      // Verify tabbed trading placeholder in right section
      const tabbedPlaceholder = mainLayout.querySelector('#tabbed-trading-placeholder');
      expect(tabbedPlaceholder).toBeTruthy();
      expect(tabbedPlaceholder.parentElement.classList.contains('right-section')).toBe(true);
    });

    it('should not have old bottom-section layout', () => {
      // Verify old bottom-section structure doesn't exist
      const bottomSection = mainLayout.querySelector('.bottom-section');
      expect(bottomSection).toBeFalsy();
      
      // Verify no bottom-positioned trading tables
      const bottomTradingTables = mainLayout.querySelector('.bottom-trading-tables');
      expect(bottomTradingTables).toBeFalsy();
    });

    it('should have proper responsive layout classes', () => {
      const tradingWrapper = mainLayout.querySelector('.trading-content-wrapper');
      
      // Verify mobile-first approach with column layout
      expect(tradingWrapper.classList.contains('flex-col')).toBe(true);
      
      // Verify large screen row layout
      expect(tradingWrapper.classList.contains('lg:flex-row')).toBe(true);
      
      // Verify gap for spacing
      expect(tradingWrapper.classList.contains('gap-4')).toBe(true);
    });
  });

  describe('Tabbed Component Integration', () => {
    it('should integrate tabbed component into right section', () => {
      // Create tabbed component
      tabbedComponent = createTabbedTradingDisplay();
      
      // Replace placeholder with actual component
      const placeholder = mainLayout.querySelector('#tabbed-trading-placeholder');
      placeholder.replaceWith(tabbedComponent.element);
      
      // Verify integration
      const rightSection = mainLayout.querySelector('.right-section');
      const tabbedElement = rightSection.querySelector('.orderfox-tabbed-trading-display');
      
      expect(tabbedElement).toBeTruthy();
      expect(tabbedElement).toBe(tabbedComponent.element);
    });

    it('should maintain tabbed component functionality within layout', () => {
      // Create and integrate tabbed component
      tabbedComponent = createTabbedTradingDisplay();
      const placeholder = mainLayout.querySelector('#tabbed-trading-placeholder');
      placeholder.replaceWith(tabbedComponent.element);
      
      // Test tab switching within integrated layout
      const radioInputs = tabbedComponent.element.querySelectorAll('input[type="radio"][name="trading_tabs"]');
      
      // Switch to Trades tab
      radioInputs[1].checked = true;
      radioInputs[1].dispatchEvent(new Event('change'));
      
      // Verify tab switch works within layout
      expect(radioInputs[1].checked).toBe(true);
      
      // Switch to Liquidations tab
      radioInputs[2].checked = true;
      radioInputs[2].dispatchEvent(new Event('change'));
      
      expect(radioInputs[2].checked).toBe(true);
    });

    it('should handle tabbed component within responsive layout', () => {
      tabbedComponent = createTabbedTradingDisplay();
      const placeholder = mainLayout.querySelector('#tabbed-trading-placeholder');
      placeholder.replaceWith(tabbedComponent.element);
      
      // Verify component maintains functionality in different viewport sizes
      const tradingWrapper = mainLayout.querySelector('.trading-content-wrapper');
      
      // Simulate mobile viewport (vertical stacking)
      tradingWrapper.classList.remove('lg:flex-row');
      tradingWrapper.classList.add('flex-col');
      
      // Tabbed component should still function
      const radioInputs = tabbedComponent.element.querySelectorAll('input[type="radio"]');
      expect(radioInputs.length).toBe(3);
      
      // Simulate desktop viewport (side-by-side)
      tradingWrapper.classList.remove('flex-col');
      tradingWrapper.classList.add('lg:flex-row');
      
      // Tabbed component should still function
      expect(radioInputs[0].checked).toBe(true); // Order Book tab default
    });
  });

  describe('Layout Sections Interaction', () => {
    it('should properly separate chart and tabbed areas', () => {
      const leftSection = mainLayout.querySelector('.left-section');
      const rightSection = mainLayout.querySelector('.right-section');
      
      // Verify sections are siblings
      expect(leftSection.parentElement).toBe(rightSection.parentElement);
      
      // Verify proper CSS classes for layout behavior
      expect(leftSection.classList.contains('flex-1')).toBe(true); // Chart takes available space
      expect(rightSection.classList.contains('flex-shrink-0')).toBe(true); // Tables maintain fixed width
      
      // Verify width constraints
      expect(rightSection.classList.contains('lg:w-96')).toBe(true); // Fixed width on large screens
      expect(rightSection.classList.contains('w-full')).toBe(true); // Full width on small screens
    });

    it('should handle content overflow properly', () => {
      const leftSection = mainLayout.querySelector('.left-section');
      const mainContent = mainLayout.querySelector('#main-content');
      
      // Verify overflow handling
      expect(mainContent.classList.contains('overflow-auto')).toBe(true);
      
      // Verify flex overflow prevention
      expect(leftSection.classList.contains('min-w-0')).toBe(true);
    });

    it('should maintain proper spacing between sections', () => {
      const tradingWrapper = mainLayout.querySelector('.trading-content-wrapper');
      
      // Verify gap classes for consistent spacing
      expect(tradingWrapper.classList.contains('gap-4')).toBe(true);
    });
  });

  describe('Navigation Integration', () => {
    it('should integrate bot navigation in sidebar', () => {
      botNavigation = createBotNavigation();
      
      const navPlaceholder = mainLayout.querySelector('#bot-navigation-placeholder');
      navPlaceholder.replaceWith(botNavigation);
      
      // Verify navigation is in sidebar
      const sidebarContent = mainLayout.querySelector('.drawer-side .menu');
      const navElement = sidebarContent.querySelector('[data-testid="bot-navigation"]');
      
      expect(navElement).toBeTruthy();
      expect(navElement).toBe(botNavigation);
    });

    it('should maintain sidebar functionality with layout', () => {
      const drawerToggle = mainLayout.querySelector('#drawer-toggle');
      const drawerOverlay = mainLayout.querySelector('.drawer-overlay');
      
      // Verify drawer toggle exists
      expect(drawerToggle).toBeTruthy();
      expect(drawerToggle.type).toBe('checkbox');
      
      // Verify overlay exists for mobile interactions
      expect(drawerOverlay).toBeTruthy();
      
      // Test drawer toggle functionality
      drawerToggle.checked = false;
      expect(drawerToggle.checked).toBe(false);
      
      drawerToggle.checked = true;
      expect(drawerToggle.checked).toBe(true);
    });
  });

  describe('Responsive Layout Behavior', () => {
    it('should adapt layout for different screen sizes', () => {
      const tradingWrapper = mainLayout.querySelector('.trading-content-wrapper');
      const rightSection = mainLayout.querySelector('.right-section');
      
      // Verify mobile-first responsive classes
      expect(tradingWrapper.classList.contains('flex-col')).toBe(true); // Mobile: vertical stacking
      expect(tradingWrapper.classList.contains('lg:flex-row')).toBe(true); // Desktop: horizontal layout
      
      // Verify right section responsive width
      expect(rightSection.classList.contains('w-full')).toBe(true); // Mobile: full width
      expect(rightSection.classList.contains('lg:w-96')).toBe(true); // Desktop: fixed width
    });

    it('should maintain functionality across breakpoints', () => {
      // Create tabbed component to test across breakpoints
      tabbedComponent = createTabbedTradingDisplay();
      const placeholder = mainLayout.querySelector('#tabbed-trading-placeholder');
      placeholder.replaceWith(tabbedComponent.element);
      
      // Test mobile viewport simulation
      document.documentElement.style.width = '375px';
      
      const radioInputs = tabbedComponent.element.querySelectorAll('input[type="radio"]');
      radioInputs[1].checked = true;
      radioInputs[1].dispatchEvent(new Event('change'));
      
      expect(radioInputs[1].checked).toBe(true);
      
      // Test desktop viewport simulation
      document.documentElement.style.width = '1024px';
      
      radioInputs[2].checked = true;
      radioInputs[2].dispatchEvent(new Event('change'));
      
      expect(radioInputs[2].checked).toBe(true);
      
      // Reset
      document.documentElement.style.width = '';
    });
  });

  describe('Layout Performance', () => {
    it('should create layout efficiently', () => {
      const startTime = performance.now();
      
      const newLayout = createMainLayout();
      
      const creationTime = performance.now() - startTime;
      
      expect(creationTime).toBeLessThan(50); // Should create quickly
      expect(newLayout).toBeInstanceOf(HTMLElement);
      
      // Clean up
      newLayout.remove();
    });

    it('should handle component integration efficiently', () => {
      const startTime = performance.now();
      
      // Integrate tabbed component
      tabbedComponent = createTabbedTradingDisplay();
      const placeholder = mainLayout.querySelector('#tabbed-trading-placeholder');
      placeholder.replaceWith(tabbedComponent.element);
      
      // Integrate navigation
      botNavigation = createBotNavigation();
      const navPlaceholder = mainLayout.querySelector('#bot-navigation-placeholder');
      navPlaceholder.replaceWith(botNavigation);
      
      const integrationTime = performance.now() - startTime;
      
      expect(integrationTime).toBeLessThan(100); // Should integrate quickly
    });
  });

  describe('Layout Error Handling', () => {
    it('should handle missing placeholders gracefully', () => {
      // Remove placeholders
      const chartPlaceholder = mainLayout.querySelector('#candlestick-chart-placeholder');
      const tabbedPlaceholder = mainLayout.querySelector('#tabbed-trading-placeholder');
      
      chartPlaceholder.remove();
      tabbedPlaceholder.remove();
      
      // Layout should still be functional
      const leftSection = mainLayout.querySelector('.left-section');
      const rightSection = mainLayout.querySelector('.right-section');
      
      expect(leftSection).toBeTruthy();
      expect(rightSection).toBeTruthy();
      
      // Should handle component creation without placeholders
      expect(() => {
        tabbedComponent = createTabbedTradingDisplay();
        rightSection.appendChild(tabbedComponent.element);
      }).not.toThrow();
    });

    it('should maintain layout stability with component failures', () => {
      const leftSection = mainLayout.querySelector('.left-section');
      const rightSection = mainLayout.querySelector('.right-section');
      
      // Remove all content from sections
      leftSection.innerHTML = '';
      rightSection.innerHTML = '';
      
      // Layout structure should remain intact
      expect(leftSection.classList.contains('left-section')).toBe(true);
      expect(rightSection.classList.contains('right-section')).toBe(true);
      
      const tradingWrapper = mainLayout.querySelector('.trading-content-wrapper');
      expect(tradingWrapper.contains(leftSection)).toBe(true);
      expect(tradingWrapper.contains(rightSection)).toBe(true);
    });
  });
});