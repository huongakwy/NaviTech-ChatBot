"""
PersonalizationAgent - Xử lý các câu hỏi về gợi ý cá nhân hóa

Agent này xử lý:
- Follow-up questions về sản phẩm đã tìm được
- Personal recommendations based on user context
- Comparative questions: "cái nào tốt hơn", "phù hợp nhất"
"""

from autogen import ConversableAgent
from env import env
from models.chat import ChatbotRequest
from fastapi import APIRouter
from typing import Dict, List, Any
import json

router = APIRouter(prefix="/chatbot", tags=["Personalization Agent"])

llm_config = {
    "model": "gemini-2.5-flash",
    "api_key": env.GEMINI_API_KEY,
    "api_type": "google"
}

class PersonalizationAgent:
    def __init__(self):
        self.llm_config = llm_config
        
    def _create_agent(self) -> ConversableAgent:
        system_message = """
Bạn là một chuyên gia tư vấn sản phẩm thông minh và tôn trọng đa dạng.

NHIỆM VỤ:
1. Phân tích context từ lịch sử chat để hiểu "cái nào" là gì
2. Đưa ra gợi ý phù hợp dựa trên nhu cầu cụ thể của người dùng
3. Tôn trọng mọi định hướng, bối cảnh cá nhân
4. Không phân biệt đối xử, không stereotype

NGUYÊN TẮC:
- Gợi ý dựa trên PRACTICAL NEEDS, không phải stereotype
- Nếu câu hỏi về "người gay", "LGBT", etc → Focus vào nhu cầu thực tế
- Ví dụ: Người gay cũng có thể có con, adopt, hoặc mua quà cho anh/chị/bạn bè
- Tránh giả định: "Gay không cần đồ em bé" → SAI

OUTPUT:
Trả về JSON:
{
    "recommendation": "Tên sản phẩm phù hợp nhất",
    "reason": "Lý do cụ thể dựa trên nhu cầu",
    "alternatives": ["Lựa chọn 2", "Lựa chọn 3"],
    "note": "Lưu ý bổ sung nếu có"
}

** Chỉ trả về JSON, không giải thích thêm **
"""
        return ConversableAgent(
            name="personalization_expert",
            system_message=system_message,
            llm_config=self.llm_config,
            human_input_mode="NEVER"
        )
    
    async def process_query(
        self, 
        query: str, 
        previous_products: List[Dict] = None,
        conversation_history: List[Dict] = None
    ) -> str:
        """
        Xử lý câu hỏi cá nhân hóa với context
        
        Args:
            query: Câu hỏi của user
            previous_products: Danh sách sản phẩm đã tìm được trước đó
            conversation_history: Lịch sử chat
        """
        agent = self._create_agent()
        
        # Build context-aware prompt
        context_prompt = f"Câu hỏi của người dùng: {query}\n\n"
        
        if previous_products:
            context_prompt += "Các sản phẩm đã được tìm thấy trước đó:\n"
            for i, product in enumerate(previous_products, 1):
                context_prompt += f"{i}. {product.get('title', 'N/A')} - {product.get('price', 'N/A')} VND\n"
            context_prompt += "\n"
        
        if conversation_history:
            context_prompt += "Lịch sử trò chuyện gần đây:\n"
            for msg in conversation_history[-3:]:  # Last 3 messages
                role = "Người dùng" if msg.get('role') == 'user' else "Trợ lý"
                context_prompt += f"{role}: {msg.get('content', '')[:100]}...\n"
            context_prompt += "\n"
        
        context_prompt += """
Hãy phân tích và đưa ra gợi ý phù hợp.
Lưu ý: 
- Focus vào nhu cầu thực tế, không stereotype
- Nếu không đủ thông tin để personalize, hãy hỏi thêm
- Tôn trọng mọi bối cảnh cá nhân
"""
        
        try:
            response = await agent.a_generate_reply(
                messages=[{"role": "user", "content": context_prompt}]
            )
            
            # Parse JSON response
            content = response.get('content', '{}')
            
            # Extract JSON
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL) or \
                        re.search(r'(\{.*?\})', content, re.DOTALL)
            
            if json_match:
                data = json.loads(json_match.group(1))
                
                # Build friendly response
                friendly_response = self._build_friendly_response(data, previous_products)
                return friendly_response
            else:
                # Fallback: return raw content
                return content
                
        except Exception as e:
            print(f"❌ Error in PersonalizationAgent: {str(e)}")
            return """Để tôi có thể tư vấn chính xác hơn, bạn có thể cho biết thêm:
- Sản phẩm dành cho ai? (bản thân, quà tặng, ...)
- Mục đích sử dụng cụ thể?
- Ngân sách dự kiến?

Tôi sẽ giúp bạn chọn sản phẩm phù hợp nhất! 😊"""
    
    def _build_friendly_response(self, data: Dict, products: List[Dict] = None) -> str:
        """
        Build friendly response from JSON data
        """
        recommendation = data.get('recommendation', '')
        reason = data.get('reason', '')
        alternatives = data.get('alternatives', [])
        note = data.get('note', '')
        
        response = f"""Dựa trên nhu cầu của bạn, tôi gợi ý:

🌟 **Lựa chọn tốt nhất:** {recommendation}
💡 **Lý do:** {reason}
"""
        
        if alternatives:
            response += f"\n📋 **Các lựa chọn khác:**\n"
            for i, alt in enumerate(alternatives, 1):
                response += f"   {i}. {alt}\n"
        
        if note:
            response += f"\n💭 **Lưu ý:** {note}\n"
        
        response += "\nBạn có cần tôi giải thích thêm về sản phẩm nào không? 😊"
        
        return response


@router.post("/personalization", response_model=str)
async def personalization_endpoint(
    request: ChatbotRequest,
    previous_products: List[Dict] = None,
    conversation_history: List[Dict] = None
):
    """
    Endpoint for personalized recommendations
    """
    agent = PersonalizationAgent()
    response = await agent.process_query(
        query=request.message,
        previous_products=previous_products,
        conversation_history=conversation_history
    )
    return response
