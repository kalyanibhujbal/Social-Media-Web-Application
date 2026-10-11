import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import db_manager
from app.middleware.rate_limit import rate_limit_check
from app.schemas.moderation import (
    ConsentRequest,
    DeleteAccountRequest,
    PrivacyRequestCreate,
    PrivacyRequestResponse,
)
from app.services.audit_logger import audit_logger

router = APIRouter()


@router.get("/contact")
async def public_privacy_contact():
    """Expose only operator contact fields that have replaced their placeholders."""
    def configured(value: str | None) -> str | None:
        if not value or value.strip().startswith("["):
            return None
        return value.strip()

    return {
        "organization_name": configured(settings.ORGANIZATION_NAME),
        "official_email": configured(settings.OFFICIAL_EMAIL),
        "official_address": configured(settings.OFFICIAL_ADDRESS),
        "grievance_contact": configured(settings.GRIEVANCE_CONTACT),
    }


def _without_database_id(item: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if key != "_id"}


async def _owned_rows(collection_name: str, user_id: str) -> list[dict[str, Any]]:
    if db_manager.use_mongo and db_manager.db is not None:
        return await db_manager.db[collection_name].find({"author_id": user_id}).to_list(length=None)
    return [
        row for row in db_manager._collections.get(collection_name, [])
        if row.get("author_id") == user_id
    ]


async def _matching_rows(collection_name: str, mongo_query: dict, memory_predicate) -> list[dict[str, Any]]:
    if db_manager.use_mongo and db_manager.db is not None:
        return await db_manager.db[collection_name].find(mongo_query).to_list(length=None)
    return [row for row in db_manager._collections.get(collection_name, []) if memory_predicate(row)]


@router.post("/consent")
async def record_consent(
    req: ConsentRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Record only the signed-in user's optional analytics preference."""
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=20, window_seconds=60)
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "consent_type": "analytics_cookies",
        "status": "GRANTED" if req.analytics_cookies else "WITHDRAWN",
        "policy_version": settings.PRIVACY_POLICY_VERSION,
        "timestamp": now,
    }
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["consent_records"].update_one(
            {"user_id": current_user["id"], "consent_type": "analytics_cookies"},
            {"$set": {key: value for key, value in record.items() if key != "id"}, "$setOnInsert": {"id": record["id"]}},
            upsert=True,
        )
    else:
        db_manager._collections["consent_records"] = [
            existing for existing in db_manager._collections["consent_records"]
            if existing.get("user_id") != current_user["id"] or existing.get("consent_type") != "analytics_cookies"
        ]
        db_manager._collections["consent_records"].append(record)
    return {"status": "success", "saved": True}


