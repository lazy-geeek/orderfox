
import { featureFlags } from '../services/featureFlags.js';
import { logger } from '../utils/logger.js';

function createOrderBookDisplay() {
  const container = document.createElement('div');
  container.className = 'order-book-display orderfox-order-book-display';

  container.innerHTML = `
    <div class="order-book-header">
      <h3>Order Book</h3>
      <div class="header-controls">
        <span class="symbol-label"></span>
        <div class="connection-status">
          <span class="status-indicator disconnected">○</span>
          <span class="status-text">Disconnected</span>
        </div>
      </div>
    </div>
    <div class="depth-selector">
      <label for="depth-select">Display Depth:</label>
      <select id="depth-select" class="depth-select">
        <option value="5">5 levels</option>
        <option value="10">10 levels</option>
        <option value="20">20 levels</option>
        <option value="50">50 levels</option>
      </select>
      <div class="rounding-selector-container">
        <label for="rounding-select">Rounding:</label>
        <select id="rounding-select" class="rounding-select"></select>
      </div>
    </div>
    <div class="order-book-content">
      <div class="asks-section">
        <div class="section-header asks-header">
          <span class="price-header">Price</span>
          <span class="amount-header">Amount</span>
          <span class="total-header">Total</span>
        </div>
        <div class="asks-list"></div>
      </div>
      <div class="bids-section">
        <div class="section-header bids-header">
          <span class="price-header">Price</span>
          <span class="amount-header">Amount</span>
          <span class="total-header">Total</span>
        </div>
        <div class="bids-list"></div>
      </div>
    </div>
    <div class="order-book-footer">
      <span class="timestamp"></span>
    </div>
  `;

  return container;
}

function updateOrderBookDisplay(container, data) {
  // Use feature flag to determine display mode
  if (featureFlags.useBackendAggregation()) {
    return updateOrderBookDisplayNew(container, data);
  } else {
    return updateOrderBookDisplayLegacy(container, data);
  }
}

