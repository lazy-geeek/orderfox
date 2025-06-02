import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import apiClient from '../../services/apiClient';
import { connectWebSocketStream, disconnectWebSocketStream, disconnectAllWebSockets } from '../../services/websocketService';
import { AppDispatch, RootState } from '../../store/store'; // Import AppDispatch and RootState

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
  /** Currently selected timeframe for candles */
  selectedTimeframe: string;
  /** List of available trading symbols */
  symbolsList: Symbol[];
  /** Current order book data */
  currentOrderBook: OrderBook | null;
  /** Current candlestick data */
  currentCandles: Candle[];
  /** Loading state for candles data */
  candlesLoading: boolean;
  /** Error message for candles data */
  candlesError: string | null;
  /** Loading state for order book data */
  orderBookLoading: boolean;
  /** Error message for order book data */
  orderBookError: string | null;
  /** Loading state for symbols list */
  symbolsLoading: boolean;
  /** Error message for symbols loading */
  symbolsError: string | null;
  /** WebSocket connection status for candles */
  candlesWsConnected: boolean;
  /** WebSocket connection status for order book */
  orderBookWsConnected: boolean;
}

const initialState: MarketDataState = {
  selectedSymbol: null,
  selectedTimeframe: '1m', // Default timeframe
  symbolsList: [],
  currentOrderBook: null,
  currentCandles: [],
  candlesLoading: false,
  candlesError: null,
  orderBookLoading: false,
  orderBookError: null,
  symbolsLoading: false,
  symbolsError: null,
  candlesWsConnected: false,
  orderBookWsConnected: false,
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

// Thunks for WebSocket management
export const startCandlesWebSocket = createAsyncThunk<
  void,
  { symbol: string; timeframe: string },
  { dispatch: AppDispatch; state: RootState }
>(
  'marketData/startCandlesWebSocket',
  async ({ symbol, timeframe }, { dispatch }) => {
    connectWebSocketStream(dispatch, symbol, 'candles', timeframe);
  }
);

export const stopCandlesWebSocket = createAsyncThunk<
  void,
  { symbol: string; timeframe: string },
  { state: RootState }
>(
  'marketData/stopCandlesWebSocket',
  async ({ symbol, timeframe }) => {
    disconnectWebSocketStream('candles', symbol, timeframe);
  }
);

export const startOrderBookWebSocket = createAsyncThunk<
  void,
  { symbol: string },
  { dispatch: AppDispatch; state: RootState }
>(
  'marketData/startOrderBookWebSocket',
  async ({ symbol }, { dispatch }) => {
    connectWebSocketStream(dispatch, symbol, 'orderbook');
  }
);

export const stopOrderBookWebSocket = createAsyncThunk<
  void,
  { symbol: string },
  { state: RootState }
>(
  'marketData/stopOrderBookWebSocket',
  async ({ symbol }) => {
    disconnectWebSocketStream('orderbook', symbol);
  }
);

export const stopAllWebSockets = createAsyncThunk<
  void,
  void,
  { state: RootState }
>(
  'marketData/stopAllWebSockets',
  async () => {
    disconnectAllWebSockets();
  }
);


const marketDataSlice = createSlice({
  name: 'marketData',
  initialState,
  reducers: {
    setSelectedSymbol: (state, action: PayloadAction<string | null>) => {
      state.selectedSymbol = action.payload;
      // When symbol changes, clear current data and stop all existing WS
      state.currentOrderBook = null;
      state.currentCandles = [];
    },
    setSelectedTimeframe: (state, action: PayloadAction<string>) => {
      state.selectedTimeframe = action.payload;
      // When timeframe changes, clear current candles
      state.currentCandles = [];
    },
    clearSelectedSymbol: (state) => {
      state.selectedSymbol = null;
      state.currentOrderBook = null;
      state.currentCandles = [];
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
        // Ensure candles are always sorted by timestamp
        state.currentCandles.sort((a, b) => a.timestamp - b.timestamp);
      }
    },
    setCandlesWsConnected: (state, action: PayloadAction<boolean>) => {
      state.candlesWsConnected = action.payload;
    },
    setOrderBookWsConnected: (state, action: PayloadAction<boolean>) => {
      state.orderBookWsConnected = action.payload;
    },
    clearError: (state) => {
      state.candlesError = null;
      state.orderBookError = null;
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
        state.orderBookLoading = true;
        state.orderBookError = null;
      })
      .addCase(fetchOrderBook.fulfilled, (state, action) => {
        state.orderBookLoading = false;
        const validatedOrderBook = validateOrderBook(action.payload);
        if (validatedOrderBook) {
          state.currentOrderBook = validatedOrderBook;
        } else {
          state.orderBookError = 'Received invalid order book data from server';
        }
      })
      .addCase(fetchOrderBook.rejected, (state, action) => {
        state.orderBookLoading = false;
        state.orderBookError = action.payload as string;
      })
      // Fetch candles
      .addCase(fetchCandles.pending, (state) => {
        state.candlesLoading = true;
        state.candlesError = null;
      })
      .addCase(fetchCandles.fulfilled, (state, action) => {
        state.candlesLoading = false;
        // action.payload is already validated and filtered by the thunk
        state.currentCandles = action.payload;
      })
      .addCase(fetchCandles.rejected, (state, action) => {
        state.candlesLoading = false;
        state.candlesError = action.payload as string;
      });
  },
});

