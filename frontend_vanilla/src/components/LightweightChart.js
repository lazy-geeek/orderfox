import { createChart, CandlestickSeries, HistogramSeries, ColorType } from 'lightweight-charts';

// Convert UTC timestamp to local timezone for chart display
function timeToLocal(originalTime) {
  const d = new Date(originalTime * 1000);
  return Date.UTC(d.getFullYear(), d.getMonth(), d.getDate(), d.getHours(), d.getMinutes(), d.getSeconds(), d.getMilliseconds()) / 1000;
}

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
let volumeSeries = null;
let lastChartData = null;
let lastSymbol = null;
let lastTimeframe = null;
let resizeObserver = null;
let currentTheme = 'dark';
let userHasZoomed = false;
let volumeSeriesVisible = true;
let currentVolumeData = []; // Store volume data for tooltips
let tooltipElement = null;
let chartInitialized = false; // Track if chart has received initial data
let pendingVolumeData = null; // Buffer volume data until chart is ready
let symbolOverlayElement = null; // Symbol overlay element reference

function createLightweightChart(container) {
  const chartContainer = document.createElement('div');
  chartContainer.className = 'chart-container';
  chartContainer.setAttribute('data-testid', 'chart-container');
  container.appendChild(chartContainer);

  // Create symbol overlay element
  symbolOverlayElement = document.createElement('div');
  symbolOverlayElement.className = 'chart-symbol-overlay';
  symbolOverlayElement.setAttribute('data-testid', 'chart-symbol-overlay');
  symbolOverlayElement.style.display = 'none'; // Hidden by default until symbol is set
  chartContainer.appendChild(symbolOverlayElement);

  // Get current theme
  currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
  
  // Initialize chart with theme options
  const chartOptions = getChartOptions(currentTheme);
  
  // Defer chart creation to avoid forced reflow
  // Use double requestAnimationFrame to ensure layout is complete
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      if (!chartContainer.parentNode) return; // Container might have been removed
      
      // Only read dimensions after layout is stable
      chartOptions.width = chartContainer.clientWidth;
      chartOptions.height = chartContainer.clientHeight;
      
      // Create chart only after dimensions are available
      createChartInstance(chartContainer, chartOptions);
    });
  });

  return chartContainer;
}

function createChartInstance(chartContainer, chartOptions) {
  chartInstance = createChart(chartContainer, chartOptions);
  
  // Add candlestick series with adjusted margins
  candlestickSeries = chartInstance.addSeries(CandlestickSeries, getCandlestickOptions());
  
  // Adjust candlestick series to use top 60% of chart
  candlestickSeries.priceScale().applyOptions({
    scaleMargins: {
      top: 0.1,    // 10% margin from top
      bottom: 0.4, // 40% margin from bottom
    },
  });

  // Create liquidation volume series as overlay
  volumeSeries = createLiquidationVolumeSeries();

  // Setup responsive sizing with ResizeObserver
  setupResizeObserver(chartContainer);

  // Track user zoom/pan interactions
  chartInstance.timeScale().subscribeVisibleTimeRangeChange(() => {
    userHasZoomed = true;
  });
  
  // Setup tooltip
  setupVolumeTooltip(chartContainer);
  
  // Optimize touch interactions for mobile
  setupMobileTouchOptimizations(chartContainer);

  // Listen for theme changes
  window.addEventListener('themechange', (e) => {
    const newTheme = e.detail.theme;
    switchTheme(newTheme);
  });
}

