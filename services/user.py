import uuid
from typing import Optional
from sqlalchemy.orm import Session
from models.user import UserCreateModel
from repositories.user import UserRespository
from services.ai_personality import AIPersonalityService

class UserService():
    @staticmethod
    def create_user(payload: UserCreateModel):
        return UserRespository.create(payload)
    
    @staticmethod
    def get_user(payload: uuid.UUID):
        return UserRespository.get(payload)
    
    @staticmethod
    def update_user(id: uuid.UUID, data: UserCreateModel):
        return UserRespository.update(id = id, data = data)
    
    @staticmethod
    def delete_user(payload: uuid.UUID):
        return UserRespository.delete(payload)
    
    @staticmethod
    def get_all_user():
        return UserRespository.get_all_user()
    
    @staticmethod
    def set_user_personality(session: Session, user_id: uuid.UUID, personality_name: str) -> Optional[dict]:
        """Set user's AI personality"""
        # Get personality by name
        personality = AIPersonalityService.get_personality_by_name(session, personality_name)
        if not personality:
            return None
        
        # Get user from database using the same session
        from models.user import UserTable
        user = session.query(UserTable).filter(UserTable.id == user_id).first()
        if not user:
            return None
        
        # Update user with personality_id in the same session
        user.ai_personality_id = personality.id
        session.add(user)
        session.commit()
        session.refresh(user)
        
        return {
            "user_id": str(user_id),
            "personality_id": personality.id,
            "personality_name": personality_name,
            "personality_description": personality.description
        }
    
    @staticmethod
    def get_user_personality(user_id: uuid.UUID) -> Optional[dict]:
        """Get user's current personality"""
        user = UserRespository.get(user_id)
        if not user or not user.ai_personality_id:
            return None
        
        return {
            "user_id": str(user_id),
            "personality_id": user.ai_personality_id,
            "personality_name": user.ai_personality.name if user.ai_personality else None,
            "personality_description": user.ai_personality.description if user.ai_personality else None
        }