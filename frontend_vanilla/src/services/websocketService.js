
import { 
  updateCandlesFromWebSocket,
  updateCandlesFromHistoricalData,
  updateOrderBookFromWebSocket,
  updateTickerFromWebSocket,
  updateTradesFromWebSocket,
  setCandlesWsConnected,
  setOrderBookWsConnected,
  setTickerWsConnected,
  setTradesWsConnected,
} from '../store/store.js';
import { WS_BASE_URL } from '../config/env.js';

const activeWebSockets = {};
const connectionAttempts = {};
const lastConnectionAttempt = {};
const connectionInProgress = {};
const lastMessageTime = {};
const connectionParams = {};
let isPageVisible = !document.hidden;


export const connectWebSocketStream = async (
  symbol,
  streamType,
  timeframe,
  limit,
  rounding = null
) => {
  const streamKey = timeframe ? `${streamType}-${symbol}-${timeframe}` : `${streamType}-${symbol}`;
  
  connectionParams[streamKey] = { symbol, streamType, timeframe, limit, rounding };
  
  const cleanWsBaseUrl = WS_BASE_URL.replace(/\/$/, '');
  
  // Convert relative URL to proper WebSocket URL
  const getWebSocketUrl = (path) => {
    if (path.startsWith('ws://') || path.startsWith('wss://')) {
      return path; // Already a proper WebSocket URL
    }
    
    // Convert relative path to WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    return `${protocol}//${host}${path}`;
  };
  
  let wsUrl;
  if (streamType === 'candles' && timeframe) {
    // Candles use timeframe in path
    const basePath = `${cleanWsBaseUrl}/ws/${streamType}/${symbol}/${timeframe}`;
    const fullPath = limit ? `${basePath}?limit=${limit}` : basePath;
    wsUrl = getWebSocketUrl(fullPath);
  } else {
    // Other streams use symbol only in path
    const basePath = `${cleanWsBaseUrl}/ws/${streamType}/${symbol}`;
    
    // Add query parameters
    const params = new URLSearchParams();
    
    if (streamType === 'orderbook' && limit) {
      params.append('limit', limit);
      if (rounding) {
        params.append('rounding', rounding);
      }
    } else if (streamType === 'liquidations' && timeframe) {
      // Support timeframe parameter for liquidations
      params.append('timeframe', timeframe);
    }
    
    const queryString = params.toString();
    const fullPath = queryString ? `${basePath}?${queryString}` : basePath;
    wsUrl = getWebSocketUrl(fullPath);
  }

  if (connectionInProgress[streamKey]) {
    return;
  }

  if (activeWebSockets[streamKey]) {
    const currentState = activeWebSockets[streamKey].readyState;
    if (currentState === WebSocket.OPEN) {
      console.log(`WebSocket ${streamKey} already open, skipping connection`);
      return;
    } else if (currentState === WebSocket.CONNECTING) {
      console.log(`WebSocket ${streamKey} still connecting, skipping connection`);
      return;
    } else if (currentState === WebSocket.CLOSING || currentState === WebSocket.CLOSED) {
      console.log(`WebSocket ${streamKey} is ${currentState === WebSocket.CLOSING ? 'closing' : 'closed'}, cleaning up and creating new connection`);
      // Clean up the old connection
      delete activeWebSockets[streamKey];
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
      await new Promise(resolve => setTimeout(resolve, waitTime));
    }
    
    lastConnectionAttempt[streamKey] = Date.now();

    if (typeof connectionAttempts[streamKey] !== 'number') {
      connectionAttempts[streamKey] = 0;
    }
    
    connectionAttempts[streamKey] += 1;
    
    if (connectionAttempts[streamKey] > 1) {
      const backoffDelay = Math.min(2000 * Math.pow(2, connectionAttempts[streamKey] - 1), 15000);
      await new Promise(resolve => setTimeout(resolve, backoffDelay));
    }

    if (activeWebSockets[streamKey]) {
      activeWebSockets[streamKey].close(1000, 'Client replacing connection');
      delete activeWebSockets[streamKey];
      
      connectionAttempts[streamKey] = 0;
      
      await new Promise(resolve => setTimeout(resolve, 1500));
    }

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
      clearTimeout(connectionTimeout);
      
      connectionAttempts[streamKey] = 0;
      connectionInProgress[streamKey] = false;
      
      if (streamType === 'candles') {
        setCandlesWsConnected(true);
      } else if (streamType === 'orderbook') {
        setOrderBookWsConnected(true);
        // Note: orderBookLoading will be set to false when first message arrives
      } else if (streamType === 'ticker') {
        setTickerWsConnected(true);
      } else if (streamType === 'trades') {
        setTradesWsConnected(true);
      } else if (streamType === 'liquidations') {
        // Liquidations connected - handled by component
      }
    };

    ws.onmessage = (event) => {
      try {
        // Track last message time for connection health monitoring
        lastMessageTime[streamKey] = Date.now();
        
        const data = JSON.parse(event.data);
        
        if (data.type === 'historical_candles') {
          console.log('Received historical candles:', data.count, 'candles for', data.symbol);
          updateCandlesFromHistoricalData(data);
        } else if (data.type === 'candle_update') {
          updateCandlesFromWebSocket(data);
        } else if (data.type === 'orderbook_update') {
          updateOrderBookFromWebSocket(data);
        } else if (data.type === 'ticker_update') {
          updateTickerFromWebSocket(data);
        } else if (data.type === 'trades_update') {
          updateTradesFromWebSocket(data);
        } else if (data.type === 'liquidations' || data.type === 'liquidation') {
          // Handle liquidation data
          if (typeof window !== 'undefined' && window.updateLiquidationDisplay) {
            window.updateLiquidationDisplay(data);
          }
        } else if (data.type === 'liquidation_volume') {
          // Handle liquidation volume updates
          console.log('Received liquidation volume:', data.data?.length, 'records for', data.symbol);
          if (typeof window !== 'undefined' && window.updateLiquidationVolume) {
            window.updateLiquidationVolume(data);
          }
        } else if (data.type === 'heartbeat') {
          // Handle heartbeat messages (keep connection alive)
          // No action needed - just acknowledge receipt
        } else if (data.type === 'param_update_ack') {
          // Parameter update acknowledged
        } else if (data.type === 'params_updated') {
          // Parameter update successful
        } else if (data.type === 'error') {
          console.error('WebSocket error message:', data.message);
          // Handle chart data errors specifically
          if (data.code === 'CHART_DATA_ERROR' && streamType === 'candles') {
            // Show error to user for chart data failures
            console.error('Chart data error:', data.message);
            // Note: In a real app, you might want to show this in the UI
            // For now, we log it clearly for debugging
          }
        } else {
          // Only process known orderbook_update messages in fallback
          if (streamType === 'orderbook' && data.type === 'orderbook_update') {
            updateOrderBookFromWebSocket(data);
          } else if (streamType === 'candles' && data.type === 'candle_update') {
            updateCandlesFromWebSocket(data);
          } else if (streamType === 'ticker' && data.type === 'ticker_update') {
            updateTickerFromWebSocket(data);
          } else if (streamType === 'trades' && data.type === 'trades_update') {
            updateTradesFromWebSocket(data);
          } else {
            console.warn('Unknown WebSocket message type:', data.type, 'for stream:', streamType, data);
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
        } else if (streamType === 'trades') {
          setTradesWsConnected(false);
        } else if (streamType === 'liquidations') {
          // Liquidations disconnected - handled by component
          if (typeof window !== 'undefined' && window.updateLiquidationDisplay) {
            window.updateLiquidationDisplay({ type: 'error', message: 'Connection error' });
          }
        }
      }
    };

    ws.onclose = (event) => {
      clearTimeout(connectionTimeout);
      connectionInProgress[streamKey] = false;
      
      if (activeWebSockets[streamKey] === ws) {
        if (streamType === 'candles') {
          setCandlesWsConnected(false);
        } else if (streamType === 'orderbook') {
          setOrderBookWsConnected(false);
        } else if (streamType === 'ticker') {
          setTickerWsConnected(false);
        } else if (streamType === 'trades') {
          setTradesWsConnected(false);
        } else if (streamType === 'liquidations') {
          // Liquidations disconnected - handled by component
          if (typeof window !== 'undefined' && window.updateLiquidationDisplay) {
            window.updateLiquidationDisplay({ type: 'error', message: 'Connection closed' });
          }
        }
        delete activeWebSockets[streamKey];

        if ((event.code !== 1000 && event.code !== 1006) ||
            (event.code === 1006 && connectionAttempts[streamKey] < 3)) {
          const reconnectDelay = Math.min(5000 * connectionAttempts[streamKey], 30000);
          setTimeout(() => {
            if (!activeWebSockets[streamKey]) {
              const params = connectionParams[streamKey];
              if (params) {
                connectWebSocketStream(params.symbol, params.streamType, params.timeframe, params.limit, params.rounding);
              } else {
                console.error(`Missing connection params for ${streamKey}, cannot reconnect without parameters`);
              }
            }
          }, reconnectDelay);
        } else if (event.code === 1006) {
          console.error(`WebSocket for ${streamKey} closed abnormally after ${connectionAttempts[streamKey]} attempts. Not reconnecting.`);
        }
      }
    };

  } catch (error) {
    console.error(`Error creating WebSocket connection for ${streamKey}:`, error);
    connectionInProgress[streamKey] = false;
    
    if (streamType === 'candles') {
      setCandlesWsConnected(false);
    } else if (streamType === 'orderbook') {
      setOrderBookWsConnected(false);
    } else if (streamType === 'trades') {
      setTradesWsConnected(false);
    }
  }
};

