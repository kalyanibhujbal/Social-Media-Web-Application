from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from typing import List, Dict, Any
from datetime import datetime, timezone

from app.schemas.moderation import AdminReviewAction, AuditLogResponse, PrivacyRequestStatusUpdate
from app.schemas.admin import AdminUserAccessUpdate
from app.schemas.dashboard import AnalyticsResponse, AdminUserSummary, ConfidenceBucket, AdminContentResponse
from app.api.deps import require_admin, require_moderator_or_admin
from app.core.database import db_manager
from app.services.audit_logger import audit_logger
from app.services.moderation_log_service import update_human_review
from app.middleware.rate_limit import rate_limit_check
from ml_pipeline.train_eval import get_latest_evaluation
from app.services.model_inference import inference_service

router = APIRouter()

ACTION_ALIASES = {
    "APPROVE": "APPROVED",
    "REJECT": "BLOCKED",
    "FLAG": "FLAGGED_FOR_REVIEW",
    "MARK_REVIEWED": "MARK_REVIEWED",
    "APPROVED": "APPROVED",
    "BLOCKED": "BLOCKED",
    "FLAGGED_FOR_REVIEW": "FLAGGED_FOR_REVIEW",
}


def _normalize_action(raw: str) -> str:
    key = (raw or "").strip().upper()
    if key not in ACTION_ALIASES:
        raise HTTPException(
            status_code=400,
            detail="Action must be APPROVED, BLOCKED, FLAGGED_FOR_REVIEW, or MARK_REVIEWED.",
        )
    return ACTION_ALIASES[key]


async def _all_posts() -> List[dict]:
    if db_manager.use_mongo and db_manager.db is not None:
        return await db_manager.db["posts"].find().to_list(length=None)
    return list(db_manager._collections["posts"])


async def _all_comments() -> List[dict]:
    if db_manager.use_mongo and db_manager.db is not None:
        return await db_manager.db["comments"].find().to_list(length=None)
    return list(db_manager._collections.get("comments", []))


async def _all_audit_logs() -> List[dict]:
    if db_manager.use_mongo and db_manager.db is not None:
        return await db_manager.db["audit_logs"].find().to_list(length=None)
    return list(db_manager._collections["audit_logs"])


async def _moderation_logs(limit: int | None = 200) -> List[dict]:
    if db_manager.use_mongo and db_manager.db is not None:
        cursor = db_manager.db["moderation_logs"].find().sort("timestamp", -1)
        if limit is not None:
            cursor = cursor.limit(limit)
        return await cursor.to_list(length=limit)
    logs = db_manager._collections.get("moderation_logs", [])
    sorted_logs = sorted(logs, key=lambda x: x.get("timestamp", ""), reverse=True)
    return sorted_logs if limit is None else sorted_logs[:limit]


def _confidence_distribution(items: List[dict]) -> List[ConfidenceBucket]:
    high = medium = low = 0
    for item in items:
        conf = (item.get("ai_prediction") or {}).get("confidence")
        if conf is None:
            continue
        if conf >= 0.8:
            high += 1
        elif conf >= 0.5:
            medium += 1
        else:
            low += 1
    return [
        ConfidenceBucket(label="High (≥80%)", count=high),
        ConfidenceBucket(label="Medium (50–79%)", count=medium),
        ConfidenceBucket(label="Low (<50%)", count=low),
    ]


def _admin_content(item: dict, content_type: str) -> AdminContentResponse:
    return AdminContentResponse(
        id=item["id"],
        content_type=content_type,
        content=item.get("content", ""),
        ai_prediction=item.get("ai_prediction"),
        moderation_recommendation=item.get("moderation_recommendation"),
        moderation_status=item.get("moderation_status", "UNKNOWN"),
        moderation_explanation=item.get("moderation_explanation"),
        created_at=item.get("created_at", ""),
    )


async def _find_content(content_type: str, content_id: str):
    if content_type not in {"post", "comment"}:
        raise HTTPException(status_code=400, detail="Content type must be post or comment.")
    collection_name = "posts" if content_type == "post" else "comments"
    if db_manager.use_mongo and db_manager.db is not None:
        return await db_manager.db[collection_name].find_one({"id": content_id})
    return next((item for item in db_manager._collections.get(collection_name, []) if item.get("id") == content_id), None)


