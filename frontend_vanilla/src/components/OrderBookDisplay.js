
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

// Display backend-aggregated orderbook data
function updateOrderBookDisplay(container, data) {
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
      // Display backend-aggregated data
      displayAggregatedOrderBook(container, orderBook, data);
    } else {
      asksList.innerHTML = '<div class="empty-state">No order book data</div>';
      bidsList.innerHTML = '<div class="empty-state">No order book data</div>';
    }
  }

  updateTimestamp(container, orderBook);
}

// Common UI update function
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

  // Update rounding options
  const roundingSelect = container.querySelector('#rounding-select');
  if (roundingSelect) {
    // Update rounding selector
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


// Common formatting functions
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
