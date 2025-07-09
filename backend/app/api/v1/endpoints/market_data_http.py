"""
Market Data HTTP API endpoints.

This module provides FastAPI HTTP endpoints for fetching market data including
symbols, order books, and candlestick data from the exchange.
"""

from typing import List, Optional
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
        # Use Symbol Service as single source of truth for all symbol data
        symbol_data = symbol_service.get_all_symbols()
        
        # Convert to SymbolInfo schema objects
        symbols = []
        for symbol_dict in symbol_data:
            symbols.append(
                SymbolInfo(
                    id=symbol_dict["id"],
                    symbol=symbol_dict["symbol"],
                    base_asset=symbol_dict["base_asset"],
                    quote_asset=symbol_dict["quote_asset"],
                    ui_name=symbol_dict["ui_name"],
                    volume24h=symbol_dict["volume24h"],
                    pricePrecision=symbol_dict["pricePrecision"],
                    roundingOptions=symbol_dict["roundingOptions"],
                    defaultRounding=symbol_dict["defaultRounding"],
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
        exchange_symbol = symbol_service.resolve_symbol_to_exchange_format(
            symbol)
        if not exchange_symbol:
            # Get suggestions for invalid symbol
            suggestions = symbol_service.get_symbol_suggestions(symbol)
            error_msg = f"Symbol {symbol} not found"
            if suggestions:
                error_msg += f". Did you mean: {', '.join(suggestions[:3])}?"
            raise HTTPException(status_code=404, detail=error_msg)

        exchange = exchange_service.get_exchange()

        # Fetch order book data using exchange symbol with limit
        order_book_data = exchange.fetch_order_book(
            exchange_symbol, limit=limit)

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
            status_code=500,
            detail=f"Failed to fetch order book for {symbol}: {
                str(e)}")


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
            detail=f"Invalid timeframe. Valid options: {
                ', '.join(valid_timeframes)}",
        )

    try:
        # Validate and convert symbol using symbol service
        exchange_symbol = symbol_service.resolve_symbol_to_exchange_format(
            symbol)
        if not exchange_symbol:
            # Get suggestions for invalid symbol
            suggestions = symbol_service.get_symbol_suggestions(symbol)
            error_msg = f"Symbol {symbol} not found"
            if suggestions:
                error_msg += f". Did you mean: {', '.join(suggestions[:3])}?"
            raise HTTPException(status_code=404, detail=error_msg)

        exchange = exchange_service.get_exchange()

        # Fetch OHLCV data using exchange symbol
        ohlcv_data = exchange.fetch_ohlcv(
            exchange_symbol, timeframe, limit=limit)

        # Convert to our schema format
        candles = []
        for ohlcv in ohlcv_data:
            candles.append(
                Candle(
                    timestamp=int(ohlcv[0]),
                    # Keep as Unix timestamp in milliseconds
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
            status_code=500,
            detail=f"Failed to fetch candles for {symbol}: {
                str(e)}")


@router.post("/refresh-symbols")
async def refresh_symbols():
    """
    Refresh the symbol cache. Useful for development when symbols are updated.

    Returns:
        Dict with refresh status and cache statistics.
    """
    try:
        logger.info("Manual symbol cache refresh requested")
        symbol_service.refresh_cache()
        stats = symbol_service.get_cache_stats()
        logger.info(f"Symbol cache refreshed successfully: {stats}")
        return {
            "status": "success",
            "message": "Symbol cache refreshed successfully",
            "cache_stats": stats,
        }
    except Exception as e:
        logger.error(
            f"Failed to refresh symbol cache: {
                str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to refresh symbol cache: {str(e)}"
        )


@router.get("/symbol-cache-stats")
async def get_symbol_cache_stats():
    """
    Get symbol cache statistics for debugging.

    Returns:
        Dict with cache statistics.
    """
    try:
        stats = symbol_service.get_cache_stats()
        return {"status": "success", "cache_stats": stats}
    except Exception as e:
        logger.error(
            f"Failed to get symbol cache stats: {
                str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get symbol cache stats: {
                str(e)}")
