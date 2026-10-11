import re
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.deps import get_current_user, get_optional_current_user
from app.core.database import db_manager
from app.middleware.rate_limit import rate_limit_check
from app.schemas.social import (
    ConnectionRequestCreate,
    ConnectionSummary,
    ConversationCreate,
    MessageCreate,
    MessageResponse,
    NotificationResponse,
    PublicProfile,
)
from app.schemas.post import PostResponse
from app.services.audit_logger import audit_logger
from app.services.notifications import create_notification
from app.services.sanitizer import InputSanitizer

router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _find_one(collection: str, mongo_query: dict, memory_predicate):
    if db_manager.use_mongo and db_manager.db is not None:
        return await db_manager.db[collection].find_one(mongo_query)
    return next((row for row in db_manager._collections.get(collection, []) if memory_predicate(row)), None)


async def _find_many(collection: str, mongo_query: dict, memory_predicate, *, sort_key: str | None = None, reverse: bool = False, limit: int = 100):
    if db_manager.use_mongo and db_manager.db is not None:
        cursor = db_manager.db[collection].find(mongo_query)
        if sort_key:
            cursor = cursor.sort(sort_key, -1 if reverse else 1)
        return await cursor.limit(limit).to_list(length=limit)
    rows = [row for row in db_manager._collections.get(collection, []) if memory_predicate(row)]
    if sort_key:
        rows.sort(key=lambda row: str(row.get(sort_key) or ""), reverse=reverse)
    return rows[:limit]


async def _count(collection: str, mongo_query: dict, memory_predicate) -> int:
    if db_manager.use_mongo and db_manager.db is not None:
        return await db_manager.db[collection].count_documents(mongo_query)
    return sum(1 for row in db_manager._collections.get(collection, []) if memory_predicate(row))


async def _get_user(user_id: str):
    return await _find_one("users", {"id": user_id}, lambda row: row.get("id") == user_id)


def _public_user(user: dict) -> dict[str, Any]:
    return {
        "id": user["id"],
        "username": user["username"],
        "full_name": user.get("full_name"),
        "headline": user.get("headline"),
        "location": user.get("location"),
        "about": user.get("about"),
        "skills": user.get("skills", []),
        "created_at": user["created_at"],
    }


async def _relationship_summary(viewer_id: str, other_id: str) -> str:
    pair_key = ":".join(sorted((viewer_id, other_id)))
    connection = await _find_one("connections", {"pair_key": pair_key}, lambda row: row.get("pair_key") == pair_key)
    if connection:
        if connection.get("status") == "ACCEPTED":
            return "CONNECTED"
        if connection.get("status") == "PENDING":
            return "REQUEST_SENT" if connection.get("requester_id") == viewer_id else "REQUEST_RECEIVED"
    follows = await _find_one("follows", {"follower_id": viewer_id, "following_id": other_id}, lambda row: row.get("follower_id") == viewer_id and row.get("following_id") == other_id)
    return "FOLLOWING" if follows else "NONE"


async def _profile(user: dict, viewer_id: str | None = None) -> PublicProfile:
    user_id = user["id"]
    if db_manager.use_mongo and db_manager.db is not None:
        connections = await db_manager.db["connections"].count_documents({"$or": [{"requester_id": user_id}, {"recipient_id": user_id}], "status": "ACCEPTED"})
    else:
        connections = sum(1 for row in db_manager._collections["connections"] if user_id in {row.get("requester_id"), row.get("recipient_id")} and row.get("status") == "ACCEPTED")
    followers = await _count("follows", {"following_id": user_id}, lambda row: row.get("following_id") == user_id)
    following = await _count("follows", {"follower_id": user_id}, lambda row: row.get("follower_id") == user_id)
    relationship = await _relationship_summary(viewer_id, user_id) if viewer_id and viewer_id != user_id else "SELF" if viewer_id == user_id else "NONE"
    return PublicProfile(**{
        **_public_user(user),
        "connection_count": connections,
        "follower_count": followers,
        "following_count": following,
        "relationship": relationship,
    })


