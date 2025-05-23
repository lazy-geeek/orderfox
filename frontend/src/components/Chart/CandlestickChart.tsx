import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import ReactECharts from 'echarts-for-react';
import { RootState, AppDispatch } from '../../store/store';
import { 
  fetchCandles, 
  updateCandlesFromWebSocket 
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
  const { selectedSymbol, currentCandles, isLoading, error } = useSelector(
    (state: RootState) => state.marketData
  );

  const [timeframe, setTimeframe] = useState<string>('1m');
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const [wsError, setWsError] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const chartRef = useRef<ReactECharts | null>(null);

  /**
   * Format candle data for ECharts
   * ECharts expects: [timestamp, open, close, low, high, volume]
   */
  const formatCandleData = useCallback(() => {
    return currentCandles.map(candle => [
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
        text: selectedSymbol ? `${selectedSymbol} - ${timeframe}` : 'Select a Symbol',
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
          const data = params[0];
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
          data: candleData,
          itemStyle: {
            color: '#00da3c',
            color0: '#ec0000',
            borderColor: '#00da3c',
            borderColor0: '#ec0000'
          }
        }
      ]
    };
  }, [selectedSymbol, timeframe, formatCandleData]);

  /**
   * Establish WebSocket connection
   */
  const connectWebSocket = useCallback(() => {
    if (!selectedSymbol || !timeframe) return;

    // Close existing connection
    if (wsRef.current && wsRef.current.close) {
      wsRef.current.close();
    }

    const wsUrl = `ws://localhost:8000/ws/candles/${selectedSymbol}/${timeframe}`;
    
    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log(`WebSocket connected: ${wsUrl}`);
        setWsConnected(true);
        setWsError(null);
      };

      ws.onmessage = (event) => {
        try {
          const candleData = JSON.parse(event.data);
          dispatch(updateCandlesFromWebSocket(candleData));
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
          setWsError('Error parsing WebSocket data');
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setWsError('WebSocket connection error');
        setWsConnected(false);
      };

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setWsConnected(false);
        
        // Attempt to reconnect after 3 seconds if not manually closed
        if (event.code !== 1000 && selectedSymbol) {
          setTimeout(() => {
            if (selectedSymbol && timeframe) {
              connectWebSocket();
            }
          }, 3000);
        }
      };
    } catch (error) {
      console.error('Error creating WebSocket connection:', error);
      setWsError('Failed to create WebSocket connection');
    }
  }, [selectedSymbol, timeframe, dispatch]);

  /**
   * Handle timeframe change
   */
  const handleTimeframeChange = useCallback((newTimeframe: string) => {
    setTimeframe(newTimeframe);
    
    // Fetch new historical data
    if (selectedSymbol) {
      dispatch(fetchCandles({ 
        symbol: selectedSymbol, 
        timeframe: newTimeframe, 
        limit: 100 
      }));
    }
  }, [selectedSymbol, dispatch]);

  /**
   * Effect: Fetch initial data when selectedSymbol changes
   */
  useEffect(() => {
    if (selectedSymbol) {
      dispatch(fetchCandles({ 
        symbol: selectedSymbol, 
        timeframe, 
        limit: 100 
      }));
    }
  }, [selectedSymbol, dispatch, timeframe]);

  /**
   * Effect: Establish WebSocket connection when symbol or timeframe changes
   */
  useEffect(() => {
    if (selectedSymbol && timeframe) {
      connectWebSocket();
    }

    // Cleanup on unmount or dependency change
    return () => {
      if (wsRef.current && wsRef.current.close) {
        wsRef.current.close();
      }
    };
  }, [selectedSymbol, timeframe, connectWebSocket]);

  /**
   * Render loading state
   */
  if (isLoading) {
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
  if (error || wsError) {
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
          {error && <div style={{ fontSize: '14px' }}>API Error: {error}</div>}
          {wsError && <div style={{ fontSize: '14px' }}>WebSocket Error: {wsError}</div>}
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
              backgroundColor: timeframe === tf.value ? '#1976d2' : '#fff',
              color: timeframe === tf.value ? '#fff' : '#333',
              cursor: 'pointer',
              fontSize: '14px',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              if (timeframe !== tf.value) {
                e.currentTarget.style.backgroundColor = '#f5f5f5';
              }
            }}
            onMouseLeave={(e) => {
              if (timeframe !== tf.value) {
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
              backgroundColor: wsConnected ? '#4caf50' : '#f44336'
            }}
          />
          <span style={{ color: wsConnected ? '#4caf50' : '#f44336' }}>
            {wsConnected ? 'Live' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Chart */}
      <ReactECharts
        ref={chartRef}
        option={getChartOptions()}
        style={{ height: '500px', width: '100%' }}
        notMerge={true}
        lazyUpdate={true}
        theme="default"
      />
    </div>
  );
};

export default CandlestickChart;