import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react'; // act is used in tests
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import OrderBookDisplay from './OrderBookDisplay';
import marketDataReducer from '../../features/marketData/marketDataSlice';
import { connectWebSocketStream, disconnectWebSocketStream, disconnectAllWebSockets } from '../../services/websocketService';
import apiClient from '../../services/apiClient';

// Mock websocketService to prevent actual WebSocket connections
jest.mock('../../services/websocketService', () => ({
  connectWebSocketStream: jest.fn(),
  disconnectWebSocketStream: jest.fn(),
  disconnectAllWebSockets: jest.fn(),
}));

export const createMockStore = (initialState = {}) => {
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
        selectedRounding: null,
        availableRoundingOptions: [],
        shouldRestartWebSocketAfterFetch: false,
        displayDepth: 10,
        ...initialState,
      },
    },
  });
};

export interface TestSetup {
  apiClientGetSpy: jest.SpyInstance;
}

export const setupOrderBookTests = (): TestSetup => {
  jest.clearAllMocks();
  // Clear mocks for websocketService
  (connectWebSocketStream as jest.Mock).mockClear();
  (disconnectWebSocketStream as jest.Mock).mockClear();
  (disconnectAllWebSockets as jest.Mock).mockClear();

  // Spy on apiClient.get and set its default mock implementation
  const apiClientGetSpy = jest.spyOn(apiClient, 'get').mockImplementation((url: string) => {
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

  return { apiClientGetSpy };
};

export const cleanupOrderBookTests = (setup: TestSetup) => {
  setup.apiClientGetSpy.mockRestore(); // Restore original implementation after each test
};

// Helper function to render OrderBookDisplay with Provider
export const renderOrderBookDisplay = (store: any) => {
  return render(
    <Provider store={store}>
      <OrderBookDisplay />
    </Provider>
  );
};

// Export commonly used testing utilities
export { render, screen, fireEvent, act, Provider };