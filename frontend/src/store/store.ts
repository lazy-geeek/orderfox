import { configureStore, createListenerMiddleware } from '@reduxjs/toolkit';
import marketDataReducer, {
  setSelectedSymbol,
  setSelectedTimeframe,
  initializeMarketDataStreams,
  updateCandlesStream,
  cleanupMarketDataStreams,
  marketDataListenerMiddleware,
} from '../features/marketData/marketDataSlice';
import tradingReducer from '../features/trading/tradingSlice';

const listenerMiddleware = createListenerMiddleware();

listenerMiddleware.startListening({
  actionCreator: setSelectedSymbol,
  effect: async (action, { dispatch, getState }) => {
    const state = getState() as RootState; // Explicitly type getState
    const { selectedSymbol } = state.marketData;
    
    // Cleanup existing streams if symbol changes or is cleared
    dispatch(cleanupMarketDataStreams() as any); // Cast to any to resolve type issues

    if (selectedSymbol) {
      // Initialize new streams for the selected symbol
      dispatch(initializeMarketDataStreams() as any); // Cast to any to resolve type issues
    }
  },
});

listenerMiddleware.startListening({
  actionCreator: setSelectedTimeframe,
  effect: async (action, { dispatch, getState }) => {
    const state = getState() as RootState; // Explicitly type getState
    const { selectedSymbol } = state.marketData;
    if (selectedSymbol) {
      // Update candles stream when timeframe changes
      // Note: We can't easily get the old timeframe here since state is already updated
      // The function will use the current timeframe for both stop and start
      dispatch(updateCandlesStream({}) as any); // Cast to any to resolve type issues
    }
  },
});

const rootReducer = {
  marketData: marketDataReducer,
  trading: tradingReducer,
};

export const store = configureStore({
  reducer: rootReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware()
      .prepend(listenerMiddleware.middleware)
      .prepend(marketDataListenerMiddleware.middleware),
});

// Infer the `RootState` and `AppDispatch` types from the store itself
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;