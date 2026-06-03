import redis.asyncio as aioredis
from typing import Any, Optional
import json
import structlog
from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
    return _redis


async def cache_get(key: str) -> Optional[Any]:
    r = await get_redis()
    try:
        value = await r.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.warning("Cache get failed", key=key, error=str(e))
        return None


async def cache_set(key: str, value: Any, ttl: int = None) -> bool:
    r = await get_redis()
    try:
        ttl = ttl or settings.CACHE_TTL
        await r.setex(key, ttl, json.dumps(value, default=str))
        return True
    except Exception as e:
        logger.warning("Cache set failed", key=key, error=str(e))
        return False


async def cache_delete(key: str) -> bool:
    r = await get_redis()
    try:
        await r.delete(key)
        return True
    except Exception as e:
        logger.warning("Cache delete failed", key=key, error=str(e))
        return False


async def cache_delete_pattern(pattern: str) -> int:
    r = await get_redis()
    try:
        keys = await r.keys(pattern)
        if keys:
            return await r.delete(*keys)
        return 0
    except Exception as e:
        logger.warning("Cache pattern delete failed", pattern=pattern, error=str(e))
        return 0


def cache_key(*parts: str) -> str:
    return ":".join(str(p) for p in parts)
