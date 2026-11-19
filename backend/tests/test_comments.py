import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.api.v1.endpoints.comments import create_comment
from app.core.database import db_manager
from app.schemas.comment import CommentCreate


class TestCreateComment(unittest.IsolatedAsyncioTestCase):
    async def test_comment_creation_uses_supported_preprocessing_pipeline(self):
        prediction = {
            "label": "Normal",
            "predicted_class": "Normal",
            "confidence": 0.95,
            "confidence_level": "HIGH",
            "probabilities": {"Hate Speech": 0.01, "Offensive": 0.04, "Normal": 0.95},
            "is_low_confidence": False,
            "model_name": "test-model",
            "model_version": "1.0",
            "inference_timestamp": "2026-01-01T00:00:00+00:00",
        }
        collections = {
            "users": [{"id": "another-user", "is_active": True}],
            "posts": [{"id": "post-1", "author_id": "another-user", "moderation_status": "APPROVED"}],
            "comments": [],
            "moderation_logs": [],
        }

        with (
            patch.object(db_manager, "use_mongo", False),
            patch.dict(db_manager._collections, collections),
            patch("app.api.v1.endpoints.comments.rate_limit_check"),
            patch("app.api.v1.endpoints.comments.inference_service.predict", return_value=prediction) as predict,
            patch(
                "app.api.v1.endpoints.comments.xai_engine.explain",
                return_value={"method": "Keyword Rule Highlights", "top_words": []},
            ),
            patch(
                "app.api.v1.endpoints.comments.moderation_engine.process_moderation",
                return_value={
                    "final_status": "APPROVED",
                    "recommendation": "Publish",
                    "user_explanation": "Your comment has been published.",
                },
            ),
            patch("app.api.v1.endpoints.comments.audit_logger.log_event", new_callable=AsyncMock),
            patch("app.api.v1.endpoints.comments.create_notification", new_callable=AsyncMock),
        ):
            result = await create_comment(
                CommentCreate(post_id="post-1", content="A thoughtful comment"),
                SimpleNamespace(client=SimpleNamespace(host="127.0.0.1")),
                {"id": "commenter", "username": "commenter", "role": "USER"},
            )

        self.assertEqual(predict.call_args.args[0], "A thoughtful comment")
        self.assertEqual(result.content, "A thoughtful comment")
        self.assertEqual(result.moderation_status, "APPROVED")

    async def test_reply_creation_persists_parent_comment_id(self):
        prediction = {
            "label": "Normal",
            "predicted_class": "Normal",
            "confidence": 0.95,
            "confidence_level": "HIGH",
            "probabilities": {"Hate Speech": 0.01, "Offensive": 0.04, "Normal": 0.95},
            "is_low_confidence": False,
            "model_name": "test-model",
            "model_version": "1.0",
            "inference_timestamp": "2026-01-01T00:00:00+00:00",
        }
        parent = {
            "id": "parent-comment",
            "post_id": "post-1",
            "author_id": "post-author",
            "moderation_status": "APPROVED",
        }
        collections = {
            "users": [{"id": "post-author", "is_active": True}],
            "posts": [{"id": "post-1", "author_id": "post-author", "moderation_status": "APPROVED"}],
            "comments": [parent],
            "moderation_logs": [],
        }

        with (
            patch.object(db_manager, "use_mongo", False),
            patch.dict(db_manager._collections, collections),
            patch("app.api.v1.endpoints.comments.rate_limit_check"),
            patch("app.api.v1.endpoints.comments.inference_service.predict", return_value=prediction),
            patch(
                "app.api.v1.endpoints.comments.xai_engine.explain",
                return_value={"method": "Keyword Rule Highlights", "top_words": []},
            ),
            patch(
                "app.api.v1.endpoints.comments.moderation_engine.process_moderation",
                return_value={
                    "final_status": "APPROVED",
                    "recommendation": "Publish",
                    "user_explanation": "Your comment has been published.",
                },
            ),
            patch("app.api.v1.endpoints.comments.audit_logger.log_event", new_callable=AsyncMock),
            patch("app.api.v1.endpoints.comments.create_notification", new_callable=AsyncMock),
        ):
            result = await create_comment(
                CommentCreate(post_id="post-1", content="A thoughtful reply", parent_comment_id=parent["id"]),
                SimpleNamespace(client=SimpleNamespace(host="127.0.0.1")),
                {"id": "reply-author", "username": "reply-author", "role": "USER"},
            )
            stored_reply = next(row for row in db_manager._collections["comments"] if row.get("content") == "A thoughtful reply")
            self.assertEqual(stored_reply["parent_comment_id"], parent["id"])

        self.assertEqual(result.parent_comment_id, parent["id"])


if __name__ == "__main__":
    unittest.main()
