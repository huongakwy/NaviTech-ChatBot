"""
FAQ Controller - API endpoints để quản lý FAQs

Endpoints:
- POST /api/faqs - Tạo FAQ mới
- GET /api/faqs - List FAQs với filters
- GET /api/faqs/{faq_id} - Chi tiết FAQ
- PUT /api/faqs/{faq_id} - Update FAQ
- DELETE /api/faqs/{faq_id} - Xóa FAQ
- POST /api/faqs/bulk - Upload nhiều FAQs
- POST /api/faqs/{faq_id}/sync - Sync embedding vào Qdrant
- POST /api/faqs/test-match - Test FAQ matching
- GET /api/faqs/stats/{user_id} - Thống kê FAQs
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from db import get_db
from models.faq import (
    FAQModel, 
    FAQCreateModel, 
    FAQUpdateModel,
    FAQSearchResult
)
from services.faq import FAQService
from embedding.faq_embedding import get_faq_embedding
from agent.faq_agent import FAQAgent

router = APIRouter(prefix="/api/faqs", tags=["FAQ Management"])


@router.post("/", response_model=FAQModel, status_code=201)
async def create_faq(
    faq_data: FAQCreateModel,
    sync_to_qdrant: bool = Query(True, description="Auto sync to Qdrant"),
    db: Session = Depends(get_db)
):
    """
    Tạo FAQ mới
    
    Args:
        faq_data: Dữ liệu FAQ
        sync_to_qdrant: Tự động sync vào Qdrant (default: True)
    
    Returns:
        Created FAQ
    """
    try:
        service = FAQService(db)
        faq = service.create_faq(faq_data)
        
        # Sync to Qdrant nếu enabled
        if sync_to_qdrant:
            faq_emb = get_faq_embedding()
            success = faq_emb.sync_faq_to_qdrant(
                faq_id=faq.id,
                user_id=faq.user_id,
                question=faq.question,
                answer=faq.answer,
                category=faq.category,
                priority=faq.priority,
                is_active=faq.is_active
            )
            
            if not success:
                print(f"⚠️  FAQ created but failed to sync to Qdrant")
        
        return faq
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating FAQ: {str(e)}")


@router.get("/", response_model=List[FAQModel])
async def list_faqs(
    user_id: Optional[uuid.UUID] = Query(None, description="Filter by user ID"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách FAQs với filters
    
    Returns:
        List of FAQs
    """
    try:
        service = FAQService(db)
        faqs = service.list_faqs(
            user_id=user_id,
            category=category,
            is_active=is_active,
            limit=limit,
            offset=offset
        )
        return faqs
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing FAQs: {str(e)}")


