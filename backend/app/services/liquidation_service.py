"""
Liquidation Service for Binance Futures Liquidation Streams

This service handles direct WebSocket connections to Binance futures liquidation streams
since CCXT Pro doesn't support liquidation order streams.
"""

import asyncio
import json
import websockets
import aiohttp
from typing import Optional, Dict, List, Callable, Any, Tuple
from datetime import datetime
import logging
from decimal import Decimal
from collections import defaultdict
import time
from app.services.formatting_service import formatting_service
from app.core.config import settings

logger = logging.getLogger(__name__)

class LiquidationService:
    """Service for connecting to Binance liquidation streams"""
    
    def __init__(self):
        self.base_url = settings.BINANCE_WS_BASE_URL
        self.active_connections: Dict[str, asyncio.Task] = {}
        self.data_callbacks: Dict[str, List[Callable]] = {}
        self.running_streams: Dict[str, bool] = {}
        self.retry_delays = [1, 2, 5, 10, 30]  # Exponential backoff
        self.symbol_info_cache: Dict[str, Optional[Dict]] = {}  # Store symbol info per symbol
        self._http_session: Optional[aiohttp.ClientSession] = None
        
        # For timeframe aggregation
        self.liquidation_buffers: Dict[str, Dict[str, List[Dict]]] = {}  # symbol -> timeframe -> liquidations
        self.buffer_callbacks: Dict[str, Dict[str, List[Callable]]] = {}  # symbol -> timeframe -> callbacks
        self.aggregation_tasks: Dict[str, Dict[str, asyncio.Task]] = {}  # symbol -> timeframe -> task
        self.liquidation_cache: Dict[str, Tuple[List[Dict], float]] = {}  # cache_key -> (data, timestamp)
        self.cache_ttl = 60  # Cache TTL in seconds
        
        # Store accumulated volume data to prevent overwriting historical data
        self.accumulated_volumes: Dict[str, Dict[str, Dict[int, Dict]]] = {}  # symbol -> timeframe -> bucket_time -> volume_data
        
    async def connect_to_liquidation_stream(self, symbol: str, callback: Callable[[Dict], Any], symbol_info: Optional[Dict] = None):
        """
        Connect to Binance liquidation stream for a specific symbol
        Uses fan-out pattern - single Binance connection, multiple frontend subscribers
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            callback: Callback function to handle liquidation data
            symbol_info: Optional symbol information for formatting
        """
        # Convert symbol to lowercase for Binance
        stream_symbol = symbol.lower()
        stream_url = f"{self.base_url}/ws/{stream_symbol}@forceOrder"
        
        # Register callback
        if symbol not in self.data_callbacks:
            self.data_callbacks[symbol] = []
        self.data_callbacks[symbol].append(callback)
        
        # Store symbol info (update if provided)
        if symbol_info:
            self.symbol_info_cache[symbol] = symbol_info
        
        # If already connected, just add callback - connection sharing
        if symbol in self.active_connections:
            logger.info(f"Adding callback to existing {symbol} liquidation stream ({len(self.data_callbacks[symbol])} total subscribers)")
            return
            
        # Start new connection - this will be shared by all subscribers
        logger.info(f"Starting new Binance liquidation stream for {symbol}")
        self.running_streams[symbol] = True
        task = asyncio.create_task(self._maintain_connection(symbol, stream_url))
        self.active_connections[symbol] = task
        
    async def _maintain_connection(self, symbol: str, stream_url: str):
        """Maintain WebSocket connection with reconnection logic"""
        retry_count = 0
        
        while self.running_streams.get(symbol, False):
            try:
                await self._connect_and_listen(symbol, stream_url)
                retry_count = 0  # Reset on successful connection
                
            except Exception as e:
                logger.error(f"Liquidation stream error for {symbol}: {e}")
                
                if not self.running_streams.get(symbol, False):
                    break
                    
                # Exponential backoff
                delay = self.retry_delays[min(retry_count, len(self.retry_delays) - 1)]
                logger.info(f"Reconnecting {symbol} liquidation stream in {delay}s...")
                await asyncio.sleep(delay)
                retry_count += 1
                
    async def _connect_and_listen(self, symbol: str, stream_url: str):
        """Connect to WebSocket and listen for messages"""
        logger.info(f"Connecting to liquidation stream: {stream_url}")
        
        async with websockets.connect(stream_url) as websocket:
            logger.info(f"Connected to {symbol} liquidation stream")
            
            # Create ping task
            ping_task = asyncio.create_task(self._send_pings(websocket))
            
            try:
                while self.running_streams.get(symbol, False):
                    try:
                        # Wait for message with timeout
                        message = await asyncio.wait_for(websocket.recv(), timeout=30)
                        data = json.loads(message)
                        
                        # Process liquidation data
                        if data.get('e') == 'forceOrder':
                            symbol_info = self.symbol_info_cache.get(symbol)
                            formatted_data = self.format_liquidation_data(data, symbol, symbol_info)
                            await self._notify_callbacks(symbol, formatted_data)
                            
                            # Also add to aggregation buffers
                            await self._add_to_aggregation_buffers(symbol, formatted_data)
                            
                    except asyncio.TimeoutError:
                        # No message in 30 seconds, continue
                        continue
                        
                    except websockets.ConnectionClosed:
                        logger.warning(f"WebSocket connection closed for {symbol}")
                        break
                        
            finally:
                ping_task.cancel()
                try:
                    await ping_task
                except asyncio.CancelledError:
                    pass
                    
    async def _send_pings(self, websocket):
        """Send periodic pings to keep connection alive"""
        try:
            while True:
                await asyncio.sleep(180)  # 3 minutes
                await websocket.ping()
                logger.debug("Sent ping to keep connection alive")
        except asyncio.CancelledError:
            pass
            
    def format_liquidation_data(self, raw_data: Dict, display_symbol: str, symbol_info: Optional[Dict] = None) -> Dict:
        """
        Format liquidation data for frontend display
        
        Expected output format:
        {
            "symbol": "BTCUSDT",
            "side": "SELL",
            "quantity": "0.014",
            "quantityFormatted": "0.014000",
            "priceUsdt": "138.74",
            "priceUsdtFormatted": "138",
            "timestamp": 1568014460893,
            "displayTime": "14:27:40",
            "avgPrice": "9910",
            "baseAsset": "BTC"
        }
        
        Args:
            raw_data: Raw liquidation message from Binance
            display_symbol: Symbol for display purposes
            symbol_info: Optional symbol information for formatting
            
        Returns:
            Formatted liquidation data for frontend
        """
        order = raw_data.get('o', {})
        
        # Extract data
        side = order.get('S', 'UNKNOWN')
        quantity = Decimal(order.get('z', '0'))  # Filled Accumulated Quantity
        avg_price = Decimal(order.get('ap', '0'))  # Average Price
        timestamp = raw_data.get('E', 0)
        
        # Calculate total value in USDT
        price_usdt = quantity * avg_price
        
        # Format timestamp
        dt = datetime.fromtimestamp(timestamp / 1000)
        display_time = dt.strftime('%H:%M:%S')
        
        # Format numbers
        if symbol_info:
            quantity_formatted = formatting_service.format_amount(float(quantity), symbol_info)
        else:
            # Fallback to existing logic if no symbol info
            if quantity >= 1:
                quantity_formatted = f"{quantity:.3f}"
            else:
                quantity_formatted = f"{quantity:.6f}"
            
        # Format price to whole USDT with thousand separators
        price_formatted = f"{int(round(float(price_usdt))):,}"
        
        return {
            "symbol": display_symbol,
            "side": side,
            "quantity": str(quantity),
            "quantityFormatted": quantity_formatted,
            "priceUsdt": str(price_usdt),
            "priceUsdtFormatted": price_formatted,
            "timestamp": timestamp,
            "displayTime": display_time,
            "avgPrice": str(avg_price),
            "baseAsset": symbol_info.get('baseAsset', '') if symbol_info else ''
        }
    
    async def fetch_historical_liquidations_by_timeframe(
        self, 
        symbol: str, 
        timeframe: str, 
        start_time: Optional[int] = None, 
        end_time: Optional[int] = None
    ) -> List[Dict]:
        """
        Fetch historical liquidations from external API grouped by timeframe
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            timeframe: Timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            start_time: Start timestamp in milliseconds (optional)
            end_time: End timestamp in milliseconds (optional)
            
        Returns:
            List of aggregated liquidation volume data
        """
        # Create cache key
        cache_key = f"{symbol}:{timeframe}:{start_time}:{end_time}"
        
        # Check cache first
        if cache_key in self.liquidation_cache:
            cached_data, cache_time = self.liquidation_cache[cache_key]
            if time.time() - cache_time < self.cache_ttl:
                logger.debug(f"Returning cached liquidation data for {cache_key}")
                return cached_data
        
        if not settings.LIQUIDATION_API_BASE_URL:
            logger.warning("LIQUIDATION_API_BASE_URL not configured")
            return []
        
        try:
            session = await self._get_http_session()
            url = f"{settings.LIQUIDATION_API_BASE_URL}/liquidations"
            
            # Build parameters
            params = {
                "symbol": symbol.upper(),
                "timeframe": timeframe
                # Note: liqui_api doesn't support limit parameter
            }
            
            if start_time:
                params["start_timestamp"] = str(start_time)
            if end_time:
                params["end_timestamp"] = str(end_time)
            
            logger.info(f"Fetching liquidations from {url} with params: {params}")
            
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=120)) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Liquidation API error {response.status}: {error_text}")
                    return []
                
                raw_data = await response.json()
                
                # Aggregate the data by timeframe
                aggregated_data = await self.aggregate_liquidations_for_timeframe(
                    raw_data, timeframe, symbol
                )
                
                # Cache the result
                self.liquidation_cache[cache_key] = (aggregated_data, time.time())
                
                return aggregated_data
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching liquidations for {symbol}")
            return []
        except Exception as e:
            logger.error(f"Error fetching liquidations for {symbol}: {e}")
            return []
    
    async def aggregate_liquidations_for_timeframe(
        self, 
        liquidations: List[Dict], 
        timeframe: str,
        symbol: str
    ) -> List[Dict]:
        """
        Aggregate liquidations into timeframe buckets
        
        Args:
            liquidations: List of individual liquidation orders
            timeframe: Target timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            symbol: Trading symbol for formatting
            
        Returns:
            List of aggregated volume data by timeframe
        """
        if not liquidations:
            return []
        
        # Convert timeframe to milliseconds
        timeframe_ms = self._get_timeframe_ms(timeframe)
        
        # Group liquidations by time bucket
        buckets = defaultdict(lambda: {"buy_volume": Decimal("0"), "sell_volume": Decimal("0"), "count": 0})
        
        # Process liquidation data from liqui_api
        # Format: {"timestamp": ms, "side": "buy/sell", "cumulated_usd_size": float}
        for liq in liquidations:
            # Get timestamp and calculate bucket start time
            timestamp = liq.get("timestamp", 0)
            if not timestamp:
                continue
            
            # Calculate bucket start time
            bucket_time = (timestamp // timeframe_ms) * timeframe_ms
                
            side = liq.get("side", "").upper()
            volume = Decimal(str(liq.get("cumulated_usd_size", "0")))
            
            # Add to appropriate side
            if side == "BUY":
                buckets[bucket_time]["buy_volume"] += volume
                buckets[bucket_time]["count"] += 1
            elif side == "SELL":
                buckets[bucket_time]["sell_volume"] += volume
                buckets[bucket_time]["count"] += 1
        
        # Convert to list format
        result = []
        symbol_info = self.symbol_info_cache.get(symbol)
        
        # Determine the time range to fill
        if buckets:
            # Get min and max bucket times
            bucket_times = list(buckets.keys())
            min_bucket_time = min(bucket_times)
            max_bucket_time = max(bucket_times)
            
            # Generate all time buckets in the range
            current_bucket = min_bucket_time
            while current_bucket <= max_bucket_time:
                if current_bucket in buckets:
                    # We have data for this bucket
                    data = buckets[current_bucket]
                    buy_volume = float(data["buy_volume"])
                    sell_volume = float(data["sell_volume"])
                    total_volume = buy_volume + sell_volume
                    delta_volume = buy_volume - sell_volume
                    count = data["count"]
                else:
                    # No data for this bucket - fill with zeros
                    buy_volume = 0.0
                    sell_volume = 0.0
                    total_volume = 0.0
                    delta_volume = 0.0
                    count = 0
                
                result.append({
                    "time": int(current_bucket / 1000),  # Convert to seconds for chart
                    "buy_volume": str(buy_volume),
                    "sell_volume": str(sell_volume),
                    "total_volume": str(total_volume),
                    "delta_volume": str(delta_volume),
                    "buy_volume_formatted": formatting_service.format_total(buy_volume, symbol_info),
                    "sell_volume_formatted": formatting_service.format_total(sell_volume, symbol_info),
                    "total_volume_formatted": formatting_service.format_total(total_volume, symbol_info),
                    "delta_volume_formatted": formatting_service.format_total(abs(delta_volume), symbol_info),
                    "count": count,
                    "timestamp_ms": current_bucket
                })
                
                # Move to next bucket
                current_bucket += timeframe_ms
        
        return result
    
    def _get_timeframe_ms(self, timeframe: str) -> int:
        """Convert timeframe string to milliseconds"""
        timeframe_map = {
            "1m": 60 * 1000,
            "5m": 5 * 60 * 1000,
            "15m": 15 * 60 * 1000,
            "30m": 30 * 60 * 1000,
            "1h": 60 * 60 * 1000,
            "4h": 4 * 60 * 60 * 1000,
            "1d": 24 * 60 * 60 * 1000
        }
        return timeframe_map.get(timeframe, 60 * 1000)  # Default to 1m
        
    async def _notify_callbacks(self, symbol: str, data: Dict):
        """Notify all registered callbacks with new data"""
        callbacks = self.data_callbacks.get(symbol, [])
        logger.debug(f"Notifying {len(callbacks)} callbacks for {symbol} with liquidation data")
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Error in liquidation callback: {e}")
    
    async def _get_http_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session for API calls"""
        if not self._http_session:
            self._http_session = aiohttp.ClientSession()
        return self._http_session
    
    async def fetch_historical_liquidations(self, symbol: str, limit: int = 50, symbol_info: Optional[Dict] = None) -> List[Dict]:
        """
        Fetch historical liquidations from external API
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            limit: Maximum number of liquidations to fetch
            symbol_info: Optional symbol information for formatting
            
        Returns:
            List of formatted liquidation data dictionaries
        """
        if not settings.LIQUIDATION_API_BASE_URL:
            logger.warning("LIQUIDATION_API_BASE_URL not configured, returning empty list")
            return []
        
        try:
            session = await self._get_http_session()
            url = f"{settings.LIQUIDATION_API_BASE_URL}/liquidation-orders"
            params = {"symbol": symbol.upper(), "limit": limit}
            
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status != 200:
                    logger.warning(f"Liquidation API returned status {response.status} for {symbol}")
                    return []
                
                data = await response.json()
                
                # Convert API format to our WebSocket format
                return [self._convert_api_to_ws_format(item, symbol, symbol_info) for item in data]
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching historical liquidations for {symbol}")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch historical liquidations for {symbol}: {e}")
            return []
    
    def _convert_api_to_ws_format(self, api_data: Dict, display_symbol: str, symbol_info: Optional[Dict] = None) -> Dict:
        """
        Convert API response format to match WebSocket format
        
        Args:
            api_data: Liquidation data from API
            display_symbol: Symbol for display
            symbol_info: Optional symbol information for formatting
            
        Returns:
            Formatted liquidation data matching WebSocket format
        """
        # Calculate USDT value using filled quantity
        quantity = Decimal(api_data.get("order_filled_accumulated_quantity", "0"))
        avg_price = Decimal(api_data.get("average_price", "0"))
        amount_usdt = quantity * avg_price
        
        # Convert timestamp
        timestamp = api_data.get("order_trade_time", 0)
        dt = datetime.fromtimestamp(timestamp / 1000)
        display_time = dt.strftime('%H:%M:%S')
        
        # Format quantity
        if symbol_info:
            quantity_formatted = formatting_service.format_amount(float(quantity), symbol_info)
        else:
            # Fallback formatting
            if quantity >= 1:
                quantity_formatted = f"{quantity:.3f}"
            else:
                quantity_formatted = f"{quantity:.6f}"
        
        # Format price to whole USDT with thousand separators
        price_formatted = f"{int(round(float(amount_usdt))):,}"
        
        return {
            "symbol": display_symbol,
            "side": api_data.get("side", "").upper(),  # API returns lowercase
            "quantity": str(quantity),
            "quantityFormatted": quantity_formatted,
            "priceUsdt": str(amount_usdt),
            "priceUsdtFormatted": price_formatted,
            "timestamp": timestamp,
            "displayTime": display_time,
            "avgPrice": str(avg_price),
            "baseAsset": symbol_info.get('baseAsset', '') if symbol_info else ''
        }
                
    async def disconnect_stream(self, symbol: str, callback: Optional[Callable] = None):
        """
        Disconnect from liquidation stream with reference counting
        Only closes Binance connection when no more subscribers
        
        Args:
            symbol: Trading symbol to disconnect
            callback: Specific callback to remove (if None, removes all)
        """
        if callback:
            # Remove specific callback
            if symbol in self.data_callbacks and callback in self.data_callbacks[symbol]:
                self.data_callbacks[symbol].remove(callback)
                logger.info(f"Removed callback from {symbol} liquidation stream ({len(self.data_callbacks[symbol])} remaining subscribers)")
                
                # If still have subscribers, don't close connection
                if self.data_callbacks[symbol]:
                    return
            else:
                # Callback not found or symbol not in callbacks
                return
        
        # Remove all callbacks or no more callbacks remaining
        logger.info(f"Disconnecting Binance liquidation stream for {symbol}")
        
        # Stop the stream
        self.running_streams[symbol] = False
        
        # Cancel the connection task
        if symbol in self.active_connections:
            task = self.active_connections[symbol]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.active_connections[symbol]
            
        # Clear callbacks
        if symbol in self.data_callbacks:
            del self.data_callbacks[symbol]
            
        # Clear symbol info cache
        if symbol in self.symbol_info_cache:
            del self.symbol_info_cache[symbol]
            
        # Clear global caches from liquidations_ws when last subscriber disconnects
        # This prevents stale data from persisting across reconnections
        from app.api.v1.endpoints.liquidations_ws import liquidations_cache, historical_loaded
        
        if symbol in liquidations_cache:
            logger.info(f"Clearing liquidations cache for {symbol} (contained {len(liquidations_cache[symbol])} items)")
            del liquidations_cache[symbol]
            
        if symbol in historical_loaded:
            logger.info(f"Resetting historical_loaded flag for {symbol}")
            del historical_loaded[symbol]
            
        # Clear aggregation buffers for this symbol
        if symbol in self.liquidation_buffers:
            logger.info(f"Clearing liquidation aggregation buffers for {symbol}")
            del self.liquidation_buffers[symbol]
            
        if symbol in self.buffer_callbacks:
            del self.buffer_callbacks[symbol]
            
        if symbol in self.aggregation_tasks:
            # Cancel any running aggregation tasks
            for timeframe, task in self.aggregation_tasks[symbol].items():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self.aggregation_tasks[symbol]
            
        # Clear accumulated volumes to prevent stale data
        if symbol in self.accumulated_volumes:
            logger.info(f"Clearing accumulated volume data for {symbol}")
            del self.accumulated_volumes[symbol]
            
    async def disconnect_all(self):
        """Disconnect all active streams"""
        symbols = list(self.active_connections.keys())
        for symbol in symbols:
            await self.disconnect_stream(symbol)
        
        # Close HTTP session if it exists
        if self._http_session:
            await self._http_session.close()
            self._http_session = None
    
    async def _add_to_aggregation_buffers(self, symbol: str, liquidation_data: Dict):
        """Add liquidation to timeframe aggregation buffers"""
        logger.debug(f"Adding liquidation to buffers for {symbol}: {liquidation_data.get('priceUsdt', 'N/A')} USDT, side: {liquidation_data.get('side', 'N/A')}")
        if symbol not in self.liquidation_buffers:
            self.liquidation_buffers[symbol] = {}
        
        # Get all active timeframes for this symbol
        timeframes = list(self.buffer_callbacks.get(symbol, {}).keys())
        
        for timeframe in timeframes:
            if timeframe not in self.liquidation_buffers[symbol]:
                self.liquidation_buffers[symbol][timeframe] = []
            
            # Add to buffer
            self.liquidation_buffers[symbol][timeframe].append(liquidation_data)
            
            # Start aggregation task if not running
            if symbol not in self.aggregation_tasks:
                self.aggregation_tasks[symbol] = {}
            
            if timeframe not in self.aggregation_tasks[symbol]:
                task = asyncio.create_task(
                    self._run_aggregation_task(symbol, timeframe)
                )
                self.aggregation_tasks[symbol][timeframe] = task
    
    async def _run_aggregation_task(self, symbol: str, timeframe: str):
        """Run periodic aggregation for a symbol/timeframe"""
        timeframe_ms = self._get_timeframe_ms(timeframe)
        interval_seconds = timeframe_ms / 1000  # Convert to seconds
        
        while symbol in self.buffer_callbacks and timeframe in self.buffer_callbacks[symbol]:
            try:
                # Wait for next interval
                await asyncio.sleep(min(interval_seconds, 5))  # Update at least every 5 seconds
                
                # Process buffer
                await self._process_aggregation_buffer(symbol, timeframe)
                
            except Exception as e:
                logger.error(f"Error in aggregation task for {symbol}/{timeframe}: {e}")
                await asyncio.sleep(1)
    
    async def _process_aggregation_buffer(self, symbol: str, timeframe: str):
        """Process and emit aggregated liquidation data with accumulation"""
        import time
        start_time = time.time()
        logger.debug(f"Starting aggregation processing for {symbol} {timeframe}")
        if (symbol not in self.liquidation_buffers or 
            timeframe not in self.liquidation_buffers[symbol]):
            return
        
        buffer = self.liquidation_buffers[symbol][timeframe]
        if not buffer:
            return
        
        # Initialize accumulated volumes for this symbol/timeframe if needed
        if symbol not in self.accumulated_volumes:
            self.accumulated_volumes[symbol] = {}
        if timeframe not in self.accumulated_volumes[symbol]:
            self.accumulated_volumes[symbol][timeframe] = {}
        
        # Get current time and timeframe info
        current_time = int(time.time() * 1000)
        timeframe_ms = self._get_timeframe_ms(timeframe)
        
        # Calculate current bucket
        current_bucket = (current_time // timeframe_ms) * timeframe_ms
        
        # Process new liquidations and add to accumulated volumes
        new_liquidations = []
        for liq in buffer:
            timestamp = liq.get("timestamp", 0)
            bucket_time = (timestamp // timeframe_ms) * timeframe_ms
            
            # Calculate volume
            price_usdt = Decimal(liq.get("priceUsdt", "0"))
            side = liq.get("side", "").upper()
            
            # Initialize bucket if needed
            if bucket_time not in self.accumulated_volumes[symbol][timeframe]:
                self.accumulated_volumes[symbol][timeframe][bucket_time] = {
                    "buy_volume": Decimal("0"),
                    "sell_volume": Decimal("0"),
                    "count": 0
                }
            
            # Accumulate volume (not replace)
            if side == "BUY":
                self.accumulated_volumes[symbol][timeframe][bucket_time]["buy_volume"] += price_usdt
            elif side == "SELL":
                self.accumulated_volumes[symbol][timeframe][bucket_time]["sell_volume"] += price_usdt
            
            self.accumulated_volumes[symbol][timeframe][bucket_time]["count"] += 1
            new_liquidations.append(liq)
        
        # Clear the buffer after processing
        buffer_size = len(self.liquidation_buffers[symbol][timeframe])
        self.liquidation_buffers[symbol][timeframe] = []
        logger.debug(f"Cleared aggregation buffer for {symbol} {timeframe}, processed {buffer_size} liquidations")
        
        # Get only the buckets that were updated
        updated_buckets = set()
        for liq in new_liquidations:
            timestamp = liq.get("timestamp", 0)
            bucket_time = (timestamp // timeframe_ms) * timeframe_ms
            updated_buckets.add(bucket_time)
        
        # Format and emit only updated volume data
        if updated_buckets:
            symbol_info = self.symbol_info_cache.get(symbol)
            volume_updates = []
            
            for bucket_time in sorted(updated_buckets):
                data = self.accumulated_volumes[symbol][timeframe][bucket_time]
                buy_volume = float(data["buy_volume"])
                sell_volume = float(data["sell_volume"])
                total_volume = buy_volume + sell_volume
                
                # Calculate delta (positive = more shorts liquidated, negative = more longs liquidated)
                delta_volume = buy_volume - sell_volume
                
                logger.debug(f"Volume aggregation for {symbol} {timeframe} bucket {int(bucket_time/1000)}: "
                           f"buy={buy_volume:.2f}, sell={sell_volume:.2f}, delta={delta_volume:.2f}, count={data['count']}")
                
                volume_updates.append({
                    "time": int(bucket_time / 1000),
                    "buy_volume": str(buy_volume),
                    "sell_volume": str(sell_volume),
                    "total_volume": str(total_volume),
                    "delta_volume": str(delta_volume),
                    "buy_volume_formatted": formatting_service.format_total(buy_volume, symbol_info),
                    "sell_volume_formatted": formatting_service.format_total(sell_volume, symbol_info),
                    "total_volume_formatted": formatting_service.format_total(total_volume, symbol_info),
                    "delta_volume_formatted": formatting_service.format_total(abs(delta_volume), symbol_info),
                    "count": data["count"],
                    "timestamp_ms": bucket_time
                })
            
            # Notify callbacks with updated data only
            await self._notify_volume_callbacks(symbol, timeframe, volume_updates)
    
    async def register_volume_callback(self, symbol: str, timeframe: str, callback: Callable):
        """Register callback for aggregated volume updates"""
        if symbol not in self.buffer_callbacks:
            self.buffer_callbacks[symbol] = {}
        
        if timeframe not in self.buffer_callbacks[symbol]:
            self.buffer_callbacks[symbol][timeframe] = []
        
        self.buffer_callbacks[symbol][timeframe].append(callback)
        
        # Initialize buffer if needed
        if symbol not in self.liquidation_buffers:
            self.liquidation_buffers[symbol] = {}
        
        if timeframe not in self.liquidation_buffers[symbol]:
            self.liquidation_buffers[symbol][timeframe] = []
    
    async def unregister_volume_callback(self, symbol: str, timeframe: str, callback: Callable):
        """Unregister volume callback with reference counting"""
        if (symbol in self.buffer_callbacks and 
            timeframe in self.buffer_callbacks[symbol]):
            try:
                self.buffer_callbacks[symbol][timeframe].remove(callback)
                logger.info(f"Removed volume callback for {symbol}/{timeframe} ({len(self.buffer_callbacks[symbol][timeframe])} remaining)")
                
                # Clean up if no more callbacks
                if not self.buffer_callbacks[symbol][timeframe]:
                    del self.buffer_callbacks[symbol][timeframe]
                    
                    # Stop aggregation task
                    if (symbol in self.aggregation_tasks and 
                        timeframe in self.aggregation_tasks[symbol]):
                        task = self.aggregation_tasks[symbol][timeframe]
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                        del self.aggregation_tasks[symbol][timeframe]
                    
                    # Clear buffer
                    if (symbol in self.liquidation_buffers and 
                        timeframe in self.liquidation_buffers[symbol]):
                        del self.liquidation_buffers[symbol][timeframe]
                
                if not self.buffer_callbacks[symbol]:
                    del self.buffer_callbacks[symbol]
                    
            except ValueError:
                logger.warning(f"Callback not found for {symbol}/{timeframe}")
                pass
    
    async def _notify_volume_callbacks(self, symbol: str, timeframe: str, volume_data: List[Dict]):
        """Notify registered callbacks with volume updates"""
        if (symbol not in self.buffer_callbacks or 
            timeframe not in self.buffer_callbacks[symbol]):
            return
        
        callbacks = self.buffer_callbacks[symbol][timeframe]
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(volume_data)
                else:
                    callback(volume_data)
            except Exception as e:
                logger.error(f"Error in volume callback: {e}")

# Singleton instance
liquidation_service = LiquidationService()