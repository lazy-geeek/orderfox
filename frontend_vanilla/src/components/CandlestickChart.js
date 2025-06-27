
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
  chartContainer.style.height = '500px';
  chartContainer.style.width = '100%';
  container.appendChild(chartContainer);

  chartInstance = echarts.init(chartContainer);

  return chartContainer;
}

function createTimeframeSelector(handleTimeframeChange) {
  const timeframeContainer = document.createElement('div');
  timeframeContainer.style.marginBottom = '20px';
  timeframeContainer.style.display = 'flex';
  timeframeContainer.style.alignItems = 'center';
  timeframeContainer.style.gap = '10px';
  timeframeContainer.style.flexWrap = 'wrap';

  const label = document.createElement('span');
  label.style.fontWeight = 'bold';
  label.style.marginRight = '10px';
  label.textContent = 'Timeframe:';
  timeframeContainer.appendChild(label);

  TIMEFRAMES.forEach(tf => {
    const button = document.createElement('button');
    button.textContent = tf.label;
    button.dataset.timeframe = tf.value;
    button.style.padding = '8px 16px';
    button.style.border = '1px solid #ddd';
    button.style.borderRadius = '4px';
    button.style.cursor = 'pointer';
    button.style.fontSize = '14px';
    button.style.transition = 'all 0.2s';
    button.addEventListener('click', () => handleTimeframeChange(tf.value));
    timeframeContainer.appendChild(button);
  });

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
    title: {
      text: symbol ? `${symbol} - ${timeframe}` : 'Select a Symbol',
      left: 'center',
      textStyle: {
        color: '#333',
        fontSize: 16
      }
    },
    tooltip: {
        trigger: 'axis',
        showContent: false,
        axisPointer: {
          type: 'cross'
        }
    },
    grid: {
      left: '5%',
      right: '80px',
      bottom: '15%'
    },
    xAxis: {
      type: 'time',
      scale: true
    },
    yAxis: {
      position: 'right',
      scale: true,
      splitArea: {
        show: true
      },
      axisLabel: {
        formatter: function (value) {
          return value.toFixed(currentPrice && currentPrice < 1 ? 6 : 2);
        }
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
          color: '#00da3c',
          color0: '#ec0000',
          borderColor: '#00da3c',
          borderColor0: '#ec0000'
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
                color: '#ff6b35',
                width: 2,
                type: 'dashed'
              },
              label: {
                show: true,
                position: 'insideEndTop',
                formatter: function() {
                  return currentPrice.toFixed(currentPrice < 1 ? 6 : 2);
                },
                backgroundColor: '#ff6b35',
                color: '#fff',
                padding: [4, 8],
                borderRadius: 4,
                fontSize: 12,
                fontWeight: 'bold'
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
