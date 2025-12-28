import redis.asyncio as redis
from typing import Optional, Tuple
from datetime import datetime
from uuid import UUID
import logging

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class RedisService:
    """
    Redis service for caching and real-time features.
    Handles typing indicators and can be extended for other caching needs.
    """
    
    _instance: Optional["RedisService"] = None
    _redis: Optional[redis.Redis] = None
    
    @classmethod
    async def get_instance(cls) -> "RedisService":
        """Get singleton instance of RedisService."""
        if cls._instance is None:
            cls._instance = cls()
            cls._redis = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
        return cls._instance
    
    @classmethod
    async def close(cls):
        """Close Redis connection."""
        if cls._redis:
            await cls._redis.close()
            cls._redis = None
            cls._instance = None
    
    async def set_typing(self, user_id: UUID, is_typing: bool) -> None:
        """
        Set typing indicator status.
        
        Args:
            user_id: User ID
            is_typing: Whether the assistant is typing
        """
        key = f"typing:{user_id}"
        try:
            if is_typing:
                await self._redis.setex(
                    key,
                    settings.TYPING_INDICATOR_TTL,
                    datetime.utcnow().isoformat()
                )
            else:
                await self._redis.delete(key)
        except Exception as e:
            logger.warning(f"Redis error setting typing status: {e}")
    
    async def get_typing_status(self, user_id: UUID) -> Tuple[bool, Optional[datetime]]:
        """
        Get typing indicator status.
        
        Returns:
            Tuple of (is_typing, started_at)
        """
        key = f"typing:{user_id}"
        try:
            value = await self._redis.get(key)
            if value:
                return True, datetime.fromisoformat(value)
            return False, None
        except Exception as e:
            logger.warning(f"Redis error getting typing status: {e}")
            return False, None
    
    async def cache_set(self, key: str, value: str, ttl: int = 300) -> None:
        """Set a cached value with TTL."""
        try:
            await self._redis.setex(key, ttl, value)
        except Exception as e:
            logger.warning(f"Redis cache set error: {e}")
    
    async def cache_get(self, key: str) -> Optional[str]:
        """Get a cached value."""
        try:
            return await self._redis.get(key)
        except Exception as e:
            logger.warning(f"Redis cache get error: {e}")
            return None

