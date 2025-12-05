#lib
from datetime import datetime
from typing import Optional
import uuid
from models.base import Base, TimestampMixin
from sqlalchemy import UUID, String, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pydantic import BaseModel, ConfigDict

class UserTable(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    website_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ai_personality_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("personality_types.id", ondelete="SET NULL"), nullable=True)
    
    # Relationship to personality
    ai_personality: Mapped[Optional["AIPersonalityTable"]] = relationship("AIPersonalityTable", lazy="joined")
    
    model_config = ConfigDict(from_attributes=True)

class UserModel(BaseModel):
    id: uuid.UUID
    full_name: str
    phone_number: Optional[str]
    email: str
    website_name: Optional[str]
    ai_personality_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)
    
class UserCreateModel(BaseModel):
    id : uuid.UUID
    full_name: str
    email: str
    model_config = ConfigDict(from_attributes=True)
    