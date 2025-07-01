"""
OrderBook Manager Service

This module provides centralized management of order books for multiple symbols.
It handles lifecycle management, connection tracking, and memory management.
"""

import asyncio
import logging
from typing import Dict, Optional, Set, Callable, Any, List
from datetime import datetime, timedelta
from collections import OrderedDict
import weakref

from app.services.orderbook_processor import OrderBookProcessor, AggregatedOrderBook
from app.services.depth_cache_service import depth_cache_service
from app.services.exchange_service import exchange_service
from app.core.logging_config import get_logger

logger = get_logger("orderbook_manager")


class OrderBookInfo:
    """Information about an active order book."""
    
    def __init__(self, symbol: str, source: str = "ccxtpro"):
        self.symbol = symbol
        self.source = source
        self.connections: Set[str] = set()  # Track connection IDs
        self.created_at = datetime.utcnow()
        self.last_accessed = datetime.utcnow()
        self.latest_orderbook: Optional[AggregatedOrderBook] = None
        self.is_active = True
        
    def add_connection(self, connection_id: str) -> None:
        """Add a connection to this order book."""
        self.connections.add(connection_id)
        self.last_accessed = datetime.utcnow()
        
    def remove_connection(self, connection_id: str) -> None:
        """Remove a connection from this order book."""
        self.connections.discard(connection_id)
        if self.connections:
            self.last_accessed = datetime.utcnow()
            
    @property
    def connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.connections)
        
    @property
    def age_seconds(self) -> float:
        """Get the age of this order book in seconds."""
        return (datetime.utcnow() - self.created_at).total_seconds()


