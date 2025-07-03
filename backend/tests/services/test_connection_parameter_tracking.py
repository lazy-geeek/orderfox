import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.api.v1.endpoints.connection_manager import ConnectionManager
from app.services.orderbook_manager import OrderBookManager


class TestConnectionParameterTracking:
    """
    Comprehensive unit tests for connection parameter tracking.
    Tests WebSocket message handling, parameter updates, and state management.
    """

    @pytest.fixture
    async def connection_manager(self):
        """Create a fresh connection manager for each test."""
        manager = ConnectionManager()
        yield manager
        # Cleanup
        await manager.cleanup()

    @pytest.fixture
    async def orderbook_manager(self):
        """Create a fresh orderbook manager for each test."""
        manager = OrderBookManager.__new__(OrderBookManager)
        manager._initialized = False
        manager.__init__()
        yield manager
        await manager.shutdown()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket connection."""
        websocket = AsyncMock()
        websocket.send = AsyncMock()
        websocket.close = AsyncMock()
        return websocket

    class TestParameterStorage:
        """Test parameter storage and retrieval."""

        @pytest.mark.asyncio
        async def test_store_connection_parameters(self, orderbook_manager):
            """Test storing connection parameters."""
            connection_id = "test_conn_1"
            symbol = "BTCUSDT"
            limit = 20
            rounding = 1.0
            
            with patch('app.services.orderbook_manager.OrderBook'):
                # Register connection with parameters
                await orderbook_manager.register_connection(connection_id, symbol, limit, rounding)
                
                # Verify parameters are stored
                params = await orderbook_manager.get_connection_params(connection_id)
                assert params is not None
                assert params['symbol'] == symbol
                assert params['limit'] == limit
                assert params['rounding'] == rounding
                assert 'connected_at' in params

        @pytest.mark.asyncio
        async def test_multiple_connections_different_parameters(self, orderbook_manager):
            """Test storing different parameters for multiple connections."""
            connections = [
                ("conn_1", "BTCUSDT", 10, 1.0),
                ("conn_2", "BTCUSDT", 20, 0.5),
                ("conn_3", "ETHUSDT", 50, 0.1)
            ]
            
            with patch('app.services.orderbook_manager.OrderBook'):
                # Register all connections
                for conn_id, symbol, limit, rounding in connections:
                    await orderbook_manager.register_connection(conn_id, symbol, limit, rounding)
                
                # Verify each has correct parameters
                for conn_id, symbol, limit, rounding in connections:
                    params = await orderbook_manager.get_connection_params(conn_id)
                    assert params['symbol'] == symbol
                    assert params['limit'] == limit
                    assert params['rounding'] == rounding

        @pytest.mark.asyncio
        async def test_parameter_timestamps(self, orderbook_manager):
            """Test that timestamps are recorded for parameter changes."""
            connection_id = "test_conn"
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook'):
                # Register connection
                start_time = time.time()
                await orderbook_manager.register_connection(connection_id, symbol, 10, 1.0)
                
                params = await orderbook_manager.get_connection_params(connection_id)
                assert params['connected_at'] >= start_time
                
                # Update parameters
                update_time = time.time()
                await orderbook_manager.update_connection_params(connection_id, limit=20)
                
                updated_params = await orderbook_manager.get_connection_params(connection_id)
                assert updated_params['updated_at'] >= update_time

    class TestParameterUpdates:
        """Test parameter update functionality."""

        @pytest.mark.asyncio
        async def test_update_limit_parameter(self, orderbook_manager):
            """Test updating limit parameter."""
            connection_id = "test_conn"
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook'):
                # Register connection
                await orderbook_manager.register_connection(connection_id, symbol, 10, 1.0)
                
                # Update limit
                result = await orderbook_manager.update_connection_params(connection_id, limit=25)
                assert result is True
                
                # Verify update
                params = await orderbook_manager.get_connection_params(connection_id)
                assert params['limit'] == 25
                assert params['rounding'] == 1.0  # Unchanged

        @pytest.mark.asyncio
        async def test_update_rounding_parameter(self, orderbook_manager):
            """Test updating rounding parameter."""
            connection_id = "test_conn"
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook'):
                # Register connection
                await orderbook_manager.register_connection(connection_id, symbol, 10, 1.0)
                
                # Update rounding
                result = await orderbook_manager.update_connection_params(connection_id, rounding=0.25)
                assert result is True
                
                # Verify update
                params = await orderbook_manager.get_connection_params(connection_id)
                assert params['limit'] == 10  # Unchanged
                assert params['rounding'] == 0.25

        @pytest.mark.asyncio
        async def test_update_both_parameters(self, orderbook_manager):
            """Test updating both limit and rounding parameters."""
            connection_id = "test_conn"
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook'):
                # Register connection
                await orderbook_manager.register_connection(connection_id, symbol, 10, 1.0)
                
                # Update both parameters
                result = await orderbook_manager.update_connection_params(
                    connection_id, limit=30, rounding=2.0
                )
                assert result is True
                
                # Verify both updates
                params = await orderbook_manager.get_connection_params(connection_id)
                assert params['limit'] == 30
                assert params['rounding'] == 2.0

        @pytest.mark.asyncio
        async def test_update_nonexistent_connection(self, orderbook_manager):
            """Test updating parameters for non-existent connection."""
            result = await orderbook_manager.update_connection_params(
                "nonexistent", limit=20, rounding=1.0
            )
            assert result is False

        @pytest.mark.asyncio
        async def test_partial_parameter_updates(self, orderbook_manager):
            """Test updating only some parameters (None values)."""
            connection_id = "test_conn"
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook'):
                # Register connection
                await orderbook_manager.register_connection(connection_id, symbol, 10, 1.0)
                
                # Update only limit (rounding=None)
                result = await orderbook_manager.update_connection_params(
                    connection_id, limit=15, rounding=None
                )
                assert result is True
                
                params = await orderbook_manager.get_connection_params(connection_id)
                assert params['limit'] == 15
                assert params['rounding'] == 1.0  # Unchanged
                
                # Update only rounding (limit=None)
                result = await orderbook_manager.update_connection_params(
                    connection_id, limit=None, rounding=0.5
                )
                assert result is True
                
                params = await orderbook_manager.get_connection_params(connection_id)
                assert params['limit'] == 15  # Unchanged
                assert params['rounding'] == 0.5

    class TestWebSocketMessageHandling:
        """Test WebSocket message handling for parameter updates."""

        @pytest.mark.asyncio
        async def test_handle_parameter_update_message(self, connection_manager, mock_websocket):
            """Test handling parameter update WebSocket messages."""
            connection_id = "test_conn"
            symbol = "BTCUSDT"
            
            # Mock the orderbook manager
            with patch.object(connection_manager, 'orderbook_manager') as mock_manager:
                mock_manager.update_connection_params = AsyncMock(return_value=True)
                mock_manager.get_aggregated_orderbook = AsyncMock(return_value={
                    'symbol': symbol,
                    'bids': [],
                    'asks': [],
                    'limit': 25,
                    'rounding': 0.5
                })
                
                # Register connection
                connection_manager.connections[connection_id] = {
                    'websocket': mock_websocket,
                    'symbol': symbol,
                    'stream_type': 'orderbook'
                }
                
                # Create parameter update message
                message = {
                    'type': 'update_params',
                    'limit': 25,
                    'rounding': 0.5
                }
                
                # Handle message
                await connection_manager.handle_websocket_message(
                    connection_id, json.dumps(message)
                )
                
                # Verify manager was called
                mock_manager.update_connection_params.assert_called_once_with(
                    connection_id, 25, 0.5
                )
                
                # Verify aggregated data was sent
                mock_websocket.send.assert_called()

        @pytest.mark.asyncio
        async def test_handle_invalid_parameter_message(self, connection_manager, mock_websocket):
            """Test handling invalid parameter update messages."""
            connection_id = "test_conn"
            
            # Mock the orderbook manager
            with patch.object(connection_manager, 'orderbook_manager') as mock_manager:
                mock_manager.update_connection_params = AsyncMock(return_value=False)
                
                # Register connection
                connection_manager.connections[connection_id] = {
                    'websocket': mock_websocket,
                    'symbol': 'BTCUSDT',
                    'stream_type': 'orderbook'
                }
                
                # Create invalid parameter message
                message = {
                    'type': 'update_params',
                    'limit': 'invalid',  # Should be int
                    'rounding': 'invalid'  # Should be float
                }
                
                # Handle message should not crash
                await connection_manager.handle_websocket_message(
                    connection_id, json.dumps(message)
                )
                
                # Should not call update since parameters are invalid
                mock_manager.update_connection_params.assert_not_called()

        @pytest.mark.asyncio
        async def test_acknowledgment_message_sent(self, connection_manager, mock_websocket):
            """Test that acknowledgment messages are sent for parameter updates."""
            connection_id = "test_conn"
            symbol = "BTCUSDT"
            
            with patch.object(connection_manager, 'orderbook_manager') as mock_manager:
                mock_manager.update_connection_params = AsyncMock(return_value=True)
                mock_manager.get_aggregated_orderbook = AsyncMock(return_value={
                    'symbol': symbol,
                    'bids': [],
                    'asks': [],
                    'limit': 20,
                    'rounding': 1.0
                })
                
                # Register connection
                connection_manager.connections[connection_id] = {
                    'websocket': mock_websocket,
                    'symbol': symbol,
                    'stream_type': 'orderbook'
                }
                
                # Handle parameter update
                message = {'type': 'update_params', 'limit': 20, 'rounding': 1.0}
                await connection_manager.handle_websocket_message(
                    connection_id, json.dumps(message)
                )
                
                # Check that websocket.send was called
                assert mock_websocket.send.call_count >= 1
                
                # Verify acknowledgment in sent messages
                sent_calls = mock_websocket.send.call_args_list
                ack_sent = False
                for call in sent_calls:
                    sent_data = json.loads(call[0][0])
                    if sent_data.get('type') == 'param_update_ack':
                        ack_sent = True
                        assert sent_data['limit'] == 20
                        assert sent_data['rounding'] == 1.0
                        break
                
                assert ack_sent, "Acknowledgment message should be sent"

    class TestParameterValidation:
        """Test parameter validation."""

        @pytest.mark.asyncio
        async def test_valid_limit_values(self, orderbook_manager):
            """Test validation of limit parameter values."""
            connection_id = "test_conn"
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook'):
                await orderbook_manager.register_connection(connection_id, symbol, 10, 1.0)
                
                # Test valid limit values
                valid_limits = [5, 10, 20, 50, 100]
                for limit in valid_limits:
                    result = await orderbook_manager.update_connection_params(
                        connection_id, limit=limit
                    )
                    assert result is True
                    
                    params = await orderbook_manager.get_connection_params(connection_id)
                    assert params['limit'] == limit

        @pytest.mark.asyncio
        async def test_valid_rounding_values(self, orderbook_manager):
            """Test validation of rounding parameter values."""
            connection_id = "test_conn"
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook'):
                await orderbook_manager.register_connection(connection_id, symbol, 10, 1.0)
                
                # Test valid rounding values
                valid_roundings = [0.01, 0.1, 0.25, 0.5, 1.0, 5.0, 10.0, 100.0]
                for rounding in valid_roundings:
                    result = await orderbook_manager.update_connection_params(
                        connection_id, rounding=rounding
                    )
                    assert result is True
                    
                    params = await orderbook_manager.get_connection_params(connection_id)
                    assert params['rounding'] == rounding

    class TestConcurrentParameterUpdates:
        """Test concurrent parameter updates."""

        @pytest.mark.asyncio
        async def test_concurrent_parameter_updates_same_connection(self, orderbook_manager):
            """Test concurrent updates to the same connection."""
            connection_id = "test_conn"
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook'):
                await orderbook_manager.register_connection(connection_id, symbol, 10, 1.0)
                
                # Create multiple concurrent update tasks
                tasks = [
                    asyncio.create_task(
                        orderbook_manager.update_connection_params(connection_id, limit=20)
                    ),
                    asyncio.create_task(
                        orderbook_manager.update_connection_params(connection_id, rounding=0.5)
                    ),
                    asyncio.create_task(
                        orderbook_manager.update_connection_params(connection_id, limit=30, rounding=2.0)
                    )
                ]
                
                # Wait for all tasks to complete
                results = await asyncio.gather(*tasks)
                
                # All should succeed
                assert all(results)
                
                # Final state should be consistent
                params = await orderbook_manager.get_connection_params(connection_id)
                assert params is not None
                assert 'updated_at' in params

        @pytest.mark.asyncio
        async def test_concurrent_updates_different_connections(self, orderbook_manager):
            """Test concurrent updates to different connections."""
            connections = [
                ("conn_1", "BTCUSDT", 15, 0.25),
                ("conn_2", "ETHUSDT", 25, 0.5),
                ("conn_3", "ADAUSDT", 35, 1.0)
            ]
            
            with patch('app.services.orderbook_manager.OrderBook'):
                # Register all connections
                for conn_id, symbol, limit, rounding in connections:
                    await orderbook_manager.register_connection(conn_id, symbol, 10, 1.0)
                
                # Create concurrent update tasks
                tasks = []
                for conn_id, symbol, limit, rounding in connections:
                    task = asyncio.create_task(
                        orderbook_manager.update_connection_params(conn_id, limit=limit, rounding=rounding)
                    )
                    tasks.append(task)
                
                # Wait for all updates
                results = await asyncio.gather(*tasks)
                
                # All should succeed
                assert all(results)
                
                # Verify each connection has correct parameters
                for conn_id, symbol, limit, rounding in connections:
                    params = await orderbook_manager.get_connection_params(conn_id)
                    assert params['limit'] == limit
                    assert params['rounding'] == rounding

    class TestParameterPersistence:
        """Test parameter persistence across different operations."""

        @pytest.mark.asyncio
        async def test_parameters_survive_aggregation_calls(self, orderbook_manager):
            """Test that parameters remain consistent during aggregation calls."""
            connection_id = "test_conn"
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock()
                mock_orderbook_class.return_value = mock_orderbook
                
                # Mock aggregation service
                orderbook_manager._aggregation_service.aggregate_orderbook = AsyncMock(
                    return_value={'symbol': symbol, 'bids': [], 'asks': []}
                )
                
                # Register connection
                await orderbook_manager.register_connection(connection_id, symbol, 20, 2.0)
                
                # Call aggregation multiple times
                for _ in range(5):
                    await orderbook_manager.get_aggregated_orderbook(connection_id)
                
                # Parameters should remain unchanged
                params = await orderbook_manager.get_connection_params(connection_id)
                assert params['limit'] == 20
                assert params['rounding'] == 2.0

        @pytest.mark.asyncio
        async def test_parameters_survive_symbol_data_updates(self, orderbook_manager):
            """Test that connection parameters survive symbol data updates."""
            connection_id = "test_conn"
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook'):
                # Register connection
                await orderbook_manager.register_connection(connection_id, symbol, 15, 1.5)
                
                # Update symbol data
                symbol_data = {'pricePrecision': 2, 'quantityPrecision': 6}
                await orderbook_manager.update_symbol_data(symbol, symbol_data)
                
                # Parameters should remain unchanged
                params = await orderbook_manager.get_connection_params(connection_id)
                assert params['limit'] == 15
                assert params['rounding'] == 1.5

    class TestErrorHandling:
        """Test error handling in parameter tracking."""

        @pytest.mark.asyncio
        async def test_handle_malformed_json_message(self, connection_manager, mock_websocket):
            """Test handling malformed JSON messages."""
            connection_id = "test_conn"
            
            # Register connection
            connection_manager.connections[connection_id] = {
                'websocket': mock_websocket,
                'symbol': 'BTCUSDT',
                'stream_type': 'orderbook'
            }
            
            # Handle malformed JSON
            await connection_manager.handle_websocket_message(connection_id, "invalid json")
            
            # Should not crash and should not call any manager methods
            # This is a basic error handling test

        @pytest.mark.asyncio
        async def test_handle_missing_message_fields(self, connection_manager, mock_websocket):
            """Test handling messages with missing required fields."""
            connection_id = "test_conn"
            
            with patch.object(connection_manager, 'orderbook_manager') as mock_manager:
                # Register connection
                connection_manager.connections[connection_id] = {
                    'websocket': mock_websocket,
                    'symbol': 'BTCUSDT',
                    'stream_type': 'orderbook'
                }
                
                # Message missing limit
                message1 = {'type': 'update_params', 'rounding': 1.0}
                await connection_manager.handle_websocket_message(
                    connection_id, json.dumps(message1)
                )
                
                # Message missing rounding
                message2 = {'type': 'update_params', 'limit': 20}
                await connection_manager.handle_websocket_message(
                    connection_id, json.dumps(message2)
                )
                
                # Should handle gracefully without crashing

        @pytest.mark.asyncio
        async def test_parameter_update_with_manager_failure(self, connection_manager, mock_websocket):
            """Test behavior when orderbook manager update fails."""
            connection_id = "test_conn"
            
            with patch.object(connection_manager, 'orderbook_manager') as mock_manager:
                mock_manager.update_connection_params = AsyncMock(return_value=False)
                
                # Register connection
                connection_manager.connections[connection_id] = {
                    'websocket': mock_websocket,
                    'symbol': 'BTCUSDT',
                    'stream_type': 'orderbook'
                }
                
                # Handle parameter update
                message = {'type': 'update_params', 'limit': 20, 'rounding': 1.0}
                await connection_manager.handle_websocket_message(
                    connection_id, json.dumps(message)
                )
                
                # Should handle failure gracefully
                mock_manager.update_connection_params.assert_called_once()
                
                # Should still attempt to send response (error message)
                mock_websocket.send.assert_called()