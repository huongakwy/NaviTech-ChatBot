import uuid
from models.message import CreateMessagePayload, UpdateMessagePayload, MessageModel, MessageHistoryModel
from repositories.message import MessageRepository


class MessageService:
    @staticmethod
    def create_message(payload: CreateMessagePayload) -> MessageModel:
        return MessageRepository.create(payload)

    @staticmethod
    def get_message(message_id: uuid.UUID) -> MessageModel:
        return MessageRepository.get_one(message_id)

    @staticmethod
    def update_message(message_id: uuid.UUID, data: UpdateMessagePayload) -> MessageModel:
        return MessageRepository.update(message_id, data)

    @staticmethod
    def delete_message(message_id: uuid.UUID) -> None:
        return MessageRepository.delete(message_id)

    @staticmethod
    def get_recent_messages(chat_id: uuid.UUID, limit: int = 20) -> list[MessageHistoryModel]:
        return MessageRepository.get_recent_messages(chat_id, limit)