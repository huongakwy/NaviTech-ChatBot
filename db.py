from sqlalchemy import engine
from sqlalchemy.orm import sessionmaker, Session as SQLSession
from app_environment import AppEnvironment
from env import env

db = engine.create_engine(
    f"postgresql://{env.POSTGRES_USER}:{env.POSTGRES_PASSWORD}@localhost:{env.POSTGRES_PORT}/{env.POSTGRES_DB}",
    # echo=(AppEnvironment.is_production_env(env.APP_ENV) == False),
    pool_pre_ping=True,
    # pool_size=5,
    # max_overflow=2,
    # pool_timeout=30,
    pool_recycle=1800,
)

vectordb_conn_str = f"postgresql+psycopg://{env.POSTGRES_USER}:{env.POSTGRES_PASSWORD}@localhost:{env.POSTGRES_PORT}/{env.POSTGRES_DB}"

Session = sessionmaker(db)
SessionLocal = Session  # Alias for compatibility


def get_db() -> SQLSession:
    """Dependency for getting database session in FastAPI endpoints"""
    session = Session()
    try:
        yield session
    finally:
        session.close()