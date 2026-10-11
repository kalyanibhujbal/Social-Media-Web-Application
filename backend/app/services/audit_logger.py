import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.core.database import db_manager

class AuditLogger:
    """Append-only audit event logger; retention cleanup may anonymize or purge rows."""

    @staticmethod
    async def log_event(
        actor_id: str,
        actor_role: str,
        event_type: str,
        details: str,
        resource_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        entry = {
            "id": str(uuid.uuid4()),
            "actor_id": actor_id,
            "actor_role": actor_role,
            "event_type": event_type,
            "resource_id": resource_id,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if db_manager.use_mongo and db_manager.db is not None:
            await db_manager.db["audit_logs"].insert_one(entry)
        else:
            db_manager._collections["audit_logs"].append(entry)

        return entry

audit_logger = AuditLogger()
