
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
        axisPointer: {
          type: 'cross'
        }
    },
    grid: {
      left: '10%',
      right: '10%',
      bottom: '15%'
    },
    xAxis: {
      type: 'time',
      scale: true
    },
    yAxis: {
      scale: true,
      splitArea: {
        show: true
      }
    },
    dataZoom: [
      {
        type: 'inside',
        start: 50,
        end: 100
      },
      {
        show: true,
        type: 'slider',
        top: '90%',
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
      }
    ]
  };

  chartInstance.setOption(option);
}

export { createCandlestickChart, createTimeframeSelector, updateCandlestickChart };
