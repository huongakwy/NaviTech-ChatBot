from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from agent.compose_history import compose_history_endpoint
from agent.product_agent import product_agent
from agent.myself import myself_endpoint
from agent.recomendation_agent import chatbot_endpoint
from agent.personalization_agent import PersonalizationAgent
from agent.document_retrieval_agent import DocumentRetrievalAgent
from agent.personality_agent import PersonalityAgent
from models.chat import ChatbotRequest
from models.message import CreateMessagePayload
from services.message import MessageService
from services.user import UserService
from services.ai_personality import AIPersonalityService
from tool_call.helper import extract_json_query, call_agen
from autogen import ConversableAgent
from env import env
from db import get_db
from sqlalchemy.orm import Session
import json
import re
import uuid

router = APIRouter(prefix="/chatbots", tags=["Pipeline All Agent"])

# Manager Agent để routing
llm_anthrophic = [
    {
        "model": "claude-3-5-sonnet-20241022",
        "api_key": env.CLAUDE_API_KEY,
        "api_type": "anthropic"
    }
]

system_message_manager = """
Bạn là một trợ lý AI thông minh làm việc cho Navitech.
Bạn sẽ nhận đầu vào câu hỏi của người dùng và lịch sử trò chuyện (nếu có).
Nhiệm vụ của bạn là phân tích câu hỏi và quyết định agent nào phù hợp nhất.

Hãy trả về JSON với cấu trúc:
{
    "agent": "ProductAgent" | "MySelf" | "RecommendationAgent" | "PersonalizationAgent" | "DocumentRetrievalAgent",
    "query": "câu hỏi gốc của người dùng"
}

PHÂN LOẠI AGENT:

- **ProductAgent**: Tìm kiếm sản phẩm theo tiêu chí cụ thể (giá, thương hiệu, tên, specs)
  Ví dụ: "Tìm laptop Dell", "Có điện thoại dưới 10 triệu không?"

- **RecommendationAgent**: Gợi ý sản phẩm dựa trên mô tả/ngữ cảnh chung
  Ví dụ: "Laptop cho sinh viên", "Điện thoại chơi game tốt"

- **PersonalizationAgent**: Câu hỏi follow-up về sản phẩm đã tìm được hoặc so sánh
  Ví dụ: "Cái nào tốt hơn?", "Phù hợp cho tôi nhất?", "Bạn nghĩ sao về X?"
  **CHÚ Ý**: Nếu câu hỏi có "cái nào", "ai nên", "phù hợp cho" → PersonalizationAgent

- **DocumentRetrievalAgent**: Câu hỏi về chính sách, hướng dẫn, FAQs từ knowledge base
  Ví dụ: "Chính sách đổi trả?", "Hướng dẫn sử dụng?", "Điều khoản bảo hành?"
  **CHÚ Ý**: Keywords như "chính sách", "quy định", "hướng dẫn", "điều khoản", "bảo hành", "FAQ"

- **MySelf**: Câu hỏi về NAVITECH hoặc câu hỏi chung không liên quan sản phẩm/documents

** Chỉ trả về JSON, không giải thích thêm. **
"""

manager_agent = ConversableAgent(
    name="ManagerChat",
    system_message=system_message_manager,
    llm_config={"config_list": llm_anthrophic},
    human_input_mode="NEVER",
)


