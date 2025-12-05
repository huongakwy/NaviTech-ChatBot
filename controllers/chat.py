from fastapi import APIRouter, HTTPException
from models.chat import CreateChatPayload, UpdateChatPayload, ChatModel
from services.chat import ChatService
import uuid

router = APIRouter(prefix="/chats", tags=["Chats"])

@router.post("", response_model=ChatModel)
def create_chat(payload: CreateChatPayload):
    return ChatService.create_chat(payload)


@router.get("", response_model=ChatModel)
def get_chat(chat_id: uuid.UUID):
    chat = ChatService.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.put("", response_model=ChatModel)
def update_chat(chat_id: uuid.UUID, payload: UpdateChatPayload):
    chat = ChatService.update_chat(chat_id, payload)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.delete("")
def delete_chat(chat_id: uuid.UUID):
    ChatService.delete_chat(chat_id)
    return {"message": "Chat deleted successfully"}

@router.get("/user/{user_id}", response_model=list[ChatModel])
def get_all_chats_by_user(user_id: uuid.UUID):
    chats = ChatService.get_all_chats_by_user(user_id)
    if not chats:
        raise HTTPException(status_code=404, detail="No chats found for this user")
    return chats


