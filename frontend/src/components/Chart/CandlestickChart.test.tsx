import React from 'react';
import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import CandlestickChart from './CandlestickChart';
import marketDataReducer from '../../features/marketData/marketDataSlice';

// Mock apiClient
jest.mock('../../services/apiClient', () => ({
  get: jest.fn()
}));

// Mock echarts-for-react to avoid rendering issues in tests
jest.mock('echarts-for-react', () => {
  return function MockReactECharts() {
    return <div data-testid="echarts-mock">Chart Component</div>;
  };
});

// Mock WebSocket completely
(global as any).WebSocket = jest.fn().mockImplementation(() => ({
  close: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  onopen: null,
  onmessage: null,
  onerror: null,
  onclose: null,
}));

const createMockStore = (marketDataState: any) => {
  return configureStore({
    reducer: {
      marketData: marketDataReducer,
    },
    preloadedState: {
      marketData: marketDataState,
    },
  });
};

describe('CandlestickChart', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders no symbol selected state when selectedSymbol is null', () => {
    const store = createMockStore({
      selectedSymbol: null,
      currentCandles: [],
      isLoading: false,
      error: null,
      symbolsList: [],
      currentOrderBook: null,
      symbolsLoading: false,
      symbolsError: null,
      selectedRounding: null,
      availableRoundingOptions: [],
    });

    render(
      <Provider store={store}>
        <CandlestickChart />
      </Provider>
    );

    expect(screen.getByText('Please select a symbol to view the chart')).toBeInTheDocument();
  });

  it('renders error state when error exists', () => {
    const store = createMockStore({
      selectedSymbol: null, // Set to null to avoid dispatching actions
      currentCandles: [],
      isLoading: false,
      error: 'Failed to fetch data',
      symbolsList: [],
      currentOrderBook: null,
      symbolsLoading: false,
      symbolsError: null,
      selectedRounding: null,
      availableRoundingOptions: [],
    });

    render(
      <Provider store={store}>
        <CandlestickChart />
      </Provider>
    );

    expect(screen.getByText('Error loading chart data')).toBeInTheDocument();
    expect(screen.getByText('API Error: Failed to fetch data')).toBeInTheDocument();
  });

  it('renders component without crashing with valid data', () => {
    const mockCandles = [
      {
        timestamp: 1640995200000,
        open: 50000,
        high: 51000,
        low: 49000,
        close: 50500,
        volume: 1000,
      },
    ];

    const store = createMockStore({
      selectedSymbol: 'BTCUSDT',
      currentCandles: mockCandles,
      isLoading: false,
      error: null,
      symbolsList: [],
      currentOrderBook: null,
      symbolsLoading: false,
      symbolsError: null,
    });

    // Should not throw an error
    expect(() => {
      render(
        <Provider store={store}>
          <CandlestickChart />
        </Provider>
      );
    }).not.toThrow();
  });

  it('handles edge case with empty candles array', () => {
    const store = createMockStore({
      selectedSymbol: 'BTCUSDT',
      currentCandles: [],
      isLoading: false,
      error: null,
      symbolsList: [],
      currentOrderBook: null,
      symbolsLoading: false,
      symbolsError: null,
    });

    // Should not throw an error
    expect(() => {
      render(
        <Provider store={store}>
          <CandlestickChart />
        </Provider>
      );
    }).not.toThrow();
  });

  it('fails gracefully with invalid candle data', () => {
    const invalidCandles = [
      {
        timestamp: null as any,
        open: 'invalid' as any,
        high: undefined as any,
        low: 49000,
        close: 50500,
        volume: 1000,
      },
    ];

    const store = createMockStore({
      selectedSymbol: 'BTCUSDT',
      currentCandles: invalidCandles,
      isLoading: false,
      error: null,
      symbolsList: [],
      currentOrderBook: null,
      symbolsLoading: false,
      symbolsError: null,
    });

    // Should not throw an error
    expect(() => {
      render(
        <Provider store={store}>
          <CandlestickChart />
        </Provider>
      );
    }).not.toThrow();
  });
});