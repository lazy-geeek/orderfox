"""
Batch Update Service

This module handles batching of rapid order book updates to optimize
WebSocket transmission and reduce message frequency.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from collections import defaultdict, deque
import logging

from .orderbook_processor import AggregatedOrderBook
from .delta_update_service import OrderBookDelta

logger = logging.getLogger(__name__)


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    max_batch_size: int = 10
    max_batch_delay_ms: float = 100.0  # Maximum delay before sending batch
    min_batch_delay_ms: float = 10.0   # Minimum delay between batches
    max_queue_size: int = 100          # Maximum updates to queue per connection


@dataclass
class PendingUpdate:
    """Represents a pending update in the batch queue."""
    connection_id: str
    data: Any  # AggregatedOrderBook or OrderBookDelta
    timestamp: float
    priority: int = 0  # Higher numbers = higher priority


@dataclass
class BatchStats:
    """Statistics for batch processing."""
    total_updates_received: int = 0
    total_batches_sent: int = 0
    total_updates_batched: int = 0
    avg_batch_size: float = 0.0
    avg_batch_delay_ms: float = 0.0
    queue_overflows: int = 0
    last_reset_time: float = field(default_factory=time.time)


class BatchUpdateService:
    """
    Service for batching rapid order book updates.
    
    Collects updates over short time windows and sends them in batches
    to reduce WebSocket message frequency and improve efficiency.
    """
    
    def __init__(self, config: BatchConfig = None):
        """
        Initialize the batch update service.
        
        Args:
            config: Batch configuration (uses defaults if None)
        """
        self.config = config or BatchConfig()
        self.logger = logging.getLogger(__name__)
        
        # Batch queues per connection
        self.update_queues: Dict[str, deque[PendingUpdate]] = defaultdict(deque)
        
        # Batch timers per connection
        self.batch_timers: Dict[str, asyncio.TimerHandle] = {}
        
        # Statistics
        self.stats = BatchStats()
        
        # Callback for sending batched updates
        self.send_callback: Optional[Callable[[str, List[Any]], None]] = None
        
        # Connection tracking
        self.active_connections: Set[str] = set()
        
        # Background tasks
        self.cleanup_task: Optional[asyncio.Task] = None
        self.stats_task: Optional[asyncio.Task] = None
        
        self.logger.info(f"BatchUpdateService initialized with config: {self.config}")
    
    def set_send_callback(self, callback: Callable[[str, List[Any]], None]):
        """
        Set the callback function for sending batched updates.
        
        Args:
            callback: Function to call with (connection_id, updates_list)
        """
        self.send_callback = callback
        self.logger.debug("Send callback configured")
    
    def register_connection(self, connection_id: str):
        """
        Register a new connection for batch processing.
        
        Args:
            connection_id: Unique connection identifier
        """
        self.active_connections.add(connection_id)
        if connection_id not in self.update_queues:
            self.update_queues[connection_id] = deque()
        self.logger.debug(f"Registered connection {connection_id} for batching")
    
    def unregister_connection(self, connection_id: str):
        """
        Unregister a connection and clean up its resources.
        
        Args:
            connection_id: Connection identifier to unregister
        """
        self.active_connections.discard(connection_id)
        
        # Cancel pending timer
        if connection_id in self.batch_timers:
            self.batch_timers[connection_id].cancel()
            del self.batch_timers[connection_id]
        
        # Clear queue
        if connection_id in self.update_queues:
            del self.update_queues[connection_id]
        
        self.logger.debug(f"Unregistered connection {connection_id}")
    
    def add_update(
        self, 
        connection_id: str, 
        data: Any, 
        priority: int = 0
    ) -> bool:
        """
        Add an update to the batch queue.
        
        Args:
            connection_id: Connection to send update to
            data: Update data (AggregatedOrderBook or OrderBookDelta)
            priority: Update priority (higher = more important)
            
        Returns:
            True if added successfully, False if queue is full
        """
        if connection_id not in self.active_connections:
            self.logger.warning(f"Attempt to add update for unregistered connection: {connection_id}")
            return False
        
        queue = self.update_queues[connection_id]
        
        # Check queue size limit
        if len(queue) >= self.config.max_queue_size:
            # Remove oldest update to make space
            queue.popleft()
            self.stats.queue_overflows += 1
            self.logger.warning(f"Queue overflow for {connection_id}, dropped oldest update")
        
        # Add new update
        update = PendingUpdate(
            connection_id=connection_id,
            data=data,
            timestamp=time.time(),
            priority=priority
        )
        
        queue.append(update)
        self.stats.total_updates_received += 1
        
        # Schedule batch processing if not already scheduled
        self._schedule_batch_processing(connection_id)
        
        return True
    
    def _schedule_batch_processing(self, connection_id: str):
        """
        Schedule batch processing for a connection.
        
        Args:
            connection_id: Connection to schedule processing for
        """
        # Cancel existing timer if present
        if connection_id in self.batch_timers:
            self.batch_timers[connection_id].cancel()
        
        # Determine delay based on queue size
        queue_size = len(self.update_queues[connection_id])
        
        if queue_size >= self.config.max_batch_size:
            # Send immediately if batch is full
            delay = 0.0
        else:
            # Use configurable delay
            delay = self.config.max_batch_delay_ms / 1000.0
        
        # Schedule processing
        loop = asyncio.get_event_loop()
        self.batch_timers[connection_id] = loop.call_later(
            delay,
            self._process_batch,
            connection_id
        )
    
    def _process_batch(self, connection_id: str):
        """
        Process and send a batch of updates for a connection.
        
        Args:
            connection_id: Connection to process batch for
        """
        if connection_id not in self.update_queues:
            return
        
        queue = self.update_queues[connection_id]
        if not queue:
            return
        
        # Remove from timers
        self.batch_timers.pop(connection_id, None)
        
        # Collect updates for batch
        batch_updates = []
        batch_start_time = time.time()
        
        # Take up to max_batch_size updates
        while queue and len(batch_updates) < self.config.max_batch_size:
            update = queue.popleft()
            batch_updates.append(update.data)
        
        if not batch_updates:
            return
        
        # Calculate batch delay
        oldest_update_time = min(
            getattr(update, 'timestamp', batch_start_time) 
            for update in batch_updates
        )
        batch_delay = (batch_start_time - oldest_update_time) * 1000
        
        # Update statistics
        self.stats.total_batches_sent += 1
        self.stats.total_updates_batched += len(batch_updates)
        
        # Calculate running averages
        total_batches = self.stats.total_batches_sent
        self.stats.avg_batch_size = (
            (self.stats.avg_batch_size * (total_batches - 1) + len(batch_updates)) / total_batches
        )
        self.stats.avg_batch_delay_ms = (
            (self.stats.avg_batch_delay_ms * (total_batches - 1) + batch_delay) / total_batches
        )
        
        # Send batch via callback
        if self.send_callback:
            try:
                self.send_callback(connection_id, batch_updates)
                self.logger.debug(
                    f"Sent batch of {len(batch_updates)} updates to {connection_id} "
                    f"(delay: {batch_delay:.1f}ms)"
                )
            except Exception as e:
                self.logger.error(f"Error sending batch to {connection_id}: {e}")
        else:
            self.logger.warning("No send callback configured, dropping batch")
        
        # Schedule next batch if more updates are queued
        if queue:
            self._schedule_batch_processing(connection_id)
    
    def force_flush(self, connection_id: str = None):
        """
        Force immediate processing of all queued updates.
        
        Args:
            connection_id: Specific connection to flush, or None for all
        """
        if connection_id:
            connections_to_flush = [connection_id] if connection_id in self.active_connections else []
        else:
            connections_to_flush = list(self.active_connections)
        
        for conn_id in connections_to_flush:
            # Cancel timer
            if conn_id in self.batch_timers:
                self.batch_timers[conn_id].cancel()
                del self.batch_timers[conn_id]
            
            # Process batch immediately
            self._process_batch(conn_id)
        
        self.logger.debug(f"Force flushed {len(connections_to_flush)} connections")
    
    def get_queue_stats(self, connection_id: str = None) -> Dict[str, Any]:
        """
        Get queue statistics.
        
        Args:
            connection_id: Specific connection to get stats for, or None for all
            
        Returns:
            Dictionary with queue statistics
        """
        if connection_id:
            if connection_id not in self.update_queues:
                return {"error": f"Connection {connection_id} not found"}
            
            queue = self.update_queues[connection_id]
            return {
                "connection_id": connection_id,
                "queue_size": len(queue),
                "has_pending_timer": connection_id in self.batch_timers,
                "oldest_update_age_ms": (
                    (time.time() - queue[0].timestamp) * 1000 
                    if queue else 0
                )
            }
        else:
            # Stats for all connections
            total_queued = sum(len(queue) for queue in self.update_queues.values())
            active_timers = len(self.batch_timers)
            
            return {
                "total_connections": len(self.active_connections),
                "total_queued_updates": total_queued,
                "active_batch_timers": active_timers,
                "connections": [
                    {
                        "connection_id": conn_id,
                        "queue_size": len(self.update_queues.get(conn_id, [])),
                        "has_timer": conn_id in self.batch_timers
                    }
                    for conn_id in self.active_connections
                ]
            }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        current_time = time.time()
        uptime_seconds = current_time - self.stats.last_reset_time
        
        # Calculate rates
        updates_per_second = (
            self.stats.total_updates_received / uptime_seconds 
            if uptime_seconds > 0 else 0
        )
        batches_per_second = (
            self.stats.total_batches_sent / uptime_seconds 
            if uptime_seconds > 0 else 0
        )
        
        # Calculate efficiency
        batching_efficiency = (
            self.stats.total_updates_batched / self.stats.total_updates_received
            if self.stats.total_updates_received > 0 else 0
        )
        
        return {
            "uptime_seconds": uptime_seconds,
            "total_updates_received": self.stats.total_updates_received,
            "total_batches_sent": self.stats.total_batches_sent,
            "total_updates_batched": self.stats.total_updates_batched,
            "updates_per_second": updates_per_second,
            "batches_per_second": batches_per_second,
            "avg_batch_size": self.stats.avg_batch_size,
            "avg_batch_delay_ms": self.stats.avg_batch_delay_ms,
            "queue_overflows": self.stats.queue_overflows,
            "batching_efficiency": batching_efficiency,
            "config": {
                "max_batch_size": self.config.max_batch_size,
                "max_batch_delay_ms": self.config.max_batch_delay_ms,
                "min_batch_delay_ms": self.config.min_batch_delay_ms,
                "max_queue_size": self.config.max_queue_size
            }
        }
    
    def reset_stats(self):
        """Reset performance statistics."""
        self.stats = BatchStats()
        self.logger.info("Reset batch processing statistics")
    
    def update_config(self, new_config: BatchConfig):
        """
        Update batch configuration.
        
        Args:
            new_config: New configuration to apply
        """
        old_config = self.config
        self.config = new_config
        
        self.logger.info(
            f"Updated batch config: max_size {old_config.max_batch_size}->{new_config.max_batch_size}, "
            f"max_delay {old_config.max_batch_delay_ms}->{new_config.max_batch_delay_ms}ms"
        )
    
    async def start_background_tasks(self):
        """Start background maintenance tasks."""
        if not self.cleanup_task:
            self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
        if not self.stats_task:
            self.stats_task = asyncio.create_task(self._periodic_stats_logging())
        
        self.logger.info("Started background tasks")
    
    async def stop_background_tasks(self):
        """Stop background maintenance tasks."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self.cleanup_task = None
        
        if self.stats_task:
            self.stats_task.cancel()
            try:
                await self.stats_task
            except asyncio.CancelledError:
                pass
            self.stats_task = None
        
        self.logger.info("Stopped background tasks")
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of stale connections and data."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                # Clean up stale connections (no updates for 1 hour)
                current_time = time.time()
                stale_connections = []
                
                for conn_id in list(self.active_connections):
                    queue = self.update_queues.get(conn_id, deque())
                    if queue:
                        last_update_time = max(update.timestamp for update in queue)
                        if current_time - last_update_time > 3600:  # 1 hour
                            stale_connections.append(conn_id)
                    elif conn_id not in self.batch_timers:
                        # No queue and no timer = likely stale
                        stale_connections.append(conn_id)
                
                for conn_id in stale_connections:
                    self.unregister_connection(conn_id)
                
                if stale_connections:
                    self.logger.info(f"Cleaned up {len(stale_connections)} stale connections")
                
            except Exception as e:
                self.logger.error(f"Error in periodic cleanup: {e}")
    
    async def _periodic_stats_logging(self):
        """Periodic logging of performance statistics."""
        while True:
            try:
                await asyncio.sleep(600)  # Log every 10 minutes
                
                stats = self.get_performance_stats()
                self.logger.info(
                    f"Batch Stats: {stats['updates_per_second']:.1f} updates/s, "
                    f"{stats['batches_per_second']:.1f} batches/s, "
                    f"avg size: {stats['avg_batch_size']:.1f}, "
                    f"efficiency: {stats['batching_efficiency']:.2%}"
                )
                
            except Exception as e:
                self.logger.error(f"Error in periodic stats logging: {e}")