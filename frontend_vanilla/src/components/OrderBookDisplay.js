
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
  const { 
    selectedSymbol,
    currentOrderBook: orderBook, 
    orderBookWsConnected, 
    selectedRounding,
    availableRoundingOptions,
    displayDepth
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

  // Note: All formatting is now handled by the backend
  // Frontend only displays pre-formatted strings from backend

  // Update asks and bids with cumulative totals
  const asksList = container.querySelector('.asks-list');
  const bidsList = container.querySelector('.bids-list');

  if (asksList && bidsList) {
    // Show loading state if transitioning
    if (data.orderBookLoading) {
      asksList.innerHTML = '<div class="loading-state">Loading...</div>';
      bidsList.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    if (orderBook && orderBook.asks && orderBook.bids) {
      asksList.innerHTML = '';
      bidsList.innerHTML = '';

      // Display asks exactly as received from backend
      orderBook.asks.forEach((ask) => {
        const row = document.createElement('div');
        row.className = 'order-level ask-level';
        
        row.innerHTML = `
          <span class="price ask-price">${ask.price_formatted}</span>
          <span class="amount">${ask.amount_formatted}</span>
          <span class="total">${ask.cumulative_formatted}</span>
        `;
        asksList.appendChild(row);
      });

      // Display bids exactly as received from backend
      orderBook.bids.forEach((bid) => {
        const row = document.createElement('div');
        row.className = 'order-level bid-level';
        
        row.innerHTML = `
          <span class="price bid-price">${bid.price_formatted}</span>
          <span class="amount">${bid.amount_formatted}</span>
          <span class="total">${bid.cumulative_formatted}</span>
        `;
        bidsList.appendChild(row);
      });
      
      // Handle market depth information from backend
      const existingInfo = container.querySelector('.market-depth-info');
      if (existingInfo) {
        existingInfo.remove();
      }
      
      if (orderBook.market_depth_info && orderBook.market_depth_info.insufficient_levels) {
        const infoDiv = document.createElement('div');
        infoDiv.className = 'market-depth-info';
        infoDiv.innerHTML = `
          <small style="color: #f39c12; font-style: italic; padding: 4px 8px; display: block; text-align: center;">
            ⚠️ ${orderBook.market_depth_info.message || 'Limited market depth at current rounding'}
          </small>
        `;
        
        const asksSection = container.querySelector('.asks-section');
        if (asksSection) {
          asksSection.after(infoDiv);
        }
      }
    
    } else {
      // Show empty state if no data
      asksList.innerHTML = '<div class="empty-state">No order book data</div>';
      bidsList.innerHTML = '<div class="empty-state">No order book data</div>';
    }
  }


  // Update timestamp
  const timestampEl = container.querySelector('.timestamp');
  if (timestampEl && orderBook && orderBook.timestamp) {
    timestampEl.textContent = `Last updated: ${new Date(orderBook.timestamp).toLocaleTimeString()}`;
  }
}

export { createOrderBookDisplay, updateOrderBookDisplay };
