from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.routes import courses

app = FastAPI(title="Course Platform API")
BASE_DIR = Path(__file__).resolve().parent

app.include_router(courses.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "API is running. Go to /docs for Swagger"}


@app.get("/demo")
async def demo():
    return FileResponse(BASE_DIR / "static" / "demo.html")
