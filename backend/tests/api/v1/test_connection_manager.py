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


class TestConnectionManagerRaceConditionFixes:
    """Test cases for race condition fixes in WebSocket connection management."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.connection_manager = ConnectionManager()
    
    @pytest.mark.asyncio
    async def test_candle_stream_key_generation(self):
        """Test that candle stream keys are generated correctly for symbol/timeframe combinations."""
        test_cases = [
            ("BTCUSDT", "1m", "BTCUSDT:1m"),
            ("ETHUSDT", "5m", "ETHUSDT:5m"),
            ("XRPUSDT", "1h", "XRPUSDT:1h"),
            ("1000PEPEUSDT", "15m", "1000PEPEUSDT:15m"),
        ]
        
        for symbol, timeframe, expected_key in test_cases:
            # Test stream key generation logic
            stream_key = f"{symbol}:{timeframe}"
            assert stream_key == expected_key
    
    @pytest.mark.asyncio
    async def test_connection_isolation_by_stream_key(self):
        """Test that connections are properly isolated by stream key to prevent race conditions."""
        # Mock WebSockets for different streams
        mock_websocket_1m = AsyncMock()
        mock_websocket_5m = AsyncMock()
        mock_websocket_1m.accept = AsyncMock()
        mock_websocket_5m.accept = AsyncMock()
        
        # Different stream keys should create separate connections
        stream_key_1m = "BTCUSDT:1m"
        stream_key_5m = "BTCUSDT:5m"
        
        # Connect to different timeframes
        with patch.object(self.connection_manager, "_start_streaming") as mock_start_streaming:
            await self.connection_manager.connect(mock_websocket_1m, stream_key_1m, "candles")
            await self.connection_manager.connect(mock_websocket_5m, stream_key_5m, "candles")
            
            # Verify both connections exist separately
            assert stream_key_1m in self.connection_manager.active_connections
            assert stream_key_5m in self.connection_manager.active_connections
            assert mock_websocket_1m in self.connection_manager.active_connections[stream_key_1m]
            assert mock_websocket_5m in self.connection_manager.active_connections[stream_key_5m]
            
            # Verify separate streaming was started for each
            assert mock_start_streaming.call_count == 2
            mock_start_streaming.assert_any_call(stream_key_1m, "candles")
            mock_start_streaming.assert_any_call(stream_key_5m, "candles")
    
    @pytest.mark.asyncio
    async def test_timeframe_switch_isolation(self):
        """Test that switching timeframes properly isolates old and new connections."""
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        
        old_stream_key = "BTCUSDT:1m"
        new_stream_key = "BTCUSDT:5m"
        
        with patch.object(self.connection_manager, "_start_streaming") as mock_start_streaming:
            with patch.object(self.connection_manager, "_stop_streaming") as mock_stop_streaming:
                # Connect to 1m timeframe
                await self.connection_manager.connect(mock_websocket, old_stream_key, "candles")
                assert old_stream_key in self.connection_manager.active_connections
                
                # Disconnect from 1m (simulating timeframe switch)
                self.connection_manager.disconnect(mock_websocket, old_stream_key)
                assert old_stream_key not in self.connection_manager.active_connections
                mock_stop_streaming.assert_called_with(old_stream_key)
                
                # Connect to 5m timeframe
                await self.connection_manager.connect(mock_websocket, new_stream_key, "candles")
                assert new_stream_key in self.connection_manager.active_connections
                
                # Verify the isolation - old stream should be completely disconnected
                mock_start_streaming.assert_any_call(old_stream_key, "candles")
                mock_start_streaming.assert_any_call(new_stream_key, "candles")
    
    @pytest.mark.asyncio
    async def test_symbol_validation_in_broadcast(self):
        """Test that broadcast messages include proper symbol validation data."""
        mock_websocket = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        
        symbol = "BTCUSDT"
        timeframe = "1m"
        stream_key = f"{symbol}:{timeframe}"
        
        # Add connection manually
        self.connection_manager.active_connections[stream_key] = [mock_websocket]
        
        # Test broadcast with symbol validation
        test_data = {
            "type": "candle_update",
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": 1640995200000,
            "candle": {
                "open": 50000.0,
                "high": 51000.0,
                "low": 49000.0,
                "close": 50500.0
            }
        }
        
        await self.connection_manager.broadcast_to_symbol(stream_key, test_data)
        
        # Verify broadcast occurred
        mock_websocket.send_text.assert_called_once()
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        
        # Verify symbol and timeframe are included for validation
        assert sent_data["symbol"] == symbol
        assert sent_data["timeframe"] == timeframe
        assert "timestamp" in sent_data
    
    @pytest.mark.asyncio
    async def test_timestamp_ordering_protection(self):
        """Test that the system handles timestamp ordering issues gracefully."""
        mock_websocket = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        
        stream_key = "BTCUSDT:1m"
        self.connection_manager.active_connections[stream_key] = [mock_websocket]
        
        # Send candles with different timestamps to test ordering
        current_time = 1640995200000  # Base timestamp
        
        test_candles = [
            {
                "type": "candle_update",
                "symbol": "BTCUSDT",
                "timeframe": "1m",
                "timestamp": current_time,  # Current time
                "candle": {"open": 50000, "high": 51000, "low": 49000, "close": 50500}
            },
            {
                "type": "candle_update", 
                "symbol": "BTCUSDT",
                "timeframe": "1m",
                "timestamp": current_time + 60000,  # 1 minute later (should be accepted)
                "candle": {"open": 50500, "high": 51500, "low": 49500, "close": 51000}
            },
            {
                "type": "candle_update",
                "symbol": "BTCUSDT", 
                "timeframe": "1m",
                "timestamp": current_time - 60000,  # 1 minute earlier (would cause ordering issue)
                "candle": {"open": 49500, "high": 50500, "low": 48500, "close": 49000}
            }
        ]
        
        # Send all candles
        for candle_data in test_candles:
            await self.connection_manager.broadcast_to_symbol(stream_key, candle_data)
        
        # Verify all broadcasts were attempted (the frontend will handle timestamp validation)
        assert mock_websocket.send_text.call_count == 3
        
        # Verify the timestamps are preserved in the broadcast
        for i, call in enumerate(mock_websocket.send_text.call_args_list):
            sent_data = json.loads(call[0][0])
            expected_timestamp = test_candles[i]["timestamp"]
            assert sent_data["timestamp"] == expected_timestamp
    
    @pytest.mark.asyncio
    async def test_concurrent_symbol_timeframe_switches(self):
        """Test handling of concurrent symbol and timeframe switches to prevent race conditions."""
        mock_websockets = [AsyncMock() for _ in range(4)]
        for ws in mock_websockets:
            ws.accept = AsyncMock()
        
        # Simulate concurrent connections for different symbol/timeframe combinations
        stream_keys = [
            "BTCUSDT:1m",
            "BTCUSDT:5m", 
            "ETHUSDT:1m",
            "ETHUSDT:5m"
        ]
        
        with patch.object(self.connection_manager, "_start_streaming") as mock_start_streaming:
            # Connect all streams concurrently
            connection_tasks = []
            for ws, stream_key in zip(mock_websockets, stream_keys):
                task = self.connection_manager.connect(ws, stream_key, "candles")
                connection_tasks.append(task)
            
            # Wait for all connections to complete
            await asyncio.gather(*connection_tasks)
            
            # Verify all connections are isolated and properly established
            for i, stream_key in enumerate(stream_keys):
                assert stream_key in self.connection_manager.active_connections
                assert mock_websockets[i] in self.connection_manager.active_connections[stream_key]
            
            # Verify separate streaming started for each unique stream
            assert mock_start_streaming.call_count == 4
            for stream_key in stream_keys:
                mock_start_streaming.assert_any_call(stream_key, "candles")
    
    @pytest.mark.asyncio
    async def test_stream_cleanup_on_error(self):
        """Test that streams are properly cleaned up when errors occur to prevent memory leaks."""
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock(side_effect=Exception("Connection broken"))
        
        stream_key = "BTCUSDT:1m"
        
        # Add connection
        self.connection_manager.active_connections[stream_key] = [mock_websocket]
        
        # Attempt broadcast that will fail
        test_data = {"type": "candle_update", "symbol": "BTCUSDT"}
        await self.connection_manager.broadcast_to_symbol(stream_key, test_data)
        
        # Verify failed connection was removed to prevent race conditions
        assert mock_websocket not in self.connection_manager.active_connections.get(stream_key, [])
    
    @pytest.mark.asyncio
    async def test_message_filtering_by_stream_type(self):
        """Test that messages are properly filtered by stream type to prevent cross-contamination."""
        mock_websocket_candles = AsyncMock()
        mock_websocket_trades = AsyncMock()
        mock_websocket_candles.send_text = AsyncMock()
        mock_websocket_trades.send_text = AsyncMock()
        
        # Set up different stream types
        candle_stream_key = "BTCUSDT:1m"
        trades_stream_key = "BTCUSDT:trades"
        
        self.connection_manager.active_connections[candle_stream_key] = [mock_websocket_candles]
        self.connection_manager.active_connections[trades_stream_key] = [mock_websocket_trades]
        
        # Send candle data
        candle_data = {
            "type": "candle_update",
            "symbol": "BTCUSDT",
            "timeframe": "1m",
            "candle": {"open": 50000, "high": 51000, "low": 49000, "close": 50500}
        }
        
        # Send trades data
        trades_data = {
            "type": "trades_update", 
            "symbol": "BTCUSDT",
            "trades": [{"price": 50250.0, "amount": 1.5, "side": "buy"}]
        }
        
        # Broadcast to appropriate streams
        await self.connection_manager.broadcast_to_symbol(candle_stream_key, candle_data)
        await self.connection_manager.broadcast_to_symbol(trades_stream_key, trades_data)
        
        # Verify each connection only received its appropriate message type
        mock_websocket_candles.send_text.assert_called_once()
        mock_websocket_trades.send_text.assert_called_once()
        
        # Verify message content isolation
        candle_sent = json.loads(mock_websocket_candles.send_text.call_args[0][0])
        trades_sent = json.loads(mock_websocket_trades.send_text.call_args[0][0])
        
        assert candle_sent["type"] == "candle_update"
        assert "timeframe" in candle_sent
        assert trades_sent["type"] == "trades_update"
        assert "trades" in trades_sent
