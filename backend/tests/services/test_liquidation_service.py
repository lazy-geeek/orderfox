"""
Tests for LiquidationService

Comprehensive tests for the liquidation service including WebSocket connections,
data formatting, error handling, and reconnection logic.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from app.services.liquidation_service import liquidation_service

class TestLiquidationService:
    """Test suite for LiquidationService"""
    
    def test_liquidation_service_initialization(self):
        """Test that liquidation service initializes correctly"""
        assert liquidation_service.base_url == "wss://fstream.binance.com"
        assert isinstance(liquidation_service.active_connections, dict)
        assert isinstance(liquidation_service.data_callbacks, dict)
        assert isinstance(liquidation_service.running_streams, dict)
        assert liquidation_service.retry_delays == [1, 2, 5, 10, 30]
    
    @pytest.mark.asyncio
    async def test_connect_to_liquidation_stream(self):
        """Test WebSocket connection to liquidation stream"""
        callback = AsyncMock()
        symbol_info = {'symbol': 'BTCUSDT', 'baseAsset': 'BTC'}
        
        with patch('websockets.connect') as mock_connect:
            mock_ws = AsyncMock()
            mock_connect.return_value.__aenter__.return_value = mock_ws
            
            # Start connection with symbol info
            await liquidation_service.connect_to_liquidation_stream("BTCUSDT", callback, symbol_info)
            
            # Verify connection attempt
            assert "BTCUSDT" in liquidation_service.active_connections
            assert "BTCUSDT" in liquidation_service.data_callbacks
            assert liquidation_service.running_streams.get("BTCUSDT") is True
            assert liquidation_service.symbol_info_cache.get("BTCUSDT") == symbol_info
    
    def test_format_liquidation_data(self):
        """Test liquidation data formatting"""
        raw_data = {
            "e": "forceOrder",
            "E": 1568014460893,
            "o": {
                "s": "BTCUSDT",
                "S": "SELL",
                "q": "0.014",
                "ap": "9910",
                "z": "0.014"
            }
        }
        
        formatted = liquidation_service.format_liquidation_data(raw_data, "BTCUSDT")
        
        assert formatted["symbol"] == "BTCUSDT"
        assert formatted["side"] == "SELL"
        assert formatted["quantity"] == "0.014"
        assert formatted["priceUsdt"] == "138.740"
        assert "displayTime" in formatted
        assert "quantityFormatted" in formatted
        assert "priceUsdtFormatted" in formatted
        assert "avgPrice" in formatted
        assert formatted["baseAsset"] == ""  # No symbol_info provided
    
    def test_format_liquidation_data_edge_cases(self):
        """Test liquidation data formatting edge cases"""
        # Test with missing data
        raw_data = {
            "e": "forceOrder",
            "E": 1568014460893,
            "o": {}
        }
        
        formatted = liquidation_service.format_liquidation_data(raw_data, "BTCUSDT")
        
        assert formatted["symbol"] == "BTCUSDT"
        assert formatted["side"] == "UNKNOWN"
        assert formatted["quantity"] == "0"
        assert formatted["priceUsdt"] == "0"

    def test_format_large_numbers(self):
        """Test formatting of large numbers"""
        raw_data = {
            "e": "forceOrder", 
            "E": 1568014460893,
            "o": {
                "s": "BTCUSDT",
                "S": "BUY",
                "q": "100",
                "ap": "50000",
                "z": "100"
            }
        }
        
        formatted = liquidation_service.format_liquidation_data(raw_data, "BTCUSDT")
        
        assert formatted["priceUsdtFormatted"] == "5,000,000"  # Whole number with commas
        assert formatted["quantityFormatted"] == "100.000"

    def test_format_small_numbers(self):
        """Test formatting of small numbers"""
        raw_data = {
            "e": "forceOrder",
            "E": 1568014460893, 
            "o": {
                "s": "BTCUSDT",
                "S": "SELL",
                "q": "0.000001",
                "ap": "50000",
                "z": "0.000001"
            }
        }
        
        formatted = liquidation_service.format_liquidation_data(raw_data, "BTCUSDT")
        
        assert formatted["quantityFormatted"] == "0.000001"
        assert formatted["priceUsdtFormatted"] == "0"  # Very small, rounds to 0
    
    @pytest.mark.asyncio 
    async def test_liquidation_callback(self):
        """Test liquidation callback handling"""
        callback = AsyncMock()
        test_data = {"symbol": "BTCUSDT", "side": "BUY"}
        
        # Register callback first
        liquidation_service.data_callbacks["BTCUSDT"] = [callback]
        
        await liquidation_service._notify_callbacks("BTCUSDT", test_data)
        
        callback.assert_called_once_with(test_data)
    
    @pytest.mark.asyncio
    async def test_disconnect_stream(self):
        """Test disconnection from liquidation stream"""
        # Create a real asyncio Task that we can cancel
        import asyncio
        
        async def dummy_task():
            await asyncio.sleep(10)  # Long-running task
            
        task = asyncio.create_task(dummy_task())
        
        liquidation_service.running_streams["BTCUSDT"] = True
        liquidation_service.active_connections["BTCUSDT"] = task
        liquidation_service.data_callbacks["BTCUSDT"] = []
        liquidation_service.symbol_info_cache["BTCUSDT"] = {'symbol': 'BTCUSDT', 'baseAsset': 'BTC'}
        
        await liquidation_service.disconnect_stream("BTCUSDT")
        
        assert liquidation_service.running_streams.get("BTCUSDT") == False
        assert "BTCUSDT" not in liquidation_service.active_connections
        assert "BTCUSDT" not in liquidation_service.data_callbacks
        assert "BTCUSDT" not in liquidation_service.symbol_info_cache
        assert task.cancelled()

    @pytest.mark.asyncio
    async def test_disconnect_all(self):
        """Test disconnecting all active streams"""
        # Create real asyncio Tasks
        import asyncio
        
        async def dummy_task():
            await asyncio.sleep(10)  # Long-running task
            
        task1 = asyncio.create_task(dummy_task())
        task2 = asyncio.create_task(dummy_task())
        
        liquidation_service.active_connections["BTCUSDT"] = task1
        liquidation_service.active_connections["ETHUSDT"] = task2
        liquidation_service.running_streams["BTCUSDT"] = True
        liquidation_service.running_streams["ETHUSDT"] = True
        
        await liquidation_service.disconnect_all()
        
        assert len(liquidation_service.active_connections) == 0
        assert task1.cancelled()
        assert task2.cancelled()
    
    def test_format_liquidation_data_with_symbol_info(self):
        """Test liquidation data formatting with symbol info for BTC"""
        raw_data = {
            "e": "forceOrder",
            "E": 1568014460893,
            "o": {
                "s": "BTCUSDT",
                "S": "SELL",
                "q": "0.014",
                "ap": "9910",
                "z": "0.014"
            }
        }
        
        # Mock symbol info for BTC (low precision)
        symbol_info = {
            'symbol': 'BTCUSDT',
            'baseAsset': 'BTC',
            'pricePrecision': 1,
            'amountPrecision': 3
        }
        
        formatted = liquidation_service.format_liquidation_data(raw_data, "BTCUSDT", symbol_info)
        
        assert formatted["symbol"] == "BTCUSDT"
        assert formatted["side"] == "SELL"
        assert formatted["priceUsdtFormatted"] == "139"  # Rounded to whole number (no comma needed for 3 digits)
        assert formatted["baseAsset"] == "BTC"
        # Note: quantityFormatted will use formatting_service which is tested separately
    
    def test_format_liquidation_data_with_comma_formatting(self):
        """Test that prices over 1000 have comma formatting"""
        raw_data = {
            "e": "forceOrder",
            "E": 1568014460893,
            "o": {
                "s": "BTCUSDT",
                "S": "SELL",
                "q": "0.5",
                "ap": "45678.90",
                "z": "0.5"
            }
        }
        
        formatted = liquidation_service.format_liquidation_data(raw_data, "BTCUSDT")
        
        # 0.5 * 45678.90 = 22839.45, rounds to 22,839
        assert formatted["priceUsdtFormatted"] == "22,839"
    
    def test_format_liquidation_data_with_altcoin_symbol_info(self):
        """Test liquidation data formatting with symbol info for altcoin"""
        raw_data = {
            "e": "forceOrder",
            "E": 1568014460893,
            "o": {
                "s": "SOLUSDT",
                "S": "BUY",
                "q": "0.123456",
                "ap": "150.50",
                "z": "0.123456"
            }
        }
        
        # Mock symbol info for SOL (high precision)
        symbol_info = {
            'symbol': 'SOLUSDT',
            'baseAsset': 'SOL',
            'pricePrecision': 2,
            'amountPrecision': 6
        }
        
        formatted = liquidation_service.format_liquidation_data(raw_data, "SOLUSDT", symbol_info)
        
        assert formatted["symbol"] == "SOLUSDT"
        assert formatted["side"] == "BUY"
        assert formatted["priceUsdtFormatted"] == "19"  # Rounded to whole number (no comma needed for 2 digits)
        assert formatted["baseAsset"] == "SOL"
    
    def test_format_liquidation_data_without_symbol_info(self):
        """Test liquidation data formatting without symbol info (fallback)"""
        raw_data = {
            "e": "forceOrder",
            "E": 1568014460893,
            "o": {
                "s": "XRPUSDT",
                "S": "SELL",
                "q": "0.000001",
                "ap": "0.5",
                "z": "0.000001"
            }
        }
        
        formatted = liquidation_service.format_liquidation_data(raw_data, "XRPUSDT", None)
        
        assert formatted["quantityFormatted"] == "0.000001"  # Fallback formatting
        assert formatted["priceUsdtFormatted"] == "0"  # Very small, rounds to 0
        assert formatted["baseAsset"] == ""
    
    def test_format_liquidation_data_edge_cases_with_symbol_info(self):
        """Test formatting edge cases with symbol info"""
        # Test with very small quantities
        raw_data = {
            "e": "forceOrder",
            "E": 1568014460893,
            "o": {
                "s": "BTCUSDT",
                "S": "SELL",
                "q": "0.000000001",
                "ap": "50000",
                "z": "0.000000001"
            }
        }
        
        symbol_info = {
            'symbol': 'BTCUSDT',
            'baseAsset': 'BTC',
            'pricePrecision': 1,
            'amountPrecision': 8
        }
        
        formatted = liquidation_service.format_liquidation_data(raw_data, "BTCUSDT", symbol_info)
        
        assert formatted["priceUsdtFormatted"] == "0"  # Very small, rounds to 0
        
        # Test with very large quantities
        raw_data = {
            "e": "forceOrder",
            "E": 1568014460893,
            "o": {
                "s": "BTCUSDT",
                "S": "BUY",
                "q": "1000000",
                "ap": "50000",
                "z": "1000000"
            }
        }
        
        formatted = liquidation_service.format_liquidation_data(raw_data, "BTCUSDT", symbol_info)
        
        assert formatted["priceUsdtFormatted"] == "50,000,000,000"  # Very large number with commas