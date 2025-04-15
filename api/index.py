from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/health")
def health():
    return JSONResponse(content={"status": "ok"})

@app.get('/')
@app.get('/<path:path>')
async def index(path=""):
    return JSONResponse(content={'hello': path})
