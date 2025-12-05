"""AI Personality Service - Business logic for personality management"""

from typing import List, Optional
from sqlalchemy.orm import Session
from models.ai_personality import AIPersonalityModel, AIPersonalityCreateModel, AIPersonalityUpdateModel
from repositories.ai_personality import AIPersonalityRepository


class AIPersonalityService:
    """Service for managing AI personality types"""
    
    @staticmethod
    def get_all_personalities(session: Session) -> List[AIPersonalityModel]:
        """Get all available personalities"""
        personalities = AIPersonalityRepository.get_all(session)
        return [AIPersonalityModel.from_orm(p) if hasattr(AIPersonalityModel, 'from_orm') else AIPersonalityModel.model_validate(p) for p in personalities]
    
    @staticmethod
    def get_personality(session: Session, personality_id: int) -> Optional[AIPersonalityModel]:
        """Get personality by ID"""
        personality = AIPersonalityRepository.get_by_id(session, personality_id)
        if not personality:
            return None
        return AIPersonalityModel.model_validate(personality)
    
    @staticmethod
    def get_personality_by_name(session: Session, name: str) -> Optional[AIPersonalityModel]:
        """Get personality by name"""
        personality = AIPersonalityRepository.get_by_name(session, name)
        if not personality:
            return None
        return AIPersonalityModel.model_validate(personality)
    
    @staticmethod
    def create_personality(session: Session, create_data: AIPersonalityCreateModel) -> AIPersonalityModel:
        """Create new personality"""
        personality = AIPersonalityRepository.create(
            session,
            name=create_data.name,
            description=create_data.description
        )
        return AIPersonalityModel.model_validate(personality)
    
    @staticmethod
    def update_personality(session: Session, personality_id: int, update_data: AIPersonalityUpdateModel) -> Optional[AIPersonalityModel]:
        """Update personality"""
        personality = AIPersonalityRepository.update(
            session,
            personality_id,
            name=update_data.name,
            description=update_data.description
        )
        if not personality:
            return None
        return AIPersonalityModel.model_validate(personality)
    
    @staticmethod
    def delete_personality(session: Session, personality_id: int) -> bool:
        """Delete personality"""
        return AIPersonalityRepository.delete(session, personality_id)
    
    @staticmethod
    def get_default_personality_id(session: Session) -> Optional[int]:
        """Get default personality ID (bình_thường)"""
        personality = AIPersonalityRepository.get_by_name(session, "bình_thường")
        return personality.id if personality else None
