"""
Integration tests for WebSocket order book flow with backend aggregation
"""

import asyncio
import pytest
import json
import time
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

from app.main import app
from app.services.orderbook_processor import OrderBookProcessor, AggregatedOrderBook, OrderBookLevel
from app.services.delta_update_service import DeltaUpdateService
from app.services.batch_update_service import BatchUpdateService
from app.services.message_serialization_service import MessageSerializationService


@pytest.fixture
def test_client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_depth_cache_service():
    """Create mock depth cache service."""
    with patch('app.api.v1.endpoints.connection_manager.depth_cache_service') as mock:
        mock.get_order_book_data.return_value = {
            'bids': [[100.0, 1.5], [99.0, 2.0], [98.0, 1.0]],
            'asks': [[101.0, 1.0], [102.0, 1.5], [103.0, 2.0]],
            'symbol': 'BTCUSDT',
            'timestamp': int(time.time() * 1000)
        }
        yield mock


@pytest.fixture
def sample_order_book_data():
    """Create sample order book data."""
    return {
        'bids': [[100.0, 1.5], [99.0, 2.0], [98.0, 1.0]],
        'asks': [[101.0, 1.0], [102.0, 1.5], [103.0, 2.0]],
        'symbol': 'BTCUSDT',
        'timestamp': int(time.time() * 1000)
    }


class TestWebSocketOrderBookFlow:
    """Integration tests for WebSocket order book flow."""

    @pytest.mark.asyncio
    async def test_websocket_connection_with_aggregation(self, test_client, mock_depth_cache_service):
        """Test WebSocket connection with backend aggregation enabled."""
        with test_client.websocket_connect(
            "/api/v1/ws/orderbook?symbol=BTCUSDT&aggregate=true&rounding=1.0&use_depth_cache=true"
        ) as websocket:
            # Should receive initial order book data
            data = websocket.receive_json()
            
            assert data['type'] == 'orderbook_update'
            assert data['symbol'] == 'BTCUSDT'
            assert data['aggregated'] is True
            assert data['rounding'] == 1.0
            assert 'bids' in data
            assert 'asks' in data

    @pytest.mark.asyncio
    async def test_websocket_connection_without_aggregation(self, test_client, mock_depth_cache_service):
        """Test WebSocket connection without backend aggregation."""
        with test_client.websocket_connect(
            "/api/v1/ws/orderbook?symbol=BTCUSDT&aggregate=false"
        ) as websocket:
            # Should receive raw order book data
            data = websocket.receive_json()
            
            assert data['type'] == 'orderbook_update'
            assert data['symbol'] == 'BTCUSDT'
            assert data.get('aggregated', False) is False

    @pytest.mark.asyncio
    async def test_parameter_validation(self, test_client):
        """Test WebSocket parameter validation."""
        # Invalid rounding value
        with pytest.raises(Exception):
            with test_client.websocket_connect(
                "/api/v1/ws/orderbook?symbol=BTCUSDT&aggregate=true&rounding=-1.0"
            ) as websocket:
                pass

    @pytest.mark.asyncio
    async def test_multiple_concurrent_connections(self, test_client, mock_depth_cache_service):
        """Test multiple concurrent WebSocket connections."""
        connections = []
        
        try:
            # Create multiple connections
            for i in range(3):
                conn = test_client.websocket_connect(
                    f"/api/v1/ws/orderbook?symbol=BTCUSDT&aggregate=true&rounding={i+1}.0"
                )
                connections.append(conn.__enter__())
            
            # Each should receive data
            for i, websocket in enumerate(connections):
                data = websocket.receive_json()
                assert data['symbol'] == 'BTCUSDT'
                assert data['rounding'] == float(i + 1)
                
        finally:
            # Clean up connections
            for conn in connections:
                try:
                    conn.__exit__(None, None, None)
                except:
                    pass

    @pytest.mark.asyncio
    async def test_connection_cleanup_on_disconnect(self, test_client, mock_depth_cache_service):
        """Test that connections are properly cleaned up on disconnect."""
        # This test would need access to internal connection manager state
        # For now, we'll test that disconnection doesn't cause errors
        
        with test_client.websocket_connect(
            "/api/v1/ws/orderbook?symbol=BTCUSDT&aggregate=true&rounding=1.0"
        ) as websocket:
            data = websocket.receive_json()
            assert data['symbol'] == 'BTCUSDT'
        
        # Connection should be cleanly closed


