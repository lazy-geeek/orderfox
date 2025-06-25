import { AppDispatch } from '../store/store';
import { 
  updateCandlesFromWebSocket, 
  updateOrderBookFromWebSocket,
  updateTickerFromWebSocket,
  setCandlesWsConnected,
  setOrderBookWsConnected,
  setTickerWsConnected,
} from '../features/marketData/marketDataSlice';

interface WebSocketManager {
  [key: string]: WebSocket;
}

const activeWebSockets: WebSocketManager = {};
const connectionAttempts: { [key: string]: number } = {};
const lastConnectionAttempt: { [key: string]: number } = {};
const connectionInProgress: { [key: string]: boolean } = {};

/**
 * Establishes and manages WebSocket connections for market data streams.
 * @param dispatch - The Redux dispatch function.
 * @param symbol - The trading symbol (e.g., 'ETHUSDT').
 * @param streamType - The type of stream ('candles', 'orderbook', or 'ticker').
 * @param timeframe - Optional, for 'candles' stream (e.g., '1m', '5m').
 * @param limit - Optional, for 'orderbook' stream, number of levels to fetch.
 */
export const connectWebSocketStream = async (
  dispatch: AppDispatch,
  symbol: string,
  streamType: 'candles' | 'orderbook' | 'ticker',
  timeframe?: string,
  limit?: number
) => {
  const streamKey = timeframe ? `${streamType}-${symbol}-${timeframe}` : `${streamType}-${symbol}`;
  const wsBaseUrl = process.env.REACT_APP_WS_BASE_URL || 'ws://localhost:8000/api/v1';
  
  // Ensure the base URL doesn't have a trailing slash
  const cleanWsBaseUrl = wsBaseUrl.replace(/\/$/, '');
  
  let wsUrl: string;
  if (timeframe) {
    wsUrl = `${cleanWsBaseUrl}/ws/${streamType}/${symbol}/${timeframe}`;
  } else {
    wsUrl = `${cleanWsBaseUrl}/ws/${streamType}/${symbol}`;
    // Add limit parameter for orderbook streams
    if (streamType === 'orderbook' && limit) {
      wsUrl += `?limit=${limit}`;
    }
  }

  // Prevent multiple simultaneous connection attempts for the same stream
  if (connectionInProgress[streamKey]) {
    console.log(`WebSocket connection already in progress for ${streamKey}, skipping duplicate attempt`);
    return;
  }

  // Check if already connected or connecting
  if (activeWebSockets[streamKey]) {
    const currentState = activeWebSockets[streamKey].readyState;
    if (currentState === WebSocket.OPEN) {
      console.log(`WebSocket for ${streamKey} is already connected, skipping new connection attempt`);
      return;
    } else if (currentState === WebSocket.CONNECTING) {
      console.log(`WebSocket for ${streamKey} is already connecting, skipping duplicate attempt`);
      return;
    }
  }

  connectionInProgress[streamKey] = true;

  try {
    // Rate limiting: prevent rapid connection attempts
    const now = Date.now();
    const lastAttempt = lastConnectionAttempt[streamKey] || 0;
    const timeSinceLastAttempt = now - lastAttempt;
    
    // Increase wait time based on number of attempts
    const minWaitTime = Math.min(1500 * Math.pow(1.5, connectionAttempts[streamKey] - 1), 10000);
    
    if (timeSinceLastAttempt < minWaitTime) {
      const waitTime = minWaitTime - timeSinceLastAttempt;
      console.log(`Rate limiting WebSocket connection for ${streamKey}, waiting ${waitTime}ms (attempt ${connectionAttempts[streamKey]})`);
      await new Promise(resolve => setTimeout(resolve, waitTime));
    }
    
    lastConnectionAttempt[streamKey] = Date.now();

    // Initialize connection attempts counter if it doesn't exist
    if (typeof connectionAttempts[streamKey] !== 'number') {
      connectionAttempts[streamKey] = 0;
    }
    
    // Track connection attempts for backoff
    connectionAttempts[streamKey] += 1;
    
    // Exponential backoff after multiple failures
    if (connectionAttempts[streamKey] > 1) {
      const backoffDelay = Math.min(2000 * Math.pow(2, connectionAttempts[streamKey] - 1), 15000);
      console.log(`WebSocket connection attempt #${connectionAttempts[streamKey]} for ${streamKey}, waiting ${backoffDelay}ms`);
      await new Promise(resolve => setTimeout(resolve, backoffDelay));
    }

    // Close existing connection for this stream type if it exists
    if (activeWebSockets[streamKey]) {
      console.log(`Closing existing WebSocket for ${streamKey} before reconnecting.`);
      activeWebSockets[streamKey].close(1000, 'Client replacing connection');
      delete activeWebSockets[streamKey];
      
      // Reset connection attempts counter when manually closing
      connectionAttempts[streamKey] = 0;
      
      // Add a longer delay to ensure the connection is properly closed
      await new Promise(resolve => setTimeout(resolve, 1500));
    }

    console.log(`Starting WebSocket connection for ${streamKey} to ${wsUrl}`);
    const ws = new WebSocket(wsUrl);
    activeWebSockets[streamKey] = ws;

    // Set up connection timeout
    const connectionTimeout = setTimeout(() => {
      if (ws.readyState === WebSocket.CONNECTING) {
        console.error(`WebSocket connection timeout for ${streamKey}`);
        ws.close();
        delete activeWebSockets[streamKey];
        connectionInProgress[streamKey] = false;
      }
    }, 10000); // 10 second timeout

    ws.onopen = () => {
      console.log(`WebSocket connected for ${streamKey}: ${wsUrl}`);
      clearTimeout(connectionTimeout);
      
      // Reset connection attempts counter on successful connection
      connectionAttempts[streamKey] = 0;
      connectionInProgress[streamKey] = false;
      
      if (streamType === 'candles') {
        dispatch(setCandlesWsConnected(true));
      } else if (streamType === 'orderbook') {
        dispatch(setOrderBookWsConnected(true));
      } else if (streamType === 'ticker') {
        dispatch(setTickerWsConnected(true));
      }
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Route messages based on their actual type, not just the stream type
        if (data.type === 'candle_update') {
          dispatch(updateCandlesFromWebSocket(data));
        } else if (data.type === 'orderbook_update') {
          dispatch(updateOrderBookFromWebSocket(data));
        } else if (data.type === 'ticker_update') {
          dispatch(updateTickerFromWebSocket(data));
        } else {
          // Fallback to stream-based routing for backwards compatibility
          if (streamType === 'candles') {
            dispatch(updateCandlesFromWebSocket(data));
          } else if (streamType === 'orderbook') {
            dispatch(updateOrderBookFromWebSocket(data));
          } else if (streamType === 'ticker') {
            dispatch(updateTickerFromWebSocket(data));
          }
        }
      } catch (error) {
        console.error(`Error parsing WebSocket message for ${streamKey}:`, error);
      }
    };

    ws.onerror = (error) => {
      const attemptCount = connectionAttempts[streamKey] || 0;
      console.error(`WebSocket error for ${streamKey} (attempt #${attemptCount}):`, error);
      console.error(`Failed to connect to: ${wsUrl}`);
      console.error(`Debug info:
        - Stream Key: ${streamKey}
        - WebSocket URL: ${wsUrl}
        - Environment WS Base URL: ${process.env.REACT_APP_WS_BASE_URL || 'not set'}
        - Connection Attempts: ${attemptCount}
        - WebSocket State: ${ws.readyState} (0=CONNECTING, 1=OPEN, 2=CLOSING, 3=CLOSED)
        - Browser: ${navigator.userAgent}`);
      
      clearTimeout(connectionTimeout);
      connectionInProgress[streamKey] = false;
      
      // Only update state if this is still the active WebSocket
      if (activeWebSockets[streamKey] === ws) {
        if (streamType === 'candles') {
          dispatch(setCandlesWsConnected(false));
        } else if (streamType === 'orderbook') {
          dispatch(setOrderBookWsConnected(false));
        } else if (streamType === 'ticker') {
          dispatch(setTickerWsConnected(false));
        }
      }
    };

    ws.onclose = (event) => {
      console.log(`WebSocket closed for ${streamKey}:`, event.code, event.reason);
      clearTimeout(connectionTimeout);
      connectionInProgress[streamKey] = false;
      
      // Check if this WebSocket is still the active one for this stream
      // If not, it means it was replaced and we shouldn't dispatch state updates
      if (activeWebSockets[streamKey] === ws) {
        if (streamType === 'candles') {
          dispatch(setCandlesWsConnected(false));
        } else if (streamType === 'orderbook') {
          dispatch(setOrderBookWsConnected(false));
        } else if (streamType === 'ticker') {
          dispatch(setTickerWsConnected(false));
        }
        delete activeWebSockets[streamKey];

        // Attempt to reconnect if not a clean close (code 1000) and attempts are reasonable
        // Also check for code 1006 which is an abnormal closure
        if ((event.code !== 1000 && event.code !== 1006) ||
            (event.code === 1006 && connectionAttempts[streamKey] < 3)) {
          const reconnectDelay = Math.min(5000 * connectionAttempts[streamKey], 30000);
          console.log(`Attempting to reconnect WebSocket for ${streamKey} in ${reconnectDelay}ms...`);
          setTimeout(() => {
            // Only reconnect if this stream key is not already connected
            if (!activeWebSockets[streamKey]) {
              connectWebSocketStream(dispatch, symbol, streamType, timeframe);
            }
          }, reconnectDelay);
        } else if (event.code === 1006) {
          console.error(`WebSocket for ${streamKey} closed abnormally after ${connectionAttempts[streamKey]} attempts. Not reconnecting.`);
        }
      } else {
        console.log(`WebSocket close event for ${streamKey} ignored - not the active connection`);
      }
    };

  } catch (error) {
    console.error(`Error creating WebSocket connection for ${streamKey}:`, error);
    connectionInProgress[streamKey] = false;
    
    if (streamType === 'candles') {
      dispatch(setCandlesWsConnected(false));
    } else if (streamType === 'orderbook') {
      dispatch(setOrderBookWsConnected(false));
    }
  }
};

