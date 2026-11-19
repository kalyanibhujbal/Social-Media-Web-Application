import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import db_manager
from app.core.security import create_access_token
from app.middleware.rate_limit import _request_history
from main import app


client = TestClient(app)
JPEG = b"\xff\xd8\xff" + b"\x00" * 24
MP4 = b"\x00\x00\x00\x18ftypisom" + b"\x00" * 24
WEBM = b"\x1a\x45\xdf\xa3" + b"\x00" * 24


def _prediction():
    return {
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


class TestRichContentFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_use_mongo = db_manager.use_mongo
        cls.original_db = db_manager.db
        cls.original_collections = {
            name: list(rows) for name, rows in db_manager._collections.items()
        }

    def setUp(self):
        db_manager.use_mongo = False
        db_manager.db = None
        for rows in db_manager._collections.values():
            rows.clear()
        _request_history.clear()
        self.media_dir = tempfile.TemporaryDirectory()
        self.media_patch = patch.object(settings, "MEDIA_ROOT", Path(self.media_dir.name))
        self.media_patch.start()
        self.addCleanup(self.media_patch.stop)
        self.addCleanup(self.media_dir.cleanup)
        self.owner = self._seed_user("content-owner")
        self.other = self._seed_user("content-other")

    def tearDown(self):
        for name, rows in self.original_collections.items():
            db_manager._collections[name] = list(rows)

    @classmethod
    def tearDownClass(cls):
        db_manager.use_mongo = cls.original_use_mongo
        db_manager.db = cls.original_db

    def _seed_user(self, user_id, is_private=False):
        user = {
            "id": user_id,
            "username": user_id,
            "email": f"{user_id}@example.com",
            "role": "USER",
            "is_active": True,
            "is_private": is_private,
            "created_at": "2026-01-01T00:00:00+00:00",
        }
        db_manager._collections["users"].append(user)
        return user

    def _headers(self, user=None):
        user = user or self.owner
        token = create_access_token(data={"sub": user["id"], "role": user["role"]})
        return {"Authorization": f"Bearer {token}"}

    def _mock_text_moderation(self):
        return (
            patch("app.api.v1.endpoints.posts.inference_service.predict", return_value=_prediction()),
            patch(
                "app.api.v1.endpoints.posts.xai_engine.explain",
                return_value={"method": "test", "top_words": []},
            ),
            patch(
                "app.api.v1.endpoints.posts.moderation_engine.process_moderation",
                return_value={
                    "final_status": "APPROVED",
                    "recommendation": "Publish",
                    "user_explanation": "Text approved.",
                },
            ),
            patch("app.api.v1.endpoints.posts.audit_logger.log_event", new_callable=AsyncMock),
            patch("app.api.v1.endpoints.posts.create_notification", new_callable=AsyncMock),
        )

    def test_multiple_images_upload_preview_metadata_and_owner_deletion(self):
        prediction_patch, xai_patch, moderation_patch, audit_patch, notification_patch = self._mock_text_moderation()
        with prediction_patch as predict, xai_patch, moderation_patch, audit_patch, notification_patch:
            response = client.post(
                "/api/v1/posts/media",
                headers=self._headers(),
                data={"caption": "A text caption"},
                files=[
                    ("files", ("first.jpg", JPEG, "image/jpeg")),
                    ("files", ("second.jpg", JPEG, "image/jpeg")),
                ],
            )

        self.assertEqual(response.status_code, 201, response.text)
        post = response.json()
        self.assertEqual(len(post["media"]), 2)
        self.assertTrue(all(item["media_type"] == "image" for item in post["media"]))
        self.assertEqual(predict.call_args.args[0], "A text caption")
        media_response = client.get(post["media"][0]["url"], headers=self._headers())
        self.assertEqual(media_response.content, JPEG)

        denied_remove = client.delete(
            f"/api/v1/posts/{post['id']}/media/{post['media'][0]['filename']}",
            headers=self._headers(self.other),
        )
        self.assertEqual(denied_remove.status_code, 403)

        removed = client.delete(
            f"/api/v1/posts/{post['id']}/media/{post['media'][0]['filename']}",
            headers=self._headers(),
        )
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(len(db_manager._collections["posts"][0]["media"]), 1)

        deleted = client.delete(f"/api/v1/posts/{post['id']}", headers=self._headers())
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(db_manager._collections["posts"], [])
        self.assertEqual(list(Path(self.media_dir.name).iterdir()), [])

    def test_video_upload_and_private_media_authorization(self):
        private_owner = self._seed_user("private-video-owner", is_private=True)
        prediction_patch, xai_patch, moderation_patch, audit_patch, notification_patch = self._mock_text_moderation()
        with prediction_patch as predict, xai_patch, moderation_patch, audit_patch, notification_patch:
            response = client.post(
                "/api/v1/posts/media",
                headers=self._headers(private_owner),
                data={"caption": "A video caption"},
                files=[("files", ("clip.mp4", MP4, "video/mp4"))],
            )

        self.assertEqual(response.status_code, 201, response.text)
        post = response.json()
        self.assertEqual(post["media"][0]["media_type"], "video")
        self.assertEqual(predict.call_args.args[0], "A video caption")
        media_url = post["media"][0]["url"]
        self.assertEqual(client.get(media_url, headers=self._headers(self.other)).status_code, 404)
        db_manager._collections["follows"].append({
            "follower_id": self.other["id"],
            "following_id": private_owner["id"],
            "status": "ACCEPTED",
        })
        self.assertEqual(client.get(media_url, headers=self._headers(self.other)).content, MP4)
        denied_delete = client.delete(
            f"/api/v1/posts/{post['id']}",
            headers=self._headers(self.other),
        )
        self.assertEqual(denied_delete.status_code, 403)

    def test_one_post_accepts_multiple_images_and_one_video_in_order(self):
        prediction_patch, xai_patch, moderation_patch, audit_patch, notification_patch = self._mock_text_moderation()
        with prediction_patch as predict, xai_patch, moderation_patch, audit_patch, notification_patch:
            response = client.post(
                "/api/v1/posts/media",
                headers=self._headers(),
                data={"caption": "A mixed media post"},
                files=[
                    ("files", ("photo.jpg", JPEG, "image/jpeg")),
                    ("files", ("second.jpg", JPEG, "image/jpeg")),
                    ("files", ("clip.webm", WEBM, "video/webm")),
                ],
            )

        self.assertEqual(response.status_code, 201, response.text)
        post = response.json()
        media = post["media"]
        self.assertEqual([item["media_type"] for item in media], ["image", "image", "video"])
        self.assertEqual(len(media), 3)
        self.assertEqual(
            [client.get(item["url"], headers=self._headers()).content for item in media],
            [JPEG, JPEG, WEBM],
        )
        self.assertEqual(predict.call_args.args[0], "A mixed media post")

        removed = client.delete(
            f"/api/v1/posts/{post['id']}/media/{media[2]['filename']}",
            headers=self._headers(),
        )
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(
            [item["media_type"] for item in db_manager._collections["posts"][0]["media"]],
            ["image", "image"],
        )
        self.assertEqual(
            client.delete(f"/api/v1/posts/{post['id']}", headers=self._headers()).status_code,
            200,
        )
        self.assertEqual(list(Path(self.media_dir.name).iterdir()), [])

    def test_media_only_post_skips_text_model_and_rejects_spoofed_file(self):
        with patch("app.api.v1.endpoints.posts.inference_service.predict") as predict:
            response = client.post(
                "/api/v1/posts/media",
                headers=self._headers(),
                files=[("files", ("photo.webp", b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 8, "image/webp"))],
            )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertIsNone(response.json()["ai_prediction"])
        self.assertIn("not analyzed", response.json()["moderation_explanation"])
        predict.assert_not_called()

        rejected = client.post(
            "/api/v1/posts/media",
            headers=self._headers(),
            files=[("files", ("spoofed.jpg", b"not an image", "image/jpeg"))],
        )
        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(len(db_manager._collections["posts"]), 1)
        self.assertEqual(len(list(Path(self.media_dir.name).iterdir())), 1)

    def test_event_and_article_creation_use_text_moderation_and_owner_can_edit(self):
        prediction_patch, xai_patch, moderation_patch, audit_patch, notification_patch = self._mock_text_moderation()
        with prediction_patch as predict, xai_patch, moderation_patch, audit_patch, notification_patch:
            event_response = client.post(
                "/api/v1/posts/events",
                headers=self._headers(),
                data={
                    "title": "Community meetup",
                    "description": "A thoughtful discussion.",
                    "event_date": "2027-05-01",
                    "event_time": "18:30",
                    "location": "OpenVibe Hall",
                },
            )
            article_response = client.post(
                "/api/v1/posts/articles",
                headers=self._headers(),
                data={"title": "A long read", "content": "First paragraph.\n\nSecond paragraph."},
                files=[("cover_image", ("cover.jpg", JPEG, "image/jpeg"))],
            )

        self.assertEqual(event_response.status_code, 201, event_response.text)
        self.assertEqual(event_response.json()["content_type"], "EVENT")
        self.assertEqual(event_response.json()["event"]["event_time"], "18:30")
        self.assertEqual(article_response.status_code, 201, article_response.text)
        article = article_response.json()
        self.assertEqual(article["content_type"], "ARTICLE")
        self.assertEqual(article["article"]["title"], "A long read")
        self.assertEqual(len(article["media"]), 1)
        self.assertEqual([call.args[0] for call in predict.call_args_list], [
            "Community meetup A thoughtful discussion.",
            "A long read First paragraph. Second paragraph.",
        ])

        other_update = client.put(
            f"/api/v1/posts/{article['id']}/article",
            headers=self._headers(self.other),
            data={"title": "Changed", "content": "Changed article text."},
        )
        self.assertEqual(other_update.status_code, 403)

        prediction_patch, xai_patch, moderation_patch, audit_patch, notification_patch = self._mock_text_moderation()
        with prediction_patch as predict, xai_patch, moderation_patch, audit_patch, notification_patch:
            updated = client.put(
                f"/api/v1/posts/{article['id']}/article",
                headers=self._headers(),
                data={"title": "Updated long read", "content": "Updated article text."},
            )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["article"]["title"], "Updated long read")
        self.assertEqual(predict.call_args.args[0], "Updated long read Updated article text.")

        self.assertEqual(client.get("/api/v1/posts?content_type=EVENT").json()[0]["id"], event_response.json()["id"])
        self.assertEqual(client.get("/api/v1/posts?content_type=ARTICLE").json()[0]["id"], article["id"])

    def test_owner_can_edit_caption_and_media_without_losing_engagement(self):
        prediction_patch, xai_patch, moderation_patch, audit_patch, notification_patch = self._mock_text_moderation()
        with prediction_patch, xai_patch, moderation_patch, audit_patch, notification_patch:
            created = client.post(
                "/api/v1/posts/media",
                headers=self._headers(),
                data={"caption": "Original caption"},
                files=[
                    ("files", ("keep.jpg", JPEG, "image/jpeg")),
                    ("files", ("remove.mp4", MP4, "video/mp4")),
                ],
            )
        self.assertEqual(created.status_code, 201, created.text)
        post = created.json()
        db_manager._collections["post_likes"].append({"post_id": post["id"], "user_id": self.other["id"]})
        db_manager._collections["comments"].append({"id": "preserved-comment", "post_id": post["id"], "content": "Existing comment"})

        denied = client.put(
            f"/api/v1/posts/{post['id']}",
            headers=self._headers(self.other),
            data={"caption": "Not the owner"},
        )
        self.assertEqual(denied.status_code, 403)

        prediction_patch, xai_patch, moderation_patch, audit_patch, notification_patch = self._mock_text_moderation()
        with prediction_patch as predict, xai_patch, moderation_patch, audit_patch, notification_patch:
            updated = client.put(
                f"/api/v1/posts/{post['id']}",
                headers=self._headers(),
                data={"caption": "Updated caption", "remove_media": post["media"][1]["filename"]},
                files=[
                    ("files", ("added.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 24, "image/png")),
                    ("files", ("added.webm", WEBM, "video/webm")),
                ],
            )

        self.assertEqual(updated.status_code, 200, updated.text)
        result = updated.json()
        self.assertEqual(result["content"], "Updated caption")
        self.assertTrue(result["is_edited"])
        self.assertIsNotNone(result["edited_at"])
        self.assertEqual([item["media_type"] for item in result["media"]], ["image", "image", "video"])
        self.assertEqual(predict.call_count, 1)
        self.assertEqual(predict.call_args.args[0], "Updated caption")
        self.assertEqual(len(db_manager._collections["post_likes"]), 1)
        self.assertEqual(db_manager._collections["comments"][0]["id"], "preserved-comment")
        self.assertFalse(Path(self.media_dir.name, post["media"][1]["filename"]).exists())
        self.assertEqual(len(list(Path(self.media_dir.name).iterdir())), 3)

    def test_post_detail_endpoint_obeys_account_privacy(self):
        private_owner = self._seed_user("private-post-owner", is_private=True)
        prediction_patch, xai_patch, moderation_patch, audit_patch, notification_patch = self._mock_text_moderation()
        with prediction_patch, xai_patch, moderation_patch, audit_patch, notification_patch:
            created = client.post(
                "/api/v1/posts",
                headers=self._headers(private_owner),
                json={"content": "Private content"},
            )
        self.assertEqual(created.status_code, 201, created.text)
        post_id = created.json()["id"]
        self.assertEqual(client.get(f"/api/v1/posts/{post_id}", headers=self._headers(self.other)).status_code, 404)
        self.assertEqual(client.get(f"/api/v1/posts/{post_id}", headers=self._headers(private_owner)).status_code, 200)

    def test_long_article_checks_all_text_chunks_and_uses_highest_severity(self):
        hate_prediction = _prediction()
        hate_prediction.update({
            "label": "Hate Speech",
            "predicted_class": "Hate Speech",
            "confidence": 0.95,
            "probabilities": {"Hate Speech": 0.95, "Offensive": 0.03, "Normal": 0.02},
        })

        def predict_chunk(text):
            return hate_prediction if "hate" in text else _prediction()

        with (
            patch("app.api.v1.endpoints.posts.inference_service.predict", side_effect=predict_chunk) as predict,
            patch("app.api.v1.endpoints.posts.xai_engine.explain", return_value={"method": "test", "top_words": []}),
            patch("app.api.v1.endpoints.posts.audit_logger.log_event", new_callable=AsyncMock),
            patch("app.api.v1.endpoints.posts.create_notification", new_callable=AsyncMock),
        ):
            content = f"{'ordinary text ' * 60}hate speech near the end"
            response = client.post(
                "/api/v1/posts/articles",
                headers=self._headers(),
                data={"title": "Long article", "content": content},
            )

        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["moderation_status"], "BLOCKED")
        self.assertGreater(len(predict.call_args_list), 1)
        self.assertTrue(any("hate" in call.args[0] for call in predict.call_args_list))


if __name__ == "__main__":
    unittest.main()
