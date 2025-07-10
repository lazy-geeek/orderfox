
export function createMainLayout() {
  const layout = document.createElement('div');
  layout.style.display = 'flex';
  layout.style.flexDirection = 'column';
  layout.style.height = '100vh';
  layout.style.fontFamily = 'Inter, -apple-system, BlinkMacSystemFont, sans-serif';
  layout.style.backgroundColor = 'var(--bg-primary)';
  layout.style.color = 'var(--text-primary)';

  // Header
  const header = document.createElement('header');
  header.style.padding = '1rem 1.5rem';
  header.style.backgroundColor = 'var(--bg-secondary)';
  header.style.color = 'var(--text-primary)';
  header.style.borderBottom = '1px solid var(--border-primary)';
  header.style.boxShadow = 'var(--shadow-light)';

  const h1 = document.createElement('h1');
  h1.style.margin = '0 0 1rem 0';
  h1.style.fontSize = '1.5rem';
  h1.style.fontWeight = '600';
  h1.style.color = 'var(--text-primary)';
  h1.textContent = 'OrderFox';

  const headerControls = document.createElement('div');
  headerControls.className = 'header-controls';
  headerControls.style.display = 'flex';
  headerControls.style.justifyContent = 'space-between';
  headerControls.style.alignItems = 'center';
  headerControls.style.gap = '1.5rem';

  const symbolSelectorPlaceholder = document.createElement('div');
  symbolSelectorPlaceholder.id = 'symbol-selector-placeholder';
  symbolSelectorPlaceholder.textContent = 'SymbolSelector';

  const tradingModeTogglePlaceholder = document.createElement('div');
  tradingModeTogglePlaceholder.id = 'trading-mode-toggle-placeholder';
  tradingModeTogglePlaceholder.textContent = 'TradingModeToggle';

  const themeSwitcherPlaceholder = document.createElement('div');
  themeSwitcherPlaceholder.id = 'theme-switcher-placeholder';
  themeSwitcherPlaceholder.textContent = 'ThemeSwitcher';

  headerControls.appendChild(symbolSelectorPlaceholder);
  headerControls.appendChild(tradingModeTogglePlaceholder);
  headerControls.appendChild(themeSwitcherPlaceholder);

  header.appendChild(h1);
  header.appendChild(headerControls);

  // Main Content
  const mainContent = document.createElement('div');
  mainContent.style.display = 'flex';
  mainContent.style.flexDirection = 'column';
  mainContent.style.flex = '1';
  mainContent.style.gap = '1rem';
  mainContent.style.padding = '1rem';
  mainContent.style.backgroundColor = 'var(--bg-primary)';
  mainContent.style.overflow = 'auto';

  // Chart Section - Full Width
  const chartSection = document.createElement('main');
  chartSection.className = 'chart-section';
  chartSection.style.width = '100%';
  chartSection.style.display = 'flex';
  chartSection.style.flexDirection = 'column';
  chartSection.style.backgroundColor = 'var(--bg-primary)';

  const candlestickChartPlaceholder = document.createElement('div');
  candlestickChartPlaceholder.id = 'candlestick-chart-placeholder';
  candlestickChartPlaceholder.textContent = 'CandlestickChart';
  chartSection.appendChild(candlestickChartPlaceholder);

  // Bottom Section - OrderBook and Trades Side by Side
  const bottomSection = document.createElement('div');
  bottomSection.className = 'bottom-section';
  bottomSection.style.display = 'grid';
  bottomSection.style.gridTemplateColumns = '1fr 1fr';
  bottomSection.style.gap = '1rem';
  bottomSection.style.width = '100%';

  const orderBookPlaceholder = document.createElement('div');
  orderBookPlaceholder.id = 'order-book-placeholder';
  orderBookPlaceholder.textContent = 'OrderBookDisplay';

  const lastTradesPlaceholder = document.createElement('div');
  lastTradesPlaceholder.id = 'last-trades-container';
  lastTradesPlaceholder.textContent = 'LastTradesDisplay';

  bottomSection.appendChild(orderBookPlaceholder);
  bottomSection.appendChild(lastTradesPlaceholder);

  mainContent.appendChild(chartSection);
  mainContent.appendChild(bottomSection);

  layout.appendChild(header);
  layout.appendChild(mainContent);

  return layout;
}
