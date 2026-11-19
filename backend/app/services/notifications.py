import uuid
from datetime import datetime, timezone
from typing import Optional

from app.core.database import db_manager


NOTIFICATION_SECTIONS = {
    "home": {"NETWORK_POST", "POST_LIKE", "COMMENT", "COMMENT_LIKE", "MODERATION_RESULT"},
    "network": {
        "CONNECTION_REQUEST",
        "CONNECTION_ACCEPTED",
        "CONNECTION_REJECTED",
        "FOLLOW_REQUEST",
        "FOLLOW_ACCEPTED",
        "FOLLOW_REJECTED",
        "FOLLOW",
    },
    "messages": {"MESSAGE"},
    "explore": {"DISCOVERY_POST"},
    "events": {"NETWORK_EVENT", "EVENT_INVITATION", "EVENT_REMINDER"},
    "articles": {"NETWORK_ARTICLE"},
}


def notification_section(kind: str) -> str:
    return next(
        (section for section, kinds in NOTIFICATION_SECTIONS.items() if kind in kinds),
        "notifications",
    )


def notification_kinds_for_section(section: str) -> set[str]:
    return NOTIFICATION_SECTIONS.get(section, set())


def content_notification_section(content_type: str | None) -> str:
    return {
        "POST": "home",
        "EVENT": "events",
        "ARTICLE": "articles",
    }.get((content_type or "POST").upper(), "home")


async def create_notification(
    recipient_id: str,
    kind: str,
    actor_id: Optional[str] = None,
    actor_username: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    deduplicate: bool = False,
    section: Optional[str] = None,
) -> Optional[dict]:
    """Store a minimal notification without copying private content into it."""
    if not recipient_id or recipient_id == actor_id:
        return None
    row = {
        "id": str(uuid.uuid4()),
        "recipient_id": recipient_id,
        "kind": kind,
        "section": section or notification_section(kind),
        "actor_id": actor_id,
        "actor_username": actor_username,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if db_manager.use_mongo and db_manager.db is not None:
        if deduplicate:
            result = await db_manager.db["notifications"].update_one(
                {"recipient_id": recipient_id, "kind": kind, "resource_id": resource_id},
                {"$setOnInsert": row},
                upsert=True,
            )
            return row if result.upserted_id is not None else None
        await db_manager.db["notifications"].insert_one(row)
    else:
        if deduplicate and any(
            item.get("recipient_id") == recipient_id
            and item.get("kind") == kind
            and item.get("resource_id") == resource_id
            for item in db_manager._collections["notifications"]
        ):
            return None
        db_manager._collections["notifications"].append(row)
    return row