class OrderBookManager:
    """
    Manages order books for multiple symbols with lifecycle and memory management.
    
    Features:
    - Symbol-based order book storage
    - Connection tracking with reference counting
    - Automatic cleanup when connections reach zero
    - LRU eviction for memory management
    - Support for both ccxtpro and DepthCacheManager data sources
    """
    
    def __init__(self, max_orderbooks: int = 100, cleanup_delay_seconds: int = 30):
        self.max_orderbooks = max_orderbooks
        self.cleanup_delay_seconds = cleanup_delay_seconds
        
        # Core storage
        self.orderbooks: OrderedDict[str, OrderBookInfo] = OrderedDict()
        self.processor = OrderBookProcessor()
        
        # Cleanup management
        self.cleanup_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        
        # Callbacks for order book updates
        self.update_callbacks: Dict[str, Set[Callable]] = {}
        
        logger.info(f"OrderBookManager initialized with max_orderbooks={max_orderbooks}, cleanup_delay={cleanup_delay_seconds}s")
    
    async def create_orderbook(
        self, 
        symbol: str, 
        connection_id: str,
        source: str = "auto"
    ) -> OrderBookInfo:
        """
        Create or get an order book for a symbol.
        
        Args:
            symbol: Trading symbol
            connection_id: Unique identifier for the connection
            source: Data source ("auto", "ccxtpro", "depth_cache")
            
        Returns:
            OrderBookInfo instance
        """
        async with self._lock:
            symbol = symbol.upper()
            
            # Determine source automatically if needed
            if source == "auto":
                source = "depth_cache" if symbol.endswith("USDT") else "ccxtpro"
            
            # Check if order book already exists
            if symbol in self.orderbooks:
                orderbook_info = self.orderbooks[symbol]
                orderbook_info.add_connection(connection_id)
                
                # Cancel any pending cleanup
                if symbol in self.cleanup_tasks:
                    self.cleanup_tasks[symbol].cancel()
                    del self.cleanup_tasks[symbol]
                    logger.info(f"Cancelled cleanup task for {symbol}")
                
                # Move to end (LRU)
                self.orderbooks.move_to_end(symbol)
                
                logger.info(f"Reusing existing order book for {symbol}, connections: {orderbook_info.connection_count}")
                return orderbook_info
            
            # Check memory limits
            if len(self.orderbooks) >= self.max_orderbooks:
                await self._evict_least_recently_used()
            
            # Create new order book
            orderbook_info = OrderBookInfo(symbol, source)
            orderbook_info.add_connection(connection_id)
            self.orderbooks[symbol] = orderbook_info
            
            # Start data streaming
            await self._start_data_stream(symbol, source)
            
            logger.info(f"Created new order book for {symbol} with source {source}")
            return orderbook_info
    
    async def remove_connection(self, symbol: str, connection_id: str) -> None:
        """
        Remove a connection from an order book.
        
        Args:
            symbol: Trading symbol
            connection_id: Connection identifier to remove
        """
        async with self._lock:
            symbol = symbol.upper()
            
            if symbol not in self.orderbooks:
                logger.warning(f"Attempted to remove connection from non-existent order book: {symbol}")
                return
            
            orderbook_info = self.orderbooks[symbol]
            orderbook_info.remove_connection(connection_id)
            
            logger.info(f"Removed connection {connection_id} from {symbol}, remaining: {orderbook_info.connection_count}")
            
            # Schedule cleanup if no connections remain
            if orderbook_info.connection_count == 0:
                await self._schedule_cleanup(symbol)
    
    async def _schedule_cleanup(self, symbol: str) -> None:
        """Schedule cleanup of an order book after delay."""
        if symbol in self.cleanup_tasks:
            # Already scheduled
            return
        
        async def cleanup_after_delay():
            try:
                await asyncio.sleep(self.cleanup_delay_seconds)
                await self._cleanup_orderbook(symbol)
            except asyncio.CancelledError:
                logger.debug(f"Cleanup task cancelled for {symbol}")
        
        self.cleanup_tasks[symbol] = asyncio.create_task(cleanup_after_delay())
        logger.info(f"Scheduled cleanup for {symbol} in {self.cleanup_delay_seconds} seconds")
    
    async def _cleanup_orderbook(self, symbol: str) -> None:
        """Clean up an order book and stop its data stream."""
        async with self._lock:
            if symbol not in self.orderbooks:
                return
            
            orderbook_info = self.orderbooks[symbol]
            
            # Double-check no connections were added during delay
            if orderbook_info.connection_count > 0:
                logger.info(f"Skipping cleanup for {symbol} - connections were added during delay")
                if symbol in self.cleanup_tasks:
                    del self.cleanup_tasks[symbol]
                return
            
            # Stop data streaming
            await self._stop_data_stream(symbol, orderbook_info.source)
            
            # Remove from storage
            del self.orderbooks[symbol]
            if symbol in self.cleanup_tasks:
                del self.cleanup_tasks[symbol]
            if symbol in self.update_callbacks:
                del self.update_callbacks[symbol]
            
            logger.info(f"Cleaned up order book for {symbol}")
    
    async def _evict_least_recently_used(self) -> None:
        """Evict the least recently used order book to free memory."""
        if not self.orderbooks:
            return
        
        # Find LRU order book (first in OrderedDict)
        lru_symbol = next(iter(self.orderbooks))
        lru_orderbook = self.orderbooks[lru_symbol]
        
        logger.warning(f"Memory limit reached, evicting LRU order book: {lru_symbol} (age: {lru_orderbook.age_seconds:.1f}s)")
        
        # Force cleanup
        await self._cleanup_orderbook(lru_symbol)
    
    async def _start_data_stream(self, symbol: str, source: str) -> None:
        """Start data streaming for a symbol."""
        try:
            if source == "depth_cache":
                # Use DepthCacheManager for Binance symbols
                callback = self._create_depth_cache_callback(symbol)
                await depth_cache_service.start_depth_cache(symbol, callback)
                logger.info(f"Started DepthCache stream for {symbol}")
            else:
                # Use ccxtpro for other exchanges
                # Note: ccxtpro streaming is handled by connection_manager
                # This is where we'd integrate with ccxtpro if needed
                logger.info(f"ccxtpro streaming for {symbol} handled by connection_manager")
                
        except Exception as e:
            logger.error(f"Failed to start data stream for {symbol}: {e}")
            raise
    
    async def _stop_data_stream(self, symbol: str, source: str) -> None:
        """Stop data streaming for a symbol."""
        try:
            if source == "depth_cache":
                # Stop DepthCacheManager stream
                callback = self._create_depth_cache_callback(symbol)
                await depth_cache_service.stop_depth_cache(symbol, callback)
                logger.info(f"Stopped DepthCache stream for {symbol}")
            else:
                # ccxtpro cleanup handled by connection_manager
                logger.info(f"ccxtpro stream cleanup for {symbol} handled by connection_manager")
                
        except Exception as e:
            logger.error(f"Failed to stop data stream for {symbol}: {e}")
    
    def _create_depth_cache_callback(self, symbol: str) -> Callable:
        """Create a callback function for DepthCache updates."""
        async def depth_cache_callback(symbol: str, depth_data: Dict[str, Any]) -> None:
            try:
                await self._process_depth_update(symbol, depth_data)
            except Exception as e:
                logger.error(f"Error in depth cache callback for {symbol}: {e}")
        
        return depth_cache_callback
    
    async def _process_depth_update(self, symbol: str, depth_data: Dict[str, Any]) -> None:
        """Process a depth cache update and store the latest data."""
        try:
            if symbol not in self.orderbooks:
                return
            
            orderbook_info = self.orderbooks[symbol]
            
            # Create a mock depth cache object for the processor
            class MockDepthCache:
                def __init__(self, bids_dict, asks_dict):
                    self.bids_dict = bids_dict
                    self.asks_dict = asks_dict
                
                def get_bids(self):
                    return self.bids_dict
                
                def get_asks(self):
                    return self.asks_dict
            
            # Convert depth_data to the format expected by processor
            mock_depth_cache = MockDepthCache(
                depth_data.get("bids", {}),
                depth_data.get("asks", {})
            )
            
            # Process with default settings (can be made configurable)
            aggregated_book = self.processor.process_depth_cache(
                mock_depth_cache,
                symbol,
                rounding=0.01,
                depth=20
            )
            
            # Store latest data
            orderbook_info.latest_orderbook = aggregated_book
            orderbook_info.last_accessed = datetime.utcnow()
            
            # Notify callbacks
            await self._notify_callbacks(symbol, aggregated_book)
            
        except Exception as e:
            logger.error(f"Error processing depth update for {symbol}: {e}")
    
    async def _notify_callbacks(self, symbol: str, orderbook: AggregatedOrderBook) -> None:
        """Notify all callbacks for a symbol about an order book update."""
        if symbol not in self.update_callbacks:
            return
        
        callbacks = list(self.update_callbacks[symbol])
        for callback in callbacks:
            try:
                await callback(symbol, orderbook)
            except Exception as e:
                logger.error(f"Error in order book callback for {symbol}: {e}")
    
    def add_update_callback(self, symbol: str, callback: Callable) -> None:
        """Add a callback for order book updates."""
        symbol = symbol.upper()
        if symbol not in self.update_callbacks:
            self.update_callbacks[symbol] = set()
        self.update_callbacks[symbol].add(callback)
    
    def remove_update_callback(self, symbol: str, callback: Callable) -> None:
        """Remove a callback for order book updates."""
        symbol = symbol.upper()
        if symbol in self.update_callbacks:
            self.update_callbacks[symbol].discard(callback)
            if not self.update_callbacks[symbol]:
                del self.update_callbacks[symbol]
    
    def get_orderbook(self, symbol: str) -> Optional[AggregatedOrderBook]:
        """Get the latest order book for a symbol."""
        symbol = symbol.upper()
        if symbol in self.orderbooks:
            orderbook_info = self.orderbooks[symbol]
            orderbook_info.last_accessed = datetime.utcnow()
            # Move to end (LRU)
            self.orderbooks.move_to_end(symbol)
            return orderbook_info.latest_orderbook
        return None
    
    def get_orderbook_info(self, symbol: str) -> Optional[OrderBookInfo]:
        """Get order book info for a symbol."""
        symbol = symbol.upper()
        return self.orderbooks.get(symbol)
    
    def get_active_symbols(self) -> List[str]:
        """Get list of symbols with active order books."""
        return list(self.orderbooks.keys())
    
    def get_connection_count(self, symbol: str) -> int:
        """Get the number of connections for a symbol."""
        symbol = symbol.upper()
        if symbol in self.orderbooks:
            return self.orderbooks[symbol].connection_count
        return 0
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        total_orderbooks = len(self.orderbooks)
        total_connections = sum(info.connection_count for info in self.orderbooks.values())
        cleanup_tasks = len(self.cleanup_tasks)
        
        return {
            "total_orderbooks": total_orderbooks,
            "max_orderbooks": self.max_orderbooks,
            "utilization_percent": (total_orderbooks / self.max_orderbooks) * 100,
            "total_connections": total_connections,
            "cleanup_tasks": cleanup_tasks,
            "symbols": list(self.orderbooks.keys())
        }
    
    async def shutdown(self) -> None:
        """Shutdown the order book manager and clean up all resources."""
        logger.info("Shutting down OrderBookManager")
        
        # Cancel all cleanup tasks
        for task in self.cleanup_tasks.values():
            task.cancel()
        
        # Stop all data streams
        symbols = list(self.orderbooks.keys())
        for symbol in symbols:
            await self._cleanup_orderbook(symbol)
        
        self.orderbooks.clear()
        self.cleanup_tasks.clear()
        self.update_callbacks.clear()
        
        logger.info("OrderBookManager shutdown complete")


# Global instance
orderbook_manager = OrderBookManager()