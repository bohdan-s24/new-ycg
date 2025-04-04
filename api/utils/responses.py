from typing import Tuple, Dict, Any, Optional
from flask import jsonify


def create_error_response(message: str, status_code: int = 500, extra_data: Optional[Dict[str, Any]] = None) -> Tuple[Any, int]:
    """
    Standardized error response helper
    
    Args:
        message: Error message
        status_code: HTTP status code
        extra_data: Additional data to include in the response
        
    Returns:
        Flask response with CORS headers and status code
    """
    response_data = {
        'success': False,
        'error': message
    }
    if extra_data:
        response_data.update(extra_data)
    
    response_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Accept',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }
    
    response = jsonify(response_data)
    for key, value in response_headers.items():
        response.headers.add(key, value)
    
    return response, status_code
