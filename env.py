import os

from dotenv import load_dotenv
from pydantic import BaseModel
from app_environment import AppEnvironment

app_env = AppEnvironment("local")

if app_env == AppEnvironment.test:
    load_dotenv(".env.test")
else:
    load_dotenv(".env", override=True)

from typing import Optional

class Env(BaseModel):
    APP_ENV: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int 
    DEBUG: bool
    FASTAPI_PORT: int
    DATABASE_URL: str
    QDRANT_PORT: int
    GEMINI_API_KEY: str
    OPENAI_API_KEY: str
    GEMINI_API_KEY1: str
    GEMINI_API_KEY2: str
    LEN_EMBEDDING: int
    CLAUDE_API_KEY: Optional[str] = None  # Optional - không bắt buộc
    
env = Env.model_validate(dict(os.environ))
