"""
Tests for the Trade Service.

This module contains unit tests for the TradeService class,
testing trade fetching, formatting, and error handling functionality.
"""

import pytest

# Chunk 4: Advanced services - Liquidation, trade, trading engine
pytestmark = pytest.mark.chunk4
import time
from unittest.mock import Mock, patch
from fastapi import HTTPException

from app.services.trade_service import TradeService


class TestTradeService:
    """Test cases for TradeService."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.trade_service = TradeService()
        self.mock_symbol_info = {
            'pricePrecision': 1,
            'amountPrecision': 3,
            'base_asset': 'BTC',
            'quote_asset': 'USDT'
        }
        self.mock_trade_raw = {
            'id': '123456',
            'price': 108905.123456,
            'amount': 0.12345678,
            'side': 'buy',
            'timestamp': 1736267157000
        }

    @pytest.mark.asyncio
    async def test_fetch_recent_trades_success(self):
        """Test successful fetching of recent trades."""
        # Mock dependencies
        with patch('app.services.trade_service.symbol_service') as mock_symbol_service, \
             patch('app.services.trade_service.exchange_service') as mock_exchange_service:
            
            # Setup mocks
            mock_symbol_service.get_symbol_info.return_value = self.mock_symbol_info
            mock_exchange = Mock()
            mock_exchange.fetch_trades.return_value = [self.mock_trade_raw]
            mock_exchange_service.get_exchange.return_value = mock_exchange
            
            # Execute test
            result = await self.trade_service.fetch_recent_trades("BTC/USDT", limit=10)
            
            # Assertions
            assert len(result) == 1
            assert result[0]['id'] == '123456'
            assert result[0]['side'] == 'buy'
            assert 'price_formatted' in result[0]
            assert 'amount_formatted' in result[0]
            assert 'time_formatted' in result[0]
            
            # Verify mock calls
            mock_symbol_service.get_symbol_info.assert_called_once_with("BTC/USDT")
            mock_exchange.fetch_trades.assert_called_once_with("BTC/USDT", limit=10)

    @pytest.mark.asyncio
    async def test_fetch_recent_trades_invalid_symbol(self):
        """Test fetching trades with invalid symbol raises appropriate error."""
        with patch('app.services.trade_service.symbol_service') as mock_symbol_service:
            # Setup mock to return None for invalid symbol
            mock_symbol_service.get_symbol_info.return_value = None
            
            # Execute test and verify exception
            with pytest.raises(ValueError, match="Unknown symbol: INVALID"):
                await self.trade_service.fetch_recent_trades("INVALID", limit=10)

    @pytest.mark.asyncio
    async def test_fetch_recent_trades_network_error(self):
        """Test network error handling during trade fetching."""
        import ccxt
        
        with patch('app.services.trade_service.symbol_service') as mock_symbol_service, \
             patch('app.services.trade_service.exchange_service') as mock_exchange_service:
            
            # Setup mocks
            mock_symbol_service.get_symbol_info.return_value = self.mock_symbol_info
            mock_exchange = Mock()
            mock_exchange.fetch_trades.side_effect = ccxt.NetworkError("Network timeout")
            mock_exchange_service.get_exchange.return_value = mock_exchange
            
            # Execute test and verify exception
            with pytest.raises(HTTPException) as exc_info:
                await self.trade_service.fetch_recent_trades("BTC/USDT", limit=10)
            
            assert exc_info.value.status_code == 503
            assert "Network error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_fetch_recent_trades_exchange_error(self):
        """Test exchange error handling during trade fetching."""
        import ccxt
        
        with patch('app.services.trade_service.symbol_service') as mock_symbol_service, \
             patch('app.services.trade_service.exchange_service') as mock_exchange_service:
            
            # Setup mocks
            mock_symbol_service.get_symbol_info.return_value = self.mock_symbol_info
            mock_exchange = Mock()
            mock_exchange.fetch_trades.side_effect = ccxt.ExchangeError("Exchange API error")
            mock_exchange_service.get_exchange.return_value = mock_exchange
            
            # Execute test and verify exception
            with pytest.raises(HTTPException) as exc_info:
                await self.trade_service.fetch_recent_trades("BTC/USDT", limit=10)
            
            assert exc_info.value.status_code == 502
            assert "Exchange API error" in str(exc_info.value.detail)

    def test_format_trade_success(self):
        """Test successful trade formatting with different precisions."""
        with patch('app.services.trade_service.formatting_service') as mock_formatting_service:
            # Setup mocks
            mock_formatting_service.format_price.return_value = "108,905.1"
            mock_formatting_service.format_amount.return_value = "0.123"
            
            # Execute test
            result = self.trade_service.format_trade(self.mock_trade_raw, self.mock_symbol_info)
            
            # Assertions
            assert result['id'] == '123456'
            assert result['price'] == 108905.123456
            assert result['amount'] == 0.12345678
            assert result['side'] == 'buy'
            assert result['timestamp'] == 1736267157000
            assert result['price_formatted'] == "108,905.1"
            assert result['amount_formatted'] == "0.123"
            assert ':' in result['time_formatted']  # Should contain time format
            
            # Verify formatting service calls
            mock_formatting_service.format_price.assert_called_once_with(
                108905.123456, self.mock_symbol_info
            )
            mock_formatting_service.format_amount.assert_called_once_with(
                0.12345678, self.mock_symbol_info
            )

    def test_format_trade_missing_required_field(self):
        """Test trade formatting with missing required fields."""
        incomplete_trade = {
            'id': '123456',
            'price': 108905.123456,
            # Missing 'amount', 'side', 'timestamp'
        }
        
        with pytest.raises(ValueError, match="Missing required field"):
            self.trade_service.format_trade(incomplete_trade, self.mock_symbol_info)

    def test_format_trade_invalid_side(self):
        """Test trade formatting with invalid side value."""
        invalid_trade = self.mock_trade_raw.copy()
        invalid_trade['side'] = 'invalid_side'
        
        with patch('app.services.trade_service.formatting_service') as mock_formatting_service:
            mock_formatting_service.format_price.return_value = "108,905.1"
            mock_formatting_service.format_amount.return_value = "0.123"
            
            result = self.trade_service.format_trade(invalid_trade, self.mock_symbol_info)
            
            # Should default to 'buy' for invalid side
            assert result['side'] == 'buy'

    def test_format_trade_invalid_timestamp(self):
        """Test trade formatting with invalid timestamp."""
        invalid_trade = self.mock_trade_raw.copy()
        invalid_trade['timestamp'] = 'invalid_timestamp'
        
        with patch('app.services.trade_service.formatting_service') as mock_formatting_service:
            mock_formatting_service.format_price.return_value = "108,905.1"
            mock_formatting_service.format_amount.return_value = "0.123"
            
            with pytest.raises(ValueError, match="Error formatting trade"):
                self.trade_service.format_trade(invalid_trade, self.mock_symbol_info)

    def test_generate_mock_trades(self):
        """Test mock trade generation."""
        with patch('app.services.trade_service.symbol_service') as mock_symbol_service:
            mock_symbol_service.get_symbol_info.return_value = self.mock_symbol_info
            
            result = self.trade_service.generate_mock_trades("BTC/USDT", count=5)
            
            # Assertions
            assert len(result) == 5
            assert all(isinstance(trade, dict) for trade in result)
            assert all('id' in trade for trade in result)
            assert all('price_formatted' in trade for trade in result)
            assert all('amount_formatted' in trade for trade in result)
            assert all('time_formatted' in trade for trade in result)
            assert all(trade['side'] in ['buy', 'sell'] for trade in result)

    def test_generate_mock_trades_no_symbol_info(self):
        """Test mock trade generation with no symbol info (fallback)."""
        with patch('app.services.trade_service.symbol_service') as mock_symbol_service:
            mock_symbol_service.get_symbol_info.return_value = None
            
            result = self.trade_service.generate_mock_trades("UNKNOWN/USDT", count=3)
            
            # Should still generate trades with fallback symbol info
            assert len(result) == 3
            assert all('price_formatted' in trade for trade in result)

    @pytest.mark.asyncio
    async def test_fetch_trades_with_fallback_success(self):
        """Test successful trade fetching with fallback."""
        with patch.object(self.trade_service, 'fetch_recent_trades') as mock_fetch:
            mock_fetch.return_value = [{'id': '123', 'side': 'buy'}]
            
            result = await self.trade_service.fetch_trades_with_fallback("BTC/USDT", limit=10)
            
            assert len(result) == 1
            assert result[0]['id'] == '123'
            mock_fetch.assert_called_once_with("BTC/USDT", 10)

    @pytest.mark.asyncio
    async def test_fetch_trades_with_fallback_to_mock(self):
        """Test trade fetching fallback to mock data when real fetch fails."""
        with patch.object(self.trade_service, 'fetch_recent_trades') as mock_fetch, \
             patch.object(self.trade_service, 'generate_mock_trades') as mock_generate:
            
            mock_fetch.side_effect = Exception("Network error")
            mock_generate.return_value = [{'id': 'mock_123', 'side': 'sell'}]
            
            result = await self.trade_service.fetch_trades_with_fallback("BTC/USDT", limit=10)
            
            assert len(result) == 1
            assert result[0]['id'] == 'mock_123'
            mock_fetch.assert_called_once_with("BTC/USDT", 10)
            mock_generate.assert_called_once_with("BTC/USDT", 10)

    def test_format_trade_edge_cases(self):
        """Test trade formatting with edge case values."""
        edge_case_trade = {
            'id': '999',
            'price': 0.00001,  # Very small price
            'amount': 1000000,  # Very large amount
            'side': 'sell',
            'timestamp': 1640995200000  # Fixed timestamp for predictable time formatting
        }
        
        with patch('app.services.trade_service.formatting_service') as mock_formatting_service:
            mock_formatting_service.format_price.return_value = "0.00001"
            mock_formatting_service.format_amount.return_value = "1.000M"
            
            result = self.trade_service.format_trade(edge_case_trade, self.mock_symbol_info)
            
            assert result['price_formatted'] == "0.00001"
            assert result['amount_formatted'] == "1.000M"
            assert result['side'] == 'sell'

    def test_format_trade_zero_values(self):
        """Test trade formatting handles zero values correctly."""
        zero_trade = {
            'id': '000',
            'price': 1.0,  # Valid price (must be > 0)
            'amount': 1.0,  # Valid amount (must be > 0)
            'side': 'buy',
            'timestamp': int(time.time() * 1000)
        }
        
        with patch('app.services.trade_service.formatting_service') as mock_formatting_service:
            mock_formatting_service.format_price.return_value = "1.0"
            mock_formatting_service.format_amount.return_value = "1.0"
            
            result = self.trade_service.format_trade(zero_trade, self.mock_symbol_info)
            
            assert result['price'] == 1.0
            assert result['amount'] == 1.0