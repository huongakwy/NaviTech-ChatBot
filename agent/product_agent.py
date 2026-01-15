import uuid
from autogen import ConversableAgent
import psycopg2
from env import env
from models.chat import ChatbotRequest
from typing import Dict, Any, List, Optional
import re
import json
import logging
import time
from sqlalchemy import create_engine, text
from fastapi import APIRouter
from psycopg2.extras import RealDictCursor
logging.basicConfig(
    level=logging.DEBUG,  # hiển thị từ DEBUG trở lên (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

router = APIRouter( prefix="/sqlchatbot", tags=["sqlsearch"])

llm_openai = {
    "model": env.OPENAI_API_MODEL,
    "api_key": env.OPENAI_API_KEY
}

class SQLAgent:
    def __init__(self):
        self.llm_config = llm_openai
        self.db_schema = self._get_db_schema()
        self.agent = self._create_sql_agent()
    
    def _get_db_schema(self) -> str:
        return """
        SQL TABLES (Relational Database):

        Table: products
        Columns:
        - id: UUID PRIMARY KEY
        - website_id: INTEGER NOT NULL
        - website_name: TEXT NOT NULL
        - url: TEXT NOT NULL
        - title: TEXT (product name)
        - price: DECIMAL
        - original_price: DECIMAL
        - currency: TEXT (default 'VND')
        - sku: TEXT
        - brand: TEXT
        - category: TEXT
        - description: TEXT (detailed product info)
        - availability: TEXT
        - images: ARRAY OF TEXT
        - created_at: TIMESTAMP
        - updated_at: TIMESTAMP
        
        IMPORTANT COLUMN MAPPINGS:
        - Use 'title' for product name (NOT 'name' or 'product_name')
        - Use 'id' for primary key (NOT 'product_id')
        - Use 'description' for product details
        - Use 'category' for product type
        """
    def _create_sql_agent(self) -> ConversableAgent:
        system_message = f"""
            🔍 Bạn là một chuyên gia SQL Query Generator cho hệ thống e-commerce.
            
            ⚠️ CRITICAL RULES:
            1. Luôn sử dụng đúng tên cột: id, title, description, category, brand, price (KHÔNG dùng product_id, name, category_id)
            2. Tìm kiếm sản phẩm phải match trên CẢ title AND category/description để chính xác
            3. Ví dụ: "sữa rửa mặt cho da dầu" → tìm BOTH "rửa mặt" trong title AND "da dầu" trong category/description
            4. Sử dụng LOWER() function cho case-insensitive search
            5. Luôn giới hạn kết quả bằng LIMIT (max 20)
            
            📋 Database schema:
            {self.db_schema}
            
            🎯 Task:
            1. Phân tích câu hỏi sản phẩm từ người dùng
            2. Xác định các tiêu chí tìm kiếm chính (keyword, category, price, brand)
            3. Sinh SQL query sử dụng ĐÚNG tên cột
            4. Trả về JSON chứa sql_query hoặc sql_queries
            5. Chỉ dùng SELECT, không INSERT/UPDATE/DELETE

            📝 JSON Output Format (ONLY ONE OR MULTIPLE sql_queries):
            
            **EXAMPLE 1 - Search "sữa rửa mặt cho da dầu":**
            ```json
            {{
                "sql_query": "SELECT id, title, description, price, brand, category FROM products WHERE (LOWER(title) LIKE '%rửa mặt%' OR LOWER(description) LIKE '%rửa mặt%') AND (LOWER(category) LIKE '%da dầu%' OR LOWER(description) LIKE '%da dầu%') LIMIT 15"
            }}
            ```
            
            **EXAMPLE 2 - Search "laptop gaming dưới 30 triệu":**
            ```json
            {{
                "sql_queries": [
                    "SELECT id, title, price, brand, category, description FROM products WHERE LOWER(title) LIKE '%laptop%' AND LOWER(title) LIKE '%gaming%' AND price < 30000000 LIMIT 15"
                ]
            }}
            ```
            
            **EXAMPLE 3 - Search "áo sơ mi":**
            ```json
            {{
                "sql_query": "SELECT id, title, price, brand, category, description FROM products WHERE LOWER(title) LIKE '%áo%' AND (LOWER(title) LIKE '%sơ mi%' OR LOWER(category) LIKE '%sơ mi%') LIMIT 15"
            }}
            ```
            
            ✅ CORRECT COLUMN NAMES: id, title, description, price, brand, category, availability, currency
            ❌ NEVER USE: product_id, name, product_name, category_id, product_category
            
            ⚡ SEARCH BEST PRACTICES:
            - Multiple conditions (AND) for specific results
            - Use LOWER() for case-insensitive search
            - Search in BOTH title and description when relevant
            - Include category filters to narrow results
        """
        return ConversableAgent(
            name="sql_expert",
            system_message=system_message,
            llm_config=self.llm_config,
            human_input_mode="NEVER"
        )
    def _extract_sql_query(self, response: str) -> Dict[str, Any]:
        json_match = re.search(r'json\s*(\{.*?\})\s*', response, re.DOTALL) or re.search(r'(\{.*?\})', response, re.DOTALL)
        if not json_match:
            logger.warning(f"Không tìm thấy truy vấn SQL: {response}")
            return {"queries": ["SELECT id, title, description, price, brand, category FROM products LIMIT 5"]}
        try:
            data = json.loads(json_match.group(1))
            queries = []
            # Chuẩn hóa thành danh sách truy vấn
            if "sql_query" in data:
                queries.append(data["sql_query"])
            if "sql_queries" in data and isinstance(data["sql_queries"], list):
                queries.extend(data["sql_queries"])
            if not queries:
                logger.warning(f"Không tìm thấy key sql_query hoặc sql_queries trong response: {data}")
                queries = ["SELECT id, title, description, price, brand, category FROM products LIMIT 5"]

            return {"queries": queries}

        except json.JSONDecodeError as e:
            logger.error(f"Lỗi parse JSON: {e}")
            return {"queries": ["SELECT id, title, description, price, brand, category FROM products LIMIT 5"]}
    def query_postgres(self, query_info: Dict[str, Any]) -> List[List[Dict]]:
        """
        Truy vấn PostgreSQL (SELECT, INSERT, UPDATE, DELETE).
        Hỗ trợ nhiều truy vấn liên tiếp.
        """
        print(f"Query Info: {query_info}")
        connection = None
        results = []
        try:
            connection = psycopg2.connect(
                host="localhost",
                port=env.POSTGRES_PORT,
                database="chatbot",
                user="postgres",
                password="mypassword"
            )
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                queries = query_info.get("queries") or [query_info.get("query") or query_info.get("sql_query")]
                params = query_info.get("params")
                for query in queries:
                    if not query:
                        continue
                    cursor.execute(query, params or None)
                    print(f"Executed Query: {query}")
                    if query.strip().lower().startswith("select"):
                        print("🍳🍳🍳🍳🍳🍳🍕🍕🍕🍕🍕🍔🍔🍔🍔🍔🍔🍟🍟🍟🍟🍟")
                        rows = cursor.fetchall()
                        results.append([dict(r) for r in rows])
                        print(f"Query Results: {rows}")
                    else:
                        connection.commit()
                        results.append([])  # giữ cấu trúc list đồng nhất
            return results
        except Exception as e:
            logger.exception(f"Lỗi khi thực thi truy vấn: {e}")
            return []
        finally:
            if connection:
                connection.close()
    def _generate_explanation(self, query_info: Dict[str, Any], query_result: List[Dict], user_query: str) -> str:
        if not query_result or len(query_result) == 0:
            return "Không tìm thấy kết quả phù hợp với yêu cầu của bạn. Bạn có muốn tôi tìm kiếm bằng cách khác không?"
        
        # Build detailed product list
        product_list = []
        for i, item in enumerate(query_result[:5], 1):
            title = item.get('title', 'N/A')
            price = item.get('price', 'N/A')
            brand = item.get('brand', '')
            category = item.get('category', '')
            desc = item.get('description', '')[:100] if item.get('description') else ''
            
            product_info = f"{i}. **{title}**"
            if brand:
                product_info += f" ({brand})"
            if price != 'N/A':
                product_info += f" - {price:,.0f} VND" if isinstance(price, (int, float)) else f" - {price} VND"
            if desc:
                product_info += f"\n   Mô tả: {desc}..."
            
            product_list.append(product_info)
        
        # Base explanation
        explanation_text = (
            f"✅ Tôi tìm thấy {len(query_result)} sản phẩm phù hợp với tìm kiếm của bạn!\n\n"
            + "\n\n".join(product_list) +
            f"\n\n💡 Có tổng cộng {len(query_result)} sản phẩm khớp với tiêu chí tìm kiếm của bạn. "
            "Bạn có muốn xem thêm hoặc tìm kiếm với tiêu chí khác không?"
        )
        return explanation_text

    async def process_query(self, user_query: str) -> Dict[str, Any]:
        try:
            prompt = f'Hãy phân tích và tạo truy vấn SQL cho câu hỏi sau:\n"{user_query}"'
            print(f"Prompt: {prompt}")

            agent_response = await self.agent.a_generate_reply(messages=[{"role": "user", "content": prompt}])
            print(f"Agent Response: {agent_response['content']}")
            query_info = self._extract_sql_query(agent_response['content'])
            print(f"Extracted SQL Query Info: {query_info}")
            query_info['chat_id'] = ""

            raw_results = self.query_postgres(query_info)[0]
            print(type(raw_results))
            print(f"Raw Query Results: {raw_results}")
            products = []
            for i in range(len(raw_results)):
                raw_results[i] = dict(raw_results[i])
                print(raw_results[i])
                print(type(raw_results[i]))
                row = dict(raw_results[i])
                
                # Extract product info with safe fallbacks
                try:
                    product = {
                        "id": str(row.get("id", "")),
                        "title": row.get("title", row.get("name", "N/A")),  # Handle both 'title' and 'name'
                        "price": row.get("price"),
                        "brand": row.get("brand"),
                        "category": row.get("category"),
                        "description": row.get("description", "")[:200] if row.get("description") else "",  # Preview only
                        "availability": row.get("availability")
                    }
                    products.append(product)
                except Exception as e:
                    logger.error(f"Error parsing product row: {e}")
                    continue

            print(f"Processed Products:🍠🥩🥩🥩🦪🦪🍚🍛🍛 {products}")
            explanation = self._generate_explanation(query_info, products, user_query, self.user_personality)
            print(f"Explanation: {explanation}")
            return {
                "response": explanation,
                "products": products
            }
        except Exception as e:
            logger.error(f"Lỗi truy vấn SQL: {e}")
            return {"response": "Đã xảy ra lỗi khi thực hiện truy vấn."}

# Minimal stubs for message storage to keep endpoint runnable; replace with real implementations as needed.
class MessageRepository:
    def create(self, payload: Any) -> None:
        logger.debug(f"Storing message payload: {payload}")

class CreateMessagePayload(dict):
    def __init__(self, chat_id: int, role: str, content: Any):
        super().__init__(chat_id=chat_id, role=role, content=content)

# AgentResponse can be a simple Dict for now; adapt to real Pydantic model if required.

@router.post("/chatbot", response_model=Dict[str, Any])
async def product_agent(question: str):
    print("HELLO")
    try:
        agent = SQLAgent()
        print("❎❎❎❎❎ Sending question to SQLAgent:", question)
        response = await agent.process_query(user_query=question)
        print(f"response: {response}")
        return response
    except Exception as e:
        logger.error(f"Lỗi trong chatbot_endpoint: {e}")
        return {"error": "internal server error"}

