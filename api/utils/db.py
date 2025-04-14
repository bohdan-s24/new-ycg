"""Database connection utilities for Redis."""

import logging
import re
import time
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

def retry_async(max_retries=MAX_RETRIES, base_delay=BASE_RETRY_DELAY):
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
        t_conn_start = time.time()
        logging.info("[REDIS_CONN] Attempting to establish new Redis connection.")
        # Validate configuration
        if not Config.REDIS_URL:
            logging.error("[REDIS_CONN] REDIS_URL is not configured.")
            raise ConfigurationError("REDIS_URL", "Redis URL not configured")

        # Get token from config
        rest_token = Config.KV_REST_API_TOKEN

        try:
            # Parse the Redis URL
            redis_url, password = parse_redis_url(Config.REDIS_URL)

            # If no token is provided but we extracted a password, use it as the token
            if not rest_token and password:
                rest_token = password
                logging.info("[REDIS_CONN] Using password from Redis URL as REST API token")

            if not rest_token:
                logging.error("[REDIS_CONN] KV_REST_API_TOKEN is not configured and could not extract password.")
                raise ConfigurationError("KV_REST_API_TOKEN", "Redis token not configured")

            logging.info(f"[REDIS_CONN] Connecting to Redis with URL: {redis_url[:20]}... (truncated)")

            # Connect using the Upstash Redis client
            redis_async_client = UpstashRedisAsync(url=redis_url, token=rest_token)

            # Test connection
            t_ping_start = time.time()
            await redis_async_client.ping()
            conn_duration = time.time() - t_conn_start
            ping_duration = time.time() - t_ping_start
            logging.info(f"[REDIS_CONN] Successfully connected and pinged Upstash Redis. Total time: {conn_duration:.4f}s (Ping time: {ping_duration:.4f}s)")

        except ConfigurationError:
            raise # Re-raise configuration errors
        except Exception as e:
            # Wrap other exceptions in our custom exception
            conn_duration = time.time() - t_conn_start
            logging.error(f"[REDIS_CONN] Failed to connect to Redis after {conn_duration:.4f}s: {str(e)}")
            redis_async_client = None # Reset client on failure
            raise RedisConnectionError(original_error=e)
    else:
        logging.debug("[REDIS_CONN] Reusing existing Redis connection.")

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
    op_start_time = time.time()
    logging.debug(f"[REDIS_OP] Starting operation '{operation_name}'.")
    try:
        # Get Redis connection
        t_get_conn_start = time.time()
        redis = await get_redis_connection()
        logging.debug(f"[REDIS_OP] '{operation_name}' - Got Redis connection in {time.time() - t_get_conn_start:.4f}s")

        # Execute the operation
        t_exec_start = time.time()
        result = await operation_func(redis, *args, **kwargs)
        op_duration = time.time() - op_start_time
        exec_duration = time.time() - t_exec_start
        logging.info(f"[REDIS_OP] Operation '{operation_name}' successful. Total time: {op_duration:.4f}s (Execution: {exec_duration:.4f}s)")
        return result
    except RedisConnectionError:
        op_duration = time.time() - op_start_time
        logging.error(f"[REDIS_OP] '{operation_name}' failed due to connection error after {op_duration:.4f}s")
        raise
    except Exception as e:
        # Wrap other exceptions
        op_duration = time.time() - op_start_time
        logging.error(f"[REDIS_OP] '{operation_name}' failed: {str(e)}. Total time: {op_duration:.4f}s")
        raise RedisOperationError(operation_name, original_error=e)

# Redis connection management notes:
# 1. Upstash Redis client doesn't require explicit closing as connections are HTTP-based
# 2. For sync operations, create a separate function if needed in the future
# 3. Connection pooling is handled by the HTTP client internally
