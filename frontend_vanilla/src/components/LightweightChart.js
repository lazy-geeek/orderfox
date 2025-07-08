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

  // Reduced logging for normal operation
  if (isContextChange) {
    console.log(`Chart: Context change - Symbol: ${symbol}, Timeframe: ${timeframe}`);
  }

  // Store the last data for theme changes
  lastChartData = data;
  lastSymbol = symbol;
  lastTimeframe = timeframe;

  // CRITICAL: Reset zoom state on context changes to allow proper fitting
  if (isContextChange) {
    console.log(`Chart: Context change detected - Symbol: ${isSymbolChange}, Timeframe: ${isTimeframeChange}`);
    resetZoomState();
  }

  // Only update price format when symbol data is provided (symbol change or initial load)
  if (symbolData && candlestickSeries) {
    let precision = 2; // Default precision
    
    // Extract and validate precision from symbolData
    if (symbolData.pricePrecision !== undefined && symbolData.pricePrecision !== null) {
      // Validate precision is a non-negative integer and clamp to reasonable range (0-8)
      const rawPrecision = symbolData.pricePrecision;
      if (typeof rawPrecision === 'number' && !isNaN(rawPrecision) && rawPrecision >= 0) {
        precision = Math.max(0, Math.min(8, Math.floor(rawPrecision)));
      } else {
        console.warn(`Invalid pricePrecision value for ${symbol}: ${rawPrecision}, using default precision: ${precision}`);
      }
    } else {
      console.warn(`Missing pricePrecision for ${symbol}, using default precision: ${precision}`);
    }
    
    // Apply price format with validated precision
    candlestickSeries.applyOptions({
      priceFormat: {
        type: 'price',
        precision: precision,
        minMove: 1 / Math.pow(10, precision),
      },
    });
  }

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

  // Only log chart data details for context changes or initial loads
  if (isInitialLoad || isContextChange) {
    console.log(`Chart: Loading ${formattedData.length} candles for ${symbol} ${timeframe}`);
  }

  // CRITICAL: Use setData to completely replace chart data
  // This clears any previous data and prevents timestamp ordering conflicts
  candlestickSeries.setData(formattedData);

  // Update chart title - we'll add this as a visual indicator
  updateChartTitle(symbol, timeframe);

  // CRITICAL: Always fit content on context changes, respect user zoom for updates
  if (isInitialLoad || isContextChange || !userHasZoomed) {
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
  if (!candlestickSeries) {
    console.warn('Chart: No candlestick series available for update');
    return;
  }

  // CRITICAL: Import state to validate current symbol
  if (typeof window !== 'undefined' && window.state) {
    // Validate that this candle is for the current symbol
    if (window.state.selectedSymbol && candleData.symbol && candleData.symbol !== window.state.selectedSymbol) {
      console.warn('Chart: Rejecting candle update for wrong symbol:', candleData.symbol, 'vs', window.state.selectedSymbol);
      return;
    }
  }

  // CRITICAL: Enhanced timestamp validation and debugging
  const rawTimestamp = candleData.timestamp;
  const convertedTime = Math.floor(rawTimestamp / 1000); // Convert milliseconds to seconds
  
  // Get current chart data to check ordering
  let lastChartTime = null;
  try {
    // Try to get the current data from the series to check timestamp ordering
    const currentData = candlestickSeries.data();
    if (currentData && currentData.length > 0) {
      lastChartTime = currentData[currentData.length - 1].time;
      
      // Check for timestamp ordering issues
      if (convertedTime <= lastChartTime) {
        const timeDiff = lastChartTime - convertedTime;
        
        // If it's a very old update (more than 5 minutes), reject it
        if (timeDiff > 300) { // 5 minutes
          console.warn('Chart: Rejecting very old candle update to prevent chart errors');
          console.warn(`Chart: Time difference: ${timeDiff} seconds`);
          return;
        }
        
        // Only log if it's a significant time difference (more than same timestamp)
        if (timeDiff > 0) {
          console.debug(`Chart: Timestamp ordering issue - rejecting update ${timeDiff}s older than current`);
        }
        // For same timestamp (timeDiff = 0), don't log - this is normal for real-time updates
      }
    }
  } catch (e) {
    console.debug('Chart: Could not get current chart data for comparison:', e.message);
  }

  // CRITICAL: Use update() for real-time updates, not setData()
  // This preserves zoom state and is more efficient for single candle updates
  const formattedCandle = {
    time: convertedTime,
    open: candleData.open,
    high: candleData.high,
    low: candleData.low,
    close: candleData.close,
  };

  try {
    candlestickSeries.update(formattedCandle);
    // Only log success in debug mode for troubleshooting
    // console.debug('Chart: Successfully updated candle');
  } catch (error) {
    // CRITICAL: Catch and log TradingView chart errors without crashing
    console.error('Chart update error (likely "Cannot update oldest data"):', error.message);
    console.error('Raw candle data causing error:', candleData);
    console.error('Formatted candle data causing error:', formattedCandle);
    
    if (lastChartTime !== null) {
      console.error(`Chart: Timestamp comparison - Last: ${lastChartTime}, Attempted: ${convertedTime}, Diff: ${convertedTime - lastChartTime}`);
    }
    
    // If it's the "Cannot update oldest data" error, we should trigger a full refresh
    if (error.message.includes('Cannot update oldest data')) {
      console.log('Triggering full chart refresh due to timestamp ordering issue');
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
    console.log('Chart: Resetting chart data completely');
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