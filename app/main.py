from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
STATIC = BASE / "static"

app = FastAPI(title="Eagle Abstract homepage mock")

@app.get("/healthz")
def healthz():
    return JSONResponse({"ok": True, "service": "eagle-abstract-mock"})

@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")

app.mount("/", StaticFiles(directory=STATIC), name="static")
