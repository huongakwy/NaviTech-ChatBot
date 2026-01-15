"""Test Qdrant connection"""
from qdrant_client import QdrantClient
from env import env

print(f"Connecting to Qdrant at http://{env.QDRANT_HOST}:{env.QDRANT_PORT}...")

try:
    client = QdrantClient(f"http://{env.QDRANT_HOST}:{env.QDRANT_PORT}")
    collections = client.get_collections()
    
    print("✅ Connected to Qdrant successfully!")
    print(f"\n📦 Existing collections ({len(collections.collections)}):")
    
    for c in collections.collections:
        print(f"  - {c.name}")
    
    # Check if FAQs collection exists
    collection_names = [c.name for c in collections.collections]
    
    if "faqs" in collection_names:
        print("\n✅ 'faqs' collection already exists!")
        # Get collection info
        info = client.get_collection("faqs")
        print(f"   Vectors count: {info.vectors_count}")
        print(f"   Points count: {info.points_count}")
    else:
        print("\n⚠️  'faqs' collection does not exist yet")
        print("   Will be created when first FAQ is added")
    
    print("\n🚀 Qdrant is ready for FAQ system!")
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
    import traceback
    traceback.print_exc()