@router.get("/users/search", response_model=list[PublicProfile])
async def search_users(
    request: Request,
    q: str = Query(..., min_length=2, max_length=80),
    current_user: dict = Depends(get_current_user),
):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=30, window_seconds=60)
    query = q.strip()
    if len(query) < 2:
        return []
    escaped = re.escape(query)
    rows = await _find_many(
        "users",
        {"is_active": {"$ne": False}, "$or": [{"username": {"$regex": escaped, "$options": "i"}}, {"full_name": {"$regex": escaped, "$options": "i"}}, {"headline": {"$regex": escaped, "$options": "i"}}]},
        lambda row: row.get("is_active", True) and any(query.lower() in str(row.get(field) or "").lower() for field in ("username", "full_name", "headline")),
        sort_key="username", limit=20,
    )
    return [await _profile(user, current_user["id"]) for user in rows if user["id"] != current_user["id"]]


@router.get("/users/{user_id}", response_model=PublicProfile)
async def get_public_profile(user_id: str, current_user: dict | None = Depends(get_optional_current_user)):
    user = await _get_user(user_id)
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=404, detail="Profile not found.")
    return await _profile(user, current_user.get("id") if current_user else None)


@router.get("/users/{user_id}/posts", response_model=list[PostResponse])
async def get_public_user_posts(user_id: str, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=60, window_seconds=60)
    user = await _get_user(user_id)
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=404, detail="Profile not found.")
    rows = await _find_many(
        "posts", {"author_id": user_id, "moderation_status": "APPROVED"},
        lambda row: row.get("author_id") == user_id and row.get("moderation_status") == "APPROVED",
        sort_key="created_at", reverse=True, limit=100,
    )
    return [PostResponse(**row) for row in rows]


@router.get("/connections/suggestions", response_model=list[PublicProfile])
async def connection_suggestions(request: Request, current_user: dict = Depends(get_current_user)):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=30, window_seconds=60)
    me = current_user["id"]
    all_users = await _find_many("users", {"id": {"$ne": me}, "is_active": {"$ne": False}}, lambda row: row.get("id") != me and row.get("is_active", True), sort_key="created_at", reverse=True, limit=50)
    results = []
    for user in all_users:
        state = await _relationship_summary(me, user["id"])
        if state == "NONE":
            results.append(await _profile(user, me))
        if len(results) >= 20:
            break
    return results


@router.post("/connections/requests", response_model=ConnectionSummary, status_code=status.HTTP_201_CREATED)
async def request_connection(req: ConnectionRequestCreate, request: Request, current_user: dict = Depends(get_current_user)):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=20, window_seconds=60)
    me = current_user["id"]
    target = await _get_user(req.target_user_id)
    if not target or not target.get("is_active", True):
        raise HTTPException(status_code=404, detail="Member not found.")
    if target["id"] == me:
        raise HTTPException(status_code=400, detail="You cannot connect with your own account.")
    pair_key = ":".join(sorted((me, target["id"])))
    existing = await _find_one("connections", {"pair_key": pair_key}, lambda row: row.get("pair_key") == pair_key)
    if existing and existing.get("status") in {"PENDING", "ACCEPTED"}:
        raise HTTPException(status_code=409, detail="A connection request already exists for this member.")
    now = _now()
    if existing:
        existing.update({"requester_id": me, "recipient_id": target["id"], "status": "PENDING", "created_at": now, "updated_at": now})
        if db_manager.use_mongo and db_manager.db is not None:
            await db_manager.db["connections"].update_one({"id": existing["id"]}, {"$set": {key: existing[key] for key in ("requester_id", "recipient_id", "status", "created_at", "updated_at")}})
        row = existing
    else:
        row = {"id": str(uuid.uuid4()), "pair_key": pair_key, "requester_id": me, "recipient_id": target["id"], "status": "PENDING", "created_at": now, "updated_at": now}
        if db_manager.use_mongo and db_manager.db is not None:
            await db_manager.db["connections"].insert_one(row)
        else:
            db_manager._collections["connections"].append(row)
    await create_notification(target["id"], "CONNECTION_REQUEST", me, current_user["username"], "connection", row["id"])
    await audit_logger.log_event(me, current_user["role"], "CONNECTION_REQUESTED", "A connection request was sent.", row["id"])
    return ConnectionSummary(**{**row, "other_user": await _profile(target, me)})


