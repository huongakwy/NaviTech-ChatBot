import uuid
from models.chat import CreateChatPayload, UpdateChatPayload, ChatModel
from repositories.chat import ChatRepository


class ChatService:
    @staticmethod
    def create_chat(payload: CreateChatPayload) -> ChatModel:
        return ChatRepository.create(payload)

    @staticmethod
    def get_chat(chat_id: uuid.UUID) -> ChatModel:
        return ChatRepository.get_one(chat_id)

    @staticmethod
    def update_chat(chat_id: uuid.UUID, data: UpdateChatPayload) -> ChatModel:
        return ChatRepository.update(chat_id, data)

    @staticmethod
    def delete_chat(chat_id: uuid.UUID) -> None:
        return ChatRepository.delete(chat_id)

    @staticmethod
    def get_all_chats_by_user(user_id: uuid.UUID) -> list[ChatModel]:
        return ChatRepository.get_all_chat_by_user(user_id)
