
function createManualTradeForm() {
  const formContainer = document.createElement('div');
  formContainer.className = 'manual-trade-form orderfox-manual-trade-form';

  formContainer.innerHTML = `
    <h3 class="form-title">Manual Trade</h3>
    <form class="trade-form">
      <div class="form-group">
        <label for="symbol">Symbol</label>
        <input type="text" id="symbol" name="symbol" class="form-input" placeholder="e.g., BTC/USDT">
      </div>
      <div class="form-group">
        <label for="side">Side</label>
        <select id="side" name="side" class="form-select">
          <option value="buy">Buy (Long)</option>
          <option value="sell">Sell (Short)</option>
        </select>
      </div>
      <div class="form-group">
        <label for="amount">Amount</label>
        <input type="number" id="amount" name="amount" class="form-input" placeholder="0.00" step="0.00001" min="0">
      </div>
      <div class="form-group">
        <label for="type">Type</label>
        <select id="type" name="type" class="form-select">
          <option value="market">Market</option>
          <option value="limit">Limit</option>
        </select>
      </div>
      <div class="form-group price-group" style="display: none;">
        <label for="price">Price</label>
        <input type="number" id="price" name="price" class="form-input" placeholder="0.00" step="0.01" min="0">
      </div>
      <div class="error-message" style="display: none;"></div>
      <button type="submit" class="submit-button">Submit Trade</button>
    </form>
  `;

  const typeSelect = formContainer.querySelector('#type');
  const priceGroup = formContainer.querySelector('.price-group');

  typeSelect.addEventListener('change', (e) => {
    if (e.target.value === 'limit') {
      priceGroup.style.display = 'block';
    } else {
      priceGroup.style.display = 'none';
    }
  });

  return formContainer;
}

function updateManualTradeForm(formContainer, data) {
  const { selectedSymbol, tradingMode, isSubmittingTrade, tradeError } = data;

  const symbolInput = formContainer.querySelector('#symbol');
  if (symbolInput) {
    symbolInput.value = selectedSymbol || '';
  }

  const submitButton = formContainer.querySelector('.submit-button');
  if (submitButton) {
    submitButton.textContent = `Submit ${tradingMode === 'paper' ? 'Paper' : 'Live'} Trade`;
    submitButton.disabled = isSubmittingTrade;
  }

  const errorMessage = formContainer.querySelector('.error-message');
  if (errorMessage) {
    errorMessage.textContent = tradeError || '';
    errorMessage.style.display = tradeError ? 'block' : 'none';
  }
}

export { createManualTradeForm, updateManualTradeForm };
