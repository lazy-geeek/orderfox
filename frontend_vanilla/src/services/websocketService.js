
import { 
  updateCandlesFromWebSocket,
  updateOrderBookFromWebSocket,
  updateTickerFromWebSocket,
  setCandlesWsConnected,
  setOrderBookWsConnected,
  setTickerWsConnected,
  clearOrderBook,
} from '../store/store.js';
import { WS_BASE_URL } from '../config/env.js';
import { featureFlags } from './featureFlags.js';
import { logger } from '../utils/logger.js';

const activeWebSockets = {};
const connectionAttempts = {};
const lastConnectionAttempt = {};
const connectionInProgress = {};
const lastMessageTime = {};
const streamParameters = {}; // Store connection parameters for reconnection
let isPageVisible = !document.hidden;


export const connectWebSocketStream = async (
  symbol,
  streamType,
  timeframe,
  limit,
  rounding = null
) => {
  const streamKey = timeframe ? `${streamType}-${symbol}-${timeframe}` : `${streamType}-${symbol}`;
  
  // Store connection parameters for later reconnection
  streamParameters[streamKey] = { symbol, streamType, timeframe, limit, rounding };
  
  const cleanWsBaseUrl = WS_BASE_URL.replace(/\/$/, '');
  
  let wsUrl;
  if (timeframe) {
    wsUrl = `${cleanWsBaseUrl}/ws/${streamType}/${symbol}/${timeframe}`;
  } else {
    wsUrl = `${cleanWsBaseUrl}/ws/${streamType}/${symbol}`;
    if (streamType === 'orderbook') {
      const params = new URLSearchParams();
      
      // Always include limit if provided
      if (limit) {
        params.append('limit', limit);
      }
      
      // Include backend aggregation parameters if enabled
      if (featureFlags.useBackendAggregation()) {
        params.append('aggregate', 'true');
        params.append('use_depth_cache', 'true');
        if (rounding) {
          params.append('rounding', rounding);
        }
      }
      
      if (params.toString()) {
        wsUrl += `?${params.toString()}`;
      }
    }
  }

  // Fix WebSocket URL for proxy setup - convert relative URLs to WebSocket protocol
  if (wsUrl.startsWith('/')) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    wsUrl = `${protocol}//${host}${wsUrl}`;
  }

  if (connectionInProgress[streamKey]) {
    logger.debug(`WebSocket connection already in progress for ${streamKey}, skipping duplicate attempt`);
    return;
  }

  if (activeWebSockets[streamKey]) {
    const currentState = activeWebSockets[streamKey].readyState;
    if (currentState === WebSocket.OPEN) {
      logger.debug(`WebSocket for ${streamKey} is already connected, skipping new connection attempt`);
      return;
    } else if (currentState === WebSocket.CONNECTING) {
      logger.debug(`WebSocket for ${streamKey} is already connecting, skipping duplicate attempt`);
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
      logger.debug(`Rate limiting WebSocket connection for ${streamKey}, waiting ${waitTime}ms (attempt ${connectionAttempts[streamKey]})`);
      await new Promise(resolve => setTimeout(resolve, waitTime));
    }
    
    lastConnectionAttempt[streamKey] = Date.now();

    if (typeof connectionAttempts[streamKey] !== 'number') {
      connectionAttempts[streamKey] = 0;
    }
    
    connectionAttempts[streamKey] += 1;
    
    if (connectionAttempts[streamKey] > 1) {
      const backoffDelay = Math.min(2000 * Math.pow(2, connectionAttempts[streamKey] - 1), 15000);
      logger.debug(`WebSocket connection attempt #${connectionAttempts[streamKey]} for ${streamKey}, waiting ${backoffDelay}ms`);
      await new Promise(resolve => setTimeout(resolve, backoffDelay));
    }

    if (activeWebSockets[streamKey]) {
      logger.debug(`Closing existing WebSocket for ${streamKey} before reconnecting.`);
      activeWebSockets[streamKey].close(1000, 'Client replacing connection');
      delete activeWebSockets[streamKey];
      
      connectionAttempts[streamKey] = 0;
      
      await new Promise(resolve => setTimeout(resolve, 1500));
    }

    logger.debug(`Starting WebSocket connection for ${streamKey} to ${wsUrl}`);
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
      logger.debug(`WebSocket connected for ${streamKey}: ${wsUrl}`);
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
        // Track last message time for connection health monitoring
        lastMessageTime[streamKey] = Date.now();
        
        const data = JSON.parse(event.data);
        
        
        // Protocol version negotiation - detect message format
        const messageVersion = data.version || '1.0';
        const isNewFormat = data.aggregated === true || messageVersion !== '1.0';
        
        if (isNewFormat && featureFlags.useBackendAggregation()) {
          logger.debug(`Received new format message (v${messageVersion}) for ${streamKey}`);
        } else if (isNewFormat && !featureFlags.useBackendAggregation()) {
          logger.warn(`Received new format message but backend aggregation disabled, processing as legacy format`);
        }
        
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
      logger.debug(`WebSocket closed for ${streamKey}:`, event.code, event.reason);
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
          logger.debug(`Attempting to reconnect WebSocket for ${streamKey} in ${reconnectDelay}ms...`);
          setTimeout(() => {
            if (!activeWebSockets[streamKey]) {
              connectWebSocketStream(symbol, streamType, timeframe, limit, rounding);
            }
          }, reconnectDelay);
        } else if (event.code === 1006) {
          console.error(`WebSocket for ${streamKey} closed abnormally after ${connectionAttempts[streamKey]} attempts. Not reconnecting.`);
        }
      } else {
        logger.debug(`WebSocket close event for ${streamKey} ignored - not the active connection`);
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
    logger.debug(`Manually closing WebSocket for ${streamKey}`);
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
  delete lastMessageTime[streamKey];
  delete streamParameters[streamKey];
};

