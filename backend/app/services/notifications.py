import uuid
from datetime import datetime, timezone
from typing import Optional

from app.core.database import db_manager


async def create_notification(
    recipient_id: str,
    kind: str,
    actor_id: Optional[str] = None,
    actor_username: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
) -> Optional[dict]:
    """Store a minimal notification without copying private content into it."""
    if not recipient_id or recipient_id == actor_id:
        return None
    row = {
        "id": str(uuid.uuid4()),
        "recipient_id": recipient_id,
        "kind": kind,
        "actor_id": actor_id,
        "actor_username": actor_username,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if db_manager.use_mongo and db_manager.db is not None:
        await db_manager.db["notifications"].insert_one(row)
    else:
        db_manager._collections["notifications"].append(row)
    return row
