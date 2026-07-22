from fastapi import FastAPI

from app.routers.user import router as user_router

app = FastAPI()

app.include_router(user_router)


@app.get("/")
async def root() -> dict:
    return {
        "message": "User Profile Cache API is Running"
    }

@app.get("/health")
async def health_check() -> dict:
    return {
        "status": "healthy"
    }