import json
import re
from agent.product_agent import product_agent 
from models.chat import ChatbotRequest
from agent.myself import myself_endpoint
from agent.recomendation_agent import chatbot_endpoint
from agent.personalization_agent import PersonalizationAgent
from agent.document_retrieval_agent import DocumentRetrievalAgent

def extract_json_query(response: str):
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL) or \
                    re.search(r'(\{.*?\})', response, re.DOTALL)
    if not json_match:
        return {'agent': 'MySelf', 'query': str(response)}
    try:
        return json.loads(json_match.group(1))
    except json.JSONDecodeError as e:
        return {'agent': 'MySelf', 'query': str(response)}
    


async def call_agen(agent: str, request: ChatbotRequest, **kwargs):
    """
    Gọi agent phù hợp dựa trên routing decision
    
    Args:
        agent: Tên agent cần gọi
        request: ChatbotRequest với chat_id, message, và user_id (optional)
        **kwargs: Additional parameters (previous_products, conversation_history, etc.)
    """
    try:
        if agent == "ProductAgent":
            return await product_agent(request.message)
        elif agent == "MySelf":
            return await myself_endpoint(request)
        elif agent == "RecommendationAgent":
            # RecommendationAgent cần user_id
            user_id = str(request.user_id) if request.user_id else "default_user"
            return await chatbot_endpoint(request, user_id=user_id)
        elif agent == "PersonalizationAgent":
            # PersonalizationAgent cần context
            personalization_agent = PersonalizationAgent()
            return await personalization_agent.process_query(
                query=request.message,
                previous_products=kwargs.get('previous_products'),
                conversation_history=kwargs.get('conversation_history')
            )
        elif agent == "DocumentRetrievalAgent":
            # DocumentRetrievalAgent tìm kiếm knowledge base
            user_id = str(request.user_id) if request.user_id else kwargs.get('user_id', 'default_user')
            document_agent = DocumentRetrievalAgent()
            return await document_agent.process_query(
                query=request.message,
                user_id=user_id,
                top_k=kwargs.get('top_k', 5)
            )
        else:
            # Fallback to MySelf nếu không match
            return await myself_endpoint(request)
    except Exception as e:
        print(f"❌ Error calling agent {agent}: {str(e)}")
        return f"Đã xảy ra lỗi khi xử lý yêu cầu với {agent}. Vui lòng thử lại."