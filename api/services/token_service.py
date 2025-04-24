"""
Token service for handling JWT token operations.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Any

from jose import jwt, JWTError

from ..config import Config
from ..utils.exceptions import AuthenticationError
from ..utils.db import redis_operation

import secrets
import hashlib
import asyncio

# Constants
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
REFRESH_TOKEN_EXPIRE_DAYS = 7
REFRESH_TOKEN_REDIS_PREFIX = "refresh_token:"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a JWT access token.

    Args:
        data: The data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        JWT token string
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    try:
        encoded_jwt = jwt.encode(to_encode, Config.JWT_SECRET_KEY, algorithm="HS256")
        return encoded_jwt
    except Exception as e:
        logging.error(f"Error creating access token: {e}")
        raise AuthenticationError(f"Failed to create access token: {str(e)}")


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decodes and validates a JWT token.

    Args:
        token: The JWT token to decode

    Returns:
        The decoded token payload

    Raises:
        AuthenticationError: If the token is invalid or expired
    """
    try:
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError as e:
        logging.error(f"Error decoding token: {e}")
        raise AuthenticationError(f"Invalid token: {str(e)}")


def create_user_token(user_id: str, email: str) -> str:
    """
    Creates a JWT token for a user.

    Args:
        user_id: The user's ID
        email: The user's email

    Returns:
        JWT token string
    """
    token_data = {
        "sub": user_id,
        "email": email,
        "iat": datetime.now(timezone.utc)
    }
    return create_access_token(token_data)


def validate_token(token: str) -> Dict[str, Any]:
    """
    Validates a token and returns the payload if valid.

    Args:
        token: The JWT token to validate

    Returns:
        The decoded token payload

    Raises:
        AuthenticationError: If the token is invalid or expired
    """
    try:
        payload = decode_token(token)

        # Check if token has required fields
        if "sub" not in payload or "email" not in payload:
            raise AuthenticationError("Token missing required fields")

        # Check if token is expired
        if "exp" in payload:
            expiration = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
            if expiration < datetime.now(timezone.utc):
                raise AuthenticationError("Token has expired")

        return payload
    except AuthenticationError:
        raise
    except Exception as e:
        logging.error(f"Unexpected error validating token: {e}")
        raise AuthenticationError(f"Token validation failed: {str(e)}")


async def generate_refresh_token(user_id: str) -> str:
    """
    Generates a secure refresh token, stores its hash in Redis with expiry, and returns the plaintext token.
    """
    token = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    redis_key = f"{REFRESH_TOKEN_REDIS_PREFIX}{user_id}:{token_hash}"
    expire_seconds = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

    async def _set(redis):
        await redis.set(redis_key, "1", ex=expire_seconds)
        return True
    await redis_operation("set_refresh_token", _set)
    return token


async def validate_refresh_token(user_id: str, token: str) -> bool:
    """
    Validates a refresh token for a user by checking its hash in Redis.
    """
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    redis_key = f"{REFRESH_TOKEN_REDIS_PREFIX}{user_id}:{token_hash}"
    async def _get(redis):
        return await redis.get(redis_key)
    result = await redis_operation("get_refresh_token", _get)
    return result is not None


async def revoke_refresh_token(user_id: str, token: str) -> bool:
    """
    Revokes a refresh token by deleting its hash from Redis.
    """
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    redis_key = f"{REFRESH_TOKEN_REDIS_PREFIX}{user_id}:{token_hash}"
    async def _del(redis):
        return await redis.delete(redis_key)
    result = await redis_operation("del_refresh_token", _del)
    return result == 1


async def revoke_all_refresh_tokens(user_id: str) -> int:
    """
    Revokes all refresh tokens for a user (logs out from all devices).
    """
    # Pattern: refresh_token:{user_id}:*
    pattern = f"{REFRESH_TOKEN_REDIS_PREFIX}{user_id}:*"
    async def _del_all(redis):
        keys = await redis.keys(pattern)
        if not keys:
            return 0
        return await redis.delete(*keys)
    return await redis_operation("del_all_refresh_tokens", _del_all)
