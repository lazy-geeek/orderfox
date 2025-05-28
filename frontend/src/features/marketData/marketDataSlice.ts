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
 * Helper function to validate and filter candle data.
 * Ensures all required numerical properties exist and are valid numbers.
 */
const validateAndFilterCandles = (candles: any[]): Candle[] => {
  if (!Array.isArray(candles)) {
    console.warn('Invalid candles data: not an array', candles);
    return [];
  }

  return candles
    .map((candle, index) => {
      // Handle both timestamp formats: Unix timestamp (number) or ISO string
      let timestamp: number;
      if (typeof candle.timestamp === 'number') {
        timestamp = candle.timestamp;
      } else if (typeof candle.timestamp === 'string') {
        // Try to parse as ISO date string first, then as number
        const dateTimestamp = new Date(candle.timestamp).getTime();
        if (!isNaN(dateTimestamp)) {
          timestamp = dateTimestamp;
        } else {
          timestamp = parseInt(candle.timestamp, 10);
        }
      } else {
        console.warn(`Invalid timestamp format at index ${index}:`, candle.timestamp);
        return null;
      }
      
      const parsedCandle = {
        timestamp: timestamp,
        open: parseFloat(candle.open as any),
        high: parseFloat(candle.high as any),
        low: parseFloat(candle.low as any),
        close: parseFloat(candle.close as any),
        volume: parseFloat(candle.volume as any),
      };

      const isValid =
        typeof parsedCandle.timestamp === 'number' && !isNaN(parsedCandle.timestamp) && parsedCandle.timestamp > 0 &&
        typeof parsedCandle.open === 'number' && !isNaN(parsedCandle.open) && parsedCandle.open > 0 &&
        typeof parsedCandle.high === 'number' && !isNaN(parsedCandle.high) && parsedCandle.high > 0 &&
        typeof parsedCandle.low === 'number' && !isNaN(parsedCandle.low) && parsedCandle.low > 0 &&
        typeof parsedCandle.close === 'number' && !isNaN(parsedCandle.close) && parsedCandle.close > 0 &&
        typeof parsedCandle.volume === 'number' && !isNaN(parsedCandle.volume) && parsedCandle.volume >= 0;

      if (!isValid) {
        console.warn(`Skipping invalid candle data at index ${index} after parsing:`, candle, 'Parsed:', parsedCandle);
        return null; // Mark as null to be filtered out
      }
      return parsedCandle as Candle;
    })
    .filter(candle => candle !== null) as Candle[];
};

/**
 * Helper function to validate and filter order book data.
 * Ensures bids and asks arrays exist and contain valid data.
 */
const validateOrderBook = (orderBook: any): OrderBook | null => {
  if (!orderBook || typeof orderBook !== 'object') {
    console.warn('Invalid order book data: not an object', orderBook);
    return null;
  }

  // Ensure bids and asks are arrays
  const bids = Array.isArray(orderBook.bids) ? orderBook.bids : [];
  const asks = Array.isArray(orderBook.asks) ? orderBook.asks : [];

  // Validate timestamp
  let timestamp: number;
  if (typeof orderBook.timestamp === 'number') {
    timestamp = orderBook.timestamp;
  } else if (typeof orderBook.timestamp === 'string') {
    const dateTimestamp = new Date(orderBook.timestamp).getTime();
    if (!isNaN(dateTimestamp)) {
      timestamp = dateTimestamp;
    } else {
      timestamp = Date.now(); // Fallback to current time
    }
  } else {
    timestamp = Date.now(); // Fallback to current time
  }

  return {
    symbol: orderBook.symbol || '',
    bids: bids.filter((bid: any) =>
      bid && typeof bid.price === 'number' && typeof bid.amount === 'number' &&
      bid.price > 0 && bid.amount > 0
    ),
    asks: asks.filter((ask: any) =>
      ask && typeof ask.price === 'number' && typeof ask.amount === 'number' &&
      ask.price > 0 && ask.amount > 0
    ),
    timestamp
  };
};

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
      // Validate and filter incoming candle data
      return validateAndFilterCandles(response.data);
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
    updateOrderBookFromWebSocket: (state, action: PayloadAction<any>) => {
      const validatedOrderBook = validateOrderBook(action.payload);
      if (validatedOrderBook) {
        state.currentOrderBook = validatedOrderBook;
      } else {
        console.warn('Received invalid order book from WebSocket, skipping update:', action.payload);
      }
    },
    updateCandlesFromWebSocket: (state, action: PayloadAction<Candle>) => {
      const incomingCandle = action.payload;

      // Validate the incoming candle before processing
      const [newCandle] = validateAndFilterCandles([incomingCandle]);
      
      if (!newCandle) {
        console.warn('Received invalid candle from WebSocket, skipping update:', incomingCandle);
        return; // Skip update if the candle is invalid
      }

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
        const validatedOrderBook = validateOrderBook(action.payload);
        if (validatedOrderBook) {
          state.currentOrderBook = validatedOrderBook;
        } else {
          state.error = 'Received invalid order book data from server';
        }
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
        // action.payload is already validated and filtered by the thunk
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