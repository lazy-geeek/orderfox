import { configureStore } from '@reduxjs/toolkit';
import marketDataReducer from '../features/marketData/marketDataSlice';
import tradingReducer from '../features/trading/tradingSlice';

const rootReducer = {
  marketData: marketDataReducer,
  trading: tradingReducer,
};

export const store = configureStore({
  reducer: rootReducer,
});

// Infer the `RootState` and `AppDispatch` types from the store itself
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;