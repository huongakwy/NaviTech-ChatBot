from env import env
from qdrant_client import QdrantClient
from embedding.generate_embeddings import query_embedding, generate_embedding
from models.product import Product, ProductModel, ProductCreate

qdrant = QdrantClient(f"http://{env.QDRANT_HOST}:{env.QDRANT_PORT}")
class QSearch:
    @staticmethod
    def search( payload, collection_name = "product_name_embeddings", limit=5):
        # Tìm kiếm ANN trong collection
        query_Vector = query_embedding(payload)  
        search_result = qdrant.query_points(
            collection_name=collection_name,
            query= query_Vector,
            using="default",
            limit=limit,    
            with_payload=False,
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



def search():
    return ""
