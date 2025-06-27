
import * as echarts from 'echarts';

const TIMEFRAMES = [
  { value: '1m', label: '1m' },
  { value: '5m', label: '5m' },
  { value: '15m', label: '15m' },
  { value: '1h', label: '1h' },
  { value: '4h', label: '4h' },
  { value: '1d', label: '1d' },
];

let chartInstance = null;

function createCandlestickChart(container) {
  const chartContainer = document.createElement('div');
  chartContainer.className = 'chart-container';
  chartContainer.style.height = '500px';
  chartContainer.style.width = '100%';
  container.appendChild(chartContainer);

  chartInstance = echarts.init(chartContainer, 'dark');

  return chartContainer;
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

function updateCandlestickChart(data, symbol, timeframe) {
  if (!chartInstance) return;

  const { currentCandles, candlesWsConnected } = data;

  const formattedData = currentCandles.map(candle => [
    candle.timestamp,
    candle.open,
    candle.close,
    candle.low,
    candle.high,
    candle.volume
  ]);

  // Get current price from the latest candle's close price
  const currentPrice = currentCandles.length > 0 ? currentCandles[currentCandles.length - 1].close : null;

  // Preserve current zoom state
  const currentOption = chartInstance.getOption();
  const currentDataZoom = currentOption?.dataZoom || [];

  const option = {
    backgroundColor: '#1E2329',
    title: {
      text: symbol ? `${symbol} - ${timeframe}` : 'Select a Symbol',
      left: 'center',
      textStyle: {
        color: '#EAECEF',
        fontSize: 16,
        fontFamily: 'Inter, sans-serif',
        fontWeight: 600
      }
    },
    tooltip: {
        trigger: 'axis',
        showContent: false,
        axisPointer: {
          type: 'cross',
          crossStyle: {
            color: '#848E9C'
          }
        }
    },
    grid: {
      left: '5%',
      right: '80px',
      bottom: '15%',
      backgroundColor: 'transparent',
      borderColor: '#2B3139'
    },
    xAxis: {
      type: 'time',
      scale: true,
      axisLine: {
        lineStyle: {
          color: '#2B3139'
        }
      },
      axisLabel: {
        color: '#848E9C',
        fontFamily: 'Inter, sans-serif'
      },
      splitLine: {
        show: false
      }
    },
    yAxis: {
      position: 'right',
      scale: true,
      axisLine: {
        lineStyle: {
          color: '#2B3139'
        }
      },
      axisLabel: {
        color: '#848E9C',
        fontFamily: 'Inter, sans-serif',
        formatter: function (value) {
          return value.toFixed(currentPrice && currentPrice < 1 ? 6 : 2);
        }
      },
      splitLine: {
        lineStyle: {
          color: '#2B3139',
          type: 'dashed'
        }
      },
      splitArea: {
        show: false
      }
    },
    dataZoom: currentDataZoom.length > 0 ? currentDataZoom : [
      {
        type: 'inside',
        start: 50,
        end: 100
      }
    ],
    series: [
      {
        name: 'Candlestick',
        type: 'candlestick',
        data: formattedData,
        itemStyle: {
          color: '#0ECB81',
          color0: '#F6465D',
          borderColor: '#0ECB81',
          borderColor0: '#F6465D'
        }
      },
      // Current price line
      currentPrice ? {
        name: 'Current Price',
        type: 'line',
        markLine: {
          silent: true,
          symbol: 'none',
          data: [
            {
              yAxis: currentPrice,
              lineStyle: {
                color: '#FCD535',
                width: 2,
                type: 'dashed'
              },
              label: {
                show: true,
                position: 'insideEndTop',
                formatter: function() {
                  return currentPrice.toFixed(currentPrice < 1 ? 6 : 2);
                },
                backgroundColor: '#FCD535',
                color: '#181A20',
                padding: [4, 8],
                borderRadius: 4,
                fontSize: 12,
                fontWeight: 'bold',
                fontFamily: 'Inter, sans-serif'
              }
            }
          ]
        }
      } : null
    ].filter(Boolean)
  };

  chartInstance.setOption(option, { notMerge: false });
}

export { createCandlestickChart, createTimeframeSelector, updateCandlestickChart };
