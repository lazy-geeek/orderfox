import { AppDispatch } from '../store/store';
import { 
  updateCandlesFromWebSocket, 
  updateOrderBookFromWebSocket,
  setCandlesWsConnected,
  setOrderBookWsConnected,
} from '../features/marketData/marketDataSlice';

interface WebSocketManager {
  [key: string]: WebSocket;
}

const activeWebSockets: WebSocketManager = {};

/**
 * Establishes and manages WebSocket connections for market data streams.
 * @param dispatch - The Redux dispatch function.
 * @param symbol - The trading symbol (e.g., 'ETHUSDT').
 * @param streamType - The type of stream ('candles' or 'orderbook').
 * @param timeframe - Optional, for 'candles' stream (e.g., '1m', '5m').
 */
export const connectWebSocketStream = (
  dispatch: AppDispatch, 
  symbol: string, 
  streamType: 'candles' | 'orderbook', 
  timeframe?: string
) => {
  const streamKey = timeframe ? `${streamType}-${symbol}-${timeframe}` : `${streamType}-${symbol}`;
  const wsBaseUrl = process.env.REACT_APP_WS_BASE_URL || 'ws://localhost:8000';
  const wsUrl = timeframe 
    ? `${wsBaseUrl}/ws/${streamType}/${symbol}/${timeframe}` 
    : `${wsBaseUrl}/ws/${streamType}/${symbol}`;

  // Close existing connection for this stream type if it exists
  if (activeWebSockets[streamKey]) {
    console.log(`Closing existing WebSocket for ${streamKey}`);
    activeWebSockets[streamKey].close();
    delete activeWebSockets[streamKey];
  }

  try {
    const ws = new WebSocket(wsUrl);
    activeWebSockets[streamKey] = ws;

    ws.onopen = () => {
      console.log(`WebSocket connected for ${streamKey}: ${wsUrl}`);
      if (streamType === 'candles') {
        dispatch(setCandlesWsConnected(true));
      } else if (streamType === 'orderbook') {
        dispatch(setOrderBookWsConnected(true));
      }
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (streamType === 'candles') {
          dispatch(updateCandlesFromWebSocket(data));
        } else if (streamType === 'orderbook') {
          dispatch(updateOrderBookFromWebSocket(data));
        }
      } catch (error) {
        console.error(`Error parsing WebSocket message for ${streamKey}:`, error);
      }
    };

    ws.onerror = (error) => {
      console.error(`WebSocket error for ${streamKey}:`, error);
      if (streamType === 'candles') {
        dispatch(setCandlesWsConnected(false));
      } else if (streamType === 'orderbook') {
        dispatch(setOrderBookWsConnected(false));
      }
      // Optionally handle reconnection logic here or in the component
    };

    ws.onclose = (event) => {
      console.log(`WebSocket closed for ${streamKey}:`, event.code, event.reason);
      if (streamType === 'candles') {
        dispatch(setCandlesWsConnected(false));
      } else if (streamType === 'orderbook') {
        dispatch(setOrderBookWsConnected(false));
      }
      delete activeWebSockets[streamKey];

      // Attempt to reconnect if not a clean close (code 1000)
      if (event.code !== 1000) {
        console.log(`Attempting to reconnect WebSocket for ${streamKey} in 3 seconds...`);
        setTimeout(() => {
          connectWebSocketStream(dispatch, symbol, streamType, timeframe);
        }, 3000);
      }
    };
  } catch (error) {
    console.error(`Error creating WebSocket connection for ${streamKey}:`, error);
    if (streamType === 'candles') {
      dispatch(setCandlesWsConnected(false));
    } else if (streamType === 'orderbook') {
      dispatch(setOrderBookWsConnected(false));
    }
  }
};

/**
 * Disconnects a specific WebSocket stream.
 * @param streamType - The type of stream ('candles' or 'orderbook').
 * @param symbol - The trading symbol.
 * @param timeframe - Optional, for 'candles' stream.
 */
export const disconnectWebSocketStream = (
  streamType: 'candles' | 'orderbook', 
  symbol: string, 
  timeframe?: string
) => {
  const streamKey = timeframe ? `${streamType}-${symbol}-${timeframe}` : `${streamType}-${symbol}`;
  if (activeWebSockets[streamKey]) {
    console.log(`Manually closing WebSocket for ${streamKey}`);
    activeWebSockets[streamKey].close(1000, 'Client initiated close'); // Code 1000 for normal closure
    delete activeWebSockets[streamKey];
  }
};

/**
 * Disconnects all active WebSocket streams.
 */
export const disconnectAllWebSockets = () => {
  console.log('Disconnecting all active WebSockets...');
  for (const key in activeWebSockets) {
    if (activeWebSockets.hasOwnProperty(key)) {
      activeWebSockets[key].close(1000, 'Client initiated close (all)');
      delete activeWebSockets[key];
    }
  }
};