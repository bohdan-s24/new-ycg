"""Database connection utilities for Redis."""

import logging
import re
from typing import Optional, Tuple
import asyncio
from functools import wraps

# Use upstash-redis library for serverless Redis
from upstash_redis.asyncio import Redis as UpstashRedisAsync

from ..config import Config
from .exceptions import RedisConnectionError, RedisOperationError, ConfigurationError

# Constants for Redis URL parsing
REDISS_URL_PATTERN = r'rediss://([^:]+):([^@]+)@([^:]+)'

# Global variable to hold the async Redis client
redis_async_client: Optional[UpstashRedisAsync] = None

# Maximum number of connection retries
MAX_RETRIES = 3

# Base delay for exponential backoff (in seconds)
BASE_RETRY_DELAY = 0.5

def parse_redis_url(url: str) -> Tuple[str, Optional[str]]:
    """
    Parse a Redis URL and convert it to the format needed for Upstash REST API.

    Args:
        url: The Redis URL to parse (e.g., rediss://username:password@hostname:port)

    Returns:
        Tuple containing (rest_url, password)
    """
    if not url:
        raise ValueError("Redis URL is empty or None")

    # If it's already in the correct format, return it as is
    if url.startswith('https://'):
        return url, None

    # Handle rediss:// protocol
    if url.startswith('rediss://'):
        # Try to parse with regex first
        match = re.match(REDISS_URL_PATTERN, url)
        if match:
            username, password, hostname = match.groups()
            logging.info(f"Extracted hostname from Redis URL: {hostname}")
            return f"https://{hostname}", password

        # Fallback: manual parsing
        try:
            parts = url.split('@')
            if len(parts) > 1:
                # Get the host part (remove port if present)
                hostname = parts[1].split(':')[0]
                logging.info(f"Fallback: Extracted hostname: {hostname}")

                # Extract password if possible
                password = None
                if len(parts[0].split(':')) > 1:
                    password = parts[0].split(':')[2]  # rediss://username:password@

                return f"https://{hostname}", password
        except Exception as e:
            logging.error(f"Error in fallback Redis URL parsing: {e}")

    # If we can't parse it, return it as is
    logging.warning(f"Could not parse Redis URL format: {url[:10]}..., using as is")
    return url, None

async def retry_async(max_retries=MAX_RETRIES, base_delay=BASE_RETRY_DELAY):
    """
    Decorator for retrying async functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (will be multiplied by 2^retry_count)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries > max_retries:
                        logging.error(f"Failed after {max_retries} retries: {e}")
                        raise

                    # Calculate delay with exponential backoff
                    delay = base_delay * (2 ** (retries - 1))
                    logging.warning(f"Retry {retries}/{max_retries} after {delay:.2f}s: {str(e)}")
                    await asyncio.sleep(delay)
        return wrapper
    return decorator

@retry_async()
async def get_redis_connection() -> UpstashRedisAsync:
    """
    Initializes and returns an async upstash-redis connection.
    Uses a global variable to reuse the client instance.
    Implements retry logic with exponential backoff.
    """
    global redis_async_client
    if redis_async_client is None:
        # Validate configuration
        if not Config.REDIS_URL:
            logging.error("REDIS_URL is not configured in environment variables.")
            raise ConfigurationError("REDIS_URL", "Redis URL not configured")

        # Get token from config
        rest_token = Config.KV_REST_API_TOKEN

        try:
            # Parse the Redis URL
            redis_url, password = parse_redis_url(Config.REDIS_URL)

            # If no token is provided but we extracted a password, use it as the token
            if not rest_token and password:
                rest_token = password
                logging.info("Using password from Redis URL as REST API token")

            if not rest_token:
                logging.error("KV_REST_API_TOKEN is not configured and could not extract password from URL")
                raise ConfigurationError("KV_REST_API_TOKEN", "Redis token not configured")

            logging.info(f"Connecting to Redis with URL: {redis_url[:20]}... (truncated)")

            # Connect using the Upstash Redis client
            redis_async_client = UpstashRedisAsync(url=redis_url, token=rest_token)

            # Test connection
            await redis_async_client.ping()
            logging.info("Successfully connected to Upstash Redis.")

        except ConfigurationError:
            # Re-raise configuration errors
            raise
        except Exception as e:
            # Wrap other exceptions in our custom exception
            logging.error(f"Failed to connect to Redis: {str(e)}")
            redis_async_client = None
            raise RedisConnectionError(original_error=e)

    return redis_async_client

async def redis_operation(operation_name: str, operation_func, *args, **kwargs):
    """
    Wrapper for Redis operations to handle errors consistently.

    Args:
        operation_name: Name of the Redis operation for logging
        operation_func: Async function to execute
        *args, **kwargs: Arguments to pass to the operation function

    Returns:
        Result of the operation

    Raises:
        RedisConnectionError: If connection to Redis fails
        RedisOperationError: If the operation fails
    """
    try:
        # Get Redis connection
        redis = await get_redis_connection()

        # Execute the operation
        return await operation_func(redis, *args, **kwargs)
    except RedisConnectionError:
        # Re-raise connection errors
        raise
    except Exception as e:
        # Wrap other exceptions
        logging.error(f"Redis operation '{operation_name}' failed: {str(e)}")
        raise RedisOperationError(operation_name, original_error=e)

# Redis connection management notes:
# 1. Upstash Redis client doesn't require explicit closing as connections are HTTP-based
# 2. For sync operations, create a separate function if needed in the future
# 3. Connection pooling is handled by the HTTP client internally
