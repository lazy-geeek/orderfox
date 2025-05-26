import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import apiClient from '../../services/apiClient';

// Types
export type TradingMode = 'paper' | 'live';

interface TradingState {
  openPositions: any[];
  tradeHistory: any[];
  tradingMode: TradingMode;
  isSubmittingTrade: boolean;
  tradeError: string | null;
  positionsLoading: boolean;
  positionsError: string | null;
}

interface TradeDetails {
  symbol: string;
  side: string;
  amount: number;
  type: string;
  price?: number;
}

const initialState: TradingState = {
  openPositions: [],
  tradeHistory: [],
  tradingMode: 'paper',
  isSubmittingTrade: false,
  tradeError: null,
  positionsLoading: false,
  positionsError: null,
};

// Async thunks
export const fetchOpenPositions = createAsyncThunk(
  'trading/fetchOpenPositions',
  async (_, { rejectWithValue }) => {
    try {
      const response = await apiClient.get('/positions');
      return response.data;
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail ||
        error.response?.data?.message ||
        'Could not load your positions. Please try again later.'
      );
    }
  }
);

export const executePaperTrade = createAsyncThunk(
  'trading/executePaperTrade',
  async (tradeDetails: TradeDetails, { rejectWithValue, dispatch }) => {
    try {
      const response = await apiClient.post('/trade', {
        ...tradeDetails,
        mode: 'paper'
      });
      
      // Re-fetch positions after successful trade
      dispatch(fetchOpenPositions());
      
      return response.data;
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail ||
        error.response?.data?.message ||
        'Could not execute paper trade. Please check your order details and try again.'
      );
    }
  }
);

export const executeLiveTrade = createAsyncThunk(
  'trading/executeLiveTrade',
  async (tradeDetails: TradeDetails, { rejectWithValue, dispatch }) => {
    try {
      const response = await apiClient.post('/trade', {
        ...tradeDetails,
        mode: 'live'
      });
      
      // Re-fetch positions after successful trade
      dispatch(fetchOpenPositions());
      
      return response.data;
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail ||
        error.response?.data?.message ||
        'Could not execute live trade. Please check your order details and try again.'
      );
    }
  }
);

export const setTradingModeApi = createAsyncThunk(
  'trading/setTradingModeApi',
  async (mode: TradingMode, { rejectWithValue }) => {
    try {
      await apiClient.post('/set_trading_mode', { mode });
      return mode;
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail ||
        error.response?.data?.message ||
        'Could not change trading mode. Please try again.'
      );
    }
  }
);

const tradingSlice = createSlice({
  name: 'trading',
  initialState,
  reducers: {
    setTradingMode: (state, action: PayloadAction<TradingMode>) => {
      state.tradingMode = action.payload;
    },
    clearTradeError: (state) => {
      state.tradeError = null;
    },
    clearPositionsError: (state) => {
      state.positionsError = null;
    },
    addToTradeHistory: (state, action: PayloadAction<any>) => {
      state.tradeHistory.unshift(action.payload);
      // Keep only the latest 100 trades
      if (state.tradeHistory.length > 100) {
        state.tradeHistory = state.tradeHistory.slice(0, 100);
      }
    },
  },
  extraReducers: (builder) => {
    // Fetch open positions
    builder
      .addCase(fetchOpenPositions.pending, (state) => {
        state.positionsLoading = true;
        state.positionsError = null;
      })
      .addCase(fetchOpenPositions.fulfilled, (state, action) => {
        state.positionsLoading = false;
        state.openPositions = action.payload;
      })
      .addCase(fetchOpenPositions.rejected, (state, action) => {
        state.positionsLoading = false;
        state.positionsError = action.payload as string;
      })
      // Execute paper trade
      .addCase(executePaperTrade.pending, (state) => {
        state.isSubmittingTrade = true;
        state.tradeError = null;
      })
      .addCase(executePaperTrade.fulfilled, (state, action) => {
        state.isSubmittingTrade = false;
        // Add to trade history
        state.tradeHistory.unshift(action.payload);
        if (state.tradeHistory.length > 100) {
          state.tradeHistory = state.tradeHistory.slice(0, 100);
        }
      })
      .addCase(executePaperTrade.rejected, (state, action) => {
        state.isSubmittingTrade = false;
        state.tradeError = action.payload as string;
      })
      // Execute live trade
      .addCase(executeLiveTrade.pending, (state) => {
        state.isSubmittingTrade = true;
        state.tradeError = null;
      })
      .addCase(executeLiveTrade.fulfilled, (state, action) => {
        state.isSubmittingTrade = false;
        // Add to trade history
        state.tradeHistory.unshift(action.payload);
        if (state.tradeHistory.length > 100) {
          state.tradeHistory = state.tradeHistory.slice(0, 100);
        }
      })
      .addCase(executeLiveTrade.rejected, (state, action) => {
        state.isSubmittingTrade = false;
        state.tradeError = action.payload as string;
      })
      // Set trading mode API
      .addCase(setTradingModeApi.pending, (state) => {
        // Could add a loading state for mode switching if needed
      })
      .addCase(setTradingModeApi.fulfilled, (state, action) => {
        state.tradingMode = action.payload;
      })
      .addCase(setTradingModeApi.rejected, (state, action) => {
        state.tradeError = action.payload as string;
      });
  },
});

export const {
  setTradingMode,
  clearTradeError,
  clearPositionsError,
  addToTradeHistory,
} = tradingSlice.actions;

export default tradingSlice.reducer;