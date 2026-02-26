from fastapi import FastAPI
from app.routes import courses

app = FastAPI(title="Course Platform API")

app.include_router(courses.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "API is running. Go to /docs for Swagger"}