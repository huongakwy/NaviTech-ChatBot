"""AI Personality Controller"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid
from db import get_db
from services.ai_personality import AIPersonalityService
from services.user import UserService

router = APIRouter(prefix="/api/personality", tags=["personality"])

class SetPersonalityRequest(BaseModel):
    user_id: str
    personality: str
    company_name: str = "NAVITECH"
    agent_name: str = "trợ lý AI"

class PersonalityResponse(BaseModel):
    user_id: str
    personality_id: int
    personality_name: str
    personality_description: str
    company_name: str = "NAVITECH"
    agent_name: str = "trợ lý AI"

class AllPersonalitiesResponse(BaseModel):
    id: int
    name: str
    description: str
    company_name: str = "NAVITECH"
    agent_name: str = "trợ lý AI"

@router.post("/set-ai-personality", response_model=PersonalityResponse)
def set_ai_personality(request: SetPersonalityRequest, session: Session = Depends(get_db)):
    try:
        user_uuid = uuid.UUID(request.user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id format")
    personality = AIPersonalityService.get_personality_by_name(session, request.personality)
    if not personality:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Personality '{request.personality}' not found")
    result = UserService.set_user_personality(session, user_uuid, request.personality)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {request.user_id} not found")
    result['company_name'] = request.company_name
    result['agent_name'] = request.agent_name
    return PersonalityResponse(**result)

@router.get("/user/{user_id}", response_model=PersonalityResponse)
def get_user_personality(user_id: str, session: Session = Depends(get_db)):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id format")
    result = UserService.get_user_personality(user_uuid)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No personality set for user {user_id}")
    return PersonalityResponse(**result)

@router.get("/list", response_model=list[AllPersonalitiesResponse])
def list_all_personalities(session: Session = Depends(get_db)):
    personalities = AIPersonalityService.get_all_personalities(session)
    return personalities

@router.post("/create", response_model=AllPersonalitiesResponse)
def create_personality(name: str, description: str, company_name: str = "NAVITECH", agent_name: str = "trợ lý AI", session: Session = Depends(get_db)):
    existing = AIPersonalityService.get_personality_by_name(session, name)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Personality '{name}' already exists")
    from models.ai_personality import AIPersonalityCreateModel
    create_data = AIPersonalityCreateModel(name=name, description=description, company_name=company_name, agent_name=agent_name)
    personality = AIPersonalityService.create_personality(session, create_data)
    return AllPersonalitiesResponse(**personality.model_dump())
