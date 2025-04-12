"""
Token service for handling JWT token operations.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

import jwt
from jwt.exceptions import PyJWTError

from ..config import Config
from ..utils.exceptions import AuthenticationError

# Constants
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


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
        expire = datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.now(datetime.timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
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
    except PyJWTError as e:
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
        "iat": datetime.now(datetime.timezone.utc)
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
            expiration = datetime.fromtimestamp(payload["exp"], tz=datetime.timezone.utc)
            if expiration < datetime.now(datetime.timezone.utc):
                raise AuthenticationError("Token has expired")
                
        return payload
    except AuthenticationError:
        raise
    except Exception as e:
        logging.error(f"Unexpected error validating token: {e}")
        raise AuthenticationError(f"Token validation failed: {str(e)}")
