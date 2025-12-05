from typing import Optional
from datetime import datetime
from sqlalchemy import TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from pydantic import BaseModel
import uuid
import sqlalchemy as sa
from models.chat import Chat

# SQLAlchemy base class
class Base(DeclarativeBase):
    pass

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    chat_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey(Chat.id), nullable=False)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    role: Mapped[str] = mapped_column(sa.Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)

# Payload khi tạo tin nhắn mới
class CreateMessagePayload(BaseModel):
    chat_id: uuid.UUID
    content: str
    role: str

# Payload khi cập nhật tin nhắn
class UpdateMessagePayload(BaseModel):
    content: Optional[str]
    role: Optional[str]

# Model phản hồi trả về từ API
class MessageModel(BaseModel):
    content: str
    role: str 


    class Config:
        from_attributes = True

class MessageHistoryModel(BaseModel):
    role: str
    content: str
    