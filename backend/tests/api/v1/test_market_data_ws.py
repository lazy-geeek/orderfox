"""
Unit tests for WebSocket market data endpoints.

This module contains comprehensive tests for the WebSocket market data endpoints
including connection management, order book streaming, and error handling.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
import json
from fastapi import WebSocketDisconnect

from app.api.v1.endpoints.market_data_ws import (
    websocket_orderbook,
    websocket_ticker,
    websocket_candles,
)


class TestWebSocketOrderbook:
    """Test WebSocket orderbook endpoint functionality."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.market_data_ws.exchange_service")
    @patch("app.api.v1.endpoints.market_data_ws.connection_manager")
    async def test_websocket_orderbook_success(
        self, mock_connection_manager, mock_exchange_service
    ):
        """Test successful WebSocket orderbook connection."""
        # Setup mocks
        mock_websocket = AsyncMock()
        mock_exchange = AsyncMock()
        mock_exchange_service.get_exchange.return_value = mock_exchange
        mock_exchange.markets = {"BTCUSDT": {"symbol": "BTCUSDT"}}
        mock_connection_manager.connect_orderbook = AsyncMock()
        mock_connection_manager.disconnect_orderbook = MagicMock()

        # Mock receive_text to simulate ping message then disconnect
        mock_websocket.receive_text.side_effect = [
            '{"type": "ping"}',
            WebSocketDisconnect(),
        ]

        # Call function
        await websocket_orderbook(mock_websocket, "BTCUSDT")

        # Assertions
        mock_exchange.load_markets.assert_called_once()
        mock_connection_manager.connect_orderbook.assert_called_once_with(
            mock_websocket, "BTCUSDT"
        )
        mock_connection_manager.disconnect_orderbook.assert_called_once_with(
            mock_websocket, "BTCUSDT"
        )

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.market_data_ws.exchange_service")
    async def test_websocket_orderbook_invalid_symbol(self, mock_exchange_service):
        """Test WebSocket orderbook with invalid symbol."""
        # Setup mocks
        mock_websocket = AsyncMock()
        mock_exchange = AsyncMock()
        mock_exchange_service.get_exchange.return_value = mock_exchange
        mock_exchange.markets = {}  # Empty markets - symbol not found

        # Call function
        await websocket_orderbook(mock_websocket, "INVALID")

        # Assertions
        mock_websocket.close.assert_called_once_with(
            code=4000, reason="Symbol INVALID not found"
        )

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.market_data_ws.exchange_service")
    @patch("app.api.v1.endpoints.market_data_ws.connection_manager")
    async def test_websocket_orderbook_ping_pong(
        self, mock_connection_manager, mock_exchange_service
    ):
        """Test WebSocket orderbook ping/pong functionality."""
        # Setup mocks
        mock_websocket = AsyncMock()
        mock_exchange = AsyncMock()
        mock_exchange_service.get_exchange.return_value = mock_exchange
        mock_exchange.markets = {"BTCUSDT": {"symbol": "BTCUSDT"}}
        mock_connection_manager.connect_orderbook = AsyncMock()
        mock_connection_manager.disconnect_orderbook = MagicMock()

        # Mock ping message
        mock_websocket.receive_text.side_effect = [
            '{"type": "ping"}',
            Exception("Disconnect"),  # Simulate disconnect
        ]

        # Call function
        await websocket_orderbook(mock_websocket, "BTCUSDT")

        # Verify pong was sent
        mock_websocket.send_text.assert_called_once_with('{"type": "pong"}')

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.market_data_ws.exchange_service")
    async def test_websocket_orderbook_connection_error(self, mock_exchange_service):
        """Test WebSocket orderbook connection error handling."""
        # Setup mocks
        mock_websocket = AsyncMock()
        mock_exchange_service.get_exchange.side_effect = Exception("Exchange error")

        # Call function
        await websocket_orderbook(mock_websocket, "BTCUSDT")

        # Should attempt to close with error
        mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.market_data_ws.exchange_service")
    @patch("app.api.v1.endpoints.market_data_ws.connection_manager")
    async def test_websocket_orderbook_invalid_json(
        self, mock_connection_manager, mock_exchange_service
    ):
        """Test WebSocket orderbook with invalid JSON message."""
        # Setup mocks
        mock_websocket = AsyncMock()
        mock_exchange = AsyncMock()
        mock_exchange_service.get_exchange.return_value = mock_exchange
        mock_exchange.markets = {"BTCUSDT": {"symbol": "BTCUSDT"}}
        mock_connection_manager.connect_orderbook = AsyncMock()
        mock_connection_manager.disconnect_orderbook = MagicMock()

        # Mock invalid JSON message
        mock_websocket.receive_text.side_effect = [
            "invalid json",
            Exception("Disconnect"),
        ]

        # Call function - should handle gracefully
        await websocket_orderbook(mock_websocket, "BTCUSDT")

        # Should still connect and disconnect
        mock_connection_manager.connect_orderbook.assert_called_once()
        mock_connection_manager.disconnect_orderbook.assert_called_once()