@router.get("/{faq_id}", response_model=FAQModel)
async def get_faq(
    faq_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Lấy chi tiết một FAQ
    
    Args:
        faq_id: FAQ ID
        
    Returns:
        FAQ details
    """
    try:
        service = FAQService(db)
        faq = service.get_faq(faq_id)
        
        if not faq:
            raise HTTPException(status_code=404, detail="FAQ not found")
        
        return faq
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting FAQ: {str(e)}")


@router.put("/{faq_id}", response_model=FAQModel)
async def update_faq(
    faq_id: uuid.UUID,
    faq_data: FAQUpdateModel,
    sync_to_qdrant: bool = Query(True, description="Auto sync to Qdrant"),
    db: Session = Depends(get_db)
):
    """
    Update FAQ
    
    Args:
        faq_id: FAQ ID
        faq_data: Update data
        sync_to_qdrant: Auto sync to Qdrant (default: True)
        
    Returns:
        Updated FAQ
    """
    try:
        service = FAQService(db)
        faq = service.update_faq(faq_id, faq_data)
        
        if not faq:
            raise HTTPException(status_code=404, detail="FAQ not found")
        
        # Re-sync to Qdrant nếu enabled
        if sync_to_qdrant:
            faq_emb = get_faq_embedding()
            faq_emb.sync_faq_to_qdrant(
                faq_id=faq.id,
                user_id=faq.user_id,
                question=faq.question,
                answer=faq.answer,
                category=faq.category,
                priority=faq.priority,
                is_active=faq.is_active
            )
        
        return faq
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating FAQ: {str(e)}")


@router.delete("/{faq_id}")
async def delete_faq(
    faq_id: uuid.UUID,
    soft: bool = Query(True, description="Soft delete (set is_active=False)"),
    delete_from_qdrant: bool = Query(True, description="Also delete from Qdrant"),
    db: Session = Depends(get_db)
):
    """
    Xóa FAQ
    
    Args:
        faq_id: FAQ ID
        soft: Soft delete (default: True)
        delete_from_qdrant: Also delete from Qdrant (default: True)
        
    Returns:
        Success message
    """
    try:
        service = FAQService(db)
        success = service.delete_faq(faq_id, soft=soft)
        
        if not success:
            raise HTTPException(status_code=404, detail="FAQ not found")
        
        # Delete from Qdrant nếu enabled
        if delete_from_qdrant and not soft:  # Chỉ xóa khỏi Qdrant nếu hard delete
            faq_emb = get_faq_embedding()
            faq_emb.delete_faq_from_qdrant(faq_id)
        
        return {
            "success": True,
            "message": f"FAQ {'deactivated' if soft else 'deleted'} successfully",
            "faq_id": str(faq_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting FAQ: {str(e)}")


@router.post("/bulk", response_model=List[FAQModel])
async def bulk_create_faqs(
    faqs_data: List[FAQCreateModel],
    sync_to_qdrant: bool = Query(True, description="Auto sync to Qdrant"),
    db: Session = Depends(get_db)
):
    """
    Tạo nhiều FAQs cùng lúc
    
    Args:
        faqs_data: List of FAQ data
        sync_to_qdrant: Auto sync to Qdrant (default: True)
        
    Returns:
        List of created FAQs
    """
    try:
        service = FAQService(db)
        faqs = service.bulk_create(faqs_data)
        
        # Sync to Qdrant nếu enabled
        if sync_to_qdrant and faqs:
            faq_emb = get_faq_embedding()
            sync_data = [
                {
                    "faq_id": faq.id,
                    "user_id": faq.user_id,
                    "question": faq.question,
                    "answer": faq.answer,
                    "category": faq.category,
                    "priority": faq.priority,
                    "is_active": faq.is_active
                }
                for faq in faqs
            ]
            faq_emb.bulk_sync_faqs(sync_data)
        
        return faqs
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error bulk creating FAQs: {str(e)}")


@router.post("/{faq_id}/sync")
async def sync_faq_to_qdrant(
    faq_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Đồng bộ một FAQ vào Qdrant
    
    Args:
        faq_id: FAQ ID
        
    Returns:
        Success message
    """
    try:
        service = FAQService(db)
        faq = service.get_faq(faq_id)
        
        if not faq:
            raise HTTPException(status_code=404, detail="FAQ not found")
        
        faq_emb = get_faq_embedding()
        success = faq_emb.sync_faq_to_qdrant(
            faq_id=faq.id,
            user_id=faq.user_id,
            question=faq.question,
            answer=faq.answer,
            category=faq.category,
            priority=faq.priority,
            is_active=faq.is_active
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to sync to Qdrant")
        
        return {
            "success": True,
            "message": "FAQ synced to Qdrant successfully",
            "faq_id": str(faq_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error syncing FAQ: {str(e)}")


@router.post("/test-match")
async def test_faq_match(
    query: str = Query(..., description="Test query"),
    user_id: uuid.UUID = Query(..., description="User ID"),
    threshold: float = Query(0.85, ge=0.0, le=1.0, description="Match threshold")
):
    """
    Test FAQ matching với query
    Hữu ích để debug và điều chỉnh threshold
    
    Args:
        query: Query để test
        user_id: User ID
        threshold: Matching threshold
        
    Returns:
        Matching results với scores
    """
    try:
        agent = FAQAgent(threshold=threshold)
        
        # Get all matches (không chỉ best match)
        matches = agent.get_all_matches(query, user_id, threshold)
        
        return {
            "query": query,
            "user_id": str(user_id),
            "threshold": threshold,
            "total_matches": len(matches),
            "matches": matches
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing FAQ match: {str(e)}")


@router.get("/stats/{user_id}")
async def get_faq_stats(
    user_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Lấy thống kê FAQs của user
    
    Args:
        user_id: User ID
        
    Returns:
        Statistics
    """
    try:
        service = FAQService(db)
        stats = service.get_statistics(user_id)
        
        return {
            "user_id": str(user_id),
            "statistics": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")


@router.post("/{faq_id}/activate")
async def activate_faq(
    faq_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Activate một FAQ"""
    try:
        service = FAQService(db)
        faq = service.activate_faq(faq_id)
        
        if not faq:
            raise HTTPException(status_code=404, detail="FAQ not found")
        
        return {"success": True, "message": "FAQ activated", "faq": faq}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error activating FAQ: {str(e)}")


@router.post("/{faq_id}/deactivate")
async def deactivate_faq(
    faq_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Deactivate một FAQ"""
    try:
        service = FAQService(db)
        faq = service.deactivate_faq(faq_id)
        
        if not faq:
            raise HTTPException(status_code=404, detail="FAQ not found")
        
        return {"success": True, "message": "FAQ deactivated", "faq": faq}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deactivating FAQ: {str(e)}")
