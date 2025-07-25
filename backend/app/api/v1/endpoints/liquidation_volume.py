"""
API endpoints for liquidation volume data
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime, timedelta
import logging

from app.services.liquidation_service import liquidation_service
from app.models.liquidation import LiquidationVolumeResponse, LiquidationVolume

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/liquidation-volume/{symbol}/{timeframe}", response_model=LiquidationVolumeResponse)
async def get_liquidation_volume(
    symbol: str,
    timeframe: str,
    start_time: Optional[int] = Query(None, description="Start timestamp in milliseconds"),
    end_time: Optional[int] = Query(None, description="End timestamp in milliseconds")
):
    """
    Get aggregated liquidation volume data for a symbol and timeframe
    
    Args:
        symbol: Trading symbol (e.g., BTCUSDT)
        timeframe: Timeframe (1m, 5m, 15m, 1h, 4h, 1d)
        start_time: Start timestamp in milliseconds (optional)
        end_time: End timestamp in milliseconds (optional)
    
    Returns:
        LiquidationVolumeResponse with aggregated volume data including:
        - Volume data for each time bucket (buy, sell, total, delta)
        - Moving average values (ma_value, ma_value_formatted) calculated from
          last 50 non-zero volume periods
    """
    try:
        # Validate timeframe
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
        if timeframe not in valid_timeframes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid timeframe. Must be one of: {', '.join(valid_timeframes)}"
            )
        
        # Default time range if not provided
        if not end_time:
            end_time = int(datetime.now().timestamp() * 1000)
        
        if not start_time:
            # Default to 24 hours ago
            start_time = end_time - (24 * 60 * 60 * 1000)
        
        # Validate time range
        if start_time >= end_time:
            raise HTTPException(
                status_code=400,
                detail="start_time must be before end_time"
            )
        
        # Limit time range to prevent excessive data
        max_range_days = {
            '1m': 1,    # 1 day for 1-minute data
            '5m': 3,    # 3 days for 5-minute data
            '15m': 7,   # 7 days for 15-minute data
            '30m': 14,  # 14 days for 30-minute data
            '1h': 30,   # 30 days for 1-hour data
            '4h': 90,   # 90 days for 4-hour data
            '1d': 365   # 365 days for daily data
        }
        
        max_range_ms = max_range_days.get(timeframe, 7) * 24 * 60 * 60 * 1000
        if end_time - start_time > max_range_ms:
            raise HTTPException(
                status_code=400,
                detail=f"Time range too large. Maximum {max_range_days.get(timeframe)} days for {timeframe} timeframe"
            )
        
        # Fetch aggregated liquidation data
        volume_data = await liquidation_service.fetch_historical_liquidations_by_timeframe(
            symbol=symbol.upper(),
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time
        )
        
        # Convert to response model
        return LiquidationVolumeResponse(
            symbol=symbol.upper(),
            timeframe=timeframe,
            data=[LiquidationVolume(**item) for item in volume_data],
            start_time=start_time,
            end_time=end_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching liquidation volume for {symbol}/{timeframe}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch liquidation volume data"
        )