@router.get("/connections/requests")
async def list_connection_requests(current_user: dict = Depends(get_current_user)):
    me = current_user["id"]
    rows = await _find_many("connections", {"$or": [{"requester_id": me}, {"recipient_id": me}], "status": "PENDING"}, lambda row: row.get("status") == "PENDING" and me in {row.get("requester_id"), row.get("recipient_id")}, sort_key="created_at", reverse=True, limit=100)
    incoming, outgoing = [], []
    for row in rows:
        other_id = row["requester_id"] if row["recipient_id"] == me else row["recipient_id"]
        other = await _get_user(other_id)
        if not other:
            continue
        item = ConnectionSummary(**{**row, "other_user": await _profile(other, me)})
        (incoming if row["recipient_id"] == me else outgoing).append(item)
    return {"incoming": incoming, "outgoing": outgoing}


@router.get("/connections", response_model=list[PublicProfile])
async def list_connections(current_user: dict = Depends(get_current_user)):
    me = current_user["id"]
    rows = await _find_many("connections", {"$or": [{"requester_id": me}, {"recipient_id": me}], "status": "ACCEPTED"}, lambda row: row.get("status") == "ACCEPTED" and me in {row.get("requester_id"), row.get("recipient_id")}, sort_key="updated_at", reverse=True, limit=200)
    profiles = []
    for row in rows:
        other_id = row["requester_id"] if row["recipient_id"] == me else row["recipient_id"]
        other = await _get_user(other_id)
        if other and other.get("is_active", True):
            profiles.append(await _profile(other, me))
    return profiles


@router.post("/connections/{connection_id}/accept")
async def accept_connection(connection_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=30, window_seconds=60)
    row = await _find_one("connections", {"id": connection_id}, lambda item: item.get("id") == connection_id)
    if not row or row.get("recipient_id") != current_user["id"] or row.get("status") != "PENDING":
        raise HTTPException(status_code=404, detail="Pending invitation not found.")
    row.update({"status": "ACCEPTED", "updated_at": _now()})
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["connections"].update_one({"id": connection_id, "recipient_id": current_user["id"], "status": "PENDING"}, {"$set": {"status": "ACCEPTED", "updated_at": row["updated_at"]}})
    requester = await _get_user(row["requester_id"])
    await create_notification(row["requester_id"], "CONNECTION_ACCEPTED", current_user["id"], current_user["username"], "connection", connection_id)
    await audit_logger.log_event(current_user["id"], current_user["role"], "CONNECTION_ACCEPTED", "A connection request was accepted.", connection_id)
    return {"status": "ACCEPTED", "other_user": await _profile(requester, current_user["id"]) if requester else None}


@router.post("/connections/{connection_id}/reject")
async def reject_connection(connection_id: str, current_user: dict = Depends(get_current_user)):
    row = await _find_one("connections", {"id": connection_id}, lambda item: item.get("id") == connection_id)
    if not row or row.get("recipient_id") != current_user["id"] or row.get("status") != "PENDING":
        raise HTTPException(status_code=404, detail="Pending invitation not found.")
    row.update({"status": "REJECTED", "updated_at": _now()})
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["connections"].update_one({"id": connection_id, "recipient_id": current_user["id"], "status": "PENDING"}, {"$set": {"status": "REJECTED", "updated_at": row["updated_at"]}})
    await audit_logger.log_event(current_user["id"], current_user["role"], "CONNECTION_REJECTED", "A connection request was declined.", connection_id)
    return {"status": "REJECTED"}


@router.delete("/connections/{connection_id}")
async def remove_connection(connection_id: str, current_user: dict = Depends(get_current_user)):
    row = await _find_one("connections", {"id": connection_id}, lambda item: item.get("id") == connection_id)
    if not row or current_user["id"] not in {row.get("requester_id"), row.get("recipient_id")}:
        raise HTTPException(status_code=404, detail="Connection not found.")
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["connections"].delete_one({"id": connection_id})
    else:
        db_manager._collections["connections"] = [item for item in db_manager._collections["connections"] if item.get("id") != connection_id]
    await audit_logger.log_event(current_user["id"], current_user["role"], "CONNECTION_REMOVED", "A connection was removed.", connection_id)
    return {"status": "REMOVED"}