function getChartOptions(theme) {
  const isDark = theme === 'dark';
  
  return {
    layout: {
      background: { type: ColorType.Solid, color: isDark ? '#1E2329' : '#FAFAFA' },
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

function createLiquidationVolumeSeries() {
  if (!chartInstance) {
    console.warn('Cannot create liquidation volume series - chart instance not ready');
    return null;
  }
  
  console.log('Creating liquidation volume series');
  
  // Create histogram series as overlay
  const series = chartInstance.addSeries(HistogramSeries, {
    priceFormat: {
      type: 'volume',
    },
    priceScaleId: '', // Empty string makes it an overlay
    scaleMargins: {
      top: 0.7,    // Start 70% from top
      bottom: 0,   // Extend to bottom
    },
    lastValueVisible: false, // Don't show last value label
    priceLineVisible: false, // Don't show horizontal price line
  });
  
  return series;
}

function setupResizeObserver(container) {
  if (resizeObserver) {
    resizeObserver.disconnect();
  }
  
  resizeObserver = new ResizeObserver(entries => {
    if (entries.length === 0 || !chartInstance) return;
    const { width, height } = entries[0].contentRect;
    chartInstance.resize(width, height);
    
    // Adjust chart margins for mobile screens
    adjustChartMarginsForScreenSize(width);
  });
  
  resizeObserver.observe(container);
}

function adjustChartMarginsForScreenSize(width) {
  if (!candlestickSeries || !volumeSeries) return;
  
  // Mobile breakpoints
  const isMobile = width < 768;
  const isSmallMobile = width < 480;
  
  if (isSmallMobile) {
    // Very small screens - more space for volume
    candlestickSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.05,
        bottom: 0.5, // 50% for volume
      },
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.65,  // Adjusted for overlay
        bottom: 0,
      },
    });
  } else if (isMobile) {
    // Mobile screens - balanced view
    candlestickSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.05,
        bottom: 0.45, // 45% for volume
      },
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.65,  // Adjusted for overlay
        bottom: 0,
      },
    });
  } else {
    // Desktop - standard margins
    candlestickSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.1,
        bottom: 0.4, // 40% for volume
      },
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.7,   // Standard overlay position
        bottom: 0,
      },
    });
  }
}

function setupMobileTouchOptimizations(container) {
  // Detect if device supports touch
  const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
  
  if (!isTouchDevice || !chartInstance) return;
  
  // Optimize chart for touch interactions
  chartInstance.applyOptions({
    handleScroll: {
      vertTouchDrag: false, // Disable vertical drag to prevent conflicts with page scroll
      mouseWheel: true,
      pressedMouseMove: true,
      horzTouchDrag: true,
    },
    handleScale: {
      axisPressedMouseMove: {
        time: true,
        price: false, // Disable price axis scaling on mobile
      },
      mouseWheel: true,
      pinch: true, // Enable pinch zoom
    },
  });
  
  // Improve tooltip behavior on touch devices
  if (tooltipElement) {
    container.addEventListener('touchstart', () => {
      // Hide tooltip on touch to prevent it from blocking interactions
      tooltipElement.style.display = 'none';
    });
  }
}

