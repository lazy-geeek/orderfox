import { createChart } from 'lightweight-charts';

const TIMEFRAMES = [
  { value: '1m', label: '1m' },
  { value: '5m', label: '5m' },
  { value: '15m', label: '15m' },
  { value: '1h', label: '1h' },
  { value: '4h', label: '4h' },
  { value: '1d', label: '1d' },
];

let chartInstance = null;
let candlestickSeries = null;
let lastChartData = null;
let lastSymbol = null;
let lastTimeframe = null;
let resizeObserver = null;
let currentTheme = 'dark';
let userHasZoomed = false;

function createLightweightChart(container) {
  const chartContainer = document.createElement('div');
  chartContainer.className = 'chart-container';
  chartContainer.style.height = '500px';
  chartContainer.style.width = '100%';
  container.appendChild(chartContainer);

  // Get current theme
  currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
  
  // Initialize chart with theme options
  const chartOptions = getChartOptions(currentTheme);
  chartOptions.width = chartContainer.clientWidth;
  chartOptions.height = chartContainer.clientHeight;
  
  chartInstance = createChart(chartContainer, chartOptions);
  
  // Add candlestick series
  candlestickSeries = chartInstance.addCandlestickSeries(getCandlestickOptions());

  // Setup responsive sizing with ResizeObserver
  setupResizeObserver(chartContainer);

  // Track user zoom/pan interactions
  chartInstance.timeScale().subscribeVisibleTimeRangeChange(() => {
    userHasZoomed = true;
  });

  // Listen for theme changes
  window.addEventListener('themechange', (e) => {
    const newTheme = e.detail.theme;
    switchTheme(newTheme);
  });

  return chartContainer;
}

function getChartOptions(theme) {
  const isDark = theme === 'dark';
  
  return {
    layout: {
      background: { color: isDark ? '#1E2329' : '#FAFAFA' },
      textColor: isDark ? '#EAECEF' : '#1A1A1A',
    },
    grid: {
      vertLines: { color: isDark ? '#2B3139' : '#EAECEF' },
      horzLines: { color: isDark ? '#2B3139' : '#EAECEF' },
    },
    rightPriceScale: {
      borderColor: isDark ? '#2B3139' : '#EAECEF',
      scaleMargins: {
        top: 0.1,
        bottom: 0.1,
      },
    },
    timeScale: {
      borderColor: isDark ? '#2B3139' : '#EAECEF',
      timeVisible: true,
      secondsVisible: false,
      rightOffset: 5, // Add space between current candle and right edge
    },
    crosshair: {
      mode: 0, // Normal crosshair mode
    },
  };
}

function getCandlestickOptions() {
  return {
    upColor: '#0ECB81',
    downColor: '#F6465D',
    borderVisible: false,
    wickUpColor: '#0ECB81',
    wickDownColor: '#F6465D',
  };
}

function setupResizeObserver(container) {
  if (resizeObserver) {
    resizeObserver.disconnect();
  }
  
  resizeObserver = new ResizeObserver(entries => {
    if (entries.length === 0 || !chartInstance) return;
    const { width, height } = entries[0].contentRect;
    chartInstance.resize(width, height);
  });
  
  resizeObserver.observe(container);
}

function switchTheme(newTheme) {
  currentTheme = newTheme;
  
  if (!chartInstance) return;
  
  // CRITICAL: More efficient than ECharts - use applyOptions instead of disposal
  chartInstance.applyOptions(getChartOptions(newTheme));
  
  // Candlestick colors remain the same for both themes
  // Re-render with last known data if available
  if (lastChartData && lastSymbol && lastTimeframe) {
    updateLightweightChart(lastChartData, lastSymbol, lastTimeframe);
  }
}

function createTimeframeSelector(handleTimeframeChange) {
  const timeframeContainer = document.createElement('div');
  timeframeContainer.className = 'timeframe-selector';

  const label = document.createElement('span');
  label.textContent = 'Timeframe:';
  timeframeContainer.appendChild(label);

  TIMEFRAMES.forEach(tf => {
    const button = document.createElement('button');
    button.textContent = tf.label;
    button.dataset.timeframe = tf.value;
    button.addEventListener('click', () => {
      // Remove active class from all buttons
      timeframeContainer.querySelectorAll('button').forEach(btn => btn.classList.remove('active'));
      // Add active class to clicked button
      button.classList.add('active');
      handleTimeframeChange(tf.value);
    });
    timeframeContainer.appendChild(button);
  });

  // Set default active timeframe (1m)
  const defaultButton = timeframeContainer.querySelector('[data-timeframe="1m"]');
  if (defaultButton) {
    defaultButton.classList.add('active');
  }

  return timeframeContainer;
}

function updateLightweightChart(data, symbol, timeframe, isInitialLoad = false) {
  if (!chartInstance || !candlestickSeries) return;

  // Store the last data for theme changes
  lastChartData = data;
  lastSymbol = symbol;
  lastTimeframe = timeframe;

  const { currentCandles } = data;

  // CRITICAL: Convert data format from ECharts to Lightweight Charts
  // ECharts: [timestamp, open, close, low, high, volume]
  // Lightweight Charts: { time: timestamp_in_seconds, open, high, low, close }
  const formattedData = currentCandles.map(candle => ({
    time: Math.floor(candle.timestamp / 1000), // Convert milliseconds to seconds
    open: candle.open,
    high: candle.high,
    low: candle.low,
    close: candle.close,
  }));

  // Sort data by time to ensure proper ordering
  formattedData.sort((a, b) => a.time - b.time);

  // Set the data for the candlestick series
  candlestickSeries.setData(formattedData);

  // Update chart title - we'll add this as a visual indicator
  updateChartTitle(symbol, timeframe);

  // Only fit content on initial load or when user hasn't zoomed
  // This preserves user zoom/pan state during real-time updates
  if (isInitialLoad || !userHasZoomed) {
    chartInstance.timeScale().fitContent();
  }
}

function updateChartTitle(symbol, timeframe) {
  // Since Lightweight Charts doesn't have built-in title support like ECharts,
  // we can create a custom title element or rely on external UI
  // For now, we'll emit a custom event that the UI can listen to
  const titleEvent = new CustomEvent('chartTitleUpdate', {
    detail: {
      title: symbol ? `${symbol} - ${timeframe}` : 'Select a Symbol'
    }
  });
  window.dispatchEvent(titleEvent);
}

function updateLatestCandle(candleData) {
  if (!candlestickSeries) return;

  // CRITICAL: Use update() for real-time updates, not setData()
  // This preserves zoom state and is more efficient for single candle updates
  const formattedCandle = {
    time: Math.floor(candleData.timestamp / 1000), // Convert milliseconds to seconds
    open: candleData.open,
    high: candleData.high,
    low: candleData.low,
    close: candleData.close,
  };

  candlestickSeries.update(formattedCandle);
}

function resetZoomState() {
  // Reset zoom tracking when symbol or timeframe changes
  userHasZoomed = false;
}

function disposeLightweightChart() {
  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }
  if (chartInstance) {
    chartInstance.remove();
    chartInstance = null;
  }
  candlestickSeries = null;
  lastChartData = null;
  lastSymbol = null;
  lastTimeframe = null;
  userHasZoomed = false;
}

// Export functions for backward compatibility with existing code
export { 
  createLightweightChart as createCandlestickChart, 
  createTimeframeSelector, 
  updateLightweightChart as updateCandlestickChart,
  updateLatestCandle,
  resetZoomState,
  disposeLightweightChart
};