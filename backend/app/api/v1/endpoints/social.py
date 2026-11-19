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
    FollowRequestSummary,
    MessageCreate,
    MessageResponse,
    NotificationResponse,
    PublicProfile,
)
from app.schemas.post import PostResponse
from app.services.audit_logger import audit_logger
from app.services.notifications import (
    create_notification,
    notification_kinds_for_section,
    notification_section,
)
from app.services.sanitizer import InputSanitizer
from app.services.social_access import can_view_profile_content, visible_author_ids

router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _find_one(collection: str, mongo_query: dict, memory_predicate):
    if db_manager.use_mongo and db_manager.db is not None:
        return await db_manager.db[collection].find_one(mongo_query)
    return next((row for row in db_manager._collections.get(collection, []) if memory_predicate(row)), None)


async def _find_many(collection: str, mongo_query: dict, memory_predicate, *, sort_key: str | None = None, reverse: bool = False, limit: int = 100, offset: int = 0):
    if db_manager.use_mongo and db_manager.db is not None:
        cursor = db_manager.db[collection].find(mongo_query)
        if sort_key:
            cursor = cursor.sort(sort_key, -1 if reverse else 1)
        return await cursor.skip(offset).limit(limit).to_list(length=limit)
    rows = [row for row in db_manager._collections.get(collection, []) if memory_predicate(row)]
    if sort_key:
        rows.sort(key=lambda row: str(row.get(sort_key) or ""), reverse=reverse)
    return rows[offset:offset + limit]


async def _count(collection: str, mongo_query: dict, memory_predicate) -> int:
    if db_manager.use_mongo and db_manager.db is not None:
        return await db_manager.db[collection].count_documents(mongo_query)
    return sum(1 for row in db_manager._collections.get(collection, []) if memory_predicate(row))


async def _unread_notification_counts(user_id: str) -> dict[str, int]:
    counts = {
        "home": 0,
        "explore": 0,
        "network": 0,
        "messages": 0,
        "events": 0,
        "articles": 0,
        "notifications": 0,
    }
    if db_manager.use_mongo and db_manager.db is not None:
        rows = await db_manager.db["notifications"].aggregate([
            {"$match": {"recipient_id": user_id, "is_read": False}},
            {"$group": {
                "_id": {"section": "$section", "kind": "$kind"},
                "count": {"$sum": 1},
            }},
        ]).to_list(length=None)
        for row in rows:
            identity = row.get("_id") or {}
            section = identity.get("section") or notification_section(identity.get("kind") or "")
            counts[section] = counts.get(section, 0) + row.get("count", 0)
        return counts

    for row in db_manager._collections.get("notifications", []):
        if row.get("recipient_id") == user_id and not row.get("is_read", False):
            section = row.get("section") or notification_section(row.get("kind") or "")
            counts[section] = counts.get(section, 0) + 1
    return counts


async def _get_user(user_id: str):
    return await _find_one("users", {"id": user_id}, lambda row: row.get("id") == user_id)


async def _mark_request_notifications_read(recipient_id: str, resource_id: str, kind: str) -> None:
    now = _now()
    query = {"recipient_id": recipient_id, "resource_id": resource_id, "kind": kind, "is_read": False}
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["notifications"].update_many(query, {"$set": {"is_read": True, "read_at": now}})
        return
    for row in db_manager._collections["notifications"]:
        if (
            row.get("recipient_id") == recipient_id
            and row.get("resource_id") == resource_id
            and row.get("kind") == kind
            and not row.get("is_read", False)
        ):
            row.update({"is_read": True, "read_at": now})


