"""
Custom exceptions for the API.
"""

class RedisConnectionError(ConnectionError):
    """Exception raised when a Redis connection fails."""
    def __init__(self, message="Failed to connect to Redis", original_error=None):
        self.original_error = original_error
        super().__init__(f"{message}: {str(original_error)}" if original_error else message)

class RedisOperationError(Exception):
    """Exception raised when a Redis operation fails."""
    def __init__(self, operation, message="Redis operation failed", original_error=None):
        self.operation = operation
        self.original_error = original_error
        error_msg = f"{message} (operation: {operation})"
        if original_error:
            error_msg += f": {str(original_error)}"
        super().__init__(error_msg)

class ConfigurationError(ValueError):
    """Exception raised when a configuration value is missing or invalid."""
    def __init__(self, config_key, message=None):
        self.config_key = config_key
        super().__init__(message or f"Missing or invalid configuration: {config_key}")

class AuthenticationError(Exception):
    """Exception raised when authentication fails."""
    def __init__(self, message="Authentication failed", status_code=401):
        self.status_code = status_code
        super().__init__(message)

class AuthorizationError(Exception):
    """Exception raised when a user is not authorized to perform an action."""
    def __init__(self, message="Not authorized to perform this action", status_code=403):
        self.status_code = status_code
        super().__init__(message)

class ResourceNotFoundError(Exception):
    """Exception raised when a requested resource is not found."""
    def __init__(self, resource_type, resource_id=None, status_code=404):
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.status_code = status_code
        message = f"{resource_type} not found"
        if resource_id:
            message += f": {resource_id}"
        super().__init__(message)

class ValidationError(Exception):
    """Exception raised when input validation fails."""
    def __init__(self, message="Validation failed", errors=None, status_code=400):
        self.errors = errors or {}
        self.status_code = status_code
        super().__init__(message)
