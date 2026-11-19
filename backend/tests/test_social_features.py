import unittest
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from main import app
from app.core.database import db_manager
from app.core.security import create_access_token, hash_password
from app.middleware.rate_limit import _request_history


client = TestClient(app)


def _seed_user(user_id: str, *, is_private: bool = False):
    user = {
        "id": user_id,
        "username": user_id,
        "email": f"{user_id}@example.com",
        "password_hash": hash_password("password123"),
        "role": "USER",
        "terms_accepted": True,
        "is_active": True,
        "is_private": is_private,
        "full_name": f"Name {user_id}",
        "headline": f"Headline {user_id}",
        "location": f"Location {user_id}",
        "about": f"About {user_id}",
        "skills": ["Testing"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    db_manager._collections["users"].append(user)
    return user


def _seed_post(author: dict, post_id: str, content: str):
    post = {
        "id": post_id,
        "author_id": author["id"],
        "author_username": author["username"],
        "author_full_name": author.get("full_name"),
        "content": content,
        "language": "en",
        "moderation_recommendation": "Publish",
        "moderation_status": "APPROVED",
        "moderation_explanation": "Approved for testing.",
        "ai_prediction": {
            "label": "Normal",
            "predicted_class": "Normal",
            "confidence": 0.95,
            "confidence_level": "HIGH",
            "probabilities": {"Hate Speech": 0.01, "Offensive": 0.04, "Normal": 0.95},
            "is_low_confidence": False,
            "model_name": "test-model",
            "model_version": "1.0",
            "inference_timestamp": datetime.now(timezone.utc).isoformat(),
            "explanation": {"method": "test", "top_words": []},
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    db_manager._collections["posts"].append(post)
    return post


def _headers(user: dict):
    token = create_access_token(data={"sub": user["id"], "role": user["role"]})
    return {"Authorization": f"Bearer {token}"}


class TestSocialPrivacyFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._original_use_mongo = db_manager.use_mongo
        cls._original_db = db_manager.db
        cls._original_collections = {
            name: list(rows) for name, rows in db_manager._collections.items()
        }

    def setUp(self):
        db_manager.use_mongo = False
        db_manager.db = None
        for rows in db_manager._collections.values():
            rows.clear()
        _request_history.clear()

    def tearDown(self):
        for name, rows in self._original_collections.items():
            db_manager._collections[name] = list(rows)

    @classmethod
    def tearDownClass(cls):
        db_manager.use_mongo = cls._original_use_mongo
        db_manager.db = cls._original_db

    def test_private_account_posts_and_details_require_approved_follow(self):
        owner = _seed_user("private-owner", is_private=True)
        follower = _seed_user("private-follower")
        outsider = _seed_user("private-outsider")
        public_author = _seed_user("public-author")
        private_post = _seed_post(owner, "private-post", "private-only text")
        _seed_post(public_author, "public-post", "public text")
        db_manager._collections["comments"].append({
            "id": "private-comment",
            "post_id": private_post["id"],
            "author_id": owner["id"],
            "author_username": owner["username"],
            "content": "private comment text",
            "language": "en",
            "moderation_status": "APPROVED",
            "ai_prediction": {
                "label": "Normal",
                "predicted_class": "Normal",
                "confidence": 0.95,
                "probabilities": {"Normal": 0.95},
                "is_low_confidence": False,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        db_manager._collections["comments"].append({
            "id": "private-reply",
            "post_id": private_post["id"],
            "parent_comment_id": "private-comment",
            "author_id": owner["id"],
            "author_username": owner["username"],
            "content": "private reply text",
            "language": "en",
            "moderation_status": "APPROVED",
            "ai_prediction": {
                "label": "Normal",
                "predicted_class": "Normal",
                "confidence": 0.95,
                "probabilities": {"Normal": 0.95},
                "is_low_confidence": False,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

        profile = client.get(f"/api/v1/users/{owner['id']}", headers=_headers(outsider))
        self.assertEqual(profile.status_code, 200)
        self.assertTrue(profile.json()["profile_restricted"])
        self.assertIsNone(profile.json()["about"])
        self.assertEqual(profile.json()["skills"], [])

        self.assertEqual(client.get(f"/api/v1/users/{owner['id']}/posts", headers=_headers(outsider)).status_code, 403)
        self.assertEqual(client.get(f"/api/v1/comments/post/{private_post['id']}", headers=_headers(outsider)).status_code, 404)
        home_posts = client.get("/api/v1/posts", headers=_headers(outsider)).json()
        self.assertEqual([row["id"] for row in home_posts], ["public-post"])
        search = client.get("/api/v1/search?q=private-only", headers=_headers(outsider))
        self.assertEqual(search.status_code, 200)
        self.assertEqual(search.json()["posts"], [])
        explore = client.get("/api/v1/posts/explore", headers=_headers(outsider))
        self.assertEqual(explore.status_code, 200)
        self.assertEqual([row["id"] for row in explore.json()], ["public-post"])

        requested = client.put(f"/api/v1/follows/{owner['id']}", headers=_headers(follower))
        self.assertEqual(requested.status_code, 200)
        self.assertEqual(requested.json()["status"], "PENDING")
        self.assertFalse(requested.json()["following"])

        incoming = client.get("/api/v1/follows/requests", headers=_headers(owner)).json()
        self.assertEqual([row["other_user"]["id"] for row in incoming["incoming"]], [follower["id"]])
        rejected_owner_action = client.post(
            f"/api/v1/follows/requests/{follower['id']}/accept",
            headers=_headers(outsider),
        )
        self.assertEqual(rejected_owner_action.status_code, 404)

        accepted = client.post(
            f"/api/v1/follows/requests/{follower['id']}/accept",
            headers=_headers(owner),
        )
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.json()["status"], "ACCEPTED")

        accessible_profile = client.get(f"/api/v1/users/{owner['id']}", headers=_headers(follower))
        self.assertFalse(accessible_profile.json()["profile_restricted"])
        self.assertEqual(accessible_profile.json()["about"], owner["about"])
        visible_posts = client.get(f"/api/v1/users/{owner['id']}/posts", headers=_headers(follower))
        self.assertEqual([row["id"] for row in visible_posts.json()], [private_post["id"]])
        visible_comments = client.get(f"/api/v1/comments/post/{private_post['id']}", headers=_headers(follower))
        visible_comment_rows = {row["id"]: row for row in visible_comments.json()}
        self.assertEqual(set(visible_comment_rows), {"private-comment", "private-reply"})
        self.assertEqual(visible_comment_rows["private-reply"]["parent_comment_id"], "private-comment")
        explore_after_follow = client.get("/api/v1/posts/explore", headers=_headers(follower))
        self.assertEqual([row["id"] for row in explore_after_follow.json()], ["public-post"])

        another_request = client.put(f"/api/v1/follows/{owner['id']}", headers=_headers(outsider))
        self.assertEqual(another_request.json()["status"], "PENDING")
        rejected = client.post(
            f"/api/v1/follows/requests/{outsider['id']}/reject",
            headers=_headers(owner),
        )
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(rejected.json()["status"], "REJECTED")
        owner["is_active"] = False
        inactive_owner_feed = client.get("/api/v1/posts", headers=_headers(follower))
        self.assertEqual([row["id"] for row in inactive_owner_feed.json()], ["public-post"])

    def test_explore_pagination_only_returns_public_posts(self):
        public_author = _seed_user("pagination-public")
        private_author = _seed_user("pagination-private", is_private=True)
        older = _seed_post(public_author, "pagination-older", "older public post")
        newer = _seed_post(public_author, "pagination-newer", "newer public post")
        _seed_post(private_author, "pagination-hidden", "private post")
        older["created_at"] = "2024-01-01T00:00:00+00:00"
        newer["created_at"] = "2024-01-02T00:00:00+00:00"

        first_page = client.get("/api/v1/posts/explore?offset=0&limit=1")
        second_page = client.get("/api/v1/posts/explore?offset=1&limit=1")

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(second_page.status_code, 200)
        self.assertEqual([row["id"] for row in first_page.json()], ["pagination-newer"])
        self.assertEqual([row["id"] for row in second_page.json()], ["pagination-older"])
        self.assertEqual(client.get("/api/v1/posts/explore?limit=51").status_code, 422)

    def test_media_post_rejects_multiple_videos(self):
        user = _seed_user("video-limit-user")
        response = client.post(
            "/api/v1/posts/media",
            headers=_headers(user),
            data={"caption": "Two videos are not allowed"},
            files=[
                ("files", ("first.mp4", b"first", "video/mp4")),
                ("files", ("second.webm", b"second", "video/webm")),
            ],
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "A post can contain only one video.")

    def test_private_setting_can_be_changed_and_pending_requests_accepted_when_public(self):
        owner = _seed_user("switch-owner", is_private=True)
        follower = _seed_user("switch-follower")
        post = _seed_post(owner, "switch-post", "visible after public switch")
        request = client.put(f"/api/v1/follows/{owner['id']}", headers=_headers(follower))
        self.assertEqual(request.json()["status"], "PENDING")
        self.assertEqual(client.get(f"/api/v1/users/{owner['id']}/posts", headers=_headers(follower)).status_code, 403)

        changed = client.patch(
            "/api/v1/auth/profile",
            headers=_headers(owner),
            json={"current_password": "password123", "is_private": True},
        )
        self.assertEqual(changed.status_code, 200)
        self.assertTrue(changed.json()["is_private"])
        self.assertEqual(client.get(f"/api/v1/users/{owner['id']}/posts").status_code, 403)

        made_public = client.patch(
            "/api/v1/auth/profile",
            headers=_headers(owner),
            json={"current_password": "password123", "is_private": False},
        )
        self.assertEqual(made_public.status_code, 200)
        self.assertFalse(made_public.json()["is_private"])
        self.assertEqual(client.get(f"/api/v1/users/{owner['id']}/posts", headers=_headers(follower)).status_code, 200)
        self.assertEqual(
            [row["id"] for row in client.get("/api/v1/posts/explore").json()],
            [post["id"]],
        )

    def test_headline_search_respects_private_account_visibility(self):
        private_user = _seed_user("hidden-headline", is_private=True)
        public_user = _seed_user("visible-headline")
        outsider = _seed_user("search-outsider")
        private_user["headline"] = "PrivateSpecialized phrase"
        public_user["headline"] = "PublicSpecialized phrase"

        private_search = client.get(
            "/api/v1/users/search?q=PrivateSpecialized",
            headers=_headers(outsider),
        )
        self.assertEqual(private_search.status_code, 200)
        self.assertEqual(private_search.json(), [])

        public_search = client.get(
            "/api/v1/users/search?q=PublicSpecialized",
            headers=_headers(outsider),
        )
        self.assertEqual([row["id"] for row in public_search.json()], [public_user["id"]])

        db_manager._collections["follows"].append({
            "follower_id": outsider["id"],
            "following_id": private_user["id"],
            "status": "ACCEPTED",
        })
        approved_search = client.get(
            "/api/v1/users/search?q=PrivateSpecialized",
            headers=_headers(outsider),
        )
        self.assertEqual([row["id"] for row in approved_search.json()], [private_user["id"]])


if __name__ == "__main__":
    unittest.main()
