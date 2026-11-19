import uuid
from datetime import date, datetime, time, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, status, Query, Request, UploadFile
from fastapi.responses import FileResponse
from typing import List, Optional

from app.schemas.post import PostCreate, PostResponse
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
from app.services.notifications import create_notification, content_notification_section
from app.services.social_access import can_view_post, visible_author_ids
from app.services.media_storage import (
    IMAGE_LIMIT,
    VIDEO_LIMIT,
    delete_media_files,
    media_path,
    store_upload,
)

router = APIRouter()


def _moderate_text(text: str, *, classify_all_text: bool = False) -> dict:
    if not text.strip():
        return {
            "content": "",
            "language": "und",
            "language_supported": True,
            "language_notice": None,
            "moderation_recommendation": "Publish",
            "moderation_status": "APPROVED",
            "moderation_explanation": "No text was submitted. Media is not analyzed by the moderation model.",
            "ai_prediction": None,
            "detected_language": "und",
        }

    sanitized_text = InputSanitizer.sanitize_text(text)
    preproc = TextPreprocessor.process(sanitized_text)
    lang = LanguageDetector.detect_language(preproc["model_text"])
    model_text = preproc["model_text"]
    text_chunks = [model_text]
    if classify_all_text and len(model_text) > 512:
        text_chunks = []
        remaining_text = model_text
        while len(remaining_text) > 512:
            split_at = remaining_text.rfind(" ", 0, 513)
            if split_at <= 0:
                split_at = 512
            text_chunks.append(remaining_text[:split_at].strip())
            remaining_text = remaining_text[split_at:].strip()
        if remaining_text:
            text_chunks.append(remaining_text)

    predictions = [(chunk, inference_service.predict(chunk)) for chunk in text_chunks]
    severity = {"Normal": 0, "Offensive": 1, "Hate Speech": 2}
    explanation_text, prediction = max(
        predictions,
        key=lambda item: (
            severity.get(item[1].get("predicted_class", item[1].get("label")), 0),
            item[1].get("confidence", 0),
        ),
    )
    xai_res = xai_engine.explain(
        text=explanation_text,
        label=prediction["predicted_class"],
        probabilities=prediction["probabilities"],
    )
    mod_res = moderation_engine.process_moderation(prediction, lang_info=lang)
    return {
        "content": sanitized_text,
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
                "top_words": xai_res["top_words"],
            },
        },
        "detected_language": lang["code"],
    }


