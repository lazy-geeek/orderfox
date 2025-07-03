from typing import Dict, Set, Optional, List, Tuple
import asyncio
import time
import logging
from collections import defaultdict

from ..models.orderbook import OrderBook, OrderBookSnapshot
from .orderbook_aggregation_service import OrderBookAggregationService


logger = logging.getLogger(__name__)


class OrderBookManager:
    """
    Singleton manager for order book lifecycle and state management.
    Handles creation, destruction, and tracking of order books.
    """
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OrderBookManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._orderbooks: Dict[str, OrderBook] = {}
        self._connections: Dict[str, Set[str]] = defaultdict(set)  # symbol -> connection_ids
        self._connection_params: Dict[str, Dict] = {}  # connection_id -> {limit, rounding, symbol}
        self._persistent_mode = False  # Future flag for persistent order books
        self._aggregation_service = OrderBookAggregationService()
        self._symbol_data: Dict[str, Dict] = {}  # symbol -> symbol metadata
        
        # Memory monitoring
        self._max_orderbooks = 100
        self._cleanup_threshold = 0.8  # Start cleanup at 80% of max
        
        logger.info("OrderBookManager initialized")
    
    async def set_persistent_mode(self, persistent: bool) -> None:
        """
        Set persistent mode for order books.
        When True, order books continue updating without connections.
        
        Args:
            persistent: Whether to enable persistent mode
        """
        async with self._lock:
            self._persistent_mode = persistent
            logger.info(f"OrderBookManager persistent mode set to {persistent}")
    
    async def register_connection(self, connection_id: str, symbol: str, 
                                limit: int, rounding: float) -> OrderBook:
        """
        Register a new connection and get or create the associated order book.
        
        Args:
            connection_id: Unique connection identifier
            symbol: Trading symbol
            limit: Display depth limit
            rounding: Price rounding value
            
        Returns:
            OrderBook instance for the symbol
        """
        async with self._lock:
            # Store connection parameters
            self._connection_params[connection_id] = {
                'symbol': symbol,
                'limit': limit,
                'rounding': rounding,
                'connected_at': time.time()
            }
            
            # Add connection to symbol tracking
            self._connections[symbol].add(connection_id)
            
            # Create or get order book
            if symbol not in self._orderbooks:
                self._orderbooks[symbol] = OrderBook(symbol)
                logger.info(f"Created new OrderBook for {symbol}")
                
                # Trigger cache warming for new orderbook (don't wait for it)
                orderbook = self._orderbooks[symbol]
                symbol_data = self._symbol_data.get(symbol)
                asyncio.create_task(
                    self._aggregation_service.warm_cache_for_symbol(symbol, orderbook, symbol_data)
                )
            else:
                orderbook = self._orderbooks[symbol]
            
            # Check if we need memory cleanup
            await self._check_memory_usage()
            
            logger.info(f"Registered connection {connection_id} for {symbol} "
                       f"(limit={limit}, rounding={rounding})")
            
            return orderbook
    
    async def unregister_connection(self, connection_id: str) -> None:
        """
        Unregister a connection and cleanup if necessary.
        
        Args:
            connection_id: Connection identifier to remove
        """
        async with self._lock:
            if connection_id not in self._connection_params:
                return
            
            # Get connection info
            connection_info = self._connection_params[connection_id]
            symbol = connection_info['symbol']
            
            # Remove from tracking
            self._connections[symbol].discard(connection_id)
            del self._connection_params[connection_id]
            
            # If no more connections and not persistent mode, cleanup order book
            if not self._connections[symbol] and not self._persistent_mode:
                if symbol in self._orderbooks:
                    del self._orderbooks[symbol]
                    logger.info(f"Removed OrderBook for {symbol} (no active connections)")
                
                # Clean up empty connection set
                if not self._connections[symbol]:
                    del self._connections[symbol]
            
            logger.info(f"Unregistered connection {connection_id} for {symbol}")
    
    async def update_connection_params(self, connection_id: str, 
                                     limit: Optional[int] = None,
                                     rounding: Optional[float] = None) -> bool:
        """
        Update parameters for an existing connection.
        
        Args:
            connection_id: Connection identifier
            limit: New display depth limit
            rounding: New price rounding value
            
        Returns:
            True if connection was found and updated, False otherwise
        """
        async with self._lock:
            if connection_id not in self._connection_params:
                return False
            
            connection_info = self._connection_params[connection_id]
            
            if limit is not None:
                connection_info['limit'] = limit
            if rounding is not None:
                connection_info['rounding'] = rounding
            
            connection_info['updated_at'] = time.time()
            
            logger.info(f"Updated connection {connection_id} parameters: "
                       f"limit={limit}, rounding={rounding}")
            
            return True
    
    async def warm_cache_for_symbol(self, symbol: str) -> None:
        """
        Trigger cache warming for a symbol's orderbook.
        
        Args:
            symbol: Trading symbol to warm cache for
        """
        async with self._lock:
            orderbook = self._orderbooks.get(symbol)
            symbol_data = self._symbol_data.get(symbol)
            
            if orderbook:
                # Trigger cache warming in background (don't wait for it)
                asyncio.create_task(
                    self._aggregation_service.warm_cache_for_symbol(symbol, orderbook, symbol_data)
                )
    
    async def get_orderbook(self, symbol: str) -> Optional[OrderBook]:
        """
        Get an order book by symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            OrderBook instance or None if not found
        """
        async with self._lock:
            return self._orderbooks.get(symbol)
    
    async def get_aggregated_orderbook(self, connection_id: str) -> Optional[Dict]:
        """
        Get aggregated order book data for a specific connection.
        
        Args:
            connection_id: Connection identifier
            
        Returns:
            Aggregated order book data or None if connection not found
        """
        async with self._lock:
            if connection_id not in self._connection_params:
                return None
            
            connection_info = self._connection_params[connection_id]
            symbol = connection_info['symbol']
            limit = connection_info['limit']
            rounding = connection_info['rounding']
            
            orderbook = self._orderbooks.get(symbol)
            if not orderbook:
                return None
            
            # Get symbol data if available
            symbol_data = self._symbol_data.get(symbol)
            
            # Use aggregation service to get aggregated data
            return await self._aggregation_service.aggregate_orderbook(
                orderbook, limit, rounding, symbol_data
            )
    
    async def get_connections_for_symbol(self, symbol: str) -> List[str]:
        """
        Get all connection IDs for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            List of connection IDs
        """
        async with self._lock:
            return list(self._connections.get(symbol, set()))
    
    async def get_connection_params(self, connection_id: str) -> Optional[Dict]:
        """
        Get parameters for a specific connection.
        
        Args:
            connection_id: Connection identifier
            
        Returns:
            Connection parameters or None if not found
        """
        async with self._lock:
            return self._connection_params.get(connection_id)
    
    async def update_symbol_data(self, symbol: str, symbol_data: Dict) -> None:
        """
        Update symbol metadata for rounding calculations.
        
        Args:
            symbol: Trading symbol
            symbol_data: Symbol metadata including price precision
        """
        async with self._lock:
            self._symbol_data[symbol] = symbol_data
    
    async def get_stats(self) -> Dict:
        """
        Get manager statistics.
        
        Returns:
            Dictionary with current statistics
        """
        async with self._lock:
            total_connections = len(self._connection_params)
            active_orderbooks = len(self._orderbooks)
            
            # Calculate memory usage estimate
            memory_usage = 0
            for orderbook in self._orderbooks.values():
                bid_count, ask_count = await orderbook.get_levels_count()
                memory_usage += (bid_count + ask_count) * 32  # Rough estimate
            
            return {
                'total_connections': total_connections,
                'active_orderbooks': active_orderbooks,
                'symbols': list(self._orderbooks.keys()),
                'persistent_mode': self._persistent_mode,
                'memory_usage_estimate': memory_usage,
                'cache_size': len(self._aggregation_service._cache),
                'cache_metrics': await self._aggregation_service.get_cache_metrics()
            }
    
    async def _check_memory_usage(self) -> None:
        """Check memory usage and perform cleanup if necessary."""
        if len(self._orderbooks) > self._max_orderbooks * self._cleanup_threshold:
            await self._cleanup_old_orderbooks()
    
    async def _cleanup_old_orderbooks(self) -> None:
        """Clean up old order books to manage memory."""
        if self._persistent_mode:
            return  # Don't cleanup in persistent mode
        
        # Find order books with no connections
        symbols_to_remove = []
        for symbol in self._orderbooks:
            if not self._connections.get(symbol):
                symbols_to_remove.append(symbol)
        
        # Remove order books with no connections
        for symbol in symbols_to_remove:
            del self._orderbooks[symbol]
            logger.info(f"Cleaned up OrderBook for {symbol} (memory management)")
        
        if symbols_to_remove:
            logger.info(f"Cleaned up {len(symbols_to_remove)} order books for memory management")
    
    async def shutdown(self) -> None:
        """Shutdown the manager and cleanup resources."""
        async with self._lock:
            self._orderbooks.clear()
            self._connections.clear()
            self._connection_params.clear()
            self._symbol_data.clear()
            self._aggregation_service._cache.clear()
            
            logger.info("OrderBookManager shutdown complete")


# Global instance
orderbook_manager = OrderBookManager()