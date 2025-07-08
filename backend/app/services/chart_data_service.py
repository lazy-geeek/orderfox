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

    async def get_initial_chart_data(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get initial historical data optimized for Lightweight Charts.

        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for candles (e.g., '1m', '5m', '1h', '1d')
            limit: Number of historical candles to fetch

        Returns:
            Dict containing historical candles data with metadata

        Raises:
            Exception: If data fetching fails
        """
        try:
            logger.info(
                f"Fetching initial chart data for {symbol} {timeframe}, limit={limit}")

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

            # Convert to standardized format
            formatted_data = []
            for candle in raw_data:
                formatted_candle = {
                    # Keep milliseconds for backend consistency
                    'timestamp': int(candle[0]),
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': float(candle[5]) if len(candle) > 5 else 0.0
                }
                formatted_data.append(formatted_candle)

            # Sort by timestamp to ensure proper ordering
            formatted_data.sort(key=lambda x: x['timestamp'])

            logger.info(
                f"Successfully formatted {
                    len(formatted_data)} candles for {symbol} {timeframe}")

            return {
                'type': 'historical_candles',
                'symbol': symbol,
                'timeframe': timeframe,
                'data': formatted_data,
                'count': len(formatted_data)
            }

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
            return {
                'type': 'candle_update',
                'symbol': candle_data['symbol'],
                'timeframe': candle_data['timeframe'],
                'timestamp': candle_data['timestamp'],
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
