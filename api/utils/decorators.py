from functools import wraps
from flask import request, g
import logging

from ..services import auth_service
from ..utils.responses import error_response
from ..utils.exceptions import AuthenticationError

def token_required(f):
    """
    Decorator to ensure a valid JWT token is present and load the user.
    Injects the user object into Flask's `g` context.
    """
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        token = None
        # Check for Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                # Expecting "Bearer <token>"
                token_type, token = auth_header.split()
                if token_type.lower() != 'bearer':
                    token = None # Invalid type
                    logging.warning("Invalid token type in Authorization header.")
            except ValueError:
                # Header format is wrong
                token = None
                logging.warning("Malformed Authorization header.")

        if not token:
            return error_response('Token is missing or invalid format!', 401)

        try:
            # Validate token and get user
            user = await auth_service.get_current_user(token)

            # Store user info in Flask's application context `g` for access in the route
            g.current_user = user
            g.current_user_id = user.id
            g.current_user_email = user.email

        except AuthenticationError as e:
            logging.error(f"Authentication error: {str(e)}")
            return error_response(str(e), 401)
        except Exception as e:
            logging.error(f"Unexpected error during token validation: {str(e)}")
            return error_response('Token validation failed!', 401)

        return await f(*args, **kwargs) # Call the original async route function

    return decorated_function
