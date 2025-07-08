/**
 * Tests for LastTradesDisplay component.
 * 
 * This module contains unit tests for the Last Trades display functionality,
 * testing component creation, trade updates, and color coding logic.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { 
  createLastTradesDisplay, 
  updateLastTradesDisplay, 
  updateTradesHeaders,
  updateLastTradesData,
  updateTradesConnectionStatus 
} from '../../src/components/LastTradesDisplay.js';

describe('LastTradesDisplay', () => {
  beforeEach(() => {
    // Create a fresh DOM environment for each test
    document.body.innerHTML = '<div id="last-trades-container"></div>';
  });

  describe('Component Creation', () => {
    it('should create trades display structure', () => {
      const container = createLastTradesDisplay();
      
      // Check basic structure
      expect(container).toBeTruthy();
      expect(container.className).toBe('order-book-display orderfox-last-trades-display');
      
      // Check header structure
      const header = container.querySelector('.order-book-header');
      expect(header).toBeTruthy();
      expect(header.querySelector('h3').textContent).toBe('Trades');
      
      // Check connection status elements
      const statusIndicator = container.querySelector('.status-indicator');
      const statusText = container.querySelector('.status-text');
      expect(statusIndicator).toBeTruthy();
      expect(statusText).toBeTruthy();
      expect(statusIndicator.textContent).toBe('○');
      expect(statusText.textContent).toBe('Disconnected');
      
      // Check section headers (uses span elements like OrderBookDisplay)
      const priceHeader = container.querySelector('#trades-price-header');
      const amountHeader = container.querySelector('#trades-amount-header');
      const timeHeader = container.querySelector('.time-header');
      
      expect(priceHeader).toBeTruthy();
      expect(priceHeader.textContent).toBe('Price');
      expect(amountHeader).toBeTruthy();
      expect(amountHeader.textContent).toBe('Amount');
      expect(timeHeader).toBeTruthy();
      expect(timeHeader.textContent).toBe('Time');
      
      // Check trades list container
      const tradesList = container.querySelector('#trades-list');
      expect(tradesList).toBeTruthy();
    });

    it('should have correct DOM structure with IDs', () => {
      const container = createLastTradesDisplay();
      
      // Check for specific IDs needed for updates
      expect(container.querySelector('#trades-price-header')).toBeTruthy();
      expect(container.querySelector('#trades-amount-header')).toBeTruthy();
      expect(container.querySelector('#trades-list')).toBeTruthy();
    });
  });

  describe('Trade Updates', () => {
    it('should update trades with correct colors for buy/sell', () => {
      const container = createLastTradesDisplay();
      document.body.appendChild(container);
      
      const mockState = {
        selectedSymbol: 'BTCUSDT',
        currentTrades: [
          {
            id: '1',
            side: 'buy',
            price_formatted: '108,905.1',
            amount_formatted: '0.240',
            time_formatted: '13:25:57'
          },
          {
            id: '2',
            side: 'sell',
            price_formatted: '108,904.0',
            amount_formatted: '0.100',
            time_formatted: '13:25:56'
          }
        ],
        tradesWsConnected: true,
        tradesLoading: false
      };
      
      updateLastTradesDisplay(container, mockState);
      
      const rows = container.querySelectorAll('.trade-level');
      expect(rows).toHaveLength(2);
      
      // Check buy trade (should have bid-price class for green color)
      const buyTrade = rows[0];
      const buyPriceElement = buyTrade.querySelector('.price');
      expect(buyPriceElement.classList.contains('bid-price')).toBe(true);
      expect(buyPriceElement.textContent).toBe('108,905.1');
      
      // Check sell trade (should have ask-price class for red color)
      const sellTrade = rows[1];
      const sellPriceElement = sellTrade.querySelector('.price');
      expect(sellPriceElement.classList.contains('ask-price')).toBe(true);
      expect(sellPriceElement.textContent).toBe('108,904.0');
    });

    it('should display loading state when tradesLoading is true', () => {
      const container = createLastTradesDisplay();
      document.body.appendChild(container);
      
      const mockState = {
        selectedSymbol: 'BTCUSDT',
        currentTrades: [],
        tradesWsConnected: false,
        tradesLoading: true
      };
      
      updateLastTradesDisplay(container, mockState);
      
      const tradesList = container.querySelector('#trades-list');
      expect(tradesList.innerHTML).toContain('Loading trades...');
    });

    it('should display empty state when no trades available', () => {
      const container = createLastTradesDisplay();
      document.body.appendChild(container);
      
      const mockState = {
        selectedSymbol: 'BTCUSDT',
        currentTrades: [],
        tradesWsConnected: true,
        tradesLoading: false
      };
      
      updateLastTradesDisplay(container, mockState);
      
      const tradesList = container.querySelector('#trades-list');
      expect(tradesList.innerHTML).toContain('No trades data');
    });

    it('should update connection status correctly', () => {
      const container = createLastTradesDisplay();
      document.body.appendChild(container);
      
      // Test connected state
      const connectedState = {
        selectedSymbol: 'BTCUSDT',
        currentTrades: [],
        tradesWsConnected: true,
        tradesLoading: false
      };
      
      updateLastTradesDisplay(container, connectedState);
      
      const statusIndicator = container.querySelector('.status-indicator');
      const statusText = container.querySelector('.status-text');
      
      expect(statusIndicator.classList.contains('connected')).toBe(true);
      expect(statusIndicator.textContent).toBe('●');
      expect(statusText.textContent).toBe('Live');
      
      // Test disconnected state
      const disconnectedState = {
        ...connectedState,
        tradesWsConnected: false
      };
      
      updateLastTradesDisplay(container, disconnectedState);
      
      expect(statusIndicator.classList.contains('disconnected')).toBe(true);
      expect(statusIndicator.textContent).toBe('○');
      expect(statusText.textContent).toBe('Disconnected');
    });
  });

  describe('Header Updates', () => {
    it('should update column headers with currency labels', () => {
      const container = createLastTradesDisplay();
      document.body.appendChild(container);
      
      const symbolData = {
        baseAsset: 'BTC',
        quoteAsset: 'USDT'
      };
      
      updateTradesHeaders(symbolData);
      
      const priceHeader = container.querySelector('#trades-price-header');
      const amountHeader = container.querySelector('#trades-amount-header');
      
      expect(priceHeader.textContent).toBe('Price (USDT)');
      expect(amountHeader.textContent).toBe('Amount (BTC)');
    });

    it('should handle missing symbol data gracefully', () => {
      const container = createLastTradesDisplay();
      document.body.appendChild(container);
      
      // Test with null symbol data
      updateTradesHeaders(null);
      
      const priceHeader = container.querySelector('#trades-price-header');
      const amountHeader = container.querySelector('#trades-amount-header');
      
      // Headers should remain as default
      expect(priceHeader.textContent).toBe('Price');
      expect(amountHeader.textContent).toBe('Amount');
      
      // Test with incomplete symbol data
      updateTradesHeaders({ baseAsset: 'BTC' }); // Missing quoteAsset
      
      expect(amountHeader.textContent).toBe('Amount (BTC)');
      expect(priceHeader.textContent).toBe('Price'); // Should remain unchanged
    });
  });

  describe('Direct Update Functions', () => {
    it('should update trades data directly via updateLastTradesData', () => {
      const container = createLastTradesDisplay();
      document.body.appendChild(container);
      
      const trades = [
        {
          id: '1',
          side: 'buy',
          price_formatted: '50,000.00',
          amount_formatted: '1.500',
          time_formatted: '12:30:45'
        }
      ];
      
      updateLastTradesData(trades);
      
      const rows = container.querySelectorAll('.trade-level');
      expect(rows).toHaveLength(1);
      
      const row = rows[0];
      expect(row.querySelector('.price').textContent).toBe('50,000.00');
      expect(row.querySelector('.amount').textContent).toBe('1.500');
      expect(row.querySelector('.time').textContent).toBe('12:30:45');
    });

    it('should handle empty trades array in updateLastTradesData', () => {
      const container = createLastTradesDisplay();
      document.body.appendChild(container);
      
      updateLastTradesData([]);
      
      const tradesList = container.querySelector('#trades-list');
      expect(tradesList.innerHTML).toContain('No trades data');
    });

    it('should update connection status via updateTradesConnectionStatus', () => {
      const container = createLastTradesDisplay();
      container.classList.add('orderfox-last-trades-display');
      document.body.appendChild(container);
      
      // Test connected status
      updateTradesConnectionStatus(true);
      
      const statusIndicator = container.querySelector('.status-indicator');
      const statusText = container.querySelector('.status-text');
      
      expect(statusIndicator.classList.contains('connected')).toBe(true);
      expect(statusText.textContent).toBe('Live');
      
      // Test disconnected status
      updateTradesConnectionStatus(false);
      
      expect(statusIndicator.classList.contains('disconnected')).toBe(true);
      expect(statusText.textContent).toBe('Disconnected');
    });
  });

  describe('Trade Formatting', () => {
    it('should display all trade fields correctly', () => {
      const container = createLastTradesDisplay();
      document.body.appendChild(container);
      
      const mockTrade = {
        id: 'test123',
        side: 'buy',
        price_formatted: '1,234.56',
        amount_formatted: '0.123456',
        time_formatted: '14:30:25'
      };
      
      updateLastTradesData([mockTrade]);
      
      const row = container.querySelector('.trade-level');
      const cells = row.querySelectorAll('span');
      
      expect(cells[0].textContent).toBe('1,234.56'); // Price
      expect(cells[1].textContent).toBe('0.123456'); // Amount
      expect(cells[2].textContent).toBe('14:30:25'); // Time
    });

    it('should apply correct CSS classes for styling', () => {
      const container = createLastTradesDisplay();
      document.body.appendChild(container);
      
      const trades = [
        {
          id: '1',
          side: 'buy',
          price_formatted: '100.00',
          amount_formatted: '1.000',
          time_formatted: '12:00:00'
        },
        {
          id: '2',
          side: 'sell',
          price_formatted: '99.00',
          amount_formatted: '2.000',
          time_formatted: '12:00:01'
        }
      ];
      
      updateLastTradesData(trades);
      
      const rows = container.querySelectorAll('.trade-level');
      
      // Buy trade should have bid-price class
      const buyRow = rows[0];
      expect(buyRow.querySelector('.price').classList.contains('bid-price')).toBe(true);
      expect(buyRow.querySelector('.amount').classList.contains('bid-price')).toBe(true);
      
      // Sell trade should have ask-price class  
      const sellRow = rows[1];
      expect(sellRow.querySelector('.price').classList.contains('ask-price')).toBe(true);
      expect(sellRow.querySelector('.amount').classList.contains('ask-price')).toBe(true);
      
      // Time should not have color class
      expect(buyRow.querySelector('.time').classList.contains('bid-price')).toBe(false);
      expect(sellRow.querySelector('.time').classList.contains('ask-price')).toBe(false);
    });
  });

  describe('Symbol Updates', () => {
    it('should update symbol label when symbol changes', () => {
      const container = createLastTradesDisplay();
      document.body.appendChild(container);
      
      const mockState = {
        selectedSymbol: 'ETHUSDT',
        currentTrades: [],
        tradesWsConnected: false,
        tradesLoading: false
      };
      
      updateLastTradesDisplay(container, mockState);
      
      const symbolLabel = container.querySelector('.symbol-label');
      expect(symbolLabel.textContent).toBe('ETHUSDT');
    });
  });
});