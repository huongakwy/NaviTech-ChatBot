"""
FAQ Repository - Data access layer cho FAQs
"""

from typing import List, Optional
import uuid
from sqlalchemy.orm import Session
from models.faq import FAQTable, FAQCreateModel, FAQUpdateModel


class FAQRepository:
    """Repository pattern cho FAQ operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, faq_data: FAQCreateModel) -> FAQTable:
        """Tạo FAQ mới"""
        faq = FAQTable(
            id=uuid.uuid4(),
            user_id=faq_data.user_id,
            question=faq_data.question,
            answer=faq_data.answer,
            category=faq_data.category,
            priority=faq_data.priority,
            is_active=faq_data.is_active
        )
        self.db.add(faq)
        self.db.commit()
        self.db.refresh(faq)
        return faq
    
    def get_by_id(self, faq_id: uuid.UUID) -> Optional[FAQTable]:
        """Lấy FAQ theo ID"""
        return self.db.query(FAQTable).filter(FAQTable.id == faq_id).first()
    
    def get_all(
        self, 
        user_id: Optional[uuid.UUID] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[FAQTable]:
        """Lấy danh sách FAQs với filters"""
        query = self.db.query(FAQTable)
        
        if user_id:
            query = query.filter(FAQTable.user_id == user_id)
        
        if category:
            query = query.filter(FAQTable.category == category)
        
        if is_active is not None:
            query = query.filter(FAQTable.is_active == is_active)
        
        # Order by priority (cao nhất trước) và created_at
        query = query.order_by(FAQTable.priority.desc(), FAQTable.created_at.desc())
        
        return query.limit(limit).offset(offset).all()
    
    def update(self, faq_id: uuid.UUID, faq_data: FAQUpdateModel) -> Optional[FAQTable]:
        """Update FAQ"""
        faq = self.get_by_id(faq_id)
        if not faq:
            return None
        
        # Update only provided fields
        update_data = faq_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(faq, key, value)
        
        self.db.commit()
        self.db.refresh(faq)
        return faq
    
    def delete(self, faq_id: uuid.UUID) -> bool:
        """Xóa FAQ (hard delete)"""
        faq = self.get_by_id(faq_id)
        if not faq:
            return False
        
        self.db.delete(faq)
        self.db.commit()
        return True
    
    def soft_delete(self, faq_id: uuid.UUID) -> Optional[FAQTable]:
        """Soft delete - set is_active = False"""
        faq = self.get_by_id(faq_id)
        if not faq:
            return None
        
        faq.is_active = False
        self.db.commit()
        self.db.refresh(faq)
        return faq
    
    def count(
        self,
        user_id: Optional[uuid.UUID] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> int:
        """Đếm số lượng FAQs"""
        query = self.db.query(FAQTable)
        
        if user_id:
            query = query.filter(FAQTable.user_id == user_id)
        
        if category:
            query = query.filter(FAQTable.category == category)
        
        if is_active is not None:
            query = query.filter(FAQTable.is_active == is_active)
        
        return query.count()
    
    def get_categories(self, user_id: uuid.UUID) -> List[str]:
        """Lấy danh sách categories của user"""
        results = self.db.query(FAQTable.category)\
            .filter(FAQTable.user_id == user_id)\
            .filter(FAQTable.category.isnot(None))\
            .distinct()\
            .all()
        
        return [r[0] for r in results if r[0]]