class TestOrderBookProcessorIntegration:
    """Integration tests for OrderBookProcessor with real data."""

    @pytest.fixture
    def processor(self):
        """Create OrderBookProcessor instance."""
        return OrderBookProcessor()

    def test_aggregation_integration(self, processor, sample_order_book_data):
        """Test order book aggregation with real data structure."""
        aggregated = processor.aggregate_order_book(
            sample_order_book_data,
            rounding=1.0,
            depth=10
        )
        
        assert isinstance(aggregated, AggregatedOrderBook)
        assert aggregated.symbol == 'BTCUSDT'
        assert aggregated.rounding == 1.0
        assert len(aggregated.bids) <= 10
        assert len(aggregated.asks) <= 10
        
        # Verify bids are sorted descending
        bid_prices = [bid.price for bid in aggregated.bids]
        assert bid_prices == sorted(bid_prices, reverse=True)
        
        # Verify asks are sorted ascending
        ask_prices = [ask.price for ask in aggregated.asks]
        assert ask_prices == sorted(ask_prices)

    def test_different_rounding_values(self, processor, sample_order_book_data):
        """Test aggregation with different rounding values."""
        for rounding in [0.1, 1.0, 10.0]:
            aggregated = processor.aggregate_order_book(
                sample_order_book_data,
                rounding=rounding,
                depth=10
            )
            
            assert aggregated.rounding == rounding
            
            # Verify all prices are properly rounded
            for bid in aggregated.bids:
                assert bid.price % rounding == 0
            for ask in aggregated.asks:
                assert ask.price % rounding == 0


class TestDeltaUpdateIntegration:
    """Integration tests for delta update flow."""

    @pytest.fixture
    def delta_service(self):
        """Create DeltaUpdateService instance."""
        return DeltaUpdateService()

    @pytest.fixture
    def processor(self):
        """Create OrderBookProcessor instance."""
        return OrderBookProcessor()

    def test_full_delta_flow(self, delta_service, processor, sample_order_book_data):
        """Test complete delta update flow."""
        # Register connection
        conn_id = delta_service.register_connection("ws123", "BTCUSDT", 1.0)
        
        # Process first order book
        aggregated1 = processor.aggregate_order_book(sample_order_book_data, rounding=1.0, depth=10)
        delta1 = delta_service.compute_delta(conn_id, aggregated1)
        
        # Should be full snapshot
        assert delta1.full_snapshot is True
        assert len(delta1.bids) == len(aggregated1.bids)
        
        # Modify data
        modified_data = sample_order_book_data.copy()
        modified_data['bids'][0][1] = 2.5  # Change amount
        
        # Process second order book
        aggregated2 = processor.aggregate_order_book(modified_data, rounding=1.0, depth=10)
        delta2 = delta_service.compute_delta(conn_id, aggregated2)
        
        # Should be delta update
        assert delta2.full_snapshot is False
        assert len(delta2.bids) == 1  # Only one change
        assert delta2.bids[0].operation == "update"


class TestBatchUpdateIntegration:
    """Integration tests for batch update flow."""

    @pytest.fixture
    def batch_service(self):
        """Create BatchUpdateService instance."""
        from app.services.batch_update_service import BatchConfig
        config = BatchConfig(max_batch_size=3, max_batch_delay_ms=50)
        return BatchUpdateService(config)

    @pytest.fixture
    def mock_send_callback(self):
        """Create mock send callback."""
        return Mock()

    def test_batch_accumulation_and_sending(self, batch_service, mock_send_callback, sample_order_book_data):
        """Test batch accumulation and sending."""
        batch_service.set_send_callback(mock_send_callback)
        conn_id = "test_conn"
        batch_service.register_connection(conn_id)
        
        # Add multiple updates
        for i in range(5):
            batch_service.add_update(conn_id, sample_order_book_data)
        
        # Force flush to ensure processing
        batch_service.force_flush(conn_id)
        
        # Should have called send callback
        assert mock_send_callback.called
        call_args = mock_send_callback.call_args[0]
        assert call_args[0] == conn_id
        assert len(call_args[1]) > 0  # Should have batched updates


