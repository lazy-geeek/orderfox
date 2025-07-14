"""
Chart data service for processing and formatting candlestick data.

This service follows the orderbook aggregation service pattern to provide
optimized data handling for Lightweight Charts frontend integration.
"""

import logging
from typing import Dict, List, Any, Optional
from app.services.exchange_service import exchange_service

logger = logging.getLogger(__name__)


class ChartDataService:
    """
    Service for handling chart data processing and formatting.

    Provides optimized data structures for Lightweight Charts frontend
    with initial historical data + real-time update patterns.
    """

    def __init__(self):
        """Initialize the chart data service."""
        self.exchange_service = exchange_service
        # Cache for storing time ranges of candle data by symbol:timeframe
        self.time_range_cache = {}

    def calculate_optimal_candle_count(self, container_width: int) -> int:
        """
        Calculate optimal number of candles based on container width.
        
        This replaces the frontend getOptimalCandleCount function to ensure
        consistent calculation and reduce frontend processing.
        
        Args:
            container_width: Container width in pixels
            
        Returns:
            Optimal number of candles (between 200 and 1000)
        """
        try:
            # Validate container width
            if not isinstance(container_width, (int, float)) or container_width <= 0:
                logger.warning(f"Invalid container width: {container_width}, using default")
                container_width = 800  # Default fallback
            
            # Original frontend logic: Math.min(Math.max((containerWidth/6)*3, 200), 1000)
            # This ensures good chart density while maintaining performance
            base_calculation = (container_width / 6) * 3
            optimal_count = min(max(base_calculation, 200), 1000)
            
            # Ensure we return an integer
            optimal_count = int(optimal_count)
            
            logger.debug(f"Container width: {container_width}px -> Optimal candle count: {optimal_count}")
            
            return optimal_count
            
        except Exception as e:
            logger.error(f"Error calculating optimal candle count: {e}")
            return 600  # Safe default

    async def get_initial_chart_data(
        self,
        symbol: str,
        timeframe: str,
        container_width: int = 800
    ) -> Dict[str, Any]:
        """
        Get initial historical data optimized for Lightweight Charts.

        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for candles (e.g., '1m', '5m', '1h', '1d')
            container_width: Container width in pixels for optimal candle count calculation

        Returns:
            Dict containing historical candles data with metadata

        Raises:
            Exception: If data fetching fails
        """
        try:
            # Calculate optimal candle count from container width
            limit = self.calculate_optimal_candle_count(container_width)
            
            logger.info(
                f"Fetching initial chart data for {symbol} {timeframe}, limit={limit} (container_width={container_width}px)")

            # Fetch from exchange service
            exchange = self.exchange_service.get_exchange()
            raw_data = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

            if not raw_data:
                logger.warning(f"No data received for {symbol} {timeframe}")
                return {
                    'type': 'historical_candles',
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'data': []
                }

            # Convert to standardized format with BOTH timestamp fields
            formatted_data = []
            for candle in raw_data:
                timestamp_ms = int(candle[0])
                formatted_candle = {
                    # Backend processing and consistency
                    'timestamp': timestamp_ms,
                    # TradingView Lightweight Charts requirement (seconds)
                    'time': timestamp_ms // 1000,
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': float(candle[5]) if len(candle) > 5 else 0.0
                }
                formatted_data.append(formatted_candle)

            # Sort by timestamp to ensure proper ordering
            formatted_data.sort(key=lambda x: x['timestamp'])

            # Get symbol info for priceFormat
            from app.services.symbol_service import symbol_service
            symbol_info = symbol_service.get_symbol_info(symbol)
            
            # Get the actual time range from the data
            time_range = None
            if formatted_data:
                time_range = {
                    'start_ms': formatted_data[0]['timestamp'],
                    'end_ms': formatted_data[-1]['timestamp'],
                    'start': formatted_data[0]['time'],
                    'end': formatted_data[-1]['time']
                }
                
                # Store in cache for coordination with liquidation service
                cache_key = f"{symbol}:{timeframe}"
                self.time_range_cache[cache_key] = time_range
                logger.info(f"Cached time range for {cache_key}: {time_range['start_ms']} to {time_range['end_ms']}")
            
            # Prepare the response with symbol data including priceFormat
            response = {
                'type': 'historical_candles',
                'symbol': symbol,
                'timeframe': timeframe,
                'data': formatted_data,
                'count': len(formatted_data),
                'time_range': time_range
            }
            
            # Add symbol data if available
            if symbol_info and symbol_info.get('priceFormat'):
                response['symbolData'] = {
                    'priceFormat': symbol_info['priceFormat']
                }

            logger.info(
                f"Successfully formatted {
                    len(formatted_data)} candles for {symbol} {timeframe}")

            return response

        except Exception as e:
            logger.error(
                f"Error fetching initial chart data for {symbol} {timeframe}: {
                    str(e)}")
            raise Exception(f"Failed to fetch chart data: {str(e)}")

    async def format_realtime_update(
            self, candle_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format real-time candle update for WebSocket transmission.

        Args:
            candle_data: Raw candle data dictionary

        Returns:
            Formatted candle update message
        """
        try:
            timestamp_ms = candle_data['timestamp']
            return {
                'type': 'candle_update',
                'symbol': candle_data['symbol'],
                'timeframe': candle_data['timeframe'],
                # Backend processing and consistency
                'timestamp': timestamp_ms,
                # TradingView Lightweight Charts requirement (seconds)
                'time': timestamp_ms // 1000,
                'open': candle_data['open'],
                'high': candle_data['high'],
                'low': candle_data['low'],
                'close': candle_data['close'],
                'volume': candle_data['volume']
            }
        except KeyError as e:
            logger.error(f"Missing required field in candle data: {e}")
            raise ValueError(f"Invalid candle data structure: missing {e}")

    def validate_candle_data(self, candle_data: Dict[str, Any]) -> bool:
        """
        Validate candle data structure and values.

        Args:
            candle_data: Candle data to validate

        Returns:
            True if valid, False otherwise
        """
        required_fields = [
            'timestamp',
            'open',
            'high',
            'low',
            'close',
            'volume']

        try:
            # Check all required fields exist
            for field in required_fields:
                if field not in candle_data:
                    logger.warning(f"Missing required field: {field}")
                    return False

            # Validate data types and ranges
            timestamp = candle_data['timestamp']
            if not isinstance(timestamp, (int, float)) or timestamp <= 0:
                logger.warning(f"Invalid timestamp: {timestamp}")
                return False

            for price_field in ['open', 'high', 'low', 'close']:
                price = candle_data[price_field]
                if not isinstance(price, (int, float)) or price <= 0:
                    logger.warning(f"Invalid {price_field}: {price}")
                    return False

            volume = candle_data['volume']
            if not isinstance(volume, (int, float)) or volume < 0:
                logger.warning(f"Invalid volume: {volume}")
                return False

            # Validate OHLC relationships
            open_price = candle_data['open']
            high_price = candle_data['high']
            low_price = candle_data['low']
            close_price = candle_data['close']

            if not (low_price <= open_price <= high_price
                    and low_price <= close_price <= high_price):
                logger.warning(
                    f"Invalid OHLC relationships: O={open_price}, H={high_price}, L={low_price}, C={close_price}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating candle data: {e}")
            return False

    async def prepare_websocket_message(
        self,
        symbol: str,
        timeframe: str,
        raw_candle: List[Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Prepare a WebSocket message from raw exchange candle data.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            raw_candle: Raw OHLCV data from exchange

        Returns:
            Formatted WebSocket message or None if invalid
        """
        try:
            if not raw_candle or len(raw_candle) < 6:
                logger.warning(
                    f"Invalid raw candle data for {symbol}: {raw_candle}")
                return None

            candle_data = {
                'symbol': symbol,
                'timeframe': timeframe,
                'timestamp': int(raw_candle[0]),
                'open': float(raw_candle[1]),
                'high': float(raw_candle[2]),
                'low': float(raw_candle[3]),
                'close': float(raw_candle[4]),
                'volume': float(raw_candle[5])
            }

            # Validate the data
            if not self.validate_candle_data(candle_data):
                return None

            # Format for WebSocket
            return await self.format_realtime_update(candle_data)

        except Exception as e:
            logger.error(
                f"Error preparing WebSocket message for {symbol}: {e}")
            return None


# Global instance
chart_data_service = ChartDataService()
