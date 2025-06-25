import React from 'react';
import { render, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import OrderBookDisplay from './OrderBookDisplay';
import marketDataReducer from '../../features/marketData/marketDataSlice';

// Mock the websocket service
jest.mock('../../services/websocketService', () => ({
  connectWebSocketStream: jest.fn(),
  disconnectWebSocketStream: jest.fn(),
  disconnectAllWebSockets: jest.fn(),
}));

// Mock the API client
jest.mock('../../services/apiClient', () => ({
  get: jest.fn(),
}));

describe('OrderBookDisplay - Initial Connection', () => {
  let store: any;
  let mockDispatch: jest.SpyInstance;

  beforeEach(() => {
    store = configureStore({
      reducer: {
        marketData: marketDataReducer,
      },
      preloadedState: {
        marketData: {
          selectedSymbol: 'BTCUSDT',
          symbolsList: [
            {
              id: 'BTCUSDT',
              symbol: 'BTCUSDT',
              baseAsset: 'BTC',
              quoteAsset: 'USDT',
              uiName: 'BTC/USDT',
              pricePrecision: 2,
            },
          ],
          symbolsLoading: false,
          symbolsError: null,
          currentOrderBook: null, // No existing orderbook data
          orderBookLoading: false,
          orderBookError: null,
          orderBookWsConnected: true, // WebSocket just connected
          currentTicker: null,
          tickerWsConnected: false,
          tickerError: null,
          selectedRounding: 0.01,
          availableRoundingOptions: [0.01, 0.1, 1],
          displayDepth: 10,
          currentCandles: [],
          candlesLoading: false,
          candlesError: null,
          candlesWsConnected: false,
          selectedTimeframe: '1m',
          shouldRestartWebSocketAfterFetch: false,
        },
      },
    });
    
    mockDispatch = jest.spyOn(store, 'dispatch');
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  test('should not stop WebSocket on initial load when no existing orderbook data', () => {
    render(
      <Provider store={store}>
        <OrderBookDisplay />
      </Provider>
    );

    // Should NOT dispatch stopOrderBookWebSocket or setShouldRestartWebSocketAfterFetch
    // when there's no existing orderbook data
    expect(mockDispatch).not.toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'marketData/stopOrderBookWebSocket/pending',
      })
    );
    
    expect(mockDispatch).not.toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'marketData/setShouldRestartWebSocketAfterFetch',
        payload: true,
      })
    );

    // Should set available rounding options (this is normal behavior)
    expect(mockDispatch).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'marketData/setAvailableRoundingOptions',
      })
    );
  });

  test('should stop and restart WebSocket when existing orderbook data present', () => {
    // Update store with existing orderbook data
    store = configureStore({
      reducer: {
        marketData: marketDataReducer,
      },
      preloadedState: {
        marketData: {
          selectedSymbol: 'BTCUSDT',
          symbolsList: [
            {
              id: 'BTCUSDT',
              symbol: 'BTCUSDT',
              baseAsset: 'BTC',
              quoteAsset: 'USDT',
              uiName: 'BTC/USDT',
              pricePrecision: 2,
            },
          ],
          symbolsLoading: false,
          symbolsError: null,
          currentOrderBook: {
            symbol: 'BTCUSDT',
            bids: [{ price: 50000, amount: 1.5 }],
            asks: [{ price: 50100, amount: 2.0 }],
            timestamp: Date.now(),
          },
          orderBookLoading: false,
          orderBookError: null,
          orderBookWsConnected: true,
          currentTicker: null,
          tickerWsConnected: false,
          tickerError: null,
          selectedRounding: 0.1, // Different rounding to trigger useEffect
          availableRoundingOptions: [0.01, 0.1, 1],
          displayDepth: 10,
          currentCandles: [],
          candlesLoading: false,
          candlesError: null,
          candlesWsConnected: false,
          selectedTimeframe: '1m',
          shouldRestartWebSocketAfterFetch: false,
        },
      },
    });

    mockDispatch = jest.spyOn(store, 'dispatch');

    render(
      <Provider store={store}>
        <OrderBookDisplay />
      </Provider>
    );

    // Should set restart flag when existing data is present
    expect(mockDispatch).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'marketData/setShouldRestartWebSocketAfterFetch',
        payload: true,
      })
    );

    // Should dispatch a thunk function (stopOrderBookWebSocket)
    const thunkCalls = mockDispatch.mock.calls.filter(call => typeof call[0] === 'function');
    expect(thunkCalls.length).toBeGreaterThan(0);
  });
});