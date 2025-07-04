from typing import List, Dict, Tuple, Optional
import math
import time
import asyncio
import logging

from ..models.orderbook import OrderBook
from .formatting_service import formatting_service

logger = logging.getLogger(__name__)


class OrderBookAggregationService:
    """
    Service for aggregating order book data with price rounding and level limiting.
    Ports the frontend aggregation logic to the backend.
    """
    
    def __init__(self):
        self._cache = {}
        self._cache_lock = asyncio.Lock()
        self._cache_ttl = 1.0  # 1 second TTL
        
        # Cache metrics
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_requests = 0
    
    @staticmethod
    def round_down(value: float, multiple: float) -> float:
        """
        Round a value down to the nearest multiple.
        Ported from frontend roundDown function.
        
        Args:
            value: The value to round
            multiple: The multiple to round to
            
        Returns:
            Rounded down value
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
        Ported from frontend roundUp function.
        
        Args:
            value: The value to round
            multiple: The multiple to round to
            
        Returns:
            Rounded up value
        """
        if multiple <= 0:
            return value
        
        # Handle floating point precision by scaling up, rounding, then scaling down
        scale = 1 / multiple
        return math.ceil(value * scale) / scale
    
    def get_exact_levels(self, raw_data: List[Dict], is_ask: bool, 
                        effective_depth: int, effective_rounding: float) -> List[Dict]:
        """
        Get exactly the needed number of levels with volume aggregation.
        Ported from frontend getExactLevels function.
        
        Args:
            raw_data: List of price/amount dictionaries
            is_ask: Whether this is ask data (True) or bid data (False)
            effective_depth: Number of levels to return
            effective_rounding: Price rounding value
            
        Returns:
            List of aggregated levels with exactly effective_depth items (or fewer if not enough non-zero levels)
        """
        buckets = {}
        
        # Debug logging for rounding issues
        if effective_rounding >= 1.0:
            logger.debug(f"Aggregating {'asks' if is_ask else 'bids'} with rounding={effective_rounding}, raw_data_count={len(raw_data)}")
        
        # Aggregate all raw data into price buckets
        for item in raw_data:
            price = item.get('price', 0)
            amount = item.get('amount', 0)
            
            if price <= 0 or amount <= 0:
                continue
                
            rounded_price = (self.round_up(price, effective_rounding) 
                           if is_ask else self.round_down(price, effective_rounding))
            
            # Debug logging for rounding issues
            if effective_rounding >= 1.0 and len(buckets) < 5:
                logger.debug(f"Price {price} -> rounded to {rounded_price} (rounding={effective_rounding})")
            
            existing_amount = buckets.get(rounded_price, 0)
            buckets[rounded_price] = existing_amount + amount
        
        # Debug logging for rounding issues
        if effective_rounding >= 1.0:
            logger.debug(f"Buckets after aggregation: {list(buckets.keys())[:10]}")  # Show first 10 prices
        
        # Convert to list with aggressive zero filtering BEFORE sorting
        # This ensures we only work with non-zero levels
        levels = []
        for price, amount in buckets.items():
            # Use a more aggressive threshold to catch floating point precision issues
            if amount > 1e-6:  # Changed from 1e-8 to 1e-6 for even more aggressive filtering
                levels.append({'price': price, 'amount': amount})
        
        # Sort: asks ascending (lowest first), bids descending (highest first)
        levels.sort(key=lambda x: x['price'], reverse=not is_ask)
        
        # Now take exactly effective_depth levels - all are guaranteed to be non-zero
        result_levels = levels[:effective_depth]
        
        # Final verification - ensure no zeros slipped through due to floating point issues
        result_levels = [level for level in result_levels if level['amount'] > 1e-6]
        
        # Debug logging final result only when there's an issue
        if len(result_levels) < effective_depth:
            # Use debug level for empty orderbooks (0 levels), warning for partial data
            if len(result_levels) == 0:
                logger.debug(f"[ORDERBOOK_AGGREGATION] Empty {'asks' if is_ask else 'bids'}: requested={effective_depth}, rounding={effective_rounding}")
            else:
                logger.warning(f"[ORDERBOOK_AGGREGATION] Insufficient {'asks' if is_ask else 'bids'} levels: requested={effective_depth}, got={len(result_levels)}, "
                              f"rounding={effective_rounding}")
        
        return result_levels
    
    def calculate_cumulative_totals(self, levels: List[Dict], is_ask: bool) -> List[Dict]:
        """
        Calculate cumulative totals for order book levels.
        
        Args:
            levels: List of aggregated levels (asks should be highest-first, bids highest-first)
            is_ask: Whether this is ask data
            
        Returns:
            List of levels with cumulative totals added
        """
        result = []
        
        if is_ask:
            # For asks (highest price first), cumulative total is from current level to end (all better prices)
            for i, level in enumerate(levels):
                cumulative_total = sum(l['amount'] for l in levels[i:])
                result.append({
                    'price': level['price'],
                    'amount': level['amount'],
                    'cumulative': cumulative_total
                })
        else:
            # For bids (highest price first), cumulative total is from top down
            for i, level in enumerate(levels):
                cumulative_total = sum(l['amount'] for l in levels[:i+1])
                result.append({
                    'price': level['price'],
                    'amount': level['amount'],
                    'cumulative': cumulative_total
                })
        
        return result
    
    def analyze_market_depth(self, raw_bids: List[Dict], raw_asks: List[Dict], 
                           effective_depth: int, effective_rounding: float) -> Dict:
        """
        Analyze market depth and provide warnings for insufficient data.
        
        Args:
            raw_bids: Raw bid data
            raw_asks: Raw ask data
            effective_depth: Requested depth
            effective_rounding: Price rounding value
            
        Returns:
            Dictionary with market depth analysis
        """
        min_required_raw_data = effective_depth * 10
        has_insufficient_data = (len(raw_bids) < min_required_raw_data or 
                               len(raw_asks) < min_required_raw_data)
        
        # Get aggregated levels to check actual available levels
        aggregated_bids = self.get_exact_levels(raw_bids, False, effective_depth, effective_rounding)
        aggregated_asks = self.get_exact_levels(raw_asks, True, effective_depth, effective_rounding)
        
        actual_levels = min(len(aggregated_bids), len(aggregated_asks))
        is_market_depth_limited = actual_levels < effective_depth
        
        return {
            'has_insufficient_raw_data': has_insufficient_data,
            'is_market_depth_limited': is_market_depth_limited,
            'actual_levels': actual_levels,
            'requested_levels': effective_depth,
            'raw_bids_count': len(raw_bids),
            'raw_asks_count': len(raw_asks),
            'min_required_raw_data': min_required_raw_data
        }
    
    def _generate_cache_key(self, symbol: str, limit: int, rounding: float, 
                          timestamp: float) -> str:
        """Generate a cache key for aggregated data."""
        # Round timestamp to nearest second for cache effectiveness
        rounded_timestamp = int(timestamp)
        return f"{symbol}:{limit}:{rounding}:{rounded_timestamp}"
    
    async def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Get data from cache if still valid."""
        async with self._cache_lock:
            self._total_requests += 1
            
            if cache_key in self._cache:
                cached_data, cached_time = self._cache[cache_key]
                if time.time() - cached_time < self._cache_ttl:
                    self._cache_hits += 1
                    return cached_data
                else:
                    # Remove expired entry
                    del self._cache[cache_key]
            
            self._cache_misses += 1
            return None
    
    async def _set_cache(self, cache_key: str, data: Dict) -> None:
        """Set data in cache."""
        async with self._cache_lock:
            self._cache[cache_key] = (data, time.time())
            
            # Simple cache cleanup - remove old entries
            if len(self._cache) > 100:  # Keep max 100 entries
                oldest_key = min(self._cache.keys(), 
                               key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
    
    async def aggregate_orderbook(self, orderbook: OrderBook, limit: int, 
                                rounding: float, symbol_data: Optional[Dict] = None) -> Dict:
        """
        Aggregate order book data with the specified parameters.
        
        Args:
            orderbook: OrderBook instance
            limit: Number of levels to return
            rounding: Price rounding value
            symbol_data: Optional symbol information for rounding options
            
        Returns:
            Dictionary with aggregated order book data
        """
        # Generate cache key
        cache_key = self._generate_cache_key(orderbook.symbol, limit, rounding, orderbook.timestamp)
        
        # Check cache first
        cached_result = await self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        # Start with a reasonable multiplier and increase if needed
        multiplier = max(100, int(rounding * 100)) if rounding >= 1 else 100
        max_attempts = 5
        attempt = 0
        
        while attempt < max_attempts:
            # Get snapshot with current multiplier
            snapshot = await orderbook.get_snapshot(limit * multiplier)
            
            # Convert to the format expected by aggregation functions
            # Filter out any potential zeros at this stage as well
            raw_bids = [{'price': level.price, 'amount': level.amount} 
                       for level in snapshot.bids if level.amount > 1e-10]
            raw_asks = [{'price': level.price, 'amount': level.amount} 
                       for level in snapshot.asks if level.amount > 1e-10]
            
            # Get aggregated levels
            aggregated_bids = self.get_exact_levels(raw_bids, False, limit, rounding)
            aggregated_asks = self.get_exact_levels(raw_asks, True, limit, rounding)
            
            # Check if we have enough non-zero levels
            if len(aggregated_bids) >= limit and len(aggregated_asks) >= limit:
                # We have enough levels, proceed
                break
            else:
                # Not enough levels, increase multiplier and try again
                logger.debug(f"[ORDERBOOK_AGGREGATION] Fetching more data for {orderbook.symbol}: "
                            f"current levels: bids={len(aggregated_bids)}, asks={len(aggregated_asks)}, requested={limit}")
                multiplier *= 2
                attempt += 1
        
        # If we still don't have enough levels after max attempts, log appropriately
        if len(aggregated_bids) < limit or len(aggregated_asks) < limit:
            # Use debug for completely empty orderbooks (initial load), warning for partial data
            if len(aggregated_bids) == 0 and len(aggregated_asks) == 0:
                logger.debug(f"[ORDERBOOK_AGGREGATION] Empty orderbook for {orderbook.symbol} after {max_attempts} attempts")
            else:
                logger.warning(f"[ORDERBOOK_AGGREGATION] Could not get {limit} levels for {orderbook.symbol} after {max_attempts} attempts. "
                              f"Got bids={len(aggregated_bids)}, asks={len(aggregated_asks)}")
        
        # Analyze market depth
        market_depth_info = self.analyze_market_depth(raw_bids, raw_asks, limit, rounding)
        
        # Calculate cumulative totals for bids (highest to lowest)
        bids_with_cumulative = self.calculate_cumulative_totals(aggregated_bids, False)
        
        # For asks: reverse order first (highest price at top), then calculate cumulative
        aggregated_asks.reverse()  # Now highest price first
        asks_with_cumulative = self.calculate_cumulative_totals(aggregated_asks, True)
        
        # Apply formatting to all levels if symbol_data is available
        if symbol_data:
            # Format bids
            for bid in bids_with_cumulative:
                bid['price_formatted'] = formatting_service.format_price(bid['price'], symbol_data)
                bid['amount_formatted'] = formatting_service.format_amount(bid['amount'], symbol_data)
                bid['cumulative_formatted'] = formatting_service.format_total(bid['cumulative'], symbol_data)
            
            # Format asks
            for ask in asks_with_cumulative:
                ask['price_formatted'] = formatting_service.format_price(ask['price'], symbol_data)
                ask['amount_formatted'] = formatting_service.format_amount(ask['amount'], symbol_data)
                ask['cumulative_formatted'] = formatting_service.format_total(ask['cumulative'], symbol_data)
        
        # Build result
        result = {
            'symbol': orderbook.symbol,
            'bids': bids_with_cumulative,
            'asks': asks_with_cumulative,
            'timestamp': orderbook.timestamp,
            'limit': limit,
            'rounding': rounding,
            'market_depth_info': market_depth_info
        }
        
        # Final verification log - check if any zeros in the result
        zero_bids_in_result = [b for b in result['bids'] if b['amount'] <= 1e-6]
        zero_asks_in_result = [a for a in result['asks'] if a['amount'] <= 1e-6]
        if zero_bids_in_result or zero_asks_in_result:
            logger.error(f"[ZERO_CHECK] CRITICAL: Zeros found in final result for {orderbook.symbol}! "
                        f"Zero bids: {zero_bids_in_result}, Zero asks: {zero_asks_in_result}")
        
        
        # Cache the result
        await self._set_cache(cache_key, result)
        
        return result
    
    async def get_cache_metrics(self) -> Dict:
        """
        Get cache performance metrics.
        
        Returns:
            Dictionary with cache statistics
        """
        async with self._cache_lock:
            hit_rate = (self._cache_hits / self._total_requests * 100) if self._total_requests > 0 else 0
            return {
                'cache_hits': self._cache_hits,
                'cache_misses': self._cache_misses,
                'total_requests': self._total_requests,
                'hit_rate_percent': round(hit_rate, 2),
                'cache_size': len(self._cache)
            }
    
    async def warm_cache_for_symbol(self, symbol: str, orderbook: OrderBook, 
                                  symbol_data: Optional[Dict] = None) -> None:
        """
        Pre-warm cache for common parameter combinations for a symbol.
        
        Args:
            symbol: Trading symbol
            orderbook: OrderBook instance
            symbol_data: Optional symbol information for rounding calculations
        """
        # Common depth limits used by most traders
        common_limits = [5, 10, 20, 50]
        
        # Calculate rounding options for this symbol
        current_price = None
        try:
            snapshot = await orderbook.get_snapshot(1)
            if snapshot.bids:
                current_price = snapshot.bids[0].price
            elif snapshot.asks:
                current_price = snapshot.asks[0].price
        except Exception:
            # If orderbook is empty or has issues, current_price will remain None
            pass
        
        # Use common rounding values for cache warming
        common_roundings = [0.01, 0.1, 1.0]  # Standard rounding values
        
        # Pre-calculate and cache common combinations
        for limit in common_limits:
            for rounding in common_roundings:
                try:
                    # This will calculate and cache the result
                    await self.aggregate_orderbook(orderbook, limit, rounding, symbol_data)
                except Exception as e:
                    # Don't let cache warming errors break the flow
                    logger.warning(f"Cache warming failed for {symbol} limit={limit} rounding={rounding}: {e}")
                    continue