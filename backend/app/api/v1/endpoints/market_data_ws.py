"""
Market Data WebSocket API endpoints.

This module provides FastAPI WebSocket endpoints for real-time market data
streaming including order books, tickers, and candlestick data.
"""

import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.exchange_service import exchange_service
from app.api.v1.endpoints.connection_manager import connection_manager

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
    try:
        # Validate symbol exists by checking if we can fetch its order book
        exchange = exchange_service.get_exchange()
        await exchange.load_markets()

        if symbol not in exchange.markets:
            await websocket.close(code=4000, reason=f"Symbol {symbol} not found")
            return

        # Connect to the connection manager
        await connection_manager.connect_orderbook(websocket, symbol)

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
            pass
        finally:
            connection_manager.disconnect_orderbook(websocket, symbol)

    except Exception as e:
        try:
            await websocket.close(code=4000, reason=f"Connection error: {str(e)}")
        except Exception:
            pass


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
    try:
        # Validate symbol exists by checking if we can fetch its ticker
        exchange = exchange_service.get_exchange()
        await exchange.load_markets()

        if symbol not in exchange.markets:
            await websocket.close(code=4000, reason=f"Symbol {symbol} not found")
            return

        # Connect to the connection manager
        await connection_manager.connect(websocket, symbol, "ticker")

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
            pass
        finally:
            connection_manager.disconnect(websocket, symbol)

    except Exception as e:
        try:
            await websocket.close(code=4000, reason=f"Connection error: {str(e)}")
        except Exception:
            pass


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
        await websocket.close(
            code=4000,
            reason=f"Invalid timeframe. Valid options: {', '.join(valid_timeframes)}",
        )
        return

    try:
        # Validate symbol exists
        exchange = exchange_service.get_exchange()
        await exchange.load_markets()

        if symbol not in exchange.markets:
            await websocket.close(code=4000, reason=f"Symbol {symbol} not found")
            return

        # Create stream key for this symbol:timeframe combination
        stream_key = f"{symbol}:{timeframe}"

        # Connect to the connection manager
        await connection_manager.connect(websocket, stream_key, "candles")

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
            pass
        finally:
            connection_manager.disconnect(websocket, stream_key)

    except Exception as e:
        try:
            await websocket.close(code=4000, reason=f"Connection error: {str(e)}")
        except Exception:
            pass