def _public_user(user: dict, *, include_profile_content: bool = True) -> dict[str, Any]:
    return {
        "id": user["id"],
        "username": user["username"],
        "full_name": user.get("full_name"),
        "headline": user.get("headline") if include_profile_content else None,
        "location": user.get("location") if include_profile_content else None,
        "about": user.get("about") if include_profile_content else None,
        "skills": user.get("skills", []) if include_profile_content else [],
        "created_at": user["created_at"],
        "is_private": user.get("is_private", False),
        "profile_restricted": bool(user.get("is_private", False) and not include_profile_content),
        "avatar_url": user.get("avatar_url") if include_profile_content else None,
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
    if follows and follows.get("status", "ACCEPTED") == "ACCEPTED":
        return "FOLLOWING"
    if follows and follows.get("status") == "PENDING":
        return "REQUEST_SENT"
    incoming = await _find_one("follows", {"follower_id": other_id, "following_id": viewer_id, "status": "PENDING"}, lambda row: row.get("follower_id") == other_id and row.get("following_id") == viewer_id and row.get("status") == "PENDING")
    return "REQUEST_RECEIVED" if incoming else "NONE"


async def _profile(user: dict, viewer_id: str | None = None) -> PublicProfile:
    user_id = user["id"]
    can_view_content = await can_view_profile_content(user, viewer_id)
    if db_manager.use_mongo and db_manager.db is not None:
        connections = await db_manager.db["connections"].count_documents({"$or": [{"requester_id": user_id}, {"recipient_id": user_id}], "status": "ACCEPTED"})
    else:
        connections = sum(1 for row in db_manager._collections["connections"] if user_id in {row.get("requester_id"), row.get("recipient_id")} and row.get("status") == "ACCEPTED")
    accepted_status = {"$or": [{"status": "ACCEPTED"}, {"status": {"$exists": False}}]}
    followers = await _count("follows", {"following_id": user_id, **accepted_status}, lambda row: row.get("following_id") == user_id and row.get("status", "ACCEPTED") == "ACCEPTED")
    following = await _count("follows", {"follower_id": user_id, **accepted_status}, lambda row: row.get("follower_id") == user_id and row.get("status", "ACCEPTED") == "ACCEPTED")
    relationship = await _relationship_summary(viewer_id, user_id) if viewer_id and viewer_id != user_id else "SELF" if viewer_id == user_id else "NONE"
    follow_status = "NONE"
    if viewer_id == user_id:
        follow_status = "SELF"
    elif viewer_id:
        outgoing = await _find_one("follows", {"follower_id": viewer_id, "following_id": user_id}, lambda row: row.get("follower_id") == viewer_id and row.get("following_id") == user_id)
        incoming = await _find_one("follows", {"follower_id": user_id, "following_id": viewer_id}, lambda row: row.get("follower_id") == user_id and row.get("following_id") == viewer_id)
        if outgoing and outgoing.get("status", "ACCEPTED") == "ACCEPTED":
            follow_status = "FOLLOWING"
        elif outgoing and outgoing.get("status") == "PENDING":
            follow_status = "REQUEST_SENT"
        elif incoming and incoming.get("status") == "PENDING":
            follow_status = "REQUEST_RECEIVED"
    profile_data = _public_user(user, include_profile_content=can_view_content)
    return PublicProfile(**{
        **profile_data,
        "connection_count": connections if can_view_content else 0,
        "follower_count": followers if can_view_content else 0,
        "following_count": following if can_view_content else 0,
        "relationship": relationship,
        "follow_status": follow_status,
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
    visible_profiles = await visible_author_ids(current_user["id"])
    searchable_fields = [
        {"username": {"$regex": escaped, "$options": "i"}},
        {"full_name": {"$regex": escaped, "$options": "i"}},
        {"$and": [{"is_private": {"$ne": True}}, {"headline": {"$regex": escaped, "$options": "i"}}]},
        {"$and": [{"is_private": True}, {"id": {"$in": list(visible_profiles)}}, {"headline": {"$regex": escaped, "$options": "i"}}]},
    ]
    rows = await _find_many(
        "users",
        {"is_active": {"$ne": False}, "$or": searchable_fields},
        lambda row: row.get("is_active", True) and (
            query.lower() in str(row.get("username") or "").lower()
            or query.lower() in str(row.get("full_name") or "").lower()
            or (
                row.get("id") in visible_profiles
                and query.lower() in str(row.get("headline") or "").lower()
            )
        ),
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
async def get_public_user_posts(
    user_id: str,
    request: Request,
    current_user: dict | None = Depends(get_optional_current_user),
):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=60, window_seconds=60)
    user = await _get_user(user_id)
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=404, detail="Profile not found.")
    if not await can_view_profile_content(user, current_user.get("id") if current_user else None):
        raise HTTPException(status_code=403, detail="Follow this private account and wait for approval to view its posts.")
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
    await _mark_request_notifications_read(current_user["id"], connection_id, "CONNECTION_REQUEST")
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
    await create_notification(row["requester_id"], "CONNECTION_REJECTED", current_user["id"], current_user["username"], "connection", connection_id)
    await _mark_request_notifications_read(current_user["id"], connection_id, "CONNECTION_REQUEST")
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
    existing = await _find_one(
        "follows",
        {"follower_id": me, "following_id": target_user_id},
        lambda item: item.get("follower_id") == me and item.get("following_id") == target_user_id,
    )
    requested_status = "PENDING" if target.get("is_private", False) else "ACCEPTED"
    if existing and existing.get("status", "ACCEPTED") in {"ACCEPTED", "PENDING"}:
        final_status = existing.get("status", "ACCEPTED")
        count = await _count("follows", {"following_id": target_user_id, "$or": [{"status": "ACCEPTED"}, {"status": {"$exists": False}}]}, lambda item: item.get("following_id") == target_user_id and item.get("status", "ACCEPTED") == "ACCEPTED")
        return {"following": final_status == "ACCEPTED", "status": final_status, "follower_count": count}

    if existing:
        row = existing
        row.update({"status": requested_status, "updated_at": now})
        if db_manager.use_mongo and db_manager.db is not None:
            await db_manager.db["follows"].update_one(
                {"id": row["id"], "follower_id": me, "following_id": target_user_id},
                {"$set": {"status": requested_status, "updated_at": now}},
            )
    else:
        row = {
            "id": str(uuid.uuid4()),
            "follower_id": me,
            "following_id": target_user_id,
            "status": requested_status,
            "created_at": now,
            "updated_at": now,
        }
        if db_manager.use_mongo and db_manager.db is not None:
            await db_manager.db["follows"].insert_one(row)
        else:
            db_manager._collections["follows"].append(row)
    if requested_status == "PENDING":
        await create_notification(target_user_id, "FOLLOW_REQUEST", me, current_user["username"], "user", me)
    else:
        await create_notification(target_user_id, "FOLLOW", me, current_user["username"], "user", me)
    await audit_logger.log_event(me, current_user["role"], "USER_FOLLOWED" if requested_status == "ACCEPTED" else "FOLLOW_REQUESTED", "A member followed or requested to follow an account.", target_user_id)
    count = await _count("follows", {"following_id": target_user_id, "$or": [{"status": "ACCEPTED"}, {"status": {"$exists": False}}]}, lambda item: item.get("following_id") == target_user_id and item.get("status", "ACCEPTED") == "ACCEPTED")
    return {"following": requested_status == "ACCEPTED", "status": requested_status, "follower_count": count}


@router.get("/follows/requests")
async def list_follow_requests(current_user: dict = Depends(get_current_user)):
    me = current_user["id"]
    rows = await _find_many(
        "follows",
        {"$or": [{"follower_id": me}, {"following_id": me}], "status": "PENDING"},
        lambda row: row.get("status") == "PENDING" and me in {row.get("follower_id"), row.get("following_id")},
        sort_key="created_at",
        reverse=True,
        limit=200,
    )
    incoming, outgoing = [], []
    for row in rows:
        other_id = row["follower_id"] if row["following_id"] == me else row["following_id"]
        other = await _get_user(other_id)
        if not other or not other.get("is_active", True):
            continue
        item = FollowRequestSummary(**{**row, "other_user": await _profile(other, me)})
        (incoming if row["following_id"] == me else outgoing).append(item)
    return {"incoming": incoming, "outgoing": outgoing}


@router.post("/follows/requests/{follower_id}/accept")
async def accept_follow_request(follower_id: str, current_user: dict = Depends(get_current_user)):
    me = current_user["id"]
    row = await _find_one(
        "follows",
        {"follower_id": follower_id, "following_id": me, "status": "PENDING"},
        lambda item: item.get("follower_id") == follower_id and item.get("following_id") == me and item.get("status") == "PENDING",
    )
    if not row:
        raise HTTPException(status_code=404, detail="Pending follow request not found.")
    now = _now()
    row.update({"status": "ACCEPTED", "updated_at": now})
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["follows"].update_one(
            {"id": row["id"], "follower_id": follower_id, "following_id": me, "status": "PENDING"},
            {"$set": {"status": "ACCEPTED", "updated_at": now}},
        )
    await create_notification(follower_id, "FOLLOW_ACCEPTED", me, current_user["username"], "user", me)
    await _mark_request_notifications_read(me, follower_id, "FOLLOW_REQUEST")
    await audit_logger.log_event(me, current_user["role"], "FOLLOW_REQUEST_ACCEPTED", "A follow request was accepted.", row["id"])
    count = await _count("follows", {"following_id": me, "$or": [{"status": "ACCEPTED"}, {"status": {"$exists": False}}]}, lambda item: item.get("following_id") == me and item.get("status", "ACCEPTED") == "ACCEPTED")
    return {"status": "ACCEPTED", "following": True, "follower_count": count}


@router.post("/follows/requests/{follower_id}/reject")
async def reject_follow_request(follower_id: str, current_user: dict = Depends(get_current_user)):
    me = current_user["id"]
    row = await _find_one(
        "follows",
        {"follower_id": follower_id, "following_id": me, "status": "PENDING"},
        lambda item: item.get("follower_id") == follower_id and item.get("following_id") == me and item.get("status") == "PENDING",
    )
    if not row:
        raise HTTPException(status_code=404, detail="Pending follow request not found.")
    now = _now()
    row.update({"status": "REJECTED", "updated_at": now})
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["follows"].update_one(
            {"id": row["id"], "follower_id": follower_id, "following_id": me, "status": "PENDING"},
            {"$set": {"status": "REJECTED", "updated_at": now}},
        )
    await create_notification(follower_id, "FOLLOW_REJECTED", me, current_user["username"], "user", me)
    await _mark_request_notifications_read(me, follower_id, "FOLLOW_REQUEST")
    await audit_logger.log_event(me, current_user["role"], "FOLLOW_REQUEST_REJECTED", "A follow request was rejected.", row["id"])
    return {"status": "REJECTED"}


@router.delete("/follows/{target_user_id}")
async def unfollow_user(target_user_id: str, current_user: dict = Depends(get_current_user)):
    me = current_user["id"]
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["follows"].delete_one({"follower_id": me, "following_id": target_user_id, "$or": [{"status": "ACCEPTED"}, {"status": {"$exists": False}}]})
    else:
        db_manager._collections["follows"] = [
            item for item in db_manager._collections["follows"]
            if not (item.get("follower_id") == me and item.get("following_id") == target_user_id and item.get("status", "ACCEPTED") == "ACCEPTED")
        ]
    count = await _count("follows", {"following_id": target_user_id, "$or": [{"status": "ACCEPTED"}, {"status": {"$exists": False}}]}, lambda item: item.get("following_id") == target_user_id and item.get("status", "ACCEPTED") == "ACCEPTED")
    return {"following": False, "follower_count": count}


@router.get("/follows/me")
async def get_my_follows(current_user: dict = Depends(get_current_user)):
    me = current_user["id"]
    accepted_status = {"$or": [{"status": "ACCEPTED"}, {"status": {"$exists": False}}]}
    following_rows = await _find_many("follows", {"follower_id": me, **accepted_status}, lambda row: row.get("follower_id") == me and row.get("status", "ACCEPTED") == "ACCEPTED", sort_key="created_at", reverse=True, limit=200)
    follower_rows = await _find_many("follows", {"following_id": me, **accepted_status}, lambda row: row.get("following_id") == me and row.get("status", "ACCEPTED") == "ACCEPTED", sort_key="created_at", reverse=True, limit=200)
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
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    section: str | None = Query(None, pattern="^(home|explore|network|messages|events|articles|notifications)$"),
    current_user: dict = Depends(get_current_user),
):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=60, window_seconds=60)
    user_id = current_user["id"]
    query = {"recipient_id": user_id}
    predicate = lambda row: row.get("recipient_id") == user_id
    if section:
        kinds = notification_kinds_for_section(section)
        query = {
            "recipient_id": user_id,
            "$or": [
                {"section": section},
                {"section": {"$exists": False}, "kind": {"$in": list(kinds)}},
            ],
        }
        predicate = lambda row: (
            row.get("recipient_id") == user_id
            and (
                row.get("section") == section
                or (not row.get("section") and notification_section(row.get("kind") or "") in {section})
            )
        )
    rows = await _find_many(
        "notifications",
        query,
        predicate,
        sort_key="created_at",
        reverse=True,
        limit=limit + 1,
        offset=offset,
    )
    has_more = len(rows) > limit
    page_rows = rows[:limit]
    actor_ids = {row.get("actor_id") for row in page_rows if row.get("actor_id")}
    post_ids = {
        row.get("resource_id")
        for row in page_rows
        if row.get("kind") in {"NETWORK_POST", "NETWORK_ARTICLE", "NETWORK_EVENT"} and row.get("resource_id")
    }
    connection_ids = {
        row.get("resource_id")
        for row in page_rows
        if row.get("resource_type") == "connection" and row.get("resource_id")
    }
    follow_pairs = set()
    for row in page_rows:
        if row.get("resource_type") != "user" or not row.get("actor_id"):
            continue
        if row.get("kind") in {"FOLLOW_ACCEPTED", "FOLLOW_REJECTED"}:
            follow_pairs.add((user_id, row["actor_id"]))
        else:
            follow_pairs.add((row["actor_id"], user_id))

    post_rows = await _find_many(
        "posts",
        {"id": {"$in": list(post_ids)}},
        lambda item: item.get("id") in post_ids,
        limit=max(1, len(post_ids)),
    ) if post_ids else []
    related_user_ids = actor_ids | {row.get("author_id") for row in post_rows if row.get("author_id")}
    users = await _find_many(
        "users",
        {"id": {"$in": list(related_user_ids)}},
        lambda item: item.get("id") in related_user_ids,
        limit=max(1, len(related_user_ids)),
    ) if related_user_ids else []
    users_by_id = {row["id"]: row for row in users if row.get("id")}
    private_user_ids = {
        user_row["id"] for user_row in users
        if user_row.get("id") and user_row.get("is_private", False)
    }
    follow_pairs.update((user_id, private_id) for private_id in private_user_ids)
    if follow_pairs:
        follow_query = {
            "$or": [{"follower_id": follower, "following_id": following} for follower, following in follow_pairs]
        }
        follow_rows = await _find_many(
            "follows",
            follow_query,
            lambda item: (item.get("follower_id"), item.get("following_id")) in follow_pairs,
            limit=max(1, len(follow_pairs)),
        )
    else:
        follow_rows = []
    follows_by_pair = {
        (row.get("follower_id"), row.get("following_id")): row
        for row in follow_rows
        if row.get("follower_id") and row.get("following_id")
    }
    connections = await _find_many(
        "connections",
        {"id": {"$in": list(connection_ids)}},
        lambda item: item.get("id") in connection_ids,
        limit=max(1, len(connection_ids)),
    ) if connection_ids else []
    connections_by_id = {row["id"]: row for row in connections if row.get("id")}

    def profile_visible(profile: dict | None) -> bool:
        if not profile or not profile.get("is_active", True):
            return False
        if not profile.get("is_private", False) or profile.get("id") == user_id:
            return True
        follow = follows_by_pair.get((user_id, profile["id"]))
        return bool(follow and follow.get("status", "ACCEPTED") == "ACCEPTED")

    notifications = []
    for row in page_rows:
        notification = dict(row)
        actor = users_by_id.get(notification.get("actor_id"))
        if actor:
            notification["actor_username"] = actor.get("username") or notification.get("actor_username")
            notification["actor_full_name"] = actor.get("full_name")
            if profile_visible(actor):
                notification["actor_avatar_url"] = actor.get("avatar_url")

        if notification.get("kind") in {"NETWORK_POST", "NETWORK_ARTICLE", "NETWORK_EVENT"}:
            post = next((item for item in post_rows if item.get("id") == notification.get("resource_id")), None)
            post_author = users_by_id.get(post.get("author_id")) if post else None
            if (
                not post
                or post.get("moderation_status") != "APPROVED"
                or not profile_visible(post_author)
            ):
                continue
            preview = (
                (post.get("article") or {}).get("title")
                if notification.get("kind") == "NETWORK_ARTICLE"
                else (post.get("event") or {}).get("title")
                if notification.get("kind") == "NETWORK_EVENT"
                else post.get("content")
            ) or post.get("content") or ""
            notification["post_preview"] = preview[:180]

        if notification.get("resource_type") == "connection":
            connection = connections_by_id.get(notification.get("resource_id"))
            if connection:
                notification["resource_status"] = connection.get("status")
        elif notification.get("resource_type") == "user":
            if notification.get("kind") in {"FOLLOW_ACCEPTED", "FOLLOW_REJECTED"}:
                pair = (user_id, notification.get("actor_id"))
            else:
                pair = (notification.get("actor_id"), user_id)
            follow = follows_by_pair.get(pair)
            if follow:
                notification["resource_status"] = follow.get("status", "ACCEPTED")

        notification["section"] = notification.get("section") or notification_section(notification.get("kind") or "")
        notifications.append(NotificationResponse(**notification))

    unread_by_section = await _unread_notification_counts(user_id)
    unread = sum(unread_by_section.values())
    return {
        "notifications": notifications,
        "unread_count": unread,
        "unread_by_section": unread_by_section,
        "section_unread_count": unread_by_section.get(section, 0) if section else None,
        "has_more": has_more,
        "next_offset": offset + len(page_rows),
    }


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    now = _now()
    row = await _find_one("notifications", {"id": notification_id, "recipient_id": user_id}, lambda item: item.get("id") == notification_id and item.get("recipient_id") == user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found.")
    if row.get("kind") == "MESSAGE" and row.get("resource_type") == "conversation" and row.get("resource_id"):
        conversation_id = row["resource_id"]
        if db_manager.use_mongo and db_manager.db is not None:
            await db_manager.db["messages"].update_many(
                {"conversation_id": conversation_id, "recipient_id": user_id, "is_read": False},
                {"$set": {"is_read": True, "read_at": now}},
            )
            await db_manager.db["notifications"].update_many(
                {
                    "recipient_id": user_id,
                    "kind": "MESSAGE",
                    "resource_type": "conversation",
                    "resource_id": conversation_id,
                    "is_read": False,
                },
                {"$set": {"is_read": True, "read_at": now}},
            )
        else:
            for message in db_manager._collections["messages"]:
                if message.get("conversation_id") == conversation_id and message.get("recipient_id") == user_id:
                    message.update({"is_read": True, "read_at": now})
            for notification in db_manager._collections["notifications"]:
                if (
                    notification.get("recipient_id") == user_id
                    and notification.get("kind") == "MESSAGE"
                    and notification.get("resource_type") == "conversation"
                    and notification.get("resource_id") == conversation_id
                ):
                    notification.update({"is_read": True, "read_at": now})
    elif db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["notifications"].update_one({"id": notification_id, "recipient_id": user_id}, {"$set": {"is_read": True, "read_at": now}})
    else:
        row.update({"is_read": True, "read_at": now})
    return {"status": "READ"}


@router.post("/notifications/read-all")
async def mark_all_notifications_read(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    now = _now()
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["notifications"].update_many({"recipient_id": user_id, "is_read": False}, {"$set": {"is_read": True, "read_at": now}})
        await db_manager.db["messages"].update_many(
            {"recipient_id": user_id, "is_read": False},
            {"$set": {"is_read": True, "read_at": now}},
        )
    else:
        for row in db_manager._collections["notifications"]:
            if row.get("recipient_id") == user_id and not row.get("is_read", False):
                row.update({"is_read": True, "read_at": now})
        for row in db_manager._collections["messages"]:
            if row.get("recipient_id") == user_id and not row.get("is_read", False):
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
            "other_user": (await _profile(other, me)).model_dump(),
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
        "other_user": (await _profile(other, me)).model_dump() if other else None,
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
        await db_manager.db["notifications"].update_many(
            {
                "recipient_id": me,
                "kind": "MESSAGE",
                "resource_type": "conversation",
                "resource_id": conversation_id,
                "is_read": False,
            },
            {"$set": {"is_read": True, "read_at": now}},
        )
    else:
        for row in db_manager._collections["messages"]:
            if row.get("conversation_id") == conversation_id and row.get("recipient_id") == me and not row.get("is_read", False):
                row.update({"is_read": True, "read_at": now})
        for row in db_manager._collections["notifications"]:
            if (
                row.get("recipient_id") == me
                and row.get("kind") == "MESSAGE"
                and row.get("resource_type") == "conversation"
                and row.get("resource_id") == conversation_id
                and not row.get("is_read", False)
            ):
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
    visible_profiles = await visible_author_ids(current_user["id"])
    users = await _find_many(
        "users",
        {"is_active": {"$ne": False}, "$or": [
            {"username": {"$regex": escaped, "$options": "i"}},
            {"full_name": {"$regex": escaped, "$options": "i"}},
            {"$and": [{"is_private": {"$ne": True}}, {"headline": {"$regex": escaped, "$options": "i"}}]},
            {"$and": [{"is_private": True}, {"id": {"$in": list(visible_profiles)}}, {"headline": {"$regex": escaped, "$options": "i"}}]},
        ]},
        lambda row: row.get("is_active", True) and (
            query.lower() in str(row.get("username") or "").lower()
            or query.lower() in str(row.get("full_name") or "").lower()
            or (
                row.get("id") in visible_profiles
                and query.lower() in str(row.get("headline") or "").lower()
            )
        ),
        sort_key="username", limit=10,
    )
    searchable_author_ids = await visible_author_ids(current_user["id"])
    post_search_query = {
        "author_id": {"$in": list(searchable_author_ids)},
        "moderation_status": "APPROVED",
        "$or": [
            {"content": {"$regex": escaped, "$options": "i"}},
            {"event.title": {"$regex": escaped, "$options": "i"}},
            {"article.title": {"$regex": escaped, "$options": "i"}},
        ],
    }
    if db_manager.use_mongo and db_manager.db is not None:
        posts = await db_manager.db["posts"].find(post_search_query).sort("created_at", -1).limit(10).to_list(length=10) if searchable_author_ids else []
    else:
        posts = [
            row for row in db_manager._collections["posts"]
            if row.get("author_id") in searchable_author_ids
            and row.get("moderation_status") == "APPROVED"
            and (
                query.lower() in str(row.get("content") or "").lower()
                or query.lower() in str((row.get("event") or {}).get("title") or "").lower()
                or query.lower() in str((row.get("article") or {}).get("title") or "").lower()
            )
        ]
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