class TestMessageSerializationIntegration:
    """Integration tests for message serialization."""

    @pytest.fixture
    def serialization_service(self):
        """Create MessageSerializationService instance."""
        return MessageSerializationService()

    @pytest.fixture
    def processor(self):
        """Create OrderBookProcessor instance."""
        return OrderBookProcessor()

    def test_serialize_aggregated_orderbook(self, serialization_service, processor, sample_order_book_data):
        """Test serializing aggregated order book."""
        aggregated = processor.aggregate_order_book(sample_order_book_data, rounding=1.0, depth=10)
        
        serialized, headers = serialization_service.serialize(aggregated)
        
        assert isinstance(serialized, bytes)
        assert headers["Content-Type"] == "application/json"
        
        # Verify can deserialize
        deserialized = serialization_service.deserialize(
            serialized,
            serialization_service.preferred_format,
            serialization_service.preferred_compression
        )
        
        assert deserialized["type"] == "orderbook_update"
        assert deserialized["symbol"] == sample_order_book_data["symbol"]

    def test_compression_with_real_data(self, serialization_service, processor, sample_order_book_data):
        """Test compression effectiveness with real order book data."""
        from app.services.message_serialization_service import CompressionMethod
        
        # Create large order book
        large_data = sample_order_book_data.copy()
        large_data['bids'] = [[100.0 - i*0.1, 1.0] for i in range(100)]
        large_data['asks'] = [[101.0 + i*0.1, 1.0] for i in range(100)]
        
        aggregated = processor.aggregate_order_book(large_data, rounding=0.1, depth=100)
        
        # Test different compression methods
        uncompressed, _ = serialization_service.serialize(aggregated, compression=CompressionMethod.NONE)
        gzip_compressed, _ = serialization_service.serialize(aggregated, compression=CompressionMethod.GZIP)
        zlib_compressed, _ = serialization_service.serialize(aggregated, compression=CompressionMethod.ZLIB)
        
        # Compression should reduce size significantly
        assert len(gzip_compressed) < len(uncompressed) * 0.8
        assert len(zlib_compressed) < len(uncompressed) * 0.8


class TestEndToEndFlow:
    """End-to-end integration tests."""

    @pytest.fixture
    def services(self):
        """Create all services for end-to-end testing."""
        from app.services.batch_update_service import BatchConfig
        
        return {
            'processor': OrderBookProcessor(),
            'delta_service': DeltaUpdateService(),
            'batch_service': BatchUpdateService(BatchConfig(max_batch_size=5)),
            'serialization_service': MessageSerializationService()
        }

    def test_complete_orderbook_pipeline(self, services, sample_order_book_data):
        """Test complete order book processing pipeline."""
        processor = services['processor']
        delta_service = services['delta_service']
        batch_service = services['batch_service']
        serialization_service = services['serialization_service']
        
        # Set up services
        conn_id = delta_service.register_connection("ws123", "BTCUSDT", 1.0)
        batch_service.register_connection("ws123")
        
        sent_messages = []
        def capture_messages(connection_id, messages):
            sent_messages.extend(messages)
        
        batch_service.set_send_callback(capture_messages)
        
        # Process order book data
        aggregated = processor.aggregate_order_book(sample_order_book_data, rounding=1.0, depth=10)
        delta = delta_service.compute_delta(conn_id, aggregated)
        
        if delta:
            batch_service.add_update("ws123", delta)
            batch_service.force_flush("ws123")
        
        # Verify messages were sent
        assert len(sent_messages) > 0
        
        # Verify can serialize the messages
        for message in sent_messages:
            serialized, headers = serialization_service.serialize(message)
            assert isinstance(serialized, bytes)
            assert len(serialized) > 0

    def test_performance_under_load(self, services, sample_order_book_data):
        """Test system performance under simulated load."""
        processor = services['processor']
        delta_service = services['delta_service']
        
        # Register multiple connections
        connections = []
        for i in range(10):
            conn_id = delta_service.register_connection(f"ws{i}", "BTCUSDT", 1.0)
            connections.append(conn_id)
        
        # Process multiple updates
        start_time = time.time()
        
        for i in range(100):
            # Slightly modify data each time
            modified_data = sample_order_book_data.copy()
            modified_data['bids'][0][1] = 1.5 + (i * 0.01)
            
            aggregated = processor.aggregate_order_book(modified_data, rounding=1.0, depth=10)
            
            # Send to all connections
            for conn_id in connections:
                delta_service.compute_delta(conn_id, aggregated)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should process reasonably quickly (less than 1 second for this load)
        assert processing_time < 1.0
        
        # Verify service stats
        stats = delta_service.get_service_stats()
        assert stats['total_connections'] == 10
        assert stats['global_sequence_id'] > 0