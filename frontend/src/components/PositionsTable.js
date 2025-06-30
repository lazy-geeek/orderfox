
function createPositionsTable() {
  const container = document.createElement('div');
  container.className = 'positions-table-container orderfox-positions-table-container';

  container.innerHTML = `
    <h3 class="positions-title">Open Positions</h3>
    <div class="positions-table-content">
      <table class="positions-table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Side</th>
            <th>Size</th>
            <th>Entry Price</th>
            <th>Current Price</th>
            <th>PnL (USDT)</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
        </tbody>
      </table>
      <div class="no-positions" style="display: none;">
        No open positions.
      </div>
    </div>
  `;

  return container;
}

function updatePositionsTable(container, data) {
  const { openPositions, isSubmittingTrade } = data;

  const tableBody = container.querySelector('tbody');
  const noPositionsMessage = container.querySelector('.no-positions');

  if (tableBody && noPositionsMessage) {
    tableBody.innerHTML = '';

    if (openPositions.length === 0) {
      noPositionsMessage.style.display = 'block';
      tableBody.style.display = 'none';
    } else {
      noPositionsMessage.style.display = 'none';
      tableBody.style.display = '';

      openPositions.forEach(position => {
        const row = document.createElement('tr');
        row.innerHTML = `
          <td class="symbol">${position.symbol}</td>
          <td class="side ${position.side.toLowerCase()}">${position.side.charAt(0).toUpperCase() + position.side.slice(1)}</td>
          <td class="size">${position.size}</td>
          <td class="entry-price">$${position.entryPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8 })}</td>
          <td class="current-price">$${position.markPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8 })}</td>
          <td class="pnl ${position.unrealizedPnl >= 0 ? 'positive' : 'negative'}">${position.unrealizedPnl >= 0 ? '+' : ''}${position.unrealizedPnl.toFixed(2)}</td>
          <td class="actions">
            <button class="close-button" ${isSubmittingTrade ? 'disabled' : ''}>${isSubmittingTrade ? 'Closing...' : 'Close'}</button>
          </td>
        `;
        tableBody.appendChild(row);
      });
    }
  }
}

export { createPositionsTable, updatePositionsTable };