@router.delete("/connections/member/{target_user_id}")
async def remove_connection_with_member(target_user_id: str, current_user: dict = Depends(get_current_user)):
    if target_user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="You cannot remove yourself from your network.")
    pair_key = ":".join(sorted((current_user["id"], target_user_id)))
    row = await _find_one("connections", {"pair_key": pair_key, "status": "ACCEPTED"}, lambda item: item.get("pair_key") == pair_key and item.get("status") == "ACCEPTED")
    if not row:
        raise HTTPException(status_code=404, detail="Connection not found.")
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["connections"].delete_one({"id": row["id"]})
    else:
        db_manager._collections["connections"] = [item for item in db_manager._collections["connections"] if item.get("id") != row["id"]]
    await audit_logger.log_event(current_user["id"], current_user["role"], "CONNECTION_REMOVED", "A connection was removed.", row["id"])
    return {"status": "REMOVED"}


@router.put("/follows/{target_user_id}")
async def follow_user(target_user_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=60, window_seconds=60)
    me = current_user["id"]
    target = await _get_user(target_user_id)
    if not target or not target.get("is_active", True):
        raise HTTPException(status_code=404, detail="Member not found.")
    if me == target_user_id:
        raise HTTPException(status_code=400, detail="You cannot follow your own account.")
    now = _now()
    row = {"id": str(uuid.uuid4()), "follower_id": me, "following_id": target_user_id, "created_at": now}
    created = False
    if db_manager.use_mongo and db_manager.db is not None:
        result = await db_manager.db["follows"].update_one({"follower_id": me, "following_id": target_user_id}, {"$setOnInsert": row}, upsert=True)
        created = result.upserted_id is not None
    else:
        created = not any(item.get("follower_id") == me and item.get("following_id") == target_user_id for item in db_manager._collections["follows"])
        if created:
            db_manager._collections["follows"].append(row)
    if created:
        await create_notification(target_user_id, "FOLLOW", me, current_user["username"], "user", me)
        await audit_logger.log_event(me, current_user["role"], "USER_FOLLOWED", "A member followed another account.", target_user_id)
    count = await _count("follows", {"following_id": target_user_id}, lambda item: item.get("following_id") == target_user_id)
    return {"following": True, "follower_count": count}


@router.delete("/follows/{target_user_id}")
async def unfollow_user(target_user_id: str, current_user: dict = Depends(get_current_user)):
    me = current_user["id"]
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["follows"].delete_one({"follower_id": me, "following_id": target_user_id})
    else:
        db_manager._collections["follows"] = [
            item for item in db_manager._collections["follows"]
            if not (item.get("follower_id") == me and item.get("following_id") == target_user_id)
        ]
    count = await _count("follows", {"following_id": target_user_id}, lambda item: item.get("following_id") == target_user_id)
    return {"following": False, "follower_count": count}


@router.get("/follows/me")
async def get_my_follows(current_user: dict = Depends(get_current_user)):
    me = current_user["id"]
    following_rows = await _find_many("follows", {"follower_id": me}, lambda row: row.get("follower_id") == me, sort_key="created_at", reverse=True, limit=200)
    follower_rows = await _find_many("follows", {"following_id": me}, lambda row: row.get("following_id") == me, sort_key="created_at", reverse=True, limit=200)
    following, followers = [], []
    for row in following_rows:
        user = await _get_user(row["following_id"])
        if user and user.get("is_active", True):
            following.append(await _profile(user, me))
    for row in follower_rows:
        user = await _get_user(row["follower_id"])
        if user and user.get("is_active", True):
            followers.append(await _profile(user, me))
    return {"following": following, "followers": followers}


