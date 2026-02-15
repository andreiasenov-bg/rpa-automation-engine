"""
System Configuration Manager - Redis-backed configuration storage.

Provides async functions to get/set system config values like API keys,
accessible from the admin UI. Sensitive values are masked when retrieved
via get_all_config().
"""

import redis.asyncio as aioredis
import structlog
from typing import Any, Dict, Optional

from app.config import get_settings

logger = structlog.get_logger(__name__)

# Global Redis connection cache
_redis: Optional[aioredis.Redis] = None

# Config hash name in Redis
CONFIG_HASH_KEY = "rpa:system_config"


async def get_redis() -> aioredis.Redis:
    """Get or create a Redis connection."""
    global _redis
    if _redis is None:
        settings = get_settings()
        try:
            _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            # Test the connection
            await _redis.ping()
            logger.info("Redis connection established for system config")
        except Exception as e:
            logger.error("Failed to connect to Redis for system config", error=str(e))
            raise
    return _redis


async def get_config(key: str) -> Optional[str]:
    """
    Get a configuration value by key.

    Args:
        key: Configuration key name

    Returns:
        Configuration value or None if not found
    """
    try:
        redis = await get_redis()
        value = await redis.hget(CONFIG_HASH_KEY, key)
        return value
    except Exception as e:
        logger.error("Failed to get config from Redis", key=key, error=str(e))
        return None


async def set_config(key: str, value: str) -> bool:
    """
    Set a configuration value.

    Args:
        key: Configuration key name
        value: Configuration value (will be stored as string)

    Returns:
        True if successful, False otherwise
    """
    try:
        redis = await get_redis()
        await redis.hset(CONFIG_HASH_KEY, key, value)
        logger.info("Configuration updated", key=key)
        return True
    except Exception as e:
        logger.error("Failed to set config in Redis", key=key, error=str(e))
        return False


async def delete_config(key: str) -> bool:
    """
    Delete a configuration value.

    Args:
        key: Configuration key name

    Returns:
        True if successful, False otherwise
    """
    try:
        redis = await get_redis()
        result = await redis.hdel(CONFIG_HASH_KEY, key)
        if result:
            logger.info("Configuration deleted", key=key)
            return True
        logger.warning("Configuration key not found", key=key)
        return False
    except Exception as e:
        logger.error("Failed to delete config from Redis", key=key, error=str(e))
        return False


async def get_all_config() -> Dict[str, Any]:
    """
    Get all configuration values.

    Sensitive values (containing 'key' or 'secret' in the key name) are masked,
    showing only the last 8 characters.

    Returns:
        Dictionary of all config values with sensitive ones masked
    """
    try:
        redis = await get_redis()
        all_config = await redis.hgetall(CONFIG_HASH_KEY)

        # Mask sensitive values
        masked_config = {}
        for key, value in all_config.items():
            if isinstance(value, str) and (
                'key' in key.lower() or 'secret' in key.lower() or 'password' in key.lower() or 'token' in key.lower()
            ):
                # Show only last 8 characters
                if len(value) > 8:
                    masked_value = f"{'*' * (len(value) - 8)}{value[-8:]}"
                else:
                    masked_value = "*" * len(value)
                masked_config[key] = masked_value
            else:
                masked_config[key] = value

        return masked_config
    except Exception as e:
        logger.error("Failed to get all config from Redis", error=str(e))
        return {}


async def close_redis() -> None:
    """Close the Redis connection."""
    global _redis
    if _redis:
        try:
            await _redis.close()
            _redis = None
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error("Error closing Redis connection", error=str(e))
