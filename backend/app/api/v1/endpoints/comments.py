import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List

from app.schemas.comment import CommentCreate, CommentResponse
from app.schemas.post import AIPrediction
from app.api.deps import get_current_user, get_optional_current_user
from app.services.sanitizer import InputSanitizer
from app.services.preprocessing import TextPreprocessor
from app.services.lang_detect import LanguageDetector
from app.services.model_inference import inference_service
from app.services.xai_engine import xai_engine
from app.services.moderation_engine import moderation_engine
from app.services.audit_logger import audit_logger
from app.core.database import db_manager
from app.middleware.rate_limit import rate_limit_check
from app.services.notifications import create_notification, content_notification_section
from app.services.social_access import can_view_post

router = APIRouter()

@router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    comment_in: CommentCreate,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=20, window_seconds=60)
    # Validate length & sanitize
    if not InputSanitizer.validate_length(comment_in.content, max_length=1000):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comment length must be between 1 and 1000 characters."
        )

    sanitized_content = InputSanitizer.sanitize_text(comment_in.content)

    if db_manager.use_mongo and db_manager.db is not None:
        parent_post = await db_manager.db["posts"].find_one({"id": comment_in.post_id, "moderation_status": "APPROVED"})
    else:
        parent_post = next((
            post for post in db_manager._collections.get("posts", [])
            if post.get("id") == comment_in.post_id and post.get("moderation_status") == "APPROVED"
        ), None)
    if not parent_post:
        raise HTTPException(status_code=404, detail="Approved post not found.")
    if not await can_view_post(parent_post, current_user["id"]):
        raise HTTPException(status_code=404, detail="Approved post not found.")

    parent_comment = None
    if comment_in.parent_comment_id:
        if db_manager.use_mongo and db_manager.db is not None:
            parent_comment = await db_manager.db["comments"].find_one({
                "id": comment_in.parent_comment_id,
                "post_id": comment_in.post_id,
                "moderation_status": "APPROVED",
            })
        else:
            parent_comment = next((
                item for item in db_manager._collections.get("comments", [])
                if item.get("id") == comment_in.parent_comment_id
                and item.get("post_id") == comment_in.post_id
                and item.get("moderation_status") == "APPROVED"
            ), None)
        if not parent_comment:
            raise HTTPException(status_code=404, detail="Approved parent comment not found.")

    # Preprocess & Lang Detect
    preproc = TextPreprocessor.process(sanitized_content)
    lang = LanguageDetector.detect_language(preproc["model_text"])

    # Predict & Explain
    prediction = inference_service.predict(preproc["model_text"])
    xai_res = xai_engine.explain(
        text=preproc["model_text"],
        label=prediction["label"],
        probabilities=prediction["probabilities"]
    )
    mod_result = moderation_engine.process_moderation(prediction, lang_info=lang)
    mod_status = mod_result["final_status"]

    comment_id = str(uuid.uuid4())
    comment_doc = {
        "id": comment_id,
        "post_id": comment_in.post_id,
        "parent_comment_id": comment_in.parent_comment_id,
        "author_id": current_user["id"],
        "author_username": current_user["username"],
        "author_full_name": current_user.get("full_name"),
        "author_avatar_url": current_user.get("avatar_url"),
        "content": sanitized_content,
        "language": lang["code"],
        "language_supported": lang["is_supported"],
        "language_notice": lang.get("notice"),
        "moderation_recommendation": mod_result["recommendation"],
        "moderation_status": mod_status,
        "moderation_explanation": mod_result["user_explanation"],
        "ai_prediction": {
            "label": prediction["predicted_class"],
            "predicted_class": prediction["predicted_class"],
            "confidence": prediction["confidence"],
            "confidence_level": prediction["confidence_level"],
            "probabilities": prediction["probabilities"],
            "is_low_confidence": prediction["is_low_confidence"],
            "model_name": prediction["model_name"],
            "model_version": prediction["model_version"],
            "inference_timestamp": prediction["inference_timestamp"],
            "explanation": {
                "method": xai_res["method"],
                "top_words": xai_res["top_words"]
            }
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["comments"].insert_one(comment_doc)
        await db_manager.db["moderation_logs"].insert_one({
            "content_id": comment_id,
            "content_type": "comment",
            "ai_label": prediction["predicted_class"],
            "confidence": prediction["confidence"],
            "recommendation": mod_result["recommendation"],
            "action_taken": mod_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    else:
        if "comments" not in db_manager._collections:
            db_manager._collections["comments"] = []
        db_manager._collections["comments"].append(comment_doc)
        db_manager._collections["moderation_logs"].append({
            "content_id": comment_id,
            "content_type": "comment",
            "ai_label": prediction["predicted_class"],
            "confidence": prediction["confidence"],
            "recommendation": mod_result["recommendation"],
            "action_taken": mod_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    await audit_logger.log_event(
        actor_id=current_user["id"],
        actor_role=current_user["role"],
        event_type="COMMENT_CREATED",
        resource_id=comment_id,
        details=f"Comment created. Moderation outcome: {mod_status}."
    )

    if mod_status == "APPROVED":
        await create_notification(
            recipient_id=(parent_comment or parent_post).get("author_id"), kind="COMMENT",
            actor_id=current_user["id"], actor_username=current_user["username"],
            resource_type="comment" if parent_comment else "post",
            resource_id=comment_in.parent_comment_id or comment_in.post_id,
            section=content_notification_section(parent_post.get("content_type")),
        )
    else:
        await create_notification(
            recipient_id=current_user["id"], kind="MODERATION_RESULT",
            resource_type="comment", resource_id=comment_id,
            section=content_notification_section(parent_post.get("content_type")),
        )

    return CommentResponse(**comment_doc)

@router.get("/post/{post_id}", response_model=List[CommentResponse])
async def list_comments_for_post(
    post_id: str,
    current_user: dict | None = Depends(get_optional_current_user),
):
    """Fetch approved comments for a specific post."""
    if db_manager.use_mongo and db_manager.db is not None:
        post = await db_manager.db["posts"].find_one({"id": post_id, "moderation_status": "APPROVED"})
    else:
        post = next((
            row for row in db_manager._collections.get("posts", [])
            if row.get("id") == post_id and row.get("moderation_status") == "APPROVED"
        ), None)
    if not post or not await can_view_post(post, current_user.get("id") if current_user else None):
        raise HTTPException(status_code=404, detail="Approved post not found.")
    if db_manager.use_mongo and db_manager.db is not None:
        cursor = db_manager.db["comments"].find({
            "post_id": post_id,
            "moderation_status": "APPROVED"
        }).sort("created_at", 1)
        comments = await cursor.to_list(length=100)
    else:
        all_comments = db_manager._collections.get("comments", [])
        comments = [c for c in all_comments if c["post_id"] == post_id and c["moderation_status"] == "APPROVED"]
        comments = sorted(comments, key=lambda x: x["created_at"])

    result = []
    for comment in comments:
        if db_manager.use_mongo and db_manager.db is not None:
            query = {"comment_id": comment["id"]}
            like_count = await db_manager.db["comment_likes"].count_documents(query)
            liked = bool(current_user and await db_manager.db["comment_likes"].find_one({**query, "user_id": current_user["id"]}))
        else:
            likes = [like for like in db_manager._collections.get("comment_likes", []) if like.get("comment_id") == comment["id"]]
            like_count = len(likes)
            liked = bool(current_user and any(like.get("user_id") == current_user["id"] for like in likes))
        result.append(CommentResponse(**{**comment, "like_count": like_count, "liked_by_me": liked}))
    return result


@router.get("/user/me", response_model=List[CommentResponse])
async def get_my_comments(current_user: dict = Depends(get_current_user)):
    """User data isolation: only the current user's comments."""
    user_id = current_user["id"]
    if db_manager.use_mongo and db_manager.db is not None:
        cursor = db_manager.db["comments"].find({"author_id": user_id}).sort("created_at", -1)
        comments = await cursor.to_list(length=100)
    else:
        all_comments = db_manager._collections.get("comments", [])
        comments = [c for c in all_comments if c.get("author_id") == user_id]
        comments = sorted(comments, key=lambda x: x["created_at"], reverse=True)

    return [CommentResponse(**c) for c in comments]


@router.put("/{comment_id}/like")
async def like_comment(
    comment_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=60, window_seconds=60)
    if db_manager.use_mongo and db_manager.db is not None:
        comment = await db_manager.db["comments"].find_one({"id": comment_id, "moderation_status": "APPROVED"})
    else:
        comment = next((item for item in db_manager._collections.get("comments", []) if item.get("id") == comment_id and item.get("moderation_status") == "APPROVED"), None)
    if not comment:
        raise HTTPException(status_code=404, detail="Approved comment not found.")
    if db_manager.use_mongo and db_manager.db is not None:
        post = await db_manager.db["posts"].find_one({"id": comment["post_id"], "moderation_status": "APPROVED"})
    else:
        post = next((row for row in db_manager._collections.get("posts", []) if row.get("id") == comment.get("post_id") and row.get("moderation_status") == "APPROVED"), None)
    if not post or not await can_view_post(post, current_user["id"]):
        raise HTTPException(status_code=404, detail="Approved comment not found.")

    now = datetime.now(timezone.utc).isoformat()
    like = {"id": str(uuid.uuid4()), "comment_id": comment_id, "user_id": current_user["id"], "created_at": now}
    created = False
    if db_manager.use_mongo and db_manager.db is not None:
        result = await db_manager.db["comment_likes"].update_one(
            {"comment_id": comment_id, "user_id": current_user["id"]},
            {"$setOnInsert": like}, upsert=True,
        )
        created = result.upserted_id is not None
        like_count = await db_manager.db["comment_likes"].count_documents({"comment_id": comment_id})
    else:
        likes = db_manager._collections["comment_likes"]
        created = not any(item.get("comment_id") == comment_id and item.get("user_id") == current_user["id"] for item in likes)
        if created:
            likes.append(like)
        like_count = sum(1 for item in likes if item.get("comment_id") == comment_id)
    if created:
        await create_notification(
            recipient_id=comment.get("author_id"), kind="COMMENT_LIKE",
            actor_id=current_user["id"], actor_username=current_user["username"],
            resource_type="comment", resource_id=comment_id,
            section=content_notification_section(post.get("content_type")),
        )
    return {"liked": True, "like_count": like_count}


@router.delete("/{comment_id}/like")
async def unlike_comment(comment_id: str, current_user: dict = Depends(get_current_user)):
    if db_manager.use_mongo and db_manager.db is not None:
        comment = await db_manager.db["comments"].find_one({"id": comment_id, "moderation_status": "APPROVED"})
        post = await db_manager.db["posts"].find_one({"id": comment.get("post_id"), "moderation_status": "APPROVED"}) if comment else None
    else:
        comment = next((row for row in db_manager._collections.get("comments", []) if row.get("id") == comment_id and row.get("moderation_status") == "APPROVED"), None)
        post = next((row for row in db_manager._collections.get("posts", []) if comment and row.get("id") == comment.get("post_id") and row.get("moderation_status") == "APPROVED"), None)
    if not comment or not post or not await can_view_post(post, current_user["id"]):
        raise HTTPException(status_code=404, detail="Approved comment not found.")
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["comment_likes"].delete_one({"comment_id": comment_id, "user_id": current_user["id"]})
        like_count = await db_manager.db["comment_likes"].count_documents({"comment_id": comment_id})
    else:
        db_manager._collections["comment_likes"] = [
            item for item in db_manager._collections["comment_likes"]
            if not (item.get("comment_id") == comment_id and item.get("user_id") == current_user["id"])
        ]
        like_count = sum(1 for item in db_manager._collections["comment_likes"] if item.get("comment_id") == comment_id)
    return {"liked": False, "like_count": like_count}


@router.delete("/{comment_id}")
async def delete_comment(comment_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=20, window_seconds=60)
    if db_manager.use_mongo and db_manager.db is not None:
        comment = await db_manager.db["comments"].find_one({"id": comment_id})
    else:
        comment = next((row for row in db_manager._collections.get("comments", []) if row.get("id") == comment_id), None)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found.")
    if comment.get("author_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="You can delete only your own comments.")
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["comments"].delete_one({"id": comment_id, "author_id": current_user["id"]})
        await db_manager.db["comments"].update_many(
            {"post_id": comment["post_id"], "parent_comment_id": comment_id},
            {"$set": {"parent_comment_id": comment.get("parent_comment_id")}},
        )
        await db_manager.db["comment_likes"].delete_many({"comment_id": comment_id})
        await db_manager.db["moderation_logs"].delete_many({"content_id": comment_id})
    else:
        for reply in db_manager._collections["comments"]:
            if reply.get("parent_comment_id") == comment_id:
                reply["parent_comment_id"] = comment.get("parent_comment_id")
        db_manager._collections["comments"] = [row for row in db_manager._collections["comments"] if row.get("id") != comment_id]
        db_manager._collections["comment_likes"] = [row for row in db_manager._collections["comment_likes"] if row.get("comment_id") != comment_id]
        db_manager._collections["moderation_logs"] = [row for row in db_manager._collections["moderation_logs"] if row.get("content_id") != comment_id]
    await audit_logger.log_event(current_user["id"], current_user["role"], "COMMENT_DELETED", "A user deleted their own comment.")
    return {"status": "DELETED"}
