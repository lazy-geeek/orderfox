"""
Market Data HTTP API endpoints.

This module provides FastAPI HTTP endpoints for fetching market data including
symbols, order books, and candlestick data from the exchange.
"""

import re
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from app.api.v1.schemas import SymbolInfo, OrderBook, OrderBookLevel, Candle
from app.services.exchange_service import exchange_service
from app.services.symbol_service import symbol_service
from app.core.logging_config import get_logger
from app.core.config import settings

logger = get_logger(__name__)

router = APIRouter()


@router.get("/symbols", response_model=List[SymbolInfo])
async def get_symbols():
    """
    Get all available USDT perpetual swap symbols from Binance.

    Returns:
        List[SymbolInfo]: List of available trading symbols

    Raises:
        HTTPException: If unable to fetch symbols from exchange
    """
    try:
        exchange = exchange_service.get_exchange()

        # Try to explicitly set the market type to futures
        exchange.options["defaultType"] = "future"

        # Load markets to get symbol information
        markets = exchange.load_markets()
        tickers = exchange.fetch_tickers()

        symbols = []

        for market_id, market in markets.items():
            # Filter for USDT-quoted active markets
            is_usdt_quoted = market.get("quote") == "USDT"
            is_active = market.get("active", True)

            # Must be a futures market (not spot)
            is_swap = market.get("type") == "swap"

            # Exclude spot markets explicitly
            is_spot = market.get("type") == "spot" or market.get("spot") == True

            if not (is_usdt_quoted and is_active and is_swap and not is_spot):
                continue

            # Get 24h volume from ticker data
            ticker = tickers.get(market["symbol"])

            volume24h = None
            if ticker and "info" in ticker and "quoteVolume" in ticker["info"]:
                try:
                    volume24h = float(ticker["info"]["quoteVolume"])
                except ValueError:
                    volume24h = (
                        None  # Handle cases where it might not be a valid number
                    )

            # Extract pricePrecision and tickSize
            price_precision = None
            tick_size = None

            # Extract pricePrecision from market['precision']['price']
            try:
                if (
                    market.get("precision")
                    and market["precision"].get("price") is not None
                ):
                    precision_value = market["precision"]["price"]
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
                    f"Could not extract pricePrecision for {market['symbol']}: {e}"
                )

            # Extract tickSize from market['info']['tickSize'] or market['limits']['price']['min']
            try:
                # First try market['info']['tickSize']
                if market.get("info") and market["info"].get("tickSize") is not None:
                    tick_size = float(market["info"]["tickSize"])
                # Fallback to market['limits']['price']['min']
                elif (
                    market.get("limits")
                    and market["limits"].get("price")
                    and market["limits"]["price"].get("min") is not None
                ):
                    tick_size = float(market["limits"]["price"]["min"])
                # Calculate from pricePrecision as fallback
                elif price_precision is not None:
                    tick_size = 10**-price_precision
            except (KeyError, TypeError, ValueError) as e:
                logger.warning(
                    f"Could not extract tickSize for {market['symbol']}: {e}"
                )

            # Log warnings if values couldn't be determined
            if price_precision is None:
                logger.warning(
                    f"pricePrecision could not be determined for {market['symbol']}"
                )
            if tick_size is None:
                logger.warning(
                    f"tickSize could not be determined for {market['symbol']}"
                )

            symbols.append(
                SymbolInfo(
                    id=market["id"],
                    symbol=market["symbol"],
                    base_asset=market["base"],
                    quote_asset=market["quote"],
                    ui_name=f"{market['base']}/{market['quote']}",
                    volume24h=volume24h,
                    pricePrecision=price_precision,
                    tickSize=tick_size,
                )
            )

        # Sort symbols by 24h volume in descending order,
        # with symbols without volume (None or 0) at the end
        symbols.sort(
            key=lambda x: (
                x.volume24h is None or x.volume24h == 0,
                -float(x.volume24h or 0),
            )
        )

        return symbols

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch symbols: {str(e)}"
        )


