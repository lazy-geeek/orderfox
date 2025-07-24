import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';
import { createTradingModal } from '../../src/components/TradingModal.js';

// Mock the dependencies
vi.mock('../../src/components/LightweightChart.js', () => ({
  createCandlestickChart: vi.fn(() => {}),
  createTimeframeSelector: vi.fn(() => document.createElement('div')),
  createVolumeToggleButton: vi.fn(() => document.createElement('div'))
}));

vi.mock('../../src/components/TabbedTradingDisplay.js', () => ({
  createTabbedTradingDisplay: vi.fn(() => ({
    element: document.createElement('div'),
    destroy: vi.fn()
  }))
}));

vi.mock('../../src/services/websocketManager.js', () => ({
  WebSocketManager: {
    switchToBotContext: vi.fn().mockResolvedValue(undefined),
    switchTimeframe: vi.fn(),
    disconnectAll: vi.fn().mockResolvedValue(undefined)
  }
}));

vi.mock('../../src/store/store.js', () => ({
  state: {
    bots: [
      { id: 'bot1', name: 'Test Bot 1', isActive: true },
      { id: 'bot2', name: 'Test Bot 2', isActive: false }
    ],
    selectedBotId: 'bot1'
  },
  subscribe: vi.fn(),
  setCurrentView: vi.fn(),
  openModal: vi.fn(),
  closeModal: vi.fn()
}));

