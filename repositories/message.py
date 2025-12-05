import uuid
from db import Session
from models.message import Message, CreateMessagePayload, UpdateMessagePayload, MessageModel, MessageHistoryModel


class MessageRepository:
    @staticmethod
    def create(payload: CreateMessagePayload) -> MessageModel:
        with Session() as session:
            message = Message(**payload.model_dump())
            session.add(message)
            session.commit()
            session.refresh(message)
            return MessageModel.model_validate(message)
        
    @staticmethod
    def get_one(message_id: uuid.UUID) -> MessageModel:
        with Session() as session:
            message = session.get(Message, message_id)
            if not message:
                raise ValueError(f"Message with ID {message_id} not found")
            return MessageModel.model_validate(message)

    @staticmethod
    def update(message_id: uuid.UUID, data: UpdateMessagePayload) -> MessageModel:
        with Session() as session:
            message = session.get(Message, message_id)
            if not message:
                raise ValueError(f"Message with ID {message_id} not found")

            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(message, field, value)

            session.commit()
            session.refresh(message)
            return MessageModel.model_validate(message)

    @staticmethod
    def delete(message_id: uuid.UUID):
        with Session() as session:
            message = session.get(Message, message_id)
            if not message:
                raise ValueError(f"Message with ID {message_id} not found")

            session.delete(message)
            session.commit()

    
    @staticmethod
    def get_recent_messages(chat_id: uuid.UUID, limit: int = 5):
        with Session() as session:
            rs =  (
                session.query(Message)
                .filter(Message.chat_id == chat_id)
                .order_by(Message.created_at.desc())
                .limit(limit)
                .all()
            )
            revert_rs = rs[::-1]
            return [MessageModel.model_validate(message) for message in revert_rs]
        
        