from datetime import datetime, timezone
from typing import Optional, Dict, Any

from app.core.database import db_manager


async def update_human_review(
    post_id: str,
    reviewer_id: str,
    reviewer_role: str,
    review_action: str,
    content_type: str = "post",
    final_status: Optional[str] = None,
) -> None:
    """Record a human review without placing notes in the audit stream."""
    human_review = {
        "reviewed_by": reviewer_id,
        "reviewer_role": reviewer_role,
        "review_action": review_action,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }

    if content_type == "post":
        query = {"$or": [{"post_id": post_id}, {"content_id": post_id, "content_type": "post"}]}
    else:
        query = {"content_id": post_id, "content_type": content_type}

    if db_manager.use_mongo and db_manager.db is not None:
        update_fields = {"human_review": human_review}
        if final_status:
            update_fields["action_taken"] = final_status
        await db_manager.db["moderation_logs"].update_one(
            query,
            {"$set": update_fields},
        )
    else:
        for log in db_manager._collections.get("moderation_logs", []):
            matches = (
                log.get("post_id") == post_id
                if content_type == "post"
                else log.get("content_id") == post_id and log.get("content_type") == content_type
            )
            if matches:
                log["human_review"] = human_review
                if final_status:
                    log["action_taken"] = final_status
                break
