import React from 'react';
import { render, screen, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import OrderBookDisplay from './OrderBookDisplay';
import marketDataReducer from '../../features/marketData/marketDataSlice';
import { connectWebSocketStream, disconnectWebSocketStream, disconnectAllWebSockets } from '../../services/websocketService'; // Import mocked functions
import apiClient from '../../services/apiClient'; // Import apiClient normally

// Mock websocketService to prevent actual WebSocket connections
jest.mock('../../services/websocketService', () => ({
  connectWebSocketStream: jest.fn(),
  disconnectWebSocketStream: jest.fn(),
  disconnectAllWebSockets: jest.fn(),
}));

const createMockStore = (initialState = {}) => {
  return configureStore({
    reducer: {
      marketData: marketDataReducer,
    },
    preloadedState: {
      marketData: {
        selectedSymbol: null,
        selectedTimeframe: '1m',
        symbolsList: [],
        currentOrderBook: null,
        currentCandles: [],
        candlesLoading: false,
        candlesError: null,
        orderBookLoading: false,
        orderBookError: null,
        symbolsLoading: false,
        symbolsError: null,
        candlesWsConnected: false,
        orderBookWsConnected: false,
        ...initialState,
      },
    },
  });
};

describe('OrderBookDisplay', () => {
  let apiClientGetSpy: jest.SpyInstance;

  beforeEach(() => {
    jest.clearAllMocks();
    // Clear mocks for websocketService
    (connectWebSocketStream as jest.Mock).mockClear();
    (disconnectWebSocketStream as jest.Mock).mockClear();
    (disconnectAllWebSockets as jest.Mock).mockClear();

    // Spy on apiClient.get and set its default mock implementation
    apiClientGetSpy = jest.spyOn(apiClient, 'get').mockImplementation((url: string) => {
      if (url.startsWith('/orderbook/')) {
        const symbol = url.split('/').pop();
        return Promise.resolve({
          data: {
            symbol: symbol,
            bids: [
              { price: 50000, amount: 1.5 },
              { price: 49999, amount: 2.0 },
            ],
            asks: [
              { price: 50001, amount: 1.2 },
              { price: 50002, amount: 1.8 },
            ],
            timestamp: Date.now(),
          },
        });
      }
      return Promise.resolve({ data: {} }); // Default for other API calls
    });
  });

  afterEach(() => {
    apiClientGetSpy.mockRestore(); // Restore original implementation after each test
  });

  it('renders no symbol selected state when no symbol is selected', () => {
    const store = createMockStore();
    
    render(
      <Provider store={store}>
        <OrderBookDisplay />
      </Provider>
    );

    expect(screen.getByText('Order Book')).toBeInTheDocument();
    expect(screen.getByText('Select a symbol to view order book')).toBeInTheDocument();
  });

  it('renders order book data when available', async () => {
    const mockOrderBook = {
      symbol: 'BTCUSDT',
      bids: [
        { price: 50000, amount: 1.5 },
        { price: 49999, amount: 2.0 },
      ],
      asks: [
        { price: 50001, amount: 1.2 },
        { price: 50002, amount: 1.8 },
        { price: 50003, amount: 0.5 },
      ],
      timestamp: Date.now(),
    };

    // Set a specific mock for apiClient.get for this test BEFORE rendering
    apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

    const store = createMockStore({
      selectedSymbol: 'BTCUSDT',
      currentOrderBook: mockOrderBook,
      orderBookLoading: false,
    });
    
    render(
      <Provider store={store}>
        <OrderBookDisplay />
      </Provider>
    );
    // Wait for the async action (fetchOrderBook) to complete
    await screen.findByText('50000'); // Wait for a bid price to appear

    expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
    expect(screen.getByText('50000')).toBeInTheDocument();
    expect(screen.getByText('50001')).toBeInTheDocument();
    // Check for bids amounts and totals
    // Query for elements with class 'amount' and 'total' specifically
    const bid50000Amount = screen.getByText('1.5', { selector: '.bid-level .amount' });
    const bid50000Total = screen.getByText('1.5', { selector: '.bid-level .total' });
    expect(bid50000Amount).toBeInTheDocument();
    expect(bid50000Total).toBeInTheDocument();

    const bid49999Amount = screen.getByText('2', { selector: '.bid-level .amount' });
    const bid49999Total = screen.getByText('3.5', { selector: '.bid-level .total' }); // 1.5 + 2.0
    expect(bid49999Amount).toBeInTheDocument();
    expect(bid49999Total).toBeInTheDocument();

    // Check for asks amounts and totals
    // The asks are reversed, so 50003 (amount 0.5) will be first, then 50002 (amount 1.8), then 50001 (amount 1.2)
    // The total for 50003 is 0.5
    // The total for 50002 is 0.5 + 1.8 = 2.3
    // The total for 50001 is 0.5 + 1.8 + 1.2 = 3.5
    const ask50003Amount = screen.getByText('0.5', { selector: '.ask-level .amount' });
    const ask50003Total = screen.getByText('0.5', { selector: '.ask-level .total' });
    expect(ask50003Amount).toBeInTheDocument();
    expect(ask50003Total).toBeInTheDocument();

    const ask50002Amount = screen.getByText('1.8', { selector: '.ask-level .amount' });
    const ask50002Total = screen.getByText('2.3', { selector: '.ask-level .total' });
    expect(ask50002Amount).toBeInTheDocument();
    expect(ask50002Total).toBeInTheDocument();

    const ask50001Amount = screen.getByText('1.2', { selector: '.ask-level .amount' });
    const ask50001Total = screen.getByText('3.5', { selector: '.ask-level .total' });
    expect(ask50001Amount).toBeInTheDocument();
    expect(ask50001Total).toBeInTheDocument();
  });

  it('displays spread information when both bids and asks are available', async () => {
    const mockOrderBook = {
      symbol: 'BTCUSDT',
      bids: [{ price: 50000, amount: 1.5 }],
      asks: [{ price: 50001, amount: 1.2 }],
      timestamp: Date.now(),
    };

    // Set a specific mock for apiClient.get for this test BEFORE rendering
    apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

    const store = createMockStore({
      selectedSymbol: 'BTCUSDT',
      currentOrderBook: mockOrderBook,
      orderBookLoading: false,
    });
    
    render(
      <Provider store={store}>
        <OrderBookDisplay />
      </Provider>
    );

    // Wait for the async action (fetchOrderBook) to complete
    await screen.findByText('Spread:');

    expect(screen.getByText('Spread:')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument(); // spread value
  });

  it('renders depth selector with default value', async () => {
    const mockOrderBookForDepth = {
      symbol: 'BTCUSDT',
      bids: [{ price: 50000, amount: 1.5 }],
      asks: [{ price: 50001, amount: 1.2 }],
      timestamp: Date.now(),
    };

    // Set a specific mock for apiClient.get for this test BEFORE rendering
    apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBookForDepth });

    const store = createMockStore({
      selectedSymbol: 'BTCUSDT',
      currentOrderBook: mockOrderBookForDepth,
      orderBookLoading: false,
    });
    
    render(
      <Provider store={store}>
        <OrderBookDisplay />
      </Provider>
    );

    // Wait for the async action (fetchOrderBook) to complete
    await screen.findByText('Display Depth:');

    expect(screen.getByText('Display Depth:')).toBeInTheDocument();
    // Check for the select element with value 10
    const selectElement = screen.getByRole('combobox');
    expect(selectElement).toHaveValue('10');
  });


  it('renders component without crashing', () => {
    const store = createMockStore();
    
    render(
      <Provider store={store}>
        <OrderBookDisplay />
      </Provider>
    );
    // No act needed here as no state updates are expected from this render
  });

  it('displays asks in correct order (lowest price at bottom)', async () => {
    const mockOrderBook = {
      symbol: 'BTCUSDT',
      bids: [],
      asks: [
        { price: 50001, amount: 1.2 },
        { price: 50002, amount: 1.8 },
        { price: 50003, amount: 0.5 },
      ],
      timestamp: Date.now(),
    };

    // Set a specific mock for apiClient.get for this test BEFORE rendering
    apiClientGetSpy.mockResolvedValueOnce({ data: mockOrderBook });

    const store = createMockStore({
      selectedSymbol: 'BTCUSDT',
      currentOrderBook: mockOrderBook,
      orderBookLoading: false,
    });
    
    render(
      <Provider store={store}>
        <OrderBookDisplay />
      </Provider>
    );
    // Wait for the async action (fetchOrderBook) to complete
    await screen.findByText('50003'); // Wait for an ask price to appear

    // Query for all elements that display an ask price
    // Query for all elements that display an ask price using text content and then filter by class
    const askPriceElements = screen.getAllByText(/^\d+\.?\d*$/)
                                   .filter(el => el.classList.contains('ask-price'));
    
    const displayedAskPrices = askPriceElements.map(el => parseFloat(el.textContent || '0'));

    // Expect the displayed asks to be in descending order of price (highest at top, lowest at bottom)
    // The original asks array is [50001, 50002, 50003] (lowest to highest)
    // After reverse and slice, it should be [50003, 50002, 50001] for display
    expect(displayedAskPrices).toEqual([50003, 50002, 50001]);
  });
});