"""
Delta Update Service

This module handles delta updates for order book data, tracking previous states
per connection and computing only the changed levels to send.
"""

import time
import json
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import logging

from .orderbook_processor import AggregatedOrderBook, OrderBookLevel

logger = logging.getLogger(__name__)


@dataclass
class DeltaLevel:
    """Represents a delta change to an order book level."""
    price: float
    amount: float
    operation: str  # "add", "update", "remove"


@dataclass
class OrderBookDelta:
    """Represents delta changes to an order book."""
    bids: List[DeltaLevel]
    asks: List[DeltaLevel]
    symbol: str
    rounding: float
    timestamp: Optional[int] = None
    full_snapshot: bool = False
    sequence_id: int = 0


@dataclass
class ConnectionState:
    """Tracks the state of an order book for a specific connection."""
    last_sent_bids: Dict[float, float]  # price -> amount
    last_sent_asks: Dict[float, float]  # price -> amount
    last_update_time: float
    sequence_id: int = 0
    last_full_snapshot_time: float = 0.0


class DeltaUpdateService:
    """
    Service for computing and managing delta updates for order book data.
    
    Tracks previous state per connection and computes only the changes
    that need to be sent to each connection.
    """
    
    def __init__(self, full_snapshot_interval: float = 300.0):
        """
        Initialize the delta update service.
        
        Args:
            full_snapshot_interval: Interval in seconds between full snapshots
        """
        self.connection_states: Dict[str, ConnectionState] = {}
        self.full_snapshot_interval = full_snapshot_interval
        self.logger = logging.getLogger(__name__)
        self.global_sequence_id = 0
    
    def _generate_connection_id(self, websocket_id: str, symbol: str, rounding: float) -> str:
        """Generate a unique connection identifier."""
        return f"{websocket_id}:{symbol}:{rounding}"
    
    def _get_next_sequence_id(self) -> int:
        """Get the next global sequence ID."""
        self.global_sequence_id += 1
        return self.global_sequence_id
    
    def _should_send_full_snapshot(self, connection_state: ConnectionState) -> bool:
        """Determine if a full snapshot should be sent."""
        current_time = time.time()
        return (
            current_time - connection_state.last_full_snapshot_time > self.full_snapshot_interval
        )
    
    def _compute_level_changes(
        self, 
        old_levels: Dict[float, float], 
        new_levels: List[OrderBookLevel]
    ) -> List[DeltaLevel]:
        """
        Compute changes between old and new order book levels.
        
        Args:
            old_levels: Previous levels as {price: amount}
            new_levels: New levels as list of OrderBookLevel
            
        Returns:
            List of delta changes
        """
        deltas = []
        new_levels_dict = {level.price: level.amount for level in new_levels}
        
        # Find additions and updates
        for price, new_amount in new_levels_dict.items():
            old_amount = old_levels.get(price, 0.0)
            
            if old_amount == 0.0:
                # New level
                deltas.append(DeltaLevel(
                    price=price,
                    amount=new_amount,
                    operation="add"
                ))
            elif abs(old_amount - new_amount) > 1e-8:  # Handle floating point precision
                # Updated level
                deltas.append(DeltaLevel(
                    price=price,
                    amount=new_amount,
                    operation="update"
                ))
        
        # Find removals
        for price, old_amount in old_levels.items():
            if price not in new_levels_dict:
                deltas.append(DeltaLevel(
                    price=price,
                    amount=0.0,
                    operation="remove"
                ))
        
        return deltas
    
    def register_connection(
        self, 
        websocket_id: str, 
        symbol: str, 
        rounding: float
    ) -> str:
        """
        Register a new WebSocket connection for delta updates.
        
        Args:
            websocket_id: Unique WebSocket identifier
            symbol: Trading symbol
            rounding: Price rounding value
            
        Returns:
            Connection ID for future operations
        """
        connection_id = self._generate_connection_id(websocket_id, symbol, rounding)
        
        self.connection_states[connection_id] = ConnectionState(
            last_sent_bids={},
            last_sent_asks={},
            last_update_time=time.time(),
            sequence_id=0,
            last_full_snapshot_time=0.0
        )
        
        self.logger.debug(f"Registered connection {connection_id} for delta updates")
        return connection_id
    
    def unregister_connection(self, connection_id: str):
        """
        Unregister a WebSocket connection.
        
        Args:
            connection_id: Connection ID to unregister
        """
        if connection_id in self.connection_states:
            del self.connection_states[connection_id]
            self.logger.debug(f"Unregistered connection {connection_id}")
    
    def compute_delta(
        self, 
        connection_id: str, 
        new_orderbook: AggregatedOrderBook
    ) -> Optional[OrderBookDelta]:
        """
        Compute delta update for a specific connection.
        
        Args:
            connection_id: Connection ID
            new_orderbook: New aggregated order book data
            
        Returns:
            OrderBookDelta with changes, or None if no changes
        """
        if connection_id not in self.connection_states:
            self.logger.warning(f"Unknown connection ID: {connection_id}")
            return None
        
        connection_state = self.connection_states[connection_id]
        current_time = time.time()
        
        # Check if we should send a full snapshot
        send_full_snapshot = (
            self._should_send_full_snapshot(connection_state) or
            not connection_state.last_sent_bids or
            not connection_state.last_sent_asks
        )
        
        if send_full_snapshot:
            # Send full snapshot
            delta = OrderBookDelta(
                bids=[DeltaLevel(level.price, level.amount, "add") for level in new_orderbook.bids],
                asks=[DeltaLevel(level.price, level.amount, "add") for level in new_orderbook.asks],
                symbol=new_orderbook.symbol,
                rounding=new_orderbook.rounding,
                timestamp=new_orderbook.timestamp,
                full_snapshot=True,
                sequence_id=self._get_next_sequence_id()
            )
            
            # Update connection state
            connection_state.last_sent_bids = {level.price: level.amount for level in new_orderbook.bids}
            connection_state.last_sent_asks = {level.price: level.amount for level in new_orderbook.asks}
            connection_state.last_full_snapshot_time = current_time
            connection_state.last_update_time = current_time
            connection_state.sequence_id = delta.sequence_id
            
            self.logger.debug(f"Sending full snapshot for {connection_id}")
            return delta
        
        # Compute deltas
        bid_deltas = self._compute_level_changes(connection_state.last_sent_bids, new_orderbook.bids)
        ask_deltas = self._compute_level_changes(connection_state.last_sent_asks, new_orderbook.asks)
        
        # Check if there are any changes
        if not bid_deltas and not ask_deltas:
            self.logger.debug(f"No changes for {connection_id}")
            return None
        
        # Create delta update
        delta = OrderBookDelta(
            bids=bid_deltas,
            asks=ask_deltas,
            symbol=new_orderbook.symbol,
            rounding=new_orderbook.rounding,
            timestamp=new_orderbook.timestamp,
            full_snapshot=False,
            sequence_id=self._get_next_sequence_id()
        )
        
        # Update connection state with only the changed levels
        for delta_level in bid_deltas:
            if delta_level.operation == "remove":
                connection_state.last_sent_bids.pop(delta_level.price, None)
            else:
                connection_state.last_sent_bids[delta_level.price] = delta_level.amount
        
        for delta_level in ask_deltas:
            if delta_level.operation == "remove":
                connection_state.last_sent_asks.pop(delta_level.price, None)
            else:
                connection_state.last_sent_asks[delta_level.price] = delta_level.amount
        
        connection_state.last_update_time = current_time
        connection_state.sequence_id = delta.sequence_id
        
        self.logger.debug(
            f"Computed delta for {connection_id}: "
            f"{len(bid_deltas)} bid changes, {len(ask_deltas)} ask changes"
        )
        return delta
    
    def get_connection_stats(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a specific connection.
        
        Args:
            connection_id: Connection ID
            
        Returns:
            Connection statistics or None if not found
        """
        if connection_id not in self.connection_states:
            return None
        
        state = self.connection_states[connection_id]
        current_time = time.time()
        
        return {
            "connection_id": connection_id,
            "sequence_id": state.sequence_id,
            "last_update_ago": current_time - state.last_update_time,
            "last_full_snapshot_ago": current_time - state.last_full_snapshot_time,
            "tracked_bids": len(state.last_sent_bids),
            "tracked_asks": len(state.last_sent_asks)
        }
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get overall service statistics."""
        current_time = time.time()
        
        total_connections = len(self.connection_states)
        active_connections = sum(
            1 for state in self.connection_states.values()
            if current_time - state.last_update_time < 300  # Active in last 5 minutes
        )
        
        total_tracked_levels = sum(
            len(state.last_sent_bids) + len(state.last_sent_asks)
            for state in self.connection_states.values()
        )
        
        return {
            "total_connections": total_connections,
            "active_connections": active_connections,
            "total_tracked_levels": total_tracked_levels,
            "global_sequence_id": self.global_sequence_id,
            "full_snapshot_interval": self.full_snapshot_interval
        }
    
    def cleanup_stale_connections(self, max_age_seconds: float = 3600.0):
        """
        Clean up connections that haven't been updated recently.
        
        Args:
            max_age_seconds: Maximum age before considering a connection stale
        """
        current_time = time.time()
        stale_connections = [
            conn_id for conn_id, state in self.connection_states.items()
            if current_time - state.last_update_time > max_age_seconds
        ]
        
        for conn_id in stale_connections:
            del self.connection_states[conn_id]
        
        if stale_connections:
            self.logger.info(f"Cleaned up {len(stale_connections)} stale connections")
    
    def to_json(self, delta: OrderBookDelta) -> str:
        """
        Convert delta to JSON format for WebSocket transmission.
        
        Args:
            delta: OrderBookDelta to convert
            
        Returns:
            JSON string representation
        """
        # Convert to dictionary format
        delta_dict = {
            "type": "orderbook_delta" if not delta.full_snapshot else "orderbook_snapshot",
            "symbol": delta.symbol,
            "rounding": delta.rounding,
            "timestamp": delta.timestamp,
            "sequence_id": delta.sequence_id,
            "full_snapshot": delta.full_snapshot,
            "bids": [
                {
                    "price": level.price,
                    "amount": level.amount,
                    "operation": level.operation
                }
                for level in delta.bids
            ],
            "asks": [
                {
                    "price": level.price,
                    "amount": level.amount,
                    "operation": level.operation
                }
                for level in delta.asks
            ]
        }
        
        return json.dumps(delta_dict)