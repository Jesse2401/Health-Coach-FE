from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Literal


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/health_coach"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # LLM Configuration
    LLM_PROVIDER: Literal["openai", "anthropic"] = "openai"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    
    # Model settings
    LLM_MODEL: str = "gpt-4-turbo-preview"  # or claude-3-sonnet-20240229
    MAX_CONTEXT_TOKENS: int = 8000
    MAX_RESPONSE_TOKENS: int = 1000
    
    # Chat settings
    MESSAGES_PER_PAGE: int = 20
    MAX_MESSAGE_LENGTH: int = 4000
    TYPING_INDICATOR_TTL: int = 60  # seconds
    
    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()

