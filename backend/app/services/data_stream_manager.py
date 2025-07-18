"""
Data Stream Manager for optimizing WebSocket connections based on active bots.
"""

import logging
from typing import Set, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from cachetools import TTLCache
import asyncio

from app.services.bot_service import bot_service
from app.core.database import get_session

logger = logging.getLogger(__name__)


class DataStreamManager:
    """Service for managing WebSocket streams based on active bot requirements."""
    
    def __init__(self):
        """Initialize the data stream manager."""
        # Cache for active symbols (2-minute TTL - shorter than bot service)
        self._active_symbols_cache = TTLCache(maxsize=10, ttl=120)
        # Track currently active streams
        self._active_streams: Set[str] = set()
        # Track stream reference counts (how many bots need each symbol)
        self._stream_references: Dict[str, int] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        logger.info("DataStreamManager initialized")
    
    async def get_required_symbols(self, session: AsyncSession) -> Set[str]:
        """
        Get symbols that should have active streams based on active bots.
        
        Args:
            session: Database session
            
        Returns:
            Set[str]: Set of symbols that need active streams
        """
        try:
            # Check cache first
            cache_key = "required_symbols"
            if cache_key in self._active_symbols_cache:
                logger.debug("Cache hit for required symbols")
                return self._active_symbols_cache[cache_key]
            
            # Get active symbols from bot service
            active_symbols = await bot_service.get_active_symbols(session)
            required_symbols = set(active_symbols)
            
            # Cache the result
            self._active_symbols_cache[cache_key] = required_symbols
            
            logger.debug(f"Found {len(required_symbols)} required symbols: {required_symbols}")
            return required_symbols
            
        except Exception as e:
            logger.error(f"Failed to get required symbols: {e}")
            # Return empty set on error to avoid breaking streams
            return set()
    
    async def update_active_streams(self, session: AsyncSession) -> Dict[str, List[str]]:
        """
        Update active streams based on current bot requirements.
        
        Args:
            session: Database session
            
        Returns:
            Dict[str, List[str]]: Dictionary with 'start' and 'stop' lists of symbols
        """
        async with self._lock:
            try:
                # Get required symbols
                required_symbols = await self.get_required_symbols(session)
                
                # Determine which streams to start and stop
                symbols_to_start = required_symbols - self._active_streams
                symbols_to_stop = self._active_streams - required_symbols
                
                # Update active streams tracking
                self._active_streams = required_symbols.copy()
                
                # Update reference counts
                for symbol in symbols_to_start:
                    self._stream_references[symbol] = self._stream_references.get(symbol, 0) + 1
                
                for symbol in symbols_to_stop:
                    if symbol in self._stream_references:
                        self._stream_references[symbol] = max(0, self._stream_references[symbol] - 1)
                        if self._stream_references[symbol] == 0:
                            del self._stream_references[symbol]
                
                result = {
                    'start': list(symbols_to_start),
                    'stop': list(symbols_to_stop)
                }
                
                if symbols_to_start or symbols_to_stop:
                    logger.info(f"Stream update - Start: {symbols_to_start}, Stop: {symbols_to_stop}")
                else:
                    logger.debug("No stream changes needed")
                
                return result
                
            except Exception as e:
                logger.error(f"Failed to update active streams: {e}")
                return {'start': [], 'stop': []}
    
    async def should_stream_symbol(self, symbol: str, session: AsyncSession) -> bool:
        """
        Check if a symbol should have an active stream.
        
        Args:
            symbol: Trading symbol to check
            session: Database session
            
        Returns:
            bool: True if symbol should have an active stream
        """
        try:
            required_symbols = await self.get_required_symbols(session)
            should_stream = symbol in required_symbols
            
            logger.debug(f"Symbol {symbol} should stream: {should_stream}")
            return should_stream
            
        except Exception as e:
            logger.error(f"Failed to check if symbol {symbol} should stream: {e}")
            # Default to False on error to avoid unnecessary streams
            return False
    
    async def get_stream_reference_count(self, symbol: str) -> int:
        """
        Get the reference count for a symbol stream.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            int: Number of references to this stream
        """
        async with self._lock:
            count = self._stream_references.get(symbol, 0)
            logger.debug(f"Symbol {symbol} reference count: {count}")
            return count
    
    async def add_stream_reference(self, symbol: str) -> bool:
        """
        Add a reference to a symbol stream.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            bool: True if this is the first reference (stream should be started)
        """
        async with self._lock:
            current_count = self._stream_references.get(symbol, 0)
            self._stream_references[symbol] = current_count + 1
            self._active_streams.add(symbol)
            
            is_first_reference = current_count == 0
            logger.debug(f"Added reference to {symbol}, count: {self._stream_references[symbol]}, first: {is_first_reference}")
            return is_first_reference
    
    async def remove_stream_reference(self, symbol: str) -> bool:
        """
        Remove a reference to a symbol stream.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            bool: True if this was the last reference (stream should be stopped)
        """
        async with self._lock:
            if symbol not in self._stream_references:
                logger.warning(f"Attempted to remove reference for non-existent symbol: {symbol}")
                return False
            
            self._stream_references[symbol] -= 1
            
            if self._stream_references[symbol] <= 0:
                # Last reference removed
                del self._stream_references[symbol]
                self._active_streams.discard(symbol)
                logger.debug(f"Removed last reference to {symbol}, stream should stop")
                return True
            
            logger.debug(f"Removed reference to {symbol}, count: {self._stream_references[symbol]}")
            return False
    
    async def get_active_streams(self) -> Set[str]:
        """
        Get currently active streams.
        
        Returns:
            Set[str]: Set of symbols with active streams
        """
        async with self._lock:
            return self._active_streams.copy()
    
    async def get_stream_statistics(self) -> Dict[str, int]:
        """
        Get statistics about active streams.
        
        Returns:
            Dict[str, int]: Dictionary with stream statistics
        """
        async with self._lock:
            return {
                'active_streams': len(self._active_streams),
                'total_references': sum(self._stream_references.values()),
                'symbols_with_references': len(self._stream_references)
            }
    
    async def optimize_streams(self, session: AsyncSession) -> Dict[str, any]:
        """
        Perform stream optimization based on current bot states.
        
        Args:
            session: Database session
            
        Returns:
            Dict[str, any]: Optimization results
        """
        try:
            # Get current bot statistics
            bot_stats = await bot_service.get_bot_stats_by_symbol(session)
            
            # Get required symbols
            required_symbols = await self.get_required_symbols(session)
            
            # Calculate optimization metrics
            total_bots = sum(stat.total_count for stat in bot_stats)
            active_bots = sum(stat.active_count for stat in bot_stats)
            
            # Get stream statistics
            stream_stats = await self.get_stream_statistics()
            
            # Calculate efficiency metrics
            efficiency = {
                'total_bots': total_bots,
                'active_bots': active_bots,
                'required_streams': len(required_symbols),
                'active_streams': stream_stats['active_streams'],
                'stream_efficiency': (
                    stream_stats['active_streams'] / len(required_symbols)
                    if required_symbols else 1.0
                ),
                'bot_to_stream_ratio': (
                    active_bots / stream_stats['active_streams']
                    if stream_stats['active_streams'] > 0 else 0
                )
            }
            
            logger.info(f"Stream optimization metrics: {efficiency}")
            return efficiency
            
        except Exception as e:
            logger.error(f"Failed to optimize streams: {e}")
            return {'error': str(e)}
    
    def clear_cache(self):
        """Clear the active symbols cache and bot service cache."""
        self._active_symbols_cache.clear()
        # Also clear bot service cache to ensure fresh data
        bot_service._clear_caches()
        logger.debug("Cleared data stream manager cache and bot service cache")
    
    async def health_check(self) -> Dict[str, any]:
        """
        Perform health check on the data stream manager.
        
        Returns:
            Dict[str, any]: Health check results
        """
        try:
            stream_stats = await self.get_stream_statistics()
            
            health = {
                'status': 'healthy',
                'cache_size': len(self._active_symbols_cache),
                'cache_maxsize': self._active_symbols_cache.maxsize,
                'cache_ttl': self._active_symbols_cache.ttl,
                'active_streams': stream_stats['active_streams'],
                'total_references': stream_stats['total_references'],
                'timestamp': asyncio.get_event_loop().time()
            }
            
            logger.debug(f"Data stream manager health check: {health}")
            return health
            
        except Exception as e:
            logger.error(f"Data stream manager health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': asyncio.get_event_loop().time()
            }


# Create global instance
data_stream_manager = DataStreamManager()