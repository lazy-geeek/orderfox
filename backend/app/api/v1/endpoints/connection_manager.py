"""
WebSocket Connection Manager for real-time data streaming.

This module provides the ConnectionManager class that handles WebSocket connections
for real-time market data streaming including order books, tickers, and candles.
"""

from typing import List, Dict, Any
import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect
from app.services.exchange_service import exchange_service
from app.services.trading_engine_service import TradingEngineService
from app.core.logging_config import get_logger

logger = get_logger("connection_manager")


class ConnectionManager:
    """Manages WebSocket connections for real-time data streaming."""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.streaming_tasks: Dict[str, asyncio.Task] = {}

    async def connect(
        self,
        websocket: WebSocket,
        stream_key: str,
        stream_type: str = "orderbook",
        display_symbol: str = None,
    ):
        """Accept a new WebSocket connection for a stream."""
        logger.info(
            f"Connecting WebSocket for stream {stream_key} (type: {stream_type})"
        )

        # Store display symbol for response formatting
        if display_symbol and stream_key not in getattr(self, "_display_symbols", {}):
            if not hasattr(self, "_display_symbols"):
                self._display_symbols = {}
            self._display_symbols[stream_key] = display_symbol

        # Note: WebSocket should already be accepted by the endpoint
        if stream_key not in self.active_connections:
            self.active_connections[stream_key] = []

        self.active_connections[stream_key].append(websocket)
        logger.info(
            f"WebSocket connected to stream {stream_key}. Total connections: {len(self.active_connections[stream_key])}"
        )

        # Start streaming task if this is the first connection for this stream
        if len(self.active_connections[stream_key]) == 1:
            logger.info(f"Starting streaming task for {stream_key}")
            await self._start_streaming(stream_key, stream_type)

    def disconnect(self, websocket: WebSocket, stream_key: str):
        """Remove a WebSocket connection."""
        if stream_key in self.active_connections:
            if websocket in self.active_connections[stream_key]:
                self.active_connections[stream_key].remove(websocket)
                logger.info(
                    f"WebSocket disconnected from stream {stream_key}. Remaining connections: {len(self.active_connections[stream_key])}"
                )

            # Stop streaming if no more connections for this stream
            if not self.active_connections[stream_key]:
                logger.info(
                    f"Stopping streaming task for {stream_key} (no more connections)"
                )
                self._stop_streaming(stream_key)
                del self.active_connections[stream_key]
        else:
            logger.warning(
                f"Attempted to disconnect from non-existent stream: {stream_key}"
            )

    async def broadcast_to_stream(self, stream_key: str, data: dict):
        """Broadcast data to all connections for a specific stream."""
        if stream_key in self.active_connections:
            disconnected = []
            for connection in self.active_connections[stream_key]:
                try:
                    await connection.send_text(json.dumps(data))
                except Exception:
                    # Connection is broken, mark for removal
                    disconnected.append(connection)

            # Remove disconnected connections
            for connection in disconnected:
                self.disconnect(connection, stream_key)

    async def _start_streaming(self, stream_key: str, stream_type: str):
        """Start streaming data for a stream key."""
        if stream_type == "orderbook":
            task = asyncio.create_task(self._stream_orderbook(stream_key))
        elif stream_type == "ticker":
            task = asyncio.create_task(self._stream_ticker(stream_key))
        elif stream_type == "candles":
            # Extract symbol and timeframe from stream_key (format: "symbol:timeframe")
            # Handle exchange symbols that may contain "/" (e.g., "BTC/USDT:1m")
            parts = stream_key.split(":")
            if len(parts) >= 2:
                # Join all parts except the last one as symbol (handles "BTC/USDT:1m")
                symbol = ":".join(parts[:-1])
                timeframe = parts[-1]
            else:
                raise ValueError(f"Invalid stream key format: {stream_key}")
            task = asyncio.create_task(
                self._stream_candles(symbol, timeframe, stream_key)
            )
        else:
            raise ValueError(f"Unknown stream type: {stream_type}")

        self.streaming_tasks[stream_key] = task

    def _stop_streaming(self, stream_key: str):
        """Stop streaming data for a stream key."""
        if stream_key in self.streaming_tasks:
            self.streaming_tasks[stream_key].cancel()
            del self.streaming_tasks[stream_key]

    # Keep backward compatibility for existing orderbook methods
    async def connect_orderbook(
        self, websocket: WebSocket, symbol: str, display_symbol: str = None
    ):
        """Accept a new WebSocket connection for orderbook (backward compatibility)."""
        await self.connect(websocket, symbol, "orderbook", display_symbol)

    def disconnect_orderbook(self, websocket: WebSocket, symbol: str):
        """Remove a WebSocket connection for orderbook (backward compatibility)."""
        self.disconnect(websocket, symbol)

    async def broadcast_to_symbol(self, symbol: str, data: dict):
        """Broadcast data to all connections for a symbol (backward compatibility)."""
        await self.broadcast_to_stream(symbol, data)

    async def _stream_orderbook(self, symbol: str):
        """Stream order book updates using ccxtpro."""
        exchange_pro = None
        try:
            logger.info(f"Initializing orderbook stream for {symbol}")
            exchange_pro = exchange_service.get_exchange_pro()

            # Test connection before starting stream
            if exchange_pro is None:
                logger.warning(f"CCXT Pro not available for {symbol}, using mock data")
                await self._stream_mock_orderbook(symbol)
                return

            try:
                test_orderbook = await exchange_pro.fetch_order_book(symbol, limit=1)
                logger.info(f"Exchange connection test successful for {symbol}")
            except Exception as e:
                logger.error(f"Exchange connection test failed for {symbol}: {str(e)}")
                logger.info(f"Falling back to mock orderbook data for {symbol}")
                await self._stream_mock_orderbook(symbol)
                return

            while symbol in self.active_connections and self.active_connections[symbol]:
                try:
                    # Watch order book updates
                    order_book_data = await exchange_pro.watch_order_book(symbol)

                    # Convert to our schema format
                    bids = [
                        {"price": float(bid[0]), "amount": float(bid[1])}
                        for bid in order_book_data["bids"][:20]  # Top 20 levels
                    ]

                    asks = [
                        {"price": float(ask[0]), "amount": float(ask[1])}
                        for ask in order_book_data["asks"][:20]  # Top 20 levels
                    ]

                    # Use display symbol if available, otherwise use the stream symbol
                    display_symbol = getattr(self, "_display_symbols", {}).get(
                        symbol, symbol
                    )
                    formatted_data = {
                        "type": "orderbook_update",
                        "symbol": display_symbol,
                        "bids": bids,
                        "asks": asks,
                        "timestamp": order_book_data["timestamp"],
                    }

                    # Broadcast to all connected clients for this symbol
                    await self.broadcast_to_symbol(symbol, formatted_data)

                    # Pass order book update to trading engine service
                    try:
                        # Import the shared trading engine service instance
                        from app.api.v1.endpoints.trading import (
                            trading_engine_service_instance,
                        )

                        await trading_engine_service_instance.process_order_book_update(
                            symbol, order_book_data
                        )
                    except Exception as e:
                        # Log error but don't interrupt the streaming
                        print(
                            f"Error processing order book update in trading engine for {symbol}: {str(e)}"
                        )

                except Exception as e:
                    error_data = {
                        "type": "error",
                        "message": f"Error streaming order book for {symbol}: {str(e)}",
                    }
                    await self.broadcast_to_symbol(symbol, error_data)
                    await asyncio.sleep(5)  # Wait before retrying

        except Exception as e:
            error_data = {
                "type": "error",
                "message": f"Failed to initialize streaming for {symbol}: {str(e)}",
            }
            await self.broadcast_to_symbol(symbol, error_data)
        finally:
            if exchange_pro:
                try:
                    await exchange_pro.close()
                except Exception:
                    pass

    async def _stream_ticker(self, symbol: str):
        """Stream ticker updates using ccxtpro."""
        exchange_pro = None
        try:
            logger.info(f"Initializing ticker stream for {symbol}")
            exchange_pro = exchange_service.get_exchange_pro()

            # Test connection before starting stream
            if exchange_pro is None:
                logger.warning(f"CCXT Pro not available for {symbol}, using mock data")
                await self._stream_mock_ticker(symbol)
                return

            try:
                test_ticker = await exchange_pro.fetch_ticker(symbol)
                logger.info(f"Exchange connection test successful for ticker {symbol}")
            except Exception as e:
                logger.error(
                    f"Exchange connection test failed for ticker {symbol}: {str(e)}"
                )
                logger.info(f"Falling back to mock ticker data for {symbol}")
                await self._stream_mock_ticker(symbol)
                return

            while symbol in self.active_connections and self.active_connections[symbol]:
                try:
                    # Watch ticker updates
                    ticker_data = await exchange_pro.watch_ticker(symbol)

                    # Use display symbol if available, otherwise use the stream symbol
                    display_symbol = getattr(self, "_display_symbols", {}).get(
                        symbol, symbol
                    )
                    # Convert to our schema format
                    formatted_data = {
                        "type": "ticker_update",
                        "symbol": display_symbol,
                        "last": (
                            float(ticker_data.get("last", 0))
                            if ticker_data.get("last")
                            else None
                        ),
                        "bid": (
                            float(ticker_data.get("bid", 0))
                            if ticker_data.get("bid")
                            else None
                        ),
                        "ask": (
                            float(ticker_data.get("ask", 0))
                            if ticker_data.get("ask")
                            else None
                        ),
                        "high": (
                            float(ticker_data.get("high", 0))
                            if ticker_data.get("high")
                            else None
                        ),
                        "low": (
                            float(ticker_data.get("low", 0))
                            if ticker_data.get("low")
                            else None
                        ),
                        "open": (
                            float(ticker_data.get("open", 0))
                            if ticker_data.get("open")
                            else None
                        ),
                        "close": (
                            float(ticker_data.get("close", 0))
                            if ticker_data.get("close")
                            else None
                        ),
                        "change": (
                            float(ticker_data.get("change", 0))
                            if ticker_data.get("change")
                            else None
                        ),
                        "percentage": (
                            float(ticker_data.get("percentage", 0))
                            if ticker_data.get("percentage")
                            else None
                        ),
                        "volume": (
                            float(ticker_data.get("baseVolume", 0))
                            if ticker_data.get("baseVolume")
                            else None
                        ),
                        "quote_volume": (
                            float(ticker_data.get("quoteVolume", 0))
                            if ticker_data.get("quoteVolume")
                            else None
                        ),
                        "timestamp": ticker_data.get("timestamp"),
                    }

                    # Broadcast to all connected clients for this symbol
                    await self.broadcast_to_stream(symbol, formatted_data)

                except Exception as e:
                    error_data = {
                        "type": "error",
                        "message": f"Error streaming ticker for {symbol}: {str(e)}",
                    }
                    await self.broadcast_to_stream(symbol, error_data)
                    await asyncio.sleep(5)  # Wait before retrying

        except Exception as e:
            error_data = {
                "type": "error",
                "message": f"Failed to initialize ticker streaming for {symbol}: {str(e)}",
            }
            await self.broadcast_to_stream(symbol, error_data)
        finally:
            if exchange_pro:
                try:
                    await exchange_pro.close()
                except Exception:
                    pass

    async def _stream_candles(self, symbol: str, timeframe: str, stream_key: str):
        """Stream candle/OHLCV updates using ccxtpro."""
        exchange_pro = None
        try:
            logger.info(f"Initializing candles stream for {symbol}/{timeframe}")
            exchange_pro = exchange_service.get_exchange_pro()

            # Test connection before starting stream
            if exchange_pro is None:
                logger.warning(
                    f"CCXT Pro not available for {symbol}/{timeframe}, using mock data"
                )
                await self._stream_mock_candles(symbol, timeframe, stream_key)
                return

            try:
                test_candles = await exchange_pro.fetch_ohlcv(
                    symbol, timeframe, limit=1
                )
                logger.info(
                    f"Exchange connection test successful for {symbol}/{timeframe}"
                )
            except Exception as e:
                logger.error(
                    f"Exchange connection test failed for {symbol}/{timeframe}: {str(e)}"
                )
                logger.info(
                    f"Falling back to mock candles data for {symbol}/{timeframe}"
                )
                await self._stream_mock_candles(symbol, timeframe, stream_key)
                return

            while (
                stream_key in self.active_connections
                and self.active_connections[stream_key]
            ):
                try:
                    # Watch OHLCV updates
                    ohlcv_data = await exchange_pro.watch_ohlcv(symbol, timeframe)

                    # Convert to our schema format - get the latest candle
                    if ohlcv_data and len(ohlcv_data) > 0:
                        latest_candle = ohlcv_data[-1]  # Get the most recent candle

                        # Use display symbol if available, otherwise use the stream symbol
                        display_symbol = getattr(self, "_display_symbols", {}).get(
                            stream_key, symbol
                        )
                        formatted_data = {
                            "type": "candle_update",
                            "symbol": display_symbol,
                            "timeframe": timeframe,
                            "timestamp": latest_candle[0],
                            "open": float(latest_candle[1]),
                            "high": float(latest_candle[2]),
                            "low": float(latest_candle[3]),
                            "close": float(latest_candle[4]),
                            "volume": float(latest_candle[5]),
                        }

                        # Broadcast to all connected clients for this stream
                        await self.broadcast_to_stream(stream_key, formatted_data)

                except Exception as e:
                    error_data = {
                        "type": "error",
                        "message": f"Error streaming candles for {symbol} {timeframe}: {str(e)}",
                    }
                    await self.broadcast_to_stream(stream_key, error_data)
                    await asyncio.sleep(5)  # Wait before retrying

        except Exception as e:
            error_data = {
                "type": "error",
                "message": f"Failed to initialize candle streaming for {symbol} {timeframe}: {str(e)}",
            }
            await self.broadcast_to_stream(stream_key, error_data)
        finally:
            if exchange_pro:
                try:
                    await exchange_pro.close()
                except Exception:
                    pass

    async def _stream_mock_orderbook(self, symbol: str):
        """Stream mock order book data when CCXT Pro is not available."""
        logger.info(f"Starting mock orderbook stream for {symbol}")
        import random
        import time

        base_price = 50000.0  # Base price for mock data

        while symbol in self.active_connections and self.active_connections[symbol]:
            try:
                # Generate mock orderbook data
                current_time = int(time.time() * 1000)
                price_variation = random.uniform(-0.01, 0.01)  # ±1% variation
                current_price = base_price * (1 + price_variation)

                # Generate mock bids and asks
                bids = []
                asks = []

                for i in range(10):  # 10 levels each side
                    bid_price = current_price - (i + 1) * random.uniform(0.5, 2.0)
                    ask_price = current_price + (i + 1) * random.uniform(0.5, 2.0)
                    bid_amount = random.uniform(0.1, 5.0)
                    ask_amount = random.uniform(0.1, 5.0)

                    bids.append(
                        {"price": round(bid_price, 2), "amount": round(bid_amount, 4)}
                    )
                    asks.append(
                        {"price": round(ask_price, 2), "amount": round(ask_amount, 4)}
                    )

                # Use display symbol if available, otherwise use the stream symbol
                display_symbol = getattr(self, "_display_symbols", {}).get(
                    symbol, symbol
                )
                formatted_data = {
                    "type": "orderbook_update",
                    "symbol": display_symbol,
                    "bids": bids,
                    "asks": asks,
                    "timestamp": current_time,
                    "mock": True,  # Indicate this is mock data
                }

                # Broadcast to all connected clients for this symbol
                await self.broadcast_to_symbol(symbol, formatted_data)

                # Wait before next update (simulate real-time updates)
                await asyncio.sleep(1.0)

            except Exception as e:
                logger.error(f"Error in mock orderbook stream for {symbol}: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying

        logger.info(f"Mock orderbook stream ended for {symbol}")

    async def _stream_mock_candles(self, symbol: str, timeframe: str, stream_key: str):
        """Stream mock candle data when CCXT Pro is not available."""
        logger.info(f"Starting mock candles stream for {symbol}/{timeframe}")
        import random
        import time

        base_price = 50000.0
        current_price = base_price

        while (
            stream_key in self.active_connections
            and self.active_connections[stream_key]
        ):
            try:
                # Generate mock candle data
                current_time = int(time.time() * 1000)

                # Simulate price movement
                price_change = random.uniform(-0.005, 0.005)  # ±0.5% change
                current_price *= 1 + price_change

                # Generate OHLCV data
                open_price = current_price
                high_price = current_price * random.uniform(1.0, 1.002)
                low_price = current_price * random.uniform(0.998, 1.0)
                close_price = current_price * random.uniform(0.999, 1.001)
                volume = random.uniform(10.0, 100.0)

                # Use display symbol if available, otherwise use the stream symbol
                display_symbol = getattr(self, "_display_symbols", {}).get(
                    stream_key, symbol
                )
                formatted_data = {
                    "type": "candle_update",
                    "symbol": display_symbol,
                    "timeframe": timeframe,
                    "timestamp": current_time,
                    "open": round(open_price, 2),
                    "high": round(high_price, 2),
                    "low": round(low_price, 2),
                    "close": round(close_price, 2),
                    "volume": round(volume, 4),
                    "mock": True,  # Indicate this is mock data
                }

                # Broadcast to all connected clients for this stream
                await self.broadcast_to_stream(stream_key, formatted_data)

                # Wait before next update
                await asyncio.sleep(2.0)

            except Exception as e:
                logger.error(
                    f"Error in mock candles stream for {symbol}/{timeframe}: {str(e)}"
                )
                await asyncio.sleep(5)  # Wait before retrying

        logger.info(f"Mock candles stream ended for {symbol}/{timeframe}")

    async def _stream_mock_ticker(self, symbol: str):
        """Stream mock ticker data when CCXT Pro is not available."""
        logger.info(f"Starting mock ticker stream for {symbol}")
        import random
        import time

        base_price = 50000.0  # Base price for mock data
        current_price = base_price

        while symbol in self.active_connections and self.active_connections[symbol]:
            try:
                # Generate mock ticker data
                current_time = int(time.time() * 1000)

                # Simulate price movement
                price_change = random.uniform(-0.005, 0.005)  # ±0.5% change
                current_price *= 1 + price_change

                # Generate ticker data
                last_price = current_price
                bid_price = current_price * random.uniform(0.9995, 0.9999)
                ask_price = current_price * random.uniform(1.0001, 1.0005)
                high_price = current_price * random.uniform(1.0, 1.02)
                low_price = current_price * random.uniform(0.98, 1.0)
                open_price = current_price * random.uniform(0.99, 1.01)
                close_price = current_price
                change = close_price - open_price
                percentage = (change / open_price) * 100 if open_price > 0 else 0
                volume = random.uniform(100.0, 1000.0)
                quote_volume = volume * current_price

                # Use display symbol if available, otherwise use the stream symbol
                display_symbol = getattr(self, "_display_symbols", {}).get(
                    symbol, symbol
                )
                formatted_data = {
                    "type": "ticker_update",
                    "symbol": display_symbol,
                    "last": round(last_price, 2),
                    "bid": round(bid_price, 2),
                    "ask": round(ask_price, 2),
                    "high": round(high_price, 2),
                    "low": round(low_price, 2),
                    "open": round(open_price, 2),
                    "close": round(close_price, 2),
                    "change": round(change, 2),
                    "percentage": round(percentage, 4),
                    "volume": round(volume, 4),
                    "quote_volume": round(quote_volume, 2),
                    "timestamp": current_time,
                    "mock": True,  # Indicate this is mock data
                }

                # Broadcast to all connected clients for this symbol
                await self.broadcast_to_stream(symbol, formatted_data)

                # Wait before next update (simulate real-time updates)
                await asyncio.sleep(1.5)

            except Exception as e:
                logger.error(f"Error in mock ticker stream for {symbol}: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying

        logger.info(f"Mock ticker stream ended for {symbol}")


# Global connection manager instance
connection_manager = ConnectionManager()
