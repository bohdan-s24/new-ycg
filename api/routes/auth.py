from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest, Unauthorized, InternalServerError, Conflict
from datetime import timedelta
import logging

# Assuming services and models are structured to be imported like this
from ..services import auth_service, credits_service # Import credits_service
from ..models.user import UserCreate, UserLogin, User # Use Pydantic models for validation if desired
from ..utils.responses import success_response, error_response # Assuming you have response helpers

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['POST'])
async def register_user():
    """
    Registers a new user with email and password.
    """
    if not request.is_json:
        return error_response("Request must be JSON", status.HTTP_400_BAD_REQUEST)

    data = request.get_json()
    
    try:
        # Validate input using Pydantic if preferred
        user_data = UserCreate(**data)
    except Exception as e: # Catch Pydantic validation errors or others
        logging.error(f"Registration validation error: {e}")
        return error_response(f"Invalid registration data: {e}", 400)

    existing_user = await auth_service.get_user_by_email(user_data.email)
    if existing_user:
        return error_response("Email already registered", 409) # 409 Conflict is suitable

    new_user = await auth_service.create_user(user_data)
    if not new_user:
         logging.error(f"Failed to create user for email: {user_data.email}")
         return error_response("Could not create user.", 500)

    # Initialize free credits for the new user
    try:
        await credits_service.initialize_credits(new_user.id)
    except Exception as e:
        # Log this error, but don't necessarily fail the registration
        # The user exists, credits can potentially be added later or manually
        logging.error(f"Failed to initialize credits for user {new_user.id}: {e}")

    # Optionally: Trigger email verification process here

    # Return the created user data (excluding sensitive info like password hash)
    # Ensure the User model returned doesn't expose the hash
    # Convert Pydantic model to dict for JSON response
    user_dict = new_user.dict(exclude={'password_hash', 'google_id'}) # Exclude sensitive fields
    return success_response(user_dict, 201)

@auth_bp.route('/login', methods=['POST'])
async def login_for_access_token():
    """
    Provides an access token for valid email/password credentials.
    Expects JSON payload with email and password.
    """
    if not request.is_json:
        return error_response("Request must be JSON", 400)

    data = request.get_json()
    
    try:
        # Validate input using Pydantic if preferred
        login_data = UserLogin(**data)
    except Exception as e:
        logging.error(f"Login validation error: {e}")
        return error_response(f"Invalid login data: {e}", 400)

    user = await auth_service.get_user_by_email(login_data.email)
    
    # Use secure comparison for password check
    if not user or not user.password_hash or not auth_service.verify_password(login_data.password, user.password_hash):
        return error_response("Incorrect email or password", 401) # Unauthorized

    # Check if email is verified if required
    # if not user.email_verified:
    #     return error_response("Email not verified", 400) # Bad Request or 403 Forbidden

    # Generate JWT token
    access_token_expires = timedelta(minutes=auth_service.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.email, "user_id": user.id}, expires_delta=access_token_expires
    )

    return success_response({"access_token": access_token, "token_type": "bearer"})


# --- Google Sign-In (ID Token Verification) ---
@auth_bp.route('/login/google', methods=['POST'])
async def login_via_google():
    """
    Authenticates a user via a Google ID token obtained from the frontend.
    Expects JSON payload: {"token": "google_id_token_here"}
    Returns an application access token upon successful verification.
    """
    if not request.is_json:
        return error_response("Request must be JSON", 400)

    data = request.get_json()
    google_token = data.get('token')

    if not google_token:
        return error_response("Missing Google ID token in request", 400)

    # Verify the token using the auth service
    idinfo = await auth_service.verify_google_id_token(google_token)
    if not idinfo:
        return error_response("Invalid or expired Google token", 401)

    # Get or create the user based on the verified Google info
    user = await auth_service.get_or_create_google_user(idinfo)
    if not user:
        # Handle potential errors like email conflict with different google_id
        logging.error(f"Failed to get or create user from Google info: {idinfo.get('email')}")
        return error_response("Failed to process Google sign-in", 500) # Or maybe 409 Conflict?

    # Issue an application access token for the user
    access_token_expires = timedelta(minutes=auth_service.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.email, "user_id": user.id}, expires_delta=access_token_expires
    )

    return success_response({"access_token": access_token, "token_type": "bearer"})


# --- Placeholder for Google OAuth Login (Full Flow - Not Used Here) ---
# @auth_bp.route('/login/google_oauth', methods=['GET'])
# async def login_google_oauth():
#     """Redirects user to Google for authentication."""
#     # Construct Google OAuth URL and redirect using Flask's redirect
#     pass

# @auth_bp.route('/callback/google', methods=['GET'])
# async def callback_google():
#     """Handles the callback from Google after authentication."""
#     code = request.args.get('code')
#     if not code:
#         return error_response("Missing authorization code from Google", 400)
#     # 1. Exchange code for Google tokens
#     # 2. Get user profile info from Google
#     # 3. Use auth_service.get_or_create_google_user
#     # 4. Create access token for the user
#     # 5. Return token (or redirect to frontend with token)
#     pass

# --- Placeholder for getting current user (requires token verification decorator/middleware) ---
# from ..utils.decorators import token_required # Need to create this decorator
# @auth_bp.route('/users/me', methods=['GET'])
# @token_required
# async def read_users_me(current_user: User): # Decorator would inject the user
#     """Gets the current logged-in user's details."""
#     user_dict = current_user.dict(exclude={'password_hash', 'google_id'})
#     return success_response(user_dict)
