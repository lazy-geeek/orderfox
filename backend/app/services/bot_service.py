"""
Bot service for managing bot CRUD operations and business logic.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import asyncio
from sqlmodel import Session, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import case
from cachetools import TTLCache

from app.models.bot import Bot, BotCreate, BotUpdate, BotPublic, BotList, BotSymbolStats
from app.core.database import get_session

logger = logging.getLogger(__name__)

class BotService:
    """Service for managing bot operations with caching and business logic."""
    
    def __init__(self):
        """Initialize the bot service with caching."""
        # Cache for bot lists (5-minute TTL)
        self._bot_cache = TTLCache(maxsize=100, ttl=300)
        # Cache for active symbols (5-minute TTL)
        self._symbol_cache = TTLCache(maxsize=50, ttl=300)
        logger.info("BotService initialized with caching (TTL=300s)")
    
    async def create_bot(self, bot_data: BotCreate, session: AsyncSession) -> BotPublic:
        """
        Create a new bot.
        
        Args:
            bot_data: Bot creation data
            session: Database session
            
        Returns:
            BotPublic: Created bot public data
            
        Raises:
            ValueError: If bot data is invalid
        """
        try:
            # Create bot instance
            bot = Bot(
                name=bot_data.name,
                symbol=bot_data.symbol,
                is_active=bot_data.is_active
            )
            
            # Add to session
            session.add(bot)
            await session.commit()
            await session.refresh(bot)
            
            # Clear caches
            self._clear_caches()
            
            logger.info(f"Created bot: {bot.name} ({bot.symbol}) - ID: {bot.id}")
            return BotPublic.model_validate(bot)
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to create bot: {e}")
            raise
    
    async def get_all_bots(self, session: AsyncSession, page: int = 1, page_size: int = 50) -> BotList:
        """
        Get all bots with pagination.
        
        Args:
            session: Database session
            page: Page number (1-based)
            page_size: Number of bots per page
            
        Returns:
            BotList: Paginated list of bots
        """
        try:
            # Create cache key
            cache_key = f"bots_page_{page}_size_{page_size}"
            
            # Check cache
            if cache_key in self._bot_cache:
                logger.debug(f"Cache hit for bot list: {cache_key}")
                return self._bot_cache[cache_key]
            
            # Calculate offset
            offset = (page - 1) * page_size
            
            # Get total count
            count_result = await session.execute(select(func.count(Bot.id)))
            total = count_result.scalar()
            
            # Get bots
            result = await session.execute(
                select(Bot)
                .order_by(Bot.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
            bots = result.scalars().all()
            
            # Convert to public models
            public_bots = [BotPublic.model_validate(bot) for bot in bots]
            
            # Create response
            bot_list = BotList(
                bots=public_bots,
                total=total,
                page=page,
                page_size=page_size
            )
            
            # Cache the result
            self._bot_cache[cache_key] = bot_list
            
            logger.debug(f"Retrieved {len(public_bots)} bots (page {page}, total {total})")
            return bot_list
            
        except Exception as e:
            logger.error(f"Failed to get bots: {e}")
            raise
    
    async def get_bot(self, bot_id: UUID, session: AsyncSession) -> Optional[BotPublic]:
        """
        Get a specific bot by ID.
        
        Args:
            bot_id: Bot UUID
            session: Database session
            
        Returns:
            Optional[BotPublic]: Bot data if found, None otherwise
        """
        try:
            # Create cache key
            cache_key = f"bot_{bot_id}"
            
            # Check cache
            if cache_key in self._bot_cache:
                logger.debug(f"Cache hit for bot: {bot_id}")
                return self._bot_cache[cache_key]
            
            # Query database
            result = await session.execute(
                select(Bot).where(Bot.id == bot_id)
            )
            bot = result.scalar_one_or_none()
            
            if not bot:
                logger.warning(f"Bot not found: {bot_id}")
                return None
            
            # Convert to public model
            public_bot = BotPublic.model_validate(bot)
            
            # Cache the result
            self._bot_cache[cache_key] = public_bot
            
            logger.debug(f"Retrieved bot: {bot.name} ({bot.symbol})")
            return public_bot
            
        except Exception as e:
            logger.error(f"Failed to get bot {bot_id}: {e}")
            raise
    
    async def update_bot(self, bot_id: UUID, bot_data: BotUpdate, session: AsyncSession) -> Optional[BotPublic]:
        """
        Update a bot.
        
        Args:
            bot_id: Bot UUID
            bot_data: Bot update data
            session: Database session
            
        Returns:
            Optional[BotPublic]: Updated bot data if found, None otherwise
        """
        try:
            # Get existing bot
            result = await session.execute(
                select(Bot).where(Bot.id == bot_id)
            )
            bot = result.scalar_one_or_none()
            
            if not bot:
                logger.warning(f"Bot not found for update: {bot_id}")
                return None
            
            # Update fields
            update_data = bot_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                if field != 'updated_at':  # Handle updated_at separately
                    setattr(bot, field, value)
            
            # Ensure timestamp is different (add small delay)
            await asyncio.sleep(0.001)
            # Always update the timestamp (timezone-naive)
            bot.updated_at = datetime.utcnow()
            
            # Commit changes
            await session.commit()
            await session.refresh(bot)
            
            # Clear caches
            self._clear_caches()
            
            logger.info(f"Updated bot: {bot.name} ({bot.symbol}) - ID: {bot.id}")
            return BotPublic.model_validate(bot)
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to update bot {bot_id}: {e}")
            raise
    
    async def delete_bot(self, bot_id: UUID, session: AsyncSession) -> bool:
        """
        Delete a bot.
        
        Args:
            bot_id: Bot UUID
            session: Database session
            
        Returns:
            bool: True if deleted, False if not found
        """
        try:
            # Get existing bot
            result = await session.execute(
                select(Bot).where(Bot.id == bot_id)
            )
            bot = result.scalar_one_or_none()
            
            if not bot:
                logger.warning(f"Bot not found for deletion: {bot_id}")
                return False
            
            # Delete bot
            await session.delete(bot)
            await session.commit()
            
            # Clear caches
            self._clear_caches()
            
            logger.info(f"Deleted bot: {bot.name} ({bot.symbol}) - ID: {bot.id}")
            return True
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to delete bot {bot_id}: {e}")
            raise
    
    async def get_active_symbols(self, session: AsyncSession) -> List[str]:
        """
        Get unique symbols from active bots.
        
        Args:
            session: Database session
            
        Returns:
            List[str]: List of unique symbols from active bots
        """
        try:
            # Check cache
            cache_key = "active_symbols"
            if cache_key in self._symbol_cache:
                logger.debug("Cache hit for active symbols")
                return self._symbol_cache[cache_key]
            
            # Query database
            result = await session.execute(
                select(Bot.symbol)
                .where(Bot.is_active == True)
                .distinct()
            )
            symbols = [row[0] for row in result.fetchall()]
            
            # Cache the result
            self._symbol_cache[cache_key] = symbols
            
            logger.debug(f"Retrieved {len(symbols)} active symbols: {symbols}")
            return symbols
            
        except Exception as e:
            logger.error(f"Failed to get active symbols: {e}")
            raise
    
    async def get_bot_stats_by_symbol(self, session: AsyncSession) -> List[BotSymbolStats]:
        """
        Get statistics for bots grouped by symbol.
        
        Args:
            session: Database session
            
        Returns:
            List[BotSymbolStats]: Statistics for each symbol
        """
        try:
            # Query database for symbol statistics  
            result = await session.execute(
                select(
                    Bot.symbol,
                    func.count(Bot.id).label('total_count'),
                    func.sum(
                        case(
                            (Bot.is_active == True, 1),
                            else_=0
                        )
                    ).label('active_count')
                )
                .group_by(Bot.symbol)
                .order_by(Bot.symbol)
            )
            
            stats = []
            for row in result:
                stat = BotSymbolStats(
                    symbol=row.symbol,
                    total_count=row.total_count,
                    active_count=row.active_count or 0
                )
                stats.append(stat)
            
            logger.debug(f"Retrieved stats for {len(stats)} symbols")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get bot stats by symbol: {e}")
            raise
    
    async def get_bots_by_symbol(self, symbol: str, session: AsyncSession, active_only: bool = False) -> List[BotPublic]:
        """
        Get bots by symbol.
        
        Args:
            symbol: Trading symbol
            session: Database session
            active_only: If True, only return active bots
            
        Returns:
            List[BotPublic]: List of bots for the symbol
        """
        try:
            # Build query
            query = select(Bot).where(Bot.symbol == symbol)
            if active_only:
                query = query.where(Bot.is_active == True)
            
            # Execute query
            result = await session.execute(query.order_by(Bot.created_at.desc()))
            bots = result.scalars().all()
            
            # Convert to public models
            public_bots = [BotPublic.model_validate(bot) for bot in bots]
            
            logger.debug(f"Retrieved {len(public_bots)} bots for symbol {symbol} (active_only={active_only})")
            return public_bots
            
        except Exception as e:
            logger.error(f"Failed to get bots by symbol {symbol}: {e}")
            raise
    
    async def set_bot_active_status(self, bot_id: UUID, is_active: bool, session: AsyncSession) -> Optional[BotPublic]:
        """
        Set bot active status.
        
        Args:
            bot_id: Bot UUID
            is_active: New active status
            session: Database session
            
        Returns:
            Optional[BotPublic]: Updated bot data if found, None otherwise
        """
        try:
            # Get existing bot
            result = await session.execute(
                select(Bot).where(Bot.id == bot_id)
            )
            bot = result.scalar_one_or_none()
            
            if not bot:
                logger.warning(f"Bot not found for status update: {bot_id}")
                return None
            
            # Update status
            bot.is_active = is_active
            # Ensure timestamp is different (add small delay)
            await asyncio.sleep(0.001)
            bot.updated_at = datetime.utcnow()
            
            # Commit changes
            await session.commit()
            await session.refresh(bot)
            
            # Clear caches
            self._clear_caches()
            
            status_text = "activated" if is_active else "deactivated"
            logger.info(f"Bot {status_text}: {bot.name} ({bot.symbol}) - ID: {bot.id}")
            return BotPublic.model_validate(bot)
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to update bot status {bot_id}: {e}")
            raise
    
    def _clear_caches(self):
        """Clear all caches."""
        self._bot_cache.clear()
        self._symbol_cache.clear()
        logger.debug("Cleared bot service caches")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict[str, Any]: Cache statistics
        """
        return {
            "bot_cache_size": len(self._bot_cache),
            "bot_cache_maxsize": self._bot_cache.maxsize,
            "bot_cache_ttl": self._bot_cache.ttl,
            "symbol_cache_size": len(self._symbol_cache),
            "symbol_cache_maxsize": self._symbol_cache.maxsize,
            "symbol_cache_ttl": self._symbol_cache.ttl
        }

# Create global instance
bot_service = BotService()