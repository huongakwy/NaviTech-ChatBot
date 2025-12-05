"""AI Personality Models - Database and Pydantic"""

from datetime import datetime
from typing import Optional
from models.base import Base, TimestampMixin
from sqlalchemy import String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel, ConfigDict


class AIPersonalityTable(Base, TimestampMixin):
    """SQLAlchemy ORM model for personality_types table"""
    __tablename__ = "personality_types"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    company_name: Mapped[str] = mapped_column(String(200), nullable=True, default="NAVITECH")
    agent_name: Mapped[str] = mapped_column(String(200), nullable=True, default="trợ lý AI")
    
    model_config = ConfigDict(from_attributes=True)


class AIPersonalityModel(BaseModel):
    """Pydantic model for API responses"""
    id: int
    name: str
    description: str
    company_name: Optional[str] = "NAVITECH"
    agent_name: Optional[str] = "trợ lý AI"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class AIPersonalityCreateModel(BaseModel):
    """Pydantic model for creating new personalities"""
    name: str
    description: str
    company_name: Optional[str] = "NAVITECH"
    agent_name: Optional[str] = "trợ lý AI"
    
    model_config = ConfigDict(from_attributes=True)


class AIPersonalityUpdateModel(BaseModel):
    """Pydantic model for updating personalities"""
    name: Optional[str] = None
    description: Optional[str] = None
    company_name: Optional[str] = None
    agent_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
