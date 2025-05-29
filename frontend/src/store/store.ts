import { configureStore, createListenerMiddleware, isAnyOf } from '@reduxjs/toolkit';
import marketDataReducer, {
  setSelectedSymbol,
  setSelectedTimeframe,
  initializeMarketDataStreams,
  updateCandlesStream,
  cleanupMarketDataStreams,
} from '../features/marketData/marketDataSlice';
import tradingReducer from '../features/trading/tradingSlice';

const listenerMiddleware = createListenerMiddleware();

listenerMiddleware.startListening({
  actionCreator: setSelectedSymbol,
  effect: async (action, { dispatch, getState }) => {
    const state = getState() as RootState; // Explicitly type getState
    const { selectedSymbol, selectedTimeframe } = state.marketData;
    
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
    const { selectedSymbol, selectedTimeframe } = state.marketData;
    if (selectedSymbol) {
      // Update candles stream when timeframe changes
      dispatch(updateCandlesStream() as any); // Cast to any to resolve type issues
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
    getDefaultMiddleware().prepend(listenerMiddleware.middleware),
});

// Infer the `RootState` and `AppDispatch` types from the store itself
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;