from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional

def create_error_response(message: str, status_code: int = 500, extra_data: Optional[Dict[str, Any]] = None) -> JSONResponse:
    """
    Standardized error response helper for FastAPI
    
    Args:
        message: Error message
        status_code: HTTP status code
        extra_data: Additional data to include in the response
        
    Returns:
        FastAPI JSONResponse with status code
    """
    response_data = {
        'success': False,
        'error': message
    }
    if extra_data:
        response_data.update(extra_data)
    
    return JSONResponse(content=response_data, status_code=status_code)


def success_response(data: Dict[str, Any] = None, status_code: int = 200) -> JSONResponse:
    """
    Standardized success response helper for FastAPI
    
    Args:
        data: Data to include in the response
        status_code: HTTP status code
        
    Returns:
        FastAPI JSONResponse with status code
    """
    if data is None:
        data = {}
        
    response_data = {
        'success': True,
        'data': data
    }
    
    return JSONResponse(content=response_data, status_code=status_code)


def error_response(message: str, status_code: int = 500, extra_data: Optional[Dict[str, Any]] = None) -> JSONResponse:
    """
    Alias for create_error_response for consistency with success_response
    """
    return create_error_response(message, status_code, extra_data)
