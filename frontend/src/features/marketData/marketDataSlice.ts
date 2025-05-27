import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import apiClient from '../../services/apiClient';

/**
 * Trading symbol information
 */
interface Symbol {
  /** Exchange symbol ID */
  id: string;
  /** Trading pair symbol (e.g., 'BTCUSDT') */
  symbol: string;
  /** Base asset (e.g., 'BTC') */
  baseAsset: string;
  /** Quote asset (e.g., 'USDT') */
  quoteAsset: string;
  /** User-friendly display name (e.g., 'BTC/USDT') */
  uiName: string;
  /** 24-hour trading volume in quote currency */
  volume24h?: number;
}

/**
 * Single price level in the order book
 */
interface OrderBookLevel {
  /** Price level */
  price: number;
  /** Volume/amount at this price level */
  amount: number;
}

/**
 * Complete order book data with bids and asks
 */
interface OrderBook {
  /** Trading symbol */
  symbol: string;
  /** Buy orders (bids) sorted by price descending */
  bids: OrderBookLevel[];
  /** Sell orders (asks) sorted by price ascending */
  asks: OrderBookLevel[];
  /** Timestamp of the order book snapshot */
  timestamp: number;
}

/**
 * Candlestick/OHLCV data for price charts
 */
interface Candle {
  /** Candle timestamp */
  timestamp: number;
  /** Opening price */
  open: number;
  /** Highest price */
  high: number;
  /** Lowest price */
  low: number;
  /** Closing price */
  close: number;
  /** Trading volume */
  volume: number;
}

/**
 * Redux state for market data management
 */
interface MarketDataState {
  /** Currently selected trading symbol */
  selectedSymbol: string | null;
  /** List of available trading symbols */
  symbolsList: Symbol[];
  /** Current order book data */
  currentOrderBook: OrderBook | null;
  /** Current candlestick data */
  currentCandles: Candle[];
  /** Loading state for market data operations */
  isLoading: boolean;
  /** Error message for market data operations */
  error: string | null;
  /** Loading state for symbols list */
  symbolsLoading: boolean;
  /** Error message for symbols loading */
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
      return rejectWithValue(
        error.response?.data?.detail ||
        error.response?.data?.message ||
        'Could not load trading symbols. Please try again later.'
      );
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
      return rejectWithValue(
        error.response?.data?.detail ||
        error.response?.data?.message ||
        'Could not load order book data. Please try again later.'
      );
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
      return rejectWithValue(
        error.response?.data?.detail ||
        error.response?.data?.message ||
        'Could not load chart data. Please try again later.'
      );
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