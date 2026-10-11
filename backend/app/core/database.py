import logging
from typing import Optional, Dict, Any, List
from app.core.config import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    """In-memory & MongoDB database abstraction manager."""
    def __init__(self):
        self.use_mongo = False
        self.client = None
        self.db = None
        # Fallback in-memory collections
        self._collections: Dict[str, List[Dict[str, Any]]] = {
            "users": [],
            "posts": [],
            "comments": [],
            "moderation_logs": [],
            "audit_logs": [],
            "consent_records": [],
            "privacy_requests": [],
            "connections": [],
            "follows": [],
            "notifications": [],
            "conversations": [],
            "messages": [],
            "post_likes": [],
            "comment_likes": [],
            "saved_posts": [],
        }

    async def connect(self):
        try:
            import motor.motor_asyncio
            self.client = motor.motor_asyncio.AsyncIOMotorClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=2000
            )
            # Test connection
            await self.client.admin.command('ping')
            self.db = self.client[settings.MONGODB_DB_NAME]
            await self.db["users"].create_index("email", unique=True, name="unique_user_email")
            await self.db["users"].create_index("username", unique=True, name="unique_user_username")
            await self.db["posts"].create_index([("author_id", 1), ("created_at", -1)], name="posts_by_author_date")
            await self.db["comments"].create_index([("author_id", 1), ("created_at", -1)], name="comments_by_author_date")
            await self.db["moderation_logs"].create_index("content_id", unique=True, sparse=True, name="unique_moderation_content")
            await self.db["audit_logs"].create_index("timestamp", name="audit_timestamp")
            await self.db["consent_records"].create_index([("user_id", 1), ("consent_type", 1)], unique=True, name="consent_by_user_type")
            await self.db["privacy_requests"].create_index([("user_id", 1), ("created_at", -1)], name="privacy_requests_by_user_date")
            await self.db["connections"].create_index("pair_key", unique=True, name="unique_connection_pair")
            await self.db["connections"].create_index([("recipient_id", 1), ("status", 1), ("created_at", -1)], name="connection_inbox")
            await self.db["follows"].create_index([("follower_id", 1), ("following_id", 1)], unique=True, name="unique_follow_pair")
            await self.db["notifications"].create_index([("recipient_id", 1), ("created_at", -1)], name="notifications_by_recipient_date")
            await self.db["notifications"].create_index([("recipient_id", 1), ("is_read", 1)], name="notifications_by_read_state")
            await self.db["conversations"].create_index("pair_key", unique=True, name="unique_direct_conversation")
            await self.db["messages"].create_index([("conversation_id", 1), ("created_at", 1)], name="messages_by_conversation_date")
            await self.db["post_likes"].create_index([("post_id", 1), ("user_id", 1)], unique=True, name="unique_post_like")
            await self.db["comment_likes"].create_index([("comment_id", 1), ("user_id", 1)], unique=True, name="unique_comment_like")
            await self.db["saved_posts"].create_index([("post_id", 1), ("user_id", 1)], unique=True, name="unique_saved_post")
            self.use_mongo = True
            logger.info("Connected successfully to MongoDB instance.")
        except Exception:
            if settings.ENVIRONMENT.lower() == "production":
                logger.error("MongoDB connection failed in production; refusing ephemeral storage.")
                raise RuntimeError("MongoDB is required in production; refusing to use ephemeral storage.") from None
            logger.warning("MongoDB unavailable; using development in-memory storage.")
            self.use_mongo = False

    async def disconnect(self):
        if self.use_mongo and self.client:
            self.client.close()

db_manager = DatabaseManager()
