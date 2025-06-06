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
const connectionAttempts: { [key: string]: number } = {};
const lastConnectionAttempt: { [key: string]: number } = {};
const connectionInProgress: { [key: string]: boolean } = {};

/**
 * Establishes and manages WebSocket connections for market data streams.
 * @param dispatch - The Redux dispatch function.
 * @param symbol - The trading symbol (e.g., 'ETHUSDT').
 * @param streamType - The type of stream ('candles' or 'orderbook').
 * @param timeframe - Optional, for 'candles' stream (e.g., '1m', '5m').
 */
export const connectWebSocketStream = async (
  dispatch: AppDispatch,
  symbol: string,
  streamType: 'candles' | 'orderbook',
  timeframe?: string
) => {
  const streamKey = timeframe ? `${streamType}-${symbol}-${timeframe}` : `${streamType}-${symbol}`;
  const wsBaseUrl = process.env.REACT_APP_WS_BASE_URL || 'ws://localhost:8000/api/v1';
  const wsUrl = timeframe
    ? `${wsBaseUrl}/ws/${streamType}/${symbol}/${timeframe}`
    : `${wsBaseUrl}/ws/${streamType}/${symbol}`;

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
    
    if (timeSinceLastAttempt < 1500) { // Wait at least 1.5 seconds between attempts
      const waitTime = 1500 - timeSinceLastAttempt;
      console.log(`Rate limiting WebSocket connection for ${streamKey}, waiting ${waitTime}ms`);
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
      const attemptCount = connectionAttempts[streamKey] || 0;
      console.error(`WebSocket error for ${streamKey} (attempt #${attemptCount}):`, error);
      console.error(`Failed to connect to: ${wsUrl}`);
      console.error(`Debug info:
        - Stream Key: ${streamKey}
        - WebSocket URL: ${wsUrl}
        - Environment WS Base URL: ${process.env.REACT_APP_WS_BASE_URL || 'not set'}
        - Connection Attempts: ${attemptCount}
        - Browser: ${navigator.userAgent}`);
      
      clearTimeout(connectionTimeout);
      connectionInProgress[streamKey] = false;
      
      if (streamType === 'candles') {
        dispatch(setCandlesWsConnected(false));
      } else if (streamType === 'orderbook') {
        dispatch(setOrderBookWsConnected(false));
      }
    };

    ws.onclose = (event) => {
      console.log(`WebSocket closed for ${streamKey}:`, event.code, event.reason);
      clearTimeout(connectionTimeout);
      connectionInProgress[streamKey] = false;
      
      if (streamType === 'candles') {
        dispatch(setCandlesWsConnected(false));
      } else if (streamType === 'orderbook') {
        dispatch(setOrderBookWsConnected(false));
      }
      delete activeWebSockets[streamKey];

      // Attempt to reconnect if not a clean close (code 1000) and attempts are reasonable
      if (event.code !== 1000 && connectionAttempts[streamKey] < 5) {
        const reconnectDelay = Math.min(5000 * connectionAttempts[streamKey], 30000);
        console.log(`Attempting to reconnect WebSocket for ${streamKey} in ${reconnectDelay}ms...`);
        setTimeout(() => {
          connectWebSocketStream(dispatch, symbol, streamType, timeframe);
        }, reconnectDelay);
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
    activeWebSockets[streamKey].close(1000, 'Client initiated close');
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