export const sendWebSocketMessage = (streamType, symbol, timeframe, message) => {
  const streamKey = timeframe ? `${streamType}-${symbol}-${timeframe}` : `${streamType}-${symbol}`;
  const ws = activeWebSockets[streamKey];
  
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(message));
    return true;
  } else {
    console.warn(`Cannot send message to ${streamKey}: WebSocket not open`);
    return false;
  }
};

export const updateOrderBookParameters = (symbol, limit, rounding) => {
  const message = {
    type: 'update_params',
    limit: limit,
    rounding: rounding
  };
  return sendWebSocketMessage('orderbook', symbol, null, message);
};

export const disconnectWebSocketStream = (
  streamType,
  symbol,
  timeframe
) => {
  const streamKey = timeframe ? `${streamType}-${symbol}-${timeframe}` : `${streamType}-${symbol}`;
  if (activeWebSockets[streamKey]) {
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
  delete connectionParams[streamKey];
};

export const disconnectAllWebSockets = () => {
  const connectionsToClose = [];
  
  for (const key in activeWebSockets) {
    if (Object.prototype.hasOwnProperty.call(activeWebSockets, key)) {
      const ws = activeWebSockets[key];
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        // Set event handlers to null to prevent error callbacks during shutdown
        ws.onopen = null;
        ws.onmessage = null;
        ws.onerror = null;
        ws.onclose = null;
        
        try {
          ws.close(1000, 'Client initiated close (all)');
          connectionsToClose.push(key);
        } catch (error) {
          // Ignore errors during cleanup - connection might already be closing
          console.warn(`Error closing WebSocket ${key}:`, error.message);
        }
      }
      delete activeWebSockets[key];
    }
  }
  
  if (connectionsToClose.length > 0) {
    console.log(`Disconnected ${connectionsToClose.length} WebSocket connections:`, connectionsToClose);
  }
  
  Object.keys(connectionAttempts).forEach(key => delete connectionAttempts[key]);
  Object.keys(lastConnectionAttempt).forEach(key => delete lastConnectionAttempt[key]);
  Object.keys(connectionInProgress).forEach(key => delete connectionInProgress[key]);
  Object.keys(lastMessageTime).forEach(key => delete lastMessageTime[key]);
  Object.keys(connectionParams).forEach(key => delete connectionParams[key]);
};

