"""
Pydantic schemas for API request/response models.

This module defines the data models used for API endpoints,
particularly for market data operations.
"""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


def to_camel(string: str) -> str:
    """Converts snake_case to camelCase."""
    return "".join(
        word.capitalize() if i > 0 else word for i,
        word in enumerate(
            string.split("_")))


class SymbolInfo(BaseModel):
    """
    Schema for trading symbol information.

    Represents basic information about a trading pair/symbol
    available on the exchange.
    """

    id: str = Field(..., description="Unique identifier for the symbol")
    symbol: str = Field(..., description="Trading symbol (e.g., 'BTCUSDT')")
    base_asset: str = Field(..., description="Base asset (e.g., 'BTC')")
    quote_asset: str = Field(..., description="Quote asset (e.g., 'USDT')")
    ui_name: str = Field(
        ..., description="User-friendly display name (e.g., 'BTC/USDT')"
    )
    volume24h: Optional[float] = Field(
        None, description="24-hour trading volume in quote currency"
    )
    volume24h_formatted: Optional[str] = Field(
        None, description="Formatted 24-hour trading volume (e.g., '1.23B', '456.78M')"
    )
    pricePrecision: Optional[int] = Field(
        None, description="Number of decimal places for price accuracy"
    )
    priceFormat: Optional[Dict[str, Any]] = Field(
        None, description="TradingView Lightweight Charts price format configuration"
    )
    roundingOptions: Optional[List[float]] = Field(
        None, description="Available rounding options for this symbol"
    )
    defaultRounding: Optional[float] = Field(
        None, description="Default rounding value for this symbol"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        json_schema_extra={
            "example": {
                "id": "BTCUSDT",
                "symbol": "BTC/USDT:USDT",
                "baseAsset": "BTC",
                "quoteAsset": "USDT",
                "uiName": "BTC/USDT",
                "volume24h": 1234567.89,
            }
        },
    )


class OrderBookLevel(BaseModel):
    """
    Schema for a single order book level (bid or ask).

    Represents a price level in the order book with its
    corresponding quantity/amount.
    """

    price: float = Field(..., description="Price level", gt=0)
    amount: float = Field(...,
                          description="Quantity/amount at this price level",
                          gt=0)

    model_config = ConfigDict(
        json_schema_extra={"example": {"price": 43250.50, "amount": 1.25}}
    )


class OrderBook(BaseModel):
    """
    Schema for order book data.

    Contains the current state of the order book for a symbol,
    including bids, asks, and timestamp.
    """

    symbol: str = Field(..., description="Trading symbol")
    bids: List[OrderBookLevel] = Field(
        ..., description="List of bid levels (buy orders)"
    )
    asks: List[OrderBookLevel] = Field(
        ..., description="List of ask levels (sell orders)"
    )
    timestamp: int = Field(
        ...,
        description="Unix timestamp in milliseconds when the order book was captured",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "BTCUSDT",
                "bids": [
                    {"price": 43250.50, "amount": 1.25},
                    {"price": 43250.00, "amount": 0.75},
                ],
                "asks": [
                    {"price": 43251.00, "amount": 0.50},
                    {"price": 43251.50, "amount": 2.00},
                ],
                "timestamp": 1704110400000,  # Unix timestamp in milliseconds
            }
        }
    )


class Candle(BaseModel):
    """
    Schema for candlestick/OHLCV data.

    Represents a single candlestick with open, high, low, close prices
    and volume for a specific time period.
    """

    timestamp: int = Field(
        ..., description="Unix timestamp in milliseconds for the candle period"
    )
    open: float = Field(..., description="Opening price", gt=0)
    high: float = Field(...,
                        description="Highest price during the period",
                        gt=0)
    low: float = Field(..., description="Lowest price during the period", gt=0)
    close: float = Field(..., description="Closing price", gt=0)
    volume: float = Field(...,
                          description="Trading volume during the period",
                          ge=0)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "timestamp": 1704110400000,  # Unix timestamp in milliseconds
                "open": 43200.00,
                "high": 43300.00,
                "low": 43150.00,
                "close": 43250.00,
                "volume": 125.75,
            }
        }
    )