class TestWebSocketTicker:
    """Test WebSocket ticker endpoint functionality."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.market_data_ws.exchange_service")
    @patch("app.api.v1.endpoints.market_data_ws.connection_manager")
    async def test_websocket_ticker_success(
        self, mock_connection_manager, mock_exchange_service
    ):
        """Test successful WebSocket ticker connection."""
        # Setup mocks
        mock_websocket = AsyncMock()
        mock_exchange = AsyncMock()
        mock_exchange_service.get_exchange.return_value = mock_exchange
        mock_exchange.markets = {"ETHUSDT": {"symbol": "ETHUSDT"}}
        mock_connection_manager.connect = AsyncMock()
        mock_connection_manager.disconnect = MagicMock()

        # Mock receive_text to simulate disconnect
        mock_websocket.receive_text.side_effect = [WebSocketDisconnect()]

        # Call function
        await websocket_ticker(mock_websocket, "ETHUSDT")

        # Assertions
        mock_exchange.load_markets.assert_called_once()
        mock_connection_manager.connect.assert_called_once_with(
            mock_websocket, "ETHUSDT", "ticker"
        )
        mock_connection_manager.disconnect.assert_called_once_with(
            mock_websocket, "ETHUSDT"
        )

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.market_data_ws.exchange_service")
    async def test_websocket_ticker_invalid_symbol(self, mock_exchange_service):
        """Test WebSocket ticker with invalid symbol."""
        # Setup mocks
        mock_websocket = AsyncMock()
        mock_exchange = AsyncMock()
        mock_exchange_service.get_exchange.return_value = mock_exchange
        mock_exchange.markets = {}

        # Call function
        await websocket_ticker(mock_websocket, "INVALID")

        # Assertions
        mock_websocket.close.assert_called_once_with(
            code=4000, reason="Symbol INVALID not found"
        )

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.market_data_ws.exchange_service")
    @patch("app.api.v1.endpoints.market_data_ws.connection_manager")
    async def test_websocket_ticker_ping_pong(
        self, mock_connection_manager, mock_exchange_service
    ):
        """Test WebSocket ticker ping/pong functionality."""
        # Setup mocks
        mock_websocket = AsyncMock()
        mock_exchange = AsyncMock()
        mock_exchange_service.get_exchange.return_value = mock_exchange
        mock_exchange.markets = {"ETHUSDT": {"symbol": "ETHUSDT"}}
        mock_connection_manager.connect = AsyncMock()
        mock_connection_manager.disconnect = MagicMock()

        # Mock ping message
        mock_websocket.receive_text.side_effect = [
            '{"type": "ping"}',
            Exception("Disconnect"),
        ]

        # Call function
        await websocket_ticker(mock_websocket, "ETHUSDT")

        # Verify pong was sent
        mock_websocket.send_text.assert_called_once_with('{"type": "pong"}')


class TestWebSocketCandles:
    """Test WebSocket candles endpoint functionality."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.market_data_ws.exchange_service")
    @patch("app.api.v1.endpoints.market_data_ws.connection_manager")
    async def test_websocket_candles_success(
        self, mock_connection_manager, mock_exchange_service
    ):
        """Test successful WebSocket candles connection."""
        # Setup mocks
        mock_websocket = AsyncMock()
        mock_exchange = AsyncMock()
        mock_exchange_service.get_exchange.return_value = mock_exchange
        mock_exchange.markets = {"BTCUSDT": {"symbol": "BTCUSDT"}}
        mock_connection_manager.connect = AsyncMock()
        mock_connection_manager.disconnect = MagicMock()

        # Mock receive_text to simulate disconnect
        mock_websocket.receive_text.side_effect = [WebSocketDisconnect()]

        # Call function
        await websocket_candles(mock_websocket, "BTCUSDT", "1m")

        # Assertions
        mock_exchange.load_markets.assert_called_once()
        mock_connection_manager.connect.assert_called_once_with(
            mock_websocket, "BTCUSDT:1m", "candles"
        )
        mock_connection_manager.disconnect.assert_called_once_with(
            mock_websocket, "BTCUSDT:1m"
        )

    @pytest.mark.asyncio
    async def test_websocket_candles_invalid_timeframe(self):
        """Test WebSocket candles with invalid timeframe."""
        # Setup mocks
        mock_websocket = AsyncMock()

        # Call function with invalid timeframe
        await websocket_candles(mock_websocket, "BTCUSDT", "invalid")

        # Should close with error
        mock_websocket.close.assert_called_once()
        call_args = mock_websocket.close.call_args
        assert call_args[1]["code"] == 4000
        assert "Invalid timeframe" in call_args[1]["reason"]

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.market_data_ws.exchange_service")
    async def test_websocket_candles_invalid_symbol(self, mock_exchange_service):
        """Test WebSocket candles with invalid symbol."""
        # Setup mocks
        mock_websocket = AsyncMock()
        mock_exchange = AsyncMock()
        mock_exchange_service.get_exchange.return_value = mock_exchange
        mock_exchange.markets = {}

        # Call function
        await websocket_candles(mock_websocket, "INVALID", "1m")

        # Assertions
        mock_websocket.close.assert_called_with(
            code=4000, reason="Symbol INVALID not found"
        )

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.market_data_ws.exchange_service")
    @patch("app.api.v1.endpoints.market_data_ws.connection_manager")
    async def test_websocket_candles_valid_timeframes(
        self, mock_connection_manager, mock_exchange_service
    ):
        """Test WebSocket candles with all valid timeframes."""
        valid_timeframes = [
            "1m",
            "3m",
            "5m",
            "15m",
            "30m",
            "1h",
            "2h",
            "4h",
            "6h",
            "8h",
            "12h",
            "1d",
            "3d",
            "1w",
            "1M",
        ]

        for timeframe in valid_timeframes:
            # Setup mocks
            mock_websocket = AsyncMock()
            mock_exchange = AsyncMock()
            mock_exchange_service.get_exchange.return_value = mock_exchange
            mock_exchange.markets = {"BTCUSDT": {"symbol": "BTCUSDT"}}
            mock_connection_manager.connect = AsyncMock()
            mock_connection_manager.disconnect = MagicMock()

            # Mock receive_text to simulate disconnect
            mock_websocket.receive_text.side_effect = [WebSocketDisconnect()]

            # Call function
            await websocket_candles(mock_websocket, "BTCUSDT", timeframe)

            # Should not close with error
            mock_websocket.close.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.market_data_ws.exchange_service")
    @patch("app.api.v1.endpoints.market_data_ws.connection_manager")
    async def test_websocket_candles_ping_pong(
        self, mock_connection_manager, mock_exchange_service
    ):
        """Test WebSocket candles ping/pong functionality."""
        # Setup mocks
        mock_websocket = AsyncMock()
        mock_exchange = AsyncMock()
        mock_exchange_service.get_exchange.return_value = mock_exchange
        mock_exchange.markets = {"BTCUSDT": {"symbol": "BTCUSDT"}}
        mock_connection_manager.connect = AsyncMock()
        mock_connection_manager.disconnect = MagicMock()

        # Mock ping message
        mock_websocket.receive_text.side_effect = [
            '{"type": "ping"}',
            Exception("Disconnect"),
        ]

        # Call function
        await websocket_candles(mock_websocket, "BTCUSDT", "1m")

        # Verify pong was sent
        mock_websocket.send_text.assert_called_once_with('{"type": "pong"}')


