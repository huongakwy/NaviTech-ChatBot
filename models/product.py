
from typing import List, Optional
from datetime import datetime
import uuid
from sqlalchemy import ARRAY, String, Text, TIMESTAMP, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from pydantic import BaseModel
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as pgUUID

class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    website_id: Mapped[int] = mapped_column(Integer, nullable=False)
    website_name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=True)
    price: Mapped[float] = mapped_column(Numeric(20, 2), nullable=True)
    original_price: Mapped[float] = mapped_column(Numeric(20, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), server_default='VND', nullable=True)
    sku: Mapped[str] = mapped_column(String(100), nullable=True)
    brand: Mapped[str] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    availability: Mapped[str] = mapped_column(String(100), nullable=True)
    images: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(pgUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)


class ProductCreate(BaseModel):
    website_name: str
    website_id: int
    url: str
    title: Optional[str] = None
    price: Optional[float] = None
    original_price: Optional[float] = None
    currency: Optional[str] = 'VND'
    sku: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    availability: Optional[str] = None
    images: Optional[List[str]] = None
    user_id: Optional[uuid.UUID] = None


class ProductUpdatePayload(BaseModel):
    website_name: Optional[str] = None
    website_id: Optional[int] = None
    url: Optional[str] = None
    title: Optional[str] = None
    price: Optional[float] = None
    original_price: Optional[float] = None
    currency: Optional[str] = None
    sku: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    availability: Optional[str] = None
    images: Optional[List[str]] = None


class ProductModel(BaseModel):

    id: uuid.UUID
    website_name: str
    url: str
    title: Optional[str]
    price: Optional[float]
    original_price: Optional[float]
    currency: str
    sku: Optional[str]
    brand: Optional[str]
    category: Optional[str]
    description: Optional[str]
    availability: Optional[str]
    images: Optional[List[str]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
