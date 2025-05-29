import { configureStore } from '@reduxjs/toolkit';
import { connectWebSocketStream, disconnectWebSocketStream, disconnectAllWebSockets } from '../../services/websocketService';
import apiClient from '../../services/apiClient';
import marketDataReducer, {
  setSelectedSymbol,
  setSelectedTimeframe,
  updateOrderBookFromWebSocket,
  updateCandlesFromWebSocket,
  setCandlesWsConnected,
  setOrderBookWsConnected,
  fetchSymbols,
  fetchOrderBook,
  fetchCandles,
  startCandlesWebSocket,
  stopCandlesWebSocket,
  startOrderBookWebSocket,
  stopOrderBookWebSocket,
  stopAllWebSockets,
  initializeMarketDataStreams,
  updateCandlesStream,
  cleanupMarketDataStreams,
} from './marketDataSlice';

// Mock apiClient
jest.mock('../../services/apiClient', () => ({
  __esModule: true,
  default: {
    get: jest.fn()
  }
}));

// Mock websocketService
jest.mock('../../services/websocketService', () => ({
  __esModule: true,
  connectWebSocketStream: jest.fn(),
  disconnectWebSocketStream: jest.fn(),
  disconnectAllWebSockets: jest.fn(),
}));

const mockGet = (apiClient as any).get;