def _build_post(
    current_user: dict,
    content: str,
    moderation: dict,
    *,
    content_type: str = "POST",
    media: list[dict] | None = None,
    event: dict | None = None,
    article: dict | None = None,
) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "author_id": current_user["id"],
        "author_username": current_user["username"],
        "author_full_name": current_user.get("full_name"),
        "author_avatar_url": current_user.get("avatar_url"),
        "content": content,
        "content_type": content_type,
        "media": media or [],
        "event": event,
        "article": article,
        "language": moderation["language"],
        "language_supported": moderation["language_supported"],
        "language_notice": moderation["language_notice"],
        "moderation_recommendation": moderation["moderation_recommendation"],
        "moderation_status": moderation["moderation_status"],
        "moderation_explanation": moderation["moderation_explanation"],
        "ai_prediction": moderation["ai_prediction"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


async def _notify_network_of_post(post_doc: dict) -> None:
    content_type = post_doc.get("content_type", "POST")
    notification_kind = {
        "POST": "NETWORK_POST",
        "ARTICLE": "NETWORK_ARTICLE",
        "EVENT": "NETWORK_EVENT",
    }.get(content_type)
    if not notification_kind or post_doc.get("moderation_status") != "APPROVED":
        return
    author_id = post_doc["author_id"]
    if db_manager.use_mongo and db_manager.db is not None:
        author = await db_manager.db["users"].find_one(
            {"id": author_id, "is_active": {"$ne": False}},
            {"id": 1, "is_private": 1},
        )
        if not author:
            return
        connections = await db_manager.db["connections"].find(
            {"status": "ACCEPTED", "$or": [{"requester_id": author_id}, {"recipient_id": author_id}]},
            {"requester_id": 1, "recipient_id": 1},
        ).to_list(length=None)
        follows = []
        if author.get("is_private", False):
            follows = await db_manager.db["follows"].find(
                {
                    "following_id": author_id,
                    "$or": [{"status": "ACCEPTED"}, {"status": {"$exists": False}}],
                },
                {"follower_id": 1},
            ).to_list(length=None)
        recipients = {
            row["recipient_id"] if row["requester_id"] == author_id else row["requester_id"]
            for row in connections
        }
        if author.get("is_private", False):
            recipients.intersection_update(row["follower_id"] for row in follows if row.get("follower_id"))
        if recipients:
            active_users = await db_manager.db["users"].find(
                {"id": {"$in": list(recipients)}, "is_active": {"$ne": False}},
                {"id": 1},
            ).to_list(length=None)
            recipients = {row["id"] for row in active_users if row.get("id")}
    else:
        author = next(
            (
                row for row in db_manager._collections.get("users", [])
                if row.get("id") == author_id and row.get("is_active", True)
            ),
            None,
        )
        if not author:
            return
        connections = [
            row for row in db_manager._collections.get("connections", [])
            if row.get("status") == "ACCEPTED" and author_id in {row.get("requester_id"), row.get("recipient_id")}
        ]
        follows = []
        if author.get("is_private", False):
            follows = [
                row for row in db_manager._collections.get("follows", [])
                if row.get("following_id") == author_id and row.get("status", "ACCEPTED") == "ACCEPTED"
            ]
        recipients = {
            row["recipient_id"] if row["requester_id"] == author_id else row["requester_id"]
            for row in connections
        }
        if author.get("is_private", False):
            recipients.intersection_update(row["follower_id"] for row in follows if row.get("follower_id"))
        active_users = {
            row["id"] for row in db_manager._collections.get("users", [])
            if row.get("id") in recipients and row.get("is_active", True)
        }
        recipients = active_users

    for recipient_id in recipients:
        await create_notification(
            recipient_id=recipient_id,
            kind=notification_kind,
            actor_id=author_id,
            actor_username=post_doc.get("author_username"),
            resource_type="post",
            resource_id=post_doc["id"],
            deduplicate=True,
        )


async def _save_post(post_doc: dict, current_user: dict) -> None:
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["posts"].insert_one(post_doc)
        if post_doc.get("ai_prediction"):
            await db_manager.db["moderation_logs"].insert_one({
                "post_id": post_doc["id"],
                "content_id": post_doc["id"],
                "content_type": "post",
                "detected_language": post_doc["language"],
                "ai_label": post_doc["ai_prediction"]["predicted_class"],
                "confidence": post_doc["ai_prediction"]["confidence"],
                "recommendation": post_doc["moderation_recommendation"],
                "action_taken": post_doc["moderation_status"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    else:
        db_manager._collections["posts"].append(post_doc)
        if post_doc.get("ai_prediction"):
            db_manager._collections["moderation_logs"].append({
                "post_id": post_doc["id"],
                "content_id": post_doc["id"],
                "content_type": "post",
                "detected_language": post_doc["language"],
                "ai_label": post_doc["ai_prediction"]["predicted_class"],
                "confidence": post_doc["ai_prediction"]["confidence"],
                "recommendation": post_doc["moderation_recommendation"],
                "action_taken": post_doc["moderation_status"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    content_type = post_doc.get("content_type", "POST")
    await audit_logger.log_event(
        actor_id=current_user["id"],
        actor_role=current_user["role"],
        event_type=f"{content_type}_CREATED",
        resource_id=post_doc["id"],
        details=f"{content_type.title()} created. Moderation status: {post_doc['moderation_status']}.",
    )
    if post_doc["moderation_status"] != "APPROVED":
        await create_notification(
            recipient_id=current_user["id"],
            kind="MODERATION_RESULT",
            resource_type="post",
            resource_id=post_doc["id"],
            section=content_notification_section(content_type),
        )
    else:
        await _notify_network_of_post(post_doc)


async def _get_post(post_id: str) -> dict | None:
    if db_manager.use_mongo and db_manager.db is not None:
        return await db_manager.db["posts"].find_one({"id": post_id})
    return next(
        (row for row in db_manager._collections.get("posts", []) if row.get("id") == post_id),
        None,
    )


async def _approved_posts(
    author_ids: set[str],
    limit: int = 50,
    content_type: str | None = None,
    offset: int = 0,
) -> list[dict]:
    if not author_ids:
        return []
    query = {
        "moderation_status": "APPROVED",
        "author_id": {"$in": list(author_ids)},
    }
    if content_type:
        if content_type == "POST":
            query["$or"] = [{"content_type": "POST"}, {"content_type": {"$exists": False}}]
        else:
            query["content_type"] = content_type
    if db_manager.use_mongo and db_manager.db is not None:
        return await db_manager.db["posts"].find(query).sort([("created_at", -1), ("id", -1)]).skip(offset).limit(limit).to_list(length=limit)
    posts = [
        row for row in db_manager._collections.get("posts", [])
        if row.get("moderation_status") == "APPROVED"
        and row.get("author_id") in author_ids
        and (not content_type or row.get("content_type", "POST") == content_type)
    ]
    return sorted(posts, key=lambda row: (row.get("created_at", ""), row.get("id", "")), reverse=True)[offset:offset + limit]


async def _post_responses(posts: list[dict], current_user: dict | None) -> list[PostResponse]:
    post_ids = [post.get("id") for post in posts]
    if db_manager.use_mongo and db_manager.db is not None:
        likes = await db_manager.db["post_likes"].find({"post_id": {"$in": post_ids}}).to_list(length=None) if post_ids else []
        saved = await db_manager.db["saved_posts"].find({"user_id": current_user["id"], "post_id": {"$in": post_ids}}).to_list(length=None) if current_user and post_ids else []
    else:
        likes = [row for row in db_manager._collections["post_likes"] if row.get("post_id") in post_ids]
        saved = [row for row in db_manager._collections["saved_posts"] if current_user and row.get("user_id") == current_user["id"] and row.get("post_id") in post_ids]
    like_counts: dict[str, int] = {}
    liked_ids = set()
    for row in likes:
        like_counts[row["post_id"]] = like_counts.get(row["post_id"], 0) + 1
        if current_user and row.get("user_id") == current_user["id"]:
            liked_ids.add(row["post_id"])
    saved_ids = {row["post_id"] for row in saved}
    return [PostResponse(**{
        **post,
        "like_count": like_counts.get(post["id"], 0),
        "liked_by_me": post["id"] in liked_ids,
        "saved_by_me": post["id"] in saved_ids,
    }) for post in posts]

@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_in: PostCreate,
    current_user: dict = Depends(get_current_user)
):
    if not InputSanitizer.validate_length(post_in.content, max_length=2000):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Post content length must be between 1 and 2000 characters."
        )
    moderation = _moderate_text(post_in.content)
    post_doc = _build_post(current_user, moderation["content"], moderation)
    await _save_post(post_doc, current_user)
    return PostResponse(**post_doc)


@router.post("/media", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_media_post(
    request: Request,
    caption: str = Form(""),
    files: list[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=10, window_seconds=60)
    if not files or len(files) > 5:
        raise HTTPException(status_code=400, detail="Add between one and five media files.")
    if sum(Path(upload.filename or "").suffix.lower() in {".mp4", ".webm"} for upload in files) > 1:
        raise HTTPException(status_code=400, detail="A post can contain only one video.")
    if len(caption) > 2000:
        raise HTTPException(status_code=400, detail="Captions cannot exceed 2,000 characters.")

    media_items: list[dict] = []
    saved = False
    try:
        for upload in files:
            media_items.append(await store_upload(upload))
        moderation = _moderate_text(caption)
        post_doc = _build_post(
            current_user,
            moderation["content"],
            moderation,
            media=media_items,
        )
        await _save_post(post_doc, current_user)
        saved = True
        return PostResponse(**post_doc)
    finally:
        if not saved:
            delete_media_files(media_items)


@router.post("/events", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    request: Request,
    title: str = Form(..., min_length=1, max_length=140),
    description: str = Form(..., min_length=1, max_length=2000),
    event_date: date = Form(...),
    event_time: time = Form(...),
    location: str = Form(..., min_length=1, max_length=180),
    cover_image: UploadFile | None = File(None),
    current_user: dict = Depends(get_current_user),
):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=10, window_seconds=60)
    if not InputSanitizer.validate_length(description, max_length=2000):
        raise HTTPException(status_code=400, detail="Event descriptions must contain 1–2,000 characters.")
    if not InputSanitizer.validate_length(location, max_length=180):
        raise HTTPException(status_code=400, detail="Enter an event location of up to 180 characters.")

    safe_title = InputSanitizer.sanitize_text(title)
    safe_description = InputSanitizer.sanitize_text(description)
    media_items: list[dict] = []
    saved = False
    try:
        if cover_image and cover_image.filename:
            media_items.append(await store_upload(cover_image, expected_type="image"))
        moderation = _moderate_text(f"{safe_title}\n{safe_description}")
        post_doc = _build_post(
            current_user,
            safe_description,
            moderation,
            content_type="EVENT",
            media=media_items,
            event={
                "title": safe_title,
                "event_date": event_date.isoformat(),
                "event_time": event_time.strftime("%H:%M"),
                "location": InputSanitizer.sanitize_text(location),
            },
        )
        await _save_post(post_doc, current_user)
        saved = True
        return PostResponse(**post_doc)
    finally:
        if not saved:
            delete_media_files(media_items)


@router.post("/articles", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_article(
    request: Request,
    title: str = Form(..., min_length=1, max_length=180),
    content: str = Form(..., min_length=1, max_length=20000),
    cover_image: UploadFile | None = File(None),
    current_user: dict = Depends(get_current_user),
):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=10, window_seconds=60)
    if not InputSanitizer.validate_length(content, max_length=20000):
        raise HTTPException(status_code=400, detail="Article text must contain 1–20,000 characters.")

    safe_title = InputSanitizer.sanitize_text(title)
    safe_content = InputSanitizer.sanitize_text(content)
    media_items: list[dict] = []
    saved = False
    try:
        if cover_image and cover_image.filename:
            media_items.append(await store_upload(cover_image, expected_type="image"))
        moderation = _moderate_text(f"{safe_title}\n{safe_content}", classify_all_text=True)
        post_doc = _build_post(
            current_user,
            safe_content,
            moderation,
            content_type="ARTICLE",
            media=media_items,
            article={"title": safe_title},
        )
        await _save_post(post_doc, current_user)
        saved = True
        return PostResponse(**post_doc)
    finally:
        if not saved:
            delete_media_files(media_items)


@router.get("/media/{filename}")
async def get_post_media(
    filename: str,
    current_user: dict | None = Depends(get_optional_current_user),
):
    path = media_path(filename)
    if path is None:
        raise HTTPException(status_code=404, detail="Media not found.")
    if db_manager.use_mongo and db_manager.db is not None:
        post = await db_manager.db["posts"].find_one({"media.filename": filename})
    else:
        post = next(
            (row for row in db_manager._collections.get("posts", [])
             if any(item.get("filename") == filename for item in row.get("media", []))),
            None,
        )
    if not post:
        raise HTTPException(status_code=404, detail="Media not found.")
    viewer_id = current_user.get("id") if current_user else None
    if post.get("moderation_status") != "APPROVED" and viewer_id != post.get("author_id"):
        raise HTTPException(status_code=404, detail="Media not found.")
    if not await can_view_post(post, viewer_id):
        raise HTTPException(status_code=404, detail="Media not found.")
    media_item = next(item for item in post.get("media", []) if item.get("filename") == filename)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Media not found.")
    return FileResponse(
        path,
        media_type=media_item["mime_type"],
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
        },
    )


@router.put("/{post_id}/article", response_model=PostResponse)
async def update_article(
    post_id: str,
    request: Request,
    title: str = Form(..., min_length=1, max_length=180),
    content: str = Form(..., min_length=1, max_length=20000),
    cover_image: UploadFile | None = File(None),
    current_user: dict = Depends(get_current_user),
):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=10, window_seconds=60)
    post = await _get_post(post_id)
    if not post or post.get("content_type", "POST") != "ARTICLE":
        raise HTTPException(status_code=404, detail="Article not found.")
    if post.get("author_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="You can only edit your own articles.")
    if not InputSanitizer.validate_length(content, max_length=20000):
        raise HTTPException(status_code=400, detail="Article text must contain 1–20,000 characters.")

    safe_title = InputSanitizer.sanitize_text(title)
    safe_content = InputSanitizer.sanitize_text(content)
    new_media: list[dict] = []
    saved = False
    previous_media = list(post.get("media", []))
    try:
        if cover_image and cover_image.filename:
            new_media.append(await store_upload(cover_image, expected_type="image"))
        moderation = _moderate_text(f"{safe_title}\n{safe_content}", classify_all_text=True)
        media_items = new_media if new_media else previous_media
        updates = {
            "content": safe_content,
            "article": {"title": safe_title},
            "media": media_items,
            "language": moderation["language"],
            "language_supported": moderation["language_supported"],
            "language_notice": moderation["language_notice"],
            "moderation_recommendation": moderation["moderation_recommendation"],
            "moderation_status": moderation["moderation_status"],
            "moderation_explanation": moderation["moderation_explanation"],
            "ai_prediction": moderation["ai_prediction"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        post.update(updates)
        if db_manager.use_mongo and db_manager.db is not None:
            await db_manager.db["posts"].update_one({"id": post_id, "author_id": current_user["id"]}, {"$set": updates})
            if moderation["ai_prediction"]:
                await db_manager.db["moderation_logs"].update_one(
                    {"content_id": post_id},
                    {"$set": {
                        "post_id": post_id,
                        "content_id": post_id,
                        "content_type": "post",
                        "detected_language": moderation["language"],
                        "ai_label": moderation["ai_prediction"]["predicted_class"],
                        "confidence": moderation["ai_prediction"]["confidence"],
                        "recommendation": moderation["moderation_recommendation"],
                        "action_taken": moderation["moderation_status"],
                        "timestamp": updates["updated_at"],
                    }},
                    upsert=True,
                )
        else:
            for row in db_manager._collections.get("moderation_logs", []):
                if row.get("content_id") == post_id:
                    row.update({
                        "ai_label": moderation["ai_prediction"]["predicted_class"],
                        "confidence": moderation["ai_prediction"]["confidence"],
                        "recommendation": moderation["moderation_recommendation"],
                        "action_taken": moderation["moderation_status"],
                        "timestamp": updates["updated_at"],
                    })
                    break
        saved = True
    finally:
        if not saved:
            delete_media_files(new_media)

    if new_media:
        delete_media_files(previous_media)
    await audit_logger.log_event(
        actor_id=current_user["id"],
        actor_role=current_user["role"],
        event_type="ARTICLE_UPDATED",
        resource_id=post_id,
        details="Article updated and its text was resubmitted for moderation.",
    )
    if post["moderation_status"] != "APPROVED":
        await create_notification(
            recipient_id=current_user["id"],
            kind="MODERATION_RESULT",
            resource_type="post",
            resource_id=post_id,
            section="articles",
        )
    return (await _post_responses([post], current_user))[0]


@router.delete("/{post_id}/media/{filename}")
async def delete_post_media(
    post_id: str,
    filename: str,
    current_user: dict = Depends(get_current_user),
):
    post = await _get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")
    if post.get("author_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="You can only remove media from your own posts.")
    media_items = list(post.get("media", []))
    updated_media = [item for item in media_items if item.get("filename") != filename]
    if len(updated_media) == len(media_items):
        raise HTTPException(status_code=404, detail="Media not found.")
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["posts"].update_one(
            {"id": post_id, "author_id": current_user["id"]},
            {"$set": {"media": updated_media}},
        )
    else:
        post["media"] = updated_media
    removed = [item for item in media_items if item.get("filename") == filename]
    delete_media_files(removed)
    return {"status": "DELETED"}


@router.put("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: str,
    request: Request,
    caption: str = Form(""),
    files: list[UploadFile] | None = File(None),
    remove_media: list[str] | None = Form(None),
    current_user: dict = Depends(get_current_user),
):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_check(client_ip, max_requests=10, window_seconds=60)
    if len(caption) > 2000:
        raise HTTPException(status_code=400, detail="Captions cannot exceed 2,000 characters.")
    post = await _get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")
    if post.get("author_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="You can only edit your own posts.")
    if post.get("content_type", "POST") != "POST":
        raise HTTPException(status_code=400, detail="Only posts can be edited here.")

    previous_media = list(post.get("media", []))
    remove_names = set(remove_media or [])
    existing_names = {item.get("filename") for item in previous_media}
    if not remove_names.issubset(existing_names):
        raise HTTPException(status_code=404, detail="One or more media files were not found.")
    retained_media = [item for item in previous_media if item.get("filename") not in remove_names]
    removed_media = [item for item in previous_media if item.get("filename") in remove_names]
    uploads = files or []
    new_video_count = sum(Path(upload.filename or "").suffix.lower() in {".mp4", ".webm"} for upload in uploads)
    retained_video_count = sum(item.get("media_type") == "video" for item in retained_media)
    retained_image_count = sum(item.get("media_type") == "image" for item in retained_media)
    if len(retained_media) + len(uploads) > 5:
        raise HTTPException(status_code=400, detail="A post can contain no more than five media files.")
    if retained_video_count + new_video_count > 1:
        raise HTTPException(status_code=400, detail="A post can contain only one video.")
    if retained_image_count + len(uploads) - new_video_count > 4:
        raise HTTPException(status_code=400, detail="A post can contain up to four images.")
    if not caption.strip() and not retained_media and not uploads:
        raise HTTPException(status_code=400, detail="A post must include text or media.")

    new_media: list[dict] = []
    saved = False
    try:
        for upload in uploads:
            new_media.append(await store_upload(upload))
        media_items = retained_media + new_media
        moderation = _moderate_text(caption)
        now = datetime.now(timezone.utc).isoformat()
        updates = {
            "content": moderation["content"],
            "media": media_items,
            "language": moderation["language"],
            "language_supported": moderation["language_supported"],
            "language_notice": moderation["language_notice"],
            "moderation_recommendation": moderation["moderation_recommendation"],
            "moderation_status": moderation["moderation_status"],
            "moderation_explanation": moderation["moderation_explanation"],
            "ai_prediction": moderation["ai_prediction"],
            "updated_at": now,
            "edited_at": now,
            "is_edited": True,
        }
        if db_manager.use_mongo and db_manager.db is not None:
            result = await db_manager.db["posts"].update_one(
                {"id": post_id, "author_id": current_user["id"], "content_type": {"$in": ["POST", None]}},
                {"$set": updates},
            )
            if not result.matched_count:
                raise HTTPException(status_code=404, detail="Post not found.")
            post.update(updates)
            saved = True
            if moderation["ai_prediction"]:
                await db_manager.db["moderation_logs"].update_one(
                    {"content_id": post_id},
                    {"$set": {
                        "post_id": post_id,
                        "content_id": post_id,
                        "content_type": "post",
                        "detected_language": moderation["language"],
                        "ai_label": moderation["ai_prediction"]["predicted_class"],
                        "confidence": moderation["ai_prediction"]["confidence"],
                        "recommendation": moderation["moderation_recommendation"],
                        "action_taken": moderation["moderation_status"],
                        "timestamp": now,
                    }},
                    upsert=True,
                )
            else:
                await db_manager.db["moderation_logs"].delete_one({"content_id": post_id})
        else:
            post.update(updates)
            saved = True
            moderation_logs = db_manager._collections.get("moderation_logs", [])
            existing_log = next((row for row in moderation_logs if row.get("content_id") == post_id), None)
            if moderation["ai_prediction"]:
                log_updates = {
                    "post_id": post_id,
                    "content_id": post_id,
                    "content_type": "post",
                    "detected_language": moderation["language"],
                    "ai_label": moderation["ai_prediction"]["predicted_class"],
                    "confidence": moderation["ai_prediction"]["confidence"],
                    "recommendation": moderation["moderation_recommendation"],
                    "action_taken": moderation["moderation_status"],
                    "timestamp": now,
                }
                if existing_log:
                    existing_log.update(log_updates)
                else:
                    moderation_logs.append(log_updates)
            elif existing_log:
                db_manager._collections["moderation_logs"] = [
                    row for row in moderation_logs if row.get("content_id") != post_id
                ]
    finally:
        if not saved:
            delete_media_files(new_media)

    delete_media_files(removed_media)
    await audit_logger.log_event(
        actor_id=current_user["id"],
        actor_role=current_user["role"],
        event_type="POST_UPDATED",
        resource_id=post_id,
        details="Post text was resubmitted for moderation and the post was updated.",
    )
    if post["moderation_status"] != "APPROVED":
        await create_notification(
            recipient_id=current_user["id"],
            kind="MODERATION_RESULT",
            resource_type="post",
            resource_id=post_id,
        )
    return (await _post_responses([post], current_user))[0]


@router.delete("/{post_id}")
async def delete_post(
    post_id: str,
    current_user: dict = Depends(get_current_user),
):
    post = await _get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")
    if post.get("author_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="You can only delete your own posts.")

    if db_manager.use_mongo and db_manager.db is not None:
        comment_rows = await db_manager.db["comments"].find({"post_id": post_id}, {"id": 1}).to_list(length=None)
        comment_ids = [row["id"] for row in comment_rows]
        if comment_ids:
            await db_manager.db["comment_likes"].delete_many({"comment_id": {"$in": comment_ids}})
            await db_manager.db["moderation_logs"].delete_many({"content_id": {"$in": comment_ids}})
        await db_manager.db["comments"].delete_many({"post_id": post_id})
        await db_manager.db["post_likes"].delete_many({"post_id": post_id})
        await db_manager.db["saved_posts"].delete_many({"post_id": post_id})
        await db_manager.db["notifications"].delete_many({"resource_id": {"$in": [post_id, *comment_ids]}})
        await db_manager.db["moderation_logs"].delete_many({"content_id": post_id})
        await db_manager.db["posts"].delete_one({"id": post_id, "author_id": current_user["id"]})
    else:
        comment_ids = [
            row["id"] for row in db_manager._collections.get("comments", [])
            if row.get("post_id") == post_id
        ]
        for collection, key in (
            ("comments", "post_id"),
            ("post_likes", "post_id"),
            ("saved_posts", "post_id"),
        ):
            db_manager._collections[collection] = [
                row for row in db_manager._collections.get(collection, [])
                if row.get(key) != post_id
            ]
        db_manager._collections["comment_likes"] = [
            row for row in db_manager._collections.get("comment_likes", [])
            if row.get("comment_id") not in comment_ids
        ]
        db_manager._collections["moderation_logs"] = [
            row for row in db_manager._collections.get("moderation_logs", [])
            if row.get("content_id") not in {post_id, *comment_ids}
        ]
        db_manager._collections["notifications"] = [
            row for row in db_manager._collections.get("notifications", [])
            if row.get("resource_id") not in {post_id, *comment_ids}
        ]
        db_manager._collections["posts"] = [
            row for row in db_manager._collections.get("posts", [])
            if row.get("id") != post_id
        ]

    delete_media_files(post.get("media", []))
    await audit_logger.log_event(
        actor_id=current_user["id"],
        actor_role=current_user["role"],
        event_type=f"{post.get('content_type', 'POST')}_DELETED",
        resource_id=post_id,
        details=f"{post.get('content_type', 'POST').title()} and attached media deleted by owner.",
    )
    return {"status": "DELETED"}


@router.get("", response_model=List[PostResponse])
async def list_posts(
    status_filter: Optional[str] = Query(None, description="Public feed supports approved content only"),
    content_type: Optional[str] = Query(None, pattern="^(POST|EVENT|ARTICLE)$"),
    current_user: dict | None = Depends(get_optional_current_user),
):
    """Retrieve approved posts visible to this viewer."""
    if status_filter and status_filter != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only approved content is available in the public feed.",
        )
    author_ids = await visible_author_ids(current_user.get("id") if current_user else None)
    posts = await _approved_posts(author_ids, content_type=content_type)
    return await _post_responses(posts, current_user)


@router.get("/explore", response_model=List[PostResponse])
async def explore_posts(
    offset: int = Query(0, ge=0),
    limit: int = Query(24, ge=1, le=50),
    current_user: dict | None = Depends(get_optional_current_user),
):
    """Explore only approved posts from public accounts."""
    author_ids = await visible_author_ids(public_only=True)
    posts = await _approved_posts(author_ids, limit=limit, offset=offset)
    return await _post_responses(posts, current_user)

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
    visible_ids = await visible_author_ids(current_user["id"])
    if db_manager.use_mongo and db_manager.db is not None:
        saved_rows = await db_manager.db["saved_posts"].find({"user_id": current_user["id"]}).sort("created_at", -1).limit(100).to_list(length=100)
        post_ids = [row["post_id"] for row in saved_rows]
        posts = await db_manager.db["posts"].find({"id": {"$in": post_ids}, "author_id": {"$in": list(visible_ids)}, "moderation_status": "APPROVED"}).to_list(length=100) if post_ids and visible_ids else []
        likes = await db_manager.db["post_likes"].find({"post_id": {"$in": post_ids}}).to_list(length=None) if post_ids else []
    else:
        saved_rows = sorted(
            (row for row in db_manager._collections["saved_posts"] if row.get("user_id") == current_user["id"]),
            key=lambda row: row.get("created_at", ""), reverse=True,
        )[:100]
        post_ids = [row["post_id"] for row in saved_rows]
        posts = [row for row in db_manager._collections["posts"] if row.get("id") in post_ids and row.get("author_id") in visible_ids and row.get("moderation_status") == "APPROVED"]
        likes = [row for row in db_manager._collections["post_likes"] if row.get("post_id") in post_ids]
    posts.sort(key=lambda row: post_ids.index(row["id"]) if row["id"] in post_ids else len(post_ids))
    like_counts = {}
    liked_ids = set()
    for row in likes:
        like_counts[row["post_id"]] = like_counts.get(row["post_id"], 0) + 1
        if row.get("user_id") == current_user["id"]:
            liked_ids.add(row["post_id"])
    return [PostResponse(**{**p, "like_count": like_counts.get(p["id"], 0), "liked_by_me": p["id"] in liked_ids, "saved_by_me": True}) for p in posts]


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: str,
    current_user: dict | None = Depends(get_optional_current_user),
):
    post = await _get_post(post_id)
    if (
        not post
        or post.get("moderation_status") != "APPROVED"
        or not await can_view_post(post, current_user.get("id") if current_user else None)
    ):
        raise HTTPException(status_code=404, detail="Approved post not found.")
    return (await _post_responses([post], current_user))[0]


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
    if not await can_view_post(post, current_user["id"]):
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
            section=content_notification_section(post.get("content_type")),
        )
    return {"liked": True, "like_count": like_count}


@router.delete("/{post_id}/like")
async def unlike_post(post_id: str, current_user: dict = Depends(get_current_user)):
    if db_manager.use_mongo and db_manager.db is not None:
        post = await db_manager.db["posts"].find_one({"id": post_id, "moderation_status": "APPROVED"})
    else:
        post = next((row for row in db_manager._collections["posts"] if row.get("id") == post_id and row.get("moderation_status") == "APPROVED"), None)
    if not post or not await can_view_post(post, current_user["id"]):
        raise HTTPException(status_code=404, detail="Approved post not found.")
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
    if not await can_view_post(post, current_user["id"]):
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
