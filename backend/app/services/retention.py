import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.database import db_manager

logger = logging.getLogger(__name__)


async def purge_expired_records(now: datetime | None = None) -> None:
    """Purge time-limited audit and resolved privacy request records."""
    current = now or datetime.now(timezone.utc)
    audit_cutoff = (current - timedelta(days=settings.AUDIT_RETENTION_DAYS)).isoformat()
    request_cutoff = (
        current - timedelta(days=settings.RESOLVED_PRIVACY_REQUEST_RETENTION_DAYS)
    ).isoformat()

    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["audit_logs"].delete_many({"timestamp": {"$lt": audit_cutoff}})
        await db_manager.db["privacy_requests"].delete_many({
            "status": {"$in": ["RESOLVED", "DECLINED"]},
            "resolved_at": {"$lt": request_cutoff},
        })
        await db_manager.db["moderation_logs"].update_many(
            {"human_review.review_notes": {"$exists": True}},
            {"$unset": {"human_review.review_notes": ""}},
        )
    else:
        db_manager._collections["audit_logs"] = [
            row for row in db_manager._collections["audit_logs"]
            if row.get("timestamp", "") >= audit_cutoff
        ]
        db_manager._collections["privacy_requests"] = [
            row for row in db_manager._collections["privacy_requests"]
            if row.get("status") not in {"RESOLVED", "DECLINED"}
            or row.get("resolved_at", "") >= request_cutoff
        ]
        for row in db_manager._collections.get("moderation_logs", []):
            (row.get("human_review") or {}).pop("review_notes", None)


async def run_retention_loop() -> None:
    """Run an initial cleanup and repeat daily while the API is running."""
    while True:
        try:
            await purge_expired_records()
        except Exception as exc:
            # Do not log record contents, connection strings, or exception text.
            logger.error("Retention cleanup failed (%s).", type(exc).__name__)
        await asyncio.sleep(24 * 60 * 60)
