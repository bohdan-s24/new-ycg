from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from api.routes.health import router as health_router
from api.routes.chapters import router as chapters_router
from api.routes.auth import router as auth_router
from api.routes.credits import router as credits_router
from api.routes.payment import router as payment_router
from api.errors import register_exception_handlers
import os

app = FastAPI()
register_exception_handlers(app)

api_prefix = "/v1"

@app.on_event("startup")
async def startup():
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        raise RuntimeError("REDIS_URL environment variable is required for rate limiting.")
    from redis.asyncio import from_url as redis_from_url
    redis = redis_from_url(redis_url, encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(redis)

app.include_router(health_router, prefix=api_prefix)
app.include_router(chapters_router, prefix=api_prefix, dependencies=[Depends(RateLimiter(times=5, seconds=60))])
app.include_router(auth_router, prefix=f"{api_prefix}/auth", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
app.include_router(credits_router, prefix=f"{api_prefix}/credits")
app.include_router(payment_router, prefix=f"{api_prefix}/payment", dependencies=[Depends(RateLimiter(times=10, seconds=60))])

@app.get('/')
@app.get('/<path:path>')
async def index(path=""):
    return JSONResponse(content={'hello': path})
