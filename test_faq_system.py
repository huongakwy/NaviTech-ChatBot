"""
Test script để verify FAQ system

Run: source venv/bin/activate && python test_faq_system.py
"""

import sys
sys.path.append('.')

print("Testing imports...")

try:
    from models.faq import FAQTable, FAQModel, FAQCreateModel
    print("✓ models.faq imported")
except Exception as e:
    print(f"✗ models.faq error: {e}")
    sys.exit(1)

try:
    from repositories.faq import FAQRepository
    print("✓ repositories.faq imported")
except Exception as e:
    print(f"✗ repositories.faq error: {e}")
    sys.exit(1)

try:
    from services.faq import FAQService
    print("✓ services.faq imported")
except Exception as e:
    print(f"✗ services.faq error: {e}")
    sys.exit(1)

try:
    from embedding.faq_embedding import FAQEmbedding, get_faq_embedding
    print("✓ embedding.faq_embedding imported")
except Exception as e:
    print(f"✗ embedding.faq_embedding error: {e}")
    sys.exit(1)

try:
    from embedding.search import faq_semantic_search
    print("✓ embedding.search.faq_semantic_search imported")
except Exception as e:
    print(f"✗ embedding.search error: {e}")
    sys.exit(1)

try:
    from agent.faq_agent import FAQAgent, check_faq_match
    print("✓ agent.faq_agent imported")
except Exception as e:
    print(f"✗ agent.faq_agent error: {e}")
    sys.exit(1)

try:
    from controllers.faq import router
    print("✓ controllers.faq imported")
except Exception as e:
    print(f"✗ controllers.faq error: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("SUCCESS: All FAQ modules imported successfully!")
print("="*60)

print("\nTesting Qdrant collection creation...")
try:
    faq_emb = get_faq_embedding()
    result = faq_emb.ensure_collection_exists()
    if result:
        print("✓ Qdrant FAQ collection created/verified")
    else:
        print("✗ Failed to create Qdrant collection")
except Exception as e:
    print(f"✗ Qdrant error: {e}")

print("\nFAQ System is ready to use!")
print("\nNext steps:")
print("1. Run sample FAQ creation: python scripts/create_sample_faqs.py [user_id]")
print("2. Start the API server: uvicorn app:app --reload")
print("3. Test FAQ endpoints: http://localhost:8000/docs")
