import logging
from fastapi import APIRouter, Request, Depends, HTTPException, status
from ..config import Config
from ..services import auth_service, credits_service
from ..models.user import UserCreate, UserLogin
from ..utils.responses import success_response, error_response
from ..utils.decorators import token_required_fastapi
from ..utils.exceptions import AuthenticationError, ValidationError

router = APIRouter()

@router.get('/debug')
def auth_debug():
    logging.info("Auth debug endpoint accessed")
    return success_response({
        "status": "Auth router is working",
        "router_name": "auth",
        "url_prefix": "/auth"
    })

@router.post('/register')
async def register_user(request: Request):
    if not request.json():
        return error_response("Request must be JSON", 400)
    data = await request.json()
    try:
        user_data = UserCreate(**data)
    except Exception as e: 
        logging.error(f"Registration validation error: {e}")
        return error_response(f"Invalid registration data: {e}", 400)

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
async def login_for_access_token(request: Request):
    try:
        data = await request.json()
        login_data = UserLogin(**data)
    except Exception as e:
        logging.error(f"Login validation error: {e}")
        return error_response(f"Invalid login data: {e}", 400)

    user = await auth_service.authenticate_user(login_data.email, login_data.password)
    if not user:
        return error_response("Incorrect email or password", 401)

    access_token_expires = auth_service.ACCESS_TOKEN_EXPIRE_MINUTES
    access_token = auth_service.create_access_token(
        data={"sub": user.email, "user_id": user.id}, expires_delta=access_token_expires
    )
    return success_response({"access_token": access_token, "token_type": "bearer"})

@router.post('/login/google')
async def login_via_google(request: Request):
    logging.info("Google login request received at /auth/login/google endpoint")
    logging.info(f"Processing login request with router: {router.prefix}")

    if not request.json():
        logging.error("Request is not JSON")
        return error_response("Request must be JSON", 400)

    try:
        data = await request.json()
        logging.info(f"Request data: {data}")

        google_token = data.get('token')
        platform = data.get('platform', 'web')  

        if not google_token:
            logging.error("Missing Google token in request")
            return error_response("Missing Google token in request", 400)

        logging.info(f"Processing Google login with platform: {platform}")

        if platform != "chrome_extension":
            logging.warning(f"Received Google login request with unsupported platform: {platform}")
            return error_response("Only Chrome extension login is supported.", 400)
    except Exception as e:
        logging.error(f"Error parsing request data: {str(e)}")
        return error_response("Invalid request format", 400)

    try:
        logging.info("Verifying Google OAuth token from Chrome extension...")
        user, is_new_user = await auth_service.login_or_register_google_user(google_token, platform)
        logging.info(f"Google OAuth token verification successful: {user.get('email') if user else 'No user info'}")

        if not user:
            logging.error("Failed to verify Google token - no user info returned")
            return error_response("Invalid or expired Google token", 401)
    except AuthenticationError as e:
        logging.error(f"Authentication error verifying Google token: {str(e)}")
        return error_response(str(e), 401)
    except Exception as e:
        logging.error(f"Unexpected error verifying Google OAuth token: {str(e)}")
        return error_response(f"Error verifying Google token: {str(e)}", 500)

    try:
        if isinstance(user, tuple) and len(user) == 2:
            user, is_new_user = user
            logging.info(f"User result: user={user.email}, is_new_user={is_new_user}")
        else:
            user = user
            is_new_user = False
            logging.info(f"User result: user={user.email if user else None}, is_new_user=False")

        if not user:
            logging.error(f"Failed to get or create user from Google info: {user.get('email')}")
            return error_response("Failed to process Google sign-in", 500)

        login_result = await auth_service.login_user(user)
        login_result["new_user"] = is_new_user
        logging.info(f"Google login successful for user: {user.email}")
        return success_response(login_result)
    except AuthenticationError as e:
        logging.error(f"Authentication error during login: {str(e)}")
        return error_response(str(e), 401)
    except Exception as e:
        logging.error(f"Unexpected error during login process: {str(e)}")
        return error_response(f"Error during login process: {str(e)}", 500)

@router.get('/user')
async def get_user_info(user_id: str = Depends(token_required_fastapi)):
    try:
        user = await auth_service.get_user_by_id(user_id)
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
async def verify_token(request: Request):
    if not request.json():
        return error_response("Request must be JSON", 400)

    try:
        data = await request.json()
        token = data.get('token')

        if not token:
            return error_response("Missing token in request", 400)
    except Exception as e:
        logging.error(f"Error parsing request data: {str(e)}")
        return error_response("Invalid request format", 400)

    try:
        await auth_service.validate_token(token)

        user = await auth_service.get_current_user(token)

        return success_response({
            "valid": True,
            "user_id": user.id,
            "email": user.email
        })
    except AuthenticationError:
        return success_response({"valid": False})
    except Exception as e:
        logging.error(f"Unexpected error verifying token: {str(e)}")
        return success_response({"valid": False})

@router.get('/config')
async def get_auth_config():
    return success_response({
        "googleClientId": Config.GOOGLE_CLIENT_ID
    })
