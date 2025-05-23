import React from 'react';
import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import OrderBookDisplay from './OrderBookDisplay';
import marketDataReducer from '../../features/marketData/marketDataSlice';

// Mock apiClient to prevent actual API calls
jest.mock('../../services/apiClient', () => ({
  get: jest.fn().mockResolvedValue({ data: {} })
}));

// Mock WebSocket completely to prevent connection attempts
const mockWebSocket = {
  close: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  onopen: null,
  onmessage: null,
  onerror: null,
  onclose: null,
  readyState: 1,
};

(global as any).WebSocket = jest.fn().mockImplementation(() => mockWebSocket);

// Mock React hooks to prevent side effects during testing
const mockUseEffect = jest.fn();
jest.mock('react', () => ({
  ...jest.requireActual('react'),
  useEffect: (fn: any, deps: any) => {
    // Only run effects that don't have selectedSymbol dependency to avoid async actions
    if (!deps || !deps.some((dep: any) => typeof dep === 'string')) {
      return jest.requireActual('react').useEffect(fn, deps);
    }
    return mockUseEffect(fn, deps);
  },
}));

const createMockStore = (initialState = {}) => {
  return configureStore({
    reducer: {
      marketData: marketDataReducer,
    },
    preloadedState: {
      marketData: {
        selectedSymbol: null,
        symbolsList: [],
        currentOrderBook: null,
        currentCandles: [],
        isLoading: false,
        error: null,
        symbolsLoading: false,
        symbolsError: null,
        ...initialState,
      },
    },
  });
};

describe('OrderBookDisplay', () => {
  beforeEach(() => {
    jest.clearAllMocks();
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

  it('renders order book data when available', () => {
    const mockOrderBook = {
      symbol: 'BTCUSDT',
      bids: [
        { price: 50000, amount: 1.5 },
        { price: 49999, amount: 2.0 },
      ],
      asks: [
        { price: 50001, amount: 1.2 },
        { price: 50002, amount: 1.8 },
      ],
      timestamp: Date.now(),
    };

    const store = createMockStore({
      selectedSymbol: 'BTCUSDT',
      currentOrderBook: mockOrderBook,
      isLoading: false,
    });
    
    render(
      <Provider store={store}>
        <OrderBookDisplay />
      </Provider>
    );

    expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
    expect(screen.getByText('50000')).toBeInTheDocument();
    expect(screen.getByText('50001')).toBeInTheDocument();
    expect(screen.getAllByText('1.5')).toHaveLength(2); // amount and total
    expect(screen.getAllByText('1.2')).toHaveLength(2); // amount and total for asks
  });

  it('displays spread information when both bids and asks are available', () => {
    const mockOrderBook = {
      symbol: 'BTCUSDT',
      bids: [{ price: 50000, amount: 1.5 }],
      asks: [{ price: 50001, amount: 1.2 }],
      timestamp: Date.now(),
    };

    const store = createMockStore({
      selectedSymbol: 'BTCUSDT',
      currentOrderBook: mockOrderBook,
      isLoading: false,
    });
    
    render(
      <Provider store={store}>
        <OrderBookDisplay />
      </Provider>
    );

    expect(screen.getByText('Spread:')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument(); // spread value
  });

  it('renders depth selector with default value', () => {
    const store = createMockStore({
      selectedSymbol: 'BTCUSDT',
      currentOrderBook: {
        symbol: 'BTCUSDT',
        bids: [{ price: 50000, amount: 1.5 }],
        asks: [{ price: 50001, amount: 1.2 }],
        timestamp: Date.now(),
      },
      isLoading: false,
    });
    
    render(
      <Provider store={store}>
        <OrderBookDisplay />
      </Provider>
    );

    expect(screen.getByText('Display Depth:')).toBeInTheDocument();
    // Check for the select element with value 10
    const selectElement = screen.getByRole('combobox');
    expect(selectElement).toHaveValue('10');
  });

  it('renders component without crashing', () => {
    const store = createMockStore();
    
    expect(() => {
      render(
        <Provider store={store}>
          <OrderBookDisplay />
        </Provider>
      );
    }).not.toThrow();
  });
});