@router.post("/full_pipeline", response_model=str)
async def pipeline_chatbot(
    query: str,
    chat_id: uuid.UUID = Query(..., description="Chat session ID"),
    user_id: uuid.UUID = Query(..., description="User ID")
):
    """
    Pipeline đầy đủ với history context, personality, và routing thông minh
    
    Args:
        query: Câu hỏi của người dùng
        chat_id: ID của chat session (must be valid UUID)
        user_id: ID của người dùng (must be valid UUID)
    
    Features:
        - Personality support: Sử dụng personality của user nếu có
        - History context: Nhớ lịch sử trò chuyện
        - Smart routing: Chọn agent phù hợp
    """
    try:
        chat_uuid = chat_id
        user_uuid = user_id
        messageservice = MessageService()
        
        # [0] LẤY PERSONALITY CỦA USER
        print(f"👤 Loading user personality...")
        user_personality = None
        user_personality_name = None
        company_name = "NAVITECH"
        agent_name = "trợ lý AI"
        
        try:
            from db import SessionLocal
            session = SessionLocal()
            
            # Lấy user
            from models.user import UserTable
            user = session.query(UserTable).filter(UserTable.id == user_id).first()
            
            if user and user.ai_personality_id:
                # Lấy personality details
                personality = session.query(AIPersonalityService).filter(
                    AIPersonalityService.id == user.ai_personality_id
                ).first()
                
                if personality:
                    user_personality = PersonalityAgent(
                        company_name=personality.company_name or "NAVITECH",
                        agent_name=personality.agent_name or "trợ lý AI"
                    )
                    user_personality_name = personality.name
                    company_name = personality.company_name or "NAVITECH"
                    agent_name = personality.agent_name or "trợ lý AI"
                    print(f"✅ Personality loaded: {user_personality_name} ({agent_name})")
            else:
                print(f"ℹ️  No personality set for user, using default")
        except Exception as e:
            print(f"⚠️  Error loading personality: {e}")
            pass
        finally:
            if 'session' in locals():
                session.close()
        
        # [1] Lưu tin nhắn người dùng vào DB
        user_message_payload = CreateMessagePayload(
            chat_id=chat_id, 
            role="user", 
            content=query
        )
        messageservice.create_message(user_message_payload)
        print(f"✅ Saved user message to DB")
        
        # [2] Lấy lịch sử trò chuyện gần đây
        history = messageservice.get_recent_messages(chat_id, limit=10)
        history_context = ""
        
        if len(history) > 1:
            history_summary = []
            for msg in history[:-1]:
                role_label = "Người dùng" if msg.role == "user" else "Trợ lý"
                history_summary.append(f"{role_label}: {msg.content}")
            
            history_context = "\n".join(history_summary[-5:])
            print(f"📜 History context: {history_context[:200]}...")
        
        # [3] Tạo enhanced query với context
        if history_context:
            enhanced_prompt = f"""
Lịch sử trò chuyện gần đây:
{history_context}

Câu hỏi hiện tại: {query}

Hãy phân tích và quyết định agent phù hợp.
"""
        else:
            enhanced_prompt = f"Câu hỏi: {query}"
        
        # [4] Manager Agent quyết định routing
        manager_response = await manager_agent.a_generate_reply(
            messages=[{"role": "user", "content": enhanced_prompt}]
        )
        print(f"🎯 Manager decision: {manager_response}")
        
        # [5] Extract routing decision
        routing_info = extract_json_query(manager_response['content'])
        agent_name = routing_info.get('agent', 'MySelf')
        agent_query = routing_info.get('query', query)
        
        print(f"🤖 Selected agent: {agent_name}")
        print(f"📝 Agent query: {agent_query}")
        
        # [6] Execute specialized agent
        request = ChatbotRequest(chat_id=chat_id, message=agent_query)
        
        if agent_name == "ProductAgent":
            chatbot_response = await product_agent(agent_query)
            
            # ProductAgent trả về dict, lấy response
            if isinstance(chatbot_response, dict):
                response_text = chatbot_response.get('response', str(chatbot_response))
                products = chatbot_response.get('products', [])
                
                # ✨ Nếu không tìm được sản phẩm nào, chuyển sang RecommendationAgent
                if not products or len(products) == 0:
                    print(f"⚠️ ProductAgent không tìm thấy sản phẩm, chuyển sang RecommendationAgent")
                    
                    try:
                        # Gọi RecommendationAgent để tìm sản phẩm tương tự
                        recommendation_response = await chatbot_endpoint(request, user_id=user_id)
                        
                        # Tạo message thông báo + gợi ý
                        response_text = f"""{recommendation_response}"""
                        
                        print(f"✅ Fallback to RecommendationAgent successful")
                    except Exception as fallback_error:
                        print(f"❌ Fallback to RecommendationAgent failed: {str(fallback_error)}")
                        response_text = """Rất tiếc, hiện tại chúng tôi không có sản phẩm bạn đang tìm kiếm.

Bạn có thể:
- Mô tả chi tiết hơn về sản phẩm bạn cần
- Thử tìm kiếm với từ khóa khác
- Xem các danh mục sản phẩm của chúng tôi

Tôi luôn sẵn sàng hỗ trợ bạn! 💪"""
            else:
                response_text = str(chatbot_response)
                
        elif agent_name == "RecommendationAgent":
            chatbot_response = await chatbot_endpoint(request, user_id=user_id)
            response_text = str(chatbot_response)
        
        elif agent_name == "PersonalizationAgent":
            # PersonalizationAgent cần context từ lịch sử
            print(f"🎨 PersonalizationAgent - Analyzing with context")
            
            # Extract previous products from history if available
            previous_products = []
            for msg in history[-5:]:  # Last 5 messages
                if msg.role == "assistant" and ("VND" in msg.content or "sản phẩm" in msg.content):
                    # Try to extract product info from previous response
                    # This is a simple extraction, có thể improve bằng regex
                    pass  # TODO: Extract products properly
            
            # Convert history to dict format
            history_dicts = []
            for msg in history[-5:]:
                history_dicts.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            personalization_agent = PersonalizationAgent()
            chatbot_response = await personalization_agent.process_query(
                query=agent_query,
                previous_products=previous_products,
                conversation_history=history_dicts
            )
            response_text = str(chatbot_response)
        
        elif agent_name == "DocumentRetrievalAgent":
            # DocumentRetrievalAgent tìm kiếm trong knowledge base
            print(f"📚 DocumentRetrievalAgent - Searching knowledge base")
            
            document_agent = DocumentRetrievalAgent()
            chatbot_response = await document_agent.process_query(
                query=agent_query,
                user_id=user_id,
                top_k=5  # Retrieve top 5 relevant chunks
            )
            response_text = str(chatbot_response)
            
        else:  # MySelf
            chatbot_response = await myself_endpoint(request)
            response_text = str(chatbot_response)
        
        print(f"💬 Chatbot response: {response_text[:200]}...")
        
        # [7] ✨ XỬ LÝ PERSONALITY - Rewrite response nếu user có personality riêng
        if user_personality and user_personality_name:
            print(f"🎨 Applying personality: {user_personality_name}")
            try:
                response_text = user_personality.rewrite_response(
                    response=response_text,
                    personality_name=user_personality_name
                )
                print(f"✅ Response personality-adjusted")
            except Exception as e:
                print(f"⚠️  Error applying personality: {e}")
                # Continue với response original nếu có lỗi
        
        # [8] Lưu phản hồi của chatbot vào DB
        assistant_message_payload = CreateMessagePayload(
            chat_id=chat_id, 
            role="assistant", 
            content=response_text
        )
        messageservice.create_message(assistant_message_payload)
        print(f"✅ Saved assistant message to DB")
        
        return response_text
        
    except Exception as e:
        print(f"❌ Error in pipeline: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Lưu error message
        error_message = "Xin lỗi, đã có lỗi xảy ra. Vui lòng thử lại sau."
        try:
            messageservice = MessageService()
            error_payload = CreateMessagePayload(
                chat_id=chat_uuid if 'chat_uuid' in locals() else uuid.UUID(chat_id), 
                role="assistant", 
                content=error_message
            )
            messageservice.create_message(error_payload)
        except:
            pass
            
        return error_message
    