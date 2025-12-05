"""PersonalityAgent - Rewrites responses with personality style using LLM"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid
import logging
import asyncio
from autogen import ConversableAgent
from db import get_db
from services.user import UserService
from env import env
from pydantic import BaseModel

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/personality", tags=["personality-styling"])

# LLM Configuration
llm_google = {
    "model": "gemini-2.5-flash",
    "api_key": env.GEMINI_API_KEY,
    "api_type": "google"
}


class PersonalityResponse(BaseModel):
    """Request body for applying personality to a response"""
    user_id: str
    response_text: str
    company_name: Optional[str] = "NAVITECH"
    agent_name: Optional[str] = "trợ lý AI"
    
    class Config:
        from_attributes = True


class StyledResponse(BaseModel):
    """Response with personality styling applied"""
    original_response: str
    styled_response: str
    personality_name: Optional[str]
    personality_applied: bool
    company_name: Optional[str] = "NAVITECH"
    agent_name: Optional[str] = "trợ lý AI"
    
    class Config:
        from_attributes = True


class PersonalityAgent:
    """Agent for rewriting responses with personality style using LLM"""
    
    PERSONALITY_PROMPTS = {
        "bình_thường": """Bạn là một trợ lý AI chuyên nghiệp, trung lập và cân bằng.
Hãy trả lời một cách rõ ràng, chính xác và chuyên nghiệp.
Giữ ngôn ngữ mặc định mà không thêm cảm xúc hoặc phong cách đặc biệt.""",

        "vui_vẻ": """Bạn là một trợ lý AI vui vẻ, thân thiện và hài hước.
Hãy trả lời một cách vui nhộn, tạo ra cảm giác tích cực.
Dùng emoji phù hợp, tone nhẹ nhàng nhưng không làm mất tính chuyên nghiệp.
Ví dụ: "Haha, bạn sẽ yêu thích cái này!"
Viết lại toàn bộ nội dung với phong cách vui vẻ này.""",

        "sáng_tạo": """Bạn là một trợ lý AI sáng tạo, có tưởng tượng và đổi mới.
Hãy trả lời một cách độc đáo, với cách nhìn nhân khác.
Dùng những mô tả sáng tạo, ẩn dụ phù hợp.
Làm cho phản hồi trở nên thú vị và gây cảm hứng.
Viết lại toàn bộ nội dung với phong cách sáng tạo này.""",

        "nghịch_ngợm": """Bạn là một trợ lý AI nghịch ngợm, tinh nghịch và đùa cợt.
Hãy trả lời một cách hài hước, với những câu chơi chữ và trò đùa.
Dùng emoji vui tươi, tone nhẹ nhàng và tươi cười.
Ví dụ: "Wink wink, bạn có thích không nè?"
Viết lại toàn bộ nội dung với phong cách nghịch ngợm này.""",

        "chuyên_nghiệp": """Bạn là một chuyên gia tư vấn chuyên nghiệp, trang trọng và chính thống.
Hãy trả lời một cách chi tiết, kỹ lưỡng và đầy tính logic.
Sử dụng ngôn ngữ chính thức, cấu trúc rõ ràng, dữ liệu cụ thể.
Tập trung vào giá trị thực tế và lợi ích.
Viết lại toàn bộ nội dung với phong cách chuyên nghiệp cao này.""",

        "tử_tế": """Bạn là một trợ lý AI lịch sự, ân cần và tử tế.
