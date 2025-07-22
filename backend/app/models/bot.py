"""
Bot models for SQLModel database integration.
"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship, Index, Column, String, Boolean, DateTime
from pydantic import field_validator, ConfigDict
from uuid import UUID, uuid4
import uuid


class BotBase(SQLModel):
    """Base model for Bot with shared attributes."""
    
    name: str = Field(min_length=1, max_length=100, description="Bot name")
    symbol: str = Field(min_length=1, max_length=20, description="Trading symbol (e.g., BTCUSDT)")
    is_active: bool = Field(default=True, description="Whether the bot is active")
    is_paper_trading: bool = Field(default=True, description="Trading mode: True for paper, False for live")
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.utcnow(), description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.utcnow(), description="Last update timestamp")
    
    model_config = ConfigDict(
        # Use camelCase for API responses
        alias_generator=lambda field_name: ''.join(
            word.capitalize() if i > 0 else word 
            for i, word in enumerate(field_name.split('_'))
        ),
        populate_by_name=True,
        from_attributes=True
    )
    
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
    
    __tablename__ = "bots"
    
    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True,
        description="Unique bot identifier"
    )
    
    # Override datetime fields to be non-optional for database
    created_at: datetime = Field(
        default_factory=lambda: datetime.utcnow(),
        sa_column=Column(DateTime, nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.utcnow(),
        sa_column=Column(DateTime, nullable=False)
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
    
    # Override is_paper_trading to make it optional with default True
    is_paper_trading: Optional[bool] = Field(default=True, description="Trading mode")
    
    # Exclude id, created_at, updated_at from creation
    pass


class BotUpdate(SQLModel):
    """Model for updating a bot with optional fields."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Bot name")
    symbol: Optional[str] = Field(None, min_length=1, max_length=20, description="Trading symbol")
    is_active: Optional[bool] = Field(None, description="Whether the bot is active")
    is_paper_trading: Optional[bool] = Field(default=None, description="Trading mode")
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.utcnow(), description="Update timestamp")
    
    model_config = ConfigDict(
        # Use camelCase for API responses
        alias_generator=lambda field_name: ''.join(
            word.capitalize() if i > 0 else word 
            for i, word in enumerate(field_name.split('_'))
        ),
        populate_by_name=True,
        from_attributes=True
    )
    
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
    model_config = ConfigDict(
        # Use camelCase for API responses
        alias_generator=lambda field_name: ''.join(
            word.capitalize() if i > 0 else word 
            for i, word in enumerate(field_name.split('_'))
        ),
        populate_by_name=True,
        from_attributes=True
    )


class BotList(SQLModel):
    """Model for listing bots with pagination."""
    
    bots: List[BotPublic] = Field(description="List of bots")
    total: int = Field(description="Total number of bots")
    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(default=50, description="Number of bots per page")
    
    model_config = ConfigDict(
        # Use camelCase for API responses
        alias_generator=lambda field_name: ''.join(
            word.capitalize() if i > 0 else word 
            for i, word in enumerate(field_name.split('_'))
        ),
        populate_by_name=True,
        from_attributes=True
    )


class BotSymbolStats(SQLModel):
    """Statistics for bot symbols."""
    
    symbol: str = Field(description="Trading symbol")
    active_count: int = Field(description="Number of active bots for this symbol")
    total_count: int = Field(description="Total number of bots for this symbol")
    
    model_config = ConfigDict(
        # Use camelCase for API responses
        alias_generator=lambda field_name: ''.join(
            word.capitalize() if i > 0 else word 
            for i, word in enumerate(field_name.split('_'))
        ),
        populate_by_name=True,
        from_attributes=True
    )