from flask import request, current_app
from datetime import timedelta
import logging

# Import services and utilities
from ..config import Config
from ..services import auth_service, credits_service
from ..models.user import UserCreate, UserLogin
from ..utils.responses import success_response, error_response
from ..utils.decorators import token_required
from ..utils.exceptions import AuthenticationError, ValidationError
from ..utils.versioning import VersionedBlueprint

# Create a versioned blueprint
auth_bp = VersionedBlueprint('auth', __name__, url_prefix='/auth')

# Debug endpoint to check if auth blueprint is registered
@auth_bp.route('/debug', methods=['GET'])
def auth_debug():
    """Debug endpoint to verify auth blueprint is registered"""
    logging.info("Auth debug endpoint accessed")
    from flask import current_app

    # Get all routes from the Flask app that belong to this blueprint
    blueprint_routes = []
    for rule in current_app.url_map.iter_rules():
        if rule.endpoint.startswith('auth.'):
            blueprint_routes.append({
                'endpoint': rule.endpoint,
                'methods': [method for method in rule.methods if method not in ['HEAD', 'OPTIONS']],
                'path': str(rule)
            })

    return success_response({
        "status": "Auth blueprint is working",
        "routes": blueprint_routes,
        "blueprint_name": auth_bp.name,
        "url_prefix": auth_bp.url_prefix,
        "total_routes": len(blueprint_routes)
    })

@auth_bp.route('/register', methods=['POST'])
async def register_user():
    """
    Registers a new user with email and password.
    """
    if not request.is_json:
        return error_response("Request must be JSON", 400)

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


# --- Google Sign-In (Chrome Extension OAuth Token only) ---
@auth_bp.route('/login/google', methods=['POST'])
async def login_via_google():
    """
    Authenticates a user via a Google OAuth token from Chrome extension.
    Expects JSON payload: {"token": "google_token_here", "platform": "chrome_extension"}
    Returns an application access token upon successful verification.
    """
    logging.info("Google login request received at /auth/login/google endpoint")
    logging.info(f"Processing login request with blueprint: {auth_bp.name}, prefix: {auth_bp.url_prefix}")

    # Validate request format
    if not request.is_json:
        logging.error("Request is not JSON")
        return error_response("Request must be JSON", 400)

    # Parse request data
    try:
        data = request.get_json()
        logging.info(f"Request data: {data}")

        google_token = data.get('token')
        platform = data.get('platform', 'web')  # Default to 'web' if platform not specified

        if not google_token:
            logging.error("Missing Google token in request")
            return error_response("Missing Google token in request", 400)

        logging.info(f"Processing Google login with platform: {platform}")

        # Only accept chrome_extension platform
        if platform != "chrome_extension":
            logging.warning(f"Received Google login request with unsupported platform: {platform}")
            return error_response("Only Chrome extension login is supported.", 400)
    except Exception as e:
        logging.error(f"Error parsing request data: {str(e)}")
        return error_response("Invalid request format", 400)

    # Verify Google OAuth token
    try:
        logging.info("Verifying Google OAuth token from Chrome extension...")
        user_info = await auth_service.verify_google_oauth_token(google_token)
        logging.info(f"Google OAuth token verification successful: {user_info.get('email') if user_info else 'No user info'}")

        if not user_info:
            logging.error("Failed to verify Google token - no user info returned")
            return error_response("Invalid or expired Google token", 401)
    except AuthenticationError as e:
        logging.error(f"Authentication error verifying Google token: {str(e)}")
        return error_response(str(e), 401)
    except Exception as e:
        logging.error(f"Unexpected error verifying Google OAuth token: {str(e)}")
        return error_response(f"Error verifying Google token: {str(e)}", 500)

    # Get or create the user based on the verified Google info
    try:
        logging.info(f"Getting or creating user for Google ID: {user_info.get('sub')}")
        user_result = await auth_service.get_or_create_google_user(user_info)
    except ValidationError as e:
        logging.error(f"Validation error creating user: {str(e)}")
        return error_response(f"Invalid user data: {str(e)}", 400)
    except Exception as e:
        logging.error(f"Unexpected error creating user: {str(e)}")
        return error_response(f"Error creating user: {str(e)}", 500)

    # Process the user result
    try:
        # Check if we got a tuple (user, is_new_user) or just a user object
        if isinstance(user_result, tuple) and len(user_result) == 2:
            user, is_new_user = user_result
            logging.info(f"User result: user={user.email}, is_new_user={is_new_user}")
        else:
            user = user_result
            is_new_user = False
            logging.info(f"User result: user={user.email if user else None}, is_new_user=False")

        if not user:
            # Handle potential errors like email conflict with different google_id
            logging.error(f"Failed to get or create user from Google info: {user_info.get('email')}")
            return error_response("Failed to process Google sign-in", 500)

        # Login the user and generate response data
        logging.info(f"Logging in user: {user.email}")
        login_result = await auth_service.login_user(user)

        # Add the new_user flag to the response
        login_result["new_user"] = is_new_user

        logging.info(f"Google login successful for user: {user.email}")
        return success_response(login_result)
    except AuthenticationError as e:
        logging.error(f"Authentication error during login: {str(e)}")
        return error_response(str(e), 401)
    except Exception as e:
        logging.error(f"Unexpected error during login process: {str(e)}")
        return error_response(f"Error during login process: {str(e)}", 500)


