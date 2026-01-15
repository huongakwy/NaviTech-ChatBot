"""
FAQ Service - Business logic cho FAQ operations
"""

from typing import List, Optional
import uuid
from sqlalchemy.orm import Session
from repositories.faq import FAQRepository
from models.faq import FAQModel, FAQCreateModel, FAQUpdateModel, FAQTable


class FAQService:
    """Service layer cho FAQ business logic"""
    
    def __init__(self, db: Session):
        self.db = db
        self.repository = FAQRepository(db)
    
    def create_faq(self, faq_data: FAQCreateModel) -> FAQModel:
        """
        Tạo FAQ mới
        
        Args:
            faq_data: Dữ liệu FAQ
            
        Returns:
            FAQModel instance
        """
        faq = self.repository.create(faq_data)
        return FAQModel.model_validate(faq)
    
    def get_faq(self, faq_id: uuid.UUID) -> Optional[FAQModel]:
        """Lấy FAQ theo ID"""
        faq = self.repository.get_by_id(faq_id)
        if not faq:
            return None
        return FAQModel.model_validate(faq)
    
    def list_faqs(
        self,
        user_id: Optional[uuid.UUID] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = True,  # Default chỉ lấy active
        limit: int = 100,
        offset: int = 0
    ) -> List[FAQModel]:
        """
        Lấy danh sách FAQs
        
        Args:
            user_id: Filter by user (optional)
            category: Filter by category (optional)
            is_active: Filter by active status (default True)
            limit: Max số lượng trả về
            offset: Offset cho pagination
            
        Returns:
            List of FAQModel
        """
        faqs = self.repository.get_all(
            user_id=user_id,
            category=category,
            is_active=is_active,
            limit=limit,
            offset=offset
        )
        return [FAQModel.model_validate(faq) for faq in faqs]
    
    def update_faq(
        self, 
        faq_id: uuid.UUID, 
        faq_data: FAQUpdateModel
    ) -> Optional[FAQModel]:
        """
        Update FAQ
        
        Args:
            faq_id: FAQ ID
            faq_data: Dữ liệu update
            
        Returns:
            Updated FAQModel hoặc None nếu không tìm thấy
        """
        faq = self.repository.update(faq_id, faq_data)
        if not faq:
            return None
        return FAQModel.model_validate(faq)
    
    def delete_faq(self, faq_id: uuid.UUID, soft: bool = True) -> bool:
        """
        Xóa FAQ
        
        Args:
            faq_id: FAQ ID
            soft: True = soft delete (set is_active=False), False = hard delete
            
        Returns:
            True nếu xóa thành công
        """
        if soft:
            faq = self.repository.soft_delete(faq_id)
            return faq is not None
        else:
            return self.repository.delete(faq_id)
    
    def get_statistics(self, user_id: uuid.UUID) -> dict:
        """
        Lấy thống kê FAQs của user
        
        Returns:
            Dictionary với stats
        """
        total = self.repository.count(user_id=user_id)
        active = self.repository.count(user_id=user_id, is_active=True)
        inactive = total - active
        categories = self.repository.get_categories(user_id)
        
        return {
            "total": total,
            "active": active,
            "inactive": inactive,
            "categories": categories,
            "category_count": len(categories)
        }
    
    def bulk_create(self, faqs_data: List[FAQCreateModel]) -> List[FAQModel]:
        """
        Tạo nhiều FAQs cùng lúc
        
        Args:
            faqs_data: List of FAQCreateModel
            
        Returns:
            List of created FAQModel
        """
        created_faqs = []
        for faq_data in faqs_data:
            faq = self.repository.create(faq_data)
            created_faqs.append(FAQModel.model_validate(faq))
        
        return created_faqs
    
    def activate_faq(self, faq_id: uuid.UUID) -> Optional[FAQModel]:
        """Activate một FAQ"""
        update_data = FAQUpdateModel(is_active=True)
        return self.update_faq(faq_id, update_data)
    
    def deactivate_faq(self, faq_id: uuid.UUID) -> Optional[FAQModel]:
        """Deactivate một FAQ"""
        update_data = FAQUpdateModel(is_active=False)
        return self.update_faq(faq_id, update_data)
