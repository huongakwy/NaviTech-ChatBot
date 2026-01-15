"""Create FAQ collection in Qdrant"""
from embedding.faq_embedding import get_faq_embedding

print("Creating FAQ collection in Qdrant...")

try:
    faq_emb = get_faq_embedding()
    result = faq_emb.ensure_collection_exists()
    
    if result:
        print("✅ FAQ collection created successfully!")
    else:
        print("❌ Failed to create collection")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
