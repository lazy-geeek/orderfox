import { configureStore } from '@reduxjs/toolkit';
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
  get: jest.fn()
}));

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
    test('fetchSymbols should be defined', () => {
      expect(fetchSymbols).toBeDefined();
      expect(typeof fetchSymbols).toBe('function');
    });

    test('fetchOrderBook should be defined', () => {
      expect(fetchOrderBook).toBeDefined();
      expect(typeof fetchOrderBook).toBe('function');
    });

    test('fetchCandles should be defined', () => {
      expect(fetchCandles).toBeDefined();
      expect(typeof fetchCandles).toBe('function');
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