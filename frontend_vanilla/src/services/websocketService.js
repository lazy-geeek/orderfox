
import { 
  updateCandlesFromWebSocket, 
  updateOrderBookFromWebSocket,
  updateTickerFromWebSocket,
  setCandlesWsConnected,
  setOrderBookWsConnected,
  setTickerWsConnected,
  clearOrderBook,
} from '../store/store.js';

const activeWebSockets = {};
const connectionAttempts = {};
const lastConnectionAttempt = {};
const connectionInProgress = {};

const WS_BASE_URL = 'ws://localhost:8000/api/v1';

export const connectWebSocketStream = async (
  symbol,
  streamType,
  timeframe,
  limit
) => {
  const streamKey = timeframe ? `${streamType}-${symbol}-${timeframe}` : `${streamType}-${symbol}`;
  
  const cleanWsBaseUrl = WS_BASE_URL.replace(/\/$/, '');
  
  let wsUrl;
  if (timeframe) {
    wsUrl = `${cleanWsBaseUrl}/ws/${streamType}/${symbol}/${timeframe}`;
  } else {
    wsUrl = `${cleanWsBaseUrl}/ws/${streamType}/${symbol}`;
    if (streamType === 'orderbook' && limit) {
      wsUrl += `?limit=${limit}`;
    }
  }

  if (connectionInProgress[streamKey]) {
    console.log(`WebSocket connection already in progress for ${streamKey}, skipping duplicate attempt`);
    return;
  }

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
    const now = Date.now();
    const lastAttempt = lastConnectionAttempt[streamKey] || 0;
    const timeSinceLastAttempt = now - lastAttempt;
    
    const minWaitTime = Math.min(1500 * Math.pow(1.5, connectionAttempts[streamKey] - 1), 10000);
    
    if (timeSinceLastAttempt < minWaitTime) {
      const waitTime = minWaitTime - timeSinceLastAttempt;
      console.log(`Rate limiting WebSocket connection for ${streamKey}, waiting ${waitTime}ms (attempt ${connectionAttempts[streamKey]})`);
      await new Promise(resolve => setTimeout(resolve, waitTime));
    }
    
    lastConnectionAttempt[streamKey] = Date.now();

    if (typeof connectionAttempts[streamKey] !== 'number') {
      connectionAttempts[streamKey] = 0;
    }
    
    connectionAttempts[streamKey] += 1;
    
    if (connectionAttempts[streamKey] > 1) {
      const backoffDelay = Math.min(2000 * Math.pow(2, connectionAttempts[streamKey] - 1), 15000);
      console.log(`WebSocket connection attempt #${connectionAttempts[streamKey]} for ${streamKey}, waiting ${backoffDelay}ms`);
      await new Promise(resolve => setTimeout(resolve, backoffDelay));
    }

    if (activeWebSockets[streamKey]) {
      console.log(`Closing existing WebSocket for ${streamKey} before reconnecting.`);
      activeWebSockets[streamKey].close(1000, 'Client replacing connection');
      delete activeWebSockets[streamKey];
      
      connectionAttempts[streamKey] = 0;
      
      await new Promise(resolve => setTimeout(resolve, 1500));
    }

    console.log(`Starting WebSocket connection for ${streamKey} to ${wsUrl}`);
    const ws = new WebSocket(wsUrl);
    activeWebSockets[streamKey] = ws;

    const connectionTimeout = setTimeout(() => {
      if (ws.readyState === WebSocket.CONNECTING) {
        console.error(`WebSocket connection timeout for ${streamKey}`);
        ws.close();
        delete activeWebSockets[streamKey];
        connectionInProgress[streamKey] = false;
      }
    }, 10000);

    ws.onopen = () => {
      console.log(`WebSocket connected for ${streamKey}: ${wsUrl}`);
      clearTimeout(connectionTimeout);
      
      connectionAttempts[streamKey] = 0;
      connectionInProgress[streamKey] = false;
      
      if (streamType === 'candles') {
        setCandlesWsConnected(true);
      } else if (streamType === 'orderbook') {
        setOrderBookWsConnected(true);
      } else if (streamType === 'ticker') {
        setTickerWsConnected(true);
      }
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'candle_update') {
          updateCandlesFromWebSocket(data);
        } else if (data.type === 'orderbook_update') {
          updateOrderBookFromWebSocket(data);
        } else if (data.type === 'ticker_update') {
          updateTickerFromWebSocket(data);
        } else {
          if (streamType === 'candles') {
            updateCandlesFromWebSocket(data);
          } else if (streamType === 'orderbook') {
            updateOrderBookFromWebSocket(data);
          } else if (streamType === 'ticker') {
            updateTickerFromWebSocket(data);
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
      
      clearTimeout(connectionTimeout);
      connectionInProgress[streamKey] = false;
      
      if (activeWebSockets[streamKey] === ws) {
        if (streamType === 'candles') {
          setCandlesWsConnected(false);
        } else if (streamType === 'orderbook') {
          setOrderBookWsConnected(false);
        } else if (streamType === 'ticker') {
          setTickerWsConnected(false);
        }
      }
    };

    ws.onclose = (event) => {
      console.log(`WebSocket closed for ${streamKey}:`, event.code, event.reason);
      clearTimeout(connectionTimeout);
      connectionInProgress[streamKey] = false;
      
      if (activeWebSockets[streamKey] === ws) {
        if (streamType === 'candles') {
          setCandlesWsConnected(false);
        } else if (streamType === 'orderbook') {
          setOrderBookWsConnected(false);
        } else if (streamType === 'ticker') {
          setTickerWsConnected(false);
        }
        delete activeWebSockets[streamKey];

        if ((event.code !== 1000 && event.code !== 1006) ||
            (event.code === 1006 && connectionAttempts[streamKey] < 3)) {
          const reconnectDelay = Math.min(5000 * connectionAttempts[streamKey], 30000);
          console.log(`Attempting to reconnect WebSocket for ${streamKey} in ${reconnectDelay}ms...`);
          setTimeout(() => {
            if (!activeWebSockets[streamKey]) {
              connectWebSocketStream(symbol, streamType, timeframe);
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
      setCandlesWsConnected(false);
    } else if (streamType === 'orderbook') {
      setOrderBookWsConnected(false);
    }
  }
};

export const disconnectWebSocketStream = (
  streamType,
  symbol,
  timeframe
) => {
  const streamKey = timeframe ? `${streamType}-${symbol}-${timeframe}` : `${streamType}-${symbol}`;
  if (activeWebSockets[streamKey]) {
    console.log(`Manually closing WebSocket for ${streamKey}`);
    const ws = activeWebSockets[streamKey];
    ws.onopen = null;
    ws.onmessage = null;
    ws.onerror = null;
    ws.onclose = null;
    
    ws.close(1000, 'Client initiated close');
    delete activeWebSockets[streamKey];
  }
  
  delete connectionAttempts[streamKey];
  delete lastConnectionAttempt[streamKey];
  delete connectionInProgress[streamKey];
};

export const disconnectAllWebSockets = () => {
  console.log('Disconnecting all active WebSockets...');
  for (const key in activeWebSockets) {
    if (activeWebSockets.hasOwnProperty(key)) {
      activeWebSockets[key].close(1000, 'Client initiated close (all)');
      delete activeWebSockets[key];
    }
  }
  
  Object.keys(connectionAttempts).forEach(key => delete connectionAttempts[key]);
  Object.keys(lastConnectionAttempt).forEach(key => delete lastConnectionAttempt[key]);
  Object.keys(connectionInProgress).forEach(key => delete connectionInProgress[key]);
};
