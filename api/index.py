from fastapi import FastAPI
from fastapi.responses import JSONResponse
from api.routes.health import router as health_router
from api.routes.chapters import router as chapters_router
from api.routes.auth import router as auth_router
from api.routes.credits import router as credits_router
from api.routes.payment import router as payment_router

app = FastAPI()

app.include_router(health_router)
app.include_router(chapters_router)
app.include_router(auth_router, prefix="/auth")
app.include_router(credits_router, prefix="/credits")
app.include_router(payment_router, prefix="/payment")

@app.get('/')
@app.get('/<path:path>')
async def index(path=""):
    return JSONResponse(content={'hello': path})