Hãy trả lời một cách ấm áp, chăm sóc và lòng mến.
Dùng ngôn ngữ nhẹ nhàng, thể hiện sự quan tâm chân thành.
Ví dụ: "Tôi hy vọng điều này sẽ giúp bạn được tốt hơn"
Viết lại toàn bộ nội dung với phong cách tử tế này.""",
    }
    
    def __init__(self, company_name: str = "NAVITECH", agent_name: str = "trợ lý AI"):
        """Initialize PersonalityAgent with LLM and custom naming"""
        self.llm_config = llm_google
        self.company_name = company_name
        self.agent_name = agent_name
    
    def _create_personality_agent(self, personality_name: str) -> ConversableAgent:
        """Create an LLM agent for specific personality"""
        system_message = self.PERSONALITY_PROMPTS.get(
            personality_name.lower().strip(),
            self.PERSONALITY_PROMPTS["bình_thường"]
        )
        
        return ConversableAgent(
            name=f"personality_{personality_name}",
            system_message=system_message,
            llm_config=self.llm_config,
            human_input_mode="NEVER"
        )
    
    async def apply_personality_async(self, response_text: str, personality_name: Optional[str]) -> Dict[str, Any]:
        """
        Rewrite response with personality style using LLM
        
        Args:
            response_text: The original response from any agent
            personality_name: The personality type to apply
            
        Returns:
            Dictionary with original and rewritten response
        """
        if not personality_name or personality_name.lower().strip() == "bình_thường":
            return {
                "original_response": response_text,
                "styled_response": response_text,
                "personality_name": personality_name or "bình_thường",
                "personality_applied": False,
                "company_name": self.company_name,
                "agent_name": self.agent_name
            }
        
        try:
            # Create personality agent
            agent = self._create_personality_agent(personality_name)
            
            # Create prompt to rewrite the response with company and agent context
            rewrite_prompt = f"""Bạn là {self.agent_name} của công ty {self.company_name}.

Hãy viết lại nội dung sau hoàn toàn theo phong cách và tính cách của bạn:

NỘI DUNG GỐC:
{response_text}

