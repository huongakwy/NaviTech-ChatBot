import uuid
from autogen import ConversableAgent
import psycopg2
from pydantic import BaseModel
from env import env
from models.chat import ChatbotRequest
from typing import Dict, Any, List
import re
import json
import time
from sqlalchemy import create_engine, text
from fastapi import APIRouter
from tool_call.qdrant_search import QSearch
from services.product import ProductService
from embedding.search import product_semantic_search

class AgentResponse(BaseModel):
    response: str


router = APIRouter( prefix="/chatbot", tags=["recomendation"])

llm_openai = {
    "model": env.OPENAI_API_MODEL,
    "api_key": env.OPENAI_API_KEY
}

class QdrantAgent:
    def __init__(self):
        self.llm_config = llm_openai
        self.db_schema = self._get_db_schema()
        self.agent = self._create_qdrant_agent()
    def _get_db_schema(self) -> str:
        return """
        point struct payload (Relational Database):

        Table: products
        Columns:
        - id: INTEGER PRIMARY KEY
        - title: TEXT NOT NULL
        """
    def _create_qdrant_agent(self) -> ConversableAgent:
        system_message = f"""
        Bạn là một chuyên gia Qdrant (vector database) với nhiệm vụ:
        1. Phân tích câu hỏi người dùng về sản phẩm, đánh giá và lọc các thông tin quan trọng để tạo truy vấn Qdrant hiệu quả.
        2. Xác định collection Qdrant cần truy vấn và từ khóa cần nhập vào để tìm kiếm
        3. Tạo duy nhất một JSON mô tả truy vấn Qdrant dựa trên phân tích của bạn, chuỗi truy vấn là mô tả sản phẩm.
        4. Chỉ trả về JSON, không thêm bất kỳ giải thích nào khác.


        {self.db_schema}

        Hãy trả về mô tả truy vấn Qdrant dưới dạng JSON:

        ```json
        {{
            "query_text": "giá trị đầu vào dạng chuỗi để là description tìm kiếm embedding",
        }}
        ```
        """
        return ConversableAgent(
            name="vector_expert",
            system_message=system_message,
            llm_config=self.llm_config,
            human_input_mode="NEVER"
        )
    def _extract_qdrant_query(self, response: str):
        print(f"Raw response for Qdrant query extraction: {response}")
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL) or \
                     re.search(r'(\{.*?\})', response, re.DOTALL)
        if not json_match:
            print("🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩111🥩🥩🥩🥩🥩")
            return {"collection_name": "products", "payload": "", "limit": 5}
        try:
            print("🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩232321🥩🥩🥩🥩🥩")
            return json.loads(json_match.group(1))
        except json.JSONDecodeError as e:
            print("🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩🥩3232132131312🥩🥩🥩🥩🥩🥩")
            return {"collection_name": "products", "payload": "", "limit": 5}

    def _execute_qdrant_query(self, query_info: Dict[str, Any], user_id: str, top_k = 5):
        id = str(user_id)
        print(id)
        print("🥨🥐🥯🧀🥖🍠🥟🥠🍤🍤🍣🍣")
        print(f"Executing Qdrant query with info: {query_info}, id: {id}, top_k: {top_k}")
        result =  product_semantic_search(query_info, id, top_k)
        print(result)
        return result

    def _generate_explanation(self,  query_result: List[Dict], user_query: str):
        if not query_result:
            return {"response": "Không tìm thấy kết quả phù hợp với yêu cầu của bạn."}

        print("🍔🍟🌴🌴🌴🌴🌴🌴🌴🌴🌴🌴🌴🌴🌴🌴🌴🌴🌴🌴🌴🌴🌴🌴🌴🌴🌭🍕🥪")
        data_description = f"Đây là một số sản phẩm mà tôi tìm thấy cho bạn: "
        top_products = ", ".join(
            f"{item['title']} ({item.get('price', 'N/A')} VND) {item.get('brand', 'N/A')}" for item in query_result[:3]
        )
        data_description += f" {top_products}."
        print(data_description)
        print("🍔🍟🌭🍕🥪🥙🥙🥙🥙🥙🥙🥙🥙🥙🥙🥙🥙🥙🥙🧆🍗🍖🥩🍠")
        explanation_prompt = f"""
        Bạn là 1 trợ lý AI thông minh, làm việc cho Navitech.
        Bạn sẽ nhận đầu vào là một câu hỏi của người dùng về sản phẩm và một mô tả dữ liệu trả về từ Qdrant.
        Câu hỏi của người dùng: {user_query}
        Mô tả dữ liệu trả về: {data_description}
        Hãy viết câu trả lời thân thiện bằng tiếng Việt để giới thiệu về sản phẩm.
        """
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=explanation_prompt,
        )
        return response.text



    async def process_query(self, user_query: str, user_id: str):
        try:
            prompt = f"""Hãy phân tích và tạo truy vấn Qdrant cho câu hỏi sau: "{user_query}" """
            print(f"Prompt: {prompt}")
            agent_response = await self.agent.a_generate_reply(messages=[{"role": "user", "content": prompt}])
            print(f"Agent Response: {agent_response}")
            print(f"Agent Response: {agent_response.get('content')}")
            query_info = self._extract_qdrant_query(agent_response.get('content'))
            print("🥗🥗🥗🥗🥗🥗🥗🥗🥗🥗🥗🥗🥗🥗🥗🥗🥗🥗🥗🥗🥗🥗🥗🥗🥗🥗🥗🥗🥗🥗🥗🥗🥗🥗")
            print(f"Extracted Qdrant Query Info: {query_info}")
            print(query_info.get("query_text"))
            raw_results = self._execute_qdrant_query(query_info.get("query_text"), user_id=str(user_id), top_k=5)
            print("🥄🥄🍴🥄🍴🍴🍴🍴🍽🍽🍽🍽🥄🥄🥄🍴🍴🍴🍴🍀🌿🌿🍁🍁🍀🍁🌾🥜🌱🌴🌳🌳🌼🌷🌱☘☘")
            print(f"Raw Results: {raw_results}")
            # Trích product_id và gọi ProductServices.get
            products = []
            for pid in raw_results:
                if pid:
                    product = ProductService.get_some_infor(pid)
                    if product:
                        products.append(product)

            print("🍇🍉🍊🍋🍌🍍🥭🍎🍏🍐🍑🍒🍓🥝🥥🥑🍆🥔🥕🌽🌶️🫑🥒🥬")
            print(f"Products: {products}")
            explanation = self._generate_explanation(products, user_query)
            print(f"Explanation: {explanation}")
            return explanation

        except Exception as e:
            return f"Đã xảy ra lỗi khi thực hiện truy vấn: {e}"

@router.post("/recomendation", response_model=str)
async def chatbot_endpoint(request: ChatbotRequest, user_id: str):
    try:
        message = request.message

        # # Lưu tin nhắn vào cơ sở dữ liệu
        # message_repository = MessageRepository()
        # message_payload = CreateMessagePayload(
        #     chat_id=request.chat_id,
        #     role="user",
        #     content=message
        # )
        # message_repository.create(message_payload)
        # Tạo câu hỏi cho agent
        question = message
        agent = QdrantAgent()
        response = await agent.process_query(user_query=question , user_id=user_id)
        # Lưu phản hồi vào cơ sở dữ liệu
        # response_payload = CreateMessagePayload(
        #     chat_id=request.chat_id,
        #     role="assistant",
        #     content=response
        # )
        # message_repository.create(response_payload)
        return response
    except Exception as e:
        return "Đã xảy ra lỗi khi xử lý yêu cầu."