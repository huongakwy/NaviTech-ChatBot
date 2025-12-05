from env import env
from qdrant_client import QdrantClient, models
from embedding.generate_embeddings import query_embedding, generate_embedding

qdrant = QdrantClient("http://localhost:6334")

def semantic_search(query, user_id, top_k=5):
    # Tìm kiếm ANN trong collection
    print("🦪🦪🍜🍜🍛🍣🍣🍣🍣🍣🦪🦪🦪🦪🦪🦪🦪🦪🦪")
    print(f"Executing Qdrant query with info: {query}, id: {user_id}, top_k: {top_k}")
    query_Vector = generate_embedding(query)  
    search_result = qdrant.query_points(
        collection_name=user_id,
        query= query_Vector,
        using="default",
        limit=top_k,
        with_payload=True,
        with_vectors=False,
        )
    # lay du lieu tu id
    ids = [item.id for item in search_result.points]
    # products = []
    # for id in ids:
    #     product = ProductServices.get(id)
    #     if product:
    #         products.append(product)

    return ids

def product_semantic_search(query, user_id, top_k=5, COLLECTION_NAME="products"):
    # Tìm kiếm ANN trong collection
    print("🦪🦪🍜🍜🍛🍣🍣🍣🍣🍣🦪🦪🦪🦪🦪🦪🦪🦪🦪")
    print(f"Executing Qdrant query with info: {query}, id : {user_id}, top_k: {top_k}")
    results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=generate_embedding(query), 
        using ="default",
        query_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(
                        value=user_id
                    )
                )
            ]
        ),
        limit=5
    )
    ids = [item.id for item in results.points]
    return ids

def document_semantic_search(query, user_id, top_k=5, COLLECTION_NAME="documents"):
    """
    Tìm kiếm documents trong knowledge base
    
    Args:
        query: Query string
        user_id: User ID để filter
        top_k: Số lượng chunks trả về
        COLLECTION_NAME: Tên collection (default: "documents")
    
    Returns:
        List of relevant document chunks với full payload
    """
    print("📚📚📚📚📚📚📚📚📚📚📚📚📚📚📚📚📚📚📚📚📚📚📚")
    print(f"Document search: query='{query}', user_id={user_id}, top_k={top_k}")
    
    results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=generate_embedding(query),
        # using="default",
        query_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(value=user_id)
                )
            ]
        ),
        limit=top_k,
        with_payload=True,
        with_vectors=False
    )
    
    # Return full payload
    chunks = []
    for point in results.points:
        chunks.append({
            "id": point.id,
            "score": point.score,
            "text": point.payload.get("text", ""),
            "document_name": point.payload.get("document_name", ""),
            "chunk_index": point.payload.get("chunk_index", 0),
            "total_chunks": point.payload.get("total_chunks", 0),
            "created_at": point.payload.get("created_at", "")
        })
    
    print(f"Found {len(chunks)} chunks")
    return chunks
    # ids = [item.id for item in results.points]
    # return ids