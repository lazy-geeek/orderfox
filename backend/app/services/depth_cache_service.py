"""
DepthCacheManager service for OrderFox.
Provides superior order book synchronization for Binance symbols using python-binance library.
"""

import asyncio
import logging
from typing import Dict, Optional, Set, Callable, Any, List, Tuple
from datetime import datetime

from binance import AsyncClient, DepthCacheManager

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("depth_cache_service")

# Configure binance logger to be less verbose
logging.getLogger('binance').setLevel(logging.WARNING)


class DepthCacheService:
    """Service for managing Binance depth caches with automatic synchronization."""
    
    def __init__(self):
        self.client: Optional[AsyncClient] = None
        self.depth_caches: Dict[str, DepthCacheManager] = {}
        self.active_streams: Dict[str, asyncio.Task] = {}
        self.callbacks: Dict[str, Set[Callable]] = {}
        self.latest_data: Dict[str, Dict[str, Any]] = {}  # Store latest depth data
        self._initialized = False
        self._lock = asyncio.Lock()
        
    async def initialize(self) -> None:
        """Initialize the Binance client."""
        async with self._lock:
            if self._initialized:
                return
                
            try:
                self.client = await AsyncClient.create(
                    api_key=settings.BINANCE_API_KEY,
                    api_secret=settings.BINANCE_SECRET_KEY
                )
                self._initialized = True
                logger.info("DepthCacheService initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize DepthCacheService: {str(e)}")
                raise
    
    async def start_depth_cache(self, symbol: str, callback: Callable[[str, Dict[str, Any]], Any]) -> None:
        """
        Start a depth cache for a symbol with a callback for updates.
        
        Args:
            symbol: The trading symbol (e.g., 'BTCUSDT')
            callback: Async function to call with updates (symbol, depth_data)
        """
        if not self._initialized:
            await self.initialize()
            
        # Convert symbol to uppercase for consistency
        symbol = symbol.upper()
        
        # Add callback to set
        if symbol not in self.callbacks:
            self.callbacks[symbol] = set()
        self.callbacks[symbol].add(callback)
        
        # Start stream if not already running
        if symbol not in self.active_streams:
            task = asyncio.create_task(self._stream_depth_cache(symbol))
            self.active_streams[symbol] = task
            logger.info(f"Started depth cache stream for {symbol}")
    
    async def stop_depth_cache(self, symbol: str, callback: Optional[Callable] = None) -> None:
        """
        Stop depth cache for a symbol or remove a specific callback.
        
        Args:
            symbol: The trading symbol
            callback: Optional specific callback to remove
        """
        symbol = symbol.upper()
        
        if callback and symbol in self.callbacks:
            self.callbacks[symbol].discard(callback)
            
        # If no callbacks remain or force stop, cancel the stream
        if symbol in self.callbacks and (not callback or not self.callbacks[symbol]):
            # Cancel the stream task
            if symbol in self.active_streams:
                self.active_streams[symbol].cancel()
                try:
                    await self.active_streams[symbol]
                except asyncio.CancelledError:
                    pass
                del self.active_streams[symbol]
                
            # Clean up
            if symbol in self.callbacks:
                del self.callbacks[symbol]
            if symbol in self.depth_caches:
                del self.depth_caches[symbol]
            if symbol in self.latest_data:
                del self.latest_data[symbol]
                
            logger.info(f"Stopped depth cache stream for {symbol}")
    
    async def _stream_depth_cache(self, symbol: str) -> None:
        """Internal method to stream depth cache updates."""
        max_retries = 5
        retry_delay = 5
        retry_count = 0
        
        while symbol in self.callbacks and self.callbacks[symbol]:
            try:
                # Create DepthCacheManager for this symbol
                dcm = DepthCacheManager(self.client, symbol)
                self.depth_caches[symbol] = dcm
                
                logger.info(f"Connecting to depth cache stream for {symbol}")
                
                async with dcm as dcm_socket:
                    retry_count = 0  # Reset on successful connection
                    
                    while symbol in self.callbacks and self.callbacks[symbol]:
                        try:
                            # Receive depth cache update
                            depth_cache = await dcm_socket.recv()
                            
                            # Process and broadcast the update
                            await self._process_depth_update(symbol, depth_cache)
                            
                        except Exception as e:
                            if "WebSocket" in str(e):
                                logger.warning(f"WebSocket error for {symbol}: {str(e)}")
                                break  # Reconnect
                            else:
                                logger.error(f"Error processing depth update for {symbol}: {str(e)}")
                                await asyncio.sleep(0.1)
                                
            except asyncio.CancelledError:
                logger.info(f"Depth cache stream cancelled for {symbol}")
                break
            except Exception as e:
                retry_count += 1
                logger.error(f"Error in depth cache stream for {symbol} (retry {retry_count}/{max_retries}): {str(e)}")
                
                if retry_count >= max_retries:
                    logger.error(f"Max retries reached for {symbol}. Stopping stream.")
                    break
                    
                await asyncio.sleep(retry_delay * retry_count)
    
    async def _process_depth_update(self, symbol: str, depth_cache) -> None:
        """Process a depth cache update and notify callbacks."""
        try:
            # Prepare depth data
            depth_data = {
                "symbol": symbol,
                "bids": depth_cache.get_bids(),
                "asks": depth_cache.get_asks(),
                "update_time": depth_cache.update_time,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            # Store latest data for later retrieval
            self.latest_data[symbol] = depth_data
            
            # Notify all callbacks for this symbol
            callbacks = list(self.callbacks.get(symbol, []))
            for callback in callbacks:
                try:
                    await callback(symbol, depth_data)
                except Exception as e:
                    logger.error(f"Error in depth cache callback for {symbol}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error processing depth update for {symbol}: {str(e)}")
    
    def get_current_orderbook(self, symbol: str, limit: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get current orderbook snapshot for a symbol.
        
        Args:
            symbol: The trading symbol
            limit: Optional limit for number of levels
            
        Returns:
            Dict with bids/asks or None if not available
        """
        symbol = symbol.upper()
        
        if symbol not in self.latest_data:
            return None
            
        try:
            data = self.latest_data[symbol]
            bids = data["bids"]
            asks = data["asks"]
            
            if limit:
                bids = bids[:limit]
                asks = asks[:limit]
                
            return {
                "symbol": symbol,
                "bids": [(float(price), float(amount)) for price, amount in bids],
                "asks": [(float(price), float(amount)) for price, amount in asks],
                "timestamp": data.get("timestamp", datetime.utcnow().isoformat())
            }
        except Exception as e:
            logger.error(f"Error getting orderbook for {symbol}: {str(e)}")
            return None
    
    async def aggregate_orderbook(
        self, 
        symbol: str, 
        rounding: float, 
        limit: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get aggregated orderbook for a symbol.
        
        Args:
            symbol: The trading symbol
            rounding: Price rounding value
            limit: Optional limit for number of levels
            
        Returns:
            Dict with aggregated bids/asks or None if not available
        """
        orderbook = self.get_current_orderbook(symbol)
        if not orderbook:
            return None
            
        try:
            # Aggregate bids
            aggregated_bids = self._aggregate_levels(
                orderbook["bids"], rounding, is_bid=True
            )
            
            # Aggregate asks
            aggregated_asks = self._aggregate_levels(
                orderbook["asks"], rounding, is_bid=False
            )
            
            # Apply limit if specified
            if limit:
                aggregated_bids = aggregated_bids[:limit]
                aggregated_asks = aggregated_asks[:limit]
                
            return {
                "symbol": symbol,
                "bids": aggregated_bids,
                "asks": aggregated_asks,
                "rounding": rounding,
                "aggregated": True,
                "timestamp": orderbook["timestamp"]
            }
        except Exception as e:
            logger.error(f"Error aggregating orderbook for {symbol}: {str(e)}")
            return None
    
    def _aggregate_levels(
        self, 
        levels: List[Tuple[float, float]], 
        rounding: float, 
        is_bid: bool
    ) -> List[Tuple[float, float]]:
        """Aggregate order book levels by rounding price."""
        aggregated: Dict[float, float] = {}
        
        for price, amount in levels:
            # Round price based on side
            if is_bid:
                # Round down for bids
                rounded_price = (price // rounding) * rounding
            else:
                # Round up for asks
                rounded_price = ((price + rounding - 0.0001) // rounding) * rounding
            
            # Aggregate amounts
            if rounded_price not in aggregated:
                aggregated[rounded_price] = 0.0
            aggregated[rounded_price] += amount
        
        # Sort and return
        sorted_levels: List[Tuple[float, float]] = sorted(aggregated.items(), key=lambda x: x[0], reverse=is_bid)
        return sorted_levels
    
    def is_symbol_active(self, symbol: str) -> bool:
        """Check if a symbol has an active depth cache stream."""
        return symbol.upper() in self.active_streams
    
    def get_active_symbols(self) -> List[str]:
        """Get list of symbols with active depth cache streams."""
        return list(self.active_streams.keys())
    
    async def shutdown(self) -> None:
        """Shutdown the service and clean up resources."""
        logger.info("Shutting down DepthCacheService")
        
        # Cancel all active streams
        symbols = list(self.active_streams.keys())
        for symbol in symbols:
            await self.stop_depth_cache(symbol)
        
        # Close client connection
        if self.client:
            await self.client.close_connection()
            self.client = None
            
        self._initialized = False
        logger.info("DepthCacheService shutdown complete")


# Global instance
depth_cache_service = DepthCacheService()