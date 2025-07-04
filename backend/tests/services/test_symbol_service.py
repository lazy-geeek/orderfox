"""
Unit tests for the Symbol Service.

Tests symbol format conversion, validation, and suggestion functionality.
"""

import pytest
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

        # Should not raise exception, but return None for symbol resolution
        result = self.symbol_service.resolve_symbol_to_exchange_format("BTCUSDT")
        assert result is None

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
