# Use upstash-redis library instead of aioredis
from upstash_redis import Redis as UpstashRedisSync # Sync client for potential non-async use
# from upstash_redis import RedisError # RedisError might not be exposed directly
from upstash_redis.asyncio import Redis as UpstashRedisAsync # Async client
import logging
from typing import Optional

from ..config import Config

# Global variable to hold the async Redis client
redis_async_client: Optional[UpstashRedisAsync] = None
# Global variable to hold the sync Redis client (optional, if needed)
# redis_sync_client: Optional[UpstashRedisSync] = None 

async def get_redis_connection() -> UpstashRedisAsync:
    """
    Initializes and returns an async upstash-redis connection.
    Uses a global variable to reuse the client instance.
    """
    global redis_async_client
    if redis_async_client is None:
        # Use the correct Vercel environment variable names from Config
        if not Config.REDIS_URL or not Config.KV_REST_API_TOKEN: 
            logging.error("REDIS_URL or KV_REST_API_TOKEN is not configured in environment variables.")
            raise ValueError("Redis URL or Token not configured")
        
        try:
            # Initialize the async client using the constructor with URL and Token
            redis_async_client = UpstashRedisAsync(url=Config.REDIS_URL, token=Config.KV_REST_API_TOKEN)
            
            # Test connection (Upstash client might not have an explicit async ping, 
            # but subsequent operations will fail if connection is bad)
            # Let's try a simple get/set or info command if available, otherwise rely on first use
            await redis_async_client.ping() # Ping seems available in async client too
            logging.info("Successfully connected to Upstash Redis (async).")
            
        # Catch generic Exception as specific RedisError might not be importable
        except Exception as e: 
            logging.error(f"Failed to connect to Upstash Redis: {e}")
            redis_async_client = None 
            raise ConnectionError(f"Unexpected error connecting to Upstash Redis: {e}") from e
            
    return redis_async_client

# Optional: Function to get a sync client if needed elsewhere
# def get_sync_redis_connection() -> UpstashRedisSync:
#     """Initializes and returns a sync upstash-redis connection."""
#     global redis_sync_client
#     if redis_sync_client is None:
#         if not Config.REDIS_URL:
#             logging.error("REDIS_URL is not configured.")
#             raise ValueError("Redis URL not configured")
#         try:
#             redis_sync_client = UpstashRedisSync.from_url(Config.REDIS_URL)
#             redis_sync_client.ping()
#             logging.info("Successfully connected to Upstash Redis (sync).")
#         except Exception as e:
#             logging.error(f"Failed to connect to Upstash Redis (sync): {e}")
#             redis_sync_client = None
#             raise ConnectionError(f"Could not connect to Upstash Redis (sync): {e}") from e
#     return redis_sync_client

# Note: upstash-redis client doesn't require explicit closing typically,
# as connections are managed per-request (HTTP-based).
# async def close_redis_connection(): # Likely not needed
#     pass
