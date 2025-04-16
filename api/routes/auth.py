import logging
from fastapi import APIRouter, Request, Depends, HTTPException, status
from ..config import Config
from ..services import auth_service, credits_service
from ..models.user import UserCreate, UserLogin
from ..utils.responses import success_response, error_response
from ..utils.decorators import token_required_fastapi
from ..utils.exceptions import AuthenticationError, ValidationError
from pydantic import BaseModel
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi import Limiter

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

class GoogleLoginData(BaseModel):
    token: str
    platform: str = 'web'

class VerifyTokenData(BaseModel):
    token: str

@router.get('/debug')
def auth_debug():
    logging.info("Auth debug endpoint accessed")
    return success_response({
        "status": "Auth router is working",
        "router_name": "auth",
        "url_prefix": "/auth"
    })

@router.post('/register')
async def register_user(user_data: UserCreate):
    existing_user = await auth_service.get_user_by_email(user_data.email)
    if existing_user:
        return error_response("Email already registered", 409)

    new_user = await auth_service.create_user(user_data)
    if not new_user:
        logging.error(f"Failed to create user for email: {user_data.email}")
        return error_response("Could not create user.", 500)

    try:
        await credits_service.initialize_credits(new_user.id)
    except Exception as e:
        logging.error(f"Failed to initialize credits for user {new_user.id}: {e}")

    user_dict = new_user.dict(exclude={'password_hash', 'google_id'})
    return success_response(user_dict, 201)

@router.post('/login')
async def login_for_access_token(request: Request, login_data: UserLogin):
    user = await auth_service.authenticate_user(login_data.email, login_data.password)
    if not user:
        return error_response("Incorrect email or password", 401)

    access_token_expires = auth_service.ACCESS_TOKEN_EXPIRE_MINUTES
    access_token = auth_service.create_access_token(
        data={"sub": user.email, "user_id": user.id}, expires_delta=access_token_expires
    )
    return success_response({"access_token": access_token, "token_type": "bearer"})

@router.post('/login/google')
async def login_via_google(request: Request, data: GoogleLoginData):
    logging.info("Google login request received at /auth/login/google endpoint")
    logging.info(f"Processing login request with router: {router.prefix}")
    try:
        login_result = await auth_service.login_via_google(data.token, data.platform)
        logging.info(f"Google login successful for user: {login_result.get('email', 'unknown')}")
        return success_response(login_result)
    except AuthenticationError as e:
        logging.error(f"Google login failed: {str(e)}")
        return error_response(str(e), 401)
    except Exception as e:
        logging.error(f"Unexpected error during Google login: {str(e)}")
        return error_response("Internal server error", 500)

@router.get('/user')
async def get_user_info(user = Depends(token_required_fastapi)):
    try:
        # token_required_fastapi should return the user object (not just user_id)
        if not user:
            return error_response("User not found", 404)
        try:
            credits = await credits_service.get_credit_balance(user.id)
        except Exception as e:
            logging.error(f"Error fetching credit balance for user {user.id}: {e}")
            credits = 0
        user_info = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "email_verified": getattr(user, 'email_verified', True),
            "credits": credits,
            "picture": getattr(user, 'picture', None),
            "created_at": user.created_at.isoformat() if hasattr(user, 'created_at') and user.created_at else None
        }
        return success_response(user_info)
    except AuthenticationError as e:
        logging.error(f"Authentication error: {str(e)}")
        return error_response("Authentication error", 401)
    except Exception as e:
        logging.error(f"Error getting user info: {str(e)}")
        return error_response("Error retrieving user information", 500)

@router.post('/verify')
async def verify_token(data: VerifyTokenData):
    try:
        await auth_service.validate_token(data.token)
        user = await auth_service.get_current_user(data.token)
        return success_response({
            "valid": True,
            "user_id": user.id,
            "email": user.email
        })
    except AuthenticationError:
        return error_response("Invalid or expired token", 401)
    except Exception as e:
        logging.error(f"Unexpected error verifying token: {str(e)}")
        return error_response("Internal server error", 500)

@router.get('/config')
async def get_auth_config():
    return success_response({
        "googleClientId": Config.GOOGLE_CLIENT_ID
    })
