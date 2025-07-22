"""
Trading API endpoints.

This module provides FastAPI endpoints for executing trades, managing positions,
and controlling trading modes (paper vs live trading).
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Dict

from app.api.v1.schemas import (
    TradeRequest,
    TradeResponse,
    Position as PositionSchema,
)
from app.services.trading_engine_service import TradingEngineService

router = APIRouter()


# This is a simple way to get a service instance.
# In a larger app, you might use FastAPI's dependency injection system more formally
# (e.g., with a global instance or a factory function).
def get_trading_engine_service():
    """
    Dependency injection function to provide TradingEngineService instance.

    Returns the module-level trading engine service instance. In production,
    this would be replaced with proper dependency injection and service lifecycle management.

    Returns:
        TradingEngineService: The trading engine service instance
    """
    return trading_engine_service_instance


# Module-level instance (placeholder approach)
trading_engine_service_instance = TradingEngineService()


@router.post("/trade", response_model=TradeResponse)
async def execute_trade_endpoint(
    trade_request: TradeRequest,
    service: TradingEngineService = Depends(get_trading_engine_service),
):
    """
    Execute a trading order (buy/sell) in the current trading mode.

    Processes trade requests and executes them through the trading engine.
    Supports both paper trading (simulation) and live trading modes.

    Args:
        trade_request: Trade details including symbol, side, amount, type, and price
        service: Injected trading engine service

    Returns:
        TradeResponse: Execution status, order ID, and position information

    Raises:
        HTTPException: If trade execution fails or parameters are invalid
    """
    try:
        # The service's execute_trade expects enum values if you defined them as such.
        # The Pydantic model TradeRequest should already validate and provide
        # correct types.
        result = await service.execute_trade(
            symbol=trade_request.symbol,
            side=trade_request.side.value,  # Use .value if side is an Enum in Pydantic model
            amount=trade_request.amount,
            trade_type=trade_request.type.value,  # Use .value if type is an Enum
            price=trade_request.price,
        )
        # The service's execute_trade placeholder returns a dict.
        # We need to map this to TradeResponse.
        # Assuming the service returns a dict compatible with TradeResponse fields.
        # If positionInfo is returned by the service, it should be a dict that
        # can be parsed into PositionSchema.

        position_info_data = result.get("positionInfo")
        position_info_schema = None
        if position_info_data and isinstance(position_info_data, dict):
            # Map the dict from service to PositionSchema
            # This assumes the dict keys match PositionSchema fields.
            # A more robust mapping might be needed if keys differ.
            try:
                # A simple example, assuming direct mapping for placeholder
                position_info_schema = PositionSchema(
                    symbol=str(position_info_data.get("symbol", "")),
                    side=str(position_info_data.get("side", "")),
                    size=float(position_info_data.get("amount", 0)),
                    entryPrice=float(position_info_data.get("entryPrice", position_info_data.get("entry_price", 1))),
                    markPrice=float(position_info_data.get("markPrice", position_info_data.get("mark_price", position_info_data.get("entryPrice", position_info_data.get("entry_price", 1))))),
                    unrealizedPnl=float(position_info_data.get("unrealizedPnl", 0.0)),
                )
            except Exception as e:
                print(f"Error mapping positionInfo: {e}")
                # Fallback or handle error appropriately

        return TradeResponse(
            status=result.get("status", "error"),
            message=result.get("message", "An unexpected error occurred."),
            orderId=result.get("orderId"),
            positionInfo=position_info_schema,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trade execution failed: {str(e)}")


@router.get("/positions", response_model=List[PositionSchema])
async def get_open_positions_endpoint(
    service: TradingEngineService = Depends(get_trading_engine_service),
):
    """
    Retrieve all open trading positions for the current trading mode.

    Returns position data including symbol, side, size, entry price, mark price,
    and unrealized P&L. For paper trading, returns simulated positions.
    For live trading, fetches actual positions from the exchange.

    Args:
        service: Injected trading engine service

    Returns:
        List[PositionSchema]: List of open positions with P&L information

    Raises:
        HTTPException: If position retrieval fails
    """
    try:
        # The service.get_open_positions() placeholder returns a List[Dict[str, Any]]
        # We need to convert this to List[PositionSchema]
        raw_positions = await service.get_open_positions()

        # Map raw_positions (list of dicts) to List[PositionSchema]
        # This is a placeholder mapping.
        # A real implementation would ensure the dicts from the service
        # correctly map to the fields of PositionSchema.
        formatted_positions: List[PositionSchema] = []
        for pos_data in raw_positions:
            try:
                # Example mapping, adjust keys based on what
                # `get_open_positions` actually returns
                formatted_positions.append(
                    PositionSchema(
                        symbol=str(pos_data.get("symbol", "")),
                        side=str(pos_data.get("side", "")),
                        size=float(pos_data.get("size", pos_data.get("amount", 0))),
                        entryPrice=float(pos_data.get("entryPrice", pos_data.get("entry_price", 1))),
                        markPrice=float(pos_data.get("markPrice", pos_data.get("mark_price", pos_data.get("entryPrice", pos_data.get("entry_price", 1))))),
                        unrealizedPnl=float(pos_data.get("unrealizedPnl", 0.0)),
                    )
                )
            except Exception as e:
                print(f"Error mapping position data: {e} - Data: {pos_data}")
                # Skip malformed data or handle error
        return formatted_positions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch positions: {str(e)}")


@router.post("/set_trading_mode", response_model=Dict[str, str])
async def set_trading_mode_endpoint(
    mode_data: Dict[str, str] = Body(..., examples=[{"mode": "paper"}]),
    service: TradingEngineService = Depends(get_trading_engine_service),
):
    """
    Set the trading mode for the application.

    Switches between paper trading (simulation) and live trading modes.
    Paper mode is recommended for testing strategies safely without real money.

    Args:
        mode_data: JSON body containing mode ("paper" or "live")
        service: Injected trading engine service

    Returns:
        Dict containing status and confirmation message

    Raises:
        HTTPException: If mode is invalid or setting fails

    Example:
        POST /set_trading_mode
        {"mode": "paper"}
    """
    try:
        mode = mode_data.get("mode")
        if not mode:
            raise HTTPException(
                status_code=400, detail="Missing 'mode' in request body."
            )

        result = await service.set_trading_mode(mode)
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
        return {
            "status": result.get("status"),
            "message": result.get("message")}
    except HTTPException:
        raise  # Re-raise HTTPException
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set trading mode: {str(e)}")
