import json
import re
from autogen import ConversableAgent
from env import env
from models.chat import ChatbotRequest
from fastapi import APIRouter
from models.message import MessageModel, CreateMessagePayload
from services.message import MessageService

llm_google = [
    {
        "model": "gemini-2.5-flash",
        "api_key": env.GEMINI_API_KEY,
        "api_type": "google"
    }
]

llm_anthrophic = [
    {
        "model": "claude-3-5-sonnet-20241022",
        "api_key": env.CLAUDE_API_KEY,
        "api_type": "anthropic"
    }
]
router = APIRouter(prefix="/chatbot", tags=["Compose History Agent"])

        
def _create_compose_history_agent() -> ConversableAgent:
    system_message = r"""Bạn là một chuyên gia tổng hợp lịch sử trò chuyện.
    Nhiệm vụ của bạn là phân tích lịch sử trò chuyện giữa người dùng và trợ lý AI, sau đó tổng hợp các thông tin quan trọng nhất từ cuộc trò chuyện đó.
    Hãy trả về 1 Json duy nhất với 2 trường:
    {
        "summary": "Tóm tắt ngắn gọn các điểm chính từ cuộc trò chuyện.",
        "key_points": ["Danh sách các điểm quan trọng được thảo luận trong cuộc trò chuyện."]
    }


    """
    return ConversableAgent(
        name="compose_history_expert",
        system_message=system_message,
        llm_config={"config_list": llm_anthrophic},
        human_input_mode="NEVER"
    )
        
@router.post("/compose_history", response_model=dict)
async def compose_history_endpoint(request: ChatbotRequest):
    """
    Tổng hợp lịch sử trò chuyện thành summary và key points
    Không lưu message - để pipeline xử lý
    """
    messageservice = MessageService()
    
    # Lấy lịch sử (không bao gồm message hiện tại)
    history = messageservice.get_recent_messages(request.chat_id, limit=10)
    
    if not history or len(history) == 0:
        return {
            "summary": "Đây là cuộc trò chuyện đầu tiên",
            "key_points": []
        }
    
    normalized_history = []
    for msg in history:
        if isinstance(msg, MessageModel):
            normalized_history.append(msg.dict())
        elif isinstance(msg, dict):
            normalized_history.append(msg)
    
    print("🥩 Normalized History:", normalized_history)
    
    agent = _create_compose_history_agent()
    response = await agent.a_generate_reply(normalized_history)
    print("📊 Compose History Response:", response)
    
    # Parse JSON response
    json_str = re.sub(r"^```json\n|\n```$", "", response["content"].strip())
    print("DEBUG: json_str =", repr(json_str))
    
    try:
        data = json.loads(json_str)
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return data
    except json.JSONDecodeError:
        return {
            "summary": "Không thể tổng hợp lịch sử",
            "key_points": []
        }


