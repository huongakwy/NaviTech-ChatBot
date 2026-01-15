"""
FAQ Model - Quản lý câu hỏi thường gặp (Frequently Asked Questions)

Table: faqs
- Lưu trữ FAQs cho từng user/company
- Được index trong Qdrant để semantic search
"""

from datetime import datetime
from typing import Optional
import uuid
from models.base import Base, TimestampMixin
from sqlalchemy import UUID, String, Text, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel, ConfigDict


class FAQTable(Base, TimestampMixin):
    """SQLAlchemy model cho FAQ table"""
    __tablename__ = "faqs"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True  # Index để filter nhanh by user
    )
    question: Mapped[str] = mapped_column(
        Text, 
        nullable=False,
        comment="Câu hỏi FAQ"
    )
    answer: Mapped[str] = mapped_column(
        Text, 
        nullable=False,
        comment="Câu trả lời"
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(100), 
        nullable=True,
        index=True,
        comment="Danh mục: chinh-sach, bao-hanh, thanh-toan, giao-hang, etc."
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Độ ưu tiên (cao hơn = quan trọng hơn)"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="FAQ có đang active không"
    )
    
    model_config = ConfigDict(from_attributes=True)


class FAQModel(BaseModel):
    """Pydantic model cho FAQ response"""
    id: uuid.UUID
    user_id: uuid.UUID
    question: str
    answer: str
    category: Optional[str] = None
    priority: int = 0
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class FAQCreateModel(BaseModel):
    """Pydantic model để tạo FAQ mới"""
    user_id: uuid.UUID
    question: str
    answer: str
    category: Optional[str] = None
    priority: int = 0
    is_active: bool = True
    
    model_config = ConfigDict(from_attributes=True)


class FAQUpdateModel(BaseModel):
    """Pydantic model để update FAQ"""
    question: Optional[str] = None
    answer: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    
    model_config = ConfigDict(from_attributes=True)


class FAQSearchResult(BaseModel):
    """Result khi search FAQ với score"""
    faq: FAQModel
    score: float
    matched: bool  # True nếu score >= threshold
    
    model_config = ConfigDict(from_attributes=True)
