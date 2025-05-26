import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useAppSelector, useAppDispatch } from '../../store/hooks';
import { fetchOrderBook, updateOrderBookFromWebSocket } from '../../features/marketData/marketDataSlice';
import './OrderBookDisplay.css';

/**
 * Props for the OrderBookDisplay component
 */
interface OrderBookDisplayProps {
  /** Optional CSS class name for styling */
  className?: string;
}

/**
 * OrderBookDisplay component shows real-time bid/ask prices and volumes.
 *
 * Displays market depth data with live updates via WebSocket connection.
 * Shows configurable number of price levels and provides visual indicators
 * for market liquidity and spread.
 */
const OrderBookDisplay: React.FC<OrderBookDisplayProps> = ({ className }) => {
  const dispatch = useAppDispatch();
  const { selectedSymbol, currentOrderBook, isLoading, error } = useAppSelector(
    (state) => state.marketData
  );

  // Local state for WebSocket and display configuration
  const [wsConnected, setWsConnected] = useState(false);
  const [wsError, setWsError] = useState<string | null>(null);
  const [displayDepth, setDisplayDepth] = useState(10);
  const wsRef = useRef<WebSocket | null>(null);

  /**
   * Establish WebSocket connection for real-time order book updates.
   *
   * Closes any existing connection before creating a new one to prevent
   * multiple connections for the same symbol.
   *
   * @param symbol - Trading symbol to subscribe to (e.g., 'BTCUSDT')
   */
  const connectWebSocket = useCallback((symbol: string) => {
    // Close existing connection if any to prevent memory leaks
    if (wsRef.current) {
      wsRef.current.close();
    }

    const wsUrl = `ws://localhost:8000/ws/orderbook/${symbol}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log(`WebSocket connected for ${symbol}`);
      setWsConnected(true);
      setWsError(null);
    };

    ws.onmessage = (event) => {
      try {
        const orderBookData = JSON.parse(event.data);
        dispatch(updateOrderBookFromWebSocket(orderBookData));
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
        setWsError('Failed to parse order book data');
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setWsError('WebSocket connection error');
      setWsConnected(false);
    };

    ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      setWsConnected(false);
      
      // Attempt to reconnect if it wasn't a clean close and we still have a selected symbol
      if (event.code !== 1000 && selectedSymbol) {
        setTimeout(() => {
          if (selectedSymbol) {
            connectWebSocket(selectedSymbol);
          }
        }, 3000);
      }
    };

    wsRef.current = ws;
  }, [dispatch, selectedSymbol]);

  // Effect to handle symbol changes and WebSocket connections
  useEffect(() => {
    if (selectedSymbol) {
      // Fetch initial order book data
      dispatch(fetchOrderBook(selectedSymbol));
      
      // Establish WebSocket connection
      connectWebSocket(selectedSymbol);
    } else {
      // Close WebSocket if no symbol selected
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setWsConnected(false);
      setWsError(null);
    }

    // Cleanup on unmount or symbol change
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [selectedSymbol, dispatch, connectWebSocket]);

  // Format price and amount for display
  const formatPrice = (price: number): string => {
    return price.toFixed(8).replace(/\.?0+$/, '');
  };

  const formatAmount = (amount: number): string => {
    return amount.toFixed(8).replace(/\.?0+$/, '');
  };

  // Get sliced bids and asks based on display depth
  const displayBids = currentOrderBook?.bids.slice(0, displayDepth) || [];
  const displayAsks = currentOrderBook?.asks.slice(0, displayDepth) || [];

  // Render loading state
  if (isLoading && !currentOrderBook) {
    return (
      <div className={`order-book-display ${className || ''}`}>
        <div className="order-book-header">
          <h3>Order Book</h3>
          {selectedSymbol && (
            <span className="symbol-label">{selectedSymbol}</span>
          )}
        </div>
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading order book...</p>
        </div>
      </div>
    );
  }

  // Render error state
  if (error || wsError) {
    return (
      <div className={`order-book-display ${className || ''}`}>
        <div className="order-book-header">
          <h3>Order Book</h3>
          {selectedSymbol && (
            <span className="symbol-label">{selectedSymbol}</span>
          )}
        </div>
        <div className="error-state">
          <p className="error-message">
            {error || wsError || 'Failed to load order book'}
          </p>
          {selectedSymbol && (
            <button 
              onClick={() => dispatch(fetchOrderBook(selectedSymbol))}
              className="retry-button"
            >
              Retry
            </button>
          )}
        </div>
      </div>
    );
  }

  // Render no symbol selected state
  if (!selectedSymbol) {
    return (
      <div className={`order-book-display ${className || ''}`}>
        <div className="order-book-header">
          <h3>Order Book</h3>
        </div>
        <div className="no-symbol-state">
          <p>Select a symbol to view order book</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`order-book-display ${className || ''}`}>
      <div className="order-book-header">
        <h3>Order Book</h3>
        <div className="header-controls">
          <span className="symbol-label">{selectedSymbol}</span>
          <div className="connection-status">
            <span className={`status-indicator ${wsConnected ? 'connected' : 'disconnected'}`}>
              {wsConnected ? '●' : '○'}
            </span>
            <span className="status-text">
              {wsConnected ? 'Live' : 'Disconnected'}
            </span>
          </div>
        </div>
      </div>

      <div className="depth-selector">
        <label htmlFor="depth-select">Display Depth:</label>
        <select
          id="depth-select"
          value={displayDepth}
          onChange={(e) => setDisplayDepth(Number(e.target.value))}
          className="depth-select"
        >
          <option value={5}>5 levels</option>
          <option value={10}>10 levels</option>
          <option value={20}>20 levels</option>
          <option value={50}>50 levels</option>
        </select>
      </div>

      <div className="order-book-content">
        {/* Asks Section */}
        <div className="asks-section">
          <div className="section-header asks-header">
            <span className="price-header">Price</span>
            <span className="amount-header">Amount</span>
            <span className="total-header">Total</span>
          </div>
          <div className="asks-list">
            {displayAsks.length > 0 ? (
              displayAsks.map((ask, index) => {
                const total = displayAsks
                  .slice(0, index + 1)
                  .reduce((sum, level) => sum + level.amount, 0);
                
                return (
                  <div key={`ask-${ask.price}-${index}`} className="order-level ask-level">
                    <span className="price ask-price">{formatPrice(ask.price)}</span>
                    <span className="amount">{formatAmount(ask.amount)}</span>
                    <span className="total">{formatAmount(total)}</span>
                  </div>
                );
              })
            ) : (
              <div className="no-data">No asks available</div>
            )}
          </div>
        </div>

        {/* Spread Section */}
        {currentOrderBook && displayBids.length > 0 && displayAsks.length > 0 && (
          <div className="spread-section">
            <div className="spread-info">
              <span className="spread-label">Spread:</span>
              <span className="spread-value">
                {formatPrice(displayAsks[0].price - displayBids[0].price)}
              </span>
              <span className="spread-percentage">
                ({(((displayAsks[0].price - displayBids[0].price) / displayBids[0].price) * 100).toFixed(4)}%)
              </span>
            </div>
          </div>
        )}

        {/* Bids Section */}
        <div className="bids-section">
          <div className="section-header bids-header">
            <span className="price-header">Price</span>
            <span className="amount-header">Amount</span>
            <span className="total-header">Total</span>
          </div>
          <div className="bids-list">
            {displayBids.length > 0 ? (
              displayBids.map((bid, index) => {
                const total = displayBids
                  .slice(0, index + 1)
                  .reduce((sum, level) => sum + level.amount, 0);
                
                return (
                  <div key={`bid-${bid.price}-${index}`} className="order-level bid-level">
                    <span className="price bid-price">{formatPrice(bid.price)}</span>
                    <span className="amount">{formatAmount(bid.amount)}</span>
                    <span className="total">{formatAmount(total)}</span>
                  </div>
                );
              })
            ) : (
              <div className="no-data">No bids available</div>
            )}
          </div>
        </div>
      </div>

      {/* Timestamp */}
      {currentOrderBook && (
        <div className="order-book-footer">
          <span className="timestamp">
            Last updated: {new Date(currentOrderBook.timestamp).toLocaleTimeString()}
          </span>
        </div>
      )}

    </div>
  );
};

export default OrderBookDisplay;