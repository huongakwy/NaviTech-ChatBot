from typing import Optional
from datetime import datetime
from sqlalchemy import Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from pydantic import BaseModel
import uuid
import sqlalchemy as sa
from models.user import UserTable


class Base(DeclarativeBase):
    pass


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey(UserTable.id), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)


class CreateChatPayload(BaseModel):
    user_id: uuid.UUID
    title: str 


class UpdateChatPayload(BaseModel):
    user_id: Optional[uuid.UUID] = None
    title: Optional[str] = None 


class ChatModel(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatbotRequest(BaseModel):
    chat_id: uuid.UUID
    message: str
    user_id: Optional[uuid.UUID] = None  # Thêm user_id để hỗ trợ RecommendationAgent