// Cast the mocked functions to jest.Mock to access their mock properties
const mockConnectWebSocketStream = connectWebSocketStream as jest.Mock;
const mockDisconnectWebSocketStream = disconnectWebSocketStream as jest.Mock;
const mockDisconnectAllWebSockets = disconnectAllWebSockets as jest.Mock;

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
    test('setSelectedSymbol should update selectedSymbol and clear data', () => {
      store.dispatch(setSelectedSymbol('BTCUSDT'));
      expect(store.getState().marketData.selectedSymbol).toBe('BTCUSDT');
      expect(store.getState().marketData.currentOrderBook).toBe(null);
      expect(store.getState().marketData.currentCandles).toEqual([]);
    });

    test('setSelectedSymbol should handle null and clear data', () => {
      store.dispatch(setSelectedSymbol('BTCUSDT')); // Set a symbol first
      store.dispatch(setSelectedSymbol(null));
      expect(store.getState().marketData.selectedSymbol).toBe(null);
      expect(store.getState().marketData.currentOrderBook).toBe(null);
      expect(store.getState().marketData.currentCandles).toEqual([]);
    });

    test('setSelectedTimeframe should update selectedTimeframe and clear candles', () => {
      store.dispatch(setSelectedTimeframe('5m'));
      expect(store.getState().marketData.selectedTimeframe).toBe('5m');
      expect(store.getState().marketData.currentCandles).toEqual([]);
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

    test('setCandlesWsConnected should update candlesWsConnected', () => {
      store.dispatch(setCandlesWsConnected(true));
      expect(store.getState().marketData.candlesWsConnected).toBe(true);
    });

    test('setOrderBookWsConnected should update orderBookWsConnected', () => {
      store.dispatch(setOrderBookWsConnected(true));
      expect(store.getState().marketData.orderBookWsConnected).toBe(true);
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
        expect(state.orderBookLoading).toBe(false);
        expect(state.orderBookError).toBe(null);
      });

      test('should handle API error', async () => {
        const errorMessage = 'Order book not found';
        mockGet.mockRejectedValueOnce({
          response: { data: { detail: errorMessage } }
        });

        await store.dispatch(fetchOrderBook('INVALID'));
        
        const state = store.getState().marketData;
        expect(state.orderBookError).toBe(errorMessage);
        expect(state.orderBookLoading).toBe(false);
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
        expect(state.candlesLoading).toBe(false);
        expect(state.candlesError).toBe(null);
      });

      test('should handle API error', async () => {
        const errorMessage = 'Chart data unavailable';
        mockGet.mockRejectedValueOnce({
          response: { data: { detail: errorMessage } }
        });

        await store.dispatch(fetchCandles({ symbol: 'INVALID' }));
        
        const state = store.getState().marketData;
        expect(state.candlesError).toBe(errorMessage);
        expect(state.candlesLoading).toBe(false);
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
        expect(state.candlesLoading).toBe(false);
        expect(state.candlesError).toBe(null);
      });
    });
  });

  describe('initial state', () => {
    test('should have correct initial state', () => {
      const state = store.getState().marketData;
      expect(state.selectedSymbol).toBe(null);
      expect(state.selectedTimeframe).toBe('1m');
      expect(state.symbolsList).toEqual([]);
      expect(state.currentOrderBook).toBe(null);
      expect(state.currentCandles).toEqual([]);
      expect(state.candlesLoading).toBe(false);
      expect(state.candlesError).toBe(null);
      expect(state.orderBookLoading).toBe(false);
      expect(state.orderBookError).toBe(null);
      expect(state.symbolsLoading).toBe(false);
      expect(state.symbolsError).toBe(null);
      expect(state.candlesWsConnected).toBe(false);
      expect(state.orderBookWsConnected).toBe(false);
    });
  });

  describe('WebSocket Thunks', () => {
    beforeEach(() => {
      jest.clearAllMocks();
    });

    test('startCandlesWebSocket should call connectWebSocketStream', async () => {
      const symbol = 'TESTUSDT';
      const timeframe = '1m';
      await store.dispatch(startCandlesWebSocket({ symbol, timeframe }) as any);
      expect(mockConnectWebSocketStream).toHaveBeenCalledWith(expect.any(Function), symbol, 'candles', timeframe);
    });

    test('stopCandlesWebSocket should call disconnectWebSocketStream', async () => {
      const symbol = 'TESTUSDT';
      const timeframe = '1m';
      await store.dispatch(stopCandlesWebSocket({ symbol, timeframe }) as any);
      expect(mockDisconnectWebSocketStream).toHaveBeenCalledWith('candles', symbol, timeframe);
    });

    test('startOrderBookWebSocket should call connectWebSocketStream', async () => {
      const symbol = 'TESTUSDT';
      await store.dispatch(startOrderBookWebSocket({ symbol }) as any);
      expect(mockConnectWebSocketStream).toHaveBeenCalledWith(expect.any(Function), symbol, 'orderbook');
    });

    test('stopOrderBookWebSocket should call disconnectWebSocketStream', async () => {
      const symbol = 'TESTUSDT';
      await store.dispatch(stopOrderBookWebSocket({ symbol }) as any);
      expect(mockDisconnectWebSocketStream).toHaveBeenCalledWith('orderbook', symbol);
    });

    test('stopAllWebSockets should call disconnectAllWebSockets', async () => {
      await store.dispatch(stopAllWebSockets() as any);
      expect(mockDisconnectAllWebSockets).toHaveBeenCalled();
    });

    test('initializeMarketDataStreams should start both candle and orderbook WS', async () => {
      store.dispatch(setSelectedSymbol('TESTUSDT'));
      store.dispatch(setSelectedTimeframe('1m'));
      await store.dispatch(initializeMarketDataStreams() as any);

      expect(mockConnectWebSocketStream).toHaveBeenCalledWith(expect.any(Function), 'TESTUSDT', 'orderbook');
      expect(mockConnectWebSocketStream).toHaveBeenCalledWith(expect.any(Function), 'TESTUSDT', 'candles', '1m');
    });

    test('updateCandlesStream should stop old and start new candle WS', async () => {
      store.dispatch(setSelectedSymbol('TESTUSDT'));
      store.dispatch(setSelectedTimeframe('1m'));
      // Simulate initial connection
      await store.dispatch(startCandlesWebSocket({ symbol: 'TESTUSDT', timeframe: '1m' }) as any);
      jest.clearAllMocks(); // Clear mocks to check calls after timeframe change

      store.dispatch(setSelectedTimeframe('5m'));
      await store.dispatch(updateCandlesStream() as any);

      expect(mockDisconnectWebSocketStream).toHaveBeenCalledWith('candles', 'TESTUSDT', '1m');
      expect(mockConnectWebSocketStream).toHaveBeenCalledWith(expect.any(Function), 'TESTUSDT', 'candles', '5m');
    });

    test('cleanupMarketDataStreams should stop all relevant WS', async () => {
      store.dispatch(setSelectedSymbol('TESTUSDT'));
      store.dispatch(setSelectedTimeframe('1m'));
      // Simulate active connections
      await store.dispatch(startCandlesWebSocket({ symbol: 'TESTUSDT', timeframe: '1m' }) as any);
      await store.dispatch(startOrderBookWebSocket({ symbol: 'TESTUSDT' }) as any);
      jest.clearAllMocks();

      await store.dispatch(cleanupMarketDataStreams() as any);

      expect(mockDisconnectWebSocketStream).toHaveBeenCalledWith('candles', 'TESTUSDT', '1m');
      expect(mockDisconnectWebSocketStream).toHaveBeenCalledWith('orderbook', 'TESTUSDT');
      expect(mockDisconnectAllWebSockets).toHaveBeenCalled();
    });
  });
});