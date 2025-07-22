"""
Unit tests for the Symbol Service.

Tests symbol format conversion, validation, and suggestion functionality.
"""

import pytest

# Chunk 2: Core services - Symbol, exchange, formatting, caching
pytestmark = pytest.mark.chunk2
import time
from unittest.mock import Mock, patch
from app.services.symbol_service import SymbolService


class TestSymbolService:
    """Test cases for SymbolService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.symbol_service = SymbolService()

        # Mock exchange markets data
        self.mock_markets = {
            "BTC/USDT": {
                "id": "BTCUSDT",
                "symbol": "BTC/USDT",
                "base": "BTC",
                "quote": "USDT",
                "active": True,
                "type": "swap",
                "spot": False,
            },
            "ETH/USDT": {
                "id": "ETHUSDT",
                "symbol": "ETH/USDT",
                "base": "ETH",
                "quote": "USDT",
                "active": True,
                "type": "swap",
                "spot": False,
            },
            "ADA/USDT": {
                "id": "ADAUSDT",
                "symbol": "ADA/USDT",
                "base": "ADA",
                "quote": "USDT",
                "active": True,
                "type": "swap",
                "spot": False,
            },
        }

    @patch("app.services.symbol_service.exchange_service")
    def test_resolve_symbol_to_exchange_format_success(self, mock_exchange_service):
        """Test successful symbol ID to exchange format conversion."""
        # Mock exchange service
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = self.mock_markets
        mock_exchange_service.get_exchange.return_value = mock_exchange

        # Test conversion
        result = self.symbol_service.resolve_symbol_to_exchange_format("BTCUSDT")
        assert result == "BTC/USDT"

    @patch("app.services.symbol_service.exchange_service")
    def test_resolve_symbol_to_exchange_format_not_found(self, mock_exchange_service):
        """Test symbol ID conversion when symbol not found."""
        # Mock exchange service
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = self.mock_markets
        mock_exchange_service.get_exchange.return_value = mock_exchange

        # Test with non-existent symbol
        result = self.symbol_service.resolve_symbol_to_exchange_format("INVALID")
        assert result is None

    @patch("app.services.symbol_service.exchange_service")
    def test_resolve_symbol_already_in_exchange_format(self, mock_exchange_service):
        """Test when symbol is already in exchange format."""
        # Mock exchange service
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = self.mock_markets
        mock_exchange_service.get_exchange.return_value = mock_exchange

        # Test with exchange format symbol
        result = self.symbol_service.resolve_symbol_to_exchange_format("BTC/USDT")
        assert result == "BTC/USDT"

    @patch("app.services.symbol_service.exchange_service")
    def test_resolve_exchange_to_id_format_success(self, mock_exchange_service):
        """Test successful exchange format to symbol ID conversion."""
        # Mock exchange service
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = self.mock_markets
        mock_exchange_service.get_exchange.return_value = mock_exchange

        # Test conversion
        result = self.symbol_service.resolve_exchange_to_id_format("BTC/USDT")
        assert result == "BTCUSDT"

    @patch("app.services.symbol_service.exchange_service")
    def test_validate_symbol_exists_true(self, mock_exchange_service):
        """Test symbol validation for existing symbol."""
        # Mock exchange service
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = self.mock_markets
        mock_exchange_service.get_exchange.return_value = mock_exchange

        # Test validation
        result = self.symbol_service.validate_symbol_exists("BTCUSDT")
        assert result is True

    @patch("app.services.symbol_service.exchange_service")
    def test_validate_symbol_exists_false(self, mock_exchange_service):
        """Test symbol validation for non-existing symbol."""
        # Mock exchange service
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = self.mock_markets
        mock_exchange_service.get_exchange.return_value = mock_exchange

        # Test validation
        result = self.symbol_service.validate_symbol_exists("INVALID")
        assert result is False

    @patch("app.services.symbol_service.exchange_service")
    def test_get_symbol_info_success(self, mock_exchange_service):
        """Test getting symbol information for existing symbol."""
        # Mock exchange service with precision data
        mock_exchange = Mock()
        mock_markets_with_precision = self.mock_markets.copy()
        mock_markets_with_precision["BTC/USDT"]["precision"] = {
            "price": 0.01,
            "amount": 0.00001
        }
        mock_exchange.load_markets.return_value = mock_markets_with_precision
        mock_exchange_service.get_exchange.return_value = mock_exchange

        # Test getting symbol info
        result = self.symbol_service.get_symbol_info("BTCUSDT")

        assert result is not None
        assert result["id"] == "BTCUSDT"
        assert result["symbol"] == "BTC/USDT"
        assert result["base_asset"] == "BTC"
        assert result["quote_asset"] == "USDT"
        assert result["active"] is True
        assert result["type"] == "swap"
        # Verify precision fields are included
        assert "pricePrecision" in result
        assert "amountPrecision" in result

    @patch("app.services.symbol_service.exchange_service")
    def test_get_symbol_info_not_found(self, mock_exchange_service):
        """Test getting symbol information for non-existing symbol."""
        # Mock exchange service
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = self.mock_markets
        mock_exchange_service.get_exchange.return_value = mock_exchange

        # Test getting symbol info for invalid symbol
        result = self.symbol_service.get_symbol_info("INVALID")
        assert result is None

    @patch("app.services.symbol_service.exchange_service")
    def test_get_symbol_suggestions_exact_match(self, mock_exchange_service):
        """Test symbol suggestions with exact match (case insensitive)."""
        # Mock exchange service
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = self.mock_markets
        mock_exchange_service.get_exchange.return_value = mock_exchange

        # Test suggestions for case mismatch
        result = self.symbol_service.get_symbol_suggestions("btcusdt")
        assert "BTCUSDT" in result

    @patch("app.services.symbol_service.exchange_service")
    def test_get_symbol_suggestions_partial_match(self, mock_exchange_service):
        """Test symbol suggestions with partial matches."""
        # Mock exchange service
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = self.mock_markets
        mock_exchange_service.get_exchange.return_value = mock_exchange

        # Test suggestions for partial match
        result = self.symbol_service.get_symbol_suggestions("BTC")
        assert "BTCUSDT" in result

    @patch("app.services.symbol_service.exchange_service")
    def test_get_symbol_suggestions_pattern_match(self, mock_exchange_service):
        """Test symbol suggestions with pattern matching."""
        # Mock exchange service
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = self.mock_markets
        mock_exchange_service.get_exchange.return_value = mock_exchange

        # Test suggestions for USDT pattern
        result = self.symbol_service.get_symbol_suggestions("XYZUSDT")

        # Should suggest other USDT pairs
        usdt_symbols = [s for s in result if s.endswith("USDT")]
        assert len(usdt_symbols) > 0

    @patch("app.services.symbol_service.exchange_service")
    def test_get_symbol_suggestions_max_limit(self, mock_exchange_service):
        """Test symbol suggestions respects max limit."""
        # Mock exchange service
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = self.mock_markets
        mock_exchange_service.get_exchange.return_value = mock_exchange

        # Test suggestions with limit
        result = self.symbol_service.get_symbol_suggestions("USDT", max_suggestions=2)
        assert len(result) <= 2

    @patch("app.services.symbol_service.exchange_service")
    def test_cache_initialization_error_handling(self, mock_exchange_service):
        """Test cache initialization handles errors gracefully."""
        # Mock exchange service to raise an error
        mock_exchange_service.get_exchange.side_effect = Exception("Exchange error")

        # Should not raise exception, but falls back to demo symbols
        result = self.symbol_service.resolve_symbol_to_exchange_format("BTCUSDT")
        assert result == "BTC/USDT"  # Falls back to demo symbols

    @patch("app.services.symbol_service.exchange_service")
    def test_refresh_cache(self, mock_exchange_service):
        """Test cache refresh functionality."""
        # Mock exchange service
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = self.mock_markets
        mock_exchange_service.get_exchange.return_value = mock_exchange

        # Initialize cache
        self.symbol_service.resolve_symbol_to_exchange_format("BTCUSDT")

        # Refresh cache
        self.symbol_service.refresh_cache()

        # Should still work after refresh
        result = self.symbol_service.resolve_symbol_to_exchange_format("BTCUSDT")
        assert result == "BTC/USDT"

    @patch("app.services.symbol_service.exchange_service")
    def test_get_cache_stats(self, mock_exchange_service):
        """Test cache statistics functionality."""
        # Mock exchange service
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = self.mock_markets
        mock_exchange_service.get_exchange.return_value = mock_exchange

        # Initialize cache
        self.symbol_service.resolve_symbol_to_exchange_format("BTCUSDT")

        # Get cache stats
        stats = self.symbol_service.get_cache_stats()

        assert stats["initialized"] is True
        assert stats["symbol_count"] == 3  # BTC, ETH, ADA
        assert stats["exchange_symbol_count"] == 3
        assert stats["markets_loaded"] is True

    @patch("app.services.symbol_service.exchange_service")
    def test_get_all_symbols_success(self, mock_exchange_service):
        """Test get_all_symbols method returns properly formatted symbols."""
        # Mock exchange service
        mock_exchange = Mock()
        mock_exchange.options = {}
        
        # Create extended mock markets with precision data
        mock_markets_extended = {
            "BTC/USDT": {
                "id": "BTCUSDT",
                "symbol": "BTC/USDT",
                "base": "BTC",
                "quote": "USDT",
                "active": True,
                "type": "swap",
                "spot": False,
                "precision": {"price": 0.01, "amount": 0.00001}
            },
            "ETH/USDT": {
                "id": "ETHUSDT",
                "symbol": "ETH/USDT",
                "base": "ETH",
                "quote": "USDT",
                "active": True,
                "type": "swap",
                "spot": False,
                "precision": {"price": 0.01, "amount": 0.00001}
            },
            "ADA/BTC": {  # This should be filtered out (not USDT)
                "id": "ADABTC",
                "symbol": "ADA/BTC",
                "base": "ADA",
                "quote": "BTC",
                "active": True,
                "type": "swap",
                "spot": False,
                "precision": {"price": 0.00000001, "amount": 0.1}
            }
        }
        
        # Mock tickers with volume data
        mock_tickers = {
            "BTC/USDT": {
                "last": 50000.0,
                "info": {"quoteVolume": "1000000.0"}
            },
            "ETH/USDT": {
                "last": 3000.0,
                "info": {"quoteVolume": "500000.0"}
            }
        }
        
        mock_exchange.load_markets.return_value = mock_markets_extended
        mock_exchange.fetch_tickers.return_value = mock_tickers
        mock_exchange_service.get_exchange.return_value = mock_exchange
        
        # Test get_all_symbols
        result = self.symbol_service.get_all_symbols()
        
        # Should return only USDT pairs
        assert len(result) == 2
        
        # Check first symbol (should be BTC/USDT with higher volume)
        btc_symbol = next(s for s in result if s["id"] == "BTCUSDT")
        assert btc_symbol["symbol"] == "BTC/USDT"
        assert btc_symbol["base_asset"] == "BTC"
        assert btc_symbol["quote_asset"] == "USDT"
        assert btc_symbol["ui_name"] == "BTC/USDT"
        assert btc_symbol["volume24h"] == 1000000.0
        assert btc_symbol["pricePrecision"] == 2  # 0.01 -> 2 decimal places
        assert "roundingOptions" in btc_symbol
        assert "defaultRounding" in btc_symbol
        
        # Check ETH symbol
        eth_symbol = next(s for s in result if s["id"] == "ETHUSDT")
        assert eth_symbol["volume24h"] == 500000.0
        
        # Verify sorting by volume (BTC should be first due to higher volume)
        assert result[0]["id"] == "BTCUSDT"
        assert result[1]["id"] == "ETHUSDT"

    @patch("app.services.symbol_service.exchange_service")
    def test_get_all_symbols_filters_correctly(self, mock_exchange_service):
        """Test that get_all_symbols applies correct filters."""
        # Mock exchange service
        mock_exchange = Mock()
        mock_exchange.options = {}
        
        # Create mock markets with various types to test filtering
        mock_markets_filtering = {
            "BTC/USDT": {  # Should be included
                "id": "BTCUSDT",
                "symbol": "BTC/USDT",
                "base": "BTC",
                "quote": "USDT",
                "active": True,
                "type": "swap",
                "spot": False,
                "precision": {"price": 0.01, "amount": 0.00001}
            },
            "ETH/BTC": {  # Should be excluded (not USDT)
                "id": "ETHBTC",
                "symbol": "ETH/BTC",
                "base": "ETH",
                "quote": "BTC",
                "active": True,
                "type": "swap",
                "spot": False,
                "precision": {"price": 0.00000001, "amount": 0.001}
            },
            "ADA/USDT": {  # Should be excluded (spot market)
                "id": "ADAUSDT",
                "symbol": "ADA/USDT",
                "base": "ADA",
                "quote": "USDT",
                "active": True,
                "type": "spot",
                "spot": True,
                "precision": {"price": 0.0001, "amount": 0.1}
            },
            "DOT/USDT": {  # Should be excluded (inactive)
                "id": "DOTUSDT",
                "symbol": "DOT/USDT",
                "base": "DOT",
                "quote": "USDT",
                "active": False,
                "type": "swap",
                "spot": False,
                "precision": {"price": 0.001, "amount": 0.01}
            }
        }
        
        mock_exchange.load_markets.return_value = mock_markets_filtering
        mock_exchange.fetch_tickers.return_value = {}
        mock_exchange_service.get_exchange.return_value = mock_exchange
        
        # Test get_all_symbols
        result = self.symbol_service.get_all_symbols()
        
        # Should return only BTC/USDT (active, swap, USDT-quoted)
        assert len(result) == 1
        assert result[0]["id"] == "BTCUSDT"

    @patch("app.services.symbol_service.exchange_service")
    def test_get_all_symbols_exchange_error(self, mock_exchange_service):
        """Test get_all_symbols handles exchange errors."""
        # Mock exchange service to raise an error
        mock_exchange_service.get_exchange.side_effect = Exception("Exchange error")
        
        # Should return empty list when markets cache is not available
        result = self.symbol_service.get_all_symbols()
        assert result == []

    @patch("app.services.symbol_service.exchange_service")
    def test_fetch_tickers_caching(self, mock_exchange_service):
        """Test ticker caching functionality."""
        # Mock exchange service
        mock_exchange = Mock()
        mock_tickers = {"BTC/USDT": {"last": 50000.0}}
        mock_exchange.fetch_tickers.return_value = mock_tickers
        mock_exchange_service.get_exchange.return_value = mock_exchange
        
        # First call should fetch from exchange
        result1 = self.symbol_service._fetch_tickers()
        assert result1 == mock_tickers
        assert mock_exchange.fetch_tickers.call_count == 1
        
        # Second call should use cache
        result2 = self.symbol_service._fetch_tickers()
        assert result2 == mock_tickers
        assert mock_exchange.fetch_tickers.call_count == 1  # Still 1, not 2
        
        # Verify cache stats
        stats = self.symbol_service.get_cache_stats()
        assert stats["ticker_cache_loaded"] is True
        assert stats["ticker_cache_age_seconds"] is not None
        assert stats["ticker_cache_ttl_seconds"] == 300  # 5 minutes

    @patch("app.services.symbol_service.exchange_service")
    def test_fetch_tickers_cache_expiry(self, mock_exchange_service):
        """Test ticker cache expiry functionality."""
        # Mock exchange service
        mock_exchange = Mock()
        mock_tickers = {"BTC/USDT": {"last": 50000.0}}
        mock_exchange.fetch_tickers.return_value = mock_tickers
        mock_exchange_service.get_exchange.return_value = mock_exchange
        
        # Set short TTL for testing
        self.symbol_service._ticker_cache_ttl = 0.1  # 100ms
        
        # First call
        result1 = self.symbol_service._fetch_tickers()
        assert result1 == mock_tickers
        assert mock_exchange.fetch_tickers.call_count == 1
        
        # Wait for cache to expire
        time.sleep(0.2)
        
        # Second call should fetch again
        result2 = self.symbol_service._fetch_tickers()
        assert result2 == mock_tickers
        assert mock_exchange.fetch_tickers.call_count == 2

    @patch("app.services.symbol_service.exchange_service")
    def test_fetch_tickers_error_handling(self, mock_exchange_service):
        """Test ticker fetching error handling."""
        # Mock exchange service to raise an error
        mock_exchange = Mock()
        mock_exchange.fetch_tickers.side_effect = Exception("Ticker fetch error")
        mock_exchange_service.get_exchange.return_value = mock_exchange
        
        # Should return empty dict on error
        result = self.symbol_service._fetch_tickers()
        assert result == {}

    @patch("app.services.symbol_service.exchange_service")
    def test_refresh_cache_clears_ticker_cache(self, mock_exchange_service):
        """Test that refresh_cache clears ticker cache."""
        # Mock exchange service
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = self.mock_markets
        mock_exchange.fetch_tickers.return_value = {"BTC/USDT": {"last": 50000.0}}
        mock_exchange_service.get_exchange.return_value = mock_exchange
        
        # Initialize caches
        self.symbol_service._fetch_tickers()
        self.symbol_service.resolve_symbol_to_exchange_format("BTCUSDT")
        
        # Verify caches are loaded
        stats_before = self.symbol_service.get_cache_stats()
        assert stats_before["ticker_cache_loaded"] is True
        assert stats_before["initialized"] is True
        
        # Refresh cache
        self.symbol_service.refresh_cache()
        
        # Verify ticker cache is cleared
        stats_after = self.symbol_service.get_cache_stats()
        assert stats_after["ticker_cache_loaded"] is False
        assert stats_after["ticker_cache_age_seconds"] is None


# Integration test with actual exchange service (if available)
class TestSymbolServiceIntegration:
    """Integration tests for SymbolService with real exchange service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.symbol_service = SymbolService()

    @pytest.mark.integration
    def test_real_exchange_integration(self):
        """Test with real exchange service (requires network)."""
        # This test requires actual exchange connection
        # Skip if exchange is not available
        try:
            result = self.symbol_service.validate_symbol_exists("BTCUSDT")
            # If we get here, exchange is available
            assert isinstance(result, bool)
        except Exception:
            # Exchange not available, skip test
            pytest.skip("Exchange service not available for integration test")

    @pytest.mark.integration
    def test_cache_performance(self):
        """Test cache performance with multiple lookups."""
        import time

        # First lookup (cache miss)
        start_time = time.time()
        result1 = self.symbol_service.resolve_symbol_to_exchange_format("BTCUSDT")
        first_lookup_time = time.time() - start_time

        # Second lookup (cache hit)
        start_time = time.time()
        result2 = self.symbol_service.resolve_symbol_to_exchange_format("BTCUSDT")
        second_lookup_time = time.time() - start_time

        # Results should be the same
        assert result1 == result2

        # Second lookup should be faster (cache hit)
        # Only assert if both lookups succeeded
        if result1 is not None:
            assert second_lookup_time < first_lookup_time

    def test_format_volume_billions(self):
        """Test volume formatting for billions."""
        assert self.symbol_service.format_volume(1_234_567_890) == "1.23B"
        assert self.symbol_service.format_volume(5_000_000_000) == "5.00B"

    def test_format_volume_millions(self):
        """Test volume formatting for millions."""
        assert self.symbol_service.format_volume(1_234_567) == "1.23M"
        assert self.symbol_service.format_volume(500_000_000) == "500.00M"

    def test_format_volume_thousands(self):
        """Test volume formatting for thousands."""
        assert self.symbol_service.format_volume(1_234) == "1.23K"
        assert self.symbol_service.format_volume(999_999) == "1000.00K"

    def test_format_volume_small_numbers(self):
        """Test volume formatting for numbers less than 1000."""
        assert self.symbol_service.format_volume(123.45) == "123.45"
        assert self.symbol_service.format_volume(1) == "1.00"

    def test_format_volume_edge_cases(self):
        """Test volume formatting edge cases."""
        assert self.symbol_service.format_volume(None) == ""
        assert self.symbol_service.format_volume(0) == ""
        assert self.symbol_service.format_volume("invalid") == ""  # type: ignore

    def test_generate_price_format_normal_precision(self):
        """Test priceFormat generation for normal precision values."""
        # 2 decimal places
        result = self.symbol_service.generate_price_format(2)
        assert result["type"] == "price"
        assert result["precision"] == 2
        assert result["minMove"] == 0.01

        # 4 decimal places
        result = self.symbol_service.generate_price_format(4)
        assert result["type"] == "price"
        assert result["precision"] == 4
        assert result["minMove"] == 0.0001

        # 1 decimal place
        result = self.symbol_service.generate_price_format(1)
        assert result["type"] == "price"
        assert result["precision"] == 1
        assert result["minMove"] == 0.1

    def test_generate_price_format_edge_cases(self):
        """Test priceFormat generation for edge cases."""
        # None precision
        result = self.symbol_service.generate_price_format(None)
        assert result["type"] == "price"
        assert result["precision"] == 2
        assert result["minMove"] == 0.01

        # Very high precision (should be clamped to 8)
        result = self.symbol_service.generate_price_format(12)
        assert result["precision"] == 8
        assert result["minMove"] == 0.00000001

        # Negative precision (should be clamped to 0)
        result = self.symbol_service.generate_price_format(-1)
        assert result["precision"] == 0
        assert result["minMove"] == 1.0

    def test_get_symbol_info_includes_price_format(self):
        """Test that get_symbol_info includes priceFormat object."""
        # Mock markets cache
        self.symbol_service._markets_cache = {
            "BTC/USDT": {
                "id": "BTCUSDT",
                "symbol": "BTC/USDT",
                "base": "BTC",
                "quote": "USDT",
                "active": True,
                "type": "swap",
                "precision": {
                    "price": 1,
                    "amount": 8
                }
            }
        }
        
        # Mock symbol cache
        self.symbol_service._symbol_cache = {"BTCUSDT": "BTC/USDT"}
        self.symbol_service._cache_initialized = True

        result = self.symbol_service.get_symbol_info("BTCUSDT")
        
        assert result is not None
        assert "priceFormat" in result
        assert result["priceFormat"]["type"] == "price"
        assert result["priceFormat"]["precision"] == 1
        assert result["priceFormat"]["minMove"] == 0.1

    @patch('app.services.symbol_service.exchange_service')
    def test_get_all_symbols_includes_formatted_volume(self, mock_exchange_service):
        """Test that get_all_symbols includes volume24h_formatted field."""
        # Mock exchange and markets
        mock_exchange = Mock()
        mock_exchange.options = {}  # Add options dict for the Mock
        mock_exchange_service.get_exchange.return_value = mock_exchange
        
        self.symbol_service._markets_cache = {
            "BTC/USDT": {
                "id": "BTCUSDT",
                "symbol": "BTC/USDT",
                "base": "BTC",
                "quote": "USDT",
                "active": True,
                "type": "swap",
                "spot": False,
                "precision": {"price": 1, "amount": 8}
            }
        }
        self.symbol_service._cache_initialized = True  # Mark cache as initialized
        
        # Mock tickers with volume data
        mock_tickers = {
            "BTC/USDT": {
                "info": {
                    "quoteVolume": "1234567890"  # 1.23B
                }
            }
        }
        
        with patch.object(self.symbol_service, '_fetch_tickers', return_value=mock_tickers):
            result = self.symbol_service.get_all_symbols()
            
            assert len(result) > 0
            symbol = result[0]
            assert "volume24h_formatted" in symbol
            assert symbol["volume24h_formatted"] == "1.23B"