function switchTheme(newTheme) {
  currentTheme = newTheme;
  
  if (!chartInstance) return;
  
  // CRITICAL: More efficient than ECharts - use applyOptions instead of disposal
  chartInstance.applyOptions(getChartOptions(newTheme));
  
  // Volume series colors are set per bar, no theme update needed
  
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

function createVolumeToggleButton() {
  const toggleContainer = document.createElement('div');
  toggleContainer.className = 'volume-toggle-container';
  
  const button = document.createElement('button');
  button.className = 'volume-toggle-button active';
  button.textContent = 'Liquidation Volume';
  button.title = 'Toggle liquidation volume display';
  
  button.addEventListener('click', () => {
    const isVisible = toggleLiquidationVolume();
    if (isVisible) {
      button.classList.add('active');
    } else {
      button.classList.remove('active');
    }
  });
  
  toggleContainer.appendChild(button);
  return toggleContainer;
}

function setupVolumeTooltip(container) {
  // Create tooltip element
  tooltipElement = document.createElement('div');
  tooltipElement.className = 'volume-tooltip';
  tooltipElement.style.display = 'none';
  tooltipElement.style.position = 'absolute';
  tooltipElement.style.zIndex = '1000';
  container.appendChild(tooltipElement);
  
  // Subscribe to crosshair move
  chartInstance.subscribeCrosshairMove((param) => {
    if (!volumeSeriesVisible || !currentVolumeData.length || !param.time) {
      tooltipElement.style.display = 'none';
      return;
    }
    
    // Find volume data for the current time
    const volumeData = currentVolumeData.find(d => d.time === param.time);
    if (!volumeData) {
      tooltipElement.style.display = 'none';
      return;
    }
    
    // Get coordinates - ensure volumeSeries exists
    if (!volumeSeries || !param.seriesPrices) {
      tooltipElement.style.display = 'none';
      return;
    }
    
    const coordinate = param.seriesPrices.get(volumeSeries);
    if (!coordinate) {
      tooltipElement.style.display = 'none';
      return;
    }
    
    // Format tooltip content
    const buyVolume = volumeData.buy_volume_formatted || volumeData.buy_volume;
    const sellVolume = volumeData.sell_volume_formatted || volumeData.sell_volume;
    const deltaVolume = volumeData.delta_volume_formatted || volumeData.delta_volume;
    const deltaValue = parseFloat(volumeData.delta_volume || 0);
    const timestamp = new Date(volumeData.timestamp_ms || volumeData.time * 1000).toLocaleTimeString();
    
    // Determine dominant side for tooltip
    const dominantSide = deltaValue > 0 ? 'Shorts' : 'Longs';
    const deltaClass = deltaValue > 0 ? 'buy' : 'sell';
    
    tooltipElement.innerHTML = `
      <div class="tooltip-header">Liquidation Volume</div>
      <div class="tooltip-row">
        <span class="tooltip-label">Time:</span>
        <span class="tooltip-value">${timestamp}</span>
      </div>
      <div class="tooltip-row">
        <span class="tooltip-label">Shorts Liquidated:</span>
        <span class="tooltip-value buy">${buyVolume}</span>
      </div>
      <div class="tooltip-row">
        <span class="tooltip-label">Longs Liquidated:</span>
        <span class="tooltip-value sell">${sellVolume}</span>
      </div>
      <div class="tooltip-row">
        <span class="tooltip-label">Net (${dominantSide}):</span>
        <span class="tooltip-value ${deltaClass}">${deltaVolume}</span>
      </div>
    `;
    
    // Position tooltip
    const y = param.point.y;
    let x = param.point.x;
    
    // Adjust position to keep tooltip visible
    const tooltipWidth = 200;
    const containerWidth = container.clientWidth;
    
    if (x + tooltipWidth > containerWidth) {
      x = x - tooltipWidth - 10;
    } else {
      x = x + 10;
    }
    
    tooltipElement.style.left = x + 'px';
    tooltipElement.style.top = y + 'px';
    tooltipElement.style.display = 'block';
  });
}

function updateLightweightChart(data, symbol, timeframe, isInitialLoad = false, symbolData = null) {
  if (!chartInstance || !candlestickSeries) return;

  // CRITICAL: Check if this is a symbol or timeframe change
  const isSymbolChange = lastSymbol !== symbol;
  const isTimeframeChange = lastTimeframe !== timeframe;
  const isContextChange = isSymbolChange || isTimeframeChange;
  
  // Enhanced symbol change detection for price scale reset
  // Reason: Only reset price scale when switching between symbols (not initial load)
  // This prevents unnecessary resets while ensuring proper scaling for new symbols
  const requiresPriceScaleReset = isSymbolChange && lastSymbol !== null;

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
    // Only warn if chart was previously initialized - avoid warnings on initial load
    if (chartInitialized) {
      console.warn(`No candle data available for ${symbol} ${timeframe}`);
    }
    // Clear the chart but don't break
    candlestickSeries.setData([]);
    return;
  }

  // Backend provides data ready for Lightweight Charts
  // Backend sends: { time: seconds, timestamp: milliseconds, open, high, low, close }
  // Convert UTC timestamps to local time for chart display
  const formattedData = currentCandles.map(candle => ({
    time: timeToLocal(candle.time), // Convert UTC to local time
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

  // Mark chart as initialized after first successful data load
  if (!chartInitialized) {
    chartInitialized = true;
    
    // Process any pending volume data
    if (pendingVolumeData) {
      updateLiquidationVolume(pendingVolumeData);
      pendingVolumeData = null;
    }
  }

  // Update chart title - we'll add this as a visual indicator
  updateChartTitle(symbol, timeframe);

  // CRITICAL: Always fit content on context changes, respect user zoom for updates
  if (isInitialLoad || isContextChange || !userHasZoomed) {
    // Ensure the chart properly fits the new data
    chartInstance.timeScale().fitContent();
    
    // For symbol changes, trigger comprehensive price scale reset
    // Reason: Different symbols have vastly different price ranges (BTC ~$50k vs EUR ~$1.05)
    // Multiple API calls ensure all price scale components are properly reset
    if (requiresPriceScaleReset) {
      resetPriceScaleForSymbolChange(true, 'auto');
    }
  }
}

function updateChartTitle(symbol, timeframe) {
  // Update the overlay text
  if (symbolOverlayElement) {
    if (symbol) {
      symbolOverlayElement.textContent = symbol;
      symbolOverlayElement.style.display = 'block';
    } else {
      symbolOverlayElement.style.display = 'none';
    }
  }
  
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

function showPriceScaleResetFeedback(trigger = 'auto') {
  // Create visual feedback for price scale reset
  const feedbackEvent = new CustomEvent('priceScaleResetFeedback', {
    detail: {
      message: trigger === 'double-click' ? 'Price scale reset manually' : 'Price scale auto-adjusted',
      trigger: trigger,
      symbol: lastSymbol,
      timeframe: lastTimeframe,
      timestamp: Date.now()
    }
  });
  window.dispatchEvent(feedbackEvent);
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
  // Convert to local time to match chart's timezone
  const chartTime = timeToLocal(candleData.time); // Convert UTC to local time
  
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
    if (!candlestickSeries) {
      console.error('Candlestick series not initialized');
      return;
    }
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

function resetPriceScaleForSymbolChange(showFeedback = false, trigger = 'auto') {
  if (!chartInstance || !candlestickSeries) return;
  
  try {
    // Method 1: Via chart right price scale API
    // Reason: Resets the main price scale axis for the chart
    const rightPriceScale = chartInstance.priceScale('right');
    rightPriceScale.setAutoScale(true);
    
    // Method 2: Via series price scale API
    // Reason: Ensures the candlestick series price scale is properly reset
    const seriesPriceScale = candlestickSeries.priceScale();
    seriesPriceScale.setAutoScale(true);
    seriesPriceScale.applyOptions({autoScale: true});
    
    // Method 3: Apply options directly to candlestick series
    // Reason: Alternative approach to ensure series-level price scale reset
    candlestickSeries.applyOptions({
      priceScale: {
        autoScale: true,
      }
    });
    
    // Method 4: Force time scale fit to ensure proper display
    // Reason: Ensures the time axis properly fits the new symbol's data range
    chartInstance.timeScale().fitContent();
    
    // Method 5: Reset volume series price scale if exists
    // Reason: Volume overlay must also adjust to new symbol's price range
    if (volumeSeries) {
      const volumePriceScale = volumeSeries.priceScale();
      volumePriceScale.setAutoScale(true);
      volumePriceScale.applyOptions({autoScale: true});
    }
    
    // Show visual feedback if requested
    if (showFeedback) {
      showPriceScaleResetFeedback(trigger);
    }
    
  } catch (error) {
    console.error('Price scale reset failed:', error);
  }
}

function resetZoomState() {
  // Reset zoom tracking when symbol or timeframe changes
  userHasZoomed = false;
  // Reset chart initialization state for new symbol/timeframe
  chartInitialized = false;
}

function updateLiquidationVolume(volumeData, isRealTimeUpdate = false) {
  console.log('updateLiquidationVolume called, volumeSeries:', !!volumeSeries, 'visible:', volumeSeriesVisible, 'isRealTimeUpdate:', isRealTimeUpdate);
  if (!volumeSeries || !volumeSeriesVisible) {
    console.warn('Volume series not ready or not visible');
    return;
  }
  
  // If chart hasn't been initialized yet, buffer the volume data
  if (!chartInitialized) {
    pendingVolumeData = volumeData;
    return;
  }
  
  // Debug: Log sample of volume data
  console.log('Updating liquidation volume with', volumeData.length, 'data points', 'isRealTimeUpdate:', isRealTimeUpdate);
  if (volumeData.length > 0) {
    console.log('Sample data:', volumeData[0], '...', volumeData[volumeData.length - 1]);
  }
  
  if (isRealTimeUpdate && volumeData.length === 1) {
    // Real-time update - use update() method to preserve existing data
    const item = volumeData[0];
    const deltaVolume = parseFloat(item.delta_volume || 0);
    
    if (deltaVolume !== 0) {
      const color = deltaVolume > 0 ? '#0ECB81' : '#F6465D';
      const histogramBar = {
        time: timeToLocal(item.time),
        value: Math.abs(deltaVolume),
        color: color,
      };
      
      try {
        // CRITICAL: Use update() for real-time updates to preserve historical data
        volumeSeries.update(histogramBar);
        console.log('Updated liquidation volume bar:', histogramBar);
        
        // Update currentVolumeData for tooltips
        // Find and update existing entry or add new one
        const existingIndex = currentVolumeData.findIndex(d => d.time === item.time);
        if (existingIndex >= 0) {
          currentVolumeData[existingIndex] = item;
        } else {
          // Insert in correct position to maintain time order
          currentVolumeData.push(item);
          currentVolumeData.sort((a, b) => a.time - b.time);
        }
      } catch (error) {
        console.error('Error updating liquidation volume:', error);
        // Fall back to setData if update fails
        updateLiquidationVolume(volumeData, false);
      }
    }
  } else if (isRealTimeUpdate && volumeData.length > 1) {
    // Real-time batch update - use update() for each item
    console.log('Processing real-time batch update with', volumeData.length, 'items');
    
    volumeData.forEach(item => {
      const deltaVolume = parseFloat(item.delta_volume || 0);
      
      if (deltaVolume !== 0) {
        const color = deltaVolume > 0 ? '#0ECB81' : '#F6465D';
        const histogramBar = {
          time: timeToLocal(item.time),
          value: Math.abs(deltaVolume),
          color: color,
        };
        
        try {
          volumeSeries.update(histogramBar);
          
          // Update currentVolumeData for tooltips
          const existingIndex = currentVolumeData.findIndex(d => d.time === item.time);
          if (existingIndex >= 0) {
            currentVolumeData[existingIndex] = item;
          } else {
            currentVolumeData.push(item);
          }
        } catch (error) {
          console.error('Error updating liquidation volume bar:', error, histogramBar);
        }
      }
    });
    
    // Sort after batch update
    currentVolumeData.sort((a, b) => a.time - b.time);
  } else {
    // Initial load - use setData() to establish the baseline
    console.log('Initial volume data load - using setData()');
    
    // Store volume data for tooltips
    currentVolumeData = volumeData;
    
    // Process volume data into histogram format using delta
    const histogramData = volumeData
      .filter(item => {
        // Filter out items with zero delta (no bars to show)
        const deltaVolume = parseFloat(item.delta_volume || 0);
        return deltaVolume !== 0;
      })
      .map(item => {
        // Use delta volume from backend
        const deltaVolume = parseFloat(item.delta_volume || 0);
        
        // Green if delta > 0 (more shorts liquidated), red if delta < 0 (more longs liquidated)
        const color = deltaVolume > 0 ? '#0ECB81' : '#F6465D';
        
        return {
          time: timeToLocal(item.time), // Convert UTC to local time to match candles
          value: Math.abs(deltaVolume), // Use absolute value for bar height
          color: color,
        };
      });
    
    console.log('Filtered histogram data points with non-zero values:', histogramData.length);
    
    // Update series data
    if (!volumeSeries) {
      console.warn('Volume series not initialized - cannot update liquidation volume');
      return;
    }
    // CRITICAL: Only use setData() for initial load, not for updates
    volumeSeries.setData(histogramData);
  }
  
  // Don't call fitContent here as it affects the main chart zoom
}

function toggleLiquidationVolume() {
  if (!volumeSeries) {
    console.warn('Volume series not initialized');
    return false;
  }
  
  volumeSeriesVisible = !volumeSeriesVisible;
  
  if (volumeSeriesVisible) {
    volumeSeries.applyOptions({ visible: true });
  } else {
    volumeSeries.applyOptions({ visible: false });
  }
  
  return volumeSeriesVisible;
}

function resetChartData() {
  // CRITICAL: Completely reset chart data to prevent timestamp conflicts
  if (candlestickSeries) {
    candlestickSeries.setData([]); // Clear all chart data
    lastChartData = null;
    lastSymbol = null;
    lastTimeframe = null;
  }
  
  if (volumeSeries) {
    volumeSeries.setData([]); // Clear volume data
    currentVolumeData = []; // Clear stored volume data
  }
  
  if (tooltipElement) {
    tooltipElement.style.display = 'none'; // Hide tooltip
  }
  
  // Reset initialization state
  chartInitialized = false;
  pendingVolumeData = null;
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
  volumeSeries = null;
  lastChartData = null;
  lastSymbol = null;
  lastTimeframe = null;
  userHasZoomed = false;
  volumeSeriesVisible = true;
  chartInitialized = false;
  pendingVolumeData = null;
  symbolOverlayElement = null;
}

// Export functions for backward compatibility with existing code
export { 
  createLightweightChart as createCandlestickChart, 
  createLightweightChart,
  createTimeframeSelector,
  createVolumeToggleButton,
  updateLightweightChart as updateCandlestickChart,
  updateLatestCandle,
  updateLiquidationVolume,
  toggleLiquidationVolume,
  updateChartTitle,
  resetZoomState,
  resetChartData,
  disposeLightweightChart
};