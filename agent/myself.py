from autogen import ConversableAgent
from env import env
from models.chat import ChatbotRequest
from fastapi import APIRouter
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


class MySelfAgent:
    def __init__(self):
        self.llm_config = llm_google
        
    def _create_myself_agent(self) -> ConversableAgent:
        system_message = f"""
        Bạn là một trợ lý AI thông minh đại diện cho trang web NAVITECH, giúp tôi trả lời các câu hỏi về sở thích, 
        kỹ năng và thông tin của NAVITECH.
        Hãy trả lời các câu hỏi một cách chính xác và trung thực nhất có thể dựa trên thông tin bạn có về NAVITECH.
        """
        return ConversableAgent(
            name="myself_expert",
            system_message=system_message,
            llm_config={"config_list": self.llm_config},
            human_input_mode="NEVER"
        )
    
    async def process_query(self, query: str):
        try:
            agent = self._create_myself_agent()
            response = await agent.a_generate_reply([{"role": "user", "content": query}])
            return response
        except Exception as e:  
            return f"Đã xảy ra lỗi khi xử lý truy vấn: {e}"
        
        
router = APIRouter(prefix="/chatbot", tags=["MySelf Agent"])

@router.post("/myself", response_model=str)
async def myself_endpoint(request: ChatbotRequest):
    agent = MySelfAgent()
    response = await agent.process_query(request.message)
    return response['content']
