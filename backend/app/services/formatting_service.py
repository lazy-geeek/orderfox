"""
Formatting service for order book display values.

This service handles formatting of prices, amounts, and totals for order book display,
moving all formatting logic from frontend to backend for consistency.

Features:
- Dynamic precision based on value size and symbol characteristics
- Optional caching for repeated values (especially amounts)
- Scientific notation for very small values
- Compact notation (K/M) for large amounts
- Thread-safe singleton pattern
"""

import logging
import time
import threading
from typing import Dict, Optional, Any, Tuple
import math

logger = logging.getLogger(__name__)


class FormattingService:
    """
    Service for formatting order book display values.
    
    Features:
    - Thread-safe singleton pattern
    - Optional caching for performance optimization
    - Configurable cache TTL and size limits
    - Cache statistics and monitoring
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(FormattingService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, enable_cache: bool = True, cache_ttl: float = 300.0, max_cache_size: int = 10000):
        """
        Initialize the formatting service.
        
        Args:
            enable_cache: Whether to enable caching (default: True)
            cache_ttl: Cache time-to-live in seconds (default: 300 = 5 minutes)
            max_cache_size: Maximum number of cache entries (default: 10000)
        """
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._initialized = True
        self._enable_cache = enable_cache
        self._cache_ttl = cache_ttl
        self._max_cache_size = max_cache_size
        
        # Cache storage: key -> (value, timestamp)
        self._cache: Dict[str, Tuple[str, float]] = {}
        self._cache_lock = threading.RLock()
        
        # Cache statistics
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_requests = 0
        
        logger.info(f"FormattingService initialized (cache_enabled={enable_cache}, "
                   f"cache_ttl={cache_ttl}s, max_size={max_cache_size})")
    
    def _generate_cache_key(self, method: str, value: float, symbol_info: Optional[Dict]) -> str:
        """Generate a cache key for the given parameters."""
        symbol = symbol_info.get('symbol', 'DEFAULT') if symbol_info else 'DEFAULT'
        precision_key = ''
        
        if symbol_info:
            price_precision = symbol_info.get('pricePrecision', 2)
            amount_precision = symbol_info.get('amountPrecision', 8)
            precision_key = f"{price_precision}:{amount_precision}"
        
        return f"{method}:{symbol}:{precision_key}:{value}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """Get value from cache if it exists and is not expired."""
        if not self._enable_cache:
            return None
        
        with self._cache_lock:
            self._total_requests += 1
            
            if cache_key in self._cache:
                cached_value, timestamp = self._cache[cache_key]
                
                # Check if cache entry is still valid
                if time.time() - timestamp < self._cache_ttl:
                    self._cache_hits += 1
                    return cached_value
                else:
                    # Remove expired entry
                    del self._cache[cache_key]
            
            self._cache_misses += 1
            return None
    
    def _set_cache(self, cache_key: str, value: str) -> None:
        """Set value in cache."""
        if not self._enable_cache:
            return
        
        with self._cache_lock:
            # Clean up cache if it's getting too large
            if len(self._cache) >= self._max_cache_size:
                self._cleanup_expired_cache()
                
                # If still too large after cleanup, remove oldest entries
                if len(self._cache) >= self._max_cache_size:
                    # Remove 20% of oldest entries
                    entries_to_remove = max(1, len(self._cache) // 5)
                    oldest_entries = sorted(self._cache.items(), key=lambda x: x[1][1])[:entries_to_remove]
                    for key, _ in oldest_entries:
                        del self._cache[key]
            
            self._cache[cache_key] = (value, time.time())
    
    def _cleanup_expired_cache(self) -> None:
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._cache.items()
            if current_time - timestamp >= self._cache_ttl
        ]
        
        for key in expired_keys:
            del self._cache[key]
    
    def format_price(self, value: float, symbol_info: Optional[Dict] = None) -> str:
        """
        Format price value based on symbol precision.
        
        Args:
            value: Price value to format
            symbol_info: Symbol information containing precision data
            
        Returns:
            Formatted price string
        """
        if value is None or value == 0:
            return "0.00"
        
        # Check cache first (prices change frequently, so cache may have lower hit rate)
        cache_key = self._generate_cache_key('price', value, symbol_info)
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        try:
            # Get price precision from symbol info
            price_precision = 2  # Default fallback
            if symbol_info and 'pricePrecision' in symbol_info:
                price_precision = symbol_info['pricePrecision']
            
            # Handle very small numbers with scientific notation
            if abs(value) < 0.00001:
                result = f"{value:.2e}"
            else:
                # For prices, we want to show the actual value, not compact notation
                # Prices need to be precise for trading decisions
                result = f"{value:.{price_precision}f}"
            
            # Cache the result
            self._set_cache(cache_key, result)
            return result
            
        except (ValueError, TypeError, OverflowError) as e:
            logger.warning(f"Price formatting error for value {value}: {e}")
            return str(value)
    
    def format_amount(self, value: float, symbol_info: Optional[Dict] = None) -> str:
        """
        Format amount value with consistent precision per symbol.
        
        Args:
            value: Amount value to format
            symbol_info: Symbol information containing precision data
            
        Returns:
            Formatted amount string
        """
        if value is None or value == 0:
            return "0.00"
        
        # Check cache first (amounts have high repetition rate, so cache is very beneficial)
        cache_key = self._generate_cache_key('amount', value, symbol_info)
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        try:
            # Get amount precision from symbol info
            amount_precision = self.get_amount_precision(symbol_info)
            
            # Handle very small amounts with scientific notation
            if abs(value) < 0.00001:
                result = f"{value:.2e}"
            
            # Handle large amounts with compact notation (use 2 decimals for readability)
            elif abs(value) >= 1000000:
                result = f"{value / 1000000:.2f}M"
            elif abs(value) >= 1000:
                result = f"{value / 1000:.2f}K"
            
            # All other amounts - use consistent symbol precision (minimum 2 for readability)
            else:
                decimal_places = max(2, amount_precision)
                result = f"{value:.{decimal_places}f}"
            
            # Cache the result
            self._set_cache(cache_key, result)
            return result
                
        except (ValueError, TypeError, OverflowError) as e:
            logger.warning(f"Amount formatting error for value {value}: {e}")
            return str(value)
    
    def format_total(self, value: float, symbol_info: Optional[Dict] = None) -> str:
        """
        Format total (cumulative) value optimized for cumulative totals.
        
        Args:
            value: Total value to format
            symbol_info: Symbol information containing precision data
            
        Returns:
            Formatted total string
        """
        if value is None or value == 0:
            return "0.00"
        
        # Check cache first (totals may have moderate repetition)
        cache_key = self._generate_cache_key('total', value, symbol_info)
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        try:
            # Totals are often larger, so use compact notation more aggressively
            if abs(value) >= 1000000:
                result = f"{value / 1000000:.2f}M"
            elif abs(value) >= 1000:
                result = f"{value / 1000:.2f}K"
            elif abs(value) < 0.00001:
                result = f"{value:.2e}"
            elif abs(value) < 0.01:
                # Use 4 decimal places for small totals
                result = f"{value:.4f}"
            else:
                # Use 2 decimal places for regular totals
                result = f"{value:.2f}"
            
            # Cache the result
            self._set_cache(cache_key, result)
            return result
                
        except (ValueError, TypeError, OverflowError) as e:
            logger.warning(f"Total formatting error for value {value}: {e}")
            return str(value)
    
    def get_amount_precision(self, symbol_info: Optional[Dict] = None) -> int:
        """
        Calculate optimal decimal places for amount display based on symbol data.
        
        Args:
            symbol_info: Symbol information containing precision data
            
        Returns:
            Number of decimal places to use for amounts
        """
        if not symbol_info:
            return 2  # Default fallback
        
        try:
            # Check if amount precision is available
            if 'amountPrecision' in symbol_info:
                amount_precision = symbol_info['amountPrecision']
                if isinstance(amount_precision, int) and amount_precision >= 0:
                    return min(amount_precision, 8)  # Cap at 8 decimal places
            
            # Fallback to price precision if amount precision not available
            if 'pricePrecision' in symbol_info:
                price_precision = symbol_info['pricePrecision']
                if isinstance(price_precision, int) and price_precision >= 0:
                    return min(price_precision, 6)  # Cap at 6 for amounts
            
            # Default fallback
            return 2
            
        except (KeyError, TypeError, ValueError) as e:
            logger.warning(f"Amount precision calculation error: {e}")
            return 2
    
    def format_orderbook_level(self, level: Dict, symbol_info: Optional[Dict] = None) -> Dict:
        """
        Format an entire order book level with all fields.
        
        Args:
            level: Order book level dict with price, amount, cumulative
            symbol_info: Symbol information containing precision data
            
        Returns:
            Level dict with added formatted fields
        """
        try:
            formatted_level = level.copy()
            
            # Add formatted fields
            formatted_level['price_formatted'] = self.format_price(level.get('price', 0), symbol_info)
            formatted_level['amount_formatted'] = self.format_amount(level.get('amount', 0), symbol_info)
            formatted_level['cumulative_formatted'] = self.format_total(level.get('cumulative', 0), symbol_info)
            
            return formatted_level
            
        except Exception as e:
            logger.error(f"Error formatting order book level: {e}")
            # Return original level if formatting fails
            return level
    
    def clear_cache(self) -> None:
        """Clear all cached formatting results."""
        with self._cache_lock:
            self._cache.clear()
            logger.info("Formatting cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._cache_lock:
            hit_rate = (self._cache_hits / self._total_requests * 100) if self._total_requests > 0 else 0
            return {
                'cache_enabled': self._enable_cache,
                'cache_hits': self._cache_hits,
                'cache_misses': self._cache_misses,
                'total_requests': self._total_requests,
                'hit_rate_percent': round(hit_rate, 2),
                'cache_size': len(self._cache),
                'cache_ttl_seconds': self._cache_ttl,
                'max_cache_size': self._max_cache_size
            }
    
    def get_formatting_stats(self) -> Dict[str, Any]:
        """
        Get formatting service statistics.
        
        Returns:
            Dictionary with formatting statistics including cache stats
        """
        stats = {
            'service_initialized': self._initialized,
            'instance_id': id(self),
        }
        
        # Add cache statistics if caching is enabled
        if self._enable_cache:
            stats.update(self.get_cache_stats())
        
        return stats
    
    def configure_cache(self, enable_cache: Optional[bool] = None, 
                       cache_ttl: Optional[float] = None, 
                       max_cache_size: Optional[int] = None) -> None:
        """
        Reconfigure cache settings.
        
        Args:
            enable_cache: Whether to enable caching
            cache_ttl: Cache time-to-live in seconds
            max_cache_size: Maximum number of cache entries
        """
        with self._cache_lock:
            if enable_cache is not None:
                self._enable_cache = enable_cache
                if not enable_cache:
                    self._cache.clear()
                logger.info(f"Cache enabled: {enable_cache}")
            
            if cache_ttl is not None:
                self._cache_ttl = cache_ttl
                logger.info(f"Cache TTL set to: {cache_ttl}s")
            
            if max_cache_size is not None:
                self._max_cache_size = max_cache_size
                # Clean up if current cache is larger than new limit
                if len(self._cache) > max_cache_size:
                    self._cleanup_expired_cache()
                    if len(self._cache) > max_cache_size:
                        # Remove oldest entries to fit new limit
                        entries_to_remove = len(self._cache) - max_cache_size
                        oldest_entries = sorted(self._cache.items(), key=lambda x: x[1][1])[:entries_to_remove]
                        for key, _ in oldest_entries:
                            del self._cache[key]
                logger.info(f"Max cache size set to: {max_cache_size}")


# Global formatting service instance
formatting_service = FormattingService()