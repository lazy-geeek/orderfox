"""
Bot models for SQLModel database integration.
"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import SQLModel, Field, Index
from pydantic import field_validator, ConfigDict
from pydantic.alias_generators import to_camel
from uuid import UUID, uuid4


class BotBase(SQLModel):
    """Base model for Bot with shared attributes."""
    
    model_config = ConfigDict(  # type: ignore
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    
    name: str = Field(min_length=1, max_length=100, description="Bot name")
    symbol: str = Field(min_length=1, max_length=20, description="Trading symbol (e.g., BTCUSDT)")
    is_active: bool = Field(default=True, description="Whether the bot is active")
    is_paper_trading: bool = Field(default=True, description="Trading mode: True for paper, False for live")
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None), description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None), description="Last update timestamp")
    
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v):
        """Validate symbol format."""
        if not v:
            raise ValueError("Symbol cannot be empty")
        # Convert to uppercase
        return v.upper()
    
    @field_validator('name') 
    @classmethod
    def validate_name(cls, v):
        """Validate bot name."""
        if not v or not v.strip():
            raise ValueError("Bot name cannot be empty")
        return v.strip()


class Bot(BotBase, table=True):
    """Bot table model for database storage."""
    
    __tablename__ = "bots"  # type: ignore
    
    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True,
        description="Unique bot identifier"
    )
    
    # Add indexes for performance
    __table_args__ = (
        Index('ix_bots_symbol', 'symbol'),
        Index('ix_bots_is_active', 'is_active'),
        Index('ix_bots_symbol_is_active', 'symbol', 'is_active'),
        Index('ix_bots_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Bot(id={self.id}, name={self.name}, symbol={self.symbol}, is_active={self.is_active}, is_paper_trading={self.is_paper_trading})>"


class BotCreate(BotBase):
    """Model for creating a new bot."""
    
    # Exclude id, created_at, updated_at from creation
    pass


class BotUpdate(SQLModel):
    """Model for updating a bot with optional fields."""
    
    model_config = ConfigDict(  # type: ignore
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Bot name")
    symbol: Optional[str] = Field(None, min_length=1, max_length=20, description="Trading symbol")
    is_active: Optional[bool] = Field(None, description="Whether the bot is active")
    is_paper_trading: Optional[bool] = Field(default=None, description="Trading mode")
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None), description="Update timestamp")
    
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v):
        """Validate symbol format."""
        if v is not None:
            if not v:
                raise ValueError("Symbol cannot be empty")
            return v.upper()
        return v
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate bot name."""
        if v is not None:
            if not v or not v.strip():
                raise ValueError("Bot name cannot be empty")
            return v.strip()
        return v


class BotPublic(BotBase):
    """Public model for bot responses."""
    
    id: UUID = Field(description="Unique bot identifier")
    
    # Include all base fields with camelCase aliases


class BotList(SQLModel):
    """Model for listing bots with pagination."""
    
    model_config = ConfigDict(  # type: ignore
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    
    bots: List[BotPublic] = Field(description="List of bots")
    total: int = Field(description="Total number of bots")
    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(default=50, description="Number of bots per page")
    


class BotSymbolStats(SQLModel):
    """Statistics for bot symbols."""
    
    model_config = ConfigDict(  # type: ignore
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    
    symbol: str = Field(description="Trading symbol")
    active_count: int = Field(description="Number of active bots for this symbol")
    total_count: int = Field(description="Total number of bots for this symbol")
