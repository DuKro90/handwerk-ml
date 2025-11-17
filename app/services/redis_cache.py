"""
Redis Caching Service
"""

import json
import logging
from typing import Optional, Any
import redis.asyncio as redis

logger = logging.getLogger(__name__)

redis_client: Optional[redis.Redis] = None

async def init_redis():
    """Initialize Redis connection"""
    global redis_client
    
    from app.config import settings
    
    try:
        redis_client = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
            socket_keepalive_options={},
            connection_pool_kwargs={"max_connections": 50}
        )
        
        # Test connection
        await redis_client.ping()
        logger.info("✓ Redis initialized successfully")
        
    except Exception as e:
        logger.error(f"✗ Redis initialization failed: {e}")
        raise

async def close_redis():
    """Close Redis connection"""
    global redis_client
    if redis_client:
        try:
            await redis_client.close()
            logger.info("✓ Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis: {e}")

async def get_cache(key: str) -> Optional[Any]:
    """Get value from cache"""
    if not redis_client:
        return None
    
    try:
        value = await redis_client.get(key)
        if value:
            return json.loads(value)
    except Exception as e:
        logger.warning(f"Cache get error: {e}")
    
    return None

async def set_cache(key: str, value: Any, ttl: int = 86400) -> bool:
    """Set value in cache with TTL"""
    if not redis_client:
        return False
    
    try:
        await redis_client.setex(
            key,
            ttl,
            json.dumps(value)
        )
        return True
    except Exception as e:
        logger.warning(f"Cache set error: {e}")
        return False
