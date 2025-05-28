import { configureStore } from '@reduxjs/toolkit';
import apiClient from '../../services/apiClient';
import marketDataReducer, {
  setSelectedSymbol,
  updateOrderBookFromWebSocket,
  updateCandlesFromWebSocket,
  fetchSymbols,
  fetchOrderBook,
  fetchCandles
} from './marketDataSlice';

// Mock apiClient
jest.mock('../../services/apiClient', () => ({
  __esModule: true,
  default: {
    get: jest.fn()
  }
}));

const mockGet = (apiClient as any).get;

type TestStore = ReturnType<typeof configureStore<{
  marketData: ReturnType<typeof marketDataReducer>;
}>>;

describe('marketDataSlice', () => {
  let store: TestStore;

  beforeEach(() => {
    store = configureStore({
      reducer: {
        marketData: marketDataReducer
      }
    });
  });

  describe('reducers', () => {
    test('setSelectedSymbol should update selectedSymbol', () => {
      store.dispatch(setSelectedSymbol('BTCUSDT'));
      expect(store.getState().marketData.selectedSymbol).toBe('BTCUSDT');
    });

    test('setSelectedSymbol should handle null', () => {
      store.dispatch(setSelectedSymbol(null));
      expect(store.getState().marketData.selectedSymbol).toBe(null);
    });

    test('updateOrderBookFromWebSocket should update currentOrderBook', () => {
      const orderBook = {
        symbol: 'BTCUSDT',
        bids: [{ price: 50000, amount: 1.5 }],
        asks: [{ price: 50100, amount: 2.0 }],
        timestamp: Date.now()
      };

      store.dispatch(updateOrderBookFromWebSocket(orderBook));
      expect(store.getState().marketData.currentOrderBook).toEqual(orderBook);
    });

    test('updateCandlesFromWebSocket should append new candle', () => {
      const candle = {
        timestamp: Date.now(),
        open: 50000,
        high: 51000,
        low: 49000,
        close: 50500,
        volume: 100
      };

      store.dispatch(updateCandlesFromWebSocket(candle));
      expect(store.getState().marketData.currentCandles).toHaveLength(1);
      expect(store.getState().marketData.currentCandles[0]).toEqual(candle);
    });

    test('updateCandlesFromWebSocket should update existing candle', () => {
      const timestamp = Date.now();
      const initialCandle = {
        timestamp,
        open: 50000,
        high: 51000,
        low: 49000,
        close: 50500,
        volume: 100
      };

      const updatedCandle = {
        timestamp,
        open: 50000,
        high: 52000,
        low: 49000,
        close: 51500,
        volume: 150
      };

      store.dispatch(updateCandlesFromWebSocket(initialCandle));
      store.dispatch(updateCandlesFromWebSocket(updatedCandle));
      
      expect(store.getState().marketData.currentCandles).toHaveLength(1);
      expect(store.getState().marketData.currentCandles[0]).toEqual(updatedCandle);
    });
  });

  describe('async thunks', () => {
    beforeEach(() => {
      jest.clearAllMocks();
    });

    describe('fetchSymbols', () => {
      test('should handle successful fetch', async () => {
        const mockSymbols = [
          { id: 'BTCUSDT', symbol: 'BTC/USDT' },
          { id: 'ETHUSDT', symbol: 'ETH/USDT' }
        ];
        
        mockGet.mockResolvedValueOnce({ data: mockSymbols });

        await store.dispatch(fetchSymbols());
        
        const state = store.getState().marketData;
        expect(state.symbolsList).toEqual(mockSymbols);
        expect(state.symbolsLoading).toBe(false);
        expect(state.symbolsError).toBe(null);
      });

      test('should handle API error with detail', async () => {
        const errorMessage = 'API service unavailable';
        mockGet.mockRejectedValueOnce({
          response: { data: { detail: errorMessage } }
        });

        await store.dispatch(fetchSymbols());
        
        const state = store.getState().marketData;
        expect(state.symbolsError).toBe(errorMessage);
        expect(state.symbolsLoading).toBe(false);
      });

      test('should handle network error with fallback message', async () => {
        mockGet.mockRejectedValueOnce(new Error('Network error'));

        await store.dispatch(fetchSymbols());
        
        const state = store.getState().marketData;
        expect(state.symbolsError).toBe('Could not load trading symbols. Please try again later.');
        expect(state.symbolsLoading).toBe(false);
      });
    });

    describe('fetchOrderBook', () => {
      test('should handle successful fetch', async () => {
        const mockOrderBook = {
          symbol: 'BTCUSDT',
          bids: [{ price: 50000, amount: 1.5 }],
          asks: [{ price: 50100, amount: 2.0 }],
          timestamp: Date.now()
        };
        
        mockGet.mockResolvedValueOnce({ data: mockOrderBook });

        await store.dispatch(fetchOrderBook('BTCUSDT'));
        
        const state = store.getState().marketData;
        expect(state.currentOrderBook).toEqual(mockOrderBook);
        expect(state.isLoading).toBe(false);
        expect(state.error).toBe(null);
      });

      test('should handle API error', async () => {
        const errorMessage = 'Order book not found';
        mockGet.mockRejectedValueOnce({
          response: { data: { detail: errorMessage } }
        });

        await store.dispatch(fetchOrderBook('INVALID'));
        
        const state = store.getState().marketData;
        expect(state.error).toBe(errorMessage);
        expect(state.isLoading).toBe(false);
      });
    });

    describe('fetchCandles', () => {
      test('should handle successful fetch', async () => {
        const mockCandles = [
          { timestamp: Date.now(), open: 50000, high: 51000, low: 49000, close: 50500, volume: 100 }
        ];
        
        mockGet.mockResolvedValueOnce({ data: mockCandles });

        await store.dispatch(fetchCandles({ symbol: 'BTCUSDT' }));
        
        const state = store.getState().marketData;
        expect(state.currentCandles).toEqual(mockCandles);
        expect(state.isLoading).toBe(false);
        expect(state.error).toBe(null);
      });

      test('should handle API error', async () => {
        const errorMessage = 'Chart data unavailable';
        mockGet.mockRejectedValueOnce({
          response: { data: { detail: errorMessage } }
        });

        await store.dispatch(fetchCandles({ symbol: 'INVALID' }));
        
        const state = store.getState().marketData;
        expect(state.error).toBe(errorMessage);
        expect(state.isLoading).toBe(false);
      });

      test('should handle fetch with invalid candle data', async () => {
        const mockInvalidCandles = [
          { timestamp: Date.now(), open: 50000, high: 51000, low: 49000, close: 50500, volume: 100 },
          { timestamp: null, open: 'invalid', high: undefined, low: 49000, close: 50500, volume: 100 },
          { timestamp: Date.now(), open: 52000, high: 53000, low: 51000, close: 52500, volume: 200 }
        ];
        
        mockGet.mockResolvedValueOnce({ data: mockInvalidCandles });

        await store.dispatch(fetchCandles({ symbol: 'BTCUSDT' }));
        
        const state = store.getState().marketData;
        // Expect only the valid candles to be present
        expect(state.currentCandles).toEqual([
          { timestamp: mockInvalidCandles[0].timestamp, open: 50000, high: 51000, low: 49000, close: 50500, volume: 100 },
          { timestamp: mockInvalidCandles[2].timestamp, open: 52000, high: 53000, low: 51000, close: 52500, volume: 200 }
        ]);
        expect(state.isLoading).toBe(false);
        expect(state.error).toBe(null);
      });
    });
  });

  describe('initial state', () => {
    test('should have correct initial state', () => {
      const state = store.getState().marketData;
      expect(state.selectedSymbol).toBe(null);
      expect(state.symbolsList).toEqual([]);
      expect(state.currentOrderBook).toBe(null);
      expect(state.currentCandles).toEqual([]);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBe(null);
      expect(state.symbolsLoading).toBe(false);
      expect(state.symbolsError).toBe(null);
    });
  });
});