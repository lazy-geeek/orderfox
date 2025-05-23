import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import apiClient from '../../services/apiClient';

// Types
interface Symbol {
  id: string;
  symbol: string;
  baseAsset?: string;
  quoteAsset?: string;
}

interface OrderBookLevel {
  price: number;
  amount: number;
}

interface OrderBook {
  symbol: string;
  bids: OrderBookLevel[];
  asks: OrderBookLevel[];
  timestamp: number;
}

interface Candle {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface MarketDataState {
  selectedSymbol: string | null;
  symbolsList: Symbol[];
  currentOrderBook: OrderBook | null;
  currentCandles: Candle[];
  isLoading: boolean;
  error: string | null;
  symbolsLoading: boolean;
  symbolsError: string | null;
}

const initialState: MarketDataState = {
  selectedSymbol: null,
  symbolsList: [],
  currentOrderBook: null,
  currentCandles: [],
  isLoading: false,
  error: null,
  symbolsLoading: false,
  symbolsError: null,
};

// Async thunks
export const fetchSymbols = createAsyncThunk(
  'marketData/fetchSymbols',
  async (_, { rejectWithValue }) => {
    try {
      const response = await apiClient.get('/symbols');
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch symbols');
    }
  }
);

export const fetchOrderBook = createAsyncThunk(
  'marketData/fetchOrderBook',
  async (symbol: string, { rejectWithValue }) => {
    try {
      const response = await apiClient.get(`/orderbook/${symbol}`);
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch order book');
    }
  }
);

export const fetchCandles = createAsyncThunk(
  'marketData/fetchCandles',
  async ({ symbol, timeframe = '1m', limit = 100 }: { symbol: string; timeframe?: string; limit?: number }, { rejectWithValue }) => {
    try {
      const response = await apiClient.get(`/candles/${symbol}`, {
        params: { timeframe, limit }
      });
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch candles');
    }
  }
);

const marketDataSlice = createSlice({
  name: 'marketData',
  initialState,
  reducers: {
    setSelectedSymbol: (state, action: PayloadAction<string | null>) => {
      state.selectedSymbol = action.payload;
    },
    clearSelectedSymbol: (state) => {
      state.selectedSymbol = null;
    },
    updateOrderBookFromWebSocket: (state, action: PayloadAction<OrderBook>) => {
      state.currentOrderBook = action.payload;
    },
    updateCandlesFromWebSocket: (state, action: PayloadAction<Candle>) => {
      // Update or append the latest candle data
      const newCandle = action.payload;
      const existingIndex = state.currentCandles.findIndex(
        candle => candle.timestamp === newCandle.timestamp
      );
      
      if (existingIndex >= 0) {
        // Update existing candle (for real-time updates of current candle)
        state.currentCandles[existingIndex] = newCandle;
      } else {
        // Append new candle and keep only the latest 100 candles
        state.currentCandles.push(newCandle);
        if (state.currentCandles.length > 100) {
          state.currentCandles = state.currentCandles.slice(-100);
        }
      }
    },
    clearError: (state) => {
      state.error = null;
      state.symbolsError = null;
    },
  },
  extraReducers: (builder) => {
    // Fetch symbols
    builder
      .addCase(fetchSymbols.pending, (state) => {
        state.symbolsLoading = true;
        state.symbolsError = null;
      })
      .addCase(fetchSymbols.fulfilled, (state, action) => {
        state.symbolsLoading = false;
        state.symbolsList = action.payload;
      })
      .addCase(fetchSymbols.rejected, (state, action) => {
        state.symbolsLoading = false;
        state.symbolsError = action.payload as string;
      })
      // Fetch order book
      .addCase(fetchOrderBook.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchOrderBook.fulfilled, (state, action) => {
        state.isLoading = false;
        state.currentOrderBook = action.payload;
      })
      .addCase(fetchOrderBook.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Fetch candles
      .addCase(fetchCandles.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchCandles.fulfilled, (state, action) => {
        state.isLoading = false;
        state.currentCandles = action.payload;
      })
      .addCase(fetchCandles.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });
  },
});

export const {
  setSelectedSymbol,
  clearSelectedSymbol,
  updateOrderBookFromWebSocket,
  updateCandlesFromWebSocket,
  clearError,
} = marketDataSlice.actions;

export default marketDataSlice.reducer;