"""
Symbol Service for centralized symbol handling and conversion.

This module provides utilities for converting between symbol formats,
validating symbols, and providing suggestions for invalid symbols.
"""

import re
from typing import Optional, List, Dict, Any, Tuple
from app.services.exchange_service import exchange_service
from app.core.logging_config import get_logger

logger = get_logger("symbol_service")


class SymbolService:
    """Service for managing symbol format conversion and validation."""

    def __init__(self):
        self._symbol_cache: Dict[str, str] = {}
        self._exchange_to_id_cache: Dict[str, str] = {}
        self._markets_cache: Optional[Dict[str, Any]] = None
        self._cache_initialized = False

        # Fallback symbols for development/demo mode when exchange is not available
        self._fallback_symbols = {
            # Common USDT pairs
            "BTCUSDT": "BTC/USDT",
            "ETHUSDT": "ETH/USDT",
            "ADAUSDT": "ADA/USDT",
            "SOLUSDT": "SOL/USDT",
            "DOTUSDT": "DOT/USDT",
            "LINKUSDT": "LINK/USDT",
            "LTCUSDT": "LTC/USDT",
            "XRPUSDT": "XRP/USDT",
            "BCHUSDT": "BCH/USDT",
            "EOSUSDT": "EOS/USDT",
            "TRXUSDT": "TRX/USDT",
            "AVAXUSDT": "AVAX/USDT",
            "MATICUSDT": "MATIC/USDT",
            "ATOMUSDT": "ATOM/USDT",
            "FTMUSDT": "FTM/USDT",
            "NEARUSDT": "NEAR/USDT",
            "ALGOUSDT": "ALGO/USDT",
            "VETUSDT": "VET/USDT",
            "ICPUSDT": "ICP/USDT",
            "FILUSDT": "FIL/USDT",
            "AXSUSDT": "AXS/USDT",
            "SANDUSDT": "SAND/USDT",
            "MANAUSDT": "MANA/USDT",
            # Common BTC pairs
            "ETHBTC": "ETH/BTC",
            "ADABTC": "ADA/BTC",
            "SOLBTC": "SOL/BTC",
            "LINKBTC": "LINK/BTC",
            "LTCBTC": "LTC/BTC",
        }

    def _initialize_cache(self) -> None:
        """Initialize symbol caches from exchange markets."""
        if self._cache_initialized:
            return

        try:
            exchange = exchange_service.get_exchange()
            markets = exchange.load_markets()
            self._markets_cache = markets

            # Build bidirectional caches
            for market_symbol, market_info in markets.items():
                market_id = market_info.get("id")
                if market_id:
                    # Cache: ID -> Exchange Symbol (e.g., BTCUSDT -> BTC/USDT)
                    self._symbol_cache[market_id] = market_symbol
                    # Cache: Exchange Symbol -> ID (e.g., BTC/USDT -> BTCUSDT)
                    self._exchange_to_id_cache[market_symbol] = market_id

            self._cache_initialized = True
            logger.info(
                f"Symbol cache initialized with {len(self._symbol_cache)} symbols from exchange"
            )

        except Exception as e:
            logger.warning(f"Failed to initialize symbol cache from exchange: {str(e)}")
            logger.info("Falling back to demo symbols for development mode")

            # Use fallback symbols for development/demo mode
            for symbol_id, exchange_symbol in self._fallback_symbols.items():
                self._symbol_cache[symbol_id] = exchange_symbol
                self._exchange_to_id_cache[exchange_symbol] = symbol_id

            self._cache_initialized = True
            logger.info(
                f"Symbol cache initialized with {len(self._symbol_cache)} fallback symbols for demo mode"
            )

    def resolve_symbol_to_exchange_format(self, symbol_id: str) -> Optional[str]:
        """
        Convert symbol ID to exchange format.

        Args:
            symbol_id: Symbol ID (e.g., 'BTCUSDT')

        Returns:
            Exchange symbol format (e.g., 'BTC/USDT') or None if not found
        """
        self._initialize_cache()

        # First check if it's already in exchange format
        if symbol_id in self._exchange_to_id_cache:
            return symbol_id

        # Then check if we can convert from ID to exchange format
        exchange_symbol = self._symbol_cache.get(symbol_id)
        if exchange_symbol:
                return exchange_symbol

        logger.warning(f"Symbol {symbol_id} not found in cache")
        return None

    def resolve_exchange_to_id_format(self, exchange_symbol: str) -> Optional[str]:
        """
        Convert exchange symbol to ID format.

        Args:
            exchange_symbol: Exchange symbol (e.g., 'BTC/USDT')

        Returns:
            Symbol ID (e.g., 'BTCUSDT') or None if not found
        """
        self._initialize_cache()

        # First check if it's already in ID format
        if exchange_symbol in self._symbol_cache:
            return exchange_symbol

        # Then check if we can convert from exchange to ID format
        symbol_id = self._exchange_to_id_cache.get(exchange_symbol)
        if symbol_id:
                return symbol_id

        logger.warning(f"Exchange symbol {exchange_symbol} not found in cache")
        return None

    def validate_symbol_exists(self, symbol_id: str) -> bool:
        """
        Check if a symbol exists in the exchange.

        Args:
            symbol_id: Symbol ID to validate

        Returns:
            True if symbol exists, False otherwise
        """
        exchange_symbol = self.resolve_symbol_to_exchange_format(symbol_id)
        return exchange_symbol is not None

    def calculate_rounding_options(self, price_precision: Optional[int] = None, 
                                  current_price: Optional[float] = None) -> Tuple[List[float], float]:
        """
        Calculate available rounding options for a symbol.
        Based on price precision and optional current price.
        
        Args:
            price_precision: Number of decimal places for price accuracy
            current_price: Current market price (optional)
            
        Returns:
            Tuple of (rounding_options, default_rounding)
        """
        if price_precision is None:
            return [], 0.01
        
        # Calculate baseRounding from pricePrecision
        base_rounding = 1 / (10 ** price_precision)
        
        # Generate options array starting with baseRounding
        options = [base_rounding]
        
        # If current_price is available, limit options to 1/10th of price
        max_rounding = current_price / 10 if current_price else 1000
        
        # Generate additional options by multiplying by 10
        next_option = base_rounding
        while len(options) < 7:  # Maximum 7 options
            next_option = next_option * 10
            
            # Stop if rounding becomes more than max_rounding
            if next_option > max_rounding:
                break
                
            options.append(next_option)
        
        # Set default rounding (third item if available, or second, or first)
        if len(options) >= 3:
            default_rounding = options[2]  # Third option as default
        elif len(options) >= 2:
            default_rounding = options[1]
        else:
            default_rounding = base_rounding
        
        return options, default_rounding

    def get_symbol_info(self, symbol_id: str, current_price: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Get detailed symbol information.

        Args:
            symbol_id: Symbol ID to get info for
            current_price: Current market price for rounding limit calculation

        Returns:
            Symbol information dict or None if not found
        """
        self._initialize_cache()

        exchange_symbol = self.resolve_symbol_to_exchange_format(symbol_id)
        if not exchange_symbol or not self._markets_cache:
            return None

        market_info = self._markets_cache.get(exchange_symbol)
        if not market_info:
            return None

        # Extract price precision from market info
        price_precision = None
        try:
            if (
                market_info.get("precision")
                and market_info["precision"].get("price") is not None
            ):
                precision_value = market_info["precision"]["price"]
                if isinstance(precision_value, (int, float)):
                    # If it's already an integer, use it directly
                    if isinstance(precision_value, int):
                        price_precision = precision_value
                    else:
                        # If it's a float like 1e-8, calculate decimal places
                        if precision_value > 0 and precision_value < 1:
                            # Convert scientific notation to decimal places
                            price_precision = abs(
                                int(
                                    round(
                                        float(
                                            f"{precision_value:.10e}".split("e")[1]
                                        )
                                    )
                                )
                            )
                        else:
                            # If it's a regular float, convert to int
                            price_precision = int(precision_value)
        except (KeyError, TypeError, ValueError) as e:
            logger.warning(
                f"Could not extract pricePrecision for {exchange_symbol}: {e}"
            )

        # Extract amount precision from market info
        amount_precision = None
        try:
            if (
                market_info.get("precision")
                and market_info["precision"].get("amount") is not None
            ):
                precision_value = market_info["precision"]["amount"]
                if isinstance(precision_value, (int, float)):
                    # If it's already an integer, use it directly
                    if isinstance(precision_value, int):
                        amount_precision = precision_value
                    else:
                        # If it's a float like 1e-8, calculate decimal places
                        if precision_value > 0 and precision_value < 1:
                            # Convert scientific notation to decimal places
                            amount_precision = abs(
                                int(
                                    round(
                                        float(
                                            f"{precision_value:.10e}".split("e")[1]
                                        )
                                    )
                                )
                            )
                        else:
                            # If it's a regular float, convert to int
                            amount_precision = int(precision_value)
        except (KeyError, TypeError, ValueError) as e:
            logger.warning(
                f"Could not extract amountPrecision for {exchange_symbol}: {e}"
            )

        # Calculate rounding options based on price precision and current price
        rounding_options, default_rounding = self.calculate_rounding_options(price_precision, current_price)

        return {
            "id": market_info.get("id"),
            "symbol": exchange_symbol,
            "base_asset": market_info.get("base"),
            "quote_asset": market_info.get("quote"),
            "active": market_info.get("active", True),
            "type": market_info.get("type"),
            "spot": market_info.get("spot", False),
            "swap": market_info.get("type") == "swap",
            "future": market_info.get("future", False),
            "pricePrecision": price_precision,
            "amountPrecision": amount_precision,
            "roundingOptions": rounding_options,
            "defaultRounding": default_rounding,
        }

    def get_symbol_suggestions(
        self, invalid_symbol: str, max_suggestions: int = 5
    ) -> List[str]:
        """
        Get symbol suggestions for an invalid symbol.

        Args:
            invalid_symbol: The invalid symbol to find suggestions for
            max_suggestions: Maximum number of suggestions to return

        Returns:
            List of suggested symbol IDs
        """
        self._initialize_cache()

        # Use symbol cache (which includes fallback symbols if exchange failed)
        available_symbols = list(self._symbol_cache.keys())
        if not available_symbols:
            # If still empty, provide some basic suggestions
            available_symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]

        suggestions = []
        invalid_upper = invalid_symbol.upper()

        # Exact match (case insensitive)
        for symbol_id in available_symbols:
            if symbol_id.upper() == invalid_upper:
                suggestions.append(symbol_id)

        # Partial matches
        if len(suggestions) < max_suggestions:
            for symbol_id in available_symbols:
                if (
                    invalid_upper in symbol_id.upper()
                    or symbol_id.upper().startswith(invalid_upper)
                ) and symbol_id not in suggestions:
                    suggestions.append(symbol_id)
                    if len(suggestions) >= max_suggestions:
                        break

        # Similar patterns (e.g., BTCUSDT -> ETHUSDT, ADAUSDT, etc.)
        if len(suggestions) < max_suggestions:
            # Extract base pattern (e.g., USDT from BTCUSDT)
            pattern_match = re.search(r"(USDT|BUSD|BTC|ETH)$", invalid_upper)
            if pattern_match:
                quote_pattern = pattern_match.group(1)
                for symbol_id in available_symbols:
                    if (
                        symbol_id.upper().endswith(quote_pattern)
                        and symbol_id not in suggestions
                    ):
                        suggestions.append(symbol_id)
                        if len(suggestions) >= max_suggestions:
                            break

        return suggestions[:max_suggestions]

    def refresh_cache(self) -> None:
        """Force refresh of symbol caches."""
        logger.info("Refreshing symbol cache...")
        self._cache_initialized = False
        self._symbol_cache.clear()
        self._exchange_to_id_cache.clear()
        self._markets_cache = None
        self._initialize_cache()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for debugging."""
        self._initialize_cache()
        return {
            "initialized": self._cache_initialized,
            "symbol_count": len(self._symbol_cache),
            "exchange_symbol_count": len(self._exchange_to_id_cache),
            "markets_loaded": self._markets_cache is not None,
        }


# Global symbol service instance
symbol_service = SymbolService()