class Trade(BaseModel):
    """
    Schema for trade data.

    Represents a single trade execution with price, amount, side,
    and formatted display values.
    """

    id: str = Field(..., description="Unique trade identifier")
    price: float = Field(..., description="Trade execution price", gt=0)
    amount: float = Field(..., description="Trade amount/quantity", gt=0)
    side: Literal["buy", "sell"] = Field(..., description="Trade side (buy or sell)")
    timestamp: int = Field(
        ..., description="Unix timestamp in milliseconds when trade occurred"
    )
    price_formatted: str = Field(..., description="Formatted price string for display")
    amount_formatted: str = Field(..., description="Formatted amount string for display")
    time_formatted: str = Field(..., description="Formatted time string (HH:MM:SS)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "12345",
                "price": 50000.0,
                "amount": 1.5,
                "side": "buy",
                "timestamp": 1640995200000,
                "price_formatted": "50,000.00",
                "amount_formatted": "1.50000000",
                "time_formatted": "12:30:45"
            }
        }
    )


class TradesUpdate(BaseModel):
    """
    Schema for WebSocket trades update message.

    Represents a real-time update containing trade data for a symbol,
    including both historical and live trades.
    """

    type: Literal["trades_update"] = Field(
        default="trades_update", 
        description="Message type identifier"
    )
    symbol: str = Field(..., description="Trading symbol")
    trades: List[Trade] = Field(
        ..., description="List of trades (newest first)"
    )
    initial: bool = Field(
        default=False, 
        description="True for first batch of historical trades"
    )
    timestamp: int = Field(
        ..., description="Unix timestamp when update was sent"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "trades_update",
                "symbol": "BTCUSDT",
                "trades": [
                    {
                        "id": "12345",
                        "price": 50000.0,
                        "amount": 1.5,
                        "side": "buy",
                        "timestamp": 1640995200000,
                        "price_formatted": "50,000.00",
                        "amount_formatted": "1.50000000",
                        "time_formatted": "12:30:45"
                    }
                ],
                "initial": True,
                "timestamp": 1640995200000
            }
        }
    )


class TradeSide(str, Enum):
    """
    Enum for trade side options.
    """

    LONG = "long"
    SHORT = "short"
    CLOSE = "close"


class OrderType(str, Enum):
    """
    Enum for order type options.
    """

    MARKET = "market"
    LIMIT = "limit"


class Position(BaseModel):
    """
    Schema for trading position information.

    Represents a current trading position with entry price,
    current market price, and unrealized profit/loss.
    """

    symbol: str = Field(..., description="Trading symbol")
    side: str = Field(..., description="Position side (long/short)")
    size: float = Field(..., description="Position size")
    entryPrice: float = Field(...,
                              description="Entry price of the position",
                              gt=0)
    markPrice: float = Field(..., description="Current mark price", gt=0)
    unrealizedPnl: float = Field(..., description="Unrealized profit and loss")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "BTCUSDT",
                "side": "long",
                "size": 0.5,
                "entryPrice": 43000.00,
                "markPrice": 43250.00,
                "unrealizedPnl": 125.00,
            }
        }
    )


class TradeRequest(BaseModel):
    """
    Schema for trade request.

    Represents a request to open, close, or modify a trading position.
    """

    symbol: str = Field(..., description="Trading symbol")
    side: TradeSide = Field(..., description="Trade side (long/short/close)")
    amount: float = Field(..., description="Trade amount", gt=0)
    type: OrderType = Field(..., description="Order type (market/limit)")
    price: Optional[float] = Field(
        None, description="Limit price (required for limit orders)", gt=0
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "BTCUSDT",
                "side": "long",
                "amount": 0.5,
                "type": "market",
                "price": None,
            }
        }
    )


class TradeResponse(BaseModel):
    """
    Schema for trade response.

    Represents the response after executing a trade request,
    including status, message, and optional order/position information.
    """

    status: str = Field(..., description="Trade execution status")
    message: str = Field(..., description="Response message")
    orderId: Optional[str] = Field(None, description="Order ID if applicable")
    positionInfo: Optional[Position] = Field(
        None, description="Updated position information"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Trade executed successfully",
                "orderId": "12345678",
                "positionInfo": {
                    "symbol": "BTCUSDT",
                    "side": "long",
                    "size": 0.5,
                    "entryPrice": 43000.00,
                    "markPrice": 43250.00,
                    "unrealizedPnl": 125.00,
                },
            }
        }
    )
