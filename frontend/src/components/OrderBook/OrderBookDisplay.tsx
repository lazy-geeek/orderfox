import React, { useEffect, useState, useMemo } from 'react';
import { useAppSelector, useAppDispatch } from '../../store/hooks';
import {
  fetchOrderBook,
  setSelectedRounding,
  setAvailableRoundingOptions,
  stopOrderBookWebSocket,
  setShouldRestartWebSocketAfterFetch,
} from '../../features/marketData/marketDataSlice';
import { formatLargeNumber } from '../../utils/formatting';
import './OrderBookDisplay.css';

/**
 * Helper function to round a value down to the nearest multiple
 */
const roundDown = (value: number, multiple: number): number => {
  if (multiple <= 0) return value;
  // Handle floating point precision by scaling up, rounding, then scaling down
  const scale = 1 / multiple;
  return Math.floor(value * scale) / scale;
};

/**
 * Helper function to round a value up to the nearest multiple
 */
const roundUp = (value: number, multiple: number): number => {
  if (multiple <= 0) return value;
  // Handle floating point precision by scaling up, rounding, then scaling down
  const scale = 1 / multiple;
  return Math.ceil(value * scale) / scale;
};

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
  const {
    selectedSymbol,
    symbolsList,
    currentOrderBook,
    orderBookLoading,
    orderBookError,
    orderBookWsConnected,
    selectedRounding,
    availableRoundingOptions,
  } = useAppSelector((state) => state.marketData);

  const [displayDepth, setDisplayDepth] = useState(10);

  // Get selected symbol data from symbolsList
  const selectedSymbolData = selectedSymbol
    ? symbolsList.find(symbol => symbol.symbol === selectedSymbol)
    : null;

  // Calculate price decimal places based on rounding selection
  const priceDecimalPlaces = useMemo(() => {
    if (selectedRounding !== null && selectedRounding > 0) {
      if (selectedRounding >= 1) {
        return 0;
      } else {
        // Calculate decimal places from rounding value, e.g., 0.1 -> 1, 0.01 -> 2
        return Math.max(0, Math.ceil(-Math.log10(selectedRounding)));
      }
    } else {
      return selectedSymbolData?.pricePrecision ?? 2; // Default to 2 if not available
    }
  }, [selectedRounding, selectedSymbolData]);

  // Memoized aggregation logic for order book data
  const aggregatedOrderBook = useMemo(() => {
    // Return null/empty if no rounding selected or no order book data
    if (selectedRounding === null || !currentOrderBook ||
        !currentOrderBook.bids || !currentOrderBook.asks) {
      return currentOrderBook || { bids: [], asks: [], symbol: '', timestamp: 0 };
    }

    // Aggregate bids (round down)
    const bidsMap = new Map<number, number>();
    currentOrderBook.bids.forEach((bid) => {
      const roundedPrice = roundDown(bid.price, selectedRounding);
      const existingAmount = bidsMap.get(roundedPrice) || 0;
      bidsMap.set(roundedPrice, existingAmount + bid.amount);
    });

    // Convert bids map to array and sort by price descending
    const aggregatedBids = Array.from(bidsMap.entries())
      .map(([price, amount]) => ({ price, amount }))
      .sort((a, b) => b.price - a.price);

    // Aggregate asks (round up)
    const asksMap = new Map<number, number>();
    currentOrderBook.asks.forEach((ask) => {
      const roundedPrice = roundUp(ask.price, selectedRounding);
      const existingAmount = asksMap.get(roundedPrice) || 0;
      asksMap.set(roundedPrice, existingAmount + ask.amount);
    });

    // Convert asks map to array and sort by price ascending
    const aggregatedAsks = Array.from(asksMap.entries())
      .map(([price, amount]) => ({ price, amount }))
      .sort((a, b) => a.price - b.price);

    return {
      symbol: currentOrderBook.symbol,
      bids: aggregatedBids,
      asks: aggregatedAsks,
      timestamp: currentOrderBook.timestamp,
    };
  }, [currentOrderBook, selectedRounding]);

  // Calculate and set available rounding options when symbol data becomes available
  useEffect(() => {
    if (!selectedSymbol || !selectedSymbolData) {
      // Clear options if no symbol is selected or symbol data is not available
      dispatch(setAvailableRoundingOptions({ options: [], defaultRounding: null }));
      return;
    }

    // Skip auto-calculation if availableRoundingOptions are already set (e.g., in tests)
    if (availableRoundingOptions.length > 0) {
      return;
    }

    // Calculate baseRounding from tickSize or pricePrecision
    const baseRounding = selectedSymbolData.tickSize ||
      (1 / (10 ** (selectedSymbolData.pricePrecision || 2)));

    // Generate options array starting with baseRounding
    const options = [baseRounding];
    
    // Get current price for stopping condition (use highest bid if available)
    const currentPrice = currentOrderBook?.bids?.[0]?.price;
    
    // Generate additional options by multiplying by 10
    let nextOption = baseRounding;
    while (options.length < 7) { // Maximum 7 options as a sensible limit
      nextOption = nextOption * 10;
      
      // Stop if rounding becomes too large relative to current price
      // or if we reach a sensible maximum
      if (currentPrice && nextOption > currentPrice / 10) {
        break;
      }
      if (nextOption > 1000) { // Sensible maximum absolute value
        break;
      }
      
      options.push(nextOption);
    }

    // Ensure we have at least 3-4 options if possible
    if (options.length < 3 && !currentPrice) {
      // If we don't have current price data, add a few more options
      let tempOption = baseRounding;
      while (options.length < 4 && tempOption * 10 <= 100) {
        tempOption = tempOption * 10;
        options.push(tempOption);
      }
    }

    // Dispatch the calculated options
    // If there's already a selectedRounding and it's in the new options, keep it
    // Otherwise, use baseRounding as default
    const currentSelectedRounding = selectedRounding;
    const shouldKeepCurrentRounding = currentSelectedRounding !== null &&
      options.includes(currentSelectedRounding);
    
    dispatch(setAvailableRoundingOptions({
      options,
      defaultRounding: shouldKeepCurrentRounding ? currentSelectedRounding : baseRounding
    }));
  }, [
    selectedSymbol,
    selectedSymbolData,
    currentOrderBook?.bids,
    selectedRounding,
    availableRoundingOptions.length,
    dispatch
  ]);

  // Fetch initial order book data when symbol changes
  useEffect(() => {
    if (selectedSymbol) {
      dispatch(fetchOrderBook({ symbol: selectedSymbol }));
    }
  }, [selectedSymbol, dispatch]);

  // Handle rounding change effect - fetch deeper data when symbol or rounding changes
  useEffect(() => {
    // Early return if required data is not available
    if (!selectedSymbol || selectedRounding === null || !selectedSymbolData) {
      return;
    }

    // Get symbolDetails (for tickSize, pricePrecision) and displayDepth from state
    const symbolDetails = selectedSymbolData;
    
    // Calculate baseTickSize = symbolDetails.tickSize || (1 / (10 ** (symbolDetails.pricePrecision || 2)))
    const baseTickSize = symbolDetails.tickSize ||
      (1 / (10 ** (symbolDetails.pricePrecision || 2)));

    // Calculate dynamicLimit for fetchOrderBook (as per task specification)
    const MIN_RAW_LIMIT = 200;
    const MAX_RAW_LIMIT = 1000;
    const AGGRESSIVENESS_FACTOR = 3;
    
    let calculatedLimit = MIN_RAW_LIMIT;
    if (selectedRounding > baseTickSize) {
      calculatedLimit = Math.ceil((selectedRounding / baseTickSize) * displayDepth * AGGRESSIVENESS_FACTOR);
    }
    const finalLimit = Math.max(MIN_RAW_LIMIT, Math.min(calculatedLimit, MAX_RAW_LIMIT));

    // Set flag to indicate WebSocket should be restarted after fetchOrderBook.fulfilled
    const wasWebSocketConnected = orderBookWsConnected;
    if (wasWebSocketConnected) {
      dispatch(setShouldRestartWebSocketAfterFetch(true));
    }

    // Stop WebSocket if currently connected for this symbol
    if (wasWebSocketConnected) {
      dispatch(stopOrderBookWebSocket({ symbol: selectedSymbol }));
    }

    // Dispatch fetchOrderBook with calculated limit
    // The startOrderBookWebSocket will be triggered after fetchOrderBook.fulfilled via listener middleware
    dispatch(fetchOrderBook({ symbol: selectedSymbol, limit: finalLimit }));
  }, [selectedSymbol, selectedRounding, selectedSymbolData, displayDepth, orderBookWsConnected, dispatch]);

  // Note: wsError state is not currently being set by websocketService.
  // If specific UI feedback for WS errors is needed here, websocketService would need to propagate errors.

  // Format price and amount for display
  const formatPrice = (price: number): string => {
    // Always format with appropriate decimal places, determined by priceDecimalPlaces memo
    return price.toFixed(priceDecimalPlaces);
  };

  const formatAmount = (amount: number): string => {
    return formatLargeNumber(amount);
  };

  const formatTotal = (total: number): string => {
    return formatLargeNumber(total);
  };

  // Get sliced bids and asks based on display depth with proper null safety
  // Use aggregated data for display
  const displayBids = aggregatedOrderBook?.bids ? aggregatedOrderBook.bids.slice(0, displayDepth) : [];
  // Asks are typically sorted ascending by price, but displayed descending (highest price at top, lowest at bottom)
  // To achieve "lowest value at the bottom" as per the task, we sort ascending and then reverse for display.
  const displayAsks = aggregatedOrderBook?.asks
    ? [...aggregatedOrderBook.asks].slice(0, displayDepth).reverse()
    : [];

  // Render loading state
  if (orderBookLoading && !currentOrderBook) {
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
  if (orderBookError) { // Removed wsError from condition
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
            {orderBookError || 'Failed to load order book'} {/* Removed wsError */}
          </p>
          {selectedSymbol && (
            <button
              onClick={() => dispatch(fetchOrderBook({ symbol: selectedSymbol }))}
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
            <span className={`status-indicator ${orderBookWsConnected ? 'connected' : 'disconnected'}`}>
              {orderBookWsConnected ? '●' : '○'}
            </span>
            <span className="status-text">
              {orderBookWsConnected ? 'Live' : 'Disconnected'}
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
        
        <div className="rounding-selector-container">
          <label htmlFor="rounding-select">Rounding:</label>
          <select
            id="rounding-select"
            value={selectedRounding || ''}
            onChange={(e) => {
              const value = e.target.value;
              if (value) {
                dispatch(setSelectedRounding(Number(value)));
              }
            }}
            className="rounding-select"
          >
            {availableRoundingOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </div>
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
                    <span className="total">{formatTotal(total)}</span>
                  </div>
                );
              })
            ) : (
              <div className="no-data">No asks available</div>
            )}
          </div>
        </div>

        {/* Spread Section */}
        {aggregatedOrderBook && displayBids.length > 0 && displayAsks.length > 0 && (
          <div className="spread-section">
            <div className="spread-info">
              <span className="spread-label">Spread:</span>
              <span className="spread-value">
                {formatPrice(displayAsks[displayAsks.length - 1].price - displayBids[0].price)}
              </span>
              <span className="spread-percentage">
                ({(((displayAsks[displayAsks.length - 1].price - displayBids[0].price) / displayBids[0].price) * 100).toFixed(4)}%)
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
                    <span className="total">{formatTotal(total)}</span>
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
      {aggregatedOrderBook && (
        <div className="order-book-footer">
          <span className="timestamp">
            Last updated: {new Date(aggregatedOrderBook.timestamp).toLocaleTimeString()}
          </span>
        </div>
      )}

    </div>
  );
};

export default OrderBookDisplay;