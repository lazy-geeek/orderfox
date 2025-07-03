from typing import List, Dict, Tuple, Optional
import math
import time
import asyncio
import logging

from ..models.orderbook import OrderBook

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
            List of aggregated levels with exactly effective_depth items
        """
        buckets = {}
        
        # Aggregate all raw data into price buckets
        for item in raw_data:
            price = item.get('price', 0)
            amount = item.get('amount', 0)
            
            if price <= 0 or amount <= 0:
                continue
                
            rounded_price = (self.round_up(price, effective_rounding) 
                           if is_ask else self.round_down(price, effective_rounding))
            
            existing_amount = buckets.get(rounded_price, 0)
            buckets[rounded_price] = existing_amount + amount
        
        # Convert to list and sort
        levels = [{'price': price, 'amount': amount} 
                 for price, amount in buckets.items() 
                 if amount > 0]
        
        # Sort: asks ascending (lowest first), bids descending (highest first)
        levels.sort(key=lambda x: x['price'], reverse=not is_ask)
        
        # Take exactly effective_depth levels
        return levels[:effective_depth]
    
    def calculate_rounding_options(self, symbol_id: str, price_precision: Optional[int] = None,
                                 current_price: Optional[float] = None) -> Tuple[List[float], float]:
        """
        Calculate available rounding options for a symbol.
        Ported from frontend calculateAndSetRoundingOptions function.
        
        Args:
            symbol_id: Symbol identifier
            price_precision: Price precision for the symbol
            current_price: Current market price
            
        Returns:
            Tuple of (rounding_options, default_rounding)
        """
        if not symbol_id:
            return [], 0.01
        
        # Calculate baseRounding from pricePrecision
        base_rounding = 1 / (10 ** (price_precision or 2))
        
        # Generate options array starting with baseRounding
        options = [base_rounding]
        
        # If no current price, use conservative estimates based on symbol name
        if not current_price:
            if 'BTC' in symbol_id.upper():
                current_price = 50000
            elif 'ETH' in symbol_id.upper():
                current_price = 3000
            elif 'USDT' in symbol_id.upper() or 'USDC' in symbol_id.upper():
                current_price = 10  # Conservative for altcoins
            else:
                current_price = 100  # Default conservative estimate
        
        # Generate additional options by multiplying by 10
        next_option = base_rounding
        while len(options) < 7:  # Maximum 7 options
            next_option = next_option * 10
            
            # Stop if rounding becomes more than 1/10th of current price
            if next_option > current_price / 10:
                break
                
            # Safety net for absolute maximum
            if next_option > 1000:
                break
                
            options.append(next_option)
        
        # Set default rounding (third item if available, or second, or first)
        if len(options) >= 3:
            default_rounding = options[2]
        elif len(options) >= 2:
            default_rounding = options[1]
        else:
            default_rounding = base_rounding
        
        return options, default_rounding
    
    def calculate_cumulative_totals(self, levels: List[Dict], is_ask: bool) -> List[Dict]:
        """
        Calculate cumulative totals for order book levels.
        
        Args:
            levels: List of aggregated levels
            is_ask: Whether this is ask data
            
        Returns:
            List of levels with cumulative totals added
        """
        result = []
        
        if is_ask:
            # For asks, cumulative total is from current level to end
            for i, level in enumerate(levels):
                cumulative_total = sum(l['amount'] for l in levels[i:])
                result.append({
                    'price': level['price'],
                    'amount': level['amount'],
                    'cumulative': cumulative_total
                })
        else:
            # For bids, cumulative total is from top down
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
        
        # Get snapshot with more data for aggregation
        snapshot = await orderbook.get_snapshot(limit * 50)  # 50x multiplier for aggregation
        
        # Convert to the format expected by aggregation functions
        raw_bids = [{'price': level.price, 'amount': level.amount} for level in snapshot.bids]
        raw_asks = [{'price': level.price, 'amount': level.amount} for level in snapshot.asks]
        
        # Analyze market depth
        market_depth_info = self.analyze_market_depth(raw_bids, raw_asks, limit, rounding)
        
        # Get aggregated levels
        aggregated_bids = self.get_exact_levels(raw_bids, False, limit, rounding)
        aggregated_asks = self.get_exact_levels(raw_asks, True, limit, rounding)
        
        # Calculate cumulative totals
        bids_with_cumulative = self.calculate_cumulative_totals(aggregated_bids, False)
        asks_with_cumulative = self.calculate_cumulative_totals(aggregated_asks, True)
        
        # For asks display, reverse the order (highest price at top)
        asks_with_cumulative.reverse()
        
        # Calculate rounding options
        current_price = None
        if raw_bids:
            current_price = raw_bids[0]['price']
        elif raw_asks:
            current_price = raw_asks[0]['price']
        
        price_precision = symbol_data.get('pricePrecision') if symbol_data else None
        rounding_options, default_rounding = self.calculate_rounding_options(
            orderbook.symbol, price_precision, current_price
        )
        
        # Build result
        result = {
            'symbol': orderbook.symbol,
            'bids': bids_with_cumulative,
            'asks': asks_with_cumulative,
            'timestamp': orderbook.timestamp,
            'limit': limit,
            'rounding': rounding,
            'rounding_options': rounding_options,
            'default_rounding': default_rounding,
            'market_depth_info': market_depth_info
        }
        
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
        if orderbook.latest_snapshot:
            snapshot = await orderbook.get_snapshot(1)
            if snapshot.bids:
                current_price = snapshot.bids[0].price
            elif snapshot.asks:
                current_price = snapshot.asks[0].price
        
        price_precision = symbol_data.get('pricePrecision') if symbol_data else None
        rounding_options, _ = self.calculate_rounding_options(symbol, price_precision, current_price)
        
        # Take first 3 most common rounding values for warming
        common_roundings = rounding_options[:3] if len(rounding_options) >= 3 else rounding_options
        
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