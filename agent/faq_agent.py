"""
FAQ Agent - Xử lý tìm kiếm và trả lời FAQ với threshold checking

Logic:
1. User query → Generate embedding
2. Search trong Qdrant collection "faqs"
3. Check score >= threshold (default 0.85)
4. Nếu matched → Return FAQ answer trực tiếp
5. Nếu không match → Return None (trigger fallback)

Features:
- Smart threshold-based matching
- User-specific FAQ filtering
- Priority-based ranking
- Fallback support cho chat pipeline
"""

from typing import Optional, Dict, Any, List
import uuid
from embedding.search import faq_semantic_search
from env import env


class FAQAgent:
    """
    FAQ Agent xử lý tìm kiếm và matching FAQs
    """
    
    def __init__(self, threshold: float = 0.85):
        """
        Initialize FAQ Agent
        
        Args:
            threshold: Ngưỡng score tối thiểu để match (0.0 - 1.0)
                      Default: 0.85 (85% similarity)
        """
        self.threshold = threshold
        self.top_k = 3  # Lấy top 3 FAQs có score cao nhất
    
    def search_faq(
        self, 
        query: str, 
        user_id: uuid.UUID,
        threshold: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Tìm kiếm FAQ matching với query
        
        Args:
            query: Câu hỏi của user
            user_id: User ID để filter FAQs
            threshold: Override threshold (optional)
            
        Returns:
            Dict với FAQ info nếu match, None nếu không match:
            {
                "faq_id": str,
                "question": str,
                "answer": str,
                "score": float,
                "category": str,
                "matched": bool
            }
        """
        # Use provided threshold or default
        search_threshold = threshold if threshold is not None else self.threshold
        
        print(f"🔍 FAQ Agent searching for: '{query}'")
        print(f"   User: {user_id}, Threshold: {search_threshold}")
        
        # Tìm kiếm trong Qdrant
        results = faq_semantic_search(
            query=query,
            user_id=str(user_id),
            top_k=self.top_k,
            threshold=search_threshold
        )
        
        # Nếu không có kết quả
        if not results:
            print(f"❌ No FAQ found matching threshold {search_threshold}")
            return None
        
        # Lấy FAQ có score cao nhất
        best_match = results[0]
        
        # Check nếu score >= threshold
        if best_match["score"] >= search_threshold:
            print(f"✅ FAQ MATCHED!")
            print(f"   Score: {best_match['score']:.3f}")
            print(f"   Question: {best_match['question'][:100]}...")
            print(f"   Answer: {best_match['answer'][:100]}...")
            
            return {
                "faq_id": best_match["faq_id"],
                "question": best_match["question"],
                "answer": best_match["answer"],
                "score": best_match["score"],
                "category": best_match["category"],
                "matched": True
            }
        else:
            print(f"⚠️  Best FAQ score ({best_match['score']:.3f}) below threshold ({search_threshold})")
            return None
    
    def process_with_fallback(
        self,
        query: str,
        user_id: uuid.UUID,
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Xử lý query với fallback logic
        
        Args:
            query: Câu hỏi của user
            user_id: User ID
            threshold: Override threshold (optional)
            
        Returns:
            Dict với:
            {
                "matched": bool,
                "answer": str (nếu matched),
                "score": float (nếu matched),
                "faq_id": str (nếu matched),
                "fallback": bool (True nếu cần fallback)
            }
        """
        result = self.search_faq(query, user_id, threshold)
        
        if result and result["matched"]:
            # FAQ matched - return answer
            return {
                "matched": True,
                "answer": result["answer"],
                "score": result["score"],
                "faq_id": result["faq_id"],
                "question": result["question"],
                "category": result["category"],
                "fallback": False
            }
        else:
            # No match - trigger fallback
            return {
                "matched": False,
                "fallback": True,
                "message": "No FAQ matched, fallback to normal flow"
            }
    
    def get_all_matches(
        self,
        query: str,
        user_id: uuid.UUID,
        threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Lấy tất cả FAQs matching (không chỉ best match)
        Hữu ích cho UI hiển thị multiple suggestions
        
        Args:
            query: Câu hỏi của user
            user_id: User ID
            threshold: Override threshold (optional)
            
        Returns:
            List of matched FAQs, sorted by score desc
        """
        search_threshold = threshold if threshold is not None else self.threshold
        
        results = faq_semantic_search(
            query=query,
            user_id=str(user_id),
            top_k=5,  # Lấy nhiều hơn để có options
            threshold=search_threshold
        )
        
        # Filter chỉ lấy matched items
        matched_faqs = [r for r in results if r["score"] >= search_threshold]
        
        print(f"📋 Found {len(matched_faqs)} matched FAQs (threshold: {search_threshold})")
        
        return matched_faqs
    
    def test_match(
        self,
        query: str,
        user_id: uuid.UUID,
        show_scores: bool = True
    ) -> None:
        """
        Test function để xem scores của các FAQs
        Hữu ích để điều chỉnh threshold
        
        Args:
            query: Câu hỏi test
            user_id: User ID
            show_scores: Hiển thị scores (default True)
        """
        print(f"\n{'='*60}")
        print(f"FAQ MATCHING TEST")
        print(f"{'='*60}")
        print(f"Query: {query}")
        print(f"User ID: {user_id}")
        print(f"Threshold: {self.threshold}")
        print(f"{'='*60}\n")
        
        # Search without threshold để xem all results
        results = faq_semantic_search(
            query=query,
            user_id=str(user_id),
            top_k=self.top_k,
            threshold=0.0  # No threshold for testing
        )
        
        if not results:
            print("❌ No FAQs found for this user")
            return
        
        print(f"📊 Top {len(results)} Results:\n")
        
        for i, faq in enumerate(results, 1):
            score = faq["score"]
            matched = "✅ MATCHED" if score >= self.threshold else "❌ Below threshold"
            
            print(f"{i}. Score: {score:.4f} {matched}")
            print(f"   Question: {faq['question'][:80]}...")
            if show_scores:
                print(f"   Answer: {faq['answer'][:80]}...")
            print()


# Convenience function cho chat pipeline
def check_faq_match(
    query: str,
    user_id: uuid.UUID,
    threshold: float = 0.85
) -> Optional[Dict[str, Any]]:
    """
    Quick function để check FAQ match trong chat pipeline
    
    Args:
        query: User query
        user_id: User ID
        threshold: Matching threshold (default 0.85)
        
    Returns:
        FAQ result dict nếu match, None nếu không
    """
    agent = FAQAgent(threshold=threshold)
    return agent.search_faq(query, user_id, threshold)