@router.get("/notifications")
async def list_notifications(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=60, window_seconds=60)
    user_id = current_user["id"]
    rows = await _find_many("notifications", {"recipient_id": user_id}, lambda row: row.get("recipient_id") == user_id, sort_key="created_at", reverse=True, limit=limit)
    unread = await _count("notifications", {"recipient_id": user_id, "is_read": False}, lambda row: row.get("recipient_id") == user_id and not row.get("is_read", False))
    return {"notifications": [NotificationResponse(**row) for row in rows], "unread_count": unread}


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    now = _now()
    row = await _find_one("notifications", {"id": notification_id, "recipient_id": user_id}, lambda item: item.get("id") == notification_id and item.get("recipient_id") == user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found.")
    row.update({"is_read": True, "read_at": now})
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["notifications"].update_one({"id": notification_id, "recipient_id": user_id}, {"$set": {"is_read": True, "read_at": now}})
    return {"status": "READ"}


@router.post("/notifications/read-all")
async def mark_all_notifications_read(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    now = _now()
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["notifications"].update_many({"recipient_id": user_id, "is_read": False}, {"$set": {"is_read": True, "read_at": now}})
    else:
        for row in db_manager._collections["notifications"]:
            if row.get("recipient_id") == user_id:
                row.update({"is_read": True, "read_at": now})
    return {"status": "READ"}


async def _conversation_for_members(member_ids: list[str]):
    pair_key = ":".join(sorted(member_ids))
    return await _find_one("conversations", {"pair_key": pair_key}, lambda row: row.get("pair_key") == pair_key)


@router.get("/messages/conversations")
async def list_conversations(current_user: dict = Depends(get_current_user)):
    me = current_user["id"]
    rows = await _find_many("conversations", {"member_ids": me}, lambda row: me in row.get("member_ids", []), sort_key="last_message_at", reverse=True, limit=100)
    result = []
    for row in rows:
        other_id = next((member_id for member_id in row.get("member_ids", []) if member_id != me), None)
        other = await _get_user(other_id) if other_id else None
        if not other or not other.get("is_active", True):
            continue
        unread = await _count("messages", {"conversation_id": row["id"], "recipient_id": me, "is_read": False}, lambda message: message.get("conversation_id") == row["id"] and message.get("recipient_id") == me and not message.get("is_read", False))
        result.append({
            "id": row["id"],
            "other_user": _public_user(other),
            "last_message": row.get("last_message"),
            "last_message_at": row.get("last_message_at"),
            "unread_count": unread,
        })
    return result


@router.post("/messages/conversations", status_code=status.HTTP_200_OK)
async def start_conversation(req: ConversationCreate, request: Request, current_user: dict = Depends(get_current_user)):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=20, window_seconds=60)
    me, other_id = current_user["id"], req.participant_id
    if me == other_id:
        raise HTTPException(status_code=400, detail="You cannot start a conversation with yourself.")
    other = await _get_user(other_id)
    if not other or not other.get("is_active", True):
        raise HTTPException(status_code=404, detail="Member not found.")
    if await _relationship_summary(me, other_id) != "CONNECTED":
        raise HTTPException(status_code=403, detail="You can message members after they accept your connection request.")
    row = await _conversation_for_members([me, other_id])
    if not row:
        now = _now()
        row = {"id": str(uuid.uuid4()), "pair_key": ":".join(sorted((me, other_id))), "member_ids": sorted((me, other_id)), "created_at": now, "last_message_at": None, "last_message": None}
        if db_manager.use_mongo and db_manager.db is not None:
            try:
                await db_manager.db["conversations"].insert_one(row)
            except Exception:
                row = await _conversation_for_members([me, other_id])
                if not row:
                    raise HTTPException(status_code=409, detail="Conversation could not be created. Please retry.") from None
        else:
            db_manager._collections["conversations"].append(row)
    return {
        "id": row["id"],
        "other_user": await _profile(other, me),
        "last_message": row.get("last_message"),
        "last_message_at": row.get("last_message_at"),
        "unread_count": 0,
    }


@router.get("/messages/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, current_user: dict = Depends(get_current_user)):
    me = current_user["id"]
    conversation = await _find_one("conversations", {"id": conversation_id, "member_ids": me}, lambda row: row.get("id") == conversation_id and me in row.get("member_ids", []))
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    rows = await _find_many("messages", {"conversation_id": conversation_id}, lambda row: row.get("conversation_id") == conversation_id, sort_key="created_at", limit=200)
    other_id = next(member_id for member_id in conversation["member_ids"] if member_id != me)
    other = await _get_user(other_id)
    return {
        "id": conversation_id,
        "other_user": _public_user(other) if other else None,
        "messages": [MessageResponse(**row) for row in rows],
    }


@router.post("/messages/conversations/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(conversation_id: str, message_in: MessageCreate, request: Request, current_user: dict = Depends(get_current_user)):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=30, window_seconds=60)
    me = current_user["id"]
    conversation = await _find_one("conversations", {"id": conversation_id, "member_ids": me}, lambda row: row.get("id") == conversation_id and me in row.get("member_ids", []))
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    other_id = next(member_id for member_id in conversation["member_ids"] if member_id != me)
    if await _relationship_summary(me, other_id) != "CONNECTED":
        raise HTTPException(status_code=403, detail="Messaging is available while you are connected.")
    content = InputSanitizer.sanitize_text(message_in.content).strip()
    if not content:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    now = _now()
    row = {"id": str(uuid.uuid4()), "conversation_id": conversation_id, "sender_id": me, "recipient_id": other_id, "content": content, "created_at": now, "is_read": False}
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["messages"].insert_one(row)
        await db_manager.db["conversations"].update_one({"id": conversation_id}, {"$set": {"last_message": content[:160], "last_message_at": now}})
    else:
        db_manager._collections["messages"].append(row)
        conversation.update({"last_message": content[:160], "last_message_at": now})
    sender = current_user.get("username")
    await create_notification(other_id, "MESSAGE", me, sender, "conversation", conversation_id)
    return MessageResponse(**row)


@router.patch("/messages/conversations/{conversation_id}/read")
async def mark_conversation_read(conversation_id: str, current_user: dict = Depends(get_current_user)):
    me = current_user["id"]
    conversation = await _find_one("conversations", {"id": conversation_id, "member_ids": me}, lambda row: row.get("id") == conversation_id and me in row.get("member_ids", []))
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    now = _now()
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["messages"].update_many({"conversation_id": conversation_id, "recipient_id": me, "is_read": False}, {"$set": {"is_read": True, "read_at": now}})
    else:
        for row in db_manager._collections["messages"]:
            if row.get("conversation_id") == conversation_id and row.get("recipient_id") == me:
                row.update({"is_read": True, "read_at": now})
    return {"status": "READ"}


@router.get("/search")
async def global_search(request: Request, q: str = Query(..., min_length=2, max_length=80), current_user: dict = Depends(get_current_user)):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=30, window_seconds=60)
    query = q.strip()
    if len(query) < 2:
        return {"users": [], "posts": []}
    escaped = re.escape(query)
    users = await _find_many(
        "users",
        {"is_active": {"$ne": False}, "$or": [{"username": {"$regex": escaped, "$options": "i"}}, {"full_name": {"$regex": escaped, "$options": "i"}}, {"headline": {"$regex": escaped, "$options": "i"}}]},
        lambda row: row.get("is_active", True) and any(query.lower() in str(row.get(field) or "").lower() for field in ("username", "full_name", "headline")),
        sort_key="username", limit=10,
    )
    if db_manager.use_mongo and db_manager.db is not None:
        posts = await db_manager.db["posts"].find({"moderation_status": "APPROVED", "content": {"$regex": escaped, "$options": "i"}}).sort("created_at", -1).limit(10).to_list(length=10)
    else:
        posts = [row for row in db_manager._collections["posts"] if row.get("moderation_status") == "APPROVED" and query.lower() in row.get("content", "").lower()]
        posts.sort(key=lambda row: row.get("created_at", ""), reverse=True)
        posts = posts[:10]
    post_ids = [post.get("id") for post in posts]
    if db_manager.use_mongo and db_manager.db is not None:
        like_rows = await db_manager.db["post_likes"].find({"post_id": {"$in": post_ids}}).to_list(length=None) if post_ids else []
        saved_rows = await db_manager.db["saved_posts"].find({"user_id": current_user["id"], "post_id": {"$in": post_ids}}).to_list(length=None) if post_ids else []
    else:
        like_rows = [row for row in db_manager._collections["post_likes"] if row.get("post_id") in post_ids]
        saved_rows = [row for row in db_manager._collections["saved_posts"] if row.get("user_id") == current_user["id"] and row.get("post_id") in post_ids]
    like_counts: dict[str, int] = {}
    liked_ids, saved_ids = set(), {row.get("post_id") for row in saved_rows}
    for row in like_rows:
        like_counts[row["post_id"]] = like_counts.get(row["post_id"], 0) + 1
        if row.get("user_id") == current_user["id"]:
            liked_ids.add(row["post_id"])
    return {
        "users": [await _profile(user, current_user["id"]) for user in users if user["id"] != current_user["id"]],
        "posts": [PostResponse(**{
            **post,
            "like_count": like_counts.get(post["id"], 0),
            "liked_by_me": post["id"] in liked_ids,
            "saved_by_me": post["id"] in saved_ids,
        }) for post in posts],
    }
