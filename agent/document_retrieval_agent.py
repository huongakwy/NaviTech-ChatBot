"""
DocumentRetrievalAgent - Tìm kiếm thông tin từ knowledge base

Agent này xử lý:
- Truy vấn thông tin từ documents đã upload
- Semantic search trên Qdrant collection "documents"
- RAG (Retrieval-Augmented Generation) để trả lời câu hỏi dựa trên knowledge base
"""

from autogen import ConversableAgent
from env import env
from models.chat import ChatbotRequest
from fastapi import APIRouter
from typing import List, Dict, Any
from qdrant_client import QdrantClient, models
from embedding.generate_embeddings import generate_embedding
from embedding.search import document_semantic_search   
import json
import re

router = APIRouter(prefix="/chatbot", tags=["Document Retrieval Agent"])

llm_config = {
    "model": "gemini-2.5-flash",
    "api_key": env.GEMINI_API_KEY,
    "api_type": "google"
}

class DocumentRetrievalAgent:
    def __init__(self):
        self.llm_config = llm_config
        self.qdrant = QdrantClient("http://localhost:6334")
        self.collection_name = "documents"
        
    def _search_documents(self, query: str, user_id: str, top_k: int = 5) -> List[Dict]:
        """
        Tìm kiếm documents trong Qdrant collection
        
        Args:
            query: Query string
            user_id: User ID để filter
            top_k: Số lượng chunks trả về
            
        Returns:
            List of relevant document chunks với payload
        """
        try:
            # Generate embedding cho query
            print("🍛🍛🍚🍜🍜🦪🦪🍠🍠🍣🍣🍣🍱🥡🥡")
            print(f"querry: {query}, user_id: {user_id}, top_k: {top_k}")
            
            # Search trong Qdrant với filter by user_id
            chunks = document_semantic_search(query, user_id, top_k, COLLECTION_NAME=self.collection_name)

            print(f"📚 Found {len(chunks)} relevant document chunks")
            print(chunks)

            # results = self.qdrant.query_points(
            #     collection_name=self.collection_name,
            #     query=query_embedding,
            #     using="default",
            #     query_filter=models.Filter(
            #         must=[
            #             models.FieldCondition(
            #                 key="user_id",
            #                 match=models.MatchValue(value=user_id)
            #             )
            #         ]
            #     ),
            #     limit=top_k,
            #     with_payload=True,
            #     with_vectors=False
            # )
            
            # Extract chunks với payload
            # chunks = []
            # for point in results.points:
            #     chunks.append({
            #         "id": point.id,
            #         "score": point.score,
            #         "text": point.payload.get("text", ""),
            #         "document_name": point.payload.get("document_name", "Unknown"),
            #         "chunk_index": point.payload.get("chunk_index", 0),
            #         "total_chunks": point.payload.get("total_chunks", 0),
            #         "created_at": point.payload.get("created_at", "")
            #     })
            
            print(f"📚 Found {len(chunks)} relevant document chunks")
            for chunk in chunks[:3]:  # Log top 3
                print(f"   - {chunk['document_name']} (chunk {chunk['chunk_index']}/{chunk['total_chunks']}) - Score: {chunk['score']:.3f}")
            
            return chunks
            
        except Exception as e:
            print(f"❌ Error searching documents: {str(e)}")
            return []
    
    def _create_rag_agent(self) -> ConversableAgent:
        """
        Tạo RAG agent để trả lời câu hỏi dựa trên retrieved documents
        """
        system_message = """
Bạn là một trợ lý AI thông minh của NAVITECH, chuyên trả lời câu hỏi dựa trên knowledge base.

NHIỆM VỤ:
1. Phân tích câu hỏi của người dùng
2. Sử dụng thông tin từ các documents đã được retrieve
3. Trả lời chính xác, đầy đủ dựa trên context
4. Trích dẫn nguồn (tên document) nếu có thể

NGUYÊN TẮC:
- Chỉ trả lời dựa trên context được cung cấp
- Nếu không có thông tin trong context → Nói rõ "Không tìm thấy thông tin"
- Trích dẫn document name khi trả lời
- Nếu context không đủ → Hỏi thêm chi tiết

OUTPUT FORMAT:
Trả lời trực tiếp bằng tiếng Việt, thân thiện, có cấu trúc rõ ràng.
"""
        return ConversableAgent(
            name="document_rag_expert",
            system_message=system_message,
            llm_config=self.llm_config,
            human_input_mode="NEVER"
        )
    
    async def process_query(self, query: str, user_id: str, top_k: int = 5) -> str:
        """
        Xử lý query với RAG pipeline
        
        Args:
            query: Câu hỏi của user
            user_id: User ID
            top_k: Số lượng chunks retrieve
            
        Returns:
            Response string với thông tin từ knowledge base
        """
        try:
            print(f"📖 DocumentRetrievalAgent processing: {query}")
            
            # [1] Retrieve relevant documents
            chunks = self._search_documents(query, user_id, top_k)
            
            if not chunks or len(chunks) == 0:
                return """Xin lỗi, tôi không tìm thấy thông tin liên quan trong knowledge base.

Có thể vì:
- Chưa có document nào được upload về chủ đề này
- Câu hỏi chưa đủ cụ thể

Bạn có thể:
- Upload thêm documents về chủ đề này
- Diễn đạt câu hỏi chi tiết hơn
- Hỏi về sản phẩm hoặc chủ đề khác

Tôi luôn sẵn sàng hỗ trợ! 😊"""
            
            # [2] Build context từ retrieved chunks
            context = self._build_context(chunks)
            
            # [3] Generate answer với RAG agent
            agent = self._create_rag_agent()
            
            prompt = f"""
Câu hỏi: {query}

Context từ knowledge base:
{context}

Hãy trả lời câu hỏi dựa trên context trên.
"""
            
            response = await agent.a_generate_reply(
                messages=[{"role": "user", "content": prompt}]
            )
            
            answer = response.get('content', '')
            
            # [4] Add metadata (sources)
            sources = self._extract_sources(chunks)
            if sources:
                answer += f"\n\n📚 **Nguồn tham khảo:**\n"
                for source in sources:
                    answer += f"- {source}\n"
            
            return answer
            
        except Exception as e:
            print(f"❌ Error in DocumentRetrievalAgent: {str(e)}")
            import traceback
            traceback.print_exc()
            return "Xin lỗi, đã có lỗi xảy ra khi tìm kiếm thông tin. Vui lòng thử lại sau."
    
    def _build_context(self, chunks: List[Dict]) -> str:
        """
        Build context string từ retrieved chunks
        """
        context_parts = []
        
        # Group by document
        docs = {}
        for chunk in chunks:
            doc_name = chunk['document_name']
            if doc_name not in docs:
                docs[doc_name] = []
            docs[doc_name].append(chunk)
        
        # Format context
        for doc_name, doc_chunks in docs.items():
            context_parts.append(f"\n--- Document: {doc_name} ---")
            
            # Sort by chunk_index
            doc_chunks.sort(key=lambda x: x['chunk_index'])
            
            for chunk in doc_chunks:
                text = chunk['text'].strip()
                if text:
                    context_parts.append(f"[Chunk {chunk['chunk_index']}/{chunk['total_chunks']}]: {text}")
        
        return "\n".join(context_parts)
    
    def _extract_sources(self, chunks: List[Dict]) -> List[str]:
        """
        Extract unique document names as sources
        """
        sources = set()
        for chunk in chunks:
            doc_name = chunk.get('document_name', 'Unknown')
            if doc_name != 'Unknown':
                sources.add(doc_name)
        return sorted(list(sources))


@router.post("/document_retrieval", response_model=str)
async def document_retrieval_endpoint(
    request: ChatbotRequest,
    user_id: str,
    top_k: int = 5
):
    """
    Endpoint để truy vấn knowledge base
    """
    agent = DocumentRetrievalAgent()
    response = await agent.process_query(
        query=request.message,
        user_id=user_id,
        top_k=top_k
    )
    return response
