"""
Global error handlers for the API.
"""

import logging
import traceback
from flask import jsonify, request
from werkzeug.exceptions import HTTPException

from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    RedisConnectionError,
    RedisOperationError,
    ResourceNotFoundError,
    ValidationError
)


def register_error_handlers(app):
    """
    Register error handlers for the Flask app.
    
    Args:
        app: The Flask application
    """
    @app.errorhandler(AuthenticationError)
    def handle_authentication_error(error):
        """Handle authentication errors."""
        logging.error(f"Authentication error: {str(error)}")
        response = {
            "success": False,
            "error": str(error),
            "error_type": "authentication_error"
        }
        return jsonify(response), 401
        
    @app.errorhandler(AuthorizationError)
    def handle_authorization_error(error):
        """Handle authorization errors."""
        logging.error(f"Authorization error: {str(error)}")
        response = {
            "success": False,
            "error": str(error),
            "error_type": "authorization_error"
        }
        return jsonify(response), error.status_code
        
    @app.errorhandler(ConfigurationError)
    def handle_configuration_error(error):
        """Handle configuration errors."""
        logging.error(f"Configuration error: {str(error)}")
        response = {
            "success": False,
            "error": f"Server configuration error: {error.config_key}",
            "error_type": "configuration_error"
        }
        return jsonify(response), 500
        
    @app.errorhandler(RedisConnectionError)
    def handle_redis_connection_error(error):
        """Handle Redis connection errors."""
        logging.error(f"Redis connection error: {str(error)}")
        response = {
            "success": False,
            "error": "Database connection error",
            "error_type": "database_error"
        }
        return jsonify(response), 500
        
    @app.errorhandler(RedisOperationError)
    def handle_redis_operation_error(error):
        """Handle Redis operation errors."""
        logging.error(f"Redis operation error: {str(error)}")
        response = {
            "success": False,
            "error": "Database operation error",
            "error_type": "database_error"
        }
        return jsonify(response), 500
        
    @app.errorhandler(ResourceNotFoundError)
    def handle_resource_not_found_error(error):
        """Handle resource not found errors."""
        logging.warning(f"Resource not found: {str(error)}")
        response = {
            "success": False,
            "error": str(error),
            "error_type": "not_found_error"
        }
        return jsonify(response), error.status_code
        
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        """Handle validation errors."""
        logging.warning(f"Validation error: {str(error)}")
        response = {
            "success": False,
            "error": str(error),
            "error_type": "validation_error",
            "errors": error.errors
        }
        return jsonify(response), error.status_code
        
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle HTTP exceptions."""
        logging.warning(f"HTTP error {error.code}: {error.description}")
        response = {
            "success": False,
            "error": error.description,
            "error_type": "http_error",
            "status_code": error.code
        }
        return jsonify(response), error.code
        
    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        """Handle all other exceptions."""
        # Log the full traceback for debugging
        logging.error(f"Unhandled exception: {str(error)}")
        logging.error(traceback.format_exc())
        
        # In production, don't expose internal error details
        response = {
            "success": False,
            "error": "An unexpected error occurred",
            "error_type": "server_error"
        }
        
        # In development, include more details
        if app.config.get('DEBUG', False):
            response["error_details"] = str(error)
            response["traceback"] = traceback.format_exc().split('\n')
            
        return jsonify(response), 500
        
    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 errors."""
        logging.warning(f"Not found: {request.path}")
        response = {
            "success": False,
            "error": f"The requested URL {request.path} was not found on this server",
            "error_type": "not_found_error"
        }
        return jsonify(response), 404
        
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """Handle 405 errors."""
        logging.warning(f"Method not allowed: {request.method} {request.path}")
        response = {
            "success": False,
            "error": f"The method {request.method} is not allowed for the URL {request.path}",
            "error_type": "method_not_allowed_error"
        }
        return jsonify(response), 405
