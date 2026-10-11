import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List, Optional

from app.schemas.post import PostCreate, PostResponse, AIPrediction, XAIExplanation, WordAttribution
from app.schemas.moderation import AppealRequest
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
from app.services.notifications import create_notification

router = APIRouter()

@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_in: PostCreate,
    current_user: dict = Depends(get_current_user)
):
    # Validate length & sanitize
    if not InputSanitizer.validate_length(post_in.content, max_length=2000):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Post content length must be between 1 and 2000 characters."
        )

    sanitized_content = InputSanitizer.sanitize_text(post_in.content)

    # 1. Preprocess Text
    preproc = TextPreprocessor.process(sanitized_content)
    
    # 2. Language Detection
    lang = LanguageDetector.detect_language(preproc["model_text"])

    # 3. Model Inference (3 classes: Hate Speech, Offensive, Normal)
    prediction = inference_service.predict(preproc["model_text"])

    # 4. Rule-based keyword highlights (not a model-faithful XAI method)
    xai_res = xai_engine.explain(
        text=preproc["model_text"],
        label=prediction["predicted_class"],
        probabilities=prediction["probabilities"]
    )

    # 5. Policy Decision Engine
    mod_res = moderation_engine.process_moderation(prediction, lang_info=lang)

    post_id = str(uuid.uuid4())
    post_doc = {
        "id": post_id,
        "author_id": current_user["id"],
        "author_username": current_user["username"],
        "author_full_name": current_user.get("full_name"),
        "content": sanitized_content,
        "language": lang["code"],
        "language_supported": lang["is_supported"],
        "language_notice": lang.get("notice"),
        "moderation_recommendation": mod_res["recommendation"],
        "moderation_status": mod_res["final_status"],
        "moderation_explanation": mod_res["user_explanation"],
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
                "top_words": [WordAttribution(**item) for item in xai_res["top_words"]]
            }
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    # Save post
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["posts"].insert_one(post_doc)
        await db_manager.db["moderation_logs"].insert_one({
            "post_id": post_id,
            "content_id": post_id,
            "content_type": "post",
            "detected_language": lang["code"],
            "ai_label": prediction["predicted_class"],
            "confidence": prediction["confidence"],
            "recommendation": mod_res["recommendation"],
            "action_taken": mod_res["final_status"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    else:
        db_manager._collections["posts"].append(post_doc)
        db_manager._collections["moderation_logs"].append({
            "post_id": post_id,
            "content_id": post_id,
            "content_type": "post",
            "detected_language": lang["code"],
            "ai_label": prediction["predicted_class"],
            "confidence": prediction["confidence"],
            "recommendation": mod_res["recommendation"],
            "action_taken": mod_res["final_status"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    # Audit Log
    await audit_logger.log_event(
        actor_id=current_user["id"],
        actor_role=current_user["role"],
        event_type="POST_CREATED",
        resource_id=post_id,
        details=f"Post created. Moderation recommendation: {mod_res['recommendation']}, Status: {mod_res['final_status']}"
    )

    if mod_res["final_status"] != "APPROVED":
        await create_notification(
            recipient_id=current_user["id"], kind="MODERATION_RESULT",
            resource_type="post", resource_id=post_id,
        )

    return PostResponse(**post_doc)

@router.get("", response_model=List[PostResponse])
async def list_posts(
    status_filter: Optional[str] = Query(None, description="Public feed supports approved content only"),
    current_user: dict | None = Depends(get_optional_current_user),
):
    """Retrieve only approved content for the public feed."""
    if status_filter and status_filter != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only approved content is available in the public feed.",
        )
    if db_manager.use_mongo and db_manager.db is not None:
        query = {"moderation_status": "APPROVED"}
        cursor = db_manager.db["posts"].find(query).sort("created_at", -1).limit(50)
        posts = await cursor.to_list(length=50)
    else:
        posts = db_manager._collections["posts"]
        posts = [p for p in posts if p["moderation_status"] == "APPROVED"]
        posts = sorted(posts, key=lambda x: x["created_at"], reverse=True)

    post_ids = [p.get("id") for p in posts]
    if db_manager.use_mongo and db_manager.db is not None:
        likes = await db_manager.db["post_likes"].find({"post_id": {"$in": post_ids}}).to_list(length=None) if post_ids else []
        saved = await db_manager.db["saved_posts"].find({"user_id": current_user["id"], "post_id": {"$in": post_ids}}).to_list(length=None) if current_user and post_ids else []
    else:
        likes = [row for row in db_manager._collections["post_likes"] if row.get("post_id") in post_ids]
        saved = [row for row in db_manager._collections["saved_posts"] if current_user and row.get("user_id") == current_user["id"] and row.get("post_id") in post_ids]
    like_counts = {}
    liked_ids = set()
    for row in likes:
        like_counts[row["post_id"]] = like_counts.get(row["post_id"], 0) + 1
        if current_user and row.get("user_id") == current_user["id"]:
            liked_ids.add(row["post_id"])
    saved_ids = {row["post_id"] for row in saved}
    return [PostResponse(**{
        **p,
        "like_count": like_counts.get(p["id"], 0),
        "liked_by_me": p["id"] in liked_ids,
        "saved_by_me": p["id"] in saved_ids,
    }) for p in posts]

@router.get("/user/me", response_model=List[PostResponse])
async def get_my_posts(current_user: dict = Depends(get_current_user)):
    """User Data Isolation: Fetch only current logged-in user's posts & moderation history."""
    user_id = current_user["id"]
    if db_manager.use_mongo and db_manager.db is not None:
        cursor = db_manager.db["posts"].find({"author_id": user_id}).sort("created_at", -1)
        posts = await cursor.to_list(length=100)
    else:
        all_posts = db_manager._collections["posts"]
        posts = [p for p in all_posts if p.get("author_id") == user_id]
        posts = sorted(posts, key=lambda x: x["created_at"], reverse=True)

    return [PostResponse(**p) for p in posts]


@router.get("/saved/me", response_model=List[PostResponse])
async def get_saved_posts(current_user: dict = Depends(get_current_user)):
    if db_manager.use_mongo and db_manager.db is not None:
        saved_rows = await db_manager.db["saved_posts"].find({"user_id": current_user["id"]}).sort("created_at", -1).limit(100).to_list(length=100)
        post_ids = [row["post_id"] for row in saved_rows]
        posts = await db_manager.db["posts"].find({"id": {"$in": post_ids}, "moderation_status": "APPROVED"}).to_list(length=100) if post_ids else []
        likes = await db_manager.db["post_likes"].find({"post_id": {"$in": post_ids}}).to_list(length=None) if post_ids else []
    else:
        saved_rows = sorted(
            (row for row in db_manager._collections["saved_posts"] if row.get("user_id") == current_user["id"]),
            key=lambda row: row.get("created_at", ""), reverse=True,
        )[:100]
        post_ids = [row["post_id"] for row in saved_rows]
        posts = [row for row in db_manager._collections["posts"] if row.get("id") in post_ids and row.get("moderation_status") == "APPROVED"]
        likes = [row for row in db_manager._collections["post_likes"] if row.get("post_id") in post_ids]
    posts.sort(key=lambda row: post_ids.index(row["id"]) if row["id"] in post_ids else len(post_ids))
    like_counts = {}
    liked_ids = set()
    for row in likes:
        like_counts[row["post_id"]] = like_counts.get(row["post_id"], 0) + 1
        if row.get("user_id") == current_user["id"]:
            liked_ids.add(row["post_id"])
    return [PostResponse(**{**p, "like_count": like_counts.get(p["id"], 0), "liked_by_me": p["id"] in liked_ids, "saved_by_me": True}) for p in posts]


@router.put("/{post_id}/like")
async def like_post(post_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=60, window_seconds=60)
    if db_manager.use_mongo and db_manager.db is not None:
        post = await db_manager.db["posts"].find_one({"id": post_id, "moderation_status": "APPROVED"})
    else:
        post = next((p for p in db_manager._collections["posts"] if p.get("id") == post_id and p.get("moderation_status") == "APPROVED"), None)
    if not post:
        raise HTTPException(status_code=404, detail="Approved post not found.")
    now = datetime.now(timezone.utc).isoformat()
    like = {"id": str(uuid.uuid4()), "post_id": post_id, "user_id": current_user["id"], "created_at": now}
    created = False
    if db_manager.use_mongo and db_manager.db is not None:
        result = await db_manager.db["post_likes"].update_one(
            {"post_id": post_id, "user_id": current_user["id"]}, {"$setOnInsert": like}, upsert=True
        )
        created = result.upserted_id is not None
        like_count = await db_manager.db["post_likes"].count_documents({"post_id": post_id})
    else:
        likes = db_manager._collections["post_likes"]
        created = not any(row.get("post_id") == post_id and row.get("user_id") == current_user["id"] for row in likes)
        if created:
            likes.append(like)
        like_count = sum(1 for row in likes if row.get("post_id") == post_id)
    if created:
        await create_notification(
            recipient_id=post.get("author_id"), kind="POST_LIKE", actor_id=current_user["id"],
            actor_username=current_user["username"], resource_type="post", resource_id=post_id,
        )
    return {"liked": True, "like_count": like_count}


@router.delete("/{post_id}/like")
async def unlike_post(post_id: str, current_user: dict = Depends(get_current_user)):
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["post_likes"].delete_one({"post_id": post_id, "user_id": current_user["id"]})
        like_count = await db_manager.db["post_likes"].count_documents({"post_id": post_id})
    else:
        db_manager._collections["post_likes"] = [
            row for row in db_manager._collections["post_likes"]
            if not (row.get("post_id") == post_id and row.get("user_id") == current_user["id"])
        ]
        like_count = sum(1 for row in db_manager._collections["post_likes"] if row.get("post_id") == post_id)
    return {"liked": False, "like_count": like_count}


@router.put("/{post_id}/save")
async def save_post(post_id: str, current_user: dict = Depends(get_current_user)):
    if db_manager.use_mongo and db_manager.db is not None:
        post = await db_manager.db["posts"].find_one({"id": post_id, "moderation_status": "APPROVED"})
    else:
        post = next((p for p in db_manager._collections["posts"] if p.get("id") == post_id and p.get("moderation_status") == "APPROVED"), None)
    if not post:
        raise HTTPException(status_code=404, detail="Approved post not found.")
    row = {"id": str(uuid.uuid4()), "post_id": post_id, "user_id": current_user["id"], "created_at": datetime.now(timezone.utc).isoformat()}
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["saved_posts"].update_one({"post_id": post_id, "user_id": current_user["id"]}, {"$setOnInsert": row}, upsert=True)
    elif not any(item.get("post_id") == post_id and item.get("user_id") == current_user["id"] for item in db_manager._collections["saved_posts"]):
        db_manager._collections["saved_posts"].append(row)
    return {"saved": True}


@router.delete("/{post_id}/save")
async def unsave_post(post_id: str, current_user: dict = Depends(get_current_user)):
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["saved_posts"].delete_one({"post_id": post_id, "user_id": current_user["id"]})
    else:
        db_manager._collections["saved_posts"] = [
            row for row in db_manager._collections["saved_posts"]
            if not (row.get("post_id") == post_id and row.get("user_id") == current_user["id"])
        ]
    return {"saved": False}

@router.post("/{post_id}/appeal", response_model=PostResponse)
async def appeal_moderation_decision(
    post_id: str,
    appeal: AppealRequest,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """False Positive Handling: User requests review of moderation decision."""
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=10, window_seconds=60)
    post = None
    if db_manager.use_mongo and db_manager.db is not None:
        post = await db_manager.db["posts"].find_one({"id": post_id})
    else:
        post = next((p for p in db_manager._collections["posts"] if p["id"] == post_id), None)

    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    if post.get("author_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="You can only appeal moderation on your own posts.")

    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["posts"].update_one(
            {"id": post_id},
            {"$set": {
                "moderation_status": "FLAGGED_FOR_REVIEW",
                "admin_reviewed": False,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }}
        )
    post["moderation_status"] = "FLAGGED_FOR_REVIEW"
    post["admin_reviewed"] = False
    post["updated_at"] = datetime.now(timezone.utc).isoformat()

    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["moderation_logs"].update_one(
            {"post_id": post_id},
            {"$set": {
                "action_taken": "FLAGGED_FOR_REVIEW",
                "recommendation": "Manual Review",
                "appeal_requested_at": post["updated_at"],
            }},
        )
    else:
        for log in db_manager._collections.get("moderation_logs", []):
            if log.get("post_id") == post_id:
                log.update({
                    "action_taken": "FLAGGED_FOR_REVIEW",
                    "recommendation": "Manual Review",
                    "appeal_requested_at": post["updated_at"],
                })
                break

    await audit_logger.log_event(
        actor_id=current_user["id"],
        actor_role=current_user["role"],
        event_type="USER_MODERATION_APPEAL",
        resource_id=post_id,
        details="User requested a moderation review."
    )

    return PostResponse(**post)
