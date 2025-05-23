import { configureStore } from '@reduxjs/toolkit';

// Initially, there are no reducers. This will be populated later.
const rootReducer = {};

export const store = configureStore({
  reducer: rootReducer,
});

// Infer the `RootState` and `AppDispatch` types from the store itself
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;