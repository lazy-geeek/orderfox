"""
Unit tests for ChartDataService.

Tests the chart data processing and formatting functionality for 
Lightweight Charts integration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.chart_data_service import ChartDataService


class TestChartDataService:
    """Test ChartDataService functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.chart_service = ChartDataService()
        
    def test_validate_candle_data_valid(self):
        """Test validation of valid candle data."""
        valid_candle = {
            'timestamp': 1640995200000,
            'open': 50000.0,
            'high': 50500.0,
            'low': 49500.0,
            'close': 50250.0,
            'volume': 100.0
        }
        
        assert self.chart_service.validate_candle_data(valid_candle) is True
    
    def test_validate_candle_data_invalid_ohlc_relationship(self):
        """Test validation fails for invalid OHLC relationships."""
        invalid_candle = {
            'timestamp': 1640995200000,
            'open': 50000.0,
            'high': 49000.0,  # Invalid: high < open
            'low': 51000.0,   # Invalid: low > open  
            'close': 50250.0,
            'volume': 100.0
        }
        
        assert self.chart_service.validate_candle_data(invalid_candle) is False
    
    def test_validate_candle_data_missing_fields(self):
        """Test validation fails for missing required fields."""
        incomplete_candle = {
            'timestamp': 1640995200000,
            'open': 50000.0,
            # Missing high, low, close, volume
        }
        
        assert self.chart_service.validate_candle_data(incomplete_candle) is False
    
    def test_validate_candle_data_negative_values(self):
        """Test validation fails for negative price values."""
        negative_candle = {
            'timestamp': 1640995200000,
            'open': -50000.0,  # Invalid: negative price
            'high': 50500.0,
            'low': 49500.0,
            'close': 50250.0,
            'volume': 100.0
        }
        
        assert self.chart_service.validate_candle_data(negative_candle) is False
    
    def test_validate_candle_data_negative_volume(self):
        """Test validation fails for negative volume."""
        negative_volume_candle = {
            'timestamp': 1640995200000,
            'open': 50000.0,
            'high': 50500.0,
            'low': 49500.0,
            'close': 50250.0,
            'volume': -100.0  # Invalid: negative volume
        }
        
        assert self.chart_service.validate_candle_data(negative_volume_candle) is False
    
    def test_validate_candle_data_zero_volume_allowed(self):
        """Test validation allows zero volume."""
        zero_volume_candle = {
            'timestamp': 1640995200000,
            'open': 50000.0,
            'high': 50500.0,
            'low': 49500.0,
            'close': 50250.0,
            'volume': 0.0  # Valid: zero volume allowed
        }
        
        assert self.chart_service.validate_candle_data(zero_volume_candle) is True
    
    @pytest.mark.asyncio
    async def test_format_realtime_update(self):
        """Test formatting real-time candle updates."""
        candle_data = {
            'symbol': 'BTCUSDT',
            'timeframe': '1m',
            'timestamp': 1640995200000,
            'open': 50000.0,
            'high': 50500.0,
            'low': 49500.0,
            'close': 50250.0,
            'volume': 100.0
        }
        
        result = await self.chart_service.format_realtime_update(candle_data)
        
        expected = {
            'type': 'candle_update',
            'symbol': 'BTCUSDT',
            'timeframe': '1m',
            'timestamp': 1640995200000,
            'open': 50000.0,
            'high': 50500.0,
            'low': 49500.0,
            'close': 50250.0,
            'volume': 100.0
        }
        
        assert result == expected
    
    @pytest.mark.asyncio
    async def test_format_realtime_update_missing_field(self):
        """Test formatting fails with missing required fields."""
        incomplete_data = {
            'symbol': 'BTCUSDT',
            'timeframe': '1m',
            # Missing timestamp and price data
        }
        
        with pytest.raises(ValueError, match="Invalid candle data structure"):
            await self.chart_service.format_realtime_update(incomplete_data)
    
    @pytest.mark.asyncio
    async def test_prepare_websocket_message_valid(self):
        """Test preparing WebSocket message from raw exchange data."""
        raw_candle = [1640995200000, 50000.0, 50500.0, 49500.0, 50250.0, 100.0]
        
        result = await self.chart_service.prepare_websocket_message(
            'BTCUSDT', '1m', raw_candle
        )
        
        assert result is not None
        assert result['type'] == 'candle_update'
        assert result['symbol'] == 'BTCUSDT'
        assert result['timeframe'] == '1m'
        assert result['timestamp'] == 1640995200000
        assert result['open'] == 50000.0
        assert result['high'] == 50500.0
        assert result['low'] == 49500.0
        assert result['close'] == 50250.0
        assert result['volume'] == 100.0
    
    @pytest.mark.asyncio
    async def test_prepare_websocket_message_invalid_data(self):
        """Test preparing WebSocket message with invalid raw data."""
        invalid_raw_candle = [1640995200000, 50000.0, 49000.0, 51000.0, 50250.0, 100.0]  # Invalid OHLC
        
        result = await self.chart_service.prepare_websocket_message(
            'BTCUSDT', '1m', invalid_raw_candle
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_prepare_websocket_message_insufficient_data(self):
        """Test preparing WebSocket message with insufficient raw data."""
        insufficient_raw_candle = [1640995200000, 50000.0]  # Missing OHLCV data
        
        result = await self.chart_service.prepare_websocket_message(
            'BTCUSDT', '1m', insufficient_raw_candle
        )
        
        assert result is None
    
    @pytest.mark.asyncio 
    async def test_get_initial_chart_data_success(self):
        """Test successful retrieval of initial chart data."""
        # Mock the exchange service
        mock_exchange = AsyncMock()
        mock_exchange.fetch_ohlcv.return_value = [
            [1640995200000, 50000.0, 50500.0, 49500.0, 50250.0, 100.0],
            [1640995260000, 50250.0, 50750.0, 50000.0, 50500.0, 150.0],
        ]
        
        self.chart_service.exchange_service = AsyncMock()
        self.chart_service.exchange_service.get_exchange.return_value = mock_exchange
        
        result = await self.chart_service.get_initial_chart_data('BTC/USDT', '1m', 100)
        
        assert result['type'] == 'historical_candles'
        assert result['symbol'] == 'BTC/USDT'
        assert result['timeframe'] == '1m'
        assert result['count'] == 2
        assert len(result['data']) == 2
        
        # Check data format conversion
        first_candle = result['data'][0]
        assert first_candle['timestamp'] == 1640995200000
        assert first_candle['open'] == 50000.0
        assert first_candle['high'] == 50500.0
        assert first_candle['low'] == 49500.0
        assert first_candle['close'] == 50250.0
        assert first_candle['volume'] == 100.0
    
    @pytest.mark.asyncio
    async def test_get_initial_chart_data_no_data(self):
        """Test handling when no data is available."""
        # Mock the exchange service to return empty data
        mock_exchange = AsyncMock()
        mock_exchange.fetch_ohlcv.return_value = []
        
        self.chart_service.exchange_service = AsyncMock()
        self.chart_service.exchange_service.get_exchange.return_value = mock_exchange
        
        result = await self.chart_service.get_initial_chart_data('BTC/USDT', '1m', 100)
        
        assert result['type'] == 'historical_candles'
        assert result['symbol'] == 'BTC/USDT'
        assert result['timeframe'] == '1m'
        assert result['data'] == []
    
    @pytest.mark.asyncio
    async def test_get_initial_chart_data_exchange_error(self):
        """Test handling exchange service errors."""
        # Mock the exchange service to raise an error
        mock_exchange = AsyncMock()
        mock_exchange.fetch_ohlcv.side_effect = Exception("Exchange connection failed")
        
        self.chart_service.exchange_service = AsyncMock()
        self.chart_service.exchange_service.get_exchange.return_value = mock_exchange
        
        with pytest.raises(Exception, match="Failed to fetch chart data"):
            await self.chart_service.get_initial_chart_data('BTC/USDT', '1m', 100)

    def test_calculate_optimal_candle_count_normal_widths(self):
        """Test optimal candle count calculation for normal container widths."""
        # Test formula: min(max((containerWidth/6)*3, 200), 1000)
        
        # Small container
        assert self.chart_service.calculate_optimal_candle_count(400) == 200  # min threshold
        
        # Medium container
        assert self.chart_service.calculate_optimal_candle_count(800) == 400  # (800/6)*3 = 400
        
        # Large container
        assert self.chart_service.calculate_optimal_candle_count(1200) == 600  # (1200/6)*3 = 600
        
        # Very large container (hits max threshold)
        assert self.chart_service.calculate_optimal_candle_count(2400) == 1000  # max threshold

    def test_calculate_optimal_candle_count_edge_cases(self):
        """Test optimal candle count calculation for edge cases."""
        # Invalid inputs - should use default
        assert self.chart_service.calculate_optimal_candle_count(0) == 600  # default fallback
        assert self.chart_service.calculate_optimal_candle_count(-100) == 600  # default fallback
        assert self.chart_service.calculate_optimal_candle_count(None) == 600  # default fallback
        
        # Very small valid width
        assert self.chart_service.calculate_optimal_candle_count(300) == 200  # min threshold
        
        # Float input should work
        assert self.chart_service.calculate_optimal_candle_count(800.5) == 400  # rounded down

    @pytest.mark.asyncio
    async def test_format_realtime_update_with_time_field(self):
        """Test formatting real-time updates includes both timestamp and time fields."""
        candle_data = {
            'symbol': 'BTCUSDT',
            'timeframe': '1m',
            'timestamp': 1640995200000,  # milliseconds
            'open': 50000.0,
            'high': 50500.0,
            'low': 49500.0,
            'close': 50250.0,
            'volume': 100.0
        }
        
        result = await self.chart_service.format_realtime_update(candle_data)
        
        # Should include both timestamp (ms) and time (seconds)
        assert result['timestamp'] == 1640995200000
        assert result['time'] == 1640995200  # timestamp // 1000
        assert result['type'] == 'candle_update'

    @pytest.mark.asyncio 
    async def test_get_initial_chart_data_with_container_width(self):
        """Test initial chart data uses container width for optimal count calculation."""
        # Mock the exchange service
        mock_exchange = AsyncMock()
        mock_exchange.fetch_ohlcv.return_value = [
            [1640995200000, 50000.0, 50500.0, 49500.0, 50250.0, 100.0],
            [1640995260000, 50250.0, 50750.0, 50000.0, 50500.0, 150.0],
        ]
        
        self.chart_service.exchange_service = AsyncMock()
        self.chart_service.exchange_service.get_exchange.return_value = mock_exchange
        
        # Test with specific container width
        container_width = 1200  # Should result in limit of 600
        result = await self.chart_service.get_initial_chart_data('BTC/USDT', '1m', container_width)
        
        # Verify that exchange was called with calculated optimal count (600)
        mock_exchange.fetch_ohlcv.assert_called_once_with('BTC/USDT', '1m', limit=600)
        
        # Check that data includes both timestamp and time fields
        first_candle = result['data'][0]
        assert first_candle['timestamp'] == 1640995200000
        assert first_candle['time'] == 1640995200  # timestamp // 1000

    @pytest.mark.asyncio
    async def test_get_initial_chart_data_includes_symbol_data(self):
        """Test initial chart data includes symbolData with priceFormat."""
        # Mock the exchange service
        mock_exchange = AsyncMock()
        mock_exchange.fetch_ohlcv.return_value = [
            [1640995200000, 50000.0, 50500.0, 49500.0, 50250.0, 100.0],
        ]
        
        self.chart_service.exchange_service = AsyncMock()
        self.chart_service.exchange_service.get_exchange.return_value = mock_exchange
        
        # Mock symbol service to return symbol info with priceFormat
        from unittest.mock import patch
        with patch('app.services.chart_data_service.symbol_service') as mock_symbol_service:
            mock_symbol_service.get_symbol_info.return_value = {
                'priceFormat': {
                    'type': 'price',
                    'precision': 1,
                    'minMove': 0.1
                }
            }
            
            result = await self.chart_service.get_initial_chart_data('BTC/USDT', '1m', 800)
            
            # Check that symbolData is included
            assert 'symbolData' in result
            assert 'priceFormat' in result['symbolData']
            assert result['symbolData']['priceFormat']['precision'] == 1
            assert result['symbolData']['priceFormat']['minMove'] == 0.1