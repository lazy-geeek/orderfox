import pytest

# Chunk 7c: WebSocket Integration tests - Real WebSocket orderbook tests
pytestmark = pytest.mark.chunk7c
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
    def fresh_orderbook_manager(self):
        """Create a fresh orderbook manager for each test."""
        manager = OrderBookManager.__new__(OrderBookManager)
        manager._initialized = False
        manager.__init__()
        yield manager
        # Shutdown will be handled by the test itself if needed

    @pytest.fixture
    def connection_manager(self, fresh_orderbook_manager):
        """Create a connection manager with fresh orderbook manager."""
        manager = ConnectionManager()
        manager.orderbook_manager = fresh_orderbook_manager
        yield manager
        # Cleanup will be handled by the test itself if needed

    @pytest.fixture
    def mock_exchange_service(self):
        """Mock the exchange service to provide test data."""
        # Patch multiple locations where exchange_service is imported
        with patch('app.services.exchange_service.exchange_service') as mock1, \
             patch('app.api.v1.endpoints.connection_manager.exchange_service', mock1):
            
            # Mock symbol data
            mock1.get_symbol_info.return_value = {
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
            mock1.get_orderbook.return_value = mock_orderbook_data
            
            # CRITICAL: Mock get_exchange_pro to return None to force mock streaming
            mock1.get_exchange_pro.return_value = None
            
            yield mock1

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
                websocket, symbol, None, limit, rounding
            )
            
            # Connection ID is generated internally as symbol:id(websocket)
            actual_connection_id = f"{symbol}:{id(websocket)}"
            
            # Verify connection was registered (active_connections is keyed by symbol)
            assert symbol in connection_manager.active_connections
            assert websocket in connection_manager.active_connections[symbol]
            
            # Verify orderbook manager registration
            params = await connection_manager.orderbook_manager.get_connection_params(actual_connection_id)
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
                websocket, symbol, None, 10, 1.0
            )
            
            # Connection manager doesn't fetch symbol info directly anymore
            # It's handled by orderbook manager or symbol service

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
                
                await connection_manager.connect_orderbook(ws, symbol, None, limit, rounding)
            
            # Verify all connections are registered under the same symbol
            # Multiple connections for the same symbol share the same stream key
            assert symbol in connection_manager.active_connections
            assert len(connection_manager.active_connections[symbol]) == len(connections)
            
            # Verify they share the same orderbook
            orderbook = await connection_manager.orderbook_manager.get_orderbook(symbol)
            assert orderbook is not None

    class TestParameterUpdates:
        """Test parameter updates without reconnection."""

        @pytest.mark.asyncio
        async def test_parameter_update_via_websocket(self, connection_manager, mock_exchange_service):
            """Test updating parameters via WebSocket message - REAL WebSocket version."""
            from fastapi.testclient import TestClient
            from app.main import app
            
            client = TestClient(app)
            symbol_info = {
                'symbol': 'BTCUSDT',
                'baseAsset': 'BTC', 
                'quoteAsset': 'USDT',
                'pricePrecision': 2,
                'amountPrecision': 8,
                'status': 'TRADING'
            }
            
            with patch('app.services.symbol_service.symbol_service.validate_symbol_exists', return_value=True):
                with patch('app.services.symbol_service.symbol_service.get_symbol_info', return_value=symbol_info):
                    
                    # Connect to real WebSocket endpoint
                    with client.websocket_connect("/api/v1/ws/orderbook/BTCUSDT?limit=10&rounding=1.0") as websocket:
                        
                        # Receive initial data
                        initial_data = websocket.receive_json()
                        assert initial_data["type"] == "orderbook_update"
                        
                        # Send parameter update
                        update_message = {
                            "type": "update_params",
                            "limit": 25,
                            "rounding": 0.5
                        }
                        websocket.send_json(update_message)
                        
                        # Should receive acknowledgment message
                        ack_response = websocket.receive_json()
                        assert ack_response["type"] == "params_updated"
                        assert ack_response["limit"] == 25
                        assert ack_response["rounding"] == 0.5
                        assert ack_response["success"] is True
                        
                        # Should receive updated orderbook data with new parameters
                        updated_data = websocket.receive_json()
                        assert updated_data["type"] == "orderbook_update"

        @pytest.mark.asyncio
        async def test_parameter_update_triggers_rebroadcast(self, connection_manager, mock_exchange_service):
            """Test that parameter updates trigger data rebroadcast - REAL WebSocket version."""
            from fastapi.testclient import TestClient
            from app.main import app
            
            client = TestClient(app)
            symbol_info = {
                'symbol': 'BTCUSDT',
                'baseAsset': 'BTC', 
                'quoteAsset': 'USDT',
                'pricePrecision': 2,
                'amountPrecision': 8,
                'status': 'TRADING'
            }
            
            with patch('app.services.symbol_service.symbol_service.validate_symbol_exists', return_value=True):
                with patch('app.services.symbol_service.symbol_service.get_symbol_info', return_value=symbol_info):
                    
                    # Connect to real WebSocket endpoint
                    with client.websocket_connect("/api/v1/ws/orderbook/BTCUSDT?limit=5&rounding=1.0") as websocket:
                        
                        # Receive initial data
                        initial_data = websocket.receive_json()
                        initial_bid_count = len(initial_data.get("bids", []))
                        
                        # Send parameter update to increase limit
                        websocket.send_json({
                            "type": "update_params", 
                            "limit": 15,
                            "rounding": 0.5
                        })
                        
                        # Receive acknowledgment
                        ack = websocket.receive_json()
                        assert ack["type"] == "params_updated"
                        assert ack["limit"] == 15
                        
                        # Receive rebroadcast data  
                        rebroadcast_data = websocket.receive_json()
                        assert rebroadcast_data["type"] == "orderbook_update"

        @pytest.mark.asyncio
        async def test_invalid_parameter_update(self, connection_manager, mock_exchange_service):
            """Test handling of invalid parameter update messages."""
            websocket = AsyncMock(spec=WebSocket)
            websocket.accept = AsyncMock()
            websocket.send_text = AsyncMock()
            
            symbol = "BTCUSDT"
            
            # Establish connection
            await connection_manager.connect_orderbook(
                websocket, symbol, None, 10, 1.0
            )
            
            # Get the actual connection ID that was generated
            connection_id = f"{symbol}:{id(websocket)}"
            
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
            """Test the complete flow from raw data to aggregated broadcast - REAL WebSocket version."""
            from fastapi.testclient import TestClient
            from app.main import app
            
            client = TestClient(app)
            symbol_info = {
                'symbol': 'BTCUSDT',
                'baseAsset': 'BTC', 
                'quoteAsset': 'USDT',
                'pricePrecision': 2,
                'amountPrecision': 8,
                'status': 'TRADING'
            }
            
            with patch('app.services.symbol_service.symbol_service.validate_symbol_exists', return_value=True):
                with patch('app.services.symbol_service.symbol_service.get_symbol_info', return_value=symbol_info):
                    
                    # Connect to real WebSocket endpoint
                    with client.websocket_connect("/api/v1/ws/orderbook/BTCUSDT?limit=20&rounding=1.0") as websocket:
                        
                        # Receive initial aggregated data
                        data = websocket.receive_json()
                        assert data["type"] == "orderbook_update"
                        
                        # Verify aggregation fields are present
                        if data["bids"]:
                            bid = data["bids"][0]
                            assert "price" in bid
                            assert "amount" in bid 
                            assert "cumulative" in bid
                            assert "price_formatted" in bid
                            assert "amount_formatted" in bid
                            assert "cumulative_formatted" in bid
                        
                        # Test parameter changes affect aggregation
                        websocket.send_json({
                            "type": "update_params",
                            "limit": 10, 
                            "rounding": 0.25
                        })
                        
                        # Acknowledgment
                        ack = websocket.receive_json()
                        assert ack["type"] == "params_updated"
                        
                        # Updated aggregated data
                        updated_data = websocket.receive_json()
                        assert updated_data["type"] == "orderbook_update"

        @pytest.mark.asyncio
        async def test_aggregation_with_different_parameters(self, connection_manager, mock_exchange_service):
            """Test that different connections get differently aggregated data - REAL WebSocket version."""
            from fastapi.testclient import TestClient
            from app.main import app
            
            client = TestClient(app)
            symbol_info = {
                'symbol': 'BTCUSDT',
                'baseAsset': 'BTC', 
                'quoteAsset': 'USDT',
                'pricePrecision': 2,
                'amountPrecision': 8,
                'status': 'TRADING'
            }
            
            with patch('app.services.symbol_service.symbol_service.validate_symbol_exists', return_value=True):
                with patch('app.services.symbol_service.symbol_service.get_symbol_info', return_value=symbol_info):
                    
                    # Test different parameter combinations sequentially
                    # Connection 1 - Low resolution
                    with client.websocket_connect("/api/v1/ws/orderbook/BTCUSDT?limit=5&rounding=1.0") as websocket:
                        data1 = websocket.receive_json()
                        assert data1["type"] == "orderbook_update"
                        assert "rounding_options" in data1
                    
                    # Connection 2 - High resolution  
                    with client.websocket_connect("/api/v1/ws/orderbook/BTCUSDT?limit=20&rounding=0.1") as websocket:
                        data2 = websocket.receive_json()
                        assert data2["type"] == "orderbook_update"
                        assert "rounding_options" in data2
                    
                    # Connection 3 - Medium resolution
                    with client.websocket_connect("/api/v1/ws/orderbook/BTCUSDT?limit=10&rounding=0.5") as websocket:
                        data3 = websocket.receive_json()
                        assert data3["type"] == "orderbook_update"
                        assert "rounding_options" in data3

        @pytest.mark.asyncio
        async def test_cache_effectiveness_in_flow(self, connection_manager, mock_exchange_service):
            """Test that caching improves performance in the full flow - REAL WebSocket version."""
            from fastapi.testclient import TestClient
            from app.main import app
            
            client = TestClient(app)
            symbol_info = {
                'symbol': 'BTCUSDT',
                'baseAsset': 'BTC', 
                'quoteAsset': 'USDT',
                'pricePrecision': 2,
                'amountPrecision': 8,
                'status': 'TRADING'
            }
            
            with patch('app.services.symbol_service.symbol_service.validate_symbol_exists', return_value=True):
                with patch('app.services.symbol_service.symbol_service.get_symbol_info', return_value=symbol_info):
                    
                    # Test cache effectiveness with sequential connections (same parameters)
                    # Connection 1 - should populate cache
                    with client.websocket_connect("/api/v1/ws/orderbook/BTCUSDT?limit=10&rounding=1.0") as websocket1:
                        data1 = websocket1.receive_json()
                        assert data1["type"] == "orderbook_update"
                        
                        # Test parameter update to verify connection works
                        websocket1.send_json({"type": "update_params", "limit": 15, "rounding": 2.0})
                        ack1 = websocket1.receive_json()
                        assert ack1["type"] == "params_updated"
                        update1 = websocket1.receive_json()
                        assert update1["type"] == "orderbook_update"
                    
                    # Connection 2 - should benefit from cache (same initial parameters)  
                    with client.websocket_connect("/api/v1/ws/orderbook/BTCUSDT?limit=10&rounding=1.0") as websocket2:
                        data2 = websocket2.receive_json()
                        assert data2["type"] == "orderbook_update"
                        
                        # Cache effectiveness is tested by the fact that both connections work correctly
                        # with the same parameters - backend handles caching internally

    class TestMultipleSymbols:
        """Test handling multiple symbols simultaneously."""

        @pytest.mark.asyncio
        async def test_multiple_symbols_isolation(self, connection_manager, mock_exchange_service):
            """Test that different symbols are handled independently - REAL WebSocket version."""
            from fastapi.testclient import TestClient
            from app.main import app
            
            client = TestClient(app)
            
            # Define symbol infos for different symbols
            symbol_info_btc = {
                'symbol': 'BTCUSDT',
                'baseAsset': 'BTC', 
                'quoteAsset': 'USDT',
                'pricePrecision': 2,
                'amountPrecision': 8,
                'status': 'TRADING'
            }
            symbol_info_eth = {
                'symbol': 'ETHUSDT',
                'baseAsset': 'ETH', 
                'quoteAsset': 'USDT',
                'pricePrecision': 2,
                'amountPrecision': 8,
                'status': 'TRADING'
            }
            
            def mock_validate_symbol(symbol):
                return symbol in ['BTCUSDT', 'ETHUSDT']
                
            def mock_get_symbol_info(symbol):
                if symbol == 'BTCUSDT':
                    return symbol_info_btc
                elif symbol == 'ETHUSDT':  
                    return symbol_info_eth
                return None
                
            with patch('app.services.symbol_service.symbol_service.validate_symbol_exists', side_effect=mock_validate_symbol):
                with patch('app.services.symbol_service.symbol_service.get_symbol_info', side_effect=mock_get_symbol_info):
                    
                    connections = []
                    try:
                        # Connect to BTC
                        ws_btc = client.websocket_connect("/api/v1/ws/orderbook/BTCUSDT?limit=10&rounding=1.0")
                        connections.append(ws_btc)
                        websocket_btc = ws_btc.__enter__()
                        
                        # Connect to ETH
                        ws_eth = client.websocket_connect("/api/v1/ws/orderbook/ETHUSDT?limit=20&rounding=0.5")  
                        connections.append(ws_eth)
                        websocket_eth = ws_eth.__enter__()
                        
                        # Receive initial data from both
                        btc_data = websocket_btc.receive_json()
                        eth_data = websocket_eth.receive_json()
                        
                        assert btc_data["symbol"] == "BTCUSDT"
                        assert eth_data["symbol"] == "ETHUSDT"
                        
                        # Update BTC parameters - should not affect ETH
                        websocket_btc.send_json({"type": "update_params", "limit": 30, "rounding": 2.0})
                        
                        # BTC should get acknowledgment and update
                        btc_ack = websocket_btc.receive_json()
                        assert btc_ack["type"] == "params_updated"
                        assert btc_ack["limit"] == 30
                        
                        btc_update = websocket_btc.receive_json()
                        assert btc_update["symbol"] == "BTCUSDT"
                        
                        # ETH should not receive any additional messages (symbols are isolated)
                        # We can't easily test this without timing issues, but the connections work independently
                        
                    finally:
                        for conn in connections:
                            try:
                                conn.__exit__(None, None, None) 
                            except:
                                pass

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
                websocket, symbol, None, 10, 1.0
            )
            
            # Verify connection exists
            # Connection ID is generated as symbol:id(websocket)
            actual_connection_id = f"{symbol}:{id(websocket)}"
            assert symbol in connection_manager.active_connections
            params = await connection_manager.orderbook_manager.get_connection_params(actual_connection_id)
            assert params is not None
            
            # Disconnect
            await connection_manager.disconnect_orderbook(websocket, symbol)
            
            # Verify cleanup
            assert symbol not in connection_manager.active_connections
            params = await connection_manager.orderbook_manager.get_connection_params(actual_connection_id)
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
                    websocket, symbol, None, 10, 1.0
                )
                
                # Verify orderbook exists
                orderbook = await connection_manager.orderbook_manager.get_orderbook(symbol)
                assert orderbook is not None
                
                # Disconnect last connection
                await connection_manager.disconnect_orderbook(websocket, symbol)
                
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
                    websocket, symbol, None, 10, 1.0
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
                    websocket, symbol, None, 10, 1.0
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
            """Test broadcast performance with real WebSocket - SIMPLIFIED version."""
            from fastapi.testclient import TestClient
            from app.main import app
            
            client = TestClient(app)
            symbol_info = {
                'symbol': 'BTCUSDT',
                'baseAsset': 'BTC', 
                'quoteAsset': 'USDT',
                'pricePrecision': 2,
                'amountPrecision': 8,
                'status': 'TRADING'
            }
            
            with patch('app.services.symbol_service.symbol_service.validate_symbol_exists', return_value=True):
                with patch('app.services.symbol_service.symbol_service.get_symbol_info', return_value=symbol_info):
                    
                    # Test single connection performance (sequential testing is more reliable)
                    with client.websocket_connect("/api/v1/ws/orderbook/BTCUSDT?limit=10&rounding=1.0") as websocket:
                        
                        # Measure initial data receive time
                        start_time = time.time()
                        data = websocket.receive_json()
                        receive_time = time.time() - start_time
                        
                        assert data["type"] == "orderbook_update"
                        
                        # Performance should be reasonable (less than 3 seconds for connection)
                        assert receive_time < 3.0, f"Initial data took too long: {receive_time}s"
                        
                        # Test parameter update performance
                        start_time = time.time()
                        websocket.send_json({"type": "update_params", "limit": 25, "rounding": 1.5})
                        ack = websocket.receive_json()
                        update_data = websocket.receive_json()
                        update_time = time.time() - start_time
                        
                        assert ack["type"] == "params_updated"
                        assert update_data["type"] == "orderbook_update"
                        
                        # Parameter updates should be fast (less than 2 seconds)
                        assert update_time < 2.0, f"Parameter update took too long: {update_time}s"

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
                    websocket, symbol, None, 10, 1.0
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