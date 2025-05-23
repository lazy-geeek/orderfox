"""
Pydantic schemas for API request/response models.

This module defines the data models used for API endpoints,
particularly for market data operations.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


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

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "BTCUSDT",
                "symbol": "BTCUSDT",
                "base_asset": "BTC",
                "quote_asset": "USDT",
            }
        }
    )


class OrderBookLevel(BaseModel):
    """
    Schema for a single order book level (bid or ask).

    Represents a price level in the order book with its
    corresponding quantity/amount.
    """

    price: float = Field(..., description="Price level", gt=0)
    amount: float = Field(..., description="Quantity/amount at this price level", gt=0)

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
    timestamp: datetime = Field(
        ..., description="Timestamp when the order book was captured"
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
                "timestamp": "2024-01-01T12:00:00Z",
            }
        }
    )


class Candle(BaseModel):
    """
    Schema for candlestick/OHLCV data.

    Represents a single candlestick with open, high, low, close prices
    and volume for a specific time period.
    """

    timestamp: datetime = Field(..., description="Timestamp for the candle period")
    open: float = Field(..., description="Opening price", gt=0)
    high: float = Field(..., description="Highest price during the period", gt=0)
    low: float = Field(..., description="Lowest price during the period", gt=0)
    close: float = Field(..., description="Closing price", gt=0)
    volume: float = Field(..., description="Trading volume during the period", ge=0)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "timestamp": "2024-01-01T12:00:00Z",
                "open": 43200.00,
                "high": 43300.00,
                "low": 43150.00,
                "close": 43250.00,
                "volume": 125.75,
            }
        }
    )


class Ticker(BaseModel):
    """
    Schema for ticker data.

    Represents real-time ticker information including current price,
    24h change, volume, and other market statistics.
    """

    symbol: str = Field(..., description="Trading symbol")
    last: float = Field(..., description="Last traded price", gt=0)
    bid: Optional[float] = Field(None, description="Best bid price", gt=0)
    ask: Optional[float] = Field(None, description="Best ask price", gt=0)
    high: Optional[float] = Field(None, description="24h high price", gt=0)
    low: Optional[float] = Field(None, description="24h low price", gt=0)
    open: Optional[float] = Field(None, description="24h opening price", gt=0)
    close: Optional[float] = Field(None, description="24h closing price", gt=0)
    change: Optional[float] = Field(None, description="24h price change")
    percentage: Optional[float] = Field(None, description="24h percentage change")
    volume: Optional[float] = Field(None, description="24h trading volume", ge=0)
    quote_volume: Optional[float] = Field(None, description="24h quote volume", ge=0)
    timestamp: datetime = Field(..., description="Timestamp of the ticker data")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "BTCUSDT",
                "last": 43250.00,
                "bid": 43249.50,
                "ask": 43250.50,
                "high": 43500.00,
                "low": 43000.00,
                "open": 43100.00,
                "close": 43250.00,
                "change": 150.00,
                "percentage": 0.35,
                "volume": 1250.75,
                "quote_volume": 54125000.00,
                "timestamp": "2024-01-01T12:00:00Z",
            }
        }
    )
