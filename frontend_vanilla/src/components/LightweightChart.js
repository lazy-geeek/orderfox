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
      autoScale: true, // Ensure price scale auto-adjusts to data
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
    priceFormat: {
      type: 'price',
      precision: 2, // Default precision
      minMove: 0.01, // Default minimum price movement
    },
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

function updateLightweightChart(data, symbol, timeframe, isInitialLoad = false, symbolData = null) {
  if (!chartInstance || !candlestickSeries) return;

  // CRITICAL: Check if this is a symbol or timeframe change
  const isSymbolChange = lastSymbol !== symbol;
  const isTimeframeChange = lastTimeframe !== timeframe;
  const isContextChange = isSymbolChange || isTimeframeChange;

  // Context change handling

  // Store the last data for theme changes
  lastChartData = data;
  lastSymbol = symbol;
  lastTimeframe = timeframe;

  // CRITICAL: Reset zoom state on context changes to allow proper fitting
  if (isContextChange) {
    resetZoomState();
  }

  // Apply price format from backend when symbol data is provided
  if (symbolData && candlestickSeries && symbolData.priceFormat) {
    // Backend provides complete priceFormat object ready for TradingView
    candlestickSeries.applyOptions({
      priceFormat: symbolData.priceFormat
    });
  }

  const { currentCandles } = data;

  // Check if we have valid candle data
  if (!currentCandles || currentCandles.length === 0) {
    console.warn(`No candle data available for ${symbol} ${timeframe}`);
    // Clear the chart but don't break
    candlestickSeries.setData([]);
    return;
  }

  // Backend provides data ready for Lightweight Charts
  // Backend sends: { time: seconds, timestamp: milliseconds, open, high, low, close }
  const formattedData = currentCandles.map(candle => ({
    time: candle.time, // Backend provides time in seconds for TradingView
    open: candle.open,
    high: candle.high,
    low: candle.low,
    close: candle.close,
  }));

  // Backend sends pre-sorted data - no sorting needed

  // Chart data loading

  // CRITICAL: Use setData to completely replace chart data
  // This clears any previous data and prevents timestamp ordering conflicts
  candlestickSeries.setData(formattedData);

  // Update chart title - we'll add this as a visual indicator
  updateChartTitle(symbol, timeframe);

  // CRITICAL: Always fit content on context changes, respect user zoom for updates
  if (isInitialLoad || isContextChange || !userHasZoomed) {
    // Ensure the chart properly fits the new data
    chartInstance.timeScale().fitContent();
    
    // For symbol changes, also ensure price scale adjusts to new price range
    if (isSymbolChange && candlestickSeries) {
      // Force price scale to recalculate its range for the new symbol
      candlestickSeries.priceScale().applyOptions({
        autoScale: true,
      });
    }
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
  if (!candlestickSeries) {
    return;
  }

  // CRITICAL: Import state to validate current symbol
  if (typeof window !== 'undefined' && window.state) {
    // Validate that this candle is for the current symbol
    if (window.state.selectedSymbol && candleData.symbol && candleData.symbol !== window.state.selectedSymbol) {
      return;
    }
  }

  // Backend provides time field in seconds for TradingView
  const chartTime = candleData.time; // Backend sends time in seconds
  
  // Get current chart data to check ordering
  let lastChartTime = null;
  try {
    // Try to get the current data from the series to check timestamp ordering
    const currentData = candlestickSeries.data();
    if (currentData && currentData.length > 0) {
      lastChartTime = currentData[currentData.length - 1].time;
      
      // Check for timestamp ordering issues
      if (chartTime <= lastChartTime) {
        const timeDiff = lastChartTime - chartTime;
        
        // If it's a very old update (more than 5 minutes), reject it
        if (timeDiff > 300) { // 5 minutes
          return;
        }
        // For same timestamp (timeDiff = 0), don't log - this is normal for real-time updates
      }
    }
  } catch (e) {
    // Chart data comparison failed - continue with update
  }

  // CRITICAL: Use update() for real-time updates, not setData()
  // This preserves zoom state and is more efficient for single candle updates
  const formattedCandle = {
    time: chartTime,
    open: candleData.open,
    high: candleData.high,
    low: candleData.low,
    close: candleData.close,
  };

  try {
    candlestickSeries.update(formattedCandle);
  } catch (error) {
    // CRITICAL: Catch and log TradingView chart errors without crashing
    console.error('Chart update error (likely "Cannot update oldest data"):', error.message);
    console.error('Raw candle data causing error:', candleData);
    console.error('Formatted candle data causing error:', formattedCandle);
    
    if (lastChartTime !== null) {
      console.error(`Chart: Timestamp comparison - Last: ${lastChartTime}, Attempted: ${chartTime}, Diff: ${chartTime - lastChartTime}`);
    }
    
    // If it's the "Cannot update oldest data" error, we should trigger a full refresh
    if (error.message.includes('Cannot update oldest data')) {
      if (typeof window !== 'undefined' && window.notify) {
        window.notify('currentCandles');
      }
    }
  }
}

function resetZoomState() {
  // Reset zoom tracking when symbol or timeframe changes
  userHasZoomed = false;
}

function resetChartData() {
  // CRITICAL: Completely reset chart data to prevent timestamp conflicts
  if (candlestickSeries) {
    candlestickSeries.setData([]); // Clear all chart data
    lastChartData = null;
    lastSymbol = null;
    lastTimeframe = null;
  }
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
  resetChartData,
  disposeLightweightChart
};