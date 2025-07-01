"""
Unit tests for BatchUpdateService
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, call

from app.services.batch_update_service import (
    BatchUpdateService, 
    BatchConfig, 
    PendingUpdate,
    BatchStats
)
from app.services.orderbook_processor import AggregatedOrderBook, OrderBookLevel
from app.services.delta_update_service import OrderBookDelta, DeltaLevel


class TestBatchUpdateService:
    """Test cases for BatchUpdateService."""

    @pytest.fixture
    def batch_config(self):
        """Create test batch configuration."""
        return BatchConfig(
            max_batch_size=5,
            max_batch_delay_ms=50.0,
            min_batch_delay_ms=5.0,
            max_queue_size=20
        )

    @pytest.fixture
    def batch_service(self, batch_config):
        """Create BatchUpdateService instance."""
        return BatchUpdateService(batch_config)

    @pytest.fixture
    def mock_callback(self):
        """Create mock send callback."""
        return Mock()

    @pytest.fixture
    def sample_orderbook(self):
        """Create sample aggregated order book."""
        return AggregatedOrderBook(
            bids=[
                OrderBookLevel(price=100.0, amount=1.5),
                OrderBookLevel(price=99.0, amount=2.0)
            ],
            asks=[
                OrderBookLevel(price=101.0, amount=1.0),
                OrderBookLevel(price=102.0, amount=1.5)
            ],
            symbol="BTCUSDT",
            rounding=1.0,
            timestamp=int(time.time() * 1000),
            source="test",
            aggregated=True,
            depth=10
        )

    @pytest.fixture
    def sample_delta(self):
        """Create sample order book delta."""
        return OrderBookDelta(
            bids=[DeltaLevel(price=100.0, amount=2.0, operation="update")],
            asks=[DeltaLevel(price=101.0, amount=0.0, operation="remove")],
            symbol="BTCUSDT",
            rounding=1.0,
            timestamp=int(time.time() * 1000),
            sequence_id=1
        )

    def test_initialization(self, batch_config):
        """Test service initialization."""
        service = BatchUpdateService(batch_config)
        
        assert service.config == batch_config
        assert len(service.update_queues) == 0
        assert len(service.batch_timers) == 0
        assert len(service.active_connections) == 0
        assert service.send_callback is None

    def test_set_send_callback(self, batch_service, mock_callback):
        """Test setting send callback."""
        batch_service.set_send_callback(mock_callback)
        assert batch_service.send_callback == mock_callback

    def test_register_connection(self, batch_service):
        """Test connection registration."""
        conn_id = "test_conn"
        batch_service.register_connection(conn_id)
        
        assert conn_id in batch_service.active_connections
        assert conn_id in batch_service.update_queues
        assert len(batch_service.update_queues[conn_id]) == 0

    def test_unregister_connection(self, batch_service):
        """Test connection unregistration."""
        conn_id = "test_conn"
        batch_service.register_connection(conn_id)
        batch_service.unregister_connection(conn_id)
        
        assert conn_id not in batch_service.active_connections
        assert conn_id not in batch_service.update_queues
        assert conn_id not in batch_service.batch_timers

    def test_add_update_success(self, batch_service, sample_orderbook):
        """Test successful update addition."""
        conn_id = "test_conn"
        batch_service.register_connection(conn_id)
        
        result = batch_service.add_update(conn_id, sample_orderbook)
        
        assert result is True
        assert len(batch_service.update_queues[conn_id]) == 1
        assert batch_service.stats.total_updates_received == 1

    def test_add_update_unregistered_connection(self, batch_service, sample_orderbook):
        """Test adding update to unregistered connection."""
        result = batch_service.add_update("unknown_conn", sample_orderbook)
        
        assert result is False
        assert batch_service.stats.total_updates_received == 0

    def test_queue_overflow_handling(self, batch_service, sample_orderbook):
        """Test queue overflow handling."""
        conn_id = "test_conn"
        batch_service.register_connection(conn_id)
        
        # Fill queue beyond max size
        max_size = batch_service.config.max_queue_size
        for i in range(max_size + 5):
            batch_service.add_update(conn_id, sample_orderbook, priority=i)
        
        # Queue should be at max size
        assert len(batch_service.update_queues[conn_id]) == max_size
        assert batch_service.stats.queue_overflows == 5

    def test_batch_processing_max_size_trigger(self, batch_service, mock_callback, sample_orderbook):
        """Test batch processing triggered by max size."""
        conn_id = "test_conn"
        batch_service.register_connection(conn_id)
        batch_service.set_send_callback(mock_callback)
        
        # Add updates to trigger immediate processing
        max_size = batch_service.config.max_batch_size
        for i in range(max_size):
            batch_service.add_update(conn_id, sample_orderbook)
        
        # Process should trigger immediately
        time.sleep(0.1)  # Allow processing to complete
        
        assert batch_service.stats.total_batches_sent >= 1
        mock_callback.assert_called()

    def test_get_queue_stats_single_connection(self, batch_service, sample_orderbook):
        """Test getting queue stats for single connection."""
        conn_id = "test_conn"
        batch_service.register_connection(conn_id)
        batch_service.add_update(conn_id, sample_orderbook)
        
        stats = batch_service.get_queue_stats(conn_id)
        
        assert stats["connection_id"] == conn_id
        assert stats["queue_size"] == 1
        assert "oldest_update_age_ms" in stats

    def test_get_queue_stats_all_connections(self, batch_service, sample_orderbook):
        """Test getting queue stats for all connections."""
        conn1, conn2 = "conn1", "conn2"
        batch_service.register_connection(conn1)
        batch_service.register_connection(conn2)
        batch_service.add_update(conn1, sample_orderbook)
        batch_service.add_update(conn2, sample_orderbook)
        
        stats = batch_service.get_queue_stats()
        
        assert stats["total_connections"] == 2
        assert stats["total_queued_updates"] == 2
        assert len(stats["connections"]) == 2

    def test_get_performance_stats(self, batch_service, mock_callback, sample_orderbook):
        """Test getting performance statistics."""
        conn_id = "test_conn"
        batch_service.register_connection(conn_id)
        batch_service.set_send_callback(mock_callback)
        
        # Add some updates and process them
        for i in range(10):
            batch_service.add_update(conn_id, sample_orderbook)
        
        time.sleep(0.1)  # Allow processing
        
        stats = batch_service.get_performance_stats()
        
        assert "uptime_seconds" in stats
        assert stats["total_updates_received"] == 10
        assert "updates_per_second" in stats
        assert "batching_efficiency" in stats

    def test_force_flush_single_connection(self, batch_service, mock_callback, sample_orderbook):
        """Test force flushing single connection."""
        conn_id = "test_conn"
        batch_service.register_connection(conn_id)
        batch_service.set_send_callback(mock_callback)
        batch_service.add_update(conn_id, sample_orderbook)
        
        batch_service.force_flush(conn_id)
        
        assert len(batch_service.update_queues[conn_id]) == 0
        mock_callback.assert_called()

    def test_force_flush_all_connections(self, batch_service, mock_callback, sample_orderbook):
        """Test force flushing all connections."""
        conn1, conn2 = "conn1", "conn2"
        batch_service.register_connection(conn1)
        batch_service.register_connection(conn2)
        batch_service.set_send_callback(mock_callback)
        batch_service.add_update(conn1, sample_orderbook)
        batch_service.add_update(conn2, sample_orderbook)
        
        batch_service.force_flush()
        
        assert len(batch_service.update_queues[conn1]) == 0
        assert len(batch_service.update_queues[conn2]) == 0
        assert mock_callback.call_count == 2

    def test_update_config(self, batch_service):
        """Test updating batch configuration."""
        new_config = BatchConfig(
            max_batch_size=10,
            max_batch_delay_ms=100.0,
            min_batch_delay_ms=10.0,
            max_queue_size=50
        )
        
        batch_service.update_config(new_config)
        
        assert batch_service.config == new_config

    def test_reset_stats(self, batch_service, sample_orderbook):
        """Test resetting statistics."""
        conn_id = "test_conn"
        batch_service.register_connection(conn_id)
        batch_service.add_update(conn_id, sample_orderbook)
        
        # Verify stats exist
        assert batch_service.stats.total_updates_received > 0
        
        batch_service.reset_stats()
        
        # Verify stats reset
        assert batch_service.stats.total_updates_received == 0
        assert batch_service.stats.total_batches_sent == 0

    @pytest.mark.asyncio
    async def test_background_tasks_lifecycle(self, batch_service):
        """Test starting and stopping background tasks."""
        # Start background tasks
        await batch_service.start_background_tasks()
        
        assert batch_service.cleanup_task is not None
        assert batch_service.stats_task is not None
        assert not batch_service.cleanup_task.done()
        assert not batch_service.stats_task.done()
        
        # Stop background tasks
        await batch_service.stop_background_tasks()
        
        assert batch_service.cleanup_task is None
        assert batch_service.stats_task is None

    def test_batch_size_calculation(self, batch_service, mock_callback, sample_orderbook):
        """Test batch size calculations in statistics."""
        conn_id = "test_conn"
        batch_service.register_connection(conn_id)
        batch_service.set_send_callback(mock_callback)
        
        # Add different batch sizes
        batch_service.add_update(conn_id, sample_orderbook)
        batch_service.force_flush(conn_id)
        
        for i in range(3):
            batch_service.add_update(conn_id, sample_orderbook)
        batch_service.force_flush(conn_id)
        
        stats = batch_service.get_performance_stats()
        
        assert stats["total_batches_sent"] == 2
        assert stats["total_updates_batched"] == 4
        assert stats["avg_batch_size"] == 2.0  # (1 + 3) / 2

    def test_error_handling_in_callback(self, batch_service, sample_orderbook):
        """Test error handling when callback fails."""
        conn_id = "test_conn"
        batch_service.register_connection(conn_id)
        
        # Set callback that raises exception
        def failing_callback(conn_id, updates):
            raise Exception("Callback failed")
        
        batch_service.set_send_callback(failing_callback)
        batch_service.add_update(conn_id, sample_orderbook)
        batch_service.force_flush(conn_id)
        
        # Should not crash, error should be logged
        assert len(batch_service.update_queues[conn_id]) == 0