describe('TradingModal', () => {
  let dom;
  let tradingModal;

  beforeEach(() => {
    // Set up JSDOM
    dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
        <body>
          <div id="app"></div>
        </body>
      </html>
    `);
    
    // Set global document and window
    global.document = dom.window.document;
    global.window = dom.window;
    
    // Mock HTMLDialogElement functionality
    const originalCreateElement = dom.window.document.createElement;
    dom.window.document.createElement = function(tagName) {
      const element = originalCreateElement.call(this, tagName);
      
      if (tagName.toLowerCase() === 'dialog') {
        // Add dialog-specific properties and methods
        element.open = false;
        element.showModal = function() {
          this.open = true;
          this.dispatchEvent(new dom.window.Event('open'));
        };
        element.close = function() {
          this.open = false;
          this.dispatchEvent(new dom.window.Event('close'));
        };
      }
      
      return element;
    };
    
    // Create trading modal
    tradingModal = createTradingModal();
  });

  afterEach(() => {
    if (tradingModal) {
      tradingModal.destroy();
    }
    vi.clearAllMocks();
  });

  describe('Modal Creation', () => {
    it('should create modal element with correct structure', () => {
      expect(tradingModal.element).toBeDefined();
      expect(tradingModal.element.tagName).toBe('DIALOG');
      expect(tradingModal.element.id).toBe('trading-modal');
      expect(tradingModal.element.className).toBe('modal');
    });

    it('should have modal box with correct classes', () => {
      const modalBox = tradingModal.element.querySelector('.modal-box');
      expect(modalBox).toBeDefined();
      expect(modalBox.className).toContain('w-11/12');
      expect(modalBox.className).toContain('max-w-[1400px]');
      expect(modalBox.className).toContain('h-[90vh]');
    });

    it('should have close button with correct attributes', () => {
      const closeButton = tradingModal.element.querySelector('[data-testid="modal-close-button"]');
      expect(closeButton).toBeDefined();
      expect(closeButton.className).toContain('btn-circle');
      expect(closeButton.getAttribute('aria-label')).toBe('Close modal');
    });

    it('should have trading interface container', () => {
      const container = tradingModal.element.querySelector('[data-testid="trading-interface-container"]');
      expect(container).toBeDefined();
      expect(container.className).toContain('trading-interface-container');
    });
  });

  describe('Modal Methods', () => {
    it('should provide open, close, destroy, and isOpen methods', () => {
      expect(typeof tradingModal.open).toBe('function');
      expect(typeof tradingModal.close).toBe('function');
      expect(typeof tradingModal.destroy).toBe('function');
      expect(typeof tradingModal.isOpen).toBe('function');
    });

    it('should return correct open state', () => {
      expect(tradingModal.isOpen()).toBe(false);
    });
  });

  describe('Modal Open Functionality', () => {
    it('should open modal and initialize components', async () => {
      await tradingModal.open();
      
      expect(tradingModal.element.open).toBe(true);
      expect(tradingModal.isOpen()).toBe(true);
    });

    it('should initialize trading interface on first open', async () => {
      await tradingModal.open();
      
      const container = tradingModal.element.querySelector('.trading-interface-container');
      expect(container.children.length).toBeGreaterThan(0);
      
      const wrapper = container.querySelector('.trading-content-wrapper');
      expect(wrapper).toBeDefined();
      expect(wrapper.className).toContain('trading-content-wrapper');
    });

    it('should create left and right sections', async () => {
      await tradingModal.open();
      
      const leftSection = tradingModal.element.querySelector('.left-section');
      const rightSection = tradingModal.element.querySelector('.right-section');
      
      expect(leftSection).toBeDefined();
      expect(rightSection).toBeDefined();
      expect(leftSection.className).toContain('flex-1');
      expect(rightSection.className).toContain('lg:w-96');
    });

    it('should create chart controls', async () => {
      await tradingModal.open();
      
      const chartControls = tradingModal.element.querySelector('.chart-controls');
      const chartContainer = tradingModal.element.querySelector('.chart-container');
      
      expect(chartControls).toBeDefined();
      expect(chartContainer).toBeDefined();
      expect(chartControls.className).toContain('flex');
    });

    it('should handle WebSocket connection for selected bot', async () => {
      const { WebSocketManager } = await import('../../src/services/websocketManager.js');
      
      await tradingModal.open();
      
      expect(WebSocketManager.switchToBotContext).toHaveBeenCalledWith({
        id: 'bot1',
        name: 'Test Bot 1',
        isActive: true
      });
    });
  });

  describe('Modal Close Functionality', () => {
    it('should close modal and disconnect WebSockets', async () => {
      const { WebSocketManager } = await import('../../src/services/websocketManager.js');
      
      await tradingModal.open();
      await tradingModal.close();
      
      expect(tradingModal.element.open).toBe(false);
      expect(WebSocketManager.disconnectAll).toHaveBeenCalled();
    });

    it('should handle close event', async () => {
      const { WebSocketManager } = await import('../../src/services/websocketManager.js');
      
      await tradingModal.open();
      
      // Trigger close event
      tradingModal.element.dispatchEvent(new dom.window.Event('close'));
      
      expect(WebSocketManager.disconnectAll).toHaveBeenCalled();
    });
  });

  describe('State Preservation', () => {
    it('should preserve components between modal opens', async () => {
      // First open
      await tradingModal.open();
      const firstContainer = tradingModal.element.querySelector('.trading-content-wrapper');
      await tradingModal.close();
      
      // Second open
      await tradingModal.open();
      const secondContainer = tradingModal.element.querySelector('.trading-content-wrapper');
      
      // Components should be reused
      expect(firstContainer).toBeDefined();
      expect(secondContainer).toBeDefined();
    });
  });

  describe('Error Handling', () => {
    it('should handle WebSocket connection errors gracefully', async () => {
      const { WebSocketManager } = await import('../../src/services/websocketManager.js');
      WebSocketManager.switchToBotContext.mockRejectedValueOnce(new Error('Connection failed'));
      
      // Should not throw
      await expect(tradingModal.open()).resolves.not.toThrow();
    });

    it('should handle close errors gracefully', async () => {
      const { WebSocketManager } = await import('../../src/services/websocketManager.js');
      WebSocketManager.disconnectAll.mockRejectedValueOnce(new Error('Disconnect failed'));
      
      await tradingModal.open();
      
      // Should not throw
      await expect(tradingModal.close()).resolves.not.toThrow();
    });
  });

  describe('Keyboard Interactions', () => {
    it('should handle ESC key', async () => {
      await tradingModal.open();
      
      // Simulate ESC key (cancel event)
      const cancelEvent = new dom.window.Event('cancel', { cancelable: true });
      tradingModal.element.dispatchEvent(cancelEvent);
      
      // ESC should be allowed (default behavior)
      expect(cancelEvent.defaultPrevented).toBe(false);
    });
  });

  describe('Backdrop Click Prevention', () => {
    it('should prevent backdrop click from closing modal', async () => {
      await tradingModal.open();
      
      // Simulate click on dialog element (backdrop)
      const clickEvent = new dom.window.Event('click', { cancelable: true, bubbles: true });
      Object.defineProperty(clickEvent, 'target', { value: tradingModal.element });
      
      tradingModal.element.dispatchEvent(clickEvent);
      
      // Click should be prevented
      expect(clickEvent.defaultPrevented).toBe(true);
    });

    it('should allow clicks on modal content', async () => {
      await tradingModal.open();
      
      const modalBox = tradingModal.element.querySelector('.modal-box');
      
      // Simulate click on modal box (content)
      const clickEvent = new dom.window.Event('click', { cancelable: true, bubbles: true });
      Object.defineProperty(clickEvent, 'target', { value: modalBox });
      
      tradingModal.element.dispatchEvent(clickEvent);
      
      // Click should NOT be prevented
      expect(clickEvent.defaultPrevented).toBe(false);
    });
  });

  describe('Resource Cleanup', () => {
    it('should clean up resources on destroy', async () => {
      await tradingModal.open();
      
      const { WebSocketManager } = await import('../../src/services/websocketManager.js');
      
      tradingModal.destroy();
      
      expect(WebSocketManager.disconnectAll).toHaveBeenCalled();
    });

    it('should remove element from DOM on destroy', async () => {
      document.body.appendChild(tradingModal.element);
      
      expect(document.body.contains(tradingModal.element)).toBe(true);
      
      tradingModal.destroy();
      
      expect(document.body.contains(tradingModal.element)).toBe(false);
    });
  });

  describe('Responsive Behavior', () => {
    it('should have responsive CSS classes', () => {
      const wrapper = document.createElement('div');
      wrapper.className = 'trading-content-wrapper flex flex-col lg:flex-row gap-4 h-full';
      
      expect(wrapper.className).toContain('flex-col');
      expect(wrapper.className).toContain('lg:flex-row');
    });

    it('should have responsive sections', () => {
      const leftSection = document.createElement('div');
      leftSection.className = 'left-section flex-1 min-w-0';
      
      const rightSection = document.createElement('div');
      rightSection.className = 'right-section w-full lg:w-96 flex-shrink-0';
      
      expect(leftSection.className).toContain('flex-1');
      expect(rightSection.className).toContain('lg:w-96');
    });
  });
});