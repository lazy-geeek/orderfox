"""
Unit tests for DeltaUpdateService
"""

import pytest
import time
from unittest.mock import Mock

from app.services.delta_update_service import (
    DeltaUpdateService,
    DeltaLevel,
    OrderBookDelta,
    ConnectionState
)
from app.services.orderbook_processor import AggregatedOrderBook, OrderBookLevel


class TestDeltaUpdateService:
    """Test cases for DeltaUpdateService."""

    @pytest.fixture
    def delta_service(self):
        """Create DeltaUpdateService instance."""
        return DeltaUpdateService(full_snapshot_interval=60.0)

    @pytest.fixture
    def sample_orderbook_v1(self):
        """Create first version of sample order book."""
        return AggregatedOrderBook(
            bids=[
                OrderBookLevel(price=100.0, amount=1.5),
                OrderBookLevel(price=99.0, amount=2.0),
                OrderBookLevel(price=98.0, amount=1.0)
            ],
            asks=[
                OrderBookLevel(price=101.0, amount=1.0),
                OrderBookLevel(price=102.0, amount=1.5),
                OrderBookLevel(price=103.0, amount=2.0)
            ],
            symbol="BTCUSDT",
            rounding=1.0,
            timestamp=int(time.time() * 1000),
            source="test",
            aggregated=True,
            depth=10
        )

    @pytest.fixture
    def sample_orderbook_v2(self):
        """Create second version with changes."""
        return AggregatedOrderBook(
            bids=[
                OrderBookLevel(price=100.0, amount=2.0),  # Updated amount
                OrderBookLevel(price=99.0, amount=2.0),   # Same
                OrderBookLevel(price=97.0, amount=1.5)    # New level (98.0 removed)
            ],
            asks=[
                OrderBookLevel(price=101.0, amount=1.0),  # Same
                OrderBookLevel(price=102.0, amount=0.5),  # Updated amount
                OrderBookLevel(price=104.0, amount=1.0)   # New level (103.0 removed)
            ],
            symbol="BTCUSDT",
            rounding=1.0,
            timestamp=int(time.time() * 1000),
            source="test",
            aggregated=True,
            depth=10
        )

    def test_initialization(self):
        """Test service initialization."""
        service = DeltaUpdateService(full_snapshot_interval=120.0)
        
        assert len(service.connection_states) == 0
        assert service.full_snapshot_interval == 120.0
        assert service.global_sequence_id == 0

    def test_generate_connection_id(self, delta_service):
        """Test connection ID generation."""
        conn_id = delta_service._generate_connection_id("ws123", "BTCUSDT", 1.0)
        expected = "ws123:BTCUSDT:1.0"
        
        assert conn_id == expected

    def test_register_connection(self, delta_service):
        """Test connection registration."""
        conn_id = delta_service.register_connection("ws123", "BTCUSDT", 1.0)
        expected_id = "ws123:BTCUSDT:1.0"
        
        assert conn_id == expected_id
        assert conn_id in delta_service.connection_states
        
        state = delta_service.connection_states[conn_id]
        assert len(state.last_sent_bids) == 0
        assert len(state.last_sent_asks) == 0
        assert state.sequence_id == 0

    def test_unregister_connection(self, delta_service):
        """Test connection unregistration."""
        conn_id = delta_service.register_connection("ws123", "BTCUSDT", 1.0)
        delta_service.unregister_connection(conn_id)
        
        assert conn_id not in delta_service.connection_states

    def test_first_delta_is_full_snapshot(self, delta_service, sample_orderbook_v1):
        """Test that first delta is always a full snapshot."""
        conn_id = delta_service.register_connection("ws123", "BTCUSDT", 1.0)
        
        delta = delta_service.compute_delta(conn_id, sample_orderbook_v1)
        
        assert delta is not None
        assert delta.full_snapshot is True
        assert len(delta.bids) == 3
        assert len(delta.asks) == 3
        
        # All operations should be "add"
        for bid in delta.bids:
            assert bid.operation == "add"
        for ask in delta.asks:
            assert ask.operation == "add"

    def test_subsequent_delta_computation(self, delta_service, sample_orderbook_v1, sample_orderbook_v2):
        """Test delta computation between two order book states."""
        conn_id = delta_service.register_connection("ws123", "BTCUSDT", 1.0)
        
        # Send first full snapshot
        delta1 = delta_service.compute_delta(conn_id, sample_orderbook_v1)
        assert delta1.full_snapshot is True
        
        # Send delta update
        delta2 = delta_service.compute_delta(conn_id, sample_orderbook_v2)
        
        assert delta2 is not None
        assert delta2.full_snapshot is False
        
        # Verify bid changes
        bid_changes = {level.price: level for level in delta2.bids}
        assert 100.0 in bid_changes  # Updated
        assert bid_changes[100.0].operation == "update"
        assert bid_changes[100.0].amount == 2.0
        
        assert 98.0 in bid_changes   # Removed
        assert bid_changes[98.0].operation == "remove"
        
        assert 97.0 in bid_changes   # Added
        assert bid_changes[97.0].operation == "add"
        assert bid_changes[97.0].amount == 1.5
        
        # Verify ask changes
        ask_changes = {level.price: level for level in delta2.asks}
        assert 102.0 in ask_changes  # Updated
        assert ask_changes[102.0].operation == "update"
        assert ask_changes[102.0].amount == 0.5
        
        assert 103.0 in ask_changes  # Removed
        assert ask_changes[103.0].operation == "remove"
        
        assert 104.0 in ask_changes  # Added
        assert ask_changes[104.0].operation == "add"
        assert ask_changes[104.0].amount == 1.0

    def test_no_changes_returns_none(self, delta_service, sample_orderbook_v1):
        """Test that no changes returns None."""
        conn_id = delta_service.register_connection("ws123", "BTCUSDT", 1.0)
        
        # Send first snapshot
        delta1 = delta_service.compute_delta(conn_id, sample_orderbook_v1)
        assert delta1 is not None
        
        # Send same data again
        delta2 = delta_service.compute_delta(conn_id, sample_orderbook_v1)
        assert delta2 is None

    def test_full_snapshot_interval_enforcement(self, delta_service, sample_orderbook_v1):
        """Test that full snapshots are sent at intervals."""
        # Set very short interval for testing
        delta_service.full_snapshot_interval = 0.1
        
        conn_id = delta_service.register_connection("ws123", "BTCUSDT", 1.0)
        
        # First delta is full snapshot
        delta1 = delta_service.compute_delta(conn_id, sample_orderbook_v1)
        assert delta1.full_snapshot is True
        
        # Wait for interval to pass
        time.sleep(0.2)
        
        # Next delta should be full snapshot due to interval
        delta2 = delta_service.compute_delta(conn_id, sample_orderbook_v1)
        assert delta2.full_snapshot is True

    def test_sequence_id_increment(self, delta_service, sample_orderbook_v1, sample_orderbook_v2):
        """Test that sequence IDs increment properly."""
        conn_id = delta_service.register_connection("ws123", "BTCUSDT", 1.0)
        
        delta1 = delta_service.compute_delta(conn_id, sample_orderbook_v1)
        delta2 = delta_service.compute_delta(conn_id, sample_orderbook_v2)
        
        assert delta2.sequence_id > delta1.sequence_id
        assert delta_service.global_sequence_id >= max(delta1.sequence_id, delta2.sequence_id)

    def test_connection_state_tracking(self, delta_service, sample_orderbook_v1, sample_orderbook_v2):
        """Test that connection state is tracked correctly."""
        conn_id = delta_service.register_connection("ws123", "BTCUSDT", 1.0)
        
        # Send first snapshot
        delta1 = delta_service.compute_delta(conn_id, sample_orderbook_v1)
        state = delta_service.connection_states[conn_id]
        
        # Verify state after first snapshot
        assert len(state.last_sent_bids) == 3
        assert len(state.last_sent_asks) == 3
        assert state.last_sent_bids[100.0] == 1.5
        assert state.last_sent_asks[101.0] == 1.0
        
        # Send delta update
        delta2 = delta_service.compute_delta(conn_id, sample_orderbook_v2)
        
        # Verify state after delta
        assert state.last_sent_bids[100.0] == 2.0  # Updated
        assert 98.0 not in state.last_sent_bids    # Removed
        assert state.last_sent_bids[97.0] == 1.5   # Added

    def test_get_connection_stats(self, delta_service, sample_orderbook_v1):
        """Test getting connection statistics."""
        conn_id = delta_service.register_connection("ws123", "BTCUSDT", 1.0)
        delta_service.compute_delta(conn_id, sample_orderbook_v1)
        
        stats = delta_service.get_connection_stats(conn_id)
        
        assert stats is not None
        assert stats["connection_id"] == conn_id
        assert stats["sequence_id"] > 0
        assert stats["tracked_bids"] == 3
        assert stats["tracked_asks"] == 3
        assert "last_update_ago" in stats

    def test_get_connection_stats_unknown_connection(self, delta_service):
        """Test getting stats for unknown connection."""
        stats = delta_service.get_connection_stats("unknown")
        assert stats is None

    def test_get_service_stats(self, delta_service, sample_orderbook_v1):
        """Test getting service statistics."""
        # Register a few connections
        conn1 = delta_service.register_connection("ws1", "BTCUSDT", 1.0)
        conn2 = delta_service.register_connection("ws2", "ETHUSDT", 0.1)
        
        # Send some data
        delta_service.compute_delta(conn1, sample_orderbook_v1)
        delta_service.compute_delta(conn2, sample_orderbook_v1)
        
        stats = delta_service.get_service_stats()
        
        assert stats["total_connections"] == 2
        assert stats["active_connections"] == 2
        assert stats["total_tracked_levels"] == 12  # 3 bids + 3 asks per connection
        assert stats["global_sequence_id"] > 0

    def test_cleanup_stale_connections(self, delta_service, sample_orderbook_v1):
        """Test cleanup of stale connections."""
        conn_id = delta_service.register_connection("ws123", "BTCUSDT", 1.0)
        delta_service.compute_delta(conn_id, sample_orderbook_v1)
        
        # Manually set old timestamp
        state = delta_service.connection_states[conn_id]
        state.last_update_time = time.time() - 7200  # 2 hours ago
        
        # Cleanup with 1 hour threshold
        delta_service.cleanup_stale_connections(max_age_seconds=3600)
        
        assert conn_id not in delta_service.connection_states

    def test_to_json_delta(self, delta_service, sample_orderbook_v1, sample_orderbook_v2):
        """Test JSON serialization of delta."""
        conn_id = delta_service.register_connection("ws123", "BTCUSDT", 1.0)
        delta_service.compute_delta(conn_id, sample_orderbook_v1)  # Full snapshot
        delta = delta_service.compute_delta(conn_id, sample_orderbook_v2)  # Delta
        
        json_str = delta_service.to_json(delta)
        
        import json
        data = json.loads(json_str)
        
        assert data["type"] == "orderbook_delta"
        assert data["symbol"] == "BTCUSDT"
        assert data["rounding"] == 1.0
        assert data["full_snapshot"] is False
        assert "bids" in data
        assert "asks" in data
        
        # Verify delta level structure
        for bid in data["bids"]:
            assert "price" in bid
            assert "amount" in bid
            assert "operation" in bid

    def test_to_json_full_snapshot(self, delta_service, sample_orderbook_v1):
        """Test JSON serialization of full snapshot."""
        conn_id = delta_service.register_connection("ws123", "BTCUSDT", 1.0)
        delta = delta_service.compute_delta(conn_id, sample_orderbook_v1)
        
        json_str = delta_service.to_json(delta)
        
        import json
        data = json.loads(json_str)
        
        assert data["type"] == "orderbook_snapshot"
        assert data["full_snapshot"] is True
        assert len(data["bids"]) == 3
        assert len(data["asks"]) == 3

    def test_floating_point_precision_handling(self, delta_service):
        """Test handling of floating point precision in comparisons."""
        # Create order books with very small differences
        ob1 = AggregatedOrderBook(
            bids=[OrderBookLevel(price=100.0, amount=1.000000001)],
            asks=[OrderBookLevel(price=101.0, amount=1.0)],
            symbol="BTCUSDT",
            rounding=1.0,
            timestamp=int(time.time() * 1000),
            source="test",
            aggregated=True,
            depth=10
        )
        
        ob2 = AggregatedOrderBook(
            bids=[OrderBookLevel(price=100.0, amount=1.000000002)],
            asks=[OrderBookLevel(price=101.0, amount=1.0)],
            symbol="BTCUSDT",
            rounding=1.0,
            timestamp=int(time.time() * 1000),
            source="test",
            aggregated=True,
            depth=10
        )
        
        conn_id = delta_service.register_connection("ws123", "BTCUSDT", 1.0)
        delta_service.compute_delta(conn_id, ob1)  # Full snapshot
        delta = delta_service.compute_delta(conn_id, ob2)  # Should be None due to precision handling
        
        assert delta is None  # Difference too small to matter

    def test_multiple_connections_independence(self, delta_service, sample_orderbook_v1, sample_orderbook_v2):
        """Test that multiple connections maintain independent state."""
        conn1 = delta_service.register_connection("ws1", "BTCUSDT", 1.0)
        conn2 = delta_service.register_connection("ws2", "BTCUSDT", 1.0)
        
        # Send different data to each connection
        delta1 = delta_service.compute_delta(conn1, sample_orderbook_v1)
        delta2 = delta_service.compute_delta(conn2, sample_orderbook_v2)
        
        # Both should be full snapshots
        assert delta1.full_snapshot is True
        assert delta2.full_snapshot is True
        
        # States should be independent
        state1 = delta_service.connection_states[conn1]
        state2 = delta_service.connection_states[conn2]
        
        assert state1.last_sent_bids != state2.last_sent_bids
        assert state1.sequence_id != state2.sequence_id