@router.get("/export-data")
async def export_user_data(request: Request, current_user: dict = Depends(get_current_user)):
    """Return an export limited to the authenticated account and its records."""
    user_id = current_user["id"]
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=10, window_seconds=60)
    posts = await _owned_rows("posts", user_id)
    comments = await _owned_rows("comments", user_id)
    content_ids = [item.get("id") for item in posts + comments if item.get("id")]

    if db_manager.use_mongo and db_manager.db is not None:
        logs = await db_manager.db["moderation_logs"].find({
            "$or": [
                {"content_id": {"$in": content_ids}},
                {"post_id": {"$in": content_ids}},
            ]
        }).to_list(length=None) if content_ids else []
        consent = await db_manager.db["consent_records"].find({"user_id": user_id}).to_list(length=None)
        requests = await db_manager.db["privacy_requests"].find({"user_id": user_id}).to_list(length=None)
        connections = await db_manager.db["connections"].find({"$or": [{"requester_id": user_id}, {"recipient_id": user_id}]}).to_list(length=None)
        follows = await db_manager.db["follows"].find({"$or": [{"follower_id": user_id}, {"following_id": user_id}]}).to_list(length=None)
        notifications = await db_manager.db["notifications"].find({"$or": [{"recipient_id": user_id}, {"actor_id": user_id}]}).to_list(length=None)
        conversations = await db_manager.db["conversations"].find({"member_ids": user_id}).to_list(length=None)
        conversation_ids = [row["id"] for row in conversations]
        messages = await db_manager.db["messages"].find({"conversation_id": {"$in": conversation_ids}}).to_list(length=None) if conversation_ids else []
        post_likes = await db_manager.db["post_likes"].find({"user_id": user_id}).to_list(length=None)
        comment_likes = await db_manager.db["comment_likes"].find({"user_id": user_id}).to_list(length=None)
        saved_posts = await db_manager.db["saved_posts"].find({"user_id": user_id}).to_list(length=None)
    else:
        logs = [
            row for row in db_manager._collections.get("moderation_logs", [])
            if row.get("content_id") in content_ids or row.get("post_id") in content_ids
        ]
        consent = [
            row for row in db_manager._collections.get("consent_records", [])
            if row.get("user_id") == user_id
        ]
        requests = [
            row for row in db_manager._collections.get("privacy_requests", [])
            if row.get("user_id") == user_id
        ]
        connections = [row for row in db_manager._collections.get("connections", []) if user_id in {row.get("requester_id"), row.get("recipient_id")}]
        follows = [row for row in db_manager._collections.get("follows", []) if user_id in {row.get("follower_id"), row.get("following_id")}]
        notifications = [row for row in db_manager._collections.get("notifications", []) if user_id in {row.get("recipient_id"), row.get("actor_id")}]
        conversations = [row for row in db_manager._collections.get("conversations", []) if user_id in row.get("member_ids", [])]
        conversation_ids = [row["id"] for row in conversations]
        messages = [row for row in db_manager._collections.get("messages", []) if row.get("conversation_id") in conversation_ids]
        post_likes = [row for row in db_manager._collections.get("post_likes", []) if row.get("user_id") == user_id]
        comment_likes = [row for row in db_manager._collections.get("comment_likes", []) if row.get("user_id") == user_id]
        saved_posts = [row for row in db_manager._collections.get("saved_posts", []) if row.get("user_id") == user_id]

    await audit_logger.log_event(
        actor_id=user_id,
        actor_role=current_user["role"],
        event_type="DATA_EXPORT_REQUEST",
        details="User exported their account data.",
    )

    return {
        "user_profile": {
            "id": current_user["id"],
            "username": current_user["username"],
            "email": current_user["email"],
            "terms_accepted": current_user.get("terms_accepted", False),
            "created_at": current_user["created_at"],
            "full_name": current_user.get("full_name"),
            "headline": current_user.get("headline"),
            "location": current_user.get("location"),
            "about": current_user.get("about"),
            "skills": current_user.get("skills", []),
        },
        "posts": [_without_database_id(row) for row in posts],
        "comments": [_without_database_id(row) for row in comments],
        "moderation_history": [_without_database_id(row) for row in logs],
        "consent_preferences": [_without_database_id(row) for row in consent],
        "privacy_requests": [_without_database_id(row) for row in requests],
        "connections": [_without_database_id(row) for row in connections],
        "follows": [_without_database_id(row) for row in follows],
        "notifications": [_without_database_id(row) for row in notifications],
        "conversations": [_without_database_id(row) for row in conversations],
        "messages": [_without_database_id(row) for row in messages],
        "post_likes": [_without_database_id(row) for row in post_likes],
        "comment_likes": [_without_database_id(row) for row in comment_likes],
        "saved_posts": [_without_database_id(row) for row in saved_posts],
        "processing_summary": [
            "Account details are used for account access and profile display.",
            "Posts and comments are stored and processed for moderation and feed features.",
            "Direct messages are stored to provide private conversations between connected accounts; message content is not sent to the moderation classifier.",
            "Moderation predictions and review outcomes are stored with the associated content.",
            "Optional analytics cookies and tracking are not currently used by this application.",
            "User content is not used to train models.",
        ],
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/requests", response_model=PrivacyRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_privacy_request(
    req: PrivacyRequestCreate,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=20, window_seconds=60)
    rate_limit_check(f"privacy-user:{user_id}", max_requests=10, window_seconds=24 * 60 * 60)

    now = datetime.now(timezone.utc).isoformat()
    record = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "request_type": req.request_type,
        "description": (req.description or "").strip() or None,
        "status": "OPEN",
        "created_at": now,
        "resolved_at": None,
    }
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["privacy_requests"].insert_one(record)
    else:
        db_manager._collections["privacy_requests"].append(record)

    await audit_logger.log_event(
        actor_id=user_id,
        actor_role=current_user["role"],
        event_type="PRIVACY_REQUEST_SUBMITTED",
        resource_id=record["id"],
        details=f"Privacy request submitted: {req.request_type}.",
    )
    return PrivacyRequestResponse(**record)


@router.get("/requests/me", response_model=list[PrivacyRequestResponse])
async def list_my_privacy_requests(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=30, window_seconds=60)
    if db_manager.use_mongo and db_manager.db is not None:
        rows = await db_manager.db["privacy_requests"].find({"user_id": user_id}).sort("created_at", -1).to_list(length=100)
    else:
        rows = sorted(
            (row for row in db_manager._collections["privacy_requests"] if row.get("user_id") == user_id),
            key=lambda row: row.get("created_at", ""),
            reverse=True,
        )[:100]
    return [PrivacyRequestResponse(**_without_database_id(row)) for row in rows]