/**
 * Disconnects a specific WebSocket stream.
 * @param streamType - The type of stream ('candles', 'orderbook', or 'ticker').
 * @param symbol - The trading symbol.
 * @param timeframe - Optional, for 'candles' stream.
 */
export const disconnectWebSocketStream = (
  streamType: 'candles' | 'orderbook' | 'ticker',
  symbol: string,
  timeframe?: string
) => {
  const streamKey = timeframe ? `${streamType}-${symbol}-${timeframe}` : `${streamType}-${symbol}`;
  if (activeWebSockets[streamKey]) {
    console.log(`Manually closing WebSocket for ${streamKey}`);
    // Remove all event handlers first to prevent any further updates
    const ws = activeWebSockets[streamKey];
    ws.onopen = null;
    ws.onmessage = null;
    ws.onerror = null;
    ws.onclose = null;
    
    // Close the connection
    ws.close(1000, 'Client initiated close');
    delete activeWebSockets[streamKey];
  }
  
  // Clean up tracking variables
  delete connectionAttempts[streamKey];
  delete lastConnectionAttempt[streamKey];
  delete connectionInProgress[streamKey];
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
  
  // Clean up all tracking variables
  Object.keys(connectionAttempts).forEach(key => delete connectionAttempts[key]);
  Object.keys(lastConnectionAttempt).forEach(key => delete lastConnectionAttempt[key]);
  Object.keys(connectionInProgress).forEach(key => delete connectionInProgress[key]);
};