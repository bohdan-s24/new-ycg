"""
OAuth service for handling external authentication providers.
"""

import logging
from typing import Dict, Any, Optional

import httpx
from google.oauth2 import id_token
from google.auth.transport import requests

from ..config import Config
from ..utils.exceptions import AuthenticationError


async def verify_google_oauth_token(token: str) -> Dict[str, Any]:
    """
    Verifies a Google OAuth token by fetching user info and returns it if valid.
    
    Args:
        token: The Google OAuth token to verify
        
    Returns:
        Dictionary containing user information
        
    Raises:
        AuthenticationError: If the token is invalid or verification fails
    """
    # Google's userinfo endpoint
    userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    headers = {"Authorization": f"Bearer {token}"}

    # Log token prefix for debugging (not the full token for security)
    token_prefix = token[:10] if token else "None"
    logging.info(f"Verifying Google OAuth token (prefix: {token_prefix}...) using userinfo endpoint")

    try:
        async with httpx.AsyncClient() as client:
            logging.info(f"Sending request to {userinfo_url}")
            # Add timeout to prevent hanging requests
            response = await client.get(userinfo_url, headers=headers, timeout=10.0)

        logging.info(f"Google userinfo response status: {response.status_code}")
        
        if response.status_code != 200:
            logging.error(f"Google API error: {response.status_code} - {response.text}")
            raise AuthenticationError(f"Google authentication failed: {response.status_code}")
            
        user_info = response.json()
        
        # Validate required fields
        if not user_info.get("sub") or not user_info.get("email"):
            logging.error("Google user info missing required fields")
            raise AuthenticationError("Google user info missing required fields")
            
        # Verify email is verified
        if not user_info.get("email_verified"):
            logging.warning(f"Unverified email from Google: {user_info.get('email')}")
            raise AuthenticationError("Email not verified with Google")
            
        logging.info(f"Successfully verified Google OAuth token for email: {user_info.get('email')}")
        return user_info
        
    except httpx.RequestError as e:
        logging.error(f"Error connecting to Google API: {e}")
        raise AuthenticationError(f"Failed to connect to Google API: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error verifying Google token: {e}")
        raise AuthenticationError(f"Google authentication failed: {str(e)}")


def verify_google_id_token(token: str, client_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Verifies a Google ID token using Google's auth library.
    
    Args:
        token: The Google ID token to verify
        client_id: Optional client ID to verify against (defaults to Config.GOOGLE_CLIENT_ID)
        
    Returns:
        Dictionary containing user information
        
    Raises:
        AuthenticationError: If the token is invalid or verification fails
    """
    if not client_id:
        client_id = Config.GOOGLE_CLIENT_ID
        
    if not client_id:
        logging.error("GOOGLE_CLIENT_ID not configured")
        raise AuthenticationError("Google client ID not configured")
        
    try:
        # Verify the token
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), client_id)
        
        # Verify issuer
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise AuthenticationError("Invalid token issuer")
            
        return idinfo
    except ValueError as e:
        logging.error(f"Invalid Google ID token: {e}")
        raise AuthenticationError(f"Invalid Google ID token: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error verifying Google ID token: {e}")
        raise AuthenticationError(f"Google authentication failed: {str(e)}")