// Handle page visibility changes to manage WebSocket connections when tab is not focused
document.addEventListener('visibilitychange', () => {
  const wasVisible = isPageVisible;
  isPageVisible = !document.hidden;
  
  if (wasVisible && !isPageVisible) {
    // Page became hidden - keep connections (browsers throttle but don't kill WebSockets)
  } else if (!wasVisible && isPageVisible) {
    // Page became visible again - check WebSocket health and reconnect if needed
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
    }
  }
  
  // If no stale connections detected but page was hidden, force a data refresh
  // This ensures we get latest data even if WebSocket appears healthy
  if (staleConnections.length === 0) {
    forceDataRefresh();
  }
  
  // Reconnect stale connections
  if (staleConnections.length > 0) {
    staleConnections.forEach(streamKey => {
      // Clean up old connection
      delete activeWebSockets[streamKey];
      delete connectionAttempts[streamKey];
      delete lastConnectionAttempt[streamKey];
      delete connectionInProgress[streamKey];
      delete lastMessageTime[streamKey];
      
      // Reconnect after a short delay using saved parameters
      setTimeout(() => {
        const params = connectionParams[streamKey];
        if (params) {
          connectWebSocketStream(params.symbol, params.streamType, params.timeframe, params.limit, params.rounding);
        } else {
          console.error(`Missing connection params for ${streamKey}, cannot reconnect without parameters`);
        }
      }, 1000);
    });
  }
}

// Force refresh data by fetching latest from API when page becomes visible
async function forceDataRefresh() {
  const { state, fetchOrderBook } = await import('../store/store.js');
  
  if (state.selectedSymbol) {
    // Refresh orderbook data
    if (state.selectedRounding && state.displayDepth) {
      // Send raw display depth - backend handles validation
      const limit = state.displayDepth;
      await fetchOrderBook(state.selectedSymbol, limit);
    }
    
    // Chart data will be refreshed automatically through WebSocket reconnection
  }
}
