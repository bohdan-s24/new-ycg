"""
Authentication service for handling user authentication.
"""

import logging
import time
from typing import Dict, Any, Optional, Tuple

from passlib.context import CryptContext

from ..models.user import User
from ..utils.exceptions import AuthenticationError, ValidationError
from . import token_service
from . import oauth_service
from . import user_service

# Password Hashing Context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against a hashed password.

    Args:
        plain_password: The plain text password
        hashed_password: The hashed password to compare against

    Returns:
        True if the password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hashes a plain password.

    Args:
        password: The plain text password to hash

    Returns:
        The hashed password
    """
    return pwd_context.hash(password)


async def authenticate_user(email: str, password: str) -> Optional[User]:
    """
    Authenticates a user with email and password.

    Args:
        email: The user's email
        password: The user's password

    Returns:
        User object if authentication is successful, None otherwise
    """
    user = await user_service.get_user_by_email(email)
    if not user:
        return None

    if not user.hashed_password:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


async def create_user_token(user: User) -> str:
    """
    Creates a JWT token for a user.

    Args:
        user: The User object

    Returns:
        JWT token string
    """
    return token_service.create_user_token(user.id, user.email)


async def verify_google_oauth_token(token: str) -> Dict[str, Any]:
    """
    Verifies a Google OAuth token.

    Args:
        token: The Google OAuth token to verify

    Returns:
        Dictionary containing user information

    Raises:
        AuthenticationError: If the token is invalid or verification fails
    """
    return await oauth_service.verify_google_oauth_token(token)


async def get_or_create_google_user(google_user_info: Dict[str, Any]) -> Tuple[User, bool]:
    """
    Gets or creates a user based on Google user info.

    Args:
        google_user_info: Dictionary containing Google user information

    Returns:
        Tuple containing (User object, bool indicating if user was created)

    Raises:
        ValidationError: If the user data is invalid
    """
    return await user_service.get_or_create_google_user(google_user_info)


async def login_user(user: User) -> Dict[str, Any]:
    """
    Logs in a user and returns token and user info.

    Args:
        user: The User object

    Returns:
        Dictionary containing access token and user information
    """
    # Create access token
    access_token = await create_user_token(user)

    # Get credit balance
    from . import credits_service
    credits = await credits_service.get_credit_balance(user.id)

    # Return token and user info
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
        "credits": credits
    }


async def validate_token(token: str) -> Dict[str, Any]:
    """
    Validates a token and returns the payload if valid.

    Args:
        token: The JWT token to validate

    Returns:
        The decoded token payload

    Raises:
        AuthenticationError: If the token is invalid or expired
    """
    start_time = time.time()
    logging.info("[VALIDATE_TOKEN] Starting token decoding and validation.")
    try:
        payload = token_service.validate_token(token)
        logging.info(f"[VALIDATE_TOKEN] Token validation successful in {time.time() - start_time:.4f}s")
        return payload
    except AuthenticationError as e:
        logging.warning(f"[VALIDATE_TOKEN] AuthenticationError during validation in {time.time() - start_time:.4f}s: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"[VALIDATE_TOKEN] Unexpected error during validation in {time.time() - start_time:.4f}s: {str(e)}")
        raise


async def get_user_by_id(user_id: str) -> User:
    """
    Gets a user by ID directly from the user service.
    This is a lightweight version of get_current_user that doesn't validate tokens.

    Args:
        user_id: The user ID to look up

    Returns:
        User object or None if not found
    """
    return await user_service.get_user_by_id(user_id)


async def get_current_user(token: str) -> User:
    """
    Gets the current user from a token.

    Args:
        token: The JWT token

    Returns:
        User object

    Raises:
        AuthenticationError: If the token is invalid or the user is not found
    """
    get_user_start_time = time.time()
    logging.info("[GET_CURRENT_USER] Starting.")
    try:
        # Validate the token (already logged in validate_token)
        t_validate_start = time.time()
        payload = await validate_token(token)
        logging.info(f"[GET_CURRENT_USER] Token validation step took {time.time() - t_validate_start:.4f}s")

        # Get the user ID from the token
        user_id = payload.get("sub")
        if not user_id:
            logging.error("[GET_CURRENT_USER] Invalid token: missing user ID.")
            raise AuthenticationError("Invalid token: missing user ID")
        logging.info(f"[GET_CURRENT_USER] User ID from token: {user_id}")

        # Get the user
        t_get_user_db_start = time.time()
        user = await user_service.get_user_by_id(user_id)
        logging.info(f"[GET_CURRENT_USER] User lookup from user_service took {time.time() - t_get_user_db_start:.4f}s")

        if not user:
            logging.warning(f"[GET_CURRENT_USER] User not found for ID: {user_id}")
            raise AuthenticationError("User not found")

        total_duration = time.time() - get_user_start_time
        logging.info(f"[GET_CURRENT_USER] Successfully retrieved user {user_id}. Total time: {total_duration:.4f}s")
        return user
    except AuthenticationError as e:
        total_duration = time.time() - get_user_start_time
        logging.warning(f"[GET_CURRENT_USER] AuthenticationError: {str(e)}. Total time: {total_duration:.4f}s")
        raise
    except Exception as e:
        total_duration = time.time() - get_user_start_time
        logging.error(f"[GET_CURRENT_USER] Unexpected error: {str(e)}. Total time: {total_duration:.4f}s")
        raise