// Thunks for managing WebSocket connections based on state changes
export const initializeMarketDataStreams = createAsyncThunk<
  void,
  void,
  { dispatch: AppDispatch; state: RootState }
>(
  'marketData/initializeMarketDataStreams',
  async (_, { dispatch, getState }) => {
    const { selectedSymbol, selectedTimeframe } = getState().marketData;

    if (selectedSymbol) {
      // Start order book WebSocket
      dispatch(startOrderBookWebSocket({ symbol: selectedSymbol }));
      // Start candles WebSocket
      dispatch(startCandlesWebSocket({ symbol: selectedSymbol, timeframe: selectedTimeframe }));
    }
  }
);

export const updateCandlesStream = createAsyncThunk<
  void,
  void,
  { dispatch: AppDispatch; state: RootState }
>(
  'marketData/updateCandlesStream',
  async (_, { dispatch, getState }) => {
    const { selectedSymbol, selectedTimeframe } = getState().marketData;

    if (selectedSymbol) {
      // Stop existing candles WebSocket
      dispatch(stopCandlesWebSocket({ symbol: selectedSymbol, timeframe: getState().marketData.selectedTimeframe }));
      // Start new candles WebSocket with updated timeframe
      dispatch(startCandlesWebSocket({ symbol: selectedSymbol, timeframe: selectedTimeframe }));
    }
  }
);

export const cleanupMarketDataStreams = createAsyncThunk<
  void,
  void,
  { dispatch: AppDispatch; state: RootState }
>(
  'marketData/cleanupMarketDataStreams',
  async (_, { dispatch, getState }) => {
    const { selectedSymbol, selectedTimeframe } = getState().marketData;
    if (selectedSymbol) {
      dispatch(stopCandlesWebSocket({ symbol: selectedSymbol, timeframe: selectedTimeframe }));
      dispatch(stopOrderBookWebSocket({ symbol: selectedSymbol }));
    }
    dispatch(stopAllWebSockets()); // Ensure all are closed
  }
);


export const {
  setSelectedSymbol,
  setSelectedTimeframe,
  clearSelectedSymbol,
  updateOrderBookFromWebSocket,
  updateCandlesFromWebSocket,
  setCandlesWsConnected,
  setOrderBookWsConnected,
  clearError,
} = marketDataSlice.actions;

export default marketDataSlice.reducer;