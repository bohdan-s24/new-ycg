"""
Authentication service for handling user authentication.
"""

import logging
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
    return token_service.validate_token(token)


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
    # Validate the token
    payload = await validate_token(token)
    
    # Get the user ID from the token
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Invalid token: missing user ID")
        
    # Get the user
    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise AuthenticationError("User not found")
        
    return user