@router.get("/queue", response_model=List[AdminContentResponse])
async def get_review_queue(request: Request, admin: dict = Depends(require_moderator_or_admin)):
    """Flagged or blocked posts and comments, without author account fields."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    rate_limit_check(client_ip, max_requests=30, window_seconds=60)

    queued = []
    for content_type, collection_name in (("post", "posts"), ("comment", "comments")):
        if db_manager.use_mongo and db_manager.db is not None:
            cursor = db_manager.db[collection_name].find({
                "moderation_status": {"$in": ["FLAGGED_FOR_REVIEW", "BLOCKED"]},
                "admin_reviewed": {"$ne": True},
            }).sort("created_at", -1)
            items = await cursor.to_list(length=None)
        else:
            items = [
                item for item in db_manager._collections.get(collection_name, [])
                if item.get("moderation_status") in {"FLAGGED_FOR_REVIEW", "BLOCKED"}
                and not item.get("admin_reviewed", False)
            ]
        queued.extend(_admin_content(item, content_type) for item in items)
    return sorted(queued, key=lambda item: item.created_at, reverse=True)


@router.get("/content/{post_id}", response_model=AdminContentResponse)
async def get_content_for_review(
    post_id: str,
    request: Request,
    content_type: str = Query("post"),
    admin: dict = Depends(require_moderator_or_admin),
):
    """Inspect moderation context without exposing author account details."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    rate_limit_check(client_ip, max_requests=30, window_seconds=60)

    item = await _find_content(content_type, post_id)
    if not item:
        raise HTTPException(status_code=404, detail="Content not found.")
    return _admin_content(item, content_type)


@router.post("/review/{post_id}", response_model=AdminContentResponse)
async def review_post(
    post_id: str,
    review: AdminReviewAction,
    request: Request,
    content_type: str = Query("post"),
    admin: dict = Depends(require_moderator_or_admin),
):
    """Approve, reject, flag, or mark reviewed — with audit trail."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    rate_limit_check(client_ip, max_requests=30, window_seconds=60)

    action = _normalize_action(review.action)
    if action != "MARK_REVIEWED" and not review.confirm_action:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirm this moderation decision before applying it.",
        )

    item = await _find_content(content_type, post_id)
    if not item:
        raise HTTPException(status_code=404, detail="Content not found.")

    review_action_log = action
    if action == "MARK_REVIEWED":
        review_action_log = "MARKED_REVIEWED"
    elif action == "APPROVED":
        review_action_log = "OVERRIDDEN_APPROVE"
    elif action == "BLOCKED":
        review_action_log = "CONFIRMED_BLOCK"
    elif action == "FLAGGED_FOR_REVIEW":
        review_action_log = "FLAGGED_FOR_REVIEW"

    update_fields: Dict[str, Any] = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "admin_reviewed": True,
    }
    if action != "MARK_REVIEWED":
        update_fields["moderation_status"] = action

    collection_name = "posts" if content_type == "post" else "comments"
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db[collection_name].update_one({"id": post_id}, {"$set": update_fields})
        item.update(update_fields)
    else:
        item.update(update_fields)

    await update_human_review(
        post_id=post_id,
        reviewer_id=admin["id"],
        reviewer_role=admin.get("role", "ADMIN"),
        review_action=review_action_log,
        content_type=content_type,
        final_status=item.get("moderation_status"),
    )

    await audit_logger.log_event(
        actor_id=admin["id"],
        actor_role=admin.get("role", "ADMIN"),
        event_type=f"ADMIN_REVIEW_{content_type.upper()}",
        resource_id=post_id,
        details=f"Admin moderation action: {action}.",
    )

    return _admin_content(item, content_type)


@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def get_audit_logs(request: Request, admin: dict = Depends(require_admin)):
    client_ip = request.client.host if request.client else "127.0.0.1"
    rate_limit_check(client_ip, max_requests=30, window_seconds=60)

    if db_manager.use_mongo and db_manager.db is not None:
        cursor = db_manager.db["audit_logs"].find().sort("timestamp", -1).limit(100)
        logs = await cursor.to_list(length=100)
    else:
        logs = sorted(
            db_manager._collections["audit_logs"],
            key=lambda x: x["timestamp"],
            reverse=True,
        )[:100]

    return [AuditLogResponse(**l) for l in logs]


@router.get("/moderation-history")
async def get_moderation_history(request: Request, admin: dict = Depends(require_moderator_or_admin)):
    """Recent moderation decisions with reviewer identity and notes removed."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    rate_limit_check(client_ip, max_requests=30, window_seconds=60)

    logs = await _moderation_logs(100)
    sanitized = []
    for log in logs:
        human_review = log.get("human_review") or {}
        sanitized.append({
            "content_id": log.get("content_id", log.get("post_id")),
            "content_type": log.get("content_type", "post"),
            "ai_label": log.get("ai_label"),
            "confidence": log.get("confidence"),
            "recommendation": log.get("recommendation"),
            "action_taken": log.get("action_taken"),
            "timestamp": log.get("timestamp"),
            "human_review": ({
                "reviewer_role": human_review.get("reviewer_role"),
                "review_action": human_review.get("review_action"),
                "reviewed_at": human_review.get("reviewed_at"),
            } if human_review else None),
        })
    return sanitized


