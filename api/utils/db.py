import aioredis
import logging
from typing import Optional

from ..config import Config

# Global variable to hold the Redis connection pool/client
redis_client: Optional[aioredis.Redis] = None

async def get_redis_connection() -> aioredis.Redis:
    """
    Initializes and returns an aioredis connection.
    Uses a global variable to reuse the connection pool.
    """
    global redis_client
    if redis_client is None:
        if not Config.REDIS_URL:
            logging.error("REDIS_URL is not configured in environment variables.")
            raise ValueError("Redis URL not configured")
        
        try:
            # aioredis automatically handles pooling when using Redis.from_url
            redis_client = aioredis.from_url(
                Config.REDIS_URL,
                encoding="utf-8",
                decode_responses=True # Decode responses to strings automatically
            )
            # Test connection
            await redis_client.ping()
            logging.info("Successfully connected to Redis.")
        except Exception as e:
            logging.error(f"Failed to connect to Redis: {e}")
            # Reset client so next call tries again
            redis_client = None 
            raise ConnectionError(f"Could not connect to Redis: {e}") from e
            
    return redis_client

async def close_redis_connection():
    """Closes the Redis connection pool."""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
        logging.info("Redis connection closed.")

# Consider adding application startup/shutdown hooks in your Flask app 
# (__init__.py or index.py) to call get_redis_connection (to initialize early)
# and close_redis_connection (on shutdown).
