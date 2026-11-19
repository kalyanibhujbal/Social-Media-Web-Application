import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bson import BSON

from app.api.v1.endpoints.comments import create_comment
from app.api.v1.endpoints.posts import create_post
from app.core.database import db_manager
from app.schemas.comment import CommentCreate
from app.schemas.post import PostCreate


class MockCollection:
    def __init__(self, find_one_result=None):
        self.find_one = AsyncMock(return_value=find_one_result)
        self.insert_one = AsyncMock()


class TestMongoContentSerialization(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.prediction = {
            "label": "Hate Speech",
            "predicted_class": "Hate Speech",
            "confidence": 0.8,
            "confidence_level": "HIGH",
            "probabilities": {"Hate Speech": 0.8, "Offensive": 0.1, "Normal": 0.1},
            "is_low_confidence": False,
            "model_name": "test-model",
            "model_version": "1.0",
            "inference_timestamp": "2026-01-01T00:00:00+00:00",
        }
        self.xai_result = {
            "method": "Keyword Rule Highlights",
            "top_words": [{"word": "kill", "matched_rule": "Hate Speech keyword"}],
        }
        self.moderation_result = {
            "final_status": "FLAGGED_FOR_REVIEW",
            "recommendation": "Manual Review",
            "user_explanation": "Your content was submitted for review.",
        }
        self.user = {"id": "user-1", "username": "member", "role": "USER"}
        self.lang_info = {"code": "en", "is_supported": True, "notice": None}

    async def test_post_explanation_is_bson_serializable(self):
        posts = MockCollection()
        logs = MockCollection()
        database = {"posts": posts, "moderation_logs": logs}

        with (
            patch.object(db_manager, "use_mongo", True),
            patch.object(db_manager, "db", database),
            patch("app.api.v1.endpoints.posts.LanguageDetector.detect_language", return_value=self.lang_info),
            patch("app.api.v1.endpoints.posts.inference_service.predict", return_value=self.prediction),
            patch("app.api.v1.endpoints.posts.xai_engine.explain", return_value=self.xai_result),
            patch("app.api.v1.endpoints.posts.moderation_engine.process_moderation", return_value=self.moderation_result),
            patch("app.api.v1.endpoints.posts.audit_logger.log_event", new_callable=AsyncMock),
            patch("app.api.v1.endpoints.posts.create_notification", new_callable=AsyncMock),
        ):
            result = await create_post(PostCreate(content="kill"), self.user)

        saved_post = posts.insert_one.await_args.args[0]
        BSON.encode(saved_post)
        self.assertEqual(result.ai_prediction.explanation.top_words[0].word, "kill")

    async def test_comment_explanation_is_bson_serializable(self):
        posts = MockCollection(find_one_result={
            "id": "post-1",
            "author_id": "author-1",
            "moderation_status": "APPROVED",
        })
        comments = MockCollection()
        logs = MockCollection()
        database = {"posts": posts, "comments": comments, "moderation_logs": logs}
        request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))

        with (
            patch.object(db_manager, "use_mongo", True),
            patch.object(db_manager, "db", database),
            patch("app.api.v1.endpoints.comments.rate_limit_check"),
            patch("app.api.v1.endpoints.comments.LanguageDetector.detect_language", return_value=self.lang_info),
            patch("app.api.v1.endpoints.comments.inference_service.predict", return_value=self.prediction),
            patch("app.api.v1.endpoints.comments.xai_engine.explain", return_value=self.xai_result),
            patch("app.api.v1.endpoints.comments.moderation_engine.process_moderation", return_value=self.moderation_result),
            patch("app.api.v1.endpoints.comments.audit_logger.log_event", new_callable=AsyncMock),
            patch("app.api.v1.endpoints.comments.create_notification", new_callable=AsyncMock),
        ):
            result = await create_comment(
                CommentCreate(post_id="post-1", content="kill"),
                request,
                self.user,
            )

        saved_comment = comments.insert_one.await_args.args[0]
        BSON.encode(saved_comment)
        self.assertEqual(result.ai_prediction.explanation.top_words[0].word, "kill")


if __name__ == "__main__":
    unittest.main()
