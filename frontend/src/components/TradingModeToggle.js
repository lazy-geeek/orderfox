
function createTradingModeToggle() {
  const container = document.createElement('div');
  container.className = 'trading-mode-toggle orderfox-trading-mode-toggle';

  container.innerHTML = `
    <span class="mode-label">Mode:</span>
    <button class="mode-button">
      <span class="mode-text"></span>
    </button>
  `;

  return container;
}

function updateTradingModeToggle(container, data) {
  const { tradingMode, isSubmittingTrade } = data;

  const button = container.querySelector('.mode-button');
  const modeText = container.querySelector('.mode-text');

  if (button && modeText) {
    button.className = `mode-button ${tradingMode}-mode`;
    button.disabled = isSubmittingTrade;
    button.title = `Switch to ${tradingMode === 'paper' ? 'Live' : 'Paper'} mode`;

    if (isSubmittingTrade) {
      modeText.innerHTML = '<span class="loading"><span class="spinner"></span>Switching...</span>';
    } else {
      modeText.textContent = tradingMode === 'paper' ? 'Paper' : 'Live';
    }
  }
}

export { createTradingModeToggle, updateTradingModeToggle };