Hãy viết lại toàn bộ nội dung này (không chỉ thêm 1 dòng cuối) sao cho phù hợp với phong cách của bạn. 
- Có thể thay thế "NAVITECH" bằng "{self.company_name}"
- Có thể thay thế "trợ lý AI" bằng "{self.agent_name}"
- Giữ lại toàn bộ thông tin quan trọng từ nội dung gốc nhưng diễn đạt lại theo cách riêng của bạn."""
            
            # Get rewritten response from LLM
            response = await agent.a_generate_reply(
                messages=[{"role": "user", "content": rewrite_prompt}]
            )
            
            styled_response = response.get("content", response_text)
            
            return {
                "original_response": response_text,
                "styled_response": styled_response,
                "personality_name": personality_name.lower().strip(),
                "personality_applied": True,
                "company_name": self.company_name,
                "agent_name": self.agent_name
            }
            
        except Exception as e:
            logger.error(f"Error applying personality: {e}")
            return {
                "original_response": response_text,
                "styled_response": response_text,
                "personality_name": personality_name,
                "personality_applied": False,
                "error": str(e),
                "company_name": self.company_name,
                "agent_name": self.agent_name
            }
    
    @staticmethod
    def apply_personality(response_text: str, personality_name: Optional[str]) -> Dict[str, Any]:
        """
        Sync wrapper for apply_personality_async
        Note: This is a fallback. Use async version for actual rewriting.
        """
        if not personality_name or personality_name.lower().strip() == "bình_thường":
            return {
                "original_response": response_text,
                "styled_response": response_text,
                "personality_name": personality_name or "bình_thường",
                "personality_applied": False
            }
        
        # For sync calls, run async in event loop
        try:
            agent = PersonalityAgent()
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(agent.apply_personality_async(response_text, personality_name))
        except RuntimeError:
            # No event loop, create new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            agent = PersonalityAgent()
            return loop.run_until_complete(agent.apply_personality_async(response_text, personality_name))


# API Endpoints

@router.post("/apply", response_model=StyledResponse)
async def apply_personality_to_response(
    request: PersonalityResponse,
    session: Session = Depends(get_db)
):
    """
    Rewrite response with user's personality style (full rewrite, not just suffix)
    
    Args:
        request: {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "response_text": "✅ Tôi tìm thấy 5 sản phẩm..."
        }
        
    Returns:
        StyledResponse with completely rewritten response
        
    Example:
        POST /api/personality/apply
        {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "response_text": "✅ Tôi tìm thấy 5 sản phẩm phù hợp"
        }
        
        Response (original):
        {
            "original_response": "✅ Tôi tìm thấy 5 sản phẩm phù hợp",
            "styled_response": "✅ Tôi tìm thấy 5 sản phẩm phù hợp",
            "personality_name": "bình_thường",
            "personality_applied": false
        }
        
        Response (vui_vẻ personality - fully rewritten):
        {
            "original_response": "✅ Tôi tìm thấy 5 sản phẩm phù hợp",
            "styled_response": "Haha! Bạn may mắn lắm! Tôi vừa tìm thấy 5 sản phẩm tuyệt vời mà chắc chắn bạn sẽ thích 😄",
            "personality_name": "vui_vẻ",
            "personality_applied": true
        }
    """
    try:
        # Validate user_id format
        user_uuid = uuid.UUID(request.user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user_id format (must be valid UUID)"
        )
    
    # Get user's personality
    user_personality = UserService.get_user_personality(user_uuid)
    personality_name = user_personality['personality_name'] if user_personality else None
    
    # Apply personality rewriting with company and agent context
    agent = PersonalityAgent(
        company_name=request.company_name or "NAVITECH",
        agent_name=request.agent_name or "trợ lý AI"
    )
    result = await agent.apply_personality_async(request.response_text, personality_name)
    
    return StyledResponse(**result)


@router.post("/apply-direct", response_model=StyledResponse)
async def apply_personality_direct(
    response_text: str,
    personality: str,
    company_name: str = None,
    agent_name: str = None
):
    """
    Rewrite response with personality style directly (without user lookup)
    
    This endpoint uses LLM to completely rewrite the response according to the personality type.
    
    Args:
        response_text: The response to rewrite
        personality: The personality type to apply (e.g., 'vui_vẻ', 'sáng_tạo', 'chuyên_nghiệp')
        company_name: Company name to include in response (optional, defaults to "NAVITECH")
        agent_name: Agent name to include in response (optional, defaults to "trợ lý AI")
        
    Returns:
        StyledResponse with completely rewritten response
        
    Example:
        POST /api/personality/apply-direct?response_text=Hello%20world&personality=vui_vẻ&company_name=ABC%20Corp&agent_name=Smart%20Assistant
        
        Response:
        {
            "original_response": "Hello world",
            "styled_response": "Hey there! How's it going? Let me tell you something amazing... 😄",
            "personality_name": "vui_vẻ",
            "personality_applied": true,
            "company_name": "ABC Corp",
            "agent_name": "Smart Assistant"
        }
    """
    agent = PersonalityAgent(
        company_name=company_name or "NAVITECH",
        agent_name=agent_name or "trợ lý AI"
    )
    result = await agent.apply_personality_async(response_text, personality)
    return StyledResponse(**result)


@router.get("/available-personalities")
def get_available_personalities():
    """
    Get all available personality types and their descriptions
    
    Returns:
        Dictionary mapping personality names to their system prompts/descriptions
        
    Example:
        GET /api/personality/available-personalities
        
        Response:
        {
            "bình_thường": "Chuyên nghiệp, trung lập và cân bằng",
            "vui_vẻ": "Vui vẻ, thân thiện và hài hước",
            "sáng_tạo": "Sáng tạo, có tưởng tượng và đổi mới",
            "nghịch_ngợm": "Nghịch ngợm, tinh nghịch và đùa cợt",
            "chuyên_nghiệp": "Chuyên gia, trang trọng và chi tiết",
            "tử_tế": "Lịch sự, ân cần và tử_tế"
        }
    """
    descriptions = {
        "bình_thường": "Chuyên nghiệp, trung lập và cân bằng",
        "vui_vẻ": "Vui vẻ, thân thiện và hài hước",
        "sáng_tạo": "Sáng tạo, có tưởng tượng và đổi mới",
        "nghịch_ngợm": "Nghịch ngợm, tinh nghịch và đùa cợt",
        "chuyên_nghiệp": "Chuyên gia, trang trọng và chi tiết",
        "tử_tế": "Lịch sự, ân cần và tử_tế",
    }
    return descriptions
