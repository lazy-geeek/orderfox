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


class TestConnectionManagerFormattedFields:
    """Test cases for verifying formatted fields in WebSocket messages."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.connection_manager = ConnectionManager()
    
    @pytest.mark.asyncio
    async def test_broadcast_aggregated_orderbook_with_formatted_fields(self):
        """Test that broadcast includes formatted fields when symbol data is available."""
        # Mock WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        
        symbol = "BTCUSDT"
        connection_id = f"{symbol}:12345"
        
        # Set up connection metadata
        self.connection_manager._connection_metadata = {
            connection_id: {
                'websocket': mock_websocket,
                'symbol': symbol,
                'display_symbol': symbol
            }
        }
        
        # Mock aggregated orderbook data with formatted fields
        aggregated_data = {
            'symbol': symbol,
            'bids': [
                {
                    'price': 50000.12,
                    'amount': 0.001234,
                    'cumulative': 1.456789,
                    'price_formatted': '50000.12',
                    'amount_formatted': '0.00123400',
                    'cumulative_formatted': '1.46'
                },
                {
                    'price': 49999.50,
                    'amount': 0.002500,
                    'cumulative': 3.956789,
                    'price_formatted': '49999.50',
                    'amount_formatted': '0.00250000',
                    'cumulative_formatted': '3.96'
                }
            ],
            'asks': [
                {
                    'price': 50001.25,
                    'amount': 0.003456,
                    'cumulative': 2.123456,
                    'price_formatted': '50001.25',
                    'amount_formatted': '0.00345600',
                    'cumulative_formatted': '2.12'
                },
                {
                    'price': 50002.00,
                    'amount': 0.001000,
                    'cumulative': 3.123456,
                    'price_formatted': '50002.00',
                    'amount_formatted': '0.00100000',
                    'cumulative_formatted': '3.12'
                }
            ],
            'timestamp': 1640995200000,
            'rounding': 0.5,
            'limit': 2,
            'rounding_options': [0.01, 0.05, 0.1, 0.25, 0.5, 1.0],
            'market_depth_info': {
                'sufficient_data': True,
                'raw_levels_count': 100
            }
        }
        
        # Mock orderbook manager
        with patch('app.api.v1.endpoints.connection_manager.orderbook_manager') as mock_orderbook_manager:
            mock_orderbook_manager.get_aggregated_orderbook = AsyncMock(return_value=aggregated_data)
            
            # Test broadcast
            await self.connection_manager._broadcast_aggregated_orderbook(connection_id)
            
            # Verify WebSocket received data
            mock_websocket.send_text.assert_called_once()
            sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
            
            # Verify message structure
            assert sent_data['type'] == 'orderbook_update'
            assert sent_data['symbol'] == symbol
            assert 'bids' in sent_data
            assert 'asks' in sent_data
            assert 'timestamp' in sent_data
            assert 'rounding' in sent_data
            assert 'rounding_options' in sent_data
            
            # Verify formatted fields are present in bids
            for bid in sent_data['bids']:
                assert 'price' in bid
                assert 'amount' in bid
                assert 'cumulative' in bid
                assert 'price_formatted' in bid
                assert 'amount_formatted' in bid
                assert 'cumulative_formatted' in bid
                
                # Verify formatted fields are strings
                assert isinstance(bid['price_formatted'], str)
                assert isinstance(bid['amount_formatted'], str)
                assert isinstance(bid['cumulative_formatted'], str)
            
            # Verify formatted fields are present in asks
            for ask in sent_data['asks']:
                assert 'price' in ask
                assert 'amount' in ask
                assert 'cumulative' in ask
                assert 'price_formatted' in ask
                assert 'amount_formatted' in ask
                assert 'cumulative_formatted' in ask
                
                # Verify formatted fields are strings
                assert isinstance(ask['price_formatted'], str)
                assert isinstance(ask['amount_formatted'], str)
                assert isinstance(ask['cumulative_formatted'], str)
            
            # Verify specific formatting for small amounts
            bid_with_small_amount = next((b for b in sent_data['bids'] if float(b['amount']) < 0.01), None)
            if bid_with_small_amount:
                # Small amounts should have more precision than "0.00"
                assert len(bid_with_small_amount['amount_formatted'].split('.')[1]) > 2
                assert bid_with_small_amount['amount_formatted'] != "0.00"
    
    @pytest.mark.asyncio 
    async def test_broadcast_aggregated_orderbook_without_formatted_fields(self):
        """Test that broadcast works when formatted fields are not present."""
        # Mock WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        
        symbol = "ETHUSDT"
        connection_id = f"{symbol}:67890"
        
        # Set up connection metadata
        self.connection_manager._connection_metadata = {
            connection_id: {
                'websocket': mock_websocket,
                'symbol': symbol,
                'display_symbol': symbol
            }
        }
        
        # Mock aggregated orderbook data WITHOUT formatted fields
        aggregated_data = {
            'symbol': symbol,
            'bids': [
                {
                    'price': 3000.12,
                    'amount': 1.234567,
                    'cumulative': 5.123456
                }
            ],
            'asks': [
                {
                    'price': 3001.25,
                    'amount': 2.345678,
                    'cumulative': 7.234567
                }
            ],
            'timestamp': 1640995200000,
            'rounding': 1.0,
            'limit': 1,
            'rounding_options': [0.01, 0.1, 1.0, 10.0],
            'market_depth_info': {
                'sufficient_data': True,
                'raw_levels_count': 50
            }
        }
        
        # Mock orderbook manager
        with patch('app.api.v1.endpoints.connection_manager.orderbook_manager') as mock_orderbook_manager:
            mock_orderbook_manager.get_aggregated_orderbook = AsyncMock(return_value=aggregated_data)
            
            # Test broadcast
            await self.connection_manager._broadcast_aggregated_orderbook(connection_id)
            
            # Verify WebSocket received data
            mock_websocket.send_text.assert_called_once()
            sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
            
            # Verify message structure
            assert sent_data['type'] == 'orderbook_update'
            assert sent_data['symbol'] == symbol
            assert 'bids' in sent_data
            assert 'asks' in sent_data
            
            # Verify formatted fields are NOT present when not provided
            for bid in sent_data['bids']:
                assert 'price' in bid
                assert 'amount' in bid
                assert 'cumulative' in bid
                assert 'price_formatted' not in bid
                assert 'amount_formatted' not in bid
                assert 'cumulative_formatted' not in bid
            
            for ask in sent_data['asks']:
                assert 'price' in ask
                assert 'amount' in ask
                assert 'cumulative' in ask
                assert 'price_formatted' not in ask
                assert 'amount_formatted' not in ask
                assert 'cumulative_formatted' not in ask
    
    @pytest.mark.asyncio
    async def test_formatted_fields_pass_through_to_websocket(self):
        """Test that formatted fields are correctly passed through to WebSocket messages."""
        # Mock WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        
        symbol = "BTCUSDT"
        connection_id = f"{symbol}:test123"
        
        # Set up connection metadata
        self.connection_manager._connection_metadata = {
            connection_id: {
                'websocket': mock_websocket,
                'symbol': symbol,
                'display_symbol': symbol
            }
        }
        
        # Mock aggregated data with formatted fields (simulating what the aggregation service returns)
        mock_aggregated_data = {
            'symbol': symbol,
            'bids': [
                {
                    'price': 50000.0,
                    'amount': 0.00123456,
                    'cumulative': 0.00123456,
                    'price_formatted': '50000.00',
                    'amount_formatted': '0.00123456',
                    'cumulative_formatted': '0.0012'
                }
            ],
            'asks': [
                {
                    'price': 50001.0,
                    'amount': 0.00234567,
                    'cumulative': 0.00234567,
                    'price_formatted': '50001.00',
                    'amount_formatted': '0.00234567', 
                    'cumulative_formatted': '0.0023'
                }
            ],
            'timestamp': 1640995200000,
            'rounding': 0.1,
            'limit': 10,
            'rounding_options': [0.01, 0.05, 0.1, 0.25, 0.5, 1.0],
            'market_depth_info': {
                'sufficient_data': True,
                'raw_levels_count': 100
            }
        }
        
        # Mock orderbook manager to return our test data
        with patch('app.api.v1.endpoints.connection_manager.orderbook_manager') as mock_orderbook_manager:
            mock_orderbook_manager.get_aggregated_orderbook = AsyncMock(return_value=mock_aggregated_data)
            
            # Test the broadcast
            await self.connection_manager._broadcast_aggregated_orderbook(connection_id)
            
            # Verify WebSocket was called
            mock_websocket.send_text.assert_called_once()
            sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
            
            # Verify message structure and that formatted fields are preserved
            assert sent_data['type'] == 'orderbook_update'
            assert sent_data['symbol'] == symbol
            
            # Check that formatted fields are present and correct
            bid = sent_data['bids'][0]
            assert bid['price_formatted'] == '50000.00'
            assert bid['amount_formatted'] == '0.00123456'
            assert bid['cumulative_formatted'] == '0.0012'
            
            ask = sent_data['asks'][0]
            assert ask['price_formatted'] == '50001.00'
            assert ask['amount_formatted'] == '0.00234567'
            assert ask['cumulative_formatted'] == '0.0023'
            
            # Verify that the connection manager doesn't modify the formatted fields
            # They should be passed through exactly as received from the aggregation service
            assert sent_data['bids'] == mock_aggregated_data['bids']
            assert sent_data['asks'] == mock_aggregated_data['asks']
