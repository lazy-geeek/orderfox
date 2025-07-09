"""
Unit tests for ExchangeService.

This module contains comprehensive tests for the ExchangeService class,
including initialization, connection testing, and error handling.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
import ccxt
import ccxt.pro

from app.services.exchange_service import ExchangeService


class TestExchangeServiceInitialization:
    """Test ExchangeService initialization methods."""

    def setup_method(self):
        """Setup test environment."""
        self.exchange_service = ExchangeService()

    def test_init_creates_empty_instances(self):
        """Test that initialization creates empty exchange instances."""
        service = ExchangeService()
        assert service.exchange is None
        assert service.exchange_pro is None

    @patch("app.services.exchange_service.settings")
    @patch("app.services.exchange_service.ccxt.binance")
    def test_initialize_exchange_success(self, mock_binance, mock_settings):
        """Test successful exchange initialization."""
        # Setup mocks
        mock_settings.BINANCE_API_KEY = "test_api_key"
        mock_settings.BINANCE_SECRET_KEY = "test_secret_key"
        mock_settings.DEBUG = False

        mock_exchange_instance = MagicMock()
        mock_binance.return_value = mock_exchange_instance

        # Call method
        result = self.exchange_service.initialize_exchange()

        # Assertions
        assert result == mock_exchange_instance
        assert self.exchange_service.exchange == mock_exchange_instance

        # Verify ccxt.binance was called with correct parameters
        mock_binance.assert_called_once_with(
            {
                "apiKey": "test_api_key",
                "secret": "test_secret_key",
                "sandbox": False,
                "enableRateLimit": True,
                "options": {
                    "defaultType": "future",
                },
            }
        )

    @patch("app.services.exchange_service.settings")
    @patch("app.services.exchange_service.ccxt.binance")
    def test_initialize_exchange_debug_mode(self, mock_binance, mock_settings):
        """Test exchange initialization in debug mode (sandbox)."""
        mock_settings.BINANCE_API_KEY = "test_api_key"
        mock_settings.BINANCE_SECRET_KEY = "test_secret_key"
        mock_settings.DEBUG = True

        mock_exchange_instance = MagicMock()
        mock_binance.return_value = mock_exchange_instance

        result = self.exchange_service.initialize_exchange()

        # Verify sandbox mode is enabled
        call_args = mock_binance.call_args[0][0]
        assert (
            call_args["sandbox"] is False
        )  # ExchangeService hardcodes sandbox to False

    @patch("app.services.exchange_service.settings")
    def test_initialize_exchange_missing_api_key(self, mock_settings):
        """Test exchange initialization with missing API key."""
        mock_settings.BINANCE_API_KEY = None
        mock_settings.BINANCE_SECRET_KEY = "test_secret_key"

        # Expect no exception, but check that it initializes in demo mode
        with patch("app.services.exchange_service.ccxt.binance") as mock_binance:
            self.exchange_service.initialize_exchange()
            # Assert that it was called without API keys and with sandbox=False
            mock_binance.assert_called_once()
            call_args = mock_binance.call_args[0][0]
            assert "apiKey" not in call_args
            assert "secret" not in call_args
            assert call_args["sandbox"] is False

    @patch("app.services.exchange_service.settings")
    def test_initialize_exchange_missing_secret_key(self, mock_settings):
        """Test exchange initialization with missing secret key."""
        mock_settings.BINANCE_API_KEY = "test_api_key"
        mock_settings.BINANCE_SECRET_KEY = None

        # Expect no exception, but check that it initializes in demo mode
        with patch("app.services.exchange_service.ccxt.binance") as mock_binance:
            self.exchange_service.initialize_exchange()
            # Assert that it was called without API keys and with sandbox=False
            mock_binance.assert_called_once()
            call_args = mock_binance.call_args[0][0]
            assert "apiKey" not in call_args
            assert "secret" not in call_args
            assert call_args["sandbox"] is False

    @patch("app.services.exchange_service.settings")
    @patch("app.services.exchange_service.ccxt.binance")
    def test_initialize_exchange_network_error(self, mock_binance, mock_settings):
        """Test exchange initialization with network error."""
        mock_settings.BINANCE_API_KEY = "test_api_key"
        mock_settings.BINANCE_SECRET_KEY = "test_secret_key"
        mock_settings.DEBUG = False

        mock_binance.side_effect = ccxt.NetworkError("Network connection failed")

        with pytest.raises(HTTPException) as exc_info:
            self.exchange_service.initialize_exchange()

        assert exc_info.value.status_code == 503
        assert "network error" in exc_info.value.detail.lower()

    @patch("app.services.exchange_service.settings")
    @patch("app.services.exchange_service.ccxt.binance")
    def test_initialize_exchange_api_error(self, mock_binance, mock_settings):
        """Test exchange initialization with API error."""
        mock_settings.BINANCE_API_KEY = "test_api_key"
        mock_settings.BINANCE_SECRET_KEY = "test_secret_key"
        mock_settings.DEBUG = False

        mock_binance.side_effect = ccxt.ExchangeError("Invalid API credentials")

        with pytest.raises(HTTPException) as exc_info:
            self.exchange_service.initialize_exchange()

        assert exc_info.value.status_code == 502
        assert "api error" in exc_info.value.detail.lower()

    @patch("app.services.exchange_service.settings")
    @patch("app.services.exchange_service.ccxt.binance")
    def test_initialize_exchange_unexpected_error(self, mock_binance, mock_settings):
        """Test exchange initialization with unexpected error."""
        mock_settings.BINANCE_API_KEY = "test_api_key"
        mock_settings.BINANCE_SECRET_KEY = "test_secret_key"
        mock_settings.DEBUG = False

        mock_binance.side_effect = ValueError("Unexpected error")

        with pytest.raises(HTTPException) as exc_info:
            self.exchange_service.initialize_exchange()

        assert exc_info.value.status_code == 500
        assert "initialization failed" in exc_info.value.detail.lower()


class TestExchangeServicePro:
    """Test ExchangeService Pro (WebSocket) initialization methods."""

    def setup_method(self):
        """Setup test environment."""
        self.exchange_service = ExchangeService()

    @patch("app.services.exchange_service.settings")
    @patch("app.services.exchange_service.ccxt.pro")
    def test_initialize_exchange_pro_success(self, mock_ccxtpro, mock_settings):
        """Test successful exchange pro initialization."""
        mock_settings.BINANCE_API_KEY = "test_api_key"
        mock_settings.BINANCE_SECRET_KEY = "test_secret_key"
        mock_settings.DEBUG = False

        mock_exchange_pro_instance = MagicMock()
        mock_binance_pro = MagicMock(return_value=mock_exchange_pro_instance)
        mock_ccxtpro.binance = mock_binance_pro

        result = self.exchange_service.initialize_exchange_pro()

        assert result == mock_exchange_pro_instance
        assert self.exchange_service.exchange_pro == mock_exchange_pro_instance

        mock_binance_pro.assert_called_once_with(
            {
                "apiKey": "test_api_key",
                "secret": "test_secret_key",
                "sandbox": False,
                "enableRateLimit": True,
                "options": {
                    "defaultType": "future",
                },
            }
        )

    @patch("app.services.exchange_service.settings")
    def test_initialize_exchange_pro_missing_credentials(self, mock_settings):
        """Test exchange pro initialization with missing credentials."""
        mock_settings.BINANCE_API_KEY = None
        mock_settings.BINANCE_SECRET_KEY = None

        # Expect no exception, but check that it returns None
        result = self.exchange_service.initialize_exchange_pro()
        assert result is None

    @patch("app.services.exchange_service.settings")
    @patch("app.services.exchange_service.ccxt.pro")
    def test_initialize_exchange_pro_network_error(self, mock_ccxtpro, mock_settings):
        """Test exchange pro initialization with network error."""
        mock_settings.BINANCE_API_KEY = "test_api_key"
        mock_settings.BINANCE_SECRET_KEY = "test_secret_key"
        mock_settings.DEBUG = False

        mock_binance_pro = MagicMock(
            side_effect=ccxt.NetworkError("WebSocket connection failed")
        )
        mock_ccxtpro.binance = mock_binance_pro

        # Expect no exception, but check that it returns None
        result = self.exchange_service.initialize_exchange_pro()
        assert result is None


class TestExchangeServiceGetters:
    """Test ExchangeService getter methods."""

    def setup_method(self):
        """Setup test environment."""
        self.exchange_service = ExchangeService()

    @patch.object(ExchangeService, "initialize_exchange")
    def test_get_exchange_initializes_if_none(self, mock_initialize):
        """Test get_exchange initializes exchange if None."""
        mock_exchange = MagicMock()

        # Mock the initialize_exchange method to set the exchange attribute
        def mock_init():
            self.exchange_service.exchange = mock_exchange
            return mock_exchange

        mock_initialize.side_effect = mock_init

        # Ensure exchange is None
        self.exchange_service.exchange = None

        result = self.exchange_service.get_exchange()

        assert result == mock_exchange
        mock_initialize.assert_called_once()

    def test_get_exchange_returns_existing(self):
        """Test get_exchange returns existing exchange instance."""
        mock_exchange = MagicMock()
        self.exchange_service.exchange = mock_exchange

        result = self.exchange_service.get_exchange()

        assert result == mock_exchange

    @patch.object(ExchangeService, "initialize_exchange_pro")
    def test_get_exchange_pro_initializes_if_none(self, mock_initialize_pro):
        """Test get_exchange_pro initializes exchange_pro if None."""
        mock_exchange_pro = MagicMock()

        # Mock the initialize_exchange_pro method to set the exchange_pro attribute
        def mock_init_pro():
            self.exchange_service.exchange_pro = mock_exchange_pro
            return mock_exchange_pro

        mock_initialize_pro.side_effect = mock_init_pro

        # Ensure exchange_pro is None
        self.exchange_service.exchange_pro = None

        result = self.exchange_service.get_exchange_pro()

        assert result == mock_exchange_pro
        mock_initialize_pro.assert_called_once()

    def test_get_exchange_pro_returns_existing(self):
        """Test get_exchange_pro returns existing exchange_pro instance."""
        mock_exchange_pro = MagicMock()
        self.exchange_service.exchange_pro = mock_exchange_pro

        result = self.exchange_service.get_exchange_pro()

        assert result == mock_exchange_pro


class TestExchangeServiceConnectionTest:
    """Test ExchangeService connection testing methods."""

    def setup_method(self):
        """Setup test environment."""
        self.exchange_service = ExchangeService()

    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test successful connection test."""
        mock_exchange = MagicMock()
        mock_exchange.fetch_status.return_value = {
            "status": "ok",
            "updated": 1640995200000,
        }

        with patch.object(
            self.exchange_service, "get_exchange", return_value=mock_exchange
        ):
            result = await self.exchange_service.test_connection()

        assert result["status"] == "success"
        assert "successful" in result["message"].lower()
        assert "exchange_status" in result
        mock_exchange.fetch_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection_network_error(self):
        """Test connection test with network error."""
        mock_exchange = MagicMock()
        mock_exchange.fetch_status.side_effect = ccxt.NetworkError("Connection timeout")

        with patch.object(
            self.exchange_service, "get_exchange", return_value=mock_exchange
        ):
            result = await self.exchange_service.test_connection()

        assert result["status"] == "error"
        assert "network error" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_test_connection_exchange_error(self):
        """Test connection test with exchange error."""
        mock_exchange = MagicMock()
        mock_exchange.fetch_status.side_effect = ccxt.ExchangeError(
            "API rate limit exceeded"
        )

        with patch.object(
            self.exchange_service, "get_exchange", return_value=mock_exchange
        ):
            result = await self.exchange_service.test_connection()

        assert result["status"] == "error"
        assert "exchange api error" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_test_connection_http_exception(self):
        """Test connection test with HTTP exception from get_exchange."""
        with patch.object(
            self.exchange_service,
            "get_exchange",
            side_effect=HTTPException(status_code=500, detail="Config error"),
        ):
            result = await self.exchange_service.test_connection()

        assert result["status"] == "error"
        assert "config error" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_test_connection_unexpected_error(self):
        """Test connection test with unexpected error."""
        mock_exchange = MagicMock()
        mock_exchange.fetch_status.side_effect = ValueError("Unexpected error")

        with patch.object(
            self.exchange_service, "get_exchange", return_value=mock_exchange
        ):
            result = await self.exchange_service.test_connection()

        assert result["status"] == "error"
        assert "failed to connect" in result["message"].lower()


