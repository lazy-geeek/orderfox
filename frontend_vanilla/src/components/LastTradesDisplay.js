/**
 * Last Trades Display Component
 * 
 * Displays the most recent trades for a selected cryptocurrency symbol
 * with real-time updates, proper formatting, and color-coded buy/sell trades.
 */

/**
 * Create the Last Trades display component
 * @returns {HTMLElement} The created component container
 */
function createLastTradesDisplay() {
  const container = document.createElement('div');
  container.className = 'orderfox-display-base orderfox-last-trades-display';

  container.innerHTML = `
    <div class="display-header">
      <h3>Trades</h3>
      <div class="header-controls">
        <span class="symbol-label"></span>
        <div class="connection-status">
          <span class="status-indicator disconnected">○</span>
          <span class="status-text">Disconnected</span>
        </div>
      </div>
    </div>
    <div class="display-content">
      <div class="trades-section">
        <div class="section-header trades-header">
          <span class="price-header" id="trades-price-header">Price</span>
          <span class="amount-header" id="trades-amount-header">Amount</span>
          <span class="time-header">Time</span>
        </div>
        <div class="trades-container">
          <div class="trades-list" id="trades-list">
            <!-- Trades will be inserted here -->
          </div>
        </div>
      </div>
    </div>
    <div class="display-footer">
      <span class="timestamp"></span>
    </div>
  `;

  return container;
}

/**
 * Update the Last Trades display with new data
 * @param {HTMLElement} container - The trades display container
 * @param {Object} data - State data containing trades and connection info
 */
function updateLastTradesDisplay(container, data) {
  const {
    selectedSymbol,
    currentTrades: trades,
    tradesWsConnected,
    tradesLoading
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
    if (tradesWsConnected) {
      statusIndicator.className = 'status-indicator connected';
      statusIndicator.textContent = '●';
      statusText.textContent = 'Live';
    } else {
      statusIndicator.className = 'status-indicator disconnected';
      statusIndicator.textContent = '○';
      statusText.textContent = 'Disconnected';
    }
  }

  // Update trades list
  const tradesList = container.querySelector('#trades-list');
  if (tradesList) {
    // Show loading state if transitioning
    if (tradesLoading) {
      tradesList.innerHTML = '<div class="loading-state">Loading trades...</div>';
      return;
    }

    if (trades && trades.length > 0) {
      tradesList.innerHTML = '';

      // Display trades exactly as received from backend
      trades.forEach((trade) => {
        const row = document.createElement('div');
        row.className = 'trade-level';
        
        // Use existing bid/ask price classes for color coding
        const sideClass = trade.side === 'buy' ? 'bid-price' : 'ask-price';
        
        row.innerHTML = `
          <span class="price ${sideClass}">${trade.price_formatted}</span>
          <span class="amount ${sideClass}">${trade.amount_formatted}</span>
          <span class="time">${trade.time_formatted}</span>
        `;
        tradesList.appendChild(row);
      });
    } else {
      // Show empty state if no data
      tradesList.innerHTML = '<div class="empty-state">No trades data</div>';
    }
  }

  // Update timestamp
  const timestampEl = container.querySelector('.timestamp');
  if (timestampEl && trades && trades.length > 0) {
    // Use the timestamp of the most recent trade
    const latestTrade = trades[0];
    if (latestTrade && latestTrade.timestamp) {
      timestampEl.textContent = `Last updated: ${new Date(latestTrade.timestamp).toLocaleTimeString()}`;
    }
  }
}

/**
 * Update the trades table column headers with currency labels
 * @param {Object} symbolData - Symbol data containing base and quote assets
 */
function updateTradesHeaders(symbolData) {
  // Update column headers with currency labels
  const priceHeader = document.getElementById('trades-price-header');
  const amountHeader = document.getElementById('trades-amount-header');
  
  if (priceHeader && symbolData?.quoteAsset) {
    priceHeader.textContent = `Price (${symbolData.quoteAsset})`;
  }
  
  if (amountHeader && symbolData?.baseAsset) {
    amountHeader.textContent = `Amount (${symbolData.baseAsset})`;
  }
}

/**
 * Update the trades display with new trades data
 * @param {Array} trades - Array of trade objects
 */
function updateLastTradesData(trades) {
  const tradesList = document.getElementById('trades-list');
  if (!tradesList) return;

  // Clear existing trades
  tradesList.innerHTML = '';

  if (!trades || trades.length === 0) {
    tradesList.innerHTML = '<div class="empty-state">No trades data</div>';
    return;
  }

  // Add each trade
  trades.forEach(trade => {
    const row = document.createElement('div');
    row.className = 'trade-level';
    
    // Use existing bid/ask price classes for color coding
    const sideClass = trade.side === 'buy' ? 'bid-price' : 'ask-price';
    
    row.innerHTML = `
      <span class="price ${sideClass}">${trade.price_formatted}</span>
      <span class="amount ${sideClass}">${trade.amount_formatted}</span>
      <span class="time">${trade.time_formatted}</span>
    `;
    
    tradesList.appendChild(row);
  });
}

/**
 * Update connection status indicator
 * @param {boolean} connected - Connection status
 */
function updateTradesConnectionStatus(connected) {
  const statusIndicator = document.querySelector('.orderfox-last-trades-display .status-indicator');
  const statusText = document.querySelector('.orderfox-last-trades-display .status-text');
  
  if (statusIndicator && statusText) {
    if (connected) {
      statusIndicator.className = 'status-indicator connected';
      statusIndicator.textContent = '●';
      statusText.textContent = 'Live';
    } else {
      statusIndicator.className = 'status-indicator disconnected';
      statusIndicator.textContent = '○';
      statusText.textContent = 'Disconnected';
    }
  }
}

export { 
  createLastTradesDisplay, 
  updateLastTradesDisplay, 
  updateTradesHeaders,
  updateLastTradesData,
  updateTradesConnectionStatus
};