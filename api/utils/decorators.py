from functools import wraps
from flask import request, g, current_app
import logging

from ..services import auth_service
from ..utils.responses import error_response

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
            # Decode token
            payload = auth_service.decode_access_token(token)
            if payload is None:
                return error_response('Token is invalid or expired!', 401)
            
            user_email = payload.get('sub') # 'sub' usually holds the username/email
            user_id = payload.get('user_id') # Get user_id if included during token creation

            if not user_id:
                 # Fallback to email if user_id wasn't in token (though it should be)
                 if not user_email:
                     logging.error("Token payload missing 'sub' (email) and 'user_id'.")
                     return error_response('Invalid token payload!', 401)
                 # If only email is present, we might need to fetch the user to get the ID
                 # For now, assume user_id is primary identifier needed by services
                 logging.warning(f"Token payload missing 'user_id', using email '{user_email}' for lookup if needed.")
                 # Depending on service needs, you might fetch user here based on email
                 # current_user = await auth_service.get_user_by_email(user_email)
                 # if not current_user:
                 #    return error_response('User not found!', 401)
                 # g.current_user_id = current_user.id # Store ID if fetched
                 # g.current_user_email = user_email
                 return error_response('Token payload missing user_id!', 401) # Require user_id for simplicity now
            
            # Store user info in Flask's application context `g` for access in the route
            g.current_user_id = user_id
            g.current_user_email = user_email # Store email too if needed

        except Exception as e:
            logging.error(f"Token validation error: {e}")
            return error_response('Token validation failed!', 401)

        return await f(*args, **kwargs) # Call the original async route function

    return decorated_function
