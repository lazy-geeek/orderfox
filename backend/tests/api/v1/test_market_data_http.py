"""
Unit tests for market data HTTP API endpoints.

This module contains tests for the HTTP market data endpoints including
symbols, order book, and candles endpoints.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import sys
import os

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
from app.main import app

client = TestClient(app)


class TestSymbolsEndpoint:
    """Test cases for the /api/v1/symbols endpoint."""

    @patch("app.api.v1.endpoints.market_data_http.exchange_service")
    def test_get_symbols_success(self, mock_exchange_service):
        """Test successful retrieval of symbols."""
        # Mock exchange and markets data
        from unittest.mock import MagicMock

        mock_exchange = MagicMock()
        mock_exchange_service.get_exchange.return_value = mock_exchange

        mock_markets = {
            "BTC/USDT": {
                "id": "BTCUSDT",
                "symbol": "BTC/USDT",
                "base": "BTC",
                "quote": "USDT",
                "type": "swap",
                "future": True,
                "spot": False,
                "contract": True,
                "swap": True,  # Perpetual swap
                "active": True,
                "precision": {"price": 8},  # For pricePrecision
                "info": {"tickSize": "0.00000001"},  # For tickSize (string from API)
            },
            "ETH/USDT": {
                "id": "ETHUSDT",
                "symbol": "ETH/USDT",
                "base": "ETH",
                "quote": "USDT",
                "type": "swap",
                "future": True,
                "spot": False,
                "contract": True,
                "swap": True,  # Perpetual swap
                "active": True,
                "precision": {"price": 5},  # For pricePrecision
                "limits": {"price": {"min": 0.00001}},  # Alternative for tickSize
            },
            "ADA/USDT": {
                "id": "ADAUSDT",
                "symbol": "ADA/USDT",
                "base": "ADA",
                "quote": "USDT",
                "type": "spot",  # Should be filtered out
                "future": False,
                "spot": True,
                "contract": False,
                "swap": False,
                "active": True,
                "precision": {},  # Case where price precision is missing
                "info": {},  # Case where tickSize info is missing
            },
            "BTC/USDT:USDT-250627": {
                "id": "BTCUSDT_250627",
                "symbol": "BTC/USDT:USDT-250627",
                "base": "BTC",
                "quote": "USDT",
                "type": "future",
                "future": True,
                "spot": False,
                "contract": True,
                "swap": False,  # Dated future - should be filtered out
                "active": True,
            },
        }
        mock_exchange.load_markets.return_value = mock_markets

        # Mock tickers data
        mock_tickers = {
            "BTC/USDT": {"info": {"quoteVolume": "1000000"}},
            "ETH/USDT": {"info": {"quoteVolume": "500000"}},
            "ADA/USDT": {"info": {"quoteVolume": "100000"}},
            "BTC/USDT:USDT-250627": {"info": {"quoteVolume": "50000"}},
        }
        mock_exchange.fetch_tickers.return_value = mock_tickers

        # Make request
        response = client.get("/api/v1/symbols")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert (
            len(data) == 2
        )  # Only perpetual swaps should be returned (not dated futures or spot)

        # Sort data by symbol for consistent testing
        data_sorted = sorted(data, key=lambda x: x["symbol"])

        # Test BTC/USDT symbol
        btc_symbol = data_sorted[0]
        assert btc_symbol["symbol"] == "BTC/USDT"
        assert btc_symbol["baseAsset"] == "BTC"
        assert btc_symbol["quoteAsset"] == "USDT"
        assert btc_symbol["exchange"] == "binance"
        assert btc_symbol["pricePrecision"] == 8
        assert btc_symbol["tickSize"] == 0.00000001
        assert btc_symbol["volume24h"] == 1000000.0

        # Test ETH/USDT symbol
        eth_symbol = data_sorted[1]
        assert eth_symbol["symbol"] == "ETH/USDT"
        assert eth_symbol["baseAsset"] == "ETH"
        assert eth_symbol["quoteAsset"] == "USDT"
        assert eth_symbol["exchange"] == "binance"
        assert eth_symbol["pricePrecision"] == 5
        assert eth_symbol["tickSize"] == 0.00001  # From limits.price.min
        assert eth_symbol["volume24h"] == 500000.0

        # Verify exchange service was called
        mock_exchange_service.get_exchange.assert_called_once()
        mock_exchange.load_markets.assert_called_once()

    @patch("app.api.v1.endpoints.market_data_http.exchange_service")
    def test_get_symbols_missing_precision_data(self, mock_exchange_service):
        """Test symbols endpoint with missing or incomplete precision data."""
        # Mock exchange and markets data with various precision scenarios
        from unittest.mock import MagicMock

        mock_exchange = MagicMock()
        mock_exchange_service.get_exchange.return_value = mock_exchange

        mock_markets = {
            "DOT/USDT": {
                "id": "DOTUSDT",
                "symbol": "DOT/USDT",
                "base": "DOT",
                "quote": "USDT",
                "type": "swap",
                "future": True,
                "spot": False,
                "contract": True,
                "swap": True,
                "active": True,
                # Missing precision and info fields entirely
            },
            "LINK/USDT": {
                "id": "LINKUSDT",
                "symbol": "LINK/USDT",
                "base": "LINK",
                "quote": "USDT",
                "type": "swap",
                "future": True,
                "spot": False,
                "contract": True,
                "swap": True,
                "active": True,
                "precision": {},  # Empty precision object
                "info": {},  # Empty info object
            },
            "MATIC/USDT": {
                "id": "MATICUSDT",
                "symbol": "MATIC/USDT",
                "base": "MATIC",
                "quote": "USDT",
                "type": "swap",
                "future": True,
                "spot": False,
                "contract": True,
                "swap": True,
                "active": True,
                "precision": {"price": 6},  # Has pricePrecision
                # Missing info field for tickSize
            },
        }
        mock_exchange.load_markets.return_value = mock_markets

        # Mock tickers data
        mock_tickers = {
            "DOT/USDT": {"info": {"quoteVolume": "300000"}},
            "LINK/USDT": {"info": {"quoteVolume": "200000"}},
            "MATIC/USDT": {"info": {"quoteVolume": "150000"}},
        }
        mock_exchange.fetch_tickers.return_value = mock_tickers

        # Make request
        response = client.get("/api/v1/symbols")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

        # Sort data by symbol for consistent testing
        data_sorted = sorted(data, key=lambda x: x["symbol"])

        # Test DOT/USDT - completely missing precision data
        dot_symbol = data_sorted[0]
        assert dot_symbol["symbol"] == "DOT/USDT"
        assert dot_symbol["pricePrecision"] is None
        assert dot_symbol["tickSize"] is None
        assert dot_symbol["volume24h"] == 300000.0

        # Test LINK/USDT - empty precision objects
        link_symbol = data_sorted[1]
        assert link_symbol["symbol"] == "LINK/USDT"
        assert link_symbol["pricePrecision"] is None
        assert link_symbol["tickSize"] is None
        assert link_symbol["volume24h"] == 200000.0

        # Test MATIC/USDT - has pricePrecision but missing tickSize info
        matic_symbol = data_sorted[2]
        assert matic_symbol["symbol"] == "MATIC/USDT"
        assert matic_symbol["pricePrecision"] == 6
        assert (
            matic_symbol["tickSize"] == 0.000001
        )  # Calculated from pricePrecision (10^-6)
        assert matic_symbol["volume24h"] == 150000.0

        # Verify exchange service was called
        mock_exchange_service.get_exchange.assert_called_once()
        mock_exchange.load_markets.assert_called_once()

    @patch("app.api.v1.endpoints.market_data_http.exchange_service")
    def test_get_symbols_exchange_error(self, mock_exchange_service):
        """Test error handling when exchange fails."""
        mock_exchange_service.get_exchange.side_effect = Exception(
            "Exchange connection failed"
        )

        response = client.get("/api/v1/symbols")

        assert response.status_code == 500
        assert "Failed to fetch symbols" in response.json()["detail"]


class TestOrderBookEndpoint:
    """Test cases for the /api/v1/orderbook/{symbol} endpoint."""

    @patch("app.api.v1.endpoints.market_data_http.symbol_service")
    @patch("app.api.v1.endpoints.market_data_http.exchange_service")
    def test_get_orderbook_success(self, mock_exchange_service, mock_symbol_service):
        """Test successful retrieval of order book."""
        # Mock symbol service and exchange
        from unittest.mock import MagicMock

        mock_symbol_service.resolve_symbol_to_exchange_format.return_value = "BTC/USDT"
        mock_exchange = MagicMock()
        mock_exchange_service.get_exchange.return_value = mock_exchange

        mock_orderbook_data = {
            "bids": [[43250.50, 1.25], [43250.00, 0.75]],
            "asks": [[43251.00, 0.50], [43251.50, 2.00]],
            "timestamp": 1640995200000,  # 2022-01-01 12:00:00 UTC
        }
        mock_exchange.fetch_order_book.return_value = mock_orderbook_data

        # Make request
        response = client.get("/api/v1/orderbook/BTCUSDT")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BTCUSDT"
        assert len(data["bids"]) == 2
        assert len(data["asks"]) == 2
        assert data["bids"][0]["price"] == 43250.50
        assert data["bids"][0]["amount"] == 1.25
        assert data["asks"][0]["price"] == 43251.00
        assert data["asks"][0]["amount"] == 0.50

        # Verify services were called
        mock_symbol_service.resolve_symbol_to_exchange_format.assert_called_once_with(
            "BTCUSDT"
        )
        mock_exchange_service.get_exchange.assert_called_once()
        mock_exchange.fetch_order_book.assert_called_once_with("BTC/USDT", limit=100)

    @patch("app.api.v1.endpoints.market_data_http.symbol_service")
    @patch("app.api.v1.endpoints.market_data_http.exchange_service")
    def test_get_orderbook_with_custom_limit(
        self, mock_exchange_service, mock_symbol_service
    ):
        """Test order book retrieval with custom limit parameter."""
        # Mock symbol service and exchange
        from unittest.mock import MagicMock

        mock_symbol_service.resolve_symbol_to_exchange_format.return_value = "BTC/USDT"
        mock_exchange = MagicMock()
        mock_exchange_service.get_exchange.return_value = mock_exchange

        mock_orderbook_data = {
            "bids": [[43250.50, 1.25]],
            "asks": [[43251.00, 0.50]],
            "timestamp": 1640995200000,
        }
        mock_exchange.fetch_order_book.return_value = mock_orderbook_data

        # Make request with custom limit
        response = client.get("/api/v1/orderbook/BTCUSDT?limit=50")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BTCUSDT"

        # Verify services were called with custom limit
        mock_symbol_service.resolve_symbol_to_exchange_format.assert_called_once_with(
            "BTCUSDT"
        )
        mock_exchange_service.get_exchange.assert_called_once()
        mock_exchange.fetch_order_book.assert_called_once_with("BTC/USDT", limit=50)

    def test_get_orderbook_invalid_limit_too_high(self):
        """Test error handling for limit exceeding maximum."""
        response = client.get("/api/v1/orderbook/BTCUSDT?limit=2000")

        assert response.status_code == 422  # Validation error

    def test_get_orderbook_invalid_limit_too_low(self):
        """Test error handling for limit below minimum."""
        response = client.get("/api/v1/orderbook/BTCUSDT?limit=0")

        assert response.status_code == 422  # Validation error

    @patch("app.api.v1.endpoints.market_data_http.exchange_service")
    def test_get_orderbook_exchange_error(self, mock_exchange_service):
        """Test error handling when exchange fails."""
        from unittest.mock import MagicMock

        mock_exchange = MagicMock()
        mock_exchange_service.get_exchange.return_value = mock_exchange
        mock_exchange.fetch_order_book.side_effect = Exception("Symbol not found")

        response = client.get("/api/v1/orderbook/INVALID")

        assert response.status_code == 500
        assert "Failed to fetch order book" in response.json()["detail"]


class TestCandlesEndpoint:
    """Test cases for the /api/v1/candles/{symbol} endpoint."""

    @patch("app.api.v1.endpoints.market_data_http.symbol_service")
    @patch("app.api.v1.endpoints.market_data_http.exchange_service")
    def test_get_candles_success(self, mock_exchange_service, mock_symbol_service):
        """Test successful retrieval of candles."""
        # Mock symbol service and exchange
        from unittest.mock import MagicMock

        mock_symbol_service.resolve_symbol_to_exchange_format.return_value = "BTC/USDT"
        mock_exchange = MagicMock()
        mock_exchange_service.get_exchange.return_value = mock_exchange

        mock_ohlcv_data = [
            [
                1640995200000,
                43200.0,
                43300.0,
                43150.0,
                43250.0,
                125.75,
            ],  # 2022-01-01 12:00:00
            [
                1640995260000,
                43250.0,
                43280.0,
                43200.0,
                43220.0,
                98.50,
            ],  # 2022-01-01 12:01:00
        ]
        mock_exchange.fetch_ohlcv.return_value = mock_ohlcv_data

        # Make request
        response = client.get("/api/v1/candles/BTCUSDT?timeframe=1m&limit=2")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["open"] == 43200.0
        assert data[0]["high"] == 43300.0
        assert data[0]["low"] == 43150.0
        assert data[0]["close"] == 43250.0
        assert data[0]["volume"] == 125.75

        # Verify services were called
        mock_symbol_service.resolve_symbol_to_exchange_format.assert_called_once_with(
            "BTCUSDT"
        )
        mock_exchange_service.get_exchange.assert_called_once()
        mock_exchange.fetch_ohlcv.assert_called_once_with("BTC/USDT", "1m", limit=2)

    @patch("app.api.v1.endpoints.market_data_http.symbol_service")
    @patch("app.api.v1.endpoints.market_data_http.exchange_service")
    def test_get_candles_default_parameters(
        self, mock_exchange_service, mock_symbol_service
    ):
        """Test candles endpoint with default parameters."""
        from unittest.mock import MagicMock

        mock_symbol_service.resolve_symbol_to_exchange_format.return_value = "BTC/USDT"
        mock_exchange = MagicMock()
        mock_exchange_service.get_exchange.return_value = mock_exchange
        mock_exchange.fetch_ohlcv.return_value = []

        response = client.get("/api/v1/candles/BTCUSDT")

        assert response.status_code == 200
        mock_symbol_service.resolve_symbol_to_exchange_format.assert_called_once_with(
            "BTCUSDT"
        )
        mock_exchange.fetch_ohlcv.assert_called_once_with("BTC/USDT", "1m", limit=100)

    def test_get_candles_invalid_timeframe(self):
        """Test error handling for invalid timeframe."""
        response = client.get("/api/v1/candles/BTCUSDT?timeframe=invalid")

        assert response.status_code == 400
        assert "Invalid timeframe" in response.json()["detail"]

    def test_get_candles_invalid_limit(self):
        """Test error handling for invalid limit."""
        response = client.get("/api/v1/candles/BTCUSDT?limit=2000")

        assert response.status_code == 422  # Validation error

    @patch("app.api.v1.endpoints.market_data_http.exchange_service")
    def test_get_candles_exchange_error(self, mock_exchange_service):
        """Test error handling when exchange fails."""
        from unittest.mock import MagicMock

        mock_exchange = MagicMock()
        mock_exchange_service.get_exchange.return_value = mock_exchange
        mock_exchange.fetch_ohlcv.side_effect = Exception("Network error")

        response = client.get("/api/v1/candles/BTCUSDT")

        assert response.status_code == 500
        assert "Failed to fetch candles" in response.json()["detail"]
