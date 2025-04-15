from fastapi import FastAPI
from fastapi.responses import JSONResponse
from api.routes.health import router as health_router
from api.routes.chapters import router as chapters_router

app = FastAPI()

app.include_router(health_router)
app.include_router(chapters_router)

@app.get('/')
@app.get('/<path:path>')
async def index(path=""):
    return JSONResponse(content={'hello': path})
