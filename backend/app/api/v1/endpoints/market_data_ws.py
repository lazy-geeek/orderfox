"""
Market Data WebSocket API endpoints.

This module provides FastAPI WebSocket endpoints for real-time market data
streaming including order books, tickers, and candlestick data.
"""

import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.exchange_service import exchange_service
from app.services.symbol_service import symbol_service
from app.api.v1.endpoints.connection_manager import connection_manager
from app.api.v1.endpoints.trading import trading_engine_service_instance
from app.core.logging_config import get_logger

logger = get_logger("market_data_ws")

router = APIRouter()


@router.websocket("/ws/orderbook/{symbol}")
async def websocket_orderbook(websocket: WebSocket, symbol: str):
    """
    WebSocket endpoint for real-time order book updates.

    Args:
        websocket: WebSocket connection
        symbol: Trading symbol (e.g., 'BTCUSDT')

    The WebSocket will send JSON messages with the following format:
    {
        "type": "orderbook_update",
        "symbol": "BTCUSDT",
        "bids": [{"price": 50000.0, "amount": 1.5}, ...],
        "asks": [{"price": 50100.0, "amount": 2.0}, ...],
        "timestamp": 1640995200000
    }

    Error messages have the format:
    {
        "type": "error",
        "message": "Error description"
    }
    """
    logger.info(
        f"WebSocket orderbook connection attempt for {symbol} from {websocket.client}"
    )

    try:
        # Accept connection first
        await websocket.accept()
        logger.info(f"WebSocket orderbook connection accepted for {symbol}")

        # Validate and convert symbol using symbol service
        exchange_symbol = symbol_service.resolve_symbol_to_exchange_format(symbol)
        if not exchange_symbol:
            # Get suggestions for invalid symbol
            suggestions = symbol_service.get_symbol_suggestions(symbol)
            error_msg = f"Symbol {symbol} not found"
            if suggestions:
                error_msg += f". Did you mean: {', '.join(suggestions[:3])}?"

            logger.warning(f"WebSocket orderbook error: {error_msg}")
            await websocket.send_text(
                json.dumps({"type": "error", "message": error_msg})
            )
            await websocket.close(code=4000, reason=error_msg)
            return

        logger.info(
            f"Using exchange symbol: {exchange_symbol} for WebSocket symbol: {symbol}"
        )

        # Connect to the connection manager using the exchange symbol
        await connection_manager.connect_orderbook(websocket, exchange_symbol, symbol)
        logger.info(
            f"WebSocket orderbook streaming started for {symbol} (exchange: {exchange_symbol})"
        )

        try:
            # Keep the connection alive and handle client messages
            while True:
                # Wait for client messages (ping/pong, etc.)
                try:
                    data = await websocket.receive_text()
                    # Handle client messages if needed (e.g., ping/pong)
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))
                except Exception:
                    # Client disconnected or sent invalid data
                    break

        except WebSocketDisconnect:
            logger.info(f"WebSocket orderbook client disconnected for {symbol}")
        finally:
            connection_manager.disconnect_orderbook(websocket, exchange_symbol)
            logger.info(f"WebSocket orderbook connection cleaned up for {symbol}")

    except Exception as e:
        logger.error(f"WebSocket orderbook error for {symbol}: {str(e)}", exc_info=True)
        try:
            if websocket.client_state.name != "DISCONNECTED":
                await websocket.send_text(
                    json.dumps(
                        {"type": "error", "message": f"Connection error: {str(e)}"}
                    )
                )
                await websocket.close(code=4000, reason=f"Connection error: {str(e)}")
        except Exception as close_error:
            logger.error(f"Error closing WebSocket for {symbol}: {str(close_error)}")


@router.websocket("/ws/ticker/{symbol}")
async def websocket_ticker(websocket: WebSocket, symbol: str):
    """
    WebSocket endpoint for real-time ticker updates.

    Args:
        websocket: WebSocket connection
        symbol: Trading symbol (e.g., 'BTCUSDT')

    The WebSocket will send JSON messages with the following format:
    {
        "type": "ticker_update",
        "symbol": "BTCUSDT",
        "last": 50000.0,
        "bid": 49999.5,
        "ask": 50000.5,
        "high": 51000.0,
        "low": 49000.0,
        "open": 49500.0,
        "close": 50000.0,
        "change": 500.0,
        "percentage": 1.01,
        "volume": 1250.75,
        "quote_volume": 62537500.0,
        "timestamp": 1640995200000
    }

    Error messages have the format:
    {
        "type": "error",
        "message": "Error description"
    }
    """
    logger.info(
        f"WebSocket ticker connection attempt for {symbol} from {websocket.client}"
    )

    try:
        # Accept connection first
        await websocket.accept()
        logger.info(f"WebSocket ticker connection accepted for {symbol}")

        # Validate and convert symbol using symbol service
        exchange_symbol = symbol_service.resolve_symbol_to_exchange_format(symbol)
        if not exchange_symbol:
            # Get suggestions for invalid symbol
            suggestions = symbol_service.get_symbol_suggestions(symbol)
            error_msg = f"Symbol {symbol} not found"
            if suggestions:
                error_msg += f". Did you mean: {', '.join(suggestions[:3])}?"

            logger.warning(f"WebSocket ticker error: {error_msg}")
            await websocket.send_text(
                json.dumps({"type": "error", "message": error_msg})
            )
            await websocket.close(code=4000, reason=error_msg)
            return

        # Connect to the connection manager using exchange symbol
        await connection_manager.connect(websocket, exchange_symbol, "ticker", symbol)
        logger.info(
            f"WebSocket ticker streaming started for {symbol} (exchange: {exchange_symbol})"
        )

        try:
            # Keep the connection alive and handle client messages
            while True:
                # Wait for client messages (ping/pong, etc.)
                try:
                    data = await websocket.receive_text()
                    # Handle client messages if needed (e.g., ping/pong)
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))
                except Exception:
                    # Client disconnected or sent invalid data
                    break

        except WebSocketDisconnect:
            logger.info(f"WebSocket ticker client disconnected for {symbol}")
        finally:
            connection_manager.disconnect(websocket, exchange_symbol)
            logger.info(f"WebSocket ticker connection cleaned up for {symbol}")

    except Exception as e:
        logger.error(f"WebSocket ticker error for {symbol}: {str(e)}", exc_info=True)
        try:
            if websocket.client_state.name != "DISCONNECTED":
                await websocket.send_text(
                    json.dumps(
                        {"type": "error", "message": f"Connection error: {str(e)}"}
                    )
                )
                await websocket.close(code=4000, reason=f"Connection error: {str(e)}")
        except Exception as close_error:
            logger.error(f"Error closing WebSocket for {symbol}: {str(close_error)}")


