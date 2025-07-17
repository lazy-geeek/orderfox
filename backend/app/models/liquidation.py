"""
Liquidation models for API responses and data structures
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal
from decimal import Decimal


class LiquidationVolume(BaseModel):
    """Aggregated liquidation volume for a specific time bucket"""
    
    time: int = Field(..., description="Unix timestamp in seconds")
    buy_volume: str = Field(..., description="Total buy liquidation volume (shorts liquidated)")
    sell_volume: str = Field(..., description="Total sell liquidation volume (longs liquidated)")
    total_volume: str = Field(..., description="Total liquidation volume")
    delta_volume: str = Field(..., description="Delta volume (buy - sell), positive = more shorts liquidated")
    buy_volume_formatted: str = Field(..., description="Formatted buy volume for display")
    sell_volume_formatted: str = Field(..., description="Formatted sell volume for display")
    total_volume_formatted: str = Field(..., description="Formatted total volume for display")
    delta_volume_formatted: str = Field(..., description="Formatted delta volume for display")
    count: int = Field(..., description="Number of liquidations in this bucket")
    timestamp_ms: int = Field(..., description="Timestamp in milliseconds")
    
    class Config:
        json_encoders = {
            Decimal: str
        }


class LiquidationVolumeResponse(BaseModel):
    """Response model for liquidation volume API endpoint"""
    
    symbol: str = Field(..., description="Trading symbol")
    timeframe: str = Field(..., description="Timeframe (1m, 5m, 15m, 1h, 4h, 1d)")
    data: List[LiquidationVolume] = Field(..., description="List of liquidation volume data")
    start_time: Optional[int] = Field(None, description="Start timestamp in milliseconds")
    end_time: Optional[int] = Field(None, description="End timestamp in milliseconds")
    
    @validator('timeframe')
    def validate_timeframe(cls, v):
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
        if v not in valid_timeframes:
            raise ValueError(f"Invalid timeframe. Must be one of: {', '.join(valid_timeframes)}")
        return v


class LiquidationVolumeUpdate(BaseModel):
    """WebSocket message for liquidation volume updates"""
    
    type: Literal["liquidation_volume"] = Field(default="liquidation_volume")
    symbol: str = Field(..., description="Trading symbol")
    timeframe: str = Field(..., description="Timeframe")
    data: List[LiquidationVolume] = Field(..., description="Volume updates")
    timestamp: str = Field(..., description="ISO format timestamp")
    is_update: bool = Field(default=False, description="True for real-time updates, False for historical data")