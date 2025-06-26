
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
      <div class="current-price-section">
        <div class="current-price-info">
          <span class="price-label">Connecting to price feed...</span>
        </div>
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
    orderBook, 
    ticker, 
    orderBookWsConnected, 
    tickerWsConnected, 
    selectedRounding,
    availableRoundingOptions
  } = data;

  // Update symbol label
  const symbolLabel = container.querySelector('.symbol-label');
  if (symbolLabel) {
    symbolLabel.textContent = selectedSymbol || '';
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

  // Update asks and bids
  const asksList = container.querySelector('.asks-list');
  const bidsList = container.querySelector('.bids-list');

  if (asksList && bidsList && orderBook) {
    asksList.innerHTML = '';
    bidsList.innerHTML = '';

    orderBook.asks.forEach(ask => {
      const row = document.createElement('div');
      row.className = 'order-level ask-level';
      row.innerHTML = `
        <span class="price ask-price">${ask.price.toFixed(2)}</span>
        <span class="amount">${ask.amount}</span>
        <span class="total">${(ask.price * ask.amount).toFixed(2)}</span>
      `;
      asksList.appendChild(row);
    });

    orderBook.bids.forEach(bid => {
      const row = document.createElement('div');
      row.className = 'order-level bid-level';
      row.innerHTML = `
        <span class="price bid-price">${bid.price.toFixed(2)}</span>
        <span class="amount">${bid.amount}</span>
        <span class="total">${(bid.price * bid.amount).toFixed(2)}</span>
      `;
      bidsList.appendChild(row);
    });
  }

  // Update timestamp
  const timestampEl = container.querySelector('.timestamp');
  if (timestampEl && orderBook) {
    timestampEl.textContent = `Last updated: ${new Date(orderBook.timestamp).toLocaleTimeString()}`;
  }
}

export { createOrderBookDisplay, updateOrderBookDisplay };
