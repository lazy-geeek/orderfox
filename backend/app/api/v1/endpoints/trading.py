from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Dict, Any

from app.api.v1.schemas import (
    TradeRequest,
    TradeResponse,
    Position as PositionSchema,
    OrderType,
    TradeSide,
)
from app.services.trading_engine_service import TradingEngineService

# Consider how the TradingEngineService will be provided/instantiated.
# For now, we can instantiate it directly or use a simple dependency.

router = APIRouter()


# This is a simple way to get a service instance.
# In a larger app, you might use FastAPI's dependency injection system more formally
# (e.g., with a global instance or a factory function).
def get_trading_engine_service():
    # If you make TradingEngineService a singleton or manage its instance elsewhere,
    # retrieve it here. For now, a new instance per request or a module-level instance.
    # Let's use a module-level instance for simplicity in this placeholder phase.
    # This is NOT suitable for production if the service has state that shouldn't be shared
    # across all requests in this manner without proper concurrency handling.
    # However, for placeholder purposes, it's straightforward.
    return trading_engine_service_instance


# Module-level instance (placeholder approach)
trading_engine_service_instance = TradingEngineService()


@router.post("/trade", response_model=TradeResponse)
async def execute_trade_endpoint(
    trade_request: TradeRequest,
    service: TradingEngineService = Depends(get_trading_engine_service),
):
    """
    Accepts a trade request and executes it using the trading engine.
    """
    try:
        # The service's execute_trade expects enum values if you defined them as such.
        # The Pydantic model TradeRequest should already validate and provide correct types.
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
        # If positionInfo is returned by the service, it should be a dict that can be parsed into PositionSchema.

        position_info_data = result.get("positionInfo")
        position_info_schema = None
        if position_info_data and isinstance(position_info_data, dict):
            # Map the dict from service to PositionSchema
            # This assumes the dict keys match PositionSchema fields.
            # A more robust mapping might be needed if keys differ.
            try:
                # A simple example, assuming direct mapping for placeholder
                position_info_schema = PositionSchema(
                    symbol=position_info_data.get("symbol"),
                    side=position_info_data.get("side"),
                    size=position_info_data.get(
                        "amount"
                    ),  # or "size" if service returns that
                    entryPrice=position_info_data.get("entry_price"),  # or "entryPrice"
                    markPrice=position_info_data.get("entry_price", 0)
                    * 1.0,  # Placeholder mark price
                    unrealizedPnl=0.0,  # Placeholder PnL
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
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions", response_model=List[PositionSchema])
async def get_open_positions_endpoint(
    service: TradingEngineService = Depends(get_trading_engine_service),
):
    """
    Fetches and returns a list of open positions from the trading engine.
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
                # Example mapping, adjust keys based on what `get_open_positions` actually returns
                formatted_positions.append(
                    PositionSchema(
                        symbol=pos_data.get("symbol"),
                        side=pos_data.get("side"),
                        size=pos_data.get("amount"),  # Assuming 'amount' is 'size'
                        entryPrice=pos_data.get("entry_price"),
                        markPrice=pos_data.get("entry_price", 0)
                        * 1.01,  # Placeholder mark price
                        unrealizedPnl=(
                            pos_data.get("entry_price", 0) * 1.01
                            - pos_data.get("entry_price", 0)
                        )
                        * pos_data.get("amount", 0),  # Placeholder PnL
                    )
                )
            except Exception as e:
                print(f"Error mapping position data: {e} - Data: {pos_data}")
                # Skip malformed data or handle error
        return formatted_positions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/set_trading_mode", response_model=Dict[str, str])
async def set_trading_mode_endpoint(
    mode_data: Dict[str, str] = Body(
        ..., example={"mode": "paper"}
    ),  # Use Body for request body
    service: TradingEngineService = Depends(get_trading_engine_service),
):
    """
    Sets the trading mode (e.g., "paper" or "live").
    Expects a JSON body like: {"mode": "paper"}
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
        return {"status": result.get("status"), "message": result.get("message")}
    except HTTPException:
        raise  # Re-raise HTTPException
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
