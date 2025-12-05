"""
Ví dụ sử dụng Model Manager trong FastAPI Controllers
"""

from fastapi import APIRouter
from embedding.generate_embeddings import generate_embedding, query_embedding
from embedding.insert_qdrant import insert_products_to_qdrant, ensure_collection_exists
router = APIRouter(prefix="/embedding", tags=["embedding"])

@router.post("/embed")
async def embed_text(text: str, payload: dict = {}):
    try:
        ensure_collection_exists("products")
        insert_products_to_qdrant(
            embedding=generate_embedding(text),
            point_id=payload.get("id"),
            payload=payload,
            USER_ID="products")
        
        return {
            "status": "success",
            "message": "Text embedded successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@router.get("/search-vector")
async def search_vector(query: str):
    """
    Endpoint để search vector.
    Cả embedding model và Qdrant client sẽ chỉ được load 1 lần.
    """
    try:
        # Lấy cả 2 resource
        model = get_embedding_model()
        qdrant_client = get_qdrant_client()
        
        # Encode query
        embedding = model.encode([query])['dense_vecs'][0]
        
        return {
            "status": "success",
            "message": "Vector search completed",
            "loaded_models": model_manager.list_models(),
            "embedding_dimension": len(embedding)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@router.get("/status")
async def check_status():
    """
    Kiểm tra trạng thái các models đã load
    """
    return {
        "loaded_models": model_manager.list_models(),
        "total_models": len(model_manager.list_models())
    }
