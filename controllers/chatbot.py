import autogen
from autogen import ConversableAgent, register_function
import uuid
from fastapi import APIRouter, HTTPException
import traceback
import asyncio
import os, json, dotenv
from pydantic import BaseModel
from db import Session
from env import env
from services.message import MessageService
from repositories.message import MessageRepository
from models.message import CreateMessagePayload
from tool_call.qdrant_search import search
from tool_call.helper import *
from models.chat import ChatbotRequest
from agent.product_agent import SQLAgent as ProductAgentSQLAgent

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

# LLM Configuration for autogen
llm_openai = [
    {
        "model": env.OPENAI_API_MODEL,
        "api_key": env.OPENAI_API_KEY,
    }
]

system_message_manager = """
Bạn là một trợ lý AI thông minh làm việc cho Navitech
    Bạn sẽ nhận đầu vào câu hỏi của người dùng về một trang web bất kỳ sau đó phân tích và quyết định sử dụng trợ lý nào để trả lời câu hỏi của người dùng
    Nhiệm vụ của bạn là phân tích câu hỏi của người dùng một cách chính xác và đầy đủ nhất có thể
    Hãy trả về mô tả truy vấn dưới dạng JSON:"
        "agent": "ProductAgent"  | "MySelf" | "RetrivalAgent" ,
        "query": String
    Với Agent là tên của trợ lý mà bạn muốn sử dụng để tìm kiếm thông tin
        Trong đó ProductAgent là trợ lý tìm kiếm thông tin sản phẩm
        Trong đó MySelf là trợ lý tìm trả lời câu hỏi bình thường
        Trong đó RetrivalAgent là trợ lý tìm kiếm thông tin chung từ cơ sở dữ liệu


    ** lưu ý: Tuyệt đối chỉ trả về JSON gồm agent sẽ trả lời và query từ người dùng, không thêm bất kỳ giải thích nào khác. **
"""

manager_chat = ConversableAgent(
    name="ManagerChat",
    system_message=system_message_manager,
    llm_config={"config_list": llm_openai},
    human_input_mode= "NEVER",
)


async def get_response(chat_request: ChatbotRequest, agent: ConversableAgent ):
    db_messages = MessageService.get_recent_messages(chat_request.chat_id, limit=10)
    chat_history = []
    for msg in db_messages:
        chat_history.append({
            "role": msg.role,
            "content": msg.content
        })
    chat_history.append({
        "role": "user", 
        "content": chat_request.message
    })
    chat = await agent.a_generate_reply(chat_history)
    print(f"❎❎❎❎❎Parsed JSON response: {chat} (type: {type(chat)})")
    return chat




@router.post("/NoupeClone")
async def ask_chatbot(chat_request: ChatbotRequest):
    # lưu tin nhắn của người dùng vào db
    # message_repository = MessageRepository()
    # message_payload = CreateMessagePayload(
    #     chat_id=chat_request.chat_id,
    #     role="user",
    #     content=chat_request.message
    # )
    # message_repository.create(message_payload)

    # chat_result = await get_response(chat_request, agent=user_proxy)
    # chat_result = await user_proxy.a_generate_reply(
    #     asisistant_agent=noupe_chat,
    #     messages=[
    #         {"role": "user", "content": chat_request.message}
    #     ]
    # ) 


    # Gửi tin nhắn cho manager_chat để phân tích và quyết định sử dụng trợ lý nào
    chat_result = await get_response(chat_request, agent=manager_chat)
    print(chat_result)
    print(f"❎❎❎❎❎Parsed JSON response: {chat_result} (type: {type(chat_result)})")
    # Trích xuất truy vấn JSON từ phản hồi của manager_chat
    extracted_query = extract_json_query(chat_result['content'])
    print(f"❎❎❎❎❎Extracted Json query: {extracted_query} (type: {type(extracted_query)})")
    # Gọi Agent tương ứng để xử lý truy vấn
    agent_response = await call_agen(extracted_query['agent'], chat_request)

    # Xử lý phản hồi từ Agent
    if agent_response:
        print(f"❎❎❎❎❎Agent response: {agent_response} (type: {type(agent_response)})")
    else:
        print("❎❎❎❎❎No response from agent")

    # response_payload = CreateMessagePayload(
    #     chat_id=chat_request.chat_id,
    #     role="assistant",
    #     content=chat_result["content"]
    # )
    # message_repository.create(response_payload)

    #

    return agent_response
