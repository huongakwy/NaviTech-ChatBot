"""AI Personality Repository - Database CRUD operations"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from models.ai_personality import AIPersonalityTable, AIPersonalityModel


class AIPersonalityRepository:
    """Repository for managing AI personality types"""
    
    @staticmethod
    def get_all(session: Session) -> List[AIPersonalityTable]:
        """Get all personality types"""
        return session.execute(select(AIPersonalityTable)).scalars().all()
    
    @staticmethod
    def get_by_id(session: Session, personality_id: int) -> Optional[AIPersonalityTable]:
        """Get personality by ID"""
        return session.execute(
            select(AIPersonalityTable).where(AIPersonalityTable.id == personality_id)
        ).scalars().first()
    
    @staticmethod
    def get_by_name(session: Session, name: str) -> Optional[AIPersonalityTable]:
        """Get personality by name"""
        return session.execute(
            select(AIPersonalityTable).where(AIPersonalityTable.name == name)
        ).scalars().first()
    
    @staticmethod
    def create(session: Session, name: str, description: str, company_name: str = "NAVITECH", agent_name: str = "trợ lý AI") -> AIPersonalityTable:
        """Create new personality"""
        personality = AIPersonalityTable(
            name=name, 
            description=description,
            company_name=company_name,
            agent_name=agent_name
        )
        session.add(personality)
        session.commit()
        session.refresh(personality)
        return personality
    
    @staticmethod
    def update(session: Session, personality_id: int, name: Optional[str] = None, description: Optional[str] = None, company_name: Optional[str] = None, agent_name: Optional[str] = None) -> Optional[AIPersonalityTable]:
        """Update personality"""
        personality = AIPersonalityRepository.get_by_id(session, personality_id)
        if not personality:
            return None
        
        if name:
            personality.name = name
        if description:
            personality.description = description
        if company_name:
            personality.company_name = company_name
        if agent_name:
            personality.agent_name = agent_name
        
        session.commit()
        session.refresh(personality)
        return personality
    
    @staticmethod
    def delete(session: Session, personality_id: int) -> bool:
        """Delete personality"""
        personality = AIPersonalityRepository.get_by_id(session, personality_id)
        if not personality:
            return False
        
        session.delete(personality)
        session.commit()
        return True
