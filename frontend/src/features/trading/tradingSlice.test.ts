import { configureStore } from '@reduxjs/toolkit';
import apiClient from '../../services/apiClient';
import tradingReducer, {
  setTradingMode,
  clearTradeError,
  clearPositionsError,
  addToTradeHistory,
  fetchOpenPositions,
  executePaperTrade,
  executeLiveTrade,
  setTradingModeApi,
} from './tradingSlice';

// Mock apiClient
jest.mock('../../services/apiClient', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
    post: jest.fn()
  }
}));

const mockGet = (apiClient as any).get;
const mockPost = (apiClient as any).post;

type TestStore = ReturnType<typeof configureStore<{
  trading: ReturnType<typeof tradingReducer>;
}>>;

describe('tradingSlice', () => {
  let store: TestStore;

  beforeEach(() => {
    store = configureStore({
      reducer: {
        trading: tradingReducer,
      },
    });
  });

  describe('initial state', () => {
    test('should have correct initial state', () => {
      const state = store.getState().trading;
      expect(state.openPositions).toEqual([]);
      expect(state.tradeHistory).toEqual([]);
      expect(state.tradingMode).toBe('paper');
      expect(state.isSubmittingTrade).toBe(false);
      expect(state.tradeError).toBe(null);
      expect(state.positionsLoading).toBe(false);
      expect(state.positionsError).toBe(null);
    });
  });

  describe('reducers', () => {
    test('setTradingMode should update tradingMode', () => {
      store.dispatch(setTradingMode('live'));
      expect(store.getState().trading.tradingMode).toBe('live');
    });

    test('setTradingMode should handle paper mode', () => {
      store.dispatch(setTradingMode('paper'));
      expect(store.getState().trading.tradingMode).toBe('paper');
    });

    test('clearTradeError should clear error', () => {
      // First set an error by testing the reducer directly
      const initialState = {
        openPositions: [],
        tradeHistory: [],
        tradingMode: 'paper' as const,
        isSubmittingTrade: false,
        tradeError: 'Some error',
        positionsLoading: false,
        positionsError: null,
      };
      
      const action = clearTradeError();
      const newState = tradingReducer(initialState, action);
      expect(newState.tradeError).toBe(null);
    });

    test('clearPositionsError should clear positions error', () => {
      const initialState = {
        openPositions: [],
        tradeHistory: [],
        tradingMode: 'paper' as const,
        isSubmittingTrade: false,
        tradeError: null,
        positionsLoading: false,
        positionsError: 'Positions error',
      };
      
      const action = clearPositionsError();
      const newState = tradingReducer(initialState, action);
      expect(newState.positionsError).toBe(null);
    });

    test('addToTradeHistory should add trade to history', () => {
      const tradeData = { id: '1', symbol: 'BTCUSDT', side: 'long', amount: 0.1 };
      store.dispatch(addToTradeHistory(tradeData));
      const state = store.getState().trading;
      expect(state.tradeHistory).toHaveLength(1);
      expect(state.tradeHistory[0]).toEqual(tradeData);
    });

    test('addToTradeHistory should limit history to 100 items', () => {
      const initialState = {
        openPositions: [],
        tradeHistory: new Array(100).fill(null).map((_, i) => ({ id: i })),
        tradingMode: 'paper' as const,
        isSubmittingTrade: false,
        tradeError: null,
        positionsLoading: false,
        positionsError: null,
      };

      const newTrade = { id: 'new' };
      const action = addToTradeHistory(newTrade);
      const newState = tradingReducer(initialState, action);
      
      expect(newState.tradeHistory).toHaveLength(100);
      expect(newState.tradeHistory[0]).toEqual(newTrade);
    });

    test('addToTradeHistory should add new trades to the beginning', () => {
      const trade1 = { id: '1', symbol: 'BTCUSDT' };
      const trade2 = { id: '2', symbol: 'ETHUSDT' };
      
      store.dispatch(addToTradeHistory(trade1));
      store.dispatch(addToTradeHistory(trade2));
      
      const state = store.getState().trading;
      expect(state.tradeHistory).toHaveLength(2);
      expect(state.tradeHistory[0]).toEqual(trade2); // Most recent first
      expect(state.tradeHistory[1]).toEqual(trade1);
    });
  });

  describe('async thunks', () => {
    beforeEach(() => {
      jest.clearAllMocks();
    });

    describe('fetchOpenPositions', () => {
      test('should handle successful fetch', async () => {
        const mockPositions = [
          { symbol: 'BTCUSDT', side: 'long', size: 0.1, entryPrice: 50000, markPrice: 51000, unrealizedPnl: 100 }
        ];
        
        mockGet.mockResolvedValueOnce({ data: mockPositions });

        await store.dispatch(fetchOpenPositions());
        
        const state = store.getState().trading;
        expect(state.openPositions).toEqual(mockPositions);
        expect(state.positionsLoading).toBe(false);
        expect(state.positionsError).toBe(null);
      });

      test('should handle API error', async () => {
        const errorMessage = 'Positions service unavailable';
        mockGet.mockRejectedValueOnce({
          response: { data: { detail: errorMessage } }
        });

        await store.dispatch(fetchOpenPositions());
        
        const state = store.getState().trading;
        expect(state.positionsError).toBe(errorMessage);
        expect(state.positionsLoading).toBe(false);
      });

      test('should handle network error with fallback message', async () => {
        mockGet.mockRejectedValueOnce(new Error('Network error'));

        await store.dispatch(fetchOpenPositions());
        
        const state = store.getState().trading;
        expect(state.positionsError).toBe('Could not load your positions. Please try again later.');
        expect(state.positionsLoading).toBe(false);
      });
    });

    describe('executePaperTrade', () => {
      test('should handle successful trade execution', async () => {
        const tradeDetails = { symbol: 'BTCUSDT', side: 'long', amount: 0.1, type: 'market' };
        const mockTradeResult = { id: 'trade123', ...tradeDetails, status: 'filled' };
        
        mockPost.mockResolvedValueOnce({ data: mockTradeResult });
        mockGet.mockResolvedValueOnce({ data: [] }); // fetchOpenPositions call

        await store.dispatch(executePaperTrade(tradeDetails));
        
        const state = store.getState().trading;
        expect(state.isSubmittingTrade).toBe(false);
        expect(state.tradeError).toBe(null);
        expect(state.tradeHistory[0]).toEqual(mockTradeResult);
      });

      test('should handle trade execution error', async () => {
        const tradeDetails = { symbol: 'BTCUSDT', side: 'long', amount: 0.1, type: 'market' };
        const errorMessage = 'Insufficient balance';
        
        mockPost.mockRejectedValueOnce({
          response: { data: { detail: errorMessage } }
        });

        await store.dispatch(executePaperTrade(tradeDetails));
        
        const state = store.getState().trading;
        expect(state.tradeError).toBe(errorMessage);
        expect(state.isSubmittingTrade).toBe(false);
      });
    });

    describe('executeLiveTrade', () => {
      test('should handle successful trade execution', async () => {
        const tradeDetails = { symbol: 'BTCUSDT', side: 'long', amount: 0.1, type: 'market' };
        const mockTradeResult = { id: 'trade123', ...tradeDetails, status: 'filled' };
        
        mockPost.mockResolvedValueOnce({ data: mockTradeResult });
        mockGet.mockResolvedValueOnce({ data: [] }); // fetchOpenPositions call

        await store.dispatch(executeLiveTrade(tradeDetails));
        
        const state = store.getState().trading;
        expect(state.isSubmittingTrade).toBe(false);
        expect(state.tradeError).toBe(null);
        expect(state.tradeHistory[0]).toEqual(mockTradeResult);
      });

      test('should handle trade execution error', async () => {
        const tradeDetails = { symbol: 'BTCUSDT', side: 'long', amount: 0.1, type: 'market' };
        const errorMessage = 'Market closed';
        
        mockPost.mockRejectedValueOnce({
          response: { data: { detail: errorMessage } }
        });

        await store.dispatch(executeLiveTrade(tradeDetails));
        
        const state = store.getState().trading;
        expect(state.tradeError).toBe(errorMessage);
        expect(state.isSubmittingTrade).toBe(false);
      });
    });

    describe('setTradingModeApi', () => {
      test('should handle successful mode change', async () => {
        mockPost.mockResolvedValueOnce({ data: {} });

        await store.dispatch(setTradingModeApi('live'));
        
        const state = store.getState().trading;
        expect(state.tradingMode).toBe('live');
        expect(state.tradeError).toBe(null);
      });

      test('should handle mode change error', async () => {
        const errorMessage = 'Live trading not enabled';
        mockPost.mockRejectedValueOnce({
          response: { data: { detail: errorMessage } }
        });

        await store.dispatch(setTradingModeApi('live'));
        
        const state = store.getState().trading;
        expect(state.tradeError).toBe(errorMessage);
      });
    });
  });

  describe('trade details interface', () => {
    test('should accept valid trade details for paper trade', () => {
      const tradeDetails = {
        symbol: 'BTCUSDT',
        side: 'long',
        amount: 0.1,
        type: 'market'
      };
      
      // Test that the thunk can be called with these parameters
      expect(() => executePaperTrade(tradeDetails)).not.toThrow();
    });

    test('should accept valid trade details with price for limit orders', () => {
      const tradeDetails = {
        symbol: 'BTCUSDT',
        side: 'long',
        amount: 0.1,
        type: 'limit',
        price: 50000
      };
      
      // Test that the thunk can be called with these parameters
      expect(() => executeLiveTrade(tradeDetails)).not.toThrow();
    });
  });
});