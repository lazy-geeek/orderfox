import pytest
import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

from app.main import app
from app.services.orderbook_manager import OrderBookManager
from app.api.v1.endpoints.connection_manager import ConnectionManager
from app.models.orderbook import OrderBook, OrderBookLevel


class TestOrderBookFullFlow:
    """
    Integration tests for the complete orderbook flow from CCXT Pro to frontend display.
    Tests the entire pipeline: WebSocket connection -> parameter updates -> aggregation -> broadcast.
    """

    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        return TestClient(app)

    @pytest.fixture
    async def fresh_orderbook_manager(self):
        """Create a fresh orderbook manager for each test."""
        manager = OrderBookManager.__new__(OrderBookManager)
        manager._initialized = False
        manager.__init__()
        yield manager
        await manager.shutdown()

    @pytest.fixture
    async def connection_manager(self, fresh_orderbook_manager):
        """Create a connection manager with fresh orderbook manager."""
        manager = ConnectionManager()
        manager.orderbook_manager = fresh_orderbook_manager
        yield manager
        await manager.cleanup()

    @pytest.fixture
    def mock_exchange_service(self):
        """Mock the exchange service to provide test data."""
        with patch('app.services.exchange_service.exchange_service') as mock:
            # Mock symbol data
            mock.get_symbol_info.return_value = {
                'id': 'BTCUSDT',
                'symbol': 'BTC/USDT',
                'pricePrecision': 2,
                'quantityPrecision': 6
            }
            
            # Mock orderbook data
            mock_orderbook_data = {
                'symbol': 'BTCUSDT',
                'bids': [
                    [50000.0, 1.0],
                    [49999.0, 2.0],
                    [49998.0, 3.0]
                ],
                'asks': [
                    [50001.0, 1.5],
                    [50002.0, 2.5],
                    [50003.0, 3.5]
                ],
                'timestamp': 1640995200000
            }
            mock.get_orderbook.return_value = mock_orderbook_data
            
            yield mock

    class TestWebSocketConnection:
        """Test WebSocket connection establishment and basic flow."""

        @pytest.mark.asyncio
        async def test_websocket_orderbook_connection(self, connection_manager, mock_exchange_service):
            """Test establishing WebSocket connection for orderbook."""
            # Mock WebSocket
            websocket = AsyncMock(spec=WebSocket)
            websocket.accept = AsyncMock()
            websocket.send_text = AsyncMock()
            websocket.close = AsyncMock()
            
            connection_id = "test_conn_1"
            symbol = "BTCUSDT"
            limit = 10
            rounding = 1.0
            
            # Test connection establishment
            await connection_manager.connect_orderbook(
                websocket, connection_id, symbol, limit, rounding
            )
            
            # Verify connection was registered
            assert connection_id in connection_manager.connections
            
            # Verify orderbook manager registration
            params = await connection_manager.orderbook_manager.get_connection_params(connection_id)
            assert params is not None
            assert params['symbol'] == symbol
            assert params['limit'] == limit
            assert params['rounding'] == rounding

        @pytest.mark.asyncio
        async def test_websocket_connection_with_symbol_data(self, connection_manager, mock_exchange_service):
            """Test connection with automatic symbol data population."""
            websocket = AsyncMock(spec=WebSocket)
            websocket.accept = AsyncMock()
            websocket.send_text = AsyncMock()
            
            connection_id = "test_conn_2"
            symbol = "BTCUSDT"
            
            # Connect
            await connection_manager.connect_orderbook(
                websocket, connection_id, symbol, 10, 1.0
            )
            
            # Verify symbol data was fetched and stored
            mock_exchange_service.get_symbol_info.assert_called_once_with(symbol)

        @pytest.mark.asyncio
        async def test_multiple_connections_same_symbol(self, connection_manager, mock_exchange_service):
            """Test multiple connections to the same symbol."""
            symbol = "BTCUSDT"
            connections = [
                ("conn_1", 10, 1.0),
                ("conn_2", 20, 0.5),
                ("conn_3", 50, 2.0)
            ]
            
            websockets = []
            for conn_id, limit, rounding in connections:
                ws = AsyncMock(spec=WebSocket)
                ws.accept = AsyncMock()
                ws.send_text = AsyncMock()
                websockets.append(ws)
                
                await connection_manager.connect_orderbook(ws, conn_id, symbol, limit, rounding)
            
            # Verify all connections are registered
            for conn_id, _, _ in connections:
                assert conn_id in connection_manager.connections
            
            # Verify they share the same orderbook
            orderbook = await connection_manager.orderbook_manager.get_orderbook(symbol)
            assert orderbook is not None

    class TestParameterUpdates:
        """Test parameter updates without reconnection."""

        @pytest.mark.asyncio
        async def test_parameter_update_via_websocket(self, connection_manager, mock_exchange_service):
            """Test updating parameters via WebSocket message."""
            websocket = AsyncMock(spec=WebSocket)
            websocket.accept = AsyncMock()
            websocket.send_text = AsyncMock()
            
            connection_id = "param_test_conn"
            symbol = "BTCUSDT"
            
            # Establish connection
            await connection_manager.connect_orderbook(
                websocket, connection_id, symbol, 10, 1.0
            )
            
            # Send parameter update message
            update_message = {
                'type': 'update_params',
                'limit': 25,
                'rounding': 0.5
            }
            
            await connection_manager.handle_websocket_message(
                connection_id, json.dumps(update_message)
            )
            
            # Verify parameters were updated
            params = await connection_manager.orderbook_manager.get_connection_params(connection_id)
            assert params['limit'] == 25
            assert params['rounding'] == 0.5
            
            # Verify acknowledgment was sent
            websocket.send_text.assert_called()

        @pytest.mark.asyncio
        async def test_parameter_update_triggers_rebroadcast(self, connection_manager, mock_exchange_service):
            """Test that parameter updates trigger data rebroadcast."""
            websocket = AsyncMock(spec=WebSocket)
            websocket.accept = AsyncMock()
            websocket.send_text = AsyncMock()
            
            connection_id = "rebroadcast_test"
            symbol = "BTCUSDT"
            
            # Mock orderbook with test data
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock()
                mock_snapshot = MagicMock()
                mock_snapshot.bids = [MagicMock(price=50000.0, amount=1.0)]
                mock_snapshot.asks = [MagicMock(price=50001.0, amount=1.0)]
                mock_orderbook.get_snapshot.return_value = mock_snapshot
                mock_orderbook.symbol = symbol
                mock_orderbook.timestamp = time.time() * 1000
                mock_orderbook_class.return_value = mock_orderbook
                
                # Establish connection
                await connection_manager.connect_orderbook(
                    websocket, connection_id, symbol, 10, 1.0
                )
                
                # Reset send_text calls
                websocket.send_text.reset_mock()
                
                # Send parameter update
                update_message = {
                    'type': 'update_params',
                    'limit': 20,
                    'rounding': 2.0
                }
                
                await connection_manager.handle_websocket_message(
                    connection_id, json.dumps(update_message)
                )
                
                # Verify multiple messages were sent (acknowledgment + new data)
                assert websocket.send_text.call_count >= 2

        @pytest.mark.asyncio
        async def test_invalid_parameter_update(self, connection_manager, mock_exchange_service):
            """Test handling of invalid parameter update messages."""
            websocket = AsyncMock(spec=WebSocket)
            websocket.accept = AsyncMock()
            websocket.send_text = AsyncMock()
            
            connection_id = "invalid_param_test"
            symbol = "BTCUSDT"
            
            # Establish connection
            await connection_manager.connect_orderbook(
                websocket, connection_id, symbol, 10, 1.0
            )
            
            # Get original parameters
            original_params = await connection_manager.orderbook_manager.get_connection_params(connection_id)
            
            # Send invalid parameter update
            invalid_message = {
                'type': 'update_params',
                'limit': 'invalid',  # Should be int
                'rounding': 'also_invalid'  # Should be float
            }
            
            # Should not crash
            await connection_manager.handle_websocket_message(
                connection_id, json.dumps(invalid_message)
            )
            
            # Parameters should remain unchanged
            current_params = await connection_manager.orderbook_manager.get_connection_params(connection_id)
            assert current_params['limit'] == original_params['limit']
            assert current_params['rounding'] == original_params['rounding']

    class TestAggregationFlow:
        """Test the complete aggregation flow."""

        @pytest.mark.asyncio
        async def test_full_aggregation_flow(self, connection_manager, mock_exchange_service):
            """Test the complete flow from raw data to aggregated broadcast."""
            websocket = AsyncMock(spec=WebSocket)
            websocket.accept = AsyncMock()
            websocket.send_text = AsyncMock()
            
            connection_id = "aggregation_test"
            symbol = "BTCUSDT"
            limit = 5
            rounding = 1.0
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                # Create detailed mock orderbook data
                mock_orderbook = AsyncMock()
                mock_snapshot = MagicMock()
                
                # Create realistic bid/ask data for aggregation
                mock_snapshot.bids = [
                    MagicMock(price=50000.5, amount=1.0),
                    MagicMock(price=50000.2, amount=2.0),
                    MagicMock(price=49999.8, amount=1.5),
                    MagicMock(price=49999.3, amount=2.5),
                    MagicMock(price=49998.9, amount=3.0)
                ]
                mock_snapshot.asks = [
                    MagicMock(price=50001.1, amount=1.2),
                    MagicMock(price=50001.7, amount=2.2),
                    MagicMock(price=50002.3, amount=1.8),
                    MagicMock(price=50002.9, amount=2.8),
                    MagicMock(price=50003.4, amount=3.4)
                ]
                
                mock_orderbook.get_snapshot.return_value = mock_snapshot
                mock_orderbook.symbol = symbol
                mock_orderbook.timestamp = time.time() * 1000
                mock_orderbook_class.return_value = mock_orderbook
                
                # Establish connection
                await connection_manager.connect_orderbook(
                    websocket, connection_id, symbol, limit, rounding
                )
                
                # Trigger aggregation by simulating orderbook update
                await connection_manager.broadcast_orderbook_update(symbol)
                
                # Verify data was sent to websocket
                websocket.send_text.assert_called()
                
                # Parse the sent data
                sent_calls = websocket.send_text.call_args_list
                orderbook_data = None
                
                for call in sent_calls:
                    data = json.loads(call[0][0])
                    if data.get('type') == 'orderbook_update':
                        orderbook_data = data
                        break
                
                assert orderbook_data is not None
                assert 'bids' in orderbook_data
                assert 'asks' in orderbook_data
                assert 'rounding_options' in orderbook_data
                
                # Verify aggregation occurred (should have cumulative totals)
                if orderbook_data['bids']:
                    assert 'cumulative' in orderbook_data['bids'][0]
                if orderbook_data['asks']:
                    assert 'cumulative' in orderbook_data['asks'][0]

        @pytest.mark.asyncio
        async def test_aggregation_with_different_parameters(self, connection_manager, mock_exchange_service):
            """Test that different connections get differently aggregated data."""
            symbol = "BTCUSDT"
            connections = [
                ("conn_low_res", 5, 1.0),    # Low resolution
                ("conn_high_res", 20, 0.1),  # High resolution
                ("conn_mid_res", 10, 0.5)    # Medium resolution
            ]
            
            websockets = {}
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                # Setup mock orderbook
                mock_orderbook = AsyncMock()
                mock_snapshot = MagicMock()
                mock_snapshot.bids = [MagicMock(price=50000.0 - i*0.1, amount=i+1) for i in range(50)]
                mock_snapshot.asks = [MagicMock(price=50001.0 + i*0.1, amount=i+1) for i in range(50)]
                mock_orderbook.get_snapshot.return_value = mock_snapshot
                mock_orderbook.symbol = symbol
                mock_orderbook.timestamp = time.time() * 1000
                mock_orderbook_class.return_value = mock_orderbook
                
                # Establish all connections
                for conn_id, limit, rounding in connections:
                    ws = AsyncMock(spec=WebSocket)
                    ws.accept = AsyncMock()
                    ws.send_text = AsyncMock()
                    websockets[conn_id] = ws
                    
                    await connection_manager.connect_orderbook(ws, conn_id, symbol, limit, rounding)
                
                # Trigger broadcast
                await connection_manager.broadcast_orderbook_update(symbol)
                
                # Verify all connections received data
                for conn_id in websockets:
                    websockets[conn_id].send_text.assert_called()

        @pytest.mark.asyncio
        async def test_cache_effectiveness_in_flow(self, connection_manager, mock_exchange_service):
            """Test that caching improves performance in the full flow."""
            websocket1 = AsyncMock(spec=WebSocket)
            websocket1.accept = AsyncMock()
            websocket1.send_text = AsyncMock()
            
            websocket2 = AsyncMock(spec=WebSocket)
            websocket2.accept = AsyncMock()
            websocket2.send_text = AsyncMock()
            
            symbol = "BTCUSDT"
            # Same parameters for both connections to test cache hit
            limit = 10
            rounding = 1.0
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock()
                mock_snapshot = MagicMock()
                mock_snapshot.bids = [MagicMock(price=50000.0, amount=1.0)]
                mock_snapshot.asks = [MagicMock(price=50001.0, amount=1.0)]
                mock_orderbook.get_snapshot.return_value = mock_snapshot
                mock_orderbook.symbol = symbol
                mock_orderbook.timestamp = time.time() * 1000
                mock_orderbook_class.return_value = mock_orderbook
                
                # Establish first connection
                await connection_manager.connect_orderbook(
                    websocket1, "conn_1", symbol, limit, rounding
                )
                
                # Establish second connection with same parameters
                await connection_manager.connect_orderbook(
                    websocket2, "conn_2", symbol, limit, rounding
                )
                
                # Trigger broadcast
                await connection_manager.broadcast_orderbook_update(symbol)
                
                # Both should receive data
                websocket1.send_text.assert_called()
                websocket2.send_text.assert_called()
                
                # Check cache metrics
                aggregation_service = connection_manager.orderbook_manager._aggregation_service
                metrics = await aggregation_service.get_cache_metrics()
                
                # Should have some cache activity
                assert metrics['total_requests'] > 0

    class TestMultipleSymbols:
        """Test handling multiple symbols simultaneously."""

        @pytest.mark.asyncio
        async def test_multiple_symbols_isolation(self, connection_manager, mock_exchange_service):
            """Test that different symbols are handled independently."""
            symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
            connections = {}
            
            # Setup mock for multiple symbols
            def mock_get_symbol_info(symbol):
                return {
                    'id': symbol,
                    'symbol': symbol.replace('USDT', '/USDT'),
                    'pricePrecision': 2,
                    'quantityPrecision': 6
                }
            
            mock_exchange_service.get_symbol_info.side_effect = mock_get_symbol_info
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                def create_mock_orderbook(symbol):
                    mock_orderbook = AsyncMock()
                    mock_snapshot = MagicMock()
                    base_price = 50000 if 'BTC' in symbol else 3000 if 'ETH' in symbol else 1
                    mock_snapshot.bids = [MagicMock(price=base_price, amount=1.0)]
                    mock_snapshot.asks = [MagicMock(price=base_price + 1, amount=1.0)]
                    mock_orderbook.get_snapshot.return_value = mock_snapshot
                    mock_orderbook.symbol = symbol
                    mock_orderbook.timestamp = time.time() * 1000
                    return mock_orderbook
                
                mock_orderbook_class.side_effect = create_mock_orderbook
                
                # Establish connections for each symbol
                for i, symbol in enumerate(symbols):
                    ws = AsyncMock(spec=WebSocket)
                    ws.accept = AsyncMock()
                    ws.send_text = AsyncMock()
                    connections[symbol] = ws
                    
                    await connection_manager.connect_orderbook(
                        ws, f"conn_{symbol}", symbol, 10, 1.0
                    )
                
                # Verify separate orderbooks were created
                for symbol in symbols:
                    orderbook = await connection_manager.orderbook_manager.get_orderbook(symbol)
                    assert orderbook is not None
                
                # Trigger broadcast for one symbol
                await connection_manager.broadcast_orderbook_update("BTCUSDT")
                
                # Only BTC connection should receive data
                connections["BTCUSDT"].send_text.assert_called()
                connections["ETHUSDT"].send_text.assert_not_called()
                connections["ADAUSDT"].send_text.assert_not_called()

    class TestConnectionCleanup:
        """Test connection cleanup and resource management."""

        @pytest.mark.asyncio
        async def test_connection_disconnect_cleanup(self, connection_manager, mock_exchange_service):
            """Test that disconnecting cleans up resources properly."""
            websocket = AsyncMock(spec=WebSocket)
            websocket.accept = AsyncMock()
            websocket.send_text = AsyncMock()
            
            connection_id = "cleanup_test"
            symbol = "BTCUSDT"
            
            # Establish connection
            await connection_manager.connect_orderbook(
                websocket, connection_id, symbol, 10, 1.0
            )
            
            # Verify connection exists
            assert connection_id in connection_manager.connections
            params = await connection_manager.orderbook_manager.get_connection_params(connection_id)
            assert params is not None
            
            # Disconnect
            await connection_manager.disconnect_client(connection_id)
            
            # Verify cleanup
            assert connection_id not in connection_manager.connections
            params = await connection_manager.orderbook_manager.get_connection_params(connection_id)
            assert params is None

        @pytest.mark.asyncio
        async def test_last_connection_removes_orderbook(self, connection_manager, mock_exchange_service):
            """Test that removing the last connection removes the orderbook."""
            websocket = AsyncMock(spec=WebSocket)
            websocket.accept = AsyncMock()
            websocket.send_text = AsyncMock()
            
            connection_id = "last_conn_test"
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook'):
                # Establish connection
                await connection_manager.connect_orderbook(
                    websocket, connection_id, symbol, 10, 1.0
                )
                
                # Verify orderbook exists
                orderbook = await connection_manager.orderbook_manager.get_orderbook(symbol)
                assert orderbook is not None
                
                # Disconnect last connection
                await connection_manager.disconnect_client(connection_id)
                
                # Orderbook should be removed (non-persistent mode)
                orderbook = await connection_manager.orderbook_manager.get_orderbook(symbol)
                assert orderbook is None

    class TestErrorHandling:
        """Test error handling in the full flow."""

        @pytest.mark.asyncio
        async def test_websocket_error_handling(self, connection_manager, mock_exchange_service):
            """Test handling of WebSocket errors."""
            websocket = AsyncMock(spec=WebSocket)
            websocket.accept = AsyncMock()
            websocket.send_text = AsyncMock(side_effect=Exception("WebSocket error"))
            
            connection_id = "error_test"
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock()
                mock_orderbook_class.return_value = mock_orderbook
                
                # Establish connection
                await connection_manager.connect_orderbook(
                    websocket, connection_id, symbol, 10, 1.0
                )
                
                # Trigger broadcast (should handle send error gracefully)
                try:
                    await connection_manager.broadcast_orderbook_update(symbol)
                except Exception as e:
                    pytest.fail(f"Broadcast should handle WebSocket errors gracefully: {e}")

        @pytest.mark.asyncio
        async def test_aggregation_error_handling(self, connection_manager, mock_exchange_service):
            """Test handling of aggregation errors."""
            websocket = AsyncMock(spec=WebSocket)
            websocket.accept = AsyncMock()
            websocket.send_text = AsyncMock()
            
            connection_id = "agg_error_test"
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock()
                # Make aggregation fail
                mock_orderbook.get_snapshot.side_effect = Exception("Aggregation error")
                mock_orderbook_class.return_value = mock_orderbook
                
                # Establish connection
                await connection_manager.connect_orderbook(
                    websocket, connection_id, symbol, 10, 1.0
                )
                
                # Trigger broadcast (should handle aggregation error gracefully)
                try:
                    await connection_manager.broadcast_orderbook_update(symbol)
                except Exception as e:
                    pytest.fail(f"Broadcast should handle aggregation errors gracefully: {e}")

    class TestPerformanceCharacteristics:
        """Test performance characteristics of the full flow."""

        @pytest.mark.asyncio
        async def test_broadcast_performance(self, connection_manager, mock_exchange_service):
            """Test broadcast performance with multiple connections."""
            symbol = "BTCUSDT"
            num_connections = 10
            websockets = []
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock()
                mock_snapshot = MagicMock()
                mock_snapshot.bids = [MagicMock(price=50000.0, amount=1.0)]
                mock_snapshot.asks = [MagicMock(price=50001.0, amount=1.0)]
                mock_orderbook.get_snapshot.return_value = mock_snapshot
                mock_orderbook.symbol = symbol
                mock_orderbook.timestamp = time.time() * 1000
                mock_orderbook_class.return_value = mock_orderbook
                
                # Establish multiple connections
                for i in range(num_connections):
                    ws = AsyncMock(spec=WebSocket)
                    ws.accept = AsyncMock()
                    ws.send_text = AsyncMock()
                    websockets.append(ws)
                    
                    await connection_manager.connect_orderbook(
                        ws, f"perf_conn_{i}", symbol, 10, 1.0
                    )
                
                # Measure broadcast time
                start_time = time.time()
                await connection_manager.broadcast_orderbook_update(symbol)
                broadcast_time = time.time() - start_time
                
                # Verify all connections received data
                for ws in websockets:
                    ws.send_text.assert_called()
                
                # Performance should be reasonable (less than 100ms for 10 connections)
                assert broadcast_time < 0.1, f"Broadcast took too long: {broadcast_time}s"

        @pytest.mark.asyncio
        async def test_memory_usage_stability(self, connection_manager, mock_exchange_service):
            """Test that memory usage remains stable over multiple operations."""
            websocket = AsyncMock(spec=WebSocket)
            websocket.accept = AsyncMock()
            websocket.send_text = AsyncMock()
            
            connection_id = "memory_test"
            symbol = "BTCUSDT"
            
            with patch('app.services.orderbook_manager.OrderBook') as mock_orderbook_class:
                mock_orderbook = AsyncMock()
                mock_snapshot = MagicMock()
                mock_snapshot.bids = [MagicMock(price=50000.0, amount=1.0)]
                mock_snapshot.asks = [MagicMock(price=50001.0, amount=1.0)]
                mock_orderbook.get_snapshot.return_value = mock_snapshot
                mock_orderbook.symbol = symbol
                mock_orderbook.timestamp = time.time() * 1000
                mock_orderbook_class.return_value = mock_orderbook
                
                # Establish connection
                await connection_manager.connect_orderbook(
                    websocket, connection_id, symbol, 10, 1.0
                )
                
                # Perform many operations
                for i in range(100):
                    # Update parameters
                    update_message = {
                        'type': 'update_params',
                        'limit': 10 + (i % 5),
                        'rounding': 1.0 + (i % 3) * 0.5
                    }
                    await connection_manager.handle_websocket_message(
                        connection_id, json.dumps(update_message)
                    )
                    
                    # Trigger broadcast
                    await connection_manager.broadcast_orderbook_update(symbol)
                
                # Check cache size hasn't grown excessively
                aggregation_service = connection_manager.orderbook_manager._aggregation_service
                metrics = await aggregation_service.get_cache_metrics()
                
                # Cache should be bounded
                assert metrics['cache_size'] < 200  # Reasonable upper bound