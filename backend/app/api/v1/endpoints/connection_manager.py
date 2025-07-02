"""
WebSocket Connection Manager for real-time data streaming.

This module provides the ConnectionManager class that handles WebSocket connections
for real-time market data streaming including order books, tickers, and candles.
"""

from typing import List, Dict, Optional, Any
import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect
from app.services.exchange_service import exchange_service
from app.services.orderbook_processor import OrderBookProcessor
from app.core.logging_config import get_logger
from app.core.config import settings

logger = get_logger("connection_manager")


class ConnectionManager:
    """Manages WebSocket connections for real-time data streaming."""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.streaming_tasks: Dict[str, asyncio.Task] = {}
        # Tracks active stream types per symbol (e.g., {"BTCUSDT": {"orderbook", "candles:1m"}})
        self.symbol_active_streams: Dict[str, set[str]] = {}
        self.stream_key_types: Dict[str, str] = {}  # Stores the type of each stream_key
        self.orderbook_processor = OrderBookProcessor()  # Add processor instance

    async def connect(
        self,
        websocket: WebSocket,
        stream_key: str,
        stream_type: str = "orderbook",
        display_symbol: Optional[str] = None,
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
        self.stream_key_types[stream_key] = stream_type  # Store stream type
        logger.info(
            f"WebSocket connected to stream {stream_key}. Total connections: {len(self.active_connections[stream_key])}"
        )

        # Extract base symbol from stream_key for symbol_active_streams tracking
        base_symbol = self._get_base_symbol_from_stream_key(stream_key, stream_type)
        if base_symbol:
            if base_symbol not in self.symbol_active_streams:
                self.symbol_active_streams[base_symbol] = set()
            self.symbol_active_streams[base_symbol].add(stream_key)
            logger.debug(
                f"Active streams for {base_symbol}: {self.symbol_active_streams[base_symbol]}"
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

            # Check if there are any remaining connections for this specific stream_key
            if not self.active_connections[stream_key]:
                logger.info(
                    f"No more connections for stream_key: {stream_key}. Stopping its specific streaming task."
                )
                self._stop_streaming(
                    stream_key
                )  # Cancels task and removes from self.streaming_tasks

                retrieved_stream_type = self.stream_key_types.get(stream_key)
                del self.active_connections[stream_key]
                # Do NOT delete from self.stream_key_types[stream_key] here yet.
                # It's needed for the "stop all tasks for base_symbol" logic below.

                base_symbol = None
                if retrieved_stream_type:
                    base_symbol = self._get_base_symbol_from_stream_key(
                        stream_key, retrieved_stream_type
                    )
                else:
                    logger.warning(
                        f"Could not retrieve stored stream_type for stream_key: {stream_key} upon disconnect. "
                        f"This might affect comprehensive cleanup if it's the last stream for its base symbol."
                    )

                if base_symbol and base_symbol in self.symbol_active_streams:
                    self.symbol_active_streams[base_symbol].discard(stream_key)
                    logger.debug(
                        f"Updated active streams for {base_symbol}: {self.symbol_active_streams[base_symbol]}"
                    )

                    if not self.symbol_active_streams[base_symbol]:
                        logger.info(
                            f"No more active specific streams for base_symbol {base_symbol}. "
                            f"Ensuring all related streaming tasks are stopped and cleaning up types."
                        )
                        # Iterate over a copy of streaming_tasks keys, as _stop_streaming modifies the dict
                        tasks_to_check_for_stop = list(self.streaming_tasks.keys())
                        stopped_task_keys_for_base_symbol = []

                        for task_key_iter in tasks_to_check_for_stop:
                            # We need the type of task_key_iter to determine its base_symbol
                            iter_task_type = self.stream_key_types.get(task_key_iter)
                            if iter_task_type:
                                iter_base_symbol = (
                                    self._get_base_symbol_from_stream_key(
                                        task_key_iter, iter_task_type
                                    )
                                )
                                if iter_base_symbol == base_symbol:
                                    logger.debug(
                                        f"Stopping task {task_key_iter} as part of {base_symbol} cleanup."
                                    )
                                    self._stop_streaming(
                                        task_key_iter
                                    )  # Ensures it's cancelled and removed from streaming_tasks
                                    stopped_task_keys_for_base_symbol.append(
                                        task_key_iter
                                    )
                            else:
                                logger.warning(
                                    f"No type found for active task {task_key_iter} during {base_symbol} cleanup. Skipping."
                                )

                        # Now, clean up stream_key_types for all stream_keys associated with this base_symbol.
                        # This includes the original stream_key and any others that were part of its group.
                        logger.debug(
                            f"Cleaning up stream_key_types for base_symbol: {base_symbol}"
                        )
                        related_stream_keys_for_type_cleanup = [
                            s_key
                            for s_key, s_type in list(
                                self.stream_key_types.items()
                            )  # Iterate over a copy
                            if self._get_base_symbol_from_stream_key(s_key, s_type)
                            == base_symbol
                        ]
                        for key_to_delete_type in related_stream_keys_for_type_cleanup:
                            if key_to_delete_type in self.stream_key_types:
                                logger.debug(
                                    f"Deleting {key_to_delete_type} from stream_key_types."
                                )
                                del self.stream_key_types[key_to_delete_type]

                        if (
                            base_symbol in self.symbol_active_streams
                        ):  # Check before deleting
                            del self.symbol_active_streams[base_symbol]
                        else:  # Should not happen if logic is correct, but good to log
                            logger.warning(
                                f"Attempted to delete {base_symbol} from symbol_active_streams, but it was already removed or not found."
                            )
                elif (
                    base_symbol
                ):  # base_symbol was determined, but not in symbol_active_streams
                    logger.warning(
                        f"Base symbol {base_symbol} (from stream_key {stream_key}) not found in symbol_active_streams for cleanup."
                    )
                # else: base_symbol could not be determined, already logged.

            else:  # Still active connections for this specific stream_key
                logger.debug(
                    f"Stream {stream_key} still has {len(self.active_connections[stream_key])} active connections."
                )
        else:  # stream_key not in self.active_connections
            logger.warning(
                f"Attempted to disconnect from non-existent or already cleaned stream: {stream_key}"
            )

    def _get_base_symbol_from_stream_key(
        self, stream_key: str, stream_type: str | None  # Added | None
    ) -> str | None:
        """Helper to extract the base symbol from a stream_key."""
        if not stream_type:  # Handle if stream_type is None
            logger.debug(
                f"Cannot determine base symbol for {stream_key} without stream_type."
            )
            return None
        if stream_type == "candles":
            parts = stream_key.split(":")
            if len(parts) >= 2:
                return ":".join(parts[:-1])
        elif stream_type == "orderbook" or stream_type == "ticker":
            return stream_key
        logger.warning(
            f"Unknown stream_type '{stream_type}' for stream_key '{stream_key}' in _get_base_symbol_from_stream_key."
        )
        return None  # Default for unknown types or if logic above fails

    async def broadcast_to_stream(self, stream_key: str, data: dict):
        """Broadcast data to all connections for a specific stream."""
        if stream_key in self.active_connections:
            disconnected = []
            # Iterate over a copy of the list of connections, as self.disconnect can modify it
            for connection in list(self.active_connections[stream_key]):
                try:
                    await connection.send_text(json.dumps(data))
                except WebSocketDisconnect:
                    logger.info(
                        f"WebSocketDisconnect detected for a connection on stream {stream_key}. Marking for removal."
                    )
                    disconnected.append(connection)
                except Exception as e:
                    logger.error(
                        f"Error sending to a connection on stream {stream_key}: {e}. Marking for removal."
                    )
                    disconnected.append(connection)

            # Remove disconnected connections
            for connection in disconnected:
                # Check if connection is still in the list before attempting to remove,
                # as multiple errors or rapid disconnects could lead to it being already handled.
                if (
                    stream_key in self.active_connections
                    and connection in self.active_connections[stream_key]
                ):
                    self.disconnect(connection, stream_key)
                else:
                    logger.debug(
                        f"Connection for stream {stream_key} already removed, skipping redundant disconnect call."
                    )

    async def _start_streaming(self, stream_key: str, stream_type: str):
        """Start streaming data for a stream key."""
        if stream_key in self.streaming_tasks:  # Prevent duplicate tasks
            logger.warning(
                f"Streaming task for {stream_key} already exists. Not starting a new one."
            )
            return

        if stream_type == "orderbook":
            task = asyncio.create_task(self._stream_orderbook(stream_key))
        elif stream_type == "ticker":
            # For ticker streams, extract symbol from stream_key (format: "SYMBOL:ticker" -> "SYMBOL")
            symbol = stream_key.replace(":ticker", "") if stream_key.endswith(":ticker") else stream_key
            task = asyncio.create_task(self._stream_ticker(symbol))
        elif stream_type == "candles":
            parts = stream_key.split(":")
            if len(parts) >= 2:
                symbol = ":".join(parts[:-1])
                timeframe = parts[-1]
            else:
                logger.error(f"Invalid stream key format for candles: {stream_key}")
                return  # Do not create task for invalid format
            task = asyncio.create_task(
                self._stream_candles(symbol, timeframe, stream_key)
            )
        else:
            logger.error(
                f"Unknown stream type: {stream_type} for stream_key: {stream_key}"
            )
            return  # Do not create task for unknown type

        self.streaming_tasks[stream_key] = task
        logger.info(
            f"Successfully started streaming task for {stream_key} (type: {stream_type})"
        )

    def _stop_streaming(self, stream_key: str):
        """Stop streaming data for a stream key. Cancels the task and removes it from tracking."""
        if stream_key in self.streaming_tasks:
            logger.info(f"Cancelling and removing streaming task for {stream_key}")
            try:
                self.streaming_tasks[stream_key].cancel()
            except Exception as e:  # Catch potential errors during cancellation
                logger.error(f"Error cancelling task for {stream_key}: {e}")
            del self.streaming_tasks[stream_key]
        else:
            # This might be normal if a task was already stopped by another path (e.g. base_symbol cleanup)
            logger.debug(
                f"Attempted to stop streaming task for {stream_key}, but it was not found in streaming_tasks (possibly already stopped)."
            )

    # Keep backward compatibility for existing orderbook methods
    async def connect_orderbook(
        self, websocket: WebSocket, symbol: str, display_symbol: Optional[str] = None, limit: int = 20,
        rounding: float = 0.01, aggregate: bool = False, use_depth_cache: bool = True
    ):
        """Accept a new WebSocket connection for orderbook with aggregation parameters."""
        # Store the configuration for this symbol stream
        if not hasattr(self, '_stream_configs'):
            self._stream_configs: Dict[str, Dict[str, Any]] = {}
        
        # Create configuration for this symbol
        new_config = {
            'limit': limit,
            'rounding': rounding,
            'aggregate': aggregate,
            'use_depth_cache': use_depth_cache
        }
        
        logger.debug(f"Setting orderbook config for {symbol}: {new_config}")
        
        # Check if configuration changed and restart if needed
        current_config = self._stream_configs.get(symbol)
        if current_config != new_config and symbol in self.active_connections:
            logger.info(f"Updating orderbook config for {symbol}: {new_config}")
            self._stream_configs[symbol] = new_config
            # Signal the streaming task to restart with new configuration
            await self._restart_orderbook_stream(symbol)
        else:
            self._stream_configs[symbol] = new_config
        
        # Backward compatibility: also store limit separately
        if not hasattr(self, '_stream_limits'):
            self._stream_limits = {}
        self._stream_limits[symbol] = limit
            
        await self.connect(websocket, symbol, "orderbook", display_symbol)

    def disconnect_orderbook(self, websocket: WebSocket, symbol: str):
        """Remove a WebSocket connection for orderbook (backward compatibility)."""
        self.disconnect(websocket, symbol)

    async def broadcast_to_symbol(self, symbol: str, data: dict):
        """Broadcast data to all connections for a symbol with optional aggregation."""
        # Get configuration for this symbol
        config = getattr(self, '_stream_configs', {}).get(symbol, {})
        
        # If aggregation is enabled and this is an orderbook update, process it
        if (config.get('aggregate', False) and 
            data.get('type') == 'orderbook_update' and 
            'bids' in data and 'asks' in data):
            
            logger.debug(f"Performing backend aggregation for {symbol}")
            try:
                # Convert message format to raw orderbook format for processor
                raw_orderbook = {
                    'bids': [[item['price'], item['amount']] for item in data.get('bids', [])],
                    'asks': [[item['price'], item['amount']] for item in data.get('asks', [])],
                    'timestamp': data.get('timestamp')
                }
                
                # Process with aggregation
                # Use a reasonable depth for backend aggregation
                # Frontend will slice to displayDepth, so generate enough levels
                aggregation_depth = 100  # Generate up to 100 aggregated levels
                aggregated = self.orderbook_processor.process_orderbook(
                    raw_orderbook=raw_orderbook,
                    symbol=symbol,
                    rounding=config.get('rounding', 0.01),
                    depth=aggregation_depth,
                    source=data.get('source', 'ccxtpro')
                )
                
                # Convert back to WebSocket message format
                aggregated_data = {
                    "type": "orderbook_update",
                    "symbol": data.get('symbol', symbol),
                    "bids": [{"price": level.price, "amount": level.amount} for level in aggregated.bids],
                    "asks": [{"price": level.price, "amount": level.amount} for level in aggregated.asks],
                    "timestamp": aggregated.timestamp or data.get('timestamp'),
                    "aggregated": True,
                    "rounding": aggregated.rounding,
                    "source": aggregated.source,
                    "depth": aggregated.depth,
                    "processing_time": int(asyncio.get_event_loop().time() * 1000)
                }
                
                await self.broadcast_to_stream(symbol, aggregated_data)
                
            except Exception as e:
                logger.error(f"Error processing aggregated orderbook for {symbol}: {e}")
                # Fall back to raw data with aggregated=false
                data = dict(data)  # Make a copy
                data['aggregated'] = False
                await self.broadcast_to_stream(symbol, data)
        else:
            # Add aggregated=false for backward compatibility
            if data.get('type') == 'orderbook_update':
                data = dict(data)  # Make a copy
                data['aggregated'] = False
            await self.broadcast_to_stream(symbol, data)

    async def _stream_orderbook(self, symbol: str):
        """Stream order book updates using DepthCacheManager, ccxtpro, or Binance partial depth streams."""
        exchange_pro = None
        try:
            logger.info(f"Initializing orderbook stream for {symbol}")
            exchange_pro = exchange_service.get_exchange_pro()

            # Get the configuration for this symbol
            config = getattr(self, '_stream_configs', {}).get(symbol, {})
            limit = config.get('limit', 20)
            use_depth_cache = config.get('use_depth_cache', True)
            aggregate = config.get('aggregate', False)
            rounding = config.get('rounding', 0.01)
            
            logger.info(
                f"Using config for {symbol}: limit={limit}, aggregate={aggregate}, "
                f"rounding={rounding}, use_depth_cache={use_depth_cache}"
            )
            
            # Validate and clamp limit parameter (same as WebSocket endpoint)
            limit = max(5, min(limit, 5000))

            # Check if we should use DepthCacheManager for Binance symbols
            if (settings.USE_DEPTH_CACHE_MANAGER and 
                self._is_binance_symbol(symbol) and 
                use_depth_cache):
                logger.info(f"🚀 Using DepthCacheManager for {symbol} with limit {limit}")
                await self._stream_orderbook_with_depth_cache(symbol, limit)
                return

            # Check if we should use Binance partial depth streams for better coverage
            use_partial_depth = self._should_use_partial_depth_stream(limit)
            logger.info(
                f"Evaluating partial depth stream for {symbol}: "
                f"limit={limit}, use_partial_depth={use_partial_depth}"
            )
            
            if use_partial_depth:
                logger.info(f"✅ Using Binance partial depth stream for {symbol} with limit {limit}")
                await self._stream_partial_depth_orderbook(symbol, limit)
                return
            else:
                logger.info(f"➡️ Using standard CCXT stream for {symbol} with limit {limit}")
                
            # Use the extracted ccxtpro streaming method
            await self._stream_orderbook_ccxtpro(symbol, limit)

        except Exception as e:
            error_data = {
                "type": "error",
                "message": f"Failed to initialize streaming for {symbol}: {str(e)}",
            }
            await self.broadcast_to_symbol(symbol, error_data)
        finally:
            # Do NOT close exchange_pro here. It should be managed globally.
            pass

    def _should_use_partial_depth_stream(self, limit: int) -> bool:
        """Determine if we should use Binance partial depth streams instead of full orderbook."""
        # Temporarily disable partial depth streams to fix real-time updates
        # The partial depth implementation needs to be reworked to properly integrate with FastAPI WebSocket
        return False  # Disable partial depth streams for now

    def _get_partial_depth_level(self, limit: int) -> int:
        """Get the appropriate Binance partial depth level (5, 10, or 20) for the given limit."""
        if limit <= 5:
            return 5
        elif limit <= 10:
            return 10
        else:
            return 20  # For limits 11-100, use 20 levels

    async def _stream_partial_depth_orderbook(self, symbol: str, requested_limit: int):
        """Stream order book updates using Binance USDT-M Futures partial depth streams."""
        try:
            import websockets
            import json
        except ImportError as e:
            logger.error(f"Failed to import websockets: {e}")
            await self._stream_mock_orderbook(symbol)
            return
        
        try:
            # Get the appropriate depth level for Binance partial depth streams
            depth_level = self._get_partial_depth_level(requested_limit)
            
            # Convert symbol to lowercase for Binance WebSocket
            ws_symbol = symbol.lower()
            
            # Binance USDT-M Futures partial depth stream URL
            # Format: {base_url}/ws/<symbol>@depth<levels>
            ws_url = f"{settings.BINANCE_WS_BASE_URL}/ws/{ws_symbol}@depth{depth_level}"
            
            logger.info(f"Connecting to Binance partial depth stream: {ws_url}")
            
            while symbol in self.active_connections and self.active_connections[symbol]:
                try:
                    async with websockets.connect(ws_url) as websocket:
                        logger.info(f"Connected to Binance partial depth stream for {symbol}")
                        
                        async for message in websocket:
                            # Check if we should still be streaming
                            if symbol not in self.active_connections or not self.active_connections[symbol]:
                                logger.info(f"Stopping partial depth stream for {symbol} - no active connections")
                                break
                                
                            try:
                                data = json.loads(message)
                                
                                # Binance partial depth stream format:
                                # {
                                #   "e": "depthUpdate",
                                #   "E": 1640995200000,
                                #   "s": "BTCUSDT", 
                                #   "b": [["7403.89", "0.002"]],
                                #   "a": [["7405.96", "3.340"]]
                                # }
                                
                                if data.get("e") == "depthUpdate":
                                    # Convert Binance format to our format
                                    bids = [
                                        {"price": float(bid[0]), "amount": float(bid[1])}
                                        for bid in data.get("b", [])
                                        if float(bid[1]) > 0  # Filter out zero quantities
                                    ]
                                    
                                    asks = [
                                        {"price": float(ask[0]), "amount": float(ask[1])}
                                        for ask in data.get("a", [])
                                        if float(ask[1]) > 0  # Filter out zero quantities
                                    ]
                                    
                                    # Use display symbol if available, otherwise use the stream symbol
                                    display_symbol = getattr(self, "_display_symbols", {}).get(symbol, symbol)
                                    
                                    formatted_data = {
                                        "type": "orderbook_update",
                                        "symbol": display_symbol,
                                        "bids": bids,
                                        "asks": asks,
                                        "timestamp": data.get("E"),
                                        "source": "binance_partial_depth",
                                        "depth_level": depth_level
                                    }
                                    
                                    # Broadcast to all connected clients for this symbol
                                    await self.broadcast_to_symbol(symbol, formatted_data)
                                    
                                    # Pass order book update to trading engine service
                                    try:
                                        from app.api.v1.endpoints.trading import trading_engine_service_instance
                                        
                                        # Convert to ccxt format for trading engine compatibility
                                        ccxt_format = {
                                            "symbol": symbol,
                                            "bids": [[float(bid["price"]), float(bid["amount"])] for bid in bids],
                                            "asks": [[float(ask["price"]), float(ask["amount"])] for ask in asks],
                                            "timestamp": data.get("E")
                                        }
                                        
                                        await trading_engine_service_instance.process_order_book_update(symbol, ccxt_format)
                                    except Exception as e:
                                        logger.warning(
                            f"Error processing order book update in trading engine "
                            f"for {symbol}: {str(e)}"
                        )
                                        
                            except json.JSONDecodeError as e:
                                logger.warning(f"Invalid JSON received from Binance for {symbol}: {str(e)}")
                            except Exception as e:
                                logger.error(f"Error processing Binance partial depth message for {symbol}: {str(e)}")
                                
                except websockets.exceptions.ConnectionClosed:
                    logger.warning(
                        f"Binance partial depth WebSocket connection closed for {symbol}, "
                        "reconnecting..."
                    )
                    await asyncio.sleep(1)  # Wait before reconnecting
                except Exception as e:
                    logger.error(f"Error in Binance partial depth stream for {symbol}: {str(e)}")
                    
                    # Send error to clients
                    error_data = {
                        "type": "error",
                        "message": f"Error in partial depth stream for {symbol}: {str(e)}",
                    }
                    await self.broadcast_to_symbol(symbol, error_data)
                    await asyncio.sleep(5)  # Wait before retrying
                    
        except Exception as e:
            logger.error(f"Failed to initialize Binance partial depth stream for {symbol}: {str(e)}")
            error_data = {
                "type": "error", 
                "message": f"Failed to initialize partial depth streaming for {symbol}: {str(e)}",
            }
            await self.broadcast_to_symbol(symbol, error_data)

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
            # Do NOT close exchange_pro here. It should be managed globally.
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
            # Do NOT close exchange_pro here. It should be managed globally.
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
                    "source": "mock",  # Add source field for aggregation logic
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

    async def _restart_orderbook_stream(self, symbol: str):
        """Restart orderbook stream with updated limit."""
        logger.info(f"Restarting orderbook stream for {symbol} with new limit")
        
        # Stop the current streaming task if it exists
        if symbol in self.streaming_tasks:
            logger.info(f"Stopping existing orderbook task for {symbol}")
            self._stop_streaming(symbol)
            
        # Start new streaming task with updated limit
        if symbol in self.active_connections and self.active_connections[symbol]:
            logger.info(f"Starting new orderbook task for {symbol}")
            await self._start_streaming(symbol, "orderbook")

    def _is_binance_symbol(self, symbol: str) -> bool:
        """Check if the symbol is a Binance symbol (USDT futures)."""
        # Simple check - can be enhanced based on exchange service info
        return symbol.endswith("USDT") or symbol.endswith("BUSD")

    async def _stream_orderbook_with_depth_cache(self, symbol: str, limit: int):
        """Stream order book updates using DepthCacheManager."""
        try:
            from app.services.depth_cache_service import depth_cache_service
            
            # Define callback to handle depth cache updates
            async def depth_cache_callback(update_symbol: str, depth_data: dict):
                """Process depth cache updates and broadcast to clients."""
                try:
                    # Get display symbol
                    display_symbol = getattr(self, "_display_symbols", {}).get(
                        symbol, symbol
                    )
                    
                    # Get limited bids and asks
                    bids = depth_data["bids"][:limit] if "bids" in depth_data else []
                    asks = depth_data["asks"][:limit] if "asks" in depth_data else []
                    
                    # Format for our schema
                    formatted_bids = [
                        {"price": float(price), "amount": float(amount)}
                        for price, amount in bids
                    ]
                    
                    formatted_asks = [
                        {"price": float(price), "amount": float(amount)}
                        for price, amount in asks
                    ]
                    
                    formatted_data = {
                        "type": "orderbook_update",
                        "symbol": display_symbol,
                        "bids": formatted_bids,
                        "asks": formatted_asks,
                        "timestamp": depth_data.get("update_time", int(asyncio.get_event_loop().time() * 1000)),
                        "source": "depth_cache_manager"
                    }
                    
                    # Broadcast to all connected clients
                    await self.broadcast_to_symbol(symbol, formatted_data)
                    
                    # Pass to trading engine if needed
                    try:
                        from app.api.v1.endpoints.trading import trading_engine_service_instance
                        
                        # Convert to ccxt-like format for trading engine
                        ccxt_orderbook = {
                            "symbol": symbol,
                            "bids": [[float(price), float(amount)] for price, amount in bids],
                            "asks": [[float(price), float(amount)] for price, amount in asks],
                            "timestamp": depth_data.get("update_time")
                        }
                        
                        await trading_engine_service_instance.process_order_book_update(
                            symbol, ccxt_orderbook
                        )
                    except Exception as e:
                        logger.error(f"Error processing depth cache update in trading engine: {str(e)}")
                        
                except Exception as e:
                    logger.error(f"Error in depth cache callback for {symbol}: {str(e)}")
            
            # Start depth cache stream
            await depth_cache_service.start_depth_cache(symbol, depth_cache_callback)
            
            # Keep the task alive while there are active connections
            while symbol in self.active_connections and self.active_connections[symbol]:
                await asyncio.sleep(1)
                
            # Stop depth cache when no more connections
            await depth_cache_service.stop_depth_cache(symbol, depth_cache_callback)
            
        except ImportError:
            logger.error("DepthCacheManager not available, falling back to standard stream")
            # Fall back to regular ccxtpro stream
            await self._stream_orderbook_ccxtpro(symbol, limit)
        except Exception as e:
            logger.error(f"Error in DepthCacheManager stream for {symbol}: {str(e)}")
            # Send error to clients
            error_data = {
                "type": "error",
                "message": f"DepthCacheManager error for {symbol}: {str(e)}"
            }
            await self.broadcast_to_symbol(symbol, error_data)
            
            # Fall back to regular stream
            await self._stream_orderbook_ccxtpro(symbol, limit)

    async def _stream_orderbook_ccxtpro(self, symbol: str, limit: int):
        """Original ccxtpro orderbook streaming logic (extracted for clarity)."""
        exchange_pro = exchange_service.get_exchange_pro()
        
        # Test connection before starting stream
        if exchange_pro is None:
            logger.warning(f"CCXT Pro not available for {symbol}, using mock data")
            await self._stream_mock_orderbook(symbol)
            return

        try:
            test_orderbook = await exchange_pro.fetch_order_book(symbol, limit=limit)
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

                # Convert to our schema format using dynamic limit
                bids = [
                    {"price": float(bid[0]), "amount": float(bid[1])}
                    for bid in order_book_data["bids"][:limit]
                ]

                asks = [
                    {"price": float(ask[0]), "amount": float(ask[1])}
                    for ask in order_book_data["asks"][:limit]
                ]

                # Use display symbol if available
                display_symbol = getattr(self, "_display_symbols", {}).get(
                    symbol, symbol
                )
                formatted_data = {
                    "type": "orderbook_update",
                    "symbol": display_symbol,
                    "bids": bids,
                    "asks": asks,
                    "timestamp": order_book_data["timestamp"],
                    "source": "ccxtpro",  # Add source field for aggregation logic
                }

                # Broadcast to all connected clients
                await self.broadcast_to_symbol(symbol, formatted_data)

                # Pass to trading engine
                try:
                    from app.api.v1.endpoints.trading import trading_engine_service_instance
                    await trading_engine_service_instance.process_order_book_update(
                        symbol, order_book_data
                    )
                except Exception as e:
                    logger.error(f"Error processing order book update in trading engine: {str(e)}")

            except Exception as e:
                error_data = {
                    "type": "error",
                    "message": f"Error streaming order book for {symbol}: {str(e)}",
                }
                await self.broadcast_to_symbol(symbol, error_data)
                await asyncio.sleep(5)  # Wait before retrying


# Global connection manager instance
connection_manager = ConnectionManager()
