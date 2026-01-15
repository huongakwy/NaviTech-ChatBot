"""
FAQ Embedding Functions - Xử lý embedding và sync vào Qdrant

Functions:
- sync_faq_to_qdrant: Đồng bộ FAQ từ PostgreSQL vào Qdrant
- delete_faq_from_qdrant: Xóa FAQ khỏi Qdrant
- recreate_faq_collection: Tạo lại collection FAQs
"""

import uuid
from typing import List, Dict, Any
from qdrant_client import QdrantClient, models
from embedding.generate_embeddings import generate_embedding
from env import env


class FAQEmbedding:
    """Class xử lý FAQ embedding operations"""
    
    def __init__(self, qdrant_url: str = None):
        if qdrant_url is None:
            from env import env
            qdrant_url = f"http://{env.QDRANT_HOST}:{env.QDRANT_PORT}"
        self.qdrant = QdrantClient(qdrant_url)
        self.collection_name = "faqs"
        self.embedding_dim = env.LEN_EMBEDDING
    
    def ensure_collection_exists(self) -> bool:
        """
        Đảm bảo collection FAQs tồn tại, tạo mới nếu chưa có
        
        Returns:
            True nếu collection exists hoặc tạo thành công
        """
        try:
            # Check if collection exists
            collections = self.qdrant.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.collection_name in collection_names:
                print(f"✅ Collection '{self.collection_name}' already exists")
                return True
            
            # Create collection
            print(f"📦 Creating collection '{self.collection_name}'...")
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.embedding_dim,
                    distance=models.Distance.COSINE
                )
            )
            
            # Create payload index for faster filtering
            self.qdrant.create_payload_index(
                collection_name=self.collection_name,
                field_name="user_id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            
            self.qdrant.create_payload_index(
                collection_name=self.collection_name,
                field_name="category",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            
            self.qdrant.create_payload_index(
                collection_name=self.collection_name,
                field_name="is_active",
                field_schema=models.PayloadSchemaType.BOOL
            )
            
            print(f"✅ Collection '{self.collection_name}' created successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error ensuring collection exists: {e}")
            return False
    
    def sync_faq_to_qdrant(
        self,
        faq_id: uuid.UUID,
        user_id: uuid.UUID,
        question: str,
        answer: str,
        category: str = None,
        priority: int = 0,
        is_active: bool = True
    ) -> bool:
        """
        Đồng bộ một FAQ vào Qdrant
        
        Args:
            faq_id: FAQ ID
            user_id: User ID
            question: Câu hỏi FAQ
            answer: Câu trả lời
            category: Danh mục (optional)
            priority: Độ ưu tiên
            is_active: Trạng thái active
            
        Returns:
            True nếu sync thành công
        """
        try:
            # Ensure collection exists
            if not self.ensure_collection_exists():
                return False
            
            # Generate embedding từ question
            print(f"🔄 Generating embedding for FAQ: {question[:50]}...")
            embedding = generate_embedding(question)
            
            if not embedding or len(embedding) != self.embedding_dim:
                print(f"❌ Invalid embedding generated")
                return False
            
            # Prepare payload
            payload = {
                "faq_id": str(faq_id),
                "user_id": str(user_id),
                "question": question,
                "answer": answer,
                "category": category or "",
                "priority": priority,
                "is_active": is_active
            }
            
            # Upsert to Qdrant (use faq_id as point id)
            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=str(faq_id),
                        vector=embedding,
                        payload=payload
                    )
                ]
            )
            
            print(f"✅ FAQ synced to Qdrant: {faq_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error syncing FAQ to Qdrant: {e}")
            return False
    
    def delete_faq_from_qdrant(self, faq_id: uuid.UUID) -> bool:
        """
        Xóa FAQ khỏi Qdrant
        
        Args:
            faq_id: FAQ ID cần xóa
            
        Returns:
            True nếu xóa thành công
        """
        try:
            self.qdrant.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=[str(faq_id)]
                )
            )
            print(f"✅ FAQ deleted from Qdrant: {faq_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting FAQ from Qdrant: {e}")
            return False
    
    def bulk_sync_faqs(self, faqs: List[Dict[str, Any]]) -> int:
        """
        Đồng bộ nhiều FAQs vào Qdrant
        
        Args:
            faqs: List of FAQ dicts với keys: faq_id, user_id, question, answer, etc.
            
        Returns:
            Số lượng FAQs synced thành công
        """
        success_count = 0
        
        for faq in faqs:
            result = self.sync_faq_to_qdrant(
                faq_id=faq["faq_id"],
                user_id=faq["user_id"],
                question=faq["question"],
                answer=faq["answer"],
                category=faq.get("category"),
                priority=faq.get("priority", 0),
                is_active=faq.get("is_active", True)
            )
            if result:
                success_count += 1
        
        print(f"✅ Bulk sync completed: {success_count}/{len(faqs)} FAQs")
        return success_count
    
    def recreate_collection(self) -> bool:
        """
        Xóa và tạo lại collection FAQs (CẢNH BÁO: Xóa toàn bộ data)
        
        Returns:
            True nếu thành công
        """
        try:
            # Delete collection if exists
            collections = self.qdrant.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.collection_name in collection_names:
                print(f"⚠️  Deleting collection '{self.collection_name}'...")
                self.qdrant.delete_collection(self.collection_name)
            
            # Create new collection
            return self.ensure_collection_exists()
            
        except Exception as e:
            print(f"❌ Error recreating collection: {e}")
            return False


# Singleton instance
_faq_embedding_instance = None

def get_faq_embedding() -> FAQEmbedding:
    """Get singleton instance of FAQEmbedding"""
    global _faq_embedding_instance
    if _faq_embedding_instance is None:
        _faq_embedding_instance = FAQEmbedding()
    return _faq_embedding_instance
