"""
OrderBook Processing Service

This module handles server-side order book aggregation and processing,
porting the logic from the frontend to enable backend-maintained order books.
"""

import math
import time
import hashlib
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN, ROUND_UP
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cached aggregated order book entry."""
    result: 'AggregatedOrderBook'
    timestamp: float
    access_count: int = 0
    last_access: float = 0.0
    
    def update_access(self):
        """Update access statistics."""
        self.access_count += 1
        self.last_access = time.time()


class OrderBookCache:
    """
    LRU Cache for aggregated order book results.
    
    Caches results by symbol + rounding + depth combination to avoid
    recomputation of expensive aggregation operations.
    """
    
    def __init__(self, max_size: int = 100, ttl_seconds: float = 30.0):
        """
        Initialize the cache.
        
        Args:
            max_size: Maximum number of cache entries
            ttl_seconds: Time-to-live for cache entries
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.hit_count = 0
        self.miss_count = 0
        self.invalidation_count = 0
        self.logger = logging.getLogger(__name__)
    
    def _generate_cache_key(self, symbol: str, rounding: float, depth: int, source: str) -> str:
        """Generate a unique cache key for the given parameters."""
        key_data = f"{symbol}:{rounding}:{depth}:{source}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if a cache entry has expired."""
        return time.time() - entry.timestamp > self.ttl_seconds
    
    def _evict_expired(self):
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time - entry.timestamp > self.ttl_seconds
        ]
        
        for key in expired_keys:
            del self.cache[key]
            self.logger.debug(f"Evicted expired cache entry: {key}")
    
    def _evict_lru(self):
        """Remove least recently used entry to make space."""
        if self.cache:
            lru_key, _ = self.cache.popitem(last=False)
            self.logger.debug(f"Evicted LRU cache entry: {lru_key}")
    
    def get(self, symbol: str, rounding: float, depth: int, source: str) -> Optional['AggregatedOrderBook']:
        """
        Get cached aggregated order book if available and not expired.
        
        Args:
            symbol: Trading symbol
            rounding: Price rounding multiple
            depth: Order book depth
            source: Data source
            
        Returns:
            Cached AggregatedOrderBook or None if not found/expired
        """
        key = self._generate_cache_key(symbol, rounding, depth, source)
        
        # Clean up expired entries
        self._evict_expired()
        
        if key in self.cache:
            entry = self.cache[key]
            if not self._is_expired(entry):
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                entry.update_access()
                self.hit_count += 1
                self.logger.debug(f"Cache hit for {symbol} (rounding: {rounding}, depth: {depth})")
                return entry.result
            else:
                # Entry expired, remove it
                del self.cache[key]
                self.logger.debug(f"Cache entry expired for {symbol}")
        
        self.miss_count += 1
        self.logger.debug(f"Cache miss for {symbol} (rounding: {rounding}, depth: {depth})")
        return None
    
    def put(self, symbol: str, rounding: float, depth: int, source: str, result: 'AggregatedOrderBook'):
        """
        Store aggregated order book result in cache.
        
        Args:
            symbol: Trading symbol
            rounding: Price rounding multiple
            depth: Order book depth
            source: Data source
            result: Aggregated order book to cache
        """
        key = self._generate_cache_key(symbol, rounding, depth, source)
        
        # Make space if needed
        while len(self.cache) >= self.max_size:
            self._evict_lru()
        
        # Store new entry
        entry = CacheEntry(
            result=result,
            timestamp=time.time()
        )
        entry.update_access()
        
        self.cache[key] = entry
        self.logger.debug(f"Cached result for {symbol} (rounding: {rounding}, depth: {depth})")
    
    def invalidate(self, symbol: str):
        """
        Invalidate all cache entries for a specific symbol.
        
        Args:
            symbol: Trading symbol to invalidate
        """
        keys_to_remove = []
        for key, entry in self.cache.items():
            if entry.result.symbol == symbol:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.cache[key]
            self.invalidation_count += 1
        
        if keys_to_remove:
            self.logger.debug(f"Invalidated {len(keys_to_remove)} cache entries for {symbol}")
    
    def invalidate_all(self):
        """Clear all cache entries."""
        count = len(self.cache)
        self.cache.clear()
        self.invalidation_count += count
        self.logger.debug(f"Invalidated all {count} cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total_requests if total_requests > 0 else 0.0
        
        return {
            "cache_size": len(self.cache),
            "max_size": self.max_size,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": hit_rate,
            "invalidation_count": self.invalidation_count,
            "ttl_seconds": self.ttl_seconds
        }
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed cache statistics including entry information."""
        stats = self.get_stats()
        
        # Add entry details
        entries_info = []
        current_time = time.time()
        
        for key, entry in self.cache.items():
            age = current_time - entry.timestamp
            entries_info.append({
                "symbol": entry.result.symbol,
                "rounding": entry.result.rounding,
                "depth": entry.result.depth,
                "source": entry.result.source,
                "age_seconds": age,
                "access_count": entry.access_count,
                "is_expired": self._is_expired(entry)
            })
        
        stats["entries"] = entries_info
        return stats


@dataclass
class OrderBookLevel:
    """Represents a single order book level with price and amount."""
    price: float
    amount: float


@dataclass
class AggregatedOrderBook:
    """Represents a fully aggregated order book with metadata."""
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    symbol: str
    rounding: float
    depth: int
    source: str
    timestamp: Optional[int] = None
    aggregated: bool = True
    
    def validate(self) -> bool:
        """Validate the aggregated order book structure."""
        try:
            # Check basic structure
            if not isinstance(self.bids, list) or not isinstance(self.asks, list):
                return False
            
            # Check bids are sorted descending (highest price first)
            for i in range(len(self.bids) - 1):
                if self.bids[i].price < self.bids[i + 1].price:
                    logger.warning(f"Bid sorting violation at index {i}: {self.bids[i].price} < {self.bids[i + 1].price}")
                    return False
            
            # Check asks are sorted ascending (lowest price first)
            for i in range(len(self.asks) - 1):
                if self.asks[i].price > self.asks[i + 1].price:
                    logger.warning(f"Ask sorting violation at index {i}: {self.asks[i].price} > {self.asks[i + 1].price}")
                    return False
            
            # Check all amounts are positive
            for bid in self.bids:
                if bid.amount <= 0:
                    logger.warning(f"Invalid bid amount: {bid.amount}")
                    return False
            
            for ask in self.asks:
                if ask.amount <= 0:
                    logger.warning(f"Invalid ask amount: {ask.amount}")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Order book validation error: {e}")
            return False


class OrderBookProcessor:
    """
    Handles order book aggregation and processing with caching support.
    
    Ports the frontend aggregation logic to the backend for server-side processing.
    Includes comprehensive caching to improve performance.
    """
    
    def __init__(self, cache_size: int = 100, cache_ttl: float = 30.0):
        """
        Initialize the processor with caching.
        
        Args:
            cache_size: Maximum number of cached results
            cache_ttl: Cache time-to-live in seconds
        """
        self.logger = logging.getLogger(__name__)
        self.cache = OrderBookCache(max_size=cache_size, ttl_seconds=cache_ttl)
    
    @staticmethod
    def round_down(value: float, multiple: float) -> float:
        """
        Round a value down to the nearest multiple.
        
        Uses scaling approach to handle floating-point precision issues.
        Ported from frontend roundDown function.
        
        Args:
            value: The value to round
            multiple: The multiple to round to
            
        Returns:
            The rounded-down value
        """
        if multiple <= 0:
            return value
        
        # Handle floating point precision by scaling up, rounding, then scaling down
        scale = 1 / multiple
        return math.floor(value * scale) / scale
    
    @staticmethod
    def round_up(value: float, multiple: float) -> float:
        """
        Round a value up to the nearest multiple.
        
        Uses scaling approach to handle floating-point precision issues.
        Ported from frontend roundUp function.
        
        Args:
            value: The value to round
            multiple: The multiple to round to
            
        Returns:
            The rounded-up value
        """
        if multiple <= 0:
            return value
        
        # Handle floating point precision by scaling up, rounding, then scaling down
        scale = 1 / multiple
        return math.ceil(value * scale) / scale
    
    def aggregate_levels(
        self, 
        raw_data: List[List[float]], 
        rounding: float, 
        depth: int, 
        is_ask: bool
    ) -> List[OrderBookLevel]:
        """
        Aggregate raw order book levels into rounded price buckets.
        
        Ported from frontend getExactLevels function.
        
        Args:
            raw_data: Raw order book data [[price, amount], ...]
            rounding: Rounding multiple for price aggregation
            depth: Maximum number of levels to return
            is_ask: True for asks (sell orders), False for bids (buy orders)
            
        Returns:
            List of aggregated order book levels
        """
        # Use dictionary for price bucket aggregation
        buckets: Dict[float, float] = {}
        
        # Aggregate all raw data into price buckets
        for item in raw_data:
            if len(item) < 2:
                continue
                
            price, amount = float(item[0]), float(item[1])
            
            # Round price based on order type
            rounded_price = (
                self.round_up(price, rounding) if is_ask 
                else self.round_down(price, rounding)
            )
            
            # Accumulate amounts for the same rounded price
            existing_amount = buckets.get(rounded_price, 0.0)
            buckets[rounded_price] = existing_amount + amount
        
        # Convert to list and filter positive amounts
        levels = [
            OrderBookLevel(price=price, amount=amount)
            for price, amount in buckets.items()
            if amount > 0
        ]
        
        # Sort based on order type
        if is_ask:
            # Asks: lowest price first (ascending)
            levels.sort(key=lambda x: x.price)
        else:
            # Bids: highest price first (descending)
            levels.sort(key=lambda x: x.price, reverse=True)
        
        # Return exactly depth levels
        return levels[:depth]
    
    def process_orderbook(
        self,
        raw_orderbook: Dict,
        symbol: str,
        rounding: float = 0.01,
        depth: int = 20,
        source: str = "ccxtpro",
        use_cache: bool = True
    ) -> AggregatedOrderBook:
        """
        Process raw order book data into aggregated format with caching.
        
        Args:
            raw_orderbook: Raw order book data with 'bids' and 'asks' keys
            symbol: Trading symbol
            rounding: Price rounding multiple
            depth: Maximum depth levels
            source: Data source identifier
            use_cache: Whether to use caching (default: True)
            
        Returns:
            AggregatedOrderBook instance
        """
        try:
            # Check cache first if enabled
            if use_cache:
                cached_result = self.cache.get(symbol, rounding, depth, source)
                if cached_result is not None:
                    # Update timestamp with fresh data
                    cached_result.timestamp = raw_orderbook.get('timestamp')
                    return cached_result
            # Extract raw data
            raw_bids = raw_orderbook.get('bids', [])
            raw_asks = raw_orderbook.get('asks', [])
            
            # Market depth validation (similar to frontend)
            min_required_raw_data = depth * 10  # 10x multiplier for aggregation
            has_insufficient_data = (
                len(raw_asks) < min_required_raw_data or 
                len(raw_bids) < min_required_raw_data
            )
            
            if has_insufficient_data:
                self.logger.warning(
                    f"Limited market depth for {symbol} at ${rounding} rounding. "
                    f"Raw data: {len(raw_asks)} asks, {len(raw_bids)} bids. "
                    f"Recommended: {min_required_raw_data}+"
                )
            
            # Aggregate levels
            aggregated_bids = self.aggregate_levels(raw_bids, rounding, depth, is_ask=False)
            aggregated_asks = self.aggregate_levels(raw_asks, rounding, depth, is_ask=True)
            
            # Market depth feedback
            actual_levels = min(len(aggregated_asks), len(aggregated_bids))
            is_market_depth_limited = actual_levels < depth
            
            if is_market_depth_limited:
                self.logger.info(
                    f"📊 Market depth limited: {actual_levels}/{depth} levels "
                    f"for {symbol} at ${rounding} rounding"
                )
                self.logger.info(
                    "💡 This is normal for high rounding values - actual market orders "
                    "may only exist within a narrow price range"
                )
            
            # Create aggregated order book
            aggregated_book = AggregatedOrderBook(
                bids=aggregated_bids,
                asks=aggregated_asks,
                symbol=symbol,
                rounding=rounding,
                depth=depth,
                source=source,
                timestamp=raw_orderbook.get('timestamp')
            )
            
            # Validate structure
            if not aggregated_book.validate():
                self.logger.error(f"Invalid aggregated order book for {symbol}")
                raise ValueError(f"Order book validation failed for {symbol}")
            
            # Cache the result if caching is enabled
            if use_cache:
                self.cache.put(symbol, rounding, depth, source, aggregated_book)
            
            return aggregated_book
            
        except Exception as e:
            self.logger.error(f"Error processing order book for {symbol}: {e}")
            raise
    
    def supports_ccxtpro_format(self, raw_orderbook: Dict) -> bool:
        """Check if raw order book is in ccxtpro format."""
        return (
            isinstance(raw_orderbook, dict) and
            'bids' in raw_orderbook and
            'asks' in raw_orderbook and
            isinstance(raw_orderbook['bids'], list) and
            isinstance(raw_orderbook['asks'], list)
        )
    
    def supports_depth_cache_format(self, depth_cache_data: any) -> bool:
        """
        Check if data is from DepthCacheManager.
        
        DepthCacheManager returns sorted dictionaries of {price: amount}
        """
        try:
            # Check if it has get_bids() and get_asks() methods (DepthCacheManager)
            return hasattr(depth_cache_data, 'get_bids') and hasattr(depth_cache_data, 'get_asks')
        except:
            return False
    
    def process_depth_cache(
        self,
        depth_cache,
        symbol: str,
        rounding: float = 0.01,
        depth: int = 20,
        use_cache: bool = True
    ) -> AggregatedOrderBook:
        """
        Process DepthCacheManager data into aggregated format with caching.
        
        Args:
            depth_cache: DepthCacheManager instance
            symbol: Trading symbol
            rounding: Price rounding multiple
            depth: Maximum depth levels
            use_cache: Whether to use caching (default: True)
            
        Returns:
            AggregatedOrderBook instance
        """
        try:
            # Get sorted data from DepthCacheManager
            bids_dict = depth_cache.get_bids()  # {price: amount} sorted descending
            asks_dict = depth_cache.get_asks()  # {price: amount} sorted ascending
            
            # Convert to list format [[price, amount], ...]
            raw_bids = [[float(price), float(amount)] for price, amount in bids_dict.items()]
            raw_asks = [[float(price), float(amount)] for price, amount in asks_dict.items()]
            
            # Create raw orderbook format
            raw_orderbook = {
                'bids': raw_bids,
                'asks': raw_asks,
                'timestamp': None  # DepthCacheManager doesn't provide timestamps
            }
            
            # Process using standard logic
            return self.process_orderbook(
                raw_orderbook=raw_orderbook,
                symbol=symbol,
                rounding=rounding,
                depth=depth,
                source="depth_cache",
                use_cache=use_cache
            )
            
        except Exception as e:
            self.logger.error(f"Error processing depth cache for {symbol}: {e}")
            raise
    
    def invalidate_cache(self, symbol: str = None):
        """
        Invalidate cache entries.
        
        Args:
            symbol: Specific symbol to invalidate, or None to clear all
        """
        if symbol:
            self.cache.invalidate(symbol)
            self.logger.info(f"Invalidated cache entries for {symbol}")
        else:
            self.cache.invalidate_all()
            self.logger.info("Invalidated all cache entries")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        return self.cache.get_stats()
    
    def get_detailed_cache_stats(self) -> Dict[str, Any]:
        """Get detailed cache statistics."""
        return self.cache.get_detailed_stats()
    
    def configure_cache(self, max_size: int = None, ttl_seconds: float = None):
        """
        Reconfigure cache settings.
        
        Args:
            max_size: New maximum cache size
            ttl_seconds: New cache TTL in seconds
        """
        if max_size is not None:
            self.cache.max_size = max_size
            # Evict excess entries if needed
            while len(self.cache.cache) > max_size:
                self.cache._evict_lru()
            self.logger.info(f"Updated cache max_size to {max_size}")
        
        if ttl_seconds is not None:
            self.cache.ttl_seconds = ttl_seconds
            self.logger.info(f"Updated cache TTL to {ttl_seconds} seconds")