// New display mode for backend-aggregated data
function updateOrderBookDisplayNew(container, data) {
  const { 
    selectedSymbol,
    currentOrderBook: orderBook, 
    currentTicker: ticker, 
    orderBookWsConnected, 
    tickerWsConnected,
    displayDepth
  } = data;

  // Update common UI elements
  updateCommonUI(container, data);

  // Handle new backend-aggregated data format
  const asksList = container.querySelector('.asks-list');
  const bidsList = container.querySelector('.bids-list');

  if (asksList && bidsList) {
    if (data.orderBookLoading) {
      asksList.innerHTML = '<div class="loading-state">Loading...</div>';
      bidsList.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    if (orderBook && orderBook.aggregated) {
      // Backend has already done aggregation, just display the data
      displayAggregatedOrderBook(container, orderBook, data);
    } else if (orderBook && orderBook.asks && orderBook.bids) {
      // Fallback to legacy aggregation if backend data isn't aggregated
      logger.warn('Backend aggregation enabled but received raw data, falling back to frontend aggregation');
      displayLegacyOrderBook(container, orderBook, data);
    } else {
      asksList.innerHTML = '<div class="empty-state">No order book data</div>';
      bidsList.innerHTML = '<div class="empty-state">No order book data</div>';
    }
  }

  updateTimestamp(container, orderBook);
}

// Legacy display mode for frontend aggregation
function updateOrderBookDisplayLegacy(container, data) {
  const { 
    selectedSymbol,
    currentOrderBook: orderBook, 
    currentTicker: ticker, 
    orderBookWsConnected, 
    tickerWsConnected, 
    selectedRounding,
    availableRoundingOptions,
    displayDepth
  } = data;

  // Update common UI elements
  updateCommonUI(container, data);

  // Handle legacy frontend aggregation
  const asksList = container.querySelector('.asks-list');
  const bidsList = container.querySelector('.bids-list');

  if (asksList && bidsList) {
    if (data.orderBookLoading) {
      asksList.innerHTML = '<div class="loading-state">Loading...</div>';
      bidsList.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    if (orderBook && orderBook.asks && orderBook.bids) {
      displayLegacyOrderBook(container, orderBook, data);
    } else {
      asksList.innerHTML = '<div class="empty-state">No order book data</div>';
      bidsList.innerHTML = '<div class="empty-state">No order book data</div>';
    }
  }

  updateTimestamp(container, orderBook);
}

// Common UI update function used by both modes
function updateCommonUI(container, data) {
  const { 
    selectedSymbol,
    orderBookWsConnected,
    displayDepth,
    selectedRounding,
    availableRoundingOptions
  } = data;

  // Update symbol label
  const symbolLabel = container.querySelector('.symbol-label');
  if (symbolLabel) {
    symbolLabel.textContent = selectedSymbol || '';
  }

  // Update connection status
  const statusIndicator = container.querySelector('.status-indicator');
  const statusText = container.querySelector('.status-text');
  if (statusIndicator && statusText) {
    if (orderBookWsConnected) {
      statusIndicator.className = 'status-indicator connected';
      statusIndicator.textContent = '●';
      statusText.textContent = 'Live';
    } else {
      statusIndicator.className = 'status-indicator disconnected';
      statusIndicator.textContent = '○';
      statusText.textContent = 'Disconnected';
    }
  }

  // Update depth selector
  const depthSelect = container.querySelector('#depth-select');
  if (depthSelect && displayDepth) {
    depthSelect.value = displayDepth;
  }

  // Update rounding options (shown in both backend and legacy modes)
  const roundingSelect = container.querySelector('#rounding-select');
  if (roundingSelect) {
    // Always show rounding selector - it's needed for both modes
    const roundingContainer = container.querySelector('.rounding-selector-container');
    if (roundingContainer) {
      roundingContainer.style.display = 'block';
    }
    
    roundingSelect.innerHTML = '';
    availableRoundingOptions.forEach(option => {
      const optionEl = document.createElement('option');
      optionEl.value = option;
      optionEl.textContent = option;
      if (option === selectedRounding) {
        optionEl.selected = true;
      }
      roundingSelect.appendChild(optionEl);
    });
  }
}

// Display function for backend-aggregated data (new mode)
function displayAggregatedOrderBook(container, orderBook, data) {
  const asksList = container.querySelector('.asks-list');
  const bidsList = container.querySelector('.bids-list');
  
  asksList.innerHTML = '';
  bidsList.innerHTML = '';

  // Backend has already provided aggregated data
  const { asks, bids, rounding, source } = orderBook;
  const { displayDepth } = data;
  const effectiveDepth = displayDepth || 10;

  // Filter out zero amounts just in case they slip through
  const filteredAsks = asks.filter(ask => ask.amount > 0);
  const filteredBids = bids.filter(bid => bid.amount > 0);

  // Limit displayed levels to user's selected depth
  const displayAsks = filteredAsks.slice(0, effectiveDepth);
  const displayBids = filteredBids.slice(0, effectiveDepth);

  // Display asks (should be pre-sorted by backend, limit to displayDepth)
  displayAsks.forEach((ask, index) => {
    // Calculate cumulative total for frontend display
    const cumulativeTotal = displayAsks
      .slice(index)
      .reduce((sum, level) => sum + level.amount, 0);
    
    const row = document.createElement('div');
    row.className = 'order-level ask-level';
    
    row.innerHTML = `
      <span class="price ask-price">${formatPrice(ask.price, rounding)}</span>
      <span class="amount">${formatAmount(ask.amount)}</span>
      <span class="total">${formatTotal(cumulativeTotal)}</span>
    `;
    asksList.appendChild(row);
  });

  // Display bids (should be pre-sorted by backend, limit to displayDepth)
  displayBids.forEach((bid, index) => {
    // Calculate cumulative total for frontend display
    const cumulativeTotal = displayBids
      .slice(0, index + 1)
      .reduce((sum, level) => sum + level.amount, 0);
    
    const row = document.createElement('div');
    row.className = 'order-level bid-level';
    
    row.innerHTML = `
      <span class="price bid-price">${formatPrice(bid.price, rounding)}</span>
      <span class="amount">${formatAmount(bid.amount)}</span>
      <span class="total">${formatTotal(cumulativeTotal)}</span>
    `;
    bidsList.appendChild(row);
  });

  // Add source indicator
  const existingInfo = container.querySelector('.aggregation-info');
  if (existingInfo) {
    existingInfo.remove();
  }

  const infoDiv = document.createElement('div');
  infoDiv.className = 'aggregation-info';
  infoDiv.innerHTML = `
    <small style="color: #28a745; font-style: italic; padding: 4px 8px; display: block; text-align: center;">
      🚀 Backend aggregation enabled (${source || 'unknown'}, ${effectiveDepth} levels, rounding: ${rounding})
    </small>
  `;
  
  const asksSection = container.querySelector('.asks-section');
  if (asksSection) {
    asksSection.after(infoDiv);
  }
}

// Display function for legacy frontend aggregation
function displayLegacyOrderBook(container, orderBook, data) {
  const { selectedRounding, displayDepth, selectedSymbol } = data;
  
  const asksList = container.querySelector('.asks-list');
  const bidsList = container.querySelector('.bids-list');
  
  asksList.innerHTML = '';
  bidsList.innerHTML = '';

  // Get current market price (use highest bid or lowest ask)
  const currentPrice = orderBook.bids?.[0]?.price || orderBook.asks?.[0]?.price;
  
  if (!currentPrice) {
    return; // No price data available
  }

  const effectiveDepth = displayDepth || 10;
  const effectiveRounding = selectedRounding || 0.01;

  // Legacy frontend aggregation helpers
  const roundDown = (value, multiple) => {
    if (multiple <= 0) return value;
    const scale = 1 / multiple;
    return Math.floor(value * scale) / scale;
  };

  const roundUp = (value, multiple) => {
    if (multiple <= 0) return value;
    const scale = 1 / multiple;
    return Math.ceil(value * scale) / scale;
  };

  // Helper function to get exactly the needed number of levels with volume
    const getExactLevels = (rawData, isAsk) => {
      const buckets = new Map();
      
      // Aggregate all raw data into price buckets
      rawData.forEach((item) => {
        const roundedPrice = isAsk 
          ? roundUp(item.price, effectiveRounding)
          : roundDown(item.price, effectiveRounding);
        const existingAmount = buckets.get(roundedPrice) || 0;
        buckets.set(roundedPrice, existingAmount + item.amount);
      });
      
      // Convert to array and sort
      const sortedLevels = Array.from(buckets.entries())
        .map(([price, amount]) => ({ price, amount }))
        .filter(level => level.amount > 0)
        .sort((a, b) => isAsk ? a.price - b.price : b.price - a.price);
        
      // Take exactly effectiveDepth levels
      return sortedLevels.slice(0, effectiveDepth);
    };

    // Enhanced market depth validation and user feedback
    const minRequiredRawData = effectiveDepth * 10; // Reasonable multiplier for aggregation
    const hasInsufficientData = orderBook.asks.length < minRequiredRawData || orderBook.bids.length < minRequiredRawData;
    
    if (hasInsufficientData) {
      logger.debug(`Limited market depth for ${selectedSymbol} at $${effectiveRounding} rounding.`);
      logger.debug(`Raw data: ${orderBook.asks.length} asks, ${orderBook.bids.length} bids. Recommended: ${minRequiredRawData}+`);
    }

    // Get exactly the needed number of levels for asks and bids
    const aggregatedAsks = getExactLevels(orderBook.asks, true);
    const aggregatedBids = getExactLevels(orderBook.bids, false);
    
    // Check if we have data to display
    if (aggregatedAsks.length > 0 && aggregatedBids.length > 0) {
      // Smart market depth feedback and adaptive UI
    const actualLevels = Math.min(aggregatedAsks.length, aggregatedBids.length);
    const isMarketDepthLimited = actualLevels < effectiveDepth;
    
    if (isMarketDepthLimited) {
      logger.debug(`📊 Market depth limited: ${actualLevels}/${effectiveDepth} levels for ${selectedSymbol} at $${effectiveRounding} rounding`);
      logger.debug(`💡 This is normal for high rounding values - actual market orders may only exist within a narrow price range`);
      
      // Add market depth indicator to UI
      const depthIndicator = container.querySelector('.market-depth-indicator') || (() => {
        const indicator = document.createElement('div');
        indicator.className = 'market-depth-indicator';
        const depthSelector = container.querySelector('.depth-selector');
        if (depthSelector) {
          depthSelector.appendChild(indicator);
        }
        return indicator;
      })();
      
      depthIndicator.innerHTML = `
        <span class="depth-warning">⚠️ Limited market depth: ${actualLevels}/${effectiveDepth} levels</span>
        <span class="depth-hint">Try smaller rounding for more levels</span>
      `;
      depthIndicator.style.display = 'block';
    } else {
      // Remove depth indicator if we have sufficient levels
      const depthIndicator = container.querySelector('.market-depth-indicator');
      if (depthIndicator) {
        depthIndicator.style.display = 'none';
      }
    }

    // Prepare for display
    const displayAsks = aggregatedAsks.reverse(); // Reverse so highest price is at top
    const displayBids = aggregatedBids; // Already sorted highest to lowest

    // Display asks (reverse order for display, highest price at top)
    displayAsks.forEach((ask, index) => {
      // Calculate cumulative total from current index to end
      const cumulativeTotal = displayAsks
        .slice(index)
        .reduce((sum, level) => sum + level.amount, 0);
      
      const row = document.createElement('div');
      row.className = 'order-level ask-level';
      
      row.innerHTML = `
        <span class="price ask-price">${formatPrice(ask.price, effectiveRounding)}</span>
        <span class="amount">${formatAmount(ask.amount)}</span>
        <span class="total">${formatTotal(cumulativeTotal)}</span>
      `;
      asksList.appendChild(row);
    });

    // Display bids (highest price first)
    displayBids.forEach((bid, index) => {
      // Calculate cumulative total from top down
      const cumulativeTotal = displayBids
        .slice(0, index + 1)
        .reduce((sum, level) => sum + level.amount, 0);
      
      const row = document.createElement('div');
      row.className = 'order-level bid-level';
      
      row.innerHTML = `
        <span class="price bid-price">${formatPrice(bid.price, effectiveRounding)}</span>
        <span class="amount">${formatAmount(bid.amount)}</span>
        <span class="total">${formatTotal(cumulativeTotal)}</span>
      `;
      bidsList.appendChild(row);
    });
    
    // Remove any existing info message
    const existingInfo = container.querySelector('.market-depth-info');
    if (existingInfo) {
      existingInfo.remove();
    }
    
    // Show info when using Binance partial depth streams
    if (orderBook.source === 'binance_partial_depth') {
      const infoDiv = document.createElement('div');
      infoDiv.className = 'market-depth-info';
      infoDiv.innerHTML = `
        <small style="color: #28a745; font-style: italic; padding: 4px 8px; display: block; text-align: center;">
          📊 Using Binance partial depth stream (${orderBook.depth_level} levels) for optimal aggregation
        </small>
      `;
      
      // Insert info after the asks section
      const asksSection = container.querySelector('.asks-section');
      if (asksSection) {
        asksSection.after(infoDiv);
      }
    }
    
    // Show warning only if we have very few levels (which should now be rare)
    else if (aggregatedAsks.length < Math.min(5, effectiveDepth) || aggregatedBids.length < Math.min(5, effectiveDepth)) {
      const warningDiv = document.createElement('div');
      warningDiv.className = 'market-depth-info';
      warningDiv.innerHTML = `
        <small style="color: #f39c12; font-style: italic; padding: 4px 8px; display: block; text-align: center;">
          ⚠️ Limited levels: ${Math.min(aggregatedAsks.length, aggregatedBids.length)} levels at $${effectiveRounding} rounding
        </small>
      `;
      
      // Insert warning after the asks section
      const asksSection = container.querySelector('.asks-section');
      if (asksSection) {
        asksSection.after(warningDiv);
      }
    }
  } else {
    // Show empty state if no data
    asksList.innerHTML = '<div class="empty-state">No order book data</div>';
    bidsList.innerHTML = '<div class="empty-state">No order book data</div>';
  }


}

// Common formatting functions used by both display modes
function formatPrice(price, rounding = null) {
  if (rounding && rounding > 0) {
    // Calculate decimal places from rounding value
    const decimalPlaces = Math.max(0, -Math.floor(Math.log10(rounding)));
    return price.toFixed(decimalPlaces);
  }
  return price.toFixed(2);
}

function formatAmount(amount) {
  if (amount >= 1000000) {
    return (amount / 1000000).toFixed(2) + 'M';
  } else if (amount >= 1000) {
    return (amount / 1000).toFixed(2) + 'K';
  }
  return amount.toFixed(2);
}

function formatTotal(total) {
  if (total >= 1000000) {
    return (total / 1000000).toFixed(2) + 'M';
  } else if (total >= 1000) {
    return (total / 1000).toFixed(2) + 'K';
  }
  return total.toFixed(2);
}

// Common timestamp update function
function updateTimestamp(container, orderBook) {
  const timestampEl = container.querySelector('.timestamp');
  if (timestampEl && orderBook && orderBook.timestamp) {
    timestampEl.textContent = `Last updated: ${new Date(orderBook.timestamp).toLocaleTimeString()}`;
  }
}

export { createOrderBookDisplay, updateOrderBookDisplay };
