from sanic.request import Request
from sanic.response import json

from sanic import exceptions as sanic_exceptions

from functools import wraps
import logging

from ..services import auth_service
from ..utils.responses import error_response
from ..utils.exceptions import AuthenticationError


def token_required(f):
    """
    Decorator to ensure a valid JWT token is present and load the user.
    Injects the user object into Sanic's `request.ctx` context.
    """
    @wraps(f)
    async def decorated_function(request: Request, *args, **kwargs):
        token = None
        # Check for Authorization header
        if 'authorization' in request.headers:
            auth_header = request.headers['authorization']
            try:
                # Expecting "Bearer <token>"
                token_type, token = auth_header.split()
                if token_type.lower() != 'bearer':
                    token = None  # Invalid type
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

            # Store user info in Sanic's request.ctx for access in the route
            request.ctx.current_user = user
            request.ctx.current_user_id = user.id
            request.ctx.current_user_email = user.email

        except AuthenticationError as e:
            logging.error(f"Authentication error: {str(e)}")
            return error_response(str(e), 401)
        except Exception as e:
            logging.error(f"Unexpected error during token validation: {str(e)}")
            return error_response('Token validation failed!', 401)

        return await f(request, *args, **kwargs)  # Call the original async route function

    return decorated_function