export const disconnectAllWebSockets = () => {
  logger.debug('Disconnecting all active WebSockets...');
  for (const key in activeWebSockets) {
    if (activeWebSockets.hasOwnProperty(key)) {
      activeWebSockets[key].close(1000, 'Client initiated close (all)');
      delete activeWebSockets[key];
    }
  }
  
  Object.keys(connectionAttempts).forEach(key => delete connectionAttempts[key]);
  Object.keys(lastConnectionAttempt).forEach(key => delete lastConnectionAttempt[key]);
  Object.keys(connectionInProgress).forEach(key => delete connectionInProgress[key]);
  Object.keys(lastMessageTime).forEach(key => delete lastMessageTime[key]);
  Object.keys(streamParameters).forEach(key => delete streamParameters[key]);
};

// Handle page visibility changes to manage WebSocket connections when tab is not focused
document.addEventListener('visibilitychange', () => {
  const wasVisible = isPageVisible;
  isPageVisible = !document.hidden;
  
  if (wasVisible && !isPageVisible) {
    // Page became hidden - log but keep connections (browsers throttle but don't kill WebSockets)
    console.log('Page became hidden, WebSocket connections may be throttled by browser');
  } else if (!wasVisible && isPageVisible) {
    // Page became visible again - check WebSocket health and reconnect if needed
    logger.debug('Page became visible, checking WebSocket connection health');
    checkAndRefreshConnections();
  }
});

// Function to check and refresh WebSocket connections when page becomes visible
function checkAndRefreshConnections() {
  const staleConnections = [];
  const now = Date.now();
  const staleThreshold = 30000; // Reduced to 30 seconds for faster detection
  
  for (const [streamKey, ws] of Object.entries(activeWebSockets)) {
    const lastMessage = lastMessageTime[streamKey] || 0;
    const timeSinceLastMessage = now - lastMessage;
    
    // More aggressive stale connection detection for page visibility changes
    // When page becomes visible, refresh connections that haven't received messages recently
    // or are in a bad state
    if (ws.readyState === WebSocket.CLOSED || 
        ws.readyState === WebSocket.CLOSING || 
        timeSinceLastMessage > staleThreshold) {
      staleConnections.push(streamKey);
      console.log(`Stale connection detected for ${streamKey}: readyState=${ws.readyState}, timeSinceLastMessage=${timeSinceLastMessage}ms`);
    }
  }
  
  // If no stale connections detected but page was hidden, force a data refresh
  // This ensures we get latest data even if WebSocket appears healthy
  if (staleConnections.length === 0) {
    logger.debug('No stale connections found, but forcing data refresh after page visibility change');
    forceDataRefresh();
  }
  
  // Reconnect stale connections
  if (staleConnections.length > 0) {
    logger.debug(`Found ${staleConnections.length} stale WebSocket connections, reconnecting...`);
    staleConnections.forEach(streamKey => {
      // Use stored parameters if available
      const params = streamParameters[streamKey];
      if (params) {
        const { symbol, streamType, timeframe, limit, rounding } = params;
        
        // Clean up old connection
        delete activeWebSockets[streamKey];
        delete connectionAttempts[streamKey];
        delete lastConnectionAttempt[streamKey];
        delete connectionInProgress[streamKey];
        delete lastMessageTime[streamKey];
        delete streamParameters[streamKey];
        
        // Reconnect after a short delay
        setTimeout(() => {
          connectWebSocketStream(symbol, streamType, timeframe, limit, rounding);
        }, 1000);
      } else {
        // Fallback to parsing streamKey (legacy support)
        const parts = streamKey.split('-');
        if (parts.length >= 2) {
          const streamType = parts[0];
          const symbol = parts[1];
          const timeframe = parts.length > 2 ? parts[2] : null;
          
          // Clean up old connection
          delete activeWebSockets[streamKey];
          delete connectionAttempts[streamKey];
          delete lastConnectionAttempt[streamKey];
          delete connectionInProgress[streamKey];
          delete lastMessageTime[streamKey];
          
          // Reconnect after a short delay
          setTimeout(() => {
            connectWebSocketStream(symbol, streamType, timeframe);
          }, 1000);
        }
      }
    });
  }
}

// Force refresh data by fetching latest from API when page becomes visible
async function forceDataRefresh() {
  const { state, fetchOrderBook, fetchCandles } = await import('../store/store.js');
  
  if (state.selectedSymbol) {
    console.log('Forcing data refresh for symbol:', state.selectedSymbol);
    
    // Refresh orderbook data
    if (state.selectedRounding && state.displayDepth) {
      const { getValidOrderBookLimit } = await import('../store/store.js');
      const limit = getValidOrderBookLimit(state.displayDepth);
      await fetchOrderBook(state.selectedSymbol, limit);
    }
    
    // Refresh candle data
    if (state.selectedTimeframe) {
      await fetchCandles(state.selectedSymbol, state.selectedTimeframe, 100);
    }
  }
}
