from sanic.response import json
from typing import Tuple, Dict, Any, Optional

def create_error_response(message: str, status_code: int = 500, extra_data: Optional[Dict[str, Any]] = None) -> Tuple[Any, int]:
    """
    Standardized error response helper for Sanic
    
    Args:
        message: Error message
        status_code: HTTP status code
        extra_data: Additional data to include in the response
        
    Returns:
        Sanic response with CORS headers and status code
    """
    response_data = {
        'success': False,
        'error': message
    }
    if extra_data:
        response_data.update(extra_data)
    
    return json(response_data, status=status_code, headers={
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Accept',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
    }), status_code


def success_response(data: Dict[str, Any] = None, status_code: int = 200) -> Tuple[Any, int]:
    """
    Standardized success response helper for Sanic
    
    Args:
        data: Data to include in the response
        status_code: HTTP status code
        
    Returns:
        Sanic response with CORS headers and status code
    """
    if data is None:
        data = {}
        
    response_data = {
        'success': True,
        'data': data
    }
    
    return json(response_data, status=status_code, headers={
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Accept',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
    }), status_code


def error_response(message: str, status_code: int = 500, extra_data: Optional[Dict[str, Any]] = None) -> Tuple[Any, int]:
    """
    Alias for create_error_response for consistency with success_response
    """
    return create_error_response(message, status_code, extra_data)
