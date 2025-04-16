from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
from ..services import auth_service
from ..utils.exceptions import AuthenticationError
from ..utils.responses import error_response
from functools import wraps


# Use FastAPI's HTTPBearer for extracting the token
bearer_scheme = HTTPBearer()

async def token_required_fastapi(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> object:
    """
    FastAPI dependency to ensure a valid JWT token is present and load the user.
    Returns the user for use in endpoints.
    """
    token = credentials.credentials
    try:
        user = await auth_service.get_current_user(token)
        # You can return the user object or just the user_id as needed
        return user
    except AuthenticationError as e:
        logging.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logging.error(f"Unexpected error during token validation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed!",
            headers={"WWW-Authenticate": "Bearer"},
        )
