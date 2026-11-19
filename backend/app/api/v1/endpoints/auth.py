import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Depends, Request, Response
from app.schemas.auth import UserRegister, UserLogin, UserResponse, SessionResponse, ProfileUpdateRequest
from app.core.security import hash_password, verify_password, create_access_token
from app.core.database import db_manager
from app.api.deps import get_current_user, get_optional_current_user
from app.middleware.rate_limit import rate_limit_check
from app.core.config import settings
from app.services.audit_logger import audit_logger

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserRegister, request: Request):
    client_ip = request.client.host if request.client else "127.0.0.1"
    rate_limit_check(client_ip, max_requests=10, window_seconds=60)

    # 1. Require Terms Acceptance
    if not user_in.terms_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must review and accept the Terms & Conditions and Privacy Policy to register."
        )

    # 2. Check existing user
    if db_manager.use_mongo and db_manager.db is not None:
        existing = await db_manager.db["users"].find_one({"$or": [{"email": user_in.email}, {"username": user_in.username}]})
    else:
        existing = next((u for u in db_manager._collections["users"] if u["email"] == user_in.email or u["username"] == user_in.username), None)

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. An account with this email or username already exists."
        )

    # 3. Create User Document with backend-controlled role ("USER")
    new_user = {
        "id": str(uuid.uuid4()),
        "username": user_in.username,
        "email": user_in.email,
        "full_name": (user_in.full_name or "").strip() or None,
        "headline": None,
        "location": None,
        "about": None,
        "skills": [],
        "password_hash": hash_password(user_in.password),
        "role": "USER",  # Backend enforced, never trust role from request
        "terms_accepted": True,
        "is_active": True,
        "is_private": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["users"].insert_one(new_user)
    else:
        db_manager._collections["users"].append(new_user)

    await audit_logger.log_event(
        actor_id=new_user["id"], actor_role="USER", event_type="ACCOUNT_REGISTERED",
        details="A new user account was registered.",
    )

    return UserResponse(**new_user)

@router.post("/login", response_model=SessionResponse)
async def login(user_in: UserLogin, request: Request, response: Response):
    client_ip = request.client.host if request.client else "127.0.0.1"
    rate_limit_check(client_ip, max_requests=10, window_seconds=60)

    if db_manager.use_mongo and db_manager.db is not None:
        user = await db_manager.db["users"].find_one({"email": user_in.email})
    else:
        user = next((u for u in db_manager._collections["users"] if u["email"] == user_in.email), None)

    # Generic non-enumerating error message to prevent user enumeration attacks
    if not user or not user.get("is_active", True) or not verify_password(user_in.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email address or password."
        )

    if not user["password_hash"].startswith("pbkdf2_sha256$"):
        upgraded_hash = hash_password(user_in.password)
        if db_manager.use_mongo and db_manager.db is not None:
            await db_manager.db["users"].update_one({"id": user["id"]}, {"$set": {"password_hash": upgraded_hash}})
        else:
            user["password_hash"] = upgraded_hash

    await audit_logger.log_event(
        actor_id=user["id"], actor_role=user.get("role", "USER"), event_type="LOGIN_SUCCEEDED",
        details="User signed in successfully.",
    )

    access_token = create_access_token(data={"sub": user["id"], "role": user["role"]})
    response.set_cookie(
        key="moderation_session",
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.ENVIRONMENT.lower() == "production",
        samesite="strict",
        path="/api/v1",
    )
    return SessionResponse(user=UserResponse(**user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, current_user: dict | None = Depends(get_optional_current_user)):
    if current_user:
        await audit_logger.log_event(
            actor_id=current_user["id"], actor_role=current_user.get("role", "USER"),
            event_type="LOGOUT", details="User signed out.",
        )
    response.delete_cookie(
        key="moderation_session",
        path="/api/v1",
        httponly=True,
        secure=settings.ENVIRONMENT.lower() == "production",
        samesite="strict",
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(**current_user)


@router.patch("/profile", response_model=UserResponse)
async def update_profile(
    profile: ProfileUpdateRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Allow an authenticated account holder to correct their profile data."""
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=10, window_seconds=60)
    if not verify_password(profile.current_password, current_user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Current password is incorrect.")

    updates = {}
    if profile.username is not None:
        updates["username"] = profile.username.strip()
    if profile.email is not None:
        updates["email"] = str(profile.email).lower()
    for field in ("full_name", "headline", "location", "about"):
        value = getattr(profile, field)
        if value is not None:
            cleaned = value.strip()
            updates[field] = cleaned or None
    if profile.skills is not None:
        updates["skills"] = [skill.strip() for skill in profile.skills]
    if profile.is_private is not None:
        updates["is_private"] = profile.is_private
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide a username or email to update.")

    for field, value in updates.items():
        if field not in {"username", "email"}:
            continue
        query = {field: value, "id": {"$ne": current_user["id"]}}
        if db_manager.use_mongo and db_manager.db is not None:
            duplicate = await db_manager.db["users"].find_one(query)
        else:
            duplicate = next((
                user for user in db_manager._collections["users"]
                if user.get("id") != current_user["id"] and user.get(field) == value
            ), None)
        if duplicate:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"That {field} is already in use.")

    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["users"].update_one({"id": current_user["id"]}, {"$set": updates})
    else:
        current_user.update(updates)

    if updates.get("is_private") is False:
        if db_manager.use_mongo and db_manager.db is not None:
            await db_manager.db["follows"].update_many(
                {"following_id": current_user["id"], "status": "PENDING"},
                {"$set": {"status": "ACCEPTED", "updated_at": datetime.now(timezone.utc).isoformat()}},
            )
        else:
            for follow in db_manager._collections.get("follows", []):
                if follow.get("following_id") == current_user["id"] and follow.get("status") == "PENDING":
                    follow.update({"status": "ACCEPTED", "updated_at": datetime.now(timezone.utc).isoformat()})

    await audit_logger.log_event(
        actor_id=current_user["id"],
        actor_role=current_user["role"],
        event_type="PROFILE_CORRECTED",
        details="User updated profile fields.",
    )
    return UserResponse(**{**current_user, **updates})