class TestWebSocketErrorHandling:
    """Test WebSocket error handling scenarios."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.market_data_ws.exchange_service")
    async def test_websocket_orderbook_exchange_load_error(self, mock_exchange_service):
        """Test WebSocket orderbook when exchange load_markets fails."""
        # Setup mocks
        mock_websocket = AsyncMock()
        mock_exchange = AsyncMock()
        mock_exchange_service.get_exchange.return_value = mock_exchange
        mock_exchange.load_markets.side_effect = Exception("Load markets failed")

        # Call function
        await websocket_orderbook(mock_websocket, "BTCUSDT")

        # Should attempt to close with error
        mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.market_data_ws.exchange_service")
    @patch("app.api.v1.endpoints.market_data_ws.connection_manager")
    async def test_websocket_orderbook_connection_manager_error(
        self, mock_connection_manager, mock_exchange_service
    ):
        """Test WebSocket orderbook when connection manager fails."""
        # Setup mocks
        mock_websocket = AsyncMock()
        mock_exchange = AsyncMock()
        mock_exchange_service.get_exchange.return_value = mock_exchange
        mock_exchange.markets = {"BTCUSDT": {"symbol": "BTCUSDT"}}
        mock_connection_manager.connect_orderbook.side_effect = Exception(
            "Connection failed"
        )

        # Call function
        await websocket_orderbook(mock_websocket, "BTCUSDT")

        # Should attempt to close with error
        mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.market_data_ws.exchange_service")
    @patch("app.api.v1.endpoints.market_data_ws.connection_manager")
    async def test_websocket_close_error_handling(
        self, mock_connection_manager, mock_exchange_service
    ):
        """Test WebSocket error handling when close itself fails."""
        # Setup mocks
        mock_websocket = AsyncMock()
        mock_exchange_service.get_exchange.side_effect = Exception("Exchange error")
        mock_websocket.close.side_effect = Exception("Close failed")

        # Call function - should handle close error gracefully
        await websocket_orderbook(mock_websocket, "BTCUSDT")

        # Should attempt to close but handle error
        mock_websocket.close.assert_called_once()


class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.market_data_ws.exchange_service")
    @patch("app.api.v1.endpoints.market_data_ws.connection_manager")
    async def test_websocket_orderbook_complete_flow(
        self, mock_connection_manager, mock_exchange_service
    ):
        """Test complete WebSocket orderbook flow."""
        # Setup mocks
        mock_websocket = AsyncMock()
        mock_exchange = AsyncMock()
        mock_exchange_service.get_exchange.return_value = mock_exchange
        mock_exchange.markets = {"BTCUSDT": {"symbol": "BTCUSDT"}}
        mock_connection_manager.connect_orderbook = AsyncMock()
        mock_connection_manager.disconnect_orderbook = MagicMock()

        # Simulate multiple messages
        mock_websocket.receive_text.side_effect = [
            '{"type": "ping"}',
            '{"type": "ping"}',
            '{"type": "unknown"}',  # Should be handled gracefully
            WebSocketDisconnect(),
        ]

        # Call function
        await websocket_orderbook(mock_websocket, "BTCUSDT")

        # Verify connection lifecycle
        mock_connection_manager.connect_orderbook.assert_called_once()
        mock_connection_manager.disconnect_orderbook.assert_called_once()

        # Verify pong responses (2 pings)
        assert mock_websocket.send_text.call_count == 2

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.market_data_ws.exchange_service")
    @patch("app.api.v1.endpoints.market_data_ws.connection_manager")
    async def test_websocket_multiple_endpoints_different_symbols(
        self, mock_connection_manager, mock_exchange_service
    ):
        """Test multiple WebSocket endpoints with different symbols."""
        # Setup mocks
        mock_exchange = AsyncMock()
        mock_exchange_service.get_exchange.return_value = mock_exchange
        mock_exchange.markets = {
            "BTCUSDT": {"symbol": "BTCUSDT"},
            "ETHUSDT": {"symbol": "ETHUSDT"},
        }
        mock_connection_manager.connect_orderbook = AsyncMock()
        mock_connection_manager.connect = AsyncMock()
        mock_connection_manager.disconnect_orderbook = MagicMock()
        mock_connection_manager.disconnect = MagicMock()

        # Test orderbook and ticker with different symbols
        mock_websocket1 = AsyncMock()
        mock_websocket1.receive_text.side_effect = [WebSocketDisconnect()]

        mock_websocket2 = AsyncMock()
        mock_websocket2.receive_text.side_effect = [WebSocketDisconnect()]

        # Call both endpoints
        await websocket_orderbook(mock_websocket1, "BTCUSDT")
        await websocket_ticker(mock_websocket2, "ETHUSDT")

        # Verify both connections were handled
        mock_connection_manager.connect_orderbook.assert_called_once_with(
            mock_websocket1, "BTCUSDT"
        )
        mock_connection_manager.connect.assert_called_once_with(
            mock_websocket2, "ETHUSDT", "ticker"
        )