@router.get("/orderbook/{symbol}", response_model=OrderBook)
async def get_orderbook(
    symbol: str,
    limit: Optional[int] = Query(
        default=100,
        ge=1,
        le=settings.MAX_ORDERBOOK_LIMIT,
        description="Number of order book levels to fetch per side",
    ),
):
    """
    Get the current order book for a given symbol.

    Args:
        symbol: Trading symbol (e.g., 'BTCUSDT')
        limit: Number of order book levels to fetch per side (default: 100, max: configurable via settings)

    Returns:
        OrderBook: Current order book data

    Raises:
        HTTPException: If unable to fetch order book or symbol not found
    """
    try:
        # Validate and convert symbol using symbol service
        exchange_symbol = symbol_service.resolve_symbol_to_exchange_format(symbol)
        if not exchange_symbol:
            # Get suggestions for invalid symbol
            suggestions = symbol_service.get_symbol_suggestions(symbol)
            error_msg = f"Symbol {symbol} not found"
            if suggestions:
                error_msg += f". Did you mean: {', '.join(suggestions[:3])}?"
            raise HTTPException(status_code=404, detail=error_msg)

        exchange = exchange_service.get_exchange()

        # Fetch order book data using exchange symbol with limit
        order_book_data = exchange.fetch_order_book(exchange_symbol, limit=limit)

        # Convert to our schema format
        bids = [
            OrderBookLevel(price=float(bid[0]), amount=float(bid[1]))
            for bid in order_book_data["bids"]
        ]

        asks = [
            OrderBookLevel(price=float(ask[0]), amount=float(ask[1]))
            for ask in order_book_data["asks"]
        ]

        return OrderBook(
            symbol=symbol,
            bids=bids,
            asks=asks,
            timestamp=int(
                order_book_data["timestamp"]
            ),  # Keep as Unix timestamp in milliseconds
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch order book for {symbol}: {str(e)}"
        )


@router.get("/candles/{symbol}", response_model=List[Candle])
async def get_candles(
    symbol: str,
    timeframe: str = Query(
        default="1m", description="Timeframe (e.g., '1m', '5m', '1h', '1d')"
    ),
    limit: int = Query(
        default=100, ge=1, le=1000, description="Number of candles to fetch"
    ),
):
    """
    Get historical candlestick data for a given symbol.

    Args:
        symbol: Trading symbol (e.g., 'BTCUSDT')
        timeframe: Timeframe for candles (default: '1m')
        limit: Number of candles to fetch (default: 100, max: 1000)

    Returns:
        List[Candle]: List of candlestick data

    Raises:
        HTTPException: If unable to fetch candles or invalid parameters
    """
    # Validate timeframe first
    valid_timeframes = [
        "1m",
        "3m",
        "5m",
        "15m",
        "30m",
        "1h",
        "2h",
        "4h",
        "6h",
        "8h",
        "12h",
        "1d",
        "3d",
        "1w",
        "1M",
    ]
    if timeframe not in valid_timeframes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid timeframe. Valid options: {', '.join(valid_timeframes)}",
        )

    try:
        # Validate and convert symbol using symbol service
        exchange_symbol = symbol_service.resolve_symbol_to_exchange_format(symbol)
        if not exchange_symbol:
            # Get suggestions for invalid symbol
            suggestions = symbol_service.get_symbol_suggestions(symbol)
            error_msg = f"Symbol {symbol} not found"
            if suggestions:
                error_msg += f". Did you mean: {', '.join(suggestions[:3])}?"
            raise HTTPException(status_code=404, detail=error_msg)

        exchange = exchange_service.get_exchange()

        # Fetch OHLCV data using exchange symbol
        ohlcv_data = exchange.fetch_ohlcv(exchange_symbol, timeframe, limit=limit)

        # Convert to our schema format
        candles = []
        for ohlcv in ohlcv_data:
            candles.append(
                Candle(
                    timestamp=int(ohlcv[0]),  # Keep as Unix timestamp in milliseconds
                    open=float(ohlcv[1]),
                    high=float(ohlcv[2]),
                    low=float(ohlcv[3]),
                    close=float(ohlcv[4]),
                    volume=float(ohlcv[5]),
                )
            )

        return candles

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch candles for {symbol}: {str(e)}"
        )
