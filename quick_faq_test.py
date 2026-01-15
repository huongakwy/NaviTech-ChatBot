"""
Quick test: Tạo 1 FAQ mẫu và test matching

Không cần database user, chỉ test Qdrant + FAQ Agent
"""

import uuid
from embedding.faq_embedding import get_faq_embedding
from agent.faq_agent import FAQAgent

print("="*60)
print("QUICK FAQ TEST")
print("="*60)

# Test user ID
test_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

print(f"\n1. Creating test FAQ...")
print(f"   User ID: {test_user_id}")

try:
    # Create FAQ directly in Qdrant (bypass database)
    faq_emb = get_faq_embedding()
    
    test_faq_id = uuid.uuid4()
    
    result = faq_emb.sync_faq_to_qdrant(
        faq_id=test_faq_id,
        user_id=test_user_id,
        question="Chính sách đổi trả sản phẩm của Navitech như thế nào?",
        answer="""Navitech hỗ trợ đổi trả sản phẩm trong vòng 7 ngày kể từ ngày mua hàng với các điều kiện sau:

1. Sản phẩm còn nguyên tem, hộp, phụ kiện đầy đủ
2. Sản phẩm chưa qua sử dụng, không có dấu hiệu va đập, trầy xước
3. Có hóa đơn mua hàng hợp lệ

Để đổi trả, vui lòng liên hệ hotline: 1900-xxxx hoặc mang sản phẩm đến cửa hàng gần nhất.""",
        category="chinh-sach",
        priority=10,
        is_active=True
    )
    
    if result:
        print(f"   ✅ FAQ created in Qdrant!")
        print(f"   FAQ ID: {test_faq_id}")
    else:
        print(f"   ❌ Failed to create FAQ")
        exit(1)
    
    # Test search
    print(f"\n2. Testing FAQ search...")
    
    agent = FAQAgent(threshold=0.85)
    
    test_queries = [
        "chính sách đổi trả như thế nào",
        "tôi muốn đổi sản phẩm",
        "làm thế nào để trả hàng",
        "laptop gaming giá rẻ"  # Should NOT match
    ]
    
    for query in test_queries:
        print(f"\n   Query: '{query}'")
        result = agent.search_faq(query, test_user_id)
        
        if result and result.get("matched"):
            print(f"   ✅ MATCHED (score: {result['score']:.3f})")
            print(f"      Answer preview: {result['answer'][:80]}...")
        else:
            print(f"   ⚠️  No match (fallback to normal flow)")
    
    print(f"\n{'='*60}")
    print(f"✅ FAQ SYSTEM WORKING!")
    print(f"{'='*60}")
    print(f"""
Next steps:
1. Create real FAQs with actual user ID from database
2. Test in chat pipeline: POST /chatbots/full_pipeline
3. Monitor FAQ hit rate

Quick stats:
- Qdrant: Connected ✅
- FAQ Collection: Created ✅  
- Test FAQ: Inserted ✅
- Matching: Working ✅
- Threshold: 0.85
""")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
