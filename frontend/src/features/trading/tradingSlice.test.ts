import { configureStore } from '@reduxjs/toolkit';
import tradingReducer, {
  setTradingMode,
  clearTradeError,
  addToTradeHistory,
  fetchOpenPositions,
  executePaperTrade,
  executeLiveTrade,
  setTradingModeApi,
} from './tradingSlice';

// Mock apiClient
jest.mock('../../services/apiClient', () => ({
  get: jest.fn(),
  post: jest.fn(),
}));

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
      };
      
      const action = clearTradeError();
      const newState = tradingReducer(initialState, action);
      expect(newState.tradeError).toBe(null);
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
    test('fetchOpenPositions should be defined', () => {
      expect(fetchOpenPositions).toBeDefined();
      expect(typeof fetchOpenPositions).toBe('function');
    });

    test('executePaperTrade should be defined', () => {
      expect(executePaperTrade).toBeDefined();
      expect(typeof executePaperTrade).toBe('function');
    });

    test('executeLiveTrade should be defined', () => {
      expect(executeLiveTrade).toBeDefined();
      expect(typeof executeLiveTrade).toBe('function');
    });

    test('setTradingModeApi should be defined', () => {
      expect(setTradingModeApi).toBeDefined();
      expect(typeof setTradingModeApi).toBe('function');
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