import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from pydantic import ValidationError as PydanticValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from api.utils.exceptions import AuthenticationError

try:
    from stripe.error import StripeError
except ImportError:
    class StripeError(Exception):
        pass


def error_response(message, status_code=400, details=None):
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": message,
            **({"details": details} if details else {})
        },
    )


def register_exception_handlers(app):
    @app.exception_handler(PydanticValidationError)
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc):
        logging.warning(f"Validation error: {exc}")
        return error_response("Validation failed", status.HTTP_422_UNPROCESSABLE_ENTITY, details=str(exc))

    @app.exception_handler(AuthenticationError)
    async def authentication_exception_handler(request: Request, exc):
        logging.warning(f"Authentication error: {exc}")
        return error_response(str(exc), status.HTTP_401_UNAUTHORIZED)

    @app.exception_handler(StripeError)
    async def stripe_exception_handler(request: Request, exc):
        logging.error(f"Stripe error: {exc}")
        return error_response("Payment processing error", status.HTTP_402_PAYMENT_REQUIRED, details=str(exc))

    @app.exception_handler(HTTPException)
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc):
        logging.warning(f"HTTP error: {exc.detail if hasattr(exc, 'detail') else exc}")
        return error_response(
            getattr(exc, 'detail', str(exc)),
            getattr(exc, 'status_code', status.HTTP_400_BAD_REQUEST)
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc):
        logging.exception(f"Unexpected error: {exc}")
        return error_response("Internal server error", status.HTTP_500_INTERNAL_SERVER_ERROR)
