from fastapi import APIRouter, HTTPException, status
from models.message import CreateMessagePayload, UpdateMessagePayload, MessageModel, MessageHistoryModel
from services.message import MessageService
import uuid

router = APIRouter(prefix="/messages", tags=["Messages"])


@router.post("", response_model=MessageModel, status_code=status.HTTP_201_CREATED)
def create_message(payload: CreateMessagePayload):
    return MessageService.create_message(payload)


@router.get("", response_model=MessageModel)
def get_message(message_id: uuid.UUID):
    try:
        message = MessageService.get_message(message_id)
        return message
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")


@router.put("", response_model=MessageModel)
def update_message(message_id: uuid.UUID, payload: UpdateMessagePayload):
    try:
        message = MessageService.update_message(message_id, payload)
        return message
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(message_id: uuid.UUID):
    try:
        MessageService.delete_message(message_id)
        return {"message": "Message deleted successfully"}
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

@router.get("/recent", response_model=list[MessageHistoryModel])
def get_recent_messages(chat_id: uuid.UUID, limit: int = 20):
    try:
        messages = MessageService.get_recent_messages(chat_id, limit)
        return messages
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Messages not found")