# --- Token Verification Endpoint ---
@auth_bp.route('/verify', methods=['POST'])
async def verify_token():
    """
    Verifies if a token is valid.
    Expects JSON payload: {"token": "jwt_token_here"}
    Returns: {"valid": true/false}
    """
    # Validate request format
    if not request.is_json:
        return error_response("Request must be JSON", 400)

    try:
        data = request.get_json()
        token = data.get('token')

        if not token:
            return error_response("Missing token in request", 400)
    except Exception as e:
        logging.error(f"Error parsing request data: {str(e)}")
        return error_response("Invalid request format", 400)

    # Verify the token
    try:
        # Validate the token
        await auth_service.validate_token(token)

        # Get the user
        user = await auth_service.get_current_user(token)

        # Token is valid and user exists
        return success_response({
            "valid": True,
            "user_id": user.id,
            "email": user.email
        })
    except AuthenticationError:
        # Token is invalid
        return success_response({"valid": False})
    except Exception as e:
        logging.error(f"Unexpected error verifying token: {str(e)}")
        return success_response({"valid": False})


# --- User Info Endpoint ---
@auth_bp.route('/user', methods=['GET'])
@token_required
async def get_user_info():
    """
    Returns information about the authenticated user.
    Requires a valid JWT token in the Authorization header.
    """
    try:
        # Get the token from the request
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return error_response("Missing or invalid Authorization header", 401)

        token = auth_header.split(' ')[1]

        # Get the user from the token
        user = await auth_service.get_current_user(token)
        if not user:
            return error_response("User not found", 404)

        # Get user's credit balance
        try:
            credits = await credits_service.get_credit_balance(user.id)
        except Exception as e:
            logging.error(f"Error fetching credit balance for user {user.id}: {e}")
            credits = 0  # Default to 0 if there's an error

        # Create user info response
        user_info = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "email_verified": getattr(user, 'email_verified', True),
            "credits": credits,
            "picture": user.picture,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }

        return success_response(user_info)
    except AuthenticationError as e:
        logging.error(f"Authentication error: {str(e)}")
        return error_response("Authentication error", 401)
    except Exception as e:
        logging.error(f"Error getting user info: {str(e)}")
        return error_response("Error retrieving user information", 500)


# --- Endpoint to provide Google Client ID to frontend/extension ---
@auth_bp.route('/config', methods=['GET'])
async def get_auth_config():
    """
    Provides necessary configuration for authentication to the frontend/extension.
    Currently returns the Google Client ID.
    """
    return success_response({
        "googleClientId": Config.GOOGLE_CLIENT_ID
    })
