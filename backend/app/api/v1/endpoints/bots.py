"""
Bot CRUD endpoints for managing bots via HTTP API.
"""

import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.services.bot_service import bot_service
from app.services.data_stream_manager import data_stream_manager
from app.models.bot import Bot, BotCreate, BotUpdate, BotPublic, BotList, BotSymbolStats

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=BotPublic, status_code=status.HTTP_201_CREATED)
async def create_bot(
    bot_data: BotCreate,
    session: AsyncSession = Depends(get_session)
) -> BotPublic:
    """
    Create a new bot.
    
    Args:
        bot_data: Bot creation data
        session: Database session
        
    Returns:
        BotPublic: Created bot data
        
    Raises:
        HTTPException: If bot creation fails
    """
    try:
        logger.info(f"Creating bot: {bot_data.name} ({bot_data.symbol})")
        
        # Create bot
        bot = await bot_service.create_bot(bot_data, session)
        
        # Update data streams if the bot is active
        if bot.is_active:
            await data_stream_manager.update_active_streams(session)
        
        logger.info(f"Bot created successfully: {bot.name} - ID: {bot.id}")
        return bot
        
    except ValueError as e:
        logger.warning(f"Invalid bot data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create bot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("", response_model=BotList)
async def get_bots(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Number of bots per page"),
    session: AsyncSession = Depends(get_session)
) -> BotList:
    """
    Get all bots with pagination.
    
    Args:
        page: Page number (1-based)
        page_size: Number of bots per page
        session: Database session
        
    Returns:
        BotList: Paginated list of bots
    """
    try:
        logger.debug(f"Getting bots - page: {page}, page_size: {page_size}")
        
        bot_list = await bot_service.get_all_bots(session, page, page_size)
        
        logger.debug(f"Retrieved {len(bot_list.bots)} bots (page {page})")
        return bot_list
        
    except Exception as e:
        logger.error(f"Failed to get bots: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/health", response_model=dict)
async def health_check(
    session: AsyncSession = Depends(get_session)
) -> dict:
    """
    Health check endpoint for bot management.
    
    Args:
        session: Database session
        
    Returns:
        dict: Health check results
    """
    try:
        # Check bot service health
        bot_stats = await bot_service.get_bot_stats_by_symbol(session)
        cache_stats = bot_service.get_cache_stats()
        
        # Check data stream manager health
        stream_health = await data_stream_manager.health_check()
        
        health = {
            "status": "healthy",
            "bot_service": {
                "symbols_count": len(bot_stats),
                "cache_hits": cache_stats.get("hits", 0),
                "cache_misses": cache_stats.get("misses", 0)
            },
            "data_stream": stream_health
        }
        
        logger.info(f"Health check completed: {health}")
        return health
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


@router.get("/{bot_id}", response_model=BotPublic)
async def get_bot(
    bot_id: UUID,
    session: AsyncSession = Depends(get_session)
) -> BotPublic:
    """
    Get a specific bot by ID.
    
    Args:
        bot_id: Bot UUID
        session: Database session
        
    Returns:
        BotPublic: Bot data
        
    Raises:
        HTTPException: If bot not found
    """
    try:
        logger.debug(f"Getting bot: {bot_id}")
        
        bot = await bot_service.get_bot(bot_id, session)
        
        if not bot:
            logger.warning(f"Bot not found: {bot_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot not found"
            )
        
        logger.debug(f"Retrieved bot: {bot.name} ({bot.symbol})")
        return bot
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get bot {bot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.patch("/{bot_id}", response_model=BotPublic)
async def update_bot(
    bot_id: UUID,
    bot_data: BotUpdate,
    session: AsyncSession = Depends(get_session)
) -> BotPublic:
    """
    Update a bot.
    
    Args:
        bot_id: Bot UUID
        bot_data: Bot update data
        session: Database session
        
    Returns:
        BotPublic: Updated bot data
        
    Raises:
        HTTPException: If bot not found or update fails
    """
    try:
        logger.info(f"Updating bot: {bot_id}")
        
        # Check if bot exists first
        existing_bot = await bot_service.get_bot(bot_id, session)
        if not existing_bot:
            logger.warning(f"Bot not found for update: {bot_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot not found"
            )
        
        # Update bot
        updated_bot = await bot_service.update_bot(bot_id, bot_data, session)
        
        # Ensure update was successful
        if not updated_bot:
            logger.error(f"Bot update failed for ID: {bot_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Bot update failed"
            )
        
        # Update data streams if active status changed
        if bot_data.is_active is not None:
            await data_stream_manager.update_active_streams(session)
        
        logger.info(f"Bot updated successfully: {updated_bot.name} - ID: {updated_bot.id}")
        return updated_bot
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid bot data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update bot {bot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete("/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bot(
    bot_id: UUID,
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Delete a bot.
    
    Args:
        bot_id: Bot UUID
        session: Database session
        
    Raises:
        HTTPException: If bot not found
    """
    try:
        logger.info(f"Deleting bot: {bot_id}")
        
        # Check if bot exists first
        existing_bot = await bot_service.get_bot(bot_id, session)
        if not existing_bot:
            logger.warning(f"Bot not found for deletion: {bot_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot not found"
            )
        
        # Delete bot
        deleted = await bot_service.delete_bot(bot_id, session)
        
        if deleted:
            # Update data streams since bot was deleted
            await data_stream_manager.update_active_streams(session)
            logger.info(f"Bot deleted successfully: {bot_id}")
        else:
            logger.warning(f"Bot deletion failed: {bot_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete bot"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete bot {bot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/symbols/active", response_model=List[str])
async def get_active_symbols(
    session: AsyncSession = Depends(get_session)
) -> List[str]:
    """
    Get unique symbols from active bots.
    
    Args:
        session: Database session
        
    Returns:
        List[str]: List of unique symbols from active bots
    """
    try:
        logger.debug("Getting active symbols")
        
        symbols = await bot_service.get_active_symbols(session)
        
        logger.debug(f"Retrieved {len(symbols)} active symbols: {symbols}")
        return symbols
        
    except Exception as e:
        logger.error(f"Failed to get active symbols: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/symbols/stats", response_model=List[BotSymbolStats])
async def get_bot_stats_by_symbol(
    session: AsyncSession = Depends(get_session)
) -> List[BotSymbolStats]:
    """
    Get statistics for bots grouped by symbol.
    
    Args:
        session: Database session
        
    Returns:
        List[BotSymbolStats]: Statistics for each symbol
    """
    try:
        logger.debug("Getting bot statistics by symbol")
        
        stats = await bot_service.get_bot_stats_by_symbol(session)
        
        logger.debug(f"Retrieved stats for {len(stats)} symbols")
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get bot stats by symbol: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/symbols/{symbol}", response_model=List[BotPublic])
async def get_bots_by_symbol(
    symbol: str,
    active_only: bool = Query(False, description="Return only active bots"),
    session: AsyncSession = Depends(get_session)
) -> List[BotPublic]:
    """
    Get bots by symbol.
    
    Args:
        symbol: Trading symbol
        active_only: If True, only return active bots
        session: Database session
        
    Returns:
        List[BotPublic]: List of bots for the symbol
    """
    try:
        logger.debug(f"Getting bots for symbol: {symbol} (active_only: {active_only})")
        
        bots = await bot_service.get_bots_by_symbol(symbol, session, active_only)
        
        logger.debug(f"Retrieved {len(bots)} bots for symbol {symbol}")
        return bots
        
    except Exception as e:
        logger.error(f"Failed to get bots by symbol {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.patch("/{bot_id}/status", response_model=BotPublic)
async def update_bot_status(
    bot_id: UUID,
    is_active: bool = Query(..., description="New active status"),
    session: AsyncSession = Depends(get_session)
) -> BotPublic:
    """
    Update bot active status.
    
    Args:
        bot_id: Bot UUID
        is_active: New active status
        session: Database session
        
    Returns:
        BotPublic: Updated bot data
        
    Raises:
        HTTPException: If bot not found
    """
    try:
        logger.info(f"Updating bot status: {bot_id} -> active: {is_active}")
        
        # Update bot status
        updated_bot = await bot_service.set_bot_active_status(bot_id, is_active, session)
        
        if not updated_bot:
            logger.warning(f"Bot not found for status update: {bot_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot not found"
            )
        
        # Update data streams
        await data_stream_manager.update_active_streams(session)
        
        logger.info(f"Bot status updated successfully: {updated_bot.name} - ID: {updated_bot.id}")
        return updated_bot
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update bot status {bot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


