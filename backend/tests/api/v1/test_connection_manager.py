"""
Unit tests for the ConnectionManager class.

This module contains tests for the WebSocket connection management functionality
including connection handling, broadcasting, and streaming.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
import json
import sys
import os

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
from app.api.v1.endpoints.connection_manager import ConnectionManager


class TestConnectionManager:
    """Test cases for the ConnectionManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.connection_manager = ConnectionManager()

    @pytest.mark.asyncio
    async def test_connection_manager_connect_disconnect(self):
        """Test connection manager connect and disconnect functionality."""
        # Mock WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()

        symbol = "BTCUSDT"

        # Test connect
        with patch.object(
            self.connection_manager, "_start_streaming"
        ) as mock_start_streaming:
            await self.connection_manager.connect(mock_websocket, symbol, "orderbook")

            # Verify connection was added
            assert symbol in self.connection_manager.active_connections
            assert mock_websocket in self.connection_manager.active_connections[symbol]
            mock_start_streaming.assert_called_once_with(symbol, "orderbook")

        # Test disconnect
        with patch.object(
            self.connection_manager, "_stop_streaming"
        ) as mock_stop_streaming:
            self.connection_manager.disconnect(mock_websocket, symbol)

            # Verify connection was removed and streaming stopped
            assert symbol not in self.connection_manager.active_connections
            mock_stop_streaming.assert_called_once_with(symbol)

    @pytest.mark.asyncio
    async def test_connection_manager_broadcast(self):
        """Test broadcasting data to connected clients."""
        # Mock WebSockets
        mock_websocket1 = AsyncMock()
        mock_websocket2 = AsyncMock()
        mock_websocket1.send_text = AsyncMock()
        mock_websocket2.send_text = AsyncMock()

        symbol = "BTCUSDT"

        # Add connections manually
        self.connection_manager.active_connections[symbol] = [
            mock_websocket1,
            mock_websocket2,
        ]

        # Test broadcast
        test_data = {"type": "orderbook_update", "symbol": symbol}
        await self.connection_manager.broadcast_to_symbol(symbol, test_data)

        # Verify both connections received the data
        mock_websocket1.send_text.assert_called_once_with(json.dumps(test_data))
        mock_websocket2.send_text.assert_called_once_with(json.dumps(test_data))

    @pytest.mark.asyncio
    async def test_connection_manager_broadcast_with_failed_connection(self):
        """Test broadcasting when one connection fails."""
        # Mock WebSockets - one working, one failing
        mock_websocket1 = AsyncMock()
        mock_websocket2 = AsyncMock()
        mock_websocket1.send_text = AsyncMock()
        mock_websocket2.send_text = AsyncMock(
            side_effect=Exception("Connection broken")
        )

        symbol = "BTCUSDT"

        # Add connections manually
        self.connection_manager.active_connections[symbol] = [
            mock_websocket1,
            mock_websocket2,
        ]

        # Test broadcast
        test_data = {"type": "orderbook_update", "symbol": symbol}
        await self.connection_manager.broadcast_to_symbol(symbol, test_data)

        # Verify working connection received data, failed connection was removed
        mock_websocket1.send_text.assert_called_once_with(json.dumps(test_data))
        assert mock_websocket2 not in self.connection_manager.active_connections[symbol]
        assert mock_websocket1 in self.connection_manager.active_connections[symbol]

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.connection_manager.exchange_service")
    async def test_stream_orderbook_exchange_error(self, mock_exchange_service):
        """Test order book streaming when exchange fails."""
        # Mock exchange service to raise exception
        mock_exchange_service.get_exchange_pro.side_effect = Exception(
            "Exchange initialization failed"
        )

        symbol = "BTCUSDT"

        # Add a mock connection
        mock_websocket = AsyncMock()
        self.connection_manager.active_connections[symbol] = [mock_websocket]

        # Mock broadcast method
        with patch.object(
            self.connection_manager, "broadcast_to_symbol"
        ) as mock_broadcast:
            # Test streaming should handle error gracefully
            await self.connection_manager._stream_orderbook(symbol)

            # Verify error was broadcast
            mock_broadcast.assert_called()
            call_args = mock_broadcast.call_args[0]
            assert call_args[0] == symbol
            assert call_args[1]["type"] == "error"
            assert "Failed to initialize streaming" in call_args[1]["message"]


class TestConnectionManagerExtended:
    """Test cases for the extended ConnectionManager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.connection_manager = ConnectionManager()

    @pytest.mark.asyncio
    async def test_connection_manager_ticker_stream(self):
        """Test connection manager ticker streaming functionality."""
        # Mock WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()

        symbol = "BTCUSDT"

        # Test connect for ticker
        with patch.object(
            self.connection_manager, "_start_streaming"
        ) as mock_start_streaming:
            await self.connection_manager.connect(mock_websocket, symbol, "ticker")

            # Verify connection was added and streaming started
            assert symbol in self.connection_manager.active_connections
            assert mock_websocket in self.connection_manager.active_connections[symbol]
            mock_start_streaming.assert_called_once_with(symbol, "ticker")

    @pytest.mark.asyncio
    async def test_connection_manager_candles_stream(self):
        """Test connection manager candles streaming functionality."""
        # Mock WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()

        stream_key = "BTCUSDT:1m"

        # Test connect for candles
        with patch.object(
            self.connection_manager, "_start_streaming"
        ) as mock_start_streaming:
            await self.connection_manager.connect(mock_websocket, stream_key, "candles")

            # Verify connection was added and streaming started
            assert stream_key in self.connection_manager.active_connections
            assert (
                mock_websocket in self.connection_manager.active_connections[stream_key]
            )
            mock_start_streaming.assert_called_once_with(stream_key, "candles")
