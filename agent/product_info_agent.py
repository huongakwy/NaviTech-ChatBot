import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

import autogen
from autogen import ConversableAgent
from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from env import env
from models.chats import ChatMessageCreate
from repositories.message import MessageRepository
from services.products import ProductServices
from services.search import SearchServices

router = APIRouter(prefix="/product-info", tags=["Product Information"])

class ProductInfoRequest(BaseModel):
    chat_id: int
    message: str
    product_id: Optional[int] = None
    entities: Optional[Dict[str, Any]] = None

class ProductInfoResponse(BaseModel):
    content: str = Field(..., description="Nội dung phản hồi từ agent")
    product_info: Dict[str, Any] = Field(default={}, description="Thông tin chi tiết sản phẩm")
    query_type: str = Field(default="product_info", description="Loại truy vấn: product_info, error")
    context_used: Dict[str, Any] = Field(default={}, description="Thông tin context đã sử dụng")
    
class ProductInfoAgent:
    def __init__(self):
        """Initialize the Product Information Agent with necessary configurations."""
        self.llm_config = {
            "model": "gpt-4o-mini",
            "api_key": env.OPENAI_API_KEY
        }
        self.agent = self._create_product_info_agent()
        
        # Define common error messages
        self.error_messages = {
            "product_not_found": "Rất tiếc, tôi không thể tìm thấy thông tin về sản phẩm này. Bạn có thể cung cấp thêm chi tiết hoặc tìm kiếm sản phẩm khác.",
            "attribute_not_found": "Tôi không tìm thấy thông tin về thuộc tính bạn yêu cầu. Bạn có muốn biết về các thuộc tính khác của sản phẩm không?",
            "general_error": "Đã xảy ra lỗi khi xử lý yêu cầu. Vui lòng thử lại sau.",
        }

    def _create_product_info_agent(self) -> ConversableAgent:
        """Create and configure the product information agent."""
        system_message = """
        Bạn là Product Information Agent thông minh cho hệ thống thương mại điện tử IUH-Ecommerce.
        
        Nhiệm vụ của bạn:
        1. Cung cấp thông tin chi tiết về sản phẩm (mô tả, thông số kỹ thuật, giá, tình trạng kho)
        2. Trả lời các câu hỏi về đặc tính sản phẩm cụ thể
        3. Kiểm tra tình trạng tồn kho
        4. Giải thích các thuật ngữ kỹ thuật và thông số
        
        Mỗi khi nhận được yêu cầu, bạn cần xác định:
        1. Sản phẩm mà người dùng đang hỏi (ID hoặc tên)
        2. Loại thông tin họ muốn biết
        3. Cách trình bày thông tin theo cách dễ hiểu nhất
        
        Hãy trả về một JSON với cấu trúc:
        {
            "query_type": "specific_product | attribute | availability | comparison",
            "product_identifier": {
                "type": "id | name | criteria",
                "value": "Giá trị định danh"
            },
            "attribute_focus": ["thuộc tính 1", "thuộc tính 2"],
            "explanation_level": "basic | detailed | technical"
        }
        """
        return autogen.ConversableAgent(
            name="product_info",
            system_message=system_message,
            llm_config=self.llm_config,
            human_input_mode="NEVER"
        )

    def _extract_product_query(self, response: str) -> Dict[str, Any]:
        """Extract JSON product query from agent response with error handling."""
        try:
            # Find JSON in the response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            # Default query if extraction fails
            default_query = {
                "query_type": "specific_product", 
                "product_identifier": {"type": "id", "value": 0},
                "attribute_focus": ["all"],
                "explanation_level": "basic"
            }
            
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                query = json.loads(json_str)
                
                # Validate essential fields
                if not query.get("query_type") or not query.get("product_identifier"):
                    logger.warning("Missing required fields in JSON query")
                    return default_query
                
                return query
            else:
                logger.warning(f"No JSON found in response: {response}")
                return default_query
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error: {e}")
            return default_query

    def _find_product(self, product_query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find product based on the query information."""
        try:
            identifier = product_query.get("product_identifier", {})
            id_type = identifier.get("type")
            value = identifier.get("value")
            
            if id_type == "id" and value:
                # Direct query by ID
                try:
                    product_id = int(value) if not isinstance(value, int) else value
                    product = ProductServices.get(product_id)
                    if product:
                        return product.__dict__
                except (ValueError, TypeError):
                    logger.warning(f"Invalid product ID format: {value}")
                    return None
                    
            elif id_type == "name" and value:
                # Search by product name
                search_results = SearchServices.search(
                    payload=value,
                    collection_name="products",
                    limit=1
                )
                if search_results and search_results.get("results"):
                    product_id = search_results["results"][0].get("id")
                    if product_id:
                        product = ProductServices.get(product_id)
                        if product:
                            return product.__dict__
                            
            elif id_type == "criteria" and value:
                # Search by description or criteria
                search_results = SearchServices.search(
                    payload=value,
                    collection_name="products",
                    limit=1
                )
                if search_results and search_results.get("results"):
                    product_id = search_results["results"][0].get("id")
                    if product_id:
                        product = ProductServices.get(product_id)
                        if product:
                            return product.__dict__
                
            return None
        except Exception as e:
            logger.error(f"Error finding product: {e}")
            return None

    def _check_availability(self, product_id: int) -> Dict[str, Any]:
        """Check inventory status for a product."""
        try:
            # Implement real inventory check in production
            # Mock implementation for now
            return {
                "in_stock": True,
                "quantity": 42,
                "delivery_estimate": "2-3 ngày"
            }
        except Exception as e:
            logger.error(f"Error checking inventory: {e}")
            return {
                "in_stock": False,
                "quantity": 0,
                "delivery_estimate": "N/A"
            }

    def _format_product_info(self, product: Dict[str, Any], query_info: Dict[str, Any]) -> str:
        """Format product information based on query type and explanation level."""
        if not product:
            return self.error_messages["product_not_found"]
            
        try:
            query_type = query_info.get("query_type")
            attribute_focus = query_info.get("attribute_focus", ["all"])
            explanation_level = query_info.get("explanation_level", "basic")
            
            if query_type == "specific_product":
                # Overall product information
                response = f"### {product.get('name')}\n\n"
                
                # Add price
                price = product.get('price')
                if price:
                    response += f"**Giá:** {price:,} VNĐ\n\n"
                
                # Add description
                description = product.get('description')
                if description:
                    if explanation_level == "basic":
                        # Brief summary
                        response += f"**Mô tả:** {description[:150]}{'...' if len(description) > 150 else ''}\n\n"
                    else:
                        # Full description
                        response += f"**Mô tả chi tiết:**\n{description}\n\n"
                
                # Add specifications if focused or detailed explanation requested
                if "all" in attribute_focus or explanation_level in ["detailed", "technical"] or len(attribute_focus) > 1:
                    specs = product.get('specifications', {})
                    if specs:
                        response += "**Thông số kỹ thuật:**\n"
                        
                        # Show only specific attributes if requested
                        if "all" not in attribute_focus:
                            filtered_specs = {k: v for k, v in specs.items() if any(attr.lower() in k.lower() for attr in attribute_focus)}
                            for key, value in filtered_specs.items():
                                response += f"- {key}: {value}\n"
                        else:
                            # Show all specifications
                            for key, value in specs.items():
                                response += f"- {key}: {value}\n"
                
                # Add inventory information
                availability = self._check_availability(product.get('id'))
                response += f"\n**Tình trạng:** {'Còn hàng' if availability.get('in_stock') else 'Hết hàng'}"
                if availability.get('in_stock'):
                    response += f" (Số lượng còn: {availability.get('quantity')})"
                
                # Add delivery information
                response += f"\n**Giao hàng dự kiến:** {availability.get('delivery_estimate')}"
                
                return response
                
            elif query_type == "attribute":
                # Answer about specific attributes
                response = f"Thông tin về {', '.join(attribute_focus)} của sản phẩm {product.get('name')}:\n\n"
                
                # Check each requested attribute
                specs = product.get('specifications', {})
                if not specs:
                    return f"Rất tiếc, tôi không tìm thấy thông tin về {', '.join(attribute_focus)} cho sản phẩm {product.get('name')}."
                
                attributes_found = False
                
                for attr in attribute_focus:
                    # Look for exact matches or partial matches
                    exact_match = specs.get(attr)
                    if exact_match:
                        response += f"**{attr}:** {exact_match}\n\n"
                        attributes_found = True
                    else:
                        # Try partial matches
                        partial_matches = {k: v for k, v in specs.items() if attr.lower() in k.lower()}
                        for key, value in partial_matches.items():
                            response += f"**{key}:** {value}\n\n"
                            attributes_found = True
                
                if not attributes_found:
                    return self.error_messages["attribute_not_found"]
                
                # Add explanation if technical level requested
                if explanation_level == "technical" and attributes_found:
                    response += "\n**Giải thích kỹ thuật:**\n"
                    for attr in attribute_focus:
                        if attr.lower() in ["ram", "bộ nhớ", "memory"]:
                            response += "RAM càng cao thì máy càng có khả năng đa nhiệm tốt, xử lý nhiều ứng dụng cùng lúc.\n"
                        elif attr.lower() in ["cpu", "processor", "vi xử lý"]:
                            response += "CPU là bộ não của thiết bị, quyết định tốc độ xử lý các tác vụ.\n"
                        elif attr.lower() in ["gpu", "graphics", "đồ họa"]:
                            response += "GPU ảnh hưởng đến khả năng xử lý đồ họa, hiệu ứng hình ảnh và game.\n"
                
                return response
                
            elif query_type == "availability":
                # Check product availability
                availability = self._check_availability(product.get('id'))
                response = f"Tình trạng sản phẩm **{product.get('name')}**:\n\n"
                
                if availability.get('in_stock'):
                    response += f"✅ **Còn hàng** - Số lượng còn: {availability.get('quantity')}\n"
                    response += f"🚚 **Giao hàng dự kiến:** {availability.get('delivery_estimate')}\n"
                    
                    # Add information about delivery policy
                    response += "\n**Chính sách giao hàng:**\n"
                    response += "- Miễn phí giao hàng cho đơn từ 300,000 VNĐ\n"
                    response += "- Giao hàng nhanh trong nội thành\n"
                    response += "- Đổi trả trong vòng 7 ngày nếu sản phẩm lỗi\n"
                else:
                    response += "❌ **Hết hàng**\n"
                    response += "Rất tiếc, sản phẩm này hiện đã hết hàng.\n\n"
                    response += "Bạn có thể:\n"
                    response += "- Đăng ký nhận thông báo khi có hàng\n"
                    response += "- Xem các sản phẩm tương tự\n"
                    
                return response
                
            elif query_type == "comparison":
                # Basic comparison info - in a real implementation, this would compare with other products
                response = f"So sánh sản phẩm **{product.get('name')}**:\n\n"
                response += f"**Giá:** {product.get('price', 0):,} VNĐ\n"
                
                specs = product.get('specifications', {})
                if specs:
                    response += "**Thông số chính:**\n"
                    main_specs = ["RAM", "CPU", "Màn hình", "Pin", "Camera", "Bộ nhớ", "Kích thước"]
                    for spec in main_specs:
                        for key, value in specs.items():
                            if spec.lower() in key.lower():
                                response += f"- {key}: {value}\n"
                                break
                
                response += "\n**Ưu điểm:**\n"
                response += "- Chất lượng tốt\n"
                response += "- Giá cả phù hợp\n"
                
                response += "\n**Nhược điểm:**\n"
                response += "- Cần đánh giá cụ thể hơn\n"
                
                response += "\n*Lưu ý: Để so sánh với sản phẩm cụ thể khác, vui lòng cung cấp thêm thông tin.*"
                
                return response
                
            else:
                # Default to basic product information
                return f"Sản phẩm: {product.get('name')}\nGiá: {product.get('price', 0):,} VNĐ"
                
        except Exception as e:
            logger.error(f"Error formatting product info: {e}")
            return f"Đã xảy ra lỗi khi xử lý thông tin sản phẩm: {str(e)}"

    async def process_product_info(self, request: ProductInfoRequest) -> ProductInfoResponse:
        """Process product information request and return detailed product information."""
        try:
            # If no product ID is provided, try to search by text
            if not request.product_id:
                # Search for products based on the message
                search_results = SearchServices.search(
                    query=request.message,
                    collection_name="products",
                    limit=5
                )
                
                if not search_results:
                    logger.warning(f"No products found for query: {request.message}")
                    return ProductInfoResponse(
                        content="Xin lỗi, tôi không tìm thấy sản phẩm phù hợp. Bạn có thể thử:\n"
                               "1. Sử dụng từ khóa khác\n"
                               "2. Tìm kiếm theo danh mục\n"
                               "3. Cung cấp ID sản phẩm cụ thể",
                        product_info={},
                        query_type="error",
                        context_used={"message": request.message}
                    )
                
                # Format search results
                products_info = []
                for result in search_results:
                    try:
                        product_info = {
                            "id": result["id"],
                            "name": result["name"],
                            "description": result["description"],
                            "price": result["price"],
                            "brand": result["brand"],
                            "category": result["category"],
                            "stock": result["stock"],
                            "similarity_score": result["similarity_score"]
                        }
                        products_info.append(product_info)
                    except KeyError as e:
                        logger.warning(f"Missing field in search result: {e}")
                        continue
                
                if not products_info:
                    return ProductInfoResponse(
                        content="Xin lỗi, tôi không thể hiển thị thông tin sản phẩm. Vui lòng thử lại sau.",
                        product_info={},
                        query_type="error",
                        context_used={"message": request.message}
                    )
                
                # Generate response using LLM
                prompt = f"""
                Phân tích thông tin sản phẩm và tạo phản hồi thân thiện với người dùng.
                
                Danh sách sản phẩm tìm thấy:
                {json.dumps(products_info, indent=2, ensure_ascii=False)}
                
                Người dùng hỏi: "{request.message}"
                
                Hãy tạo phản hồi thân thiện, đầy đủ thông tin và hữu ích, bao gồm:
                1. Tổng số sản phẩm tìm thấy
                2. Thông tin chi tiết về từng sản phẩm (tên, giá, thương hiệu, danh mục)
                3. Điểm tương đồng của mỗi sản phẩm
                4. Gợi ý nếu người dùng muốn biết thêm thông tin về sản phẩm cụ thể
                
                Nếu người dùng hỏi về giá của một số lượng cụ thể (ví dụ: "10 cuộn giấy"), hãy tính toán và hiển thị tổng giá.
                """
                
                # Get response from agent
                agent_response = await self.agent.a_generate_reply(
                    messages=[{"role": "user", "content": prompt}]
                )
                
                return ProductInfoResponse(
                    content=agent_response,
                    product_info={"products": products_info},
                    query_type="product_search",
                    context_used={
                        "message": request.message,
                        "timestamp": datetime.now().isoformat()
                    }
                )

            # If product ID is provided, get detailed information
            product_info = ProductServices.get_info(request.product_id)
            if not product_info or not product_info.get("product"):
                logger.warning(f"Product with ID {request.product_id} not found")
                return ProductInfoResponse(
                    content="Xin lỗi, không tìm thấy thông tin sản phẩm. Vui lòng kiểm tra lại ID sản phẩm.",
                    product_info={},
                    query_type="error",
                    context_used={}
                )

            # Get product details
            product = product_info["product"]
            brand = product_info.get("brand", [{}])[0] if product_info.get("brand") else {}
            category = product_info.get("category", [{}])[0] if product_info.get("category") else {}
            inventory = product_info.get("inventory", [{}])[0] if product_info.get("inventory") else {}

            # Handle category_id
            try:
                if isinstance(category.get("id"), str):
                    # Try to extract first number from string like "1520/1584/1587/68187/0"
                    category_id = int(category.get("id").split("/")[0])
                else:
                    category_id = int(category.get("id", 0)) if category else 0
            except (ValueError, TypeError, IndexError):
                category_id = 0

            # Handle datetime fields
            def format_datetime(dt):
                if dt is None:
                    return None
                try:
                    if isinstance(dt, str):
                        return dt
                    return dt.isoformat()
                except (AttributeError, TypeError):
                    return None

            # Prepare product information
            product_details = {
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "price": product.price,
                "brand": brand.get("name") if brand else None,
                "category": category.get("name") if category else None,
                "category_id": category_id,
                "stock": inventory.get("quantity", 0) if inventory else 0,
                "created_at": format_datetime(getattr(product, 'created_at', None)),
                "updated_at": format_datetime(getattr(product, 'updated_at', None))
            }

            # Generate response using LLM
            prompt = f"""
            Phân tích thông tin sản phẩm và tạo phản hồi thân thiện với người dùng.
            
            Thông tin sản phẩm:
            - Tên: {product.name}
            - Mô tả: {product.description}
            - Giá: {product.price:,} VND
            - Thương hiệu: {brand.get('name') if brand else 'Không có'}
            - Danh mục: {category.get('name') if category else 'Không có'}
            - Số lượng tồn kho: {inventory.get('quantity', 0) if inventory else 0}
            
            Người dùng hỏi: "{request.message}"
            
            Hãy tạo phản hồi thân thiện, đầy đủ thông tin và hữu ích.
            """

            # Get response from agent
            agent_response = await self.agent.a_generate_reply(
                messages=[{"role": "user", "content": prompt}]
            )

            # Prepare context used
            context_used = {
                "product_id": request.product_id,
                "message": request.message,
                "timestamp": datetime.now().isoformat()
            }

            return ProductInfoResponse(
                content=agent_response,
                product_info=product_details,
                query_type="product_info",
                context_used=context_used
            )

        except Exception as e:
            logger.error(f"Error processing product info: {e}")
            return ProductInfoResponse(
                content=f"Xin lỗi, đã xảy ra lỗi khi xử lý thông tin sản phẩm: {str(e)}",
                product_info={},
                query_type="error",
                context_used={}
            )

    async def process_request(self, request: Union[ProductInfoRequest, Any]) -> ProductInfoResponse:
        """Process a product information request."""
        try:
            # Convert any request type to ProductInfoRequest
            if not isinstance(request, ProductInfoRequest):
                # Extract necessary fields from the request object
                product_id = getattr(request, 'product_id', None)
                if product_id is None and hasattr(request, 'entities'):
                    entities = getattr(request, 'entities', {})
                    if isinstance(entities, dict):
                        product_id = entities.get('product_id')
                
                request = ProductInfoRequest(
                    chat_id=getattr(request, 'chat_id', 0),
                    message=getattr(request, 'message', ''),
                    product_id=product_id,
                    entities=getattr(request, 'entities', {})
                )

            # If no product_id is provided, try to search by text
            if not request.product_id:
                # First, extract product keywords from the question
                keyword_prompt = f"""
                Từ câu hỏi của người dùng, hãy trích xuất từ khóa sản phẩm chính.
                Chỉ trả về từ khóa, không thêm giải thích hay định dạng.
                Nếu có tên sản phẩm cụ thể, hãy sử dụng tên đó.
                Câu hỏi: {request.message}
                """
                
                keyword_response = await self.agent.a_generate_reply(
                    messages=[{"role": "user", "content": keyword_prompt}]
                )
                
                # Clean up the keyword response
                keywords = str(keyword_response).strip()
                logger.info(f"Extracted keywords: {keywords}")

                # Search for products using the keywords
                search_results = SearchServices.search(
                    query=keywords,
                    collection_name="product_embeddings",  # Changed to correct collection name
                    limit=5
                )
                
                if not search_results:
                    logger.warning(f"No products found for keywords: {keywords}")
                    return ProductInfoResponse(
                        content="Xin lỗi, tôi không tìm thấy sản phẩm phù hợp. Bạn có thể thử:\n"
                               "1. Sử dụng từ khóa khác\n"
                               "2. Tìm kiếm theo danh mục\n"
                               "3. Cung cấp ID sản phẩm cụ thể",
                        product_info={},
                        query_type="error",
                        context_used={"message": request.message, "keywords": keywords}
                    )
                
                # Format search results
                products_info = []
                for result in search_results:
                    try:
                        payload = result.get("payload", {})
                        product_info = {
                            "id": result.get("id"),
                            "name": payload.get("product_name"),
                            "description": payload.get("description"),
                            "category": payload.get("category"),
                            "similarity_score": result.get("score", 0)
                        }
                        products_info.append(product_info)
                    except Exception as e:
                        logger.warning(f"Error formatting product info: {e}")
                        continue
                
                if not products_info:
                    return ProductInfoResponse(
                        content="Xin lỗi, tôi không thể hiển thị thông tin sản phẩm. Vui lòng thử lại sau.",
                        product_info={},
                        query_type="error",
                        context_used={"message": request.message, "keywords": keywords}
                    )
                
                # Generate response using LLM
                response_prompt = f"""
                Dựa trên thông tin sản phẩm tìm thấy, hãy tạo phản hồi thân thiện cho người dùng.
                
                Câu hỏi của người dùng: {request.message}
                
                Thông tin sản phẩm tìm thấy:
                {json.dumps(products_info, indent=2, ensure_ascii=False)}
                
                Yêu cầu:
                1. Mở đầu bằng lời chào thân thiện
                2. Trả lời câu hỏi dựa trên thông tin sản phẩm có sẵn
                3. Nếu có nhiều sản phẩm, liệt kê các sản phẩm phù hợp nhất
                4. Kết thúc bằng gợi ý nếu người dùng muốn biết thêm thông tin chi tiết
                5. Giữ giọng điệu chuyên nghiệp và thân thiện
                6. KHÔNG sử dụng markdown hoặc định dạng đặc biệt
                """
                
                # Get response from agent
                agent_response = await self.agent.a_generate_reply(
                    messages=[{"role": "user", "content": response_prompt}]
                )
                
                return ProductInfoResponse(
                    content=str(agent_response),
                    product_info={"products": products_info},
                    query_type="product_search",
                    context_used={
                        "message": request.message,
                        "keywords": keywords,
                        "timestamp": datetime.now().isoformat()
                    }
                )

            # If product_id is provided, get detailed information
            product_info = ProductServices.get_info(request.product_id)
            if not product_info or not product_info.get("product"):
                logger.warning(f"Product with ID {request.product_id} not found")
                return ProductInfoResponse(
                    content="Xin lỗi, không tìm thấy thông tin sản phẩm. Vui lòng kiểm tra lại ID sản phẩm.",
                    product_info={},
                    query_type="error",
                    context_used={}
                )

            # Get product details
            product = product_info["product"]
            brand = product_info.get("brand", [{}])[0] if product_info.get("brand") else {}
            category = product_info.get("category", [{}])[0] if product_info.get("category") else {}
            inventory = product_info.get("inventory", [{}])[0] if product_info.get("inventory") else {}

            # Handle category_id
            try:
                if isinstance(category.get("id"), str):
                    # Try to extract first number from string like "1520/1584/1587/68187/0"
                    category_id = int(category.get("id").split("/")[0])
                else:
                    category_id = int(category.get("id", 0)) if category else 0
            except (ValueError, TypeError, IndexError):
                category_id = 0

            # Handle datetime fields
            def format_datetime(dt):
                if dt is None:
                    return None
                try:
                    if isinstance(dt, str):
                        return dt
                    return dt.isoformat()
                except (AttributeError, TypeError):
                    return None

            # Prepare product information
            product_details = {
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "price": product.price,
                "brand": brand.get("name") if brand else None,
                "category": category.get("name") if category else None,
                "category_id": category_id,
                "stock": inventory.get("quantity", 0) if inventory else 0,
                "created_at": format_datetime(getattr(product, 'created_at', None)),
                "updated_at": format_datetime(getattr(product, 'updated_at', None))
            }

            # Generate response using LLM
            prompt = f"""
            Phân tích thông tin sản phẩm và tạo phản hồi thân thiện với người dùng.
            
            Thông tin sản phẩm:
            - Tên: {product.name}
            - Mô tả: {product.description}
            - Giá: {product.price:,} VND
            - Thương hiệu: {brand.get('name') if brand else 'Không có'}
            - Danh mục: {category.get('name') if category else 'Không có'}
            - Số lượng tồn kho: {inventory.get('quantity', 0) if inventory else 0}
            
            Người dùng hỏi: "{request.message}"
            
            Hãy tạo phản hồi thân thiện, đầy đủ thông tin và hữu ích.
            """

            # Get response from agent
            agent_response = await self.agent.a_generate_reply(
                messages=[{"role": "user", "content": prompt}]
            )

            # Ensure response is a string
            if isinstance(agent_response, dict):
                response_content = json.dumps(agent_response, ensure_ascii=False)
            elif isinstance(agent_response, (list, tuple)):
                response_content = "\n".join(str(item) for item in agent_response)
            else:
                response_content = str(agent_response)

            return ProductInfoResponse(
                content=response_content,
                product_info=product_details,
                query_type="product_info",
                context_used={
                    "message": request.message,
                    "product_id": request.product_id,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Unexpected error in process_request: {str(e)}")
            return ProductInfoResponse(
                content=f"Đã xảy ra lỗi khi xử lý yêu cầu: {str(e)}",
                query_type="error",
                context_used={"error": str(e)}
            )


@router.post("/info", response_model=ProductInfoResponse)
async def get_product_info(request: ProductInfoRequest):
    """Endpoint to get detailed product information."""
    try:
        agent = ProductInfoAgent()
        return await agent.process_product_info(request)
    except Exception as e:
        logger.error(f"Error in product info endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing product info request: {str(e)}") 