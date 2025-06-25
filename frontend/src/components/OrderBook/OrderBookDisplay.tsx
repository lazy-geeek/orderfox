import React, { useEffect, useState, useMemo, useRef } from 'react';
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
    currentTicker,
    orderBookLoading,
    orderBookError,
    orderBookWsConnected,
    tickerWsConnected,
    selectedRounding,
    availableRoundingOptions,
  } = useAppSelector((state) => state.marketData);

  const [displayDepth, setDisplayDepth] = useState(10);
  const isInitialRenderForSymbol = useRef(true);

  // Get selected symbol data from symbolsList (selectedSymbol is the id from the dropdown)
  const selectedSymbolData = selectedSymbol
    ? symbolsList.find(symbol => symbol.id === selectedSymbol)
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

    // Get current market price (best bid) to determine static price levels
    const currentPrice = currentOrderBook.bids[0]?.price;
    if (!currentPrice) {
      return currentOrderBook;
    }

    // Create static price levels for bids (round down from current price)
    const staticBidLevels: number[] = [];
    for (let i = 0; i < displayDepth; i++) {
      const priceLevel = roundDown(currentPrice - (i * selectedRounding), selectedRounding);
      staticBidLevels.push(priceLevel);
    }

    // Create static price levels for asks (round up from current price)
    const staticAskLevels: number[] = [];
    for (let i = 0; i < displayDepth; i++) {
      const priceLevel = roundUp(currentPrice + (i * selectedRounding), selectedRounding);
      staticAskLevels.push(priceLevel);
    }

    // Aggregate bids into static levels
    const bidsMap = new Map<number, number>();
    staticBidLevels.forEach(level => bidsMap.set(level, 0));
    
    currentOrderBook.bids.forEach((bid) => {
      const roundedPrice = roundDown(bid.price, selectedRounding);
      if (bidsMap.has(roundedPrice)) {
        const existingAmount = bidsMap.get(roundedPrice) || 0;
        bidsMap.set(roundedPrice, existingAmount + bid.amount);
      }
    });

    // Convert bids map to array and sort by price descending
    let aggregatedBids = staticBidLevels
      .map(price => ({ price, amount: bidsMap.get(price) || 0 }))
      .sort((a, b) => b.price - a.price);

    // Aggregate asks into static levels
    const asksMap = new Map<number, number>();
    staticAskLevels.forEach(level => asksMap.set(level, 0));
    
    currentOrderBook.asks.forEach((ask) => {
      const roundedPrice = roundUp(ask.price, selectedRounding);
      if (asksMap.has(roundedPrice)) {
        const existingAmount = asksMap.get(roundedPrice) || 0;
        asksMap.set(roundedPrice, existingAmount + ask.amount);
      }
    });

    // Convert asks map to array and sort by price ascending
    let aggregatedAsks = staticAskLevels
      .map(price => ({ price, amount: asksMap.get(price) || 0 }))
      .sort((a, b) => a.price - b.price);

    return {
      symbol: currentOrderBook.symbol,
      bids: aggregatedBids,
      asks: aggregatedAsks,
      timestamp: currentOrderBook.timestamp,
    };
  }, [currentOrderBook, selectedRounding, displayDepth]);

  // Cleanup WebSocket when component unmounts or symbol changes
  useEffect(() => {
    // When symbol changes, reset the ref to allow the rounding effect to be skipped on initial load
    isInitialRenderForSymbol.current = true;
    return () => {
      // Cleanup function - disconnect WebSocket when component unmounts
      if (selectedSymbol) {
        console.log(`OrderBookDisplay cleanup: disconnecting WebSocket for ${selectedSymbol}`);
        dispatch(stopOrderBookWebSocket({ symbol: selectedSymbol }));
      }
    };
  }, [selectedSymbol, dispatch]);

  // Calculate and set available rounding options when symbol data becomes available
  useEffect(() => {
    if (!selectedSymbol || !selectedSymbolData) {
      // Clear options if no symbol is selected or symbol data is not available
      dispatch(setAvailableRoundingOptions({ options: [], defaultRounding: null }));
      return;
    }

    // Calculate baseRounding from pricePrecision
    const baseRounding = 1 / (10 ** (selectedSymbolData.pricePrecision || 2));

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
    if (options.length < 3) {
      // If we don't have current price data or need more options, add a few more
      let tempOption = options[options.length - 1];
      while (options.length < 4 && tempOption * 10 <= 1000) {
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
    currentOrderBook,
    dispatch,
    selectedRounding,
  ]);


  // Handle rounding/depth change effect - fetch deeper data when symbol, rounding, or display depth changes
  useEffect(() => {
    // Early return if required data is not available
    if (!selectedSymbol || selectedRounding === null || !selectedSymbolData) {
      return;
    }

    // Don't run this logic on the very first render for a symbol,
    // as the `changeSelectedSymbol` thunk handles the initial fetch and WS connection.
    // This effect should only run when rounding or depth are changed by the user.
    if (isInitialRenderForSymbol.current) {
      isInitialRenderForSymbol.current = false;
      return;
    }

    // Get symbolDetails (for pricePrecision) and displayDepth from state
    const symbolDetails = selectedSymbolData;
    
    // Calculate baseTickSize from pricePrecision
    const baseTickSize = 1 / (10 ** (symbolDetails.pricePrecision || 2));

    // Calculate dynamicLimit for fetchOrderBook (as per task specification)
    // Binance futures only accepts specific limits: 5, 10, 20, 50, 100, 500, 1000
    const MIN_RAW_LIMIT = 100;  // Changed from 200 to 100 (valid Binance limit)
    const MAX_RAW_LIMIT = 1000;
    const AGGRESSIVENESS_FACTOR = 50; // Increased to 50 for much better coverage with high rounding
    
    // Valid Binance futures orderbook limits
    const VALID_LIMITS = [5, 10, 20, 50, 100, 500, 1000];
    
    let calculatedLimit = MIN_RAW_LIMIT;
    if (selectedRounding > baseTickSize) {
      // Calculate how many raw levels we need to ensure we have enough data after aggregation
      const roundingMultiplier = selectedRounding / baseTickSize;
      calculatedLimit = Math.ceil(roundingMultiplier * displayDepth * AGGRESSIVENESS_FACTOR);
      
      // For very high rounding values, always use maximum limit
      if (roundingMultiplier > 100) {
        calculatedLimit = MAX_RAW_LIMIT;
      }
    }
    
    // Round to nearest valid limit, always prefer higher limit for better coverage
    const clampedLimit = Math.max(MIN_RAW_LIMIT, Math.min(calculatedLimit, MAX_RAW_LIMIT));
    const finalLimit = VALID_LIMITS.find(limit => limit >= clampedLimit) || MAX_RAW_LIMIT;

    // When rounding or depth changes, we always want to stop the stream, fetch a new snapshot,
    // and have the listener middleware restart the stream.
    dispatch(setShouldRestartWebSocketAfterFetch(true));
    dispatch(stopOrderBookWebSocket({ symbol: selectedSymbol }));

    // Dispatch fetchOrderBook with calculated limit
    // The startOrderBookWebSocket will be triggered after fetchOrderBook.fulfilled via listener middleware
    dispatch(fetchOrderBook({ symbol: selectedSymbol, limit: finalLimit }));
  }, [selectedSymbol, selectedRounding, selectedSymbolData, displayDepth, dispatch]);

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

  // Use aggregated data for display (already limited to displayDepth in aggregation)
  const displayBids = aggregatedOrderBook?.bids || [];
  // Asks are typically sorted ascending by price, but displayed descending (highest price at top, lowest at bottom)
  // To achieve "lowest value at the bottom" as per the task, we sort ascending and then reverse for display.
  const displayAsks = aggregatedOrderBook?.asks
    ? [...aggregatedOrderBook.asks].reverse()
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
                // For asks, since displayAsks is reversed (highest price first), 
                // cumulative should represent volume available at this price and higher
                // We need to sum from current index to the end (which represents lower to higher prices)
                const total = displayAsks
                  .slice(index)
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

        {/* Current Price Section */}
        <div className="current-price-section">
          <div className="current-price-info">
            {currentTicker ? (
              <>
                <span className="price-label">Current Price:</span>
                <span className={`current-price ${currentTicker.change >= 0 ? 'positive' : 'negative'}`}>
                  {formatPrice(currentTicker.last)}
                </span>
                <span className={`price-change ${currentTicker.change >= 0 ? 'positive' : 'negative'}`}>
                  {currentTicker.change >= 0 ? '+' : ''}{formatPrice(currentTicker.change)} ({currentTicker.percentage.toFixed(2)}%)
                </span>
              </>
            ) : (
              <span className="price-label">
                {tickerWsConnected ? 'Waiting for price data...' : 'Connecting to price feed...'}
              </span>
            )}
            <span className={`connection-indicator ${tickerWsConnected ? 'connected' : 'disconnected'}`}>
              {tickerWsConnected ? '●' : '○'}
            </span>
          </div>
        </div>

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
                // For bids, cumulative total should be from top down (highest price to current price)
                // Since bids are displayed highest to lowest, we sum from 0 to current index
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