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
MAX_RETRIES = 5

# Base delay for exponential backoff (in seconds)
BASE_RETRY_DELAY = 1.0

# Connection pool settings
CONNECTION_POOL = {}
MAX_POOL_SIZE = Config.REDIS_MAX_CONNECTIONS

# Timeout settings
REDIS_TIMEOUT = Config.REDIS_TIMEOUT

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

@retry_async(max_retries=MAX_RETRIES, base_delay=BASE_RETRY_DELAY)
async def get_redis_connection() -> UpstashRedisAsync:
    """
    Initializes and returns an async upstash-redis connection.
    Uses a connection pool to manage connections efficiently.
    Implements retry logic with exponential backoff.
    """
    global redis_async_client

    # Check if we already have a client in the global variable
    if redis_async_client is not None:
        try:
            # Test if the connection is still alive with a short timeout
            await asyncio.wait_for(redis_async_client.ping(), timeout=2.0)
            return redis_async_client
        except (asyncio.TimeoutError, Exception) as e:
            # Connection is stale or failed, create a new one
            logging.warning(f"[REDIS_CONN] Existing connection failed ping test: {str(e)}")
            redis_async_client = None

    # Validate configuration
    if not Config.REDIS_URL:
        logging.error("[REDIS_CONN] REDIS_URL is not configured in environment variables.")
        raise ConfigurationError("REDIS_URL", "Redis URL not configured")

    # Get token from config
    rest_token = Config.KV_REST_API_TOKEN

    # Check if we have a connection in the pool
    pool_key = Config.REDIS_URL
    if pool_key in CONNECTION_POOL and len(CONNECTION_POOL) <= MAX_POOL_SIZE:
        try:
            # Get connection from pool
            client = CONNECTION_POOL[pool_key]
            # Test if it's still alive
            await asyncio.wait_for(client.ping(), timeout=2.0)
            redis_async_client = client
            logging.info("[REDIS_CONN] Reusing existing Redis connection.")
            return client
        except Exception as e:
            # Remove stale connection from pool
            logging.warning(f"[REDIS_CONN] Pooled connection failed: {str(e)}")
            CONNECTION_POOL.pop(pool_key, None)

    # Create a new connection
    try:
        # Parse the Redis URL
        redis_url, password = parse_redis_url(Config.REDIS_URL)

        # If no token is provided but we extracted a password, use it as the token
        if not rest_token and password:
            rest_token = password
            logging.info("[REDIS_CONN] Using password from Redis URL as REST API token")

        if not rest_token:
            logging.error("[REDIS_CONN] KV_REST_API_TOKEN is not configured and could not extract password from URL")
            raise ConfigurationError("KV_REST_API_TOKEN", "Redis token not configured")

        logging.info(f"[REDIS_CONN] Connecting to Redis with URL: {redis_url[:20]}... (truncated)")

        # Connect using the Upstash Redis client with timeout
        start_time = time.time()
        redis_async_client = UpstashRedisAsync(url=redis_url, token=rest_token)

        # Test connection with timeout
        ping_start = time.time()
        await asyncio.wait_for(redis_async_client.ping(), timeout=REDIS_TIMEOUT)
        ping_time = time.time() - ping_start

        # Add to connection pool
        CONNECTION_POOL[pool_key] = redis_async_client

        # Log success
        total_time = time.time() - start_time
        logging.info(f"[REDIS_CONN] Successfully connected and pinged Upstash Redis. Total time: {total_time:.4f}s (Ping time: {ping_time:.4f}s)")

    except ConfigurationError:
        # Re-raise configuration errors
        raise
    except asyncio.TimeoutError as e:
        # Handle timeout specifically
        logging.error(f"[REDIS_CONN] Redis connection timed out after {REDIS_TIMEOUT}s")
        redis_async_client = None
        raise RedisConnectionError(original_error=e, message=f"Redis connection timed out after {REDIS_TIMEOUT}s")
    except Exception as e:
        # Wrap other exceptions in our custom exception
        logging.error(f"[REDIS_CONN] Failed to connect to Redis: {str(e)}")
        redis_async_client = None
        raise RedisConnectionError(original_error=e)

    return redis_async_client

async def redis_operation(operation_name: str, operation_func, *args, **kwargs):
    """
    Wrapper for Redis operations to handle errors consistently.
    Includes timeout handling and detailed logging.

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
    start_time = time.time()
    logging.info(f"[REDIS_OP] Starting operation '{operation_name}'.")

    try:
        # Get Redis connection with timing
        conn_start = time.time()
        redis = await get_redis_connection()
        conn_time = time.time() - conn_start
        logging.info(f"[REDIS_OP] '{operation_name}' - Got Redis connection in {conn_time:.4f}s")

        # Execute the operation with timeout
        try:
            execution_start = time.time()
            result = await asyncio.wait_for(
                operation_func(redis, *args, **kwargs),
                timeout=REDIS_TIMEOUT
            )
            execution_time = time.time() - execution_start

            # Log success
            total_time = time.time() - start_time
            logging.info(f"[REDIS_OP] Operation '{operation_name}' successful. Total time: {total_time:.4f}s (Execution: {execution_time:.4f}s)")

            return result

        except asyncio.TimeoutError as e:
            # Handle operation timeout
            total_time = time.time() - start_time
            logging.error(f"[REDIS_OP] Operation '{operation_name}' timed out after {REDIS_TIMEOUT}s. Total time: {total_time:.4f}s")
            raise RedisOperationError(
                operation_name,
                original_error=e,
                message=f"Operation timed out after {REDIS_TIMEOUT}s"
            )

    except RedisConnectionError as e:
        # Re-raise connection errors with timing info
        total_time = time.time() - start_time
        logging.error(f"[REDIS_OP] Connection error during '{operation_name}'. Total time: {total_time:.4f}s")
        raise

    except Exception as e:
        # Wrap other exceptions with timing info
        total_time = time.time() - start_time
        logging.error(f"[REDIS_OP] Operation '{operation_name}' failed: {str(e)}. Total time: {total_time:.4f}s")
        raise RedisOperationError(operation_name, original_error=e)

# Redis connection management notes:
# 1. Upstash Redis client doesn't require explicit closing as connections are HTTP-based
# 2. For sync operations, create a separate function if needed in the future
# 3. Connection pooling is handled by the HTTP client internally
