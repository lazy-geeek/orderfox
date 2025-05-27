"""
Market Data HTTP API endpoints.

This module provides FastAPI HTTP endpoints for fetching market data including
symbols, order books, and candlestick data from the exchange.
"""

import re
from typing import List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from app.api.v1.schemas import SymbolInfo, OrderBook, OrderBookLevel, Candle
from app.services.exchange_service import exchange_service

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

            symbols.append(
                SymbolInfo(
                    id=market["id"],
                    symbol=market["symbol"],
                    base_asset=market["base"],
                    quote_asset=market["quote"],
                    ui_name=f"{market['base']}/{market['quote']}",
                    volume24h=volume24h,
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
async def get_orderbook(symbol: str):
    """
    Get the current order book for a given symbol.

    Args:
        symbol: Trading symbol (e.g., 'BTCUSDT')

    Returns:
        OrderBook: Current order book data

    Raises:
        HTTPException: If unable to fetch order book or symbol not found
    """
    try:
        exchange = exchange_service.get_exchange()

        # Fetch order book data
        order_book_data = exchange.fetch_order_book(symbol)

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
            timestamp=datetime.fromtimestamp(order_book_data["timestamp"] / 1000),
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
        exchange = exchange_service.get_exchange()

        # Fetch OHLCV data
        ohlcv_data = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

        # Convert to our schema format
        candles = []
        for ohlcv in ohlcv_data:
            candles.append(
                Candle(
                    timestamp=datetime.fromtimestamp(ohlcv[0] / 1000),
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
