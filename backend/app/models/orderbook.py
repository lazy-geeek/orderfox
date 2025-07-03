from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from sortedcontainers import SortedDict
import asyncio
import time


@dataclass
class OrderBookLevel:
    """Represents a single price level in the order book."""
    price: float
    amount: float
    
    def __post_init__(self):
        """Validate the order book level data."""
        if self.price <= 0:
            raise ValueError("Price must be positive")
        if self.amount < 0:
            raise ValueError("Amount must be non-negative")


@dataclass
class OrderBookSnapshot:
    """Represents a complete order book snapshot."""
    symbol: str
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    timestamp: float
    
    def __post_init__(self):
        """Validate the snapshot data."""
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        if self.timestamp <= 0:
            self.timestamp = time.time()


class OrderBook:
    """
    Thread-safe order book implementation with sorted price levels.
    Supports both full snapshots and delta updates.
    """
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.timestamp = time.time()
        self._lock = asyncio.Lock()
        
        # Use SortedDict for efficient price-based sorting
        # Bids: highest price first (descending)
        # Asks: lowest price first (ascending)
        self._bids = SortedDict(lambda x: -x)  # Negative for descending order
        self._asks = SortedDict()  # Positive for ascending order
        
        # Track last update time
        self._last_update = time.time()
    
    async def update_snapshot(self, snapshot: OrderBookSnapshot) -> None:
        """
        Update the order book with a full snapshot.
        
        Args:
            snapshot: Complete order book snapshot
        """
        if snapshot.symbol != self.symbol:
            raise ValueError(f"Symbol mismatch: expected {self.symbol}, got {snapshot.symbol}")
        
        async with self._lock:
            # Clear existing data
            self._bids.clear()
            self._asks.clear()
            
            # Update bids
            for level in snapshot.bids:
                if level.amount > 0:  # Only add non-zero amounts
                    self._bids[level.price] = level.amount
            
            # Update asks
            for level in snapshot.asks:
                if level.amount > 0:  # Only add non-zero amounts
                    self._asks[level.price] = level.amount
            
            self.timestamp = snapshot.timestamp
            self._last_update = time.time()
    
    async def update_delta(self, bids: List[OrderBookLevel], asks: List[OrderBookLevel], 
                          timestamp: float) -> None:
        """
        Update the order book with delta changes.
        
        Args:
            bids: List of bid level changes
            asks: List of ask level changes
            timestamp: Update timestamp
        """
        async with self._lock:
            # Update bids
            for level in bids:
                if level.amount == 0:
                    # Remove the level if amount is 0
                    self._bids.pop(level.price, None)
                else:
                    # Update or add the level
                    self._bids[level.price] = level.amount
            
            # Update asks
            for level in asks:
                if level.amount == 0:
                    # Remove the level if amount is 0
                    self._asks.pop(level.price, None)
                else:
                    # Update or add the level
                    self._asks[level.price] = level.amount
            
            self.timestamp = timestamp
            self._last_update = time.time()
    
    async def get_snapshot(self, limit: Optional[int] = None) -> OrderBookSnapshot:
        """
        Get a snapshot of the current order book.
        
        Args:
            limit: Maximum number of levels to return per side
            
        Returns:
            OrderBookSnapshot with current data
        """
        async with self._lock:
            # Get bids (highest price first)
            bid_items = list(self._bids.items())
            if limit:
                bid_items = bid_items[:limit]
            bids = [OrderBookLevel(price=price, amount=amount) for price, amount in bid_items]
            
            # Get asks (lowest price first)
            ask_items = list(self._asks.items())
            if limit:
                ask_items = ask_items[:limit]
            asks = [OrderBookLevel(price=price, amount=amount) for price, amount in ask_items]
            
            return OrderBookSnapshot(
                symbol=self.symbol,
                bids=bids,
                asks=asks,
                timestamp=self.timestamp
            )
    
    async def get_best_bid_ask(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Get the best bid and ask prices.
        
        Returns:
            Tuple of (best_bid_price, best_ask_price)
        """
        async with self._lock:
            best_bid = None
            best_ask = None
            
            if self._bids:
                best_bid = next(iter(self._bids))  # First key (highest price)
            
            if self._asks:
                best_ask = next(iter(self._asks))  # First key (lowest price)
            
            return best_bid, best_ask
    
    async def get_levels_count(self) -> Tuple[int, int]:
        """
        Get the count of bid and ask levels.
        
        Returns:
            Tuple of (bid_count, ask_count)
        """
        async with self._lock:
            return len(self._bids), len(self._asks)
    
    async def get_aggregated_view(self, limit: int, rounding: float) -> Dict:
        """
        Get an aggregated view of the order book with price rounding.
        This is a basic implementation - full aggregation logic will be in the service.
        
        Args:
            limit: Number of levels to return
            rounding: Price rounding value
            
        Returns:
            Dictionary with aggregated bid/ask data
        """
        async with self._lock:
            # This is a placeholder - actual aggregation will be handled by the service
            snapshot = await self.get_snapshot(limit * 10)  # Get more data for aggregation
            return {
                'symbol': self.symbol,
                'bids': [{'price': level.price, 'amount': level.amount} for level in snapshot.bids],
                'asks': [{'price': level.price, 'amount': level.amount} for level in snapshot.asks],
                'timestamp': self.timestamp,
                'limit': limit,
                'rounding': rounding
            }
    
    def is_empty(self) -> bool:
        """Check if the order book is empty."""
        return len(self._bids) == 0 and len(self._asks) == 0
    
    def get_age(self) -> float:
        """Get the age of the last update in seconds."""
        return time.time() - self._last_update
    
    def __repr__(self) -> str:
        return f"OrderBook(symbol={self.symbol}, bids={len(self._bids)}, asks={len(self._asks)})"