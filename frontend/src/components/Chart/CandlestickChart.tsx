import React, { useEffect, useRef, useCallback } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import ReactECharts from 'echarts-for-react';
import { RootState, AppDispatch } from '../../store/store';
import {
  fetchCandles,
  setSelectedTimeframe,
  startCandlesWebSocket,
  stopCandlesWebSocket
} from '../../features/marketData/marketDataSlice';

interface CandlestickChartProps {
  className?: string;
}

const TIMEFRAMES = [
  { value: '1m', label: '1m' },
  { value: '5m', label: '5m' },
  { value: '15m', label: '15m' },
  { value: '1h', label: '1h' },
  { value: '4h', label: '4h' },
  { value: '1d', label: '1d' },
];

const CandlestickChart: React.FC<CandlestickChartProps> = ({ className }) => {
  const dispatch = useDispatch<AppDispatch>();
  const {
    selectedSymbol,
    selectedTimeframe,
    currentCandles,
    candlesLoading,
    candlesError,
    candlesWsConnected,
  } = useSelector((state: RootState) => state.marketData);

  const chartRef = useRef<ReactECharts | null>(null);

  /**
   * Format candle data for ECharts
   * ECharts expects: [timestamp, open, close, low, high, volume]
   */
  const formatCandleData = useCallback(() => {
    // console.log('Formatting candle data. currentCandles:', currentCandles); // Keep for debugging if needed
    if (!currentCandles || !Array.isArray(currentCandles) || currentCandles.length === 0) {
      return [];
    }

    return currentCandles.filter(candle => {
      const isValid =
        typeof candle.timestamp === 'number' &&
        typeof candle.open === 'number' &&
        typeof candle.close === 'number' &&
        typeof candle.low === 'number' &&
        typeof candle.high === 'number' &&
        typeof candle.volume === 'number';
      
      if (!isValid) {
        console.warn('Skipping invalid candle data:', candle);
      }
      return isValid;
    }).map(candle => [
      candle.timestamp,
      candle.open,
      candle.close,
      candle.low,
      candle.high,
      candle.volume
    ]);
  }, [currentCandles]);

  /**
   * Get chart options for ECharts
   */
  const getChartOptions = useCallback(() => {
    const candleData = formatCandleData();

    return {
      title: {
        text: selectedSymbol ? `${selectedSymbol} - ${selectedTimeframe}` : 'Select a Symbol',
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
        },
        formatter: function (params: any) {
          const data = params && params.length > 0 ? params[0] : null;
          if (!data || !data.data) return '';

          const [timestamp, open, close, low, high, volume] = data.data;
          const date = new Date(timestamp).toLocaleString();

          return `
            <div>
              <strong>${date}</strong><br/>
              Open: ${open}<br/>
              High: ${high}<br/>
              Low: ${low}<br/>
              Close: ${close}<br/>
              Volume: ${volume}
            </div>
          `;
        }
      },
      grid: {
        left: '10%',
        right: '10%',
        bottom: '15%'
      },
      xAxis: {
        type: 'time',
        scale: true,
        axisLabel: {
          formatter: function (value: number) {
            return new Date(value).toLocaleTimeString();
          }
        }
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
          data: candleData.length > 0 ? candleData : [],
          itemStyle: {
            color: '#00da3c',
            color0: '#ec0000',
            borderColor: '#00da3c',
            borderColor0: '#ec0000'
          }
        }
      ]
    };
  }, [selectedSymbol, selectedTimeframe, formatCandleData]);

  /**
   * Handle timeframe change
   */
  const handleTimeframeChange = useCallback(async (newTimeframe: string) => {
    dispatch(setSelectedTimeframe(newTimeframe));
    
    if (selectedSymbol) {
      dispatch(fetchCandles({
        symbol: selectedSymbol,
        timeframe: newTimeframe,
        limit: 100
      }));
      // Restart WebSocket with new timeframe
      await dispatch(stopCandlesWebSocket({ symbol: selectedSymbol, timeframe: selectedTimeframe }));
      await dispatch(startCandlesWebSocket({ symbol: selectedSymbol, timeframe: newTimeframe }));
    }
  }, [selectedSymbol, selectedTimeframe, dispatch]);

  /**
   * Effect: Fetch initial historical data when selectedSymbol or selectedTimeframe changes
   */
  useEffect(() => {
    if (selectedSymbol && selectedTimeframe) {
      dispatch(fetchCandles({
        symbol: selectedSymbol,
        timeframe: selectedTimeframe,
        limit: 100
      }));
    }
  }, [selectedSymbol, selectedTimeframe, dispatch]);

  // WebSocket connections are now managed centrally by the Redux slice
  
  // Note: WebSocket errors are logged by websocketService.
  // For specific UI feedback, websocketService could dispatch error actions to Redux.

  /**
   * Render loading state
   */
  if (candlesLoading) {
    return (
      <div className={`candlestick-chart ${className || ''}`}>
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '400px',
          fontSize: '16px',
          color: '#666'
        }}>
          Loading chart data...
        </div>
      </div>
    );
  }

  /**
   * Render error state
   */
  if (candlesError) { // Removed wsError from condition
    return (
      <div className={`candlestick-chart ${className || ''}`}>
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          height: '400px',
          color: '#d32f2f'
        }}>
          <div style={{ fontSize: '16px', marginBottom: '10px' }}>
            Error loading chart data
          </div>
          {candlesError && <div style={{ fontSize: '14px' }}>API Error: {candlesError}</div>}
          {/* Removed wsError display */}
        </div>
      </div>
    );
  }

  /**
   * Render no symbol selected state
   */
  if (!selectedSymbol) {
    return (
      <div className={`candlestick-chart ${className || ''}`}>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          height: '400px',
          fontSize: '16px',
          color: '#666'
        }}>
          Please select a symbol to view the chart
        </div>
      </div>
    );
  }

  return (
    <div className={`candlestick-chart ${className || ''}`}>
      {/* Timeframe Selection */}
      <div style={{ 
        marginBottom: '20px', 
        display: 'flex', 
        alignItems: 'center', 
        gap: '10px',
        flexWrap: 'wrap'
      }}>
        <span style={{ fontWeight: 'bold', marginRight: '10px' }}>Timeframe:</span>
        {TIMEFRAMES.map((tf) => (
          <button
            key={tf.value}
            onClick={() => handleTimeframeChange(tf.value)}
            style={{
              padding: '8px 16px',
              border: '1px solid #ddd',
              borderRadius: '4px',
              backgroundColor: selectedTimeframe === tf.value ? '#1976d2' : '#fff',
              color: selectedTimeframe === tf.value ? '#fff' : '#333',
              cursor: 'pointer',
              fontSize: '14px',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              if (selectedTimeframe !== tf.value) {
                e.currentTarget.style.backgroundColor = '#f5f5f5';
              }
            }}
            onMouseLeave={(e) => {
              if (selectedTimeframe !== tf.value) {
                e.currentTarget.style.backgroundColor = '#fff';
              }
            }}
          >
            {tf.label}
          </button>
        ))}
        
        {/* WebSocket Status Indicator */}
        <div style={{
          marginLeft: 'auto',
          display: 'flex',
          alignItems: 'center',
          gap: '5px',
          fontSize: '12px'
        }}>
          <div
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: candlesWsConnected ? '#4caf50' : '#f44336'
            }}
          />
          <span style={{ color: candlesWsConnected ? '#4caf50' : '#f44336' }}>
            {candlesWsConnected ? 'Live' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Chart */}
      {!candlesLoading && currentCandles.length > 0 ? (
        <ReactECharts
          key={`${selectedSymbol}-${selectedTimeframe}`} // Add key to force re-mount on symbol/timeframe change
          ref={chartRef}
          option={getChartOptions()}
          style={{ height: '500px', width: '100%' }}
          theme="default"
        />
      ) : !candlesLoading && currentCandles.length === 0 ? (
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '400px',
          fontSize: '16px',
          color: '#666'
        }}>
          No chart data available for the selected symbol and timeframe.
        </div>
      ) : null /* Render nothing while loading, or handle with a specific loading indicator if preferred */}
    </div>
  );
};

export default CandlestickChart;