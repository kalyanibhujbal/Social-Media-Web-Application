import uuid
import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import db_manager
from app.core.security import hash_password
from app.api.v1.router import api_router
from app.services.retention import run_retention_loop

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.ENVIRONMENT.lower() == "production" and (
        len(settings.JWT_SECRET) < 32
        or settings.JWT_SECRET.startswith("DEFAULT_INSECURE")
        or settings.JWT_SECRET.startswith("CHANGE_THIS")
    ):
        raise RuntimeError("Production requires a unique JWT_SECRET of at least 32 characters.")

    # Connect Database
    await db_manager.connect()
    
    # Create a bootstrap administrator only when the operator explicitly
    # supplies credentials. There are no built-in demo accounts.
    admin_email = settings.INITIAL_ADMIN_EMAIL
    admin_pw = settings.INITIAL_ADMIN_PASSWORD

    if admin_email and admin_pw and db_manager.use_mongo and db_manager.db is not None:
        admin = await db_manager.db["users"].find_one({"email": admin_email})
        if not admin:
            if settings.ENVIRONMENT.lower() == "production" and (
                admin_email.lower() == "admin@moderation.local"
                or admin_pw == "ChangeMeAdmin123!"
                or len(admin_pw) < 14
            ):
                raise RuntimeError("Production bootstrap credentials must be unique and at least 14 characters.")
            await db_manager.db["users"].insert_one({
                "id": str(uuid.uuid4()),
                "username": "admin",
                "email": admin_email,
                "password_hash": hash_password(admin_pw),
                "role": "ADMIN",
                "terms_accepted": False,
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            logger.info("Created explicitly configured bootstrap administrator in MongoDB.")
    elif admin_email and admin_pw and not db_manager.use_mongo:
        admin = next((u for u in db_manager._collections["users"] if u["email"] == admin_email), None)
        if not admin:
            db_manager._collections["users"].append({
                "id": str(uuid.uuid4()),
                "username": "admin",
                "email": admin_email,
                "password_hash": hash_password(admin_pw),
                "role": "ADMIN",
                "terms_accepted": False,
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            logger.info("Created explicitly configured bootstrap administrator in memory.")

    retention_task = asyncio.create_task(run_retention_loop())
    try:
        yield
    finally:
        retention_task.cancel()
        try:
            await retention_task
        except asyncio.CancelledError:
            pass
        await db_manager.disconnect()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API server for AI-Driven Content Moderation & Explainable Hate Speech Detection",
    lifespan=lifespan
)


@app.middleware("http")
async def prevent_api_caching(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/v1/"):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
    return response

# Secure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router, prefix="/api/v1")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Avoid putting request values or content into application logs.
    logger.error("Unhandled request exception (%s).", type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please contact system support."}
    )

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": "MongoDB" if db_manager.use_mongo else "In-Memory Fallback"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