@router.post("/delete-account")
async def delete_user_account(
    req: DeleteAccountRequest,
    request: Request,
    response: Response,
    current_user: dict = Depends(get_current_user),
):
    """Delete the account and owned content, and anonymize retained audit rows."""
    if not req.confirm_deletion:
        raise HTTPException(status_code=400, detail="Confirm account deletion before continuing.")
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=3, window_seconds=60)
    user_id = current_user["id"]
    owned_posts = await _owned_rows("posts", user_id)
    owned_comments = await _owned_rows("comments", user_id)
    content_ids = [item.get("id") for item in owned_posts + owned_comments if item.get("id")]

    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["users"].delete_one({"id": user_id})
        await db_manager.db["posts"].delete_many({"author_id": user_id})
        await db_manager.db["comments"].delete_many({"author_id": user_id})
        if content_ids:
            await db_manager.db["moderation_logs"].delete_many({
                "$or": [
                    {"content_id": {"$in": content_ids}},
                    {"post_id": {"$in": content_ids}},
                ]
            })
            await db_manager.db["audit_logs"].update_many(
                {"resource_id": {"$in": content_ids}}, {"$set": {"resource_id": None}}
            )
        for item in owned_posts:
            await db_manager.db["audit_logs"].update_many(
                {"details": {"$regex": item["id"]}},
                {"$set": {"details": "Related content reference removed after account deletion."}},
            )
        await db_manager.db["consent_records"].delete_many({"user_id": user_id})
        await db_manager.db["privacy_requests"].delete_many({"user_id": user_id})
        await db_manager.db["connections"].delete_many({"$or": [{"requester_id": user_id}, {"recipient_id": user_id}]})
        await db_manager.db["follows"].delete_many({"$or": [{"follower_id": user_id}, {"following_id": user_id}]})
        await db_manager.db["notifications"].delete_many({"$or": [{"recipient_id": user_id}, {"actor_id": user_id}]})
        await db_manager.db["conversations"].delete_many({"member_ids": user_id})
        await db_manager.db["messages"].delete_many({"$or": [{"sender_id": user_id}, {"recipient_id": user_id}]})
        await db_manager.db["post_likes"].delete_many({"user_id": user_id})
        await db_manager.db["comment_likes"].delete_many({"user_id": user_id})
        await db_manager.db["saved_posts"].delete_many({"user_id": user_id})
        await db_manager.db["audit_logs"].update_many(
            {"actor_id": user_id}, {"$set": {"actor_id": "deleted-user"}}
        )
    else:
        for collection in (
            "users", "posts", "comments", "consent_records", "privacy_requests",
            "connections", "follows", "notifications", "conversations", "messages",
            "post_likes", "comment_likes", "saved_posts",
        ):
            db_manager._collections[collection] = [
                row for row in db_manager._collections.get(collection, [])
                if row.get("id") != user_id
                and row.get("author_id") != user_id
                and row.get("user_id") != user_id
                and row.get("requester_id") != user_id
                and row.get("recipient_id") != user_id
                and row.get("follower_id") != user_id
                and row.get("following_id") != user_id
                and row.get("actor_id") != user_id
                and row.get("sender_id") != user_id
                and user_id not in row.get("member_ids", [])
            ]
        db_manager._collections["moderation_logs"] = [
            row for row in db_manager._collections["moderation_logs"]
            if row.get("content_id") not in content_ids and row.get("post_id") not in content_ids
        ]
        for row in db_manager._collections["audit_logs"]:
            if row.get("resource_id") in content_ids:
                row["resource_id"] = None
            if row.get("actor_id") == user_id:
                row["actor_id"] = "deleted-user"
            if any(item.get("id") and item["id"] in row.get("details", "") for item in owned_posts):
                row["details"] = "Related content reference removed after account deletion."

    await audit_logger.log_event(
        actor_id="deleted-user",
        actor_role=current_user.get("role", "USER"),
        event_type="ACCOUNT_DELETED",
        details="Account and associated user content deleted.",
    )
    response.delete_cookie(
        key="moderation_session",
        path="/api/v1",
        httponly=True,
        secure=settings.ENVIRONMENT.lower() == "production",
        samesite="strict",
    )
    return {"status": "success", "message": "Account and associated user content deleted."}
