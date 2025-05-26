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
            "BTCUSDT": {
                "id": "BTCUSDT",
                "symbol": "BTC/USDT",
                "base": "BTC",
                "quote": "USDT",
                "type": "future",
                "future": True,
                "spot": False,
                "contract": True,
                "swap": True,  # Perpetual swap
                "active": True,
            },
            "ETHUSDT": {
                "id": "ETHUSDT",
                "symbol": "ETH/USDT",
                "base": "ETH",
                "quote": "USDT",
                "type": "future",
                "future": True,
                "spot": False,
                "contract": True,
                "swap": True,  # Perpetual swap
                "active": True,
            },
            "ADAUSDT": {
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
            },
            "BTCUSDT_250627": {
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

        # Make request
        response = client.get("/api/v1/symbols")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert (
            len(data) == 2
        )  # Only perpetual swaps should be returned (not dated futures or spot)
        assert data[0]["symbol"] == "BTC/USDT"
        assert data[1]["symbol"] == "ETH/USDT"

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

    @patch("app.api.v1.endpoints.market_data_http.exchange_service")
    def test_get_orderbook_success(self, mock_exchange_service):
        """Test successful retrieval of order book."""
        # Mock exchange and order book data
        from unittest.mock import MagicMock

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

        # Verify exchange service was called
        mock_exchange_service.get_exchange.assert_called_once()
        mock_exchange.fetch_order_book.assert_called_once_with("BTCUSDT")

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

    @patch("app.api.v1.endpoints.market_data_http.exchange_service")
    def test_get_candles_success(self, mock_exchange_service):
        """Test successful retrieval of candles."""
        # Mock exchange and OHLCV data
        from unittest.mock import MagicMock

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

        # Verify exchange service was called
        mock_exchange_service.get_exchange.assert_called_once()
        mock_exchange.fetch_ohlcv.assert_called_once_with("BTCUSDT", "1m", limit=2)

    @patch("app.api.v1.endpoints.market_data_http.exchange_service")
    def test_get_candles_default_parameters(self, mock_exchange_service):
        """Test candles endpoint with default parameters."""
        from unittest.mock import MagicMock

        mock_exchange = MagicMock()
        mock_exchange_service.get_exchange.return_value = mock_exchange
        mock_exchange.fetch_ohlcv.return_value = []

        response = client.get("/api/v1/candles/BTCUSDT")

        assert response.status_code == 200
        mock_exchange.fetch_ohlcv.assert_called_once_with("BTCUSDT", "1m", limit=100)

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
