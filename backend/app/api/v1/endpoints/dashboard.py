import asyncio
from fastapi import APIRouter, Depends, Request
from typing import List, Dict, Any

from app.api.deps import get_current_user
from app.core.database import db_manager
from app.middleware.rate_limit import rate_limit_check
from app.schemas.post import PostResponse
from app.schemas.comment import CommentResponse
from app.schemas.dashboard import (
    UserDashboardResponse,
    UserDashboardStats,
    ModerationHistoryItem,
)

router = APIRouter()


async def _fetch_user_posts(user_id: str) -> List[dict]:
    if db_manager.use_mongo and db_manager.db is not None:
        cursor = db_manager.db["posts"].find({"author_id": user_id}).sort("created_at", -1)
        return await cursor.to_list(length=None)
    posts = [p for p in db_manager._collections["posts"] if p.get("author_id") == user_id]
    return sorted(posts, key=lambda x: x["created_at"], reverse=True)


async def _fetch_user_comments(user_id: str) -> List[dict]:
    if db_manager.use_mongo and db_manager.db is not None:
        cursor = db_manager.db["comments"].find({"author_id": user_id}).sort("created_at", -1)
        return await cursor.to_list(length=None)
    comments = db_manager._collections.get("comments", [])
    user_comments = [c for c in comments if c.get("author_id") == user_id]
    return sorted(user_comments, key=lambda x: x["created_at"], reverse=True)


async def _fetch_moderation_history_for_content(content_ids: List[str]) -> List[dict]:
    if not content_ids:
        return []
    if db_manager.use_mongo and db_manager.db is not None:
        cursor = db_manager.db["moderation_logs"].find({"$or": [
            {"content_id": {"$in": content_ids}},
            {"post_id": {"$in": content_ids}},
        ]}).sort("timestamp", -1)
        return await cursor.to_list(length=None)
    logs = db_manager._collections.get("moderation_logs", [])
    filtered = [l for l in logs if l.get("content_id", l.get("post_id")) in content_ids]
    return sorted(filtered, key=lambda x: x.get("timestamp", ""), reverse=True)


async def _count_user_items(collection_name: str, user_id: str, status_filter: str | None = None) -> int:
    query = {"author_id": user_id}
    if status_filter:
        query["moderation_status"] = status_filter
    if db_manager.use_mongo and db_manager.db is not None:
        return await db_manager.db[collection_name].count_documents(query)
    return sum(
        1 for item in db_manager._collections.get(collection_name, [])
        if item.get("author_id") == user_id
        and (status_filter is None or item.get("moderation_status") == status_filter)
    )


async def _count_user_pending_reviews(collection_name: str, user_id: str) -> int:
    query = {
        "author_id": user_id,
        "moderation_status": "FLAGGED_FOR_REVIEW",
        "admin_reviewed": {"$ne": True},
    }
    if db_manager.use_mongo and db_manager.db is not None:
        return await db_manager.db[collection_name].count_documents(query)
    return sum(
        1 for item in db_manager._collections.get(collection_name, [])
        if item.get("author_id") == user_id
        and item.get("moderation_status") == "FLAGGED_FOR_REVIEW"
        and not item.get("admin_reviewed", False)
    )


@router.get("/me", response_model=UserDashboardResponse)
async def get_user_dashboard(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Aggregated user dashboard: own posts, comments, moderation history, pending items."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    rate_limit_check(client_ip, max_requests=60, window_seconds=60)

    user_id = current_user["id"]
    posts = await _fetch_user_posts(user_id)
    comments = await _fetch_user_comments(user_id)
    content_ids = [item["id"] for item in posts + comments]
    mod_logs = await _fetch_moderation_history_for_content(content_ids)

    total_posts, total_comments, approved_posts, pending_posts, blocked_posts, pending_comments = await asyncio.gather(
        _count_user_items("posts", user_id),
        _count_user_items("comments", user_id),
        _count_user_items("posts", user_id, "APPROVED"),
        _count_user_pending_reviews("posts", user_id),
        _count_user_items("posts", user_id, "BLOCKED"),
        _count_user_pending_reviews("comments", user_id),
    )

    stats = UserDashboardStats(
        total_posts=total_posts,
        total_comments=total_comments,
        approved_posts=approved_posts,
        pending_review_posts=pending_posts,
        blocked_posts=blocked_posts,
        pending_review_comments=pending_comments,
    )

    history = [
        ModerationHistoryItem(
            content_id=log.get("content_id", log.get("post_id", "")),
            content_type=log.get("content_type", "post"),
            ai_label=log.get("ai_label", "Unknown"),
            confidence=float(log.get("confidence", 0)),
            recommendation=log.get("recommendation"),
            action_taken=log.get("action_taken", "UNKNOWN"),
            timestamp=log.get("timestamp", ""),
            human_review=(
                {
                    "reviewer_role": log["human_review"].get("reviewer_role"),
                    "review_action": log["human_review"].get("review_action"),
                    "reviewed_at": log["human_review"].get("reviewed_at"),
                }
                if log.get("human_review") else None
            ),
        )
        for log in mod_logs
    ]

    pending_items: List[Dict[str, Any]] = []
    for p in posts:
        if p.get("moderation_status") == "FLAGGED_FOR_REVIEW" and not p.get("admin_reviewed", False):
            pending_items.append({
                "type": "post",
                "id": p["id"],
                "content_preview": (p.get("content") or "")[:120],
                "moderation_status": p["moderation_status"],
                "prediction_label": p.get("ai_prediction", {}).get("label"),
                "confidence": p.get("ai_prediction", {}).get("confidence"),
                "created_at": p.get("created_at"),
            })
    for c in comments:
        if c.get("moderation_status") == "FLAGGED_FOR_REVIEW" and not c.get("admin_reviewed", False):
            pending_items.append({
                "type": "comment",
                "id": c["id"],
                "content_preview": (c.get("content") or "")[:120],
                "moderation_status": c["moderation_status"],
                "prediction_label": c.get("ai_prediction", {}).get("label"),
                "confidence": c.get("ai_prediction", {}).get("confidence"),
                "created_at": c.get("created_at"),
            })

    return UserDashboardResponse(
        stats=stats,
        posts=[PostResponse(**p) for p in posts],
        comments=[CommentResponse(**c) for c in comments],
        moderation_history=history,
        pending_items=pending_items,
    )