@router.websocket("/ws/candles/{symbol}/{timeframe}")
async def websocket_candles(websocket: WebSocket, symbol: str, timeframe: str):
    """
    WebSocket endpoint for real-time candle/OHLCV updates.

    Args:
        websocket: WebSocket connection
        symbol: Trading symbol (e.g., 'BTCUSDT')
        timeframe: Timeframe for candles (e.g., '1m', '5m', '1h', '1d')

    The WebSocket will send JSON messages with the following format:
    {
        "type": "candle_update",
        "symbol": "BTCUSDT",
        "timeframe": "1m",
        "timestamp": 1640995200000,
        "open": 49500.0,
        "high": 50100.0,
        "low": 49400.0,
        "close": 50000.0,
        "volume": 125.75
    }

    Error messages have the format:
    {
        "type": "error",
        "message": "Error description"
    }
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
        logger.warning(f"WebSocket candles invalid timeframe: {timeframe}")
        await websocket.accept()
        error_msg = f"Invalid timeframe. Valid options: {', '.join(valid_timeframes)}"
        await websocket.send_text(json.dumps({"type": "error", "message": error_msg}))
        await websocket.close(code=4000, reason=error_msg)
        return

    logger.info(
        f"WebSocket candles connection attempt for {symbol}/{timeframe} from {websocket.client}"
    )

    try:
        # Accept connection first
        await websocket.accept()
        logger.info(f"WebSocket candles connection accepted for {symbol}/{timeframe}")

        # Validate and convert symbol using symbol service
        exchange_symbol = symbol_service.resolve_symbol_to_exchange_format(symbol)
        if not exchange_symbol:
            # Get suggestions for invalid symbol
            suggestions = symbol_service.get_symbol_suggestions(symbol)
            error_msg = f"Symbol {symbol} not found"
            if suggestions:
                error_msg += f". Did you mean: {', '.join(suggestions[:3])}?"

            logger.warning(f"WebSocket candles error: {error_msg}")
            await websocket.send_text(
                json.dumps({"type": "error", "message": error_msg})
            )
            await websocket.close(code=4000, reason=error_msg)
            return

        # Create stream key for this symbol:timeframe combination using exchange symbol
        stream_key = f"{exchange_symbol}:{timeframe}"

        # Connect to the connection manager
        await connection_manager.connect(websocket, stream_key, "candles", symbol)
        logger.info(
            f"WebSocket candles streaming started for {symbol}/{timeframe} (exchange: {exchange_symbol})"
        )

        try:
            # Keep the connection alive and handle client messages
            while True:
                # Wait for client messages (ping/pong, etc.)
                try:
                    data = await websocket.receive_text()
                    # Handle client messages if needed (e.g., ping/pong)
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))
                except Exception:
                    # Client disconnected or sent invalid data
                    break

        except WebSocketDisconnect:
            logger.info(
                f"WebSocket candles client disconnected for {symbol}/{timeframe}"
            )
        finally:
            connection_manager.disconnect(websocket, stream_key)
            logger.info(
                f"WebSocket candles connection cleaned up for {symbol}/{timeframe}"
            )

    except Exception as e:
        logger.error(
            f"WebSocket candles error for {symbol}/{timeframe}: {str(e)}", exc_info=True
        )
        try:
            if websocket.client_state.name != "DISCONNECTED":
                await websocket.send_text(
                    json.dumps(
                        {"type": "error", "message": f"Connection error: {str(e)}"}
                    )
                )
                await websocket.close(code=4000, reason=f"Connection error: {str(e)}")
        except Exception as close_error:
            logger.error(
                f"Error closing WebSocket for {symbol}/{timeframe}: {str(close_error)}"
            )
