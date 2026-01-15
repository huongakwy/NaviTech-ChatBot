"""
Test FAQ matching với different thresholds
"""

import uuid
from agent.faq_agent import FAQAgent

test_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

print("="*60)
print("FAQ THRESHOLD TESTING")
print("="*60)

test_query = "chính sách đổi trả như thế nào"

thresholds = [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]

print(f"\nQuery: '{test_query}'")
print(f"\nTesting different thresholds:\n")

for threshold in thresholds:
    agent = FAQAgent(threshold=threshold)
    result = agent.search_faq(test_query, test_user_id)
    
    if result and result.get("matched"):
        print(f"✅ Threshold {threshold:.2f}: MATCHED (score: {result['score']:.3f})")
    else:
        if result:
            print(f"⚠️  Threshold {threshold:.2f}: No match (best score: {result.get('score', 0):.3f})")
        else:
            print(f"❌ Threshold {threshold:.2f}: No results")

print(f"\n{'='*60}")
print("RECOMMENDATION")
print("="*60)
print("""
Based on the scores above, recommended thresholds:

- 0.70-0.75: Good balance (not too strict, not too loose)
- 0.65-0.70: More flexible, may match more variations
- 0.75-0.80: Stricter, more precise matches

For production, suggest: 0.70 or 0.72
""")
