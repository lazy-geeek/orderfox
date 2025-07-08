"""
Trade Service for fetching and formatting trade data.

This service handles fetching recent trades from the exchange and formatting
them for display, including proper precision handling and timestamp formatting.
"""

import ccxt
import random
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import HTTPException

from app.services.exchange_service import exchange_service
from app.services.symbol_service import symbol_service
from app.services.formatting_service import formatting_service
from app.core.logging_config import get_logger

logger = get_logger("trade_service")


class TradeService:
    """Service for fetching and formatting trade data."""

    def __init__(self):
        pass

    async def fetch_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch recent trades for a symbol from the exchange.

        Args:
            symbol: Trading symbol in exchange format (e.g., 'BTC/USDT')
            limit: Maximum number of trades to fetch (default: 100)

        Returns:
            List of formatted trade dictionaries

        Raises:
            ValueError: If symbol is not found
            HTTPException: If network or exchange errors occur
        """
        logger.info(f"Fetching recent trades for {symbol} (limit: {limit})")

        # Validate symbol exists
        symbol_info = symbol_service.get_symbol_info(symbol)
        if not symbol_info:
            error_msg = f"Unknown symbol: {symbol}"
            logger.warning(error_msg)
            raise ValueError(error_msg)

        # Get exchange instance
        exchange = exchange_service.get_exchange()

        try:
            # Fetch trades from exchange
            logger.debug(f"Requesting trades from exchange for {symbol}")
            trades = exchange.fetch_trades(symbol, limit=limit)
            
            if not trades:
                logger.warning(f"No trades returned for {symbol}")
                return []

            # Format each trade
            formatted_trades = []
            for trade in trades:
                try:
                    formatted_trade = self.format_trade(trade, symbol_info)
                    formatted_trades.append(formatted_trade)
                except Exception as e:
                    logger.warning(f"Failed to format trade {trade.get('id', 'unknown')}: {e}")
                    continue

            # Return most recent trades first (newest at top)
            # Limit to requested number of trades
            result = formatted_trades[-limit:][::-1]
            logger.info(f"Successfully fetched and formatted {len(result)} trades for {symbol}")
            return result

        except ccxt.NetworkError as e:
            error_msg = f"Network error fetching trades for {symbol}: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=503, detail="Network error")
        except ccxt.ExchangeError as e:
            error_msg = f"Exchange error fetching trades for {symbol}: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=502, detail="Exchange API error")
        except Exception as e:
            error_msg = f"Unexpected error fetching trades for {symbol}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to fetch trades")

    def format_trade(self, trade: Dict[str, Any], symbol_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a single trade with proper precision and timestamps.

        Args:
            trade: Raw trade data from CCXT
            symbol_info: Symbol information with precision data

        Returns:
            Formatted trade dictionary

        Raises:
            ValueError: If trade data is invalid
        """
        try:
            # Validate required trade fields
            required_fields = ['id', 'price', 'amount', 'side', 'timestamp']
            for field in required_fields:
                if field not in trade or trade[field] is None:
                    raise ValueError(f"Missing required field: {field}")

            # Extract precision from symbol info
            price_precision = symbol_info.get('pricePrecision', 2)
            amount_precision = symbol_info.get('amountPrecision', 8)

            # Format price and amount using the formatting service
            price_formatted = formatting_service.format_price(
                trade['price'], 
                symbol_info
            )
            amount_formatted = formatting_service.format_amount(
                trade['amount'],
                symbol_info
            )

            # Format time as HH:MM:SS (local time)
            try:
                dt = datetime.fromtimestamp(trade['timestamp'] / 1000)
                time_formatted = dt.strftime('%H:%M:%S')
            except (ValueError, OSError) as e:
                logger.warning(f"Invalid timestamp {trade['timestamp']}: {e}")
                time_formatted = "Invalid"

            # Validate side value
            side = trade['side']
            if side not in ['buy', 'sell']:
                logger.warning(f"Invalid trade side '{side}', defaulting to 'buy'")
                side = 'buy'

            return {
                'id': str(trade['id']),
                'price': float(trade['price']),
                'amount': float(trade['amount']),
                'side': side,
                'timestamp': int(trade['timestamp']),
                'price_formatted': price_formatted,
                'amount_formatted': amount_formatted,
                'time_formatted': time_formatted
            }

        except (KeyError, TypeError, ValueError) as e:
            error_msg = f"Error formatting trade: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def generate_mock_trades(self, symbol: str, count: int = 100) -> List[Dict[str, Any]]:
        """
        Generate mock trade data for testing and demo purposes.

        Args:
            symbol: Trading symbol
            count: Number of mock trades to generate

        Returns:
            List of mock trade dictionaries
        """
        logger.info(f"Generating {count} mock trades for {symbol}")
        
        # Get symbol info for proper formatting
        symbol_info = symbol_service.get_symbol_info(symbol)
        if not symbol_info:
            # Fallback symbol info for mock data
            symbol_info = {
                'pricePrecision': 2,
                'amountPrecision': 8,
                'base_asset': 'BTC',
                'quote_asset': 'USDT'
            }

        base_price = 50000.0  # Base price for mock data
        current_time = int(time.time() * 1000)
        trades = []

        for i in range(count):
            # Generate realistic price variation
            price_variation = random.uniform(-0.01, 0.01)  # ±1% variation
            price = base_price * (1 + price_variation)
            
            # Generate realistic amount
            amount = random.uniform(0.001, 5.0)
            
            # Random side
            side = random.choice(['buy', 'sell'])
            
            # Create mock trade with decreasing timestamps (older trades first)
            trade_time = current_time - (i * random.randint(1000, 10000))  # 1-10 seconds apart
            
            mock_trade = {
                'id': f"mock_{i}_{trade_time}",
                'price': price,
                'amount': amount,
                'side': side,
                'timestamp': trade_time
            }

            # Format the mock trade
            try:
                formatted_trade = self.format_trade(mock_trade, symbol_info)
                trades.append(formatted_trade)
            except Exception as e:
                logger.warning(f"Failed to format mock trade {i}: {e}")
                continue

        # Return in reverse order (newest first)
        return trades[::-1]

    async def fetch_trades_with_fallback(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch trades with automatic fallback to mock data if exchange fails.

        Args:
            symbol: Trading symbol
            limit: Maximum number of trades to fetch

        Returns:
            List of trade dictionaries (real or mock)
        """
        try:
            # Try to fetch real trades first
            return await self.fetch_recent_trades(symbol, limit)
        except Exception as e:
            logger.warning(f"Failed to fetch real trades for {symbol}: {e}")
            logger.info(f"Falling back to mock trade data for {symbol}")
            
            # Generate mock trades as fallback
            return self.generate_mock_trades(symbol, limit)


# Global trade service instance
trade_service = TradeService()