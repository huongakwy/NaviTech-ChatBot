import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance

from env import env

qdrant = QdrantClient(f"http://localhost:{env.QDRANT_PORT}")

def ensure_collection_exists(USER_ID: str):
    collections = qdrant.get_collections().collections
    collection_names = [col.name for col in collections]

    if USER_ID not in collection_names:
        qdrant.create_collection(
            collection_name=USER_ID,
            vectors_config={"default": VectorParams(size=env.LEN_EMBEDDING, distance=Distance.COSINE)},
            on_disk_payload=False  
        )

        print(f"✅ Đã tạo collection '{USER_ID}'.")
    else:
        print(f"ℹ️ Collection '{USER_ID}' đã tồn tại.")



def insert_products_to_qdrant(embedding: list,  payload: dict, USER_ID: str):
    if embedding:
        point = PointStruct(
            id =  payload.get("id"),
            vector={"default": embedding},
            payload={
                "title": payload.get("title"),
                "description": payload.get("description"),
            }
        )
        qdrant.upsert(collection_name=USER_ID, points=[point])
        print(f"✅ Đã chèn dữ liệu vào collection '{payload.get("id")}'.")


def ensure_product_collection_exists(COLLECTION_NAME: str = "products"):
    collections = qdrant.get_collections().collections
    collection_names = [col.name for col in collections]

    if COLLECTION_NAME not in collection_names:
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config={"default": VectorParams(size=env.LEN_EMBEDDING, distance=Distance.COSINE)},
            on_disk_payload=False  
        )

        print(f"✅ Đã tạo collection '{COLLECTION_NAME}'.")
    else:
        print(f"ℹ️ Collection '{COLLECTION_NAME}' đã tồn tại.")



def insert_products_to_qdrant_product(embedding: list,  payload: dict, USER_ID: str, COLLECTION_NAME: str = "products"):
    if embedding:
        point = PointStruct(
            id =  payload.get("id"),
            vector={"default": embedding},
            payload={
                "user_id": USER_ID,
                "title": payload.get("title"),
                "description": payload.get("description"),
            }
        )
        qdrant.upsert(collection_name=COLLECTION_NAME, points=[point])
        print(f"✅ Đã chèn dữ liệu vào collection '{payload.get("id")}'.")