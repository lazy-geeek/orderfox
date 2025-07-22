"""
Unit tests for error handling and logging functionality.
"""

import pytest

# Chunk 1: Foundation tests - Database, config, utilities
pytestmark = pytest.mark.chunk1
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException

from app.services.exchange_service import ExchangeService
from app.services.trading_engine_service import TradingEngineService
from app.core.logging_config import setup_logging, get_logger


class TestExchangeServiceErrorHandling:
    """Test error handling in ExchangeService."""

    def setup_method(self):
        """Setup test environment."""
        setup_logging("DEBUG")
        self.exchange_service = ExchangeService()

    def test_initialize_exchange_missing_api_keys(self):
        """Test exchange initialization with missing API keys."""
        with patch("app.services.exchange_service.settings") as mock_settings:
            mock_settings.BINANCE_API_KEY = None
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

    def test_initialize_exchange_network_error(self):
        """Test exchange initialization with network error."""
        with patch("app.services.exchange_service.settings") as mock_settings:
            mock_settings.BINANCE_API_KEY = "test_key"
            mock_settings.BINANCE_SECRET_KEY = "test_secret"
            mock_settings.DEBUG = False

            with patch("app.services.exchange_service.ccxt.binance") as mock_binance:
                import ccxt

                mock_binance.side_effect = ccxt.NetworkError("Network error")

                with pytest.raises(HTTPException) as exc_info:
                    self.exchange_service.initialize_exchange()

                assert exc_info.value.status_code == 503
                assert "network error" in exc_info.value.detail.lower()

    def test_initialize_exchange_exchange_error(self):
        """Test exchange initialization with exchange error."""
        with patch("app.services.exchange_service.settings") as mock_settings:
            mock_settings.BINANCE_API_KEY = "test_key"
            mock_settings.BINANCE_SECRET_KEY = "test_secret"
            mock_settings.DEBUG = False

            with patch("app.services.exchange_service.ccxt.binance") as mock_binance:
                import ccxt

                mock_binance.side_effect = ccxt.ExchangeError("Exchange error")

                with pytest.raises(HTTPException) as exc_info:
                    self.exchange_service.initialize_exchange()

                assert exc_info.value.status_code == 502
                assert "api error" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test successful connection test."""
        mock_exchange = MagicMock()
        mock_exchange.fetch_status = AsyncMock(return_value={"status": "ok"})

        with patch.object(
            self.exchange_service, "get_exchange", return_value=mock_exchange
        ):
            result = await self.exchange_service.test_connection()

            assert result["status"] == "success"
            assert "successful" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_test_connection_network_error(self):
        """Test connection test with network error."""
        mock_exchange = MagicMock()
        import ccxt

        mock_exchange.fetch_status = MagicMock(
            side_effect=ccxt.NetworkError("Network error")
        )

        with patch.object(
            self.exchange_service, "get_exchange", return_value=mock_exchange
        ):
            result = await self.exchange_service.test_connection()

            assert result["status"] == "error"
            assert "network error" in result["message"].lower()


class TestTradingEngineServiceErrorHandling:
    """Test error handling in TradingEngineService."""

    def setup_method(self):
        """Setup test environment."""
        setup_logging("DEBUG")
        self.trading_engine = TradingEngineService()

    @pytest.mark.asyncio
    async def test_execute_trade_invalid_symbol(self):
        """Test trade execution with invalid symbol."""
        with pytest.raises(HTTPException) as exc_info:
            await self.trading_engine.execute_trade("", "buy", 1.0)

        assert exc_info.value.status_code == 400
        assert "invalid trade parameters" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_execute_trade_invalid_side(self):
        """Test trade execution with invalid side."""
        with pytest.raises(HTTPException) as exc_info:
            await self.trading_engine.execute_trade("BTCUSDT", "invalid_side", 1.0)

        assert exc_info.value.status_code == 400
        assert "invalid trade side" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_execute_trade_invalid_amount(self):
        """Test trade execution with invalid amount."""
        with pytest.raises(HTTPException) as exc_info:
            await self.trading_engine.execute_trade("BTCUSDT", "buy", -1.0)

        assert exc_info.value.status_code == 400
        assert "invalid trade parameters" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_execute_trade_limit_without_price(self):
        """Test limit order execution without price."""
        with pytest.raises(HTTPException) as exc_info:
            await self.trading_engine.execute_trade("BTCUSDT", "buy", 1.0, "limit")

        assert exc_info.value.status_code == 400
        assert "price is required" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_execute_trade_paper_success(self):
        """Test successful paper trade execution."""
        self.trading_engine.current_trading_mode = "paper"

        result = await self.trading_engine.execute_trade(
            "BTCUSDT", "buy", 1.0, "market"
        )

        assert result["status"] == "success"
        assert "paper trade executed" in result["message"].lower()
        assert len(self.trading_engine.paper_positions) == 1

    @pytest.mark.asyncio
    async def test_set_trading_mode_invalid(self):
        """Test setting invalid trading mode."""
        with pytest.raises(HTTPException) as exc_info:
            await self.trading_engine.set_trading_mode("invalid_mode")

        assert exc_info.value.status_code == 400
        assert "invalid trading mode" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_set_trading_mode_empty(self):
        """Test setting empty trading mode."""
        with pytest.raises(HTTPException) as exc_info:
            await self.trading_engine.set_trading_mode("")

        assert exc_info.value.status_code == 400
        assert "non-empty string" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_set_trading_mode_success(self):
        """Test successful trading mode change."""
        result = await self.trading_engine.set_trading_mode("paper")

        assert result["status"] == "success"
        assert self.trading_engine.current_trading_mode == "paper"

    @pytest.mark.asyncio
    async def test_get_open_positions_paper_mode(self):
        """Test getting positions in paper mode."""
        self.trading_engine.current_trading_mode = "paper"
        self.trading_engine.paper_positions = [{"symbol": "BTCUSDT", "side": "buy"}]

        positions = await self.trading_engine.get_open_positions()

        assert len(positions) == 1
        assert positions[0]["symbol"] == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_determine_signal_with_invalid_data(self):
        """Test signal determination with invalid data."""
        # Should not raise exception, just return None
        signal = await self.trading_engine.determine_signal("BTCUSDT", {})
        assert signal is None

        signal = await self.trading_engine.determine_signal("BTCUSDT", None)
        assert signal is None

    @pytest.mark.asyncio
    async def test_process_order_book_update_with_error(self):
        """Test order book processing with error in signal determination."""
        # Mock determine_signal to raise an exception
        with patch.object(
            self.trading_engine, "determine_signal", side_effect=Exception("Test error")
        ):
            # Should not raise exception, just log the error
            await self.trading_engine.process_order_book_update(
                "BTCUSDT", {"test": "data"}
            )


class TestLoggingConfiguration:
    """Test logging configuration."""

    def test_setup_logging(self):
        """Test logging setup."""
        logger = setup_logging("INFO")
        assert logger.name == "trading_bot"
        assert logger.level == 20  # INFO level

    def test_get_logger(self):
        """Test getting module logger."""
        logger = get_logger("test_module")
        assert logger.name == "trading_bot.test_module"