@router.get("/users", response_model=List[AdminUserSummary])
async def list_users_minimal(request: Request, admin: dict = Depends(require_admin)):
    """User management view with data minimization (no emails or password hashes)."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    rate_limit_check(client_ip, max_requests=20, window_seconds=60)

    if db_manager.use_mongo and db_manager.db is not None:
        cursor = db_manager.db["users"].find({}, {"password_hash": 0, "email": 0})
        users = await cursor.to_list(length=None)
    else:
        users = [
            {
                "id": u["id"],
                "username": u["username"],
                "role": u.get("role", "USER"),
                "is_active": u.get("is_active", True),
                "created_at": u.get("created_at", ""),
            }
            for u in db_manager._collections["users"]
        ]

    return [
        AdminUserSummary(
            id=u["id"],
            username=u["username"],
            role=u.get("role", "USER"),
            is_active=u.get("is_active", True),
            created_at=u.get("created_at", ""),
        )
        for u in users
    ]


@router.patch("/users/{user_id}", response_model=AdminUserSummary)
async def update_user_access(
    user_id: str,
    update: AdminUserAccessUpdate,
    request: Request,
    admin: dict = Depends(require_admin),
):
    """Allow administrators to assign USER/MODERATOR/ADMIN and activate accounts."""
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=20, window_seconds=60)
    if db_manager.use_mongo and db_manager.db is not None:
        target = await db_manager.db["users"].find_one({"id": user_id})
    else:
        target = next((row for row in db_manager._collections["users"] if row.get("id") == user_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="User account not found.")
    fields = update.model_dump(exclude_none=True)
    if not fields:
        raise HTTPException(status_code=400, detail="Provide a role or account status to update.")
    if user_id == admin["id"] and (fields.get("role", "ADMIN") != "ADMIN" or fields.get("is_active", True) is False):
        raise HTTPException(status_code=400, detail="You cannot remove your own active administrator access.")

    removes_admin = target.get("role") == "ADMIN" and (fields.get("role", "ADMIN") != "ADMIN" or fields.get("is_active", True) is False)
    if removes_admin:
        if db_manager.use_mongo and db_manager.db is not None:
            active_admins = await db_manager.db["users"].count_documents({"role": "ADMIN", "is_active": {"$ne": False}})
        else:
            active_admins = sum(1 for row in db_manager._collections["users"] if row.get("role") == "ADMIN" and row.get("is_active", True))
        if active_admins <= 1:
            raise HTTPException(status_code=409, detail="At least one active administrator must remain.")

    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["users"].update_one({"id": user_id}, {"$set": fields})
        target = await db_manager.db["users"].find_one({"id": user_id})
    else:
        target.update(fields)

    await audit_logger.log_event(
        actor_id=admin["id"], actor_role=admin.get("role", "ADMIN"),
        event_type="ADMIN_USER_ACCESS_UPDATED", resource_id=user_id,
        details="An administrator updated a user role or account status.",
    )
    return AdminUserSummary(
        id=target["id"], username=target["username"], role=target.get("role", "USER"),
        is_active=target.get("is_active", True), created_at=target.get("created_at", ""),
    )


@router.get("/privacy-requests")
async def list_privacy_requests(request: Request, admin: dict = Depends(require_admin)):
    """Return only the information needed to handle account privacy requests."""
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=20, window_seconds=60)
    if db_manager.use_mongo and db_manager.db is not None:
        rows = await db_manager.db["privacy_requests"].find().sort("created_at", -1).limit(200).to_list(length=200)
    else:
        rows = sorted(
            db_manager._collections.get("privacy_requests", []),
            key=lambda row: row.get("created_at", ""),
            reverse=True,
        )[:200]
    return [
        {
            "id": row["id"],
            "requester_reference": row.get("user_id"),
            "request_type": row["request_type"],
            "description": row.get("description"),
            "status": row["status"],
            "response": row.get("response"),
            "created_at": row["created_at"],
            "resolved_at": row.get("resolved_at"),
        }
        for row in rows
    ]


@router.patch("/privacy-requests/{request_id}")
async def update_privacy_request(
    request_id: str,
    update: PrivacyRequestStatusUpdate,
    request: Request,
    admin: dict = Depends(require_admin),
):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=20, window_seconds=60)
    resolved_at = datetime.now(timezone.utc).isoformat()
    fields = {"status": update.status, "response": update.response.strip(), "resolved_at": resolved_at}
    if db_manager.use_mongo and db_manager.db is not None:
        result = await db_manager.db["privacy_requests"].update_one({"id": request_id}, {"$set": fields})
        if not result.matched_count:
            raise HTTPException(status_code=404, detail="Privacy request not found.")
        row = await db_manager.db["privacy_requests"].find_one({"id": request_id})
    else:
        row = next((item for item in db_manager._collections.get("privacy_requests", []) if item.get("id") == request_id), None)
        if not row:
            raise HTTPException(status_code=404, detail="Privacy request not found.")
        row.update(fields)

    await audit_logger.log_event(
        actor_id=admin["id"],
        actor_role="ADMIN",
        event_type="ADMIN_PRIVACY_REQUEST_UPDATED",
        resource_id=request_id,
        details=f"Privacy request status updated to {update.status}.",
    )
    return {
        "id": row["id"],
        "request_type": row["request_type"],
        "status": row["status"],
        "response": row.get("response"),
        "created_at": row["created_at"],
        "resolved_at": row.get("resolved_at"),
    }


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(request: Request, admin: dict = Depends(require_admin)):
    client_ip = request.client.host if request.client else "127.0.0.1"
    rate_limit_check(client_ip, max_requests=30, window_seconds=60)

    all_posts = await _all_posts()
    all_comments = await _all_comments()
    all_logs = await _all_audit_logs()
    mod_history = await _moderation_logs(None)
    all_items = all_posts + all_comments

    approved = sum(1 for item in all_items if item.get("moderation_status") == "APPROVED")
    flagged = sum(1 for item in all_items if item.get("moderation_status") == "FLAGGED_FOR_REVIEW")
    blocked = sum(1 for item in all_items if item.get("moderation_status") == "BLOCKED")

    hate = sum(1 for item in all_items if (item.get("ai_prediction") or {}).get("label") == "Hate Speech")
    offensive = sum(1 for item in all_items if (item.get("ai_prediction") or {}).get("label") == "Offensive")
    normal = sum(1 for item in all_items if (item.get("ai_prediction") or {}).get("label") == "Normal")

    overrides = sum(
        1 for log in all_logs
        if log.get("event_type", "").startswith("ADMIN_REVIEW_")
        or log.get("event_type") == "ADMIN_OVERRIDE_POST"
    )

    eval_results = get_latest_evaluation()
    model_information = {
        "model_name": inference_service.model_name,
        "model_version": inference_service.model_version,
        "inference_backend": "transformer" if inference_service.is_loaded else "heuristic fallback",
    }

    return AnalyticsResponse(
        total_moderation_items=len(all_items),
        total_posts=len(all_posts),
        total_comments=len(all_comments),
        approved_count=approved,
        flagged_count=flagged,
        blocked_count=blocked,
        hate_speech_count=hate,
        offensive_count=offensive,
        normal_count=normal,
        override_count=overrides,
        confidence_distribution=_confidence_distribution(all_items),
        moderation_history_count=len(mod_history),
        pending_manual_reviews=sum(
            1 for item in all_items
            if item.get("moderation_status") in {"FLAGGED_FOR_REVIEW", "BLOCKED"}
            and not item.get("admin_reviewed", False)
        ),
        model_evaluation=eval_results,
        model_information=model_information,
    )


@router.get("/report")
async def generate_system_report(request: Request, admin: dict = Depends(require_admin)):
    """Generate moderation summary report from actual system data only."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    rate_limit_check(client_ip, max_requests=10, window_seconds=60)

    analytics = await get_analytics(request, admin)
    mod_history = await get_moderation_history(request, admin)
    eval_results = get_latest_evaluation()

    await audit_logger.log_event(
        actor_id=admin["id"],
        actor_role="ADMIN",
        event_type="ADMIN_REPORT_GENERATED",
        details="Generated a moderation system report.",
    )

    return {
        "report_title": "AI Social Media Content Moderation & XAI System Report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by_role": "ADMIN",
        "system_summary": analytics.model_dump(),
        "moderation_history_sample": mod_history[:50],
        "model_evaluation": eval_results,
    }
