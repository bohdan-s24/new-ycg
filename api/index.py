from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from api.routes.health import router as health_router
from api.routes.chapters import router as chapters_router
from api.routes.auth import router as auth_router
from api.routes.credits import router as credits_router
from api.routes.payment import router as payment_router
from api.errors import register_exception_handlers
import os
import logging

app = FastAPI()
register_exception_handlers(app)

api_prefix = "/v1"

# Set up SlowAPI Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Register SlowAPI exception handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(status_code=429, content={"success": False, "error": "Rate limit exceeded"})

app.include_router(health_router, prefix=api_prefix)
app.include_router(chapters_router, prefix=api_prefix)
app.include_router(auth_router, prefix=f"{api_prefix}/auth")
app.include_router(credits_router, prefix=f"{api_prefix}/credits")
app.include_router(payment_router, prefix=f"{api_prefix}/payment")

@app.get('/')
@app.get('/<path:path>')
async def index(path=""):
    return JSONResponse(content={'hello': path})
