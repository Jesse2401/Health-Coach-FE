from pydantic_settings import BaseSettings
from typing import Literal
from pydantic import field_validator


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://neondb_owner:npg_8WrZJcFvM3iu@ep-misty-night-ae4x4o1k-pooler.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require"
    
    @field_validator("DATABASE_URL")
    @classmethod
    def ensure_asyncpg_driver(cls, v: str) -> str:
        """Ensure DATABASE_URL uses asyncpg driver for async operations."""
        if isinstance(v, str):
            if v.startswith("postgresql://") and "+asyncpg" not in v:
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgres://") and "+asyncpg" not in v:
                v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v
    
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


def get_settings() -> Settings:
    return Settings()