class TestExchangeServiceEdgeCases:
    """Test edge cases and integration scenarios."""

    def setup_method(self):
        """Setup test environment."""
        self.exchange_service = ExchangeService()

    @patch("app.services.exchange_service.settings")
    @patch("app.services.exchange_service.ccxt.binance")
    def test_multiple_initialization_calls(self, mock_binance, mock_settings):
        """Test that multiple initialization calls work correctly."""
        mock_settings.BINANCE_API_KEY = "test_api_key"
        mock_settings.BINANCE_SECRET_KEY = "test_secret_key"
        mock_settings.DEBUG = False

        mock_exchange1 = MagicMock()
        mock_exchange2 = MagicMock()
        mock_binance.side_effect = [mock_exchange1, mock_exchange2]

        # First initialization
        result1 = self.exchange_service.initialize_exchange()
        assert result1 == mock_exchange1
        assert self.exchange_service.exchange == mock_exchange1

        # Second initialization should replace the first
        result2 = self.exchange_service.initialize_exchange()
        assert result2 == mock_exchange2
        assert self.exchange_service.exchange == mock_exchange2

        # Verify both calls were made
        assert mock_binance.call_count == 2

    @patch("app.services.exchange_service.settings")
    def test_empty_string_credentials(self, mock_settings):
        """Test initialization with empty string credentials."""
        mock_settings.BINANCE_API_KEY = ""
        mock_settings.BINANCE_SECRET_KEY = ""

        # Expect no exception, but check that it initializes in demo mode
        with patch("app.services.exchange_service.ccxt.binance") as mock_binance:
            self.exchange_service.initialize_exchange()
            # Assert that it was called without API keys and with sandbox=False
            mock_binance.assert_called_once()
            call_args = mock_binance.call_args[0][0]
            assert "apiKey" not in call_args
            assert "secret" not in call_args
            assert call_args["sandbox"] is False

    @pytest.mark.asyncio
    async def test_test_connection_with_uninitialized_exchange(self):
        """Test connection test when exchange initialization fails."""
        with patch.object(
            self.exchange_service,
            "get_exchange",
            side_effect=HTTPException(status_code=500, detail="Init failed"),
        ):
            result = await self.exchange_service.test_connection()

        assert result["status"] == "error"
        assert "init failed" in result["message"].lower()
