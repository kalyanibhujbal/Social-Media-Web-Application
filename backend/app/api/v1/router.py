from fastapi import APIRouter
from app.api.v1.endpoints import auth, posts, comments, moderation, admin, privacy, dashboard, social

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["User Dashboard"])
api_router.include_router(posts.router, prefix="/posts", tags=["Social Posts & Moderation"])
api_router.include_router(comments.router, prefix="/comments", tags=["Comments & Moderation"])
api_router.include_router(moderation.router, prefix="/moderation", tags=["Interactive Moderation Sandbox"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin Queue & Analytics"])
api_router.include_router(privacy.router, prefix="/privacy", tags=["Privacy & Data Rights"])
api_router.include_router(social.router, tags=["Profiles, Network, Notifications & Messaging"])
