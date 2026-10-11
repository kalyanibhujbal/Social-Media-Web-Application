from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from typing import Dict, Any
from app.core.security import decode_access_token
from app.core.database import db_manager

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

async def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
) -> Dict[str, Any]:
    cookie_token = request.cookies.get("moderation_session")
    if not token:
        token = cookie_token
        if token and request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            from app.core.config import settings
            if origin and origin not in settings.FRONTEND_ORIGINS:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Request origin is not allowed for this session.",
                )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    
    user = None
    if db_manager.use_mongo and db_manager.db is not None:
        user = await db_manager.db["users"].find_one({"id": user_id})
    else:
        user = next((u for u in db_manager._collections["users"] if u["id"] == user_id), None)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
        )
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive.",
        )
    return user


async def get_optional_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
) -> Dict[str, Any] | None:
    """Resolve an optional session for public feed personalization."""
    try:
        return await get_current_user(request, token)
    except HTTPException:
        return None

async def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if current_user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required to perform this action.",
        )
    return current_user


async def require_moderator_or_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if current_user.get("role") not in {"MODERATOR", "ADMIN"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator privileges are required to review content.",
        )
    return current_user
