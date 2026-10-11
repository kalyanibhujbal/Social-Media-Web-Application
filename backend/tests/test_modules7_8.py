import unittest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from main import app
from app.core.security import create_access_token, hash_password
from app.core.database import db_manager
from app.middleware.rate_limit import _request_history

client = TestClient(app)


def _seed_user(user_id: str, role: str = "USER", username: str = "testuser"):
    doc = {
        "id": user_id,
        "username": username,
        "email": f"{user_id}@example.com",
        "password_hash": hash_password("password123"),
        "role": role,
        "is_active": True,
        "terms_accepted": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    db_manager._collections["users"].append(doc)
    return doc


def _seed_post(author_id: str, author_username: str, status: str = "APPROVED", label: str = "Normal"):
    post = {
        "id": f"post-{len(db_manager._collections['posts']) + 1}",
        "author_id": author_id,
        "author_username": author_username,
        "content": "Sample moderated content for testing.",
        "language": "en",
        "moderation_recommendation": "Publish",
        "moderation_status": status,
        "moderation_explanation": "Test explanation",
        "ai_prediction": {
            "label": label,
            "predicted_class": label,
            "confidence": 0.91,
            "confidence_level": "HIGH",
            "probabilities": {"Hate Speech": 0.02, "Offensive": 0.07, "Normal": 0.91},
            "is_low_confidence": False,
            "model_name": "xlm-roberta-base",
            "model_version": "1.0.0",
            "inference_timestamp": datetime.now(timezone.utc).isoformat(),
            "explanation": {"method": "LIME", "top_words": []},
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    db_manager._collections["posts"].append(post)
    db_manager._collections["moderation_logs"].append({
        "post_id": post["id"],
        "ai_label": label,
        "confidence": 0.91,
        "recommendation": "Publish",
        "action_taken": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return post


def _seed_comment(author_id: str, author_username: str, status: str = "APPROVED", label: str = "Normal"):
    comment = {
        "id": f"comment-{len(db_manager._collections['comments']) + 1}",
        "post_id": "source-post-id",
        "author_id": author_id,
        "author_username": author_username,
        "content": "A moderated comment for testing.",
        "language": "en",
        "moderation_recommendation": "Manual Review" if status == "FLAGGED_FOR_REVIEW" else "Publish",
        "moderation_status": status,
        "moderation_explanation": "Test explanation",
        "ai_prediction": {
            "label": label,
            "predicted_class": label,
            "confidence": 0.61,
            "confidence_level": "MEDIUM",
            "probabilities": {"Hate Speech": 0.61, "Offensive": 0.19, "Normal": 0.2},
            "is_low_confidence": False,
            "model_name": "heuristic-fallback",
            "model_version": "1.0.0",
            "inference_timestamp": datetime.now(timezone.utc).isoformat(),
            "explanation": {"method": "LIME", "top_words": []},
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    db_manager._collections["comments"].append(comment)
    db_manager._collections["moderation_logs"].append({
        "content_id": comment["id"],
        "content_type": "comment",
        "ai_label": label,
        "confidence": 0.61,
        "recommendation": comment["moderation_recommendation"],
        "action_taken": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return comment


class TestModules7And8DashboardAdmin(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._orig_posts = list(db_manager._collections.get("posts", []))
        cls._orig_comments = list(db_manager._collections.get("comments", []))
        cls._orig_users = list(db_manager._collections.get("users", []))
        cls._orig_logs = list(db_manager._collections.get("moderation_logs", []))
        cls._orig_audit_logs = list(db_manager._collections.get("audit_logs", []))
        cls._orig_consents = list(db_manager._collections.get("consent_records", []))
        cls._orig_privacy_requests = list(db_manager._collections.get("privacy_requests", []))

    def setUp(self):
        client.cookies.clear()
        db_manager._collections["posts"] = []
        db_manager._collections["moderation_logs"] = []
        db_manager._collections["comments"] = []
        db_manager._collections["users"] = list(self._orig_users)
        db_manager._collections["audit_logs"] = []
        db_manager._collections["consent_records"] = []
        db_manager._collections["privacy_requests"] = []
        _request_history.clear()

    def tearDown(self):
        db_manager._collections["posts"] = list(self._orig_posts)
        db_manager._collections["comments"] = list(self._orig_comments)
        db_manager._collections["users"] = list(self._orig_users)
        db_manager._collections["moderation_logs"] = list(self._orig_logs)
        db_manager._collections["audit_logs"] = list(self._orig_audit_logs)
        db_manager._collections["consent_records"] = list(self._orig_consents)
        db_manager._collections["privacy_requests"] = list(self._orig_privacy_requests)

    def test_unauthorized_user_blocked_from_admin_queue(self):
        user = _seed_user("regular-user-id", "USER")
        user_token = create_access_token(data={"sub": user["id"], "role": "USER"})
        response = client.get(
            "/api/v1/admin/queue",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_admin_routes_rejected(self):
        for path in ["/api/v1/admin/analytics", "/api/v1/admin/report", "/api/v1/admin/users", "/api/v1/admin/privacy-requests"]:
            response = client.get(path)
            self.assertEqual(response.status_code, 401, msg=path)

    def test_admin_authorized_access_to_analytics(self):
        admin = _seed_user("admin-id", "ADMIN", "admin")
        admin_token = create_access_token(data={"sub": admin["id"], "role": "ADMIN"})
        _seed_post(admin["id"], "admin", status="FLAGGED_FOR_REVIEW", label="Offensive")

        response = client.get(
            "/api/v1/admin/analytics",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_posts"], 1)
        self.assertEqual(data["flagged_count"], 1)
        self.assertIn("confidence_distribution", data)
        self.assertIn("model_evaluation", data)

    def test_admin_report_generation_from_real_data(self):
        admin = _seed_user("admin-id-2", "ADMIN", "admin2")
        admin_token = create_access_token(data={"sub": admin["id"], "role": "ADMIN"})
        _seed_post(admin["id"], "admin2")

        response = client.get(
            "/api/v1/admin/report",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(response.status_code, 200)
        report = response.json()
        self.assertEqual(report["system_summary"]["total_posts"], 1)

    def test_empty_analytics_zero_posts(self):
        admin = _seed_user("admin-empty", "ADMIN", "adminempty")
        admin_token = create_access_token(data={"sub": admin["id"], "role": "ADMIN"})
        response = client.get(
            "/api/v1/admin/analytics",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total_posts"], 0)
        self.assertEqual(response.json()["total_moderation_items"], 0)
        self.assertEqual(response.json()["pending_manual_reviews"], 0)
        self.assertEqual(response.json()["model_evaluation"]["evaluation_status"], "NOT_AVAILABLE")

    def test_user_data_isolation_dashboard_me(self):
        user_a = _seed_user("user-a", "USER", "alice")
        user_b = _seed_user("user-b", "USER", "bob")
        _seed_post(user_a["id"], "alice")
        _seed_post(user_b["id"], "bob")

        token_a = create_access_token(data={"sub": user_a["id"], "role": "USER"})
        response = client.get(
            "/api/v1/dashboard/me",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["stats"]["total_posts"], 1)
        self.assertEqual(len(body["posts"]), 1)
        self.assertEqual(body["posts"][0]["author_id"], user_a["id"])

    def test_user_cannot_access_admin_users(self):
        user = _seed_user("user-block", "USER")
        token = create_access_token(data={"sub": user["id"], "role": "USER"})
        response = client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 403)

    def test_user_is_rejected_from_every_admin_api_family(self):
        user = _seed_user("admin-api-block", "USER")
        token = create_access_token(data={"sub": user["id"], "role": "ADMIN"})
        headers = {"Authorization": f"Bearer {token}"}
        paths = [
            ("GET", "/api/v1/admin/queue"),
            ("GET", "/api/v1/admin/content/missing"),
            ("POST", "/api/v1/admin/review/missing"),
            ("GET", "/api/v1/admin/analytics"),
            ("GET", "/api/v1/admin/report"),
            ("GET", "/api/v1/admin/moderation-history"),
            ("GET", "/api/v1/admin/audit-logs"),
            ("GET", "/api/v1/admin/users"),
            ("GET", "/api/v1/admin/privacy-requests"),
            ("PATCH", "/api/v1/admin/privacy-requests/missing"),
        ]
        for method, path in paths:
            payload = {"action": "APPROVED"} if method == "POST" else {"status": "RESOLVED", "response": "Handled"} if method == "PATCH" else None
            response = client.request(method, path, headers=headers, json=payload)
            self.assertEqual(response.status_code, 403, msg=path)

    def test_user_dashboard_includes_only_own_posts_comments_and_history(self):
        user_a = _seed_user("dashboard-owner", "USER", "owner")
        user_b = _seed_user("dashboard-other", "USER", "other")
        _seed_post(user_a["id"], "owner")
        own_comment = _seed_comment(user_a["id"], "owner", "FLAGGED_FOR_REVIEW", "Hate Speech")
        _seed_comment(user_b["id"], "other")
        token = create_access_token(data={"sub": user_a["id"], "role": "USER"})

        response = client.get("/api/v1/dashboard/me", headers={"Authorization": f"Bearer {token}"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["stats"]["total_posts"], 1)
        self.assertEqual(body["stats"]["total_comments"], 1)
        self.assertEqual([item["author_id"] for item in body["comments"]], [user_a["id"]])
        self.assertEqual(body["pending_items"][0]["type"], "comment")
        own_history = next(entry for entry in body["moderation_history"] if entry["content_id"] == own_comment["id"])
        self.assertEqual(own_history["content_type"], "comment")
        self.assertNotIn(user_b["id"], str(body))

    def test_admin_queue_includes_comments_without_author_details(self):
        admin = _seed_user("admin-comment-queue", "ADMIN", "moderator")
        _seed_comment("private-author-id", "private-author", "FLAGGED_FOR_REVIEW", "Offensive")
        token = create_access_token(data={"sub": admin["id"], "role": "ADMIN"})

        response = client.get("/api/v1/admin/queue", headers={"Authorization": f"Bearer {token}"})

        self.assertEqual(response.status_code, 200)
        queued = response.json()[0]
        self.assertEqual(queued["content_type"], "comment")
        self.assertNotIn("author_id", queued)
        self.assertNotIn("author_username", queued)
        self.assertNotIn("private-author", str(queued))

    def test_admin_can_review_comment_and_action_is_audited_without_notes_or_ip(self):
        admin = _seed_user("admin-comment-review", "ADMIN", "moderator")
        comment = _seed_comment("private-author", "private-author", "FLAGGED_FOR_REVIEW", "Offensive")
        token = create_access_token(data={"sub": admin["id"], "role": "ADMIN"})

        response = client.post(
            f"/api/v1/admin/review/{comment['id']}?content_type=comment",
            headers={"Authorization": f"Bearer {token}"},
            json={"action": "APPROVED", "confirm_action": True, "review_notes": "Reviewed"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["moderation_status"], "APPROVED")
        self.assertEqual(db_manager._collections["comments"][0]["moderation_status"], "APPROVED")
        log = db_manager._collections["audit_logs"][-1]
        self.assertEqual(log["event_type"], "ADMIN_REVIEW_COMMENT")
        self.assertNotIn("ip_address", log)
        self.assertNotIn("Reviewed", log["details"])

    def test_admin_decision_requires_explicit_confirmation(self):
        admin = _seed_user("admin-confirmation", "ADMIN", "moderator")
        comment = _seed_comment("author", "author", "FLAGGED_FOR_REVIEW", "Offensive")
        token = create_access_token(data={"sub": admin["id"], "role": "ADMIN"})
        response = client.post(
            f"/api/v1/admin/review/{comment['id']}?content_type=comment",
            headers={"Authorization": f"Bearer {token}"},
            json={"action": "REJECT"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(comment["moderation_status"], "FLAGGED_FOR_REVIEW")

    def test_admin_analytics_aggregates_actual_posts_and_comments(self):
        admin = _seed_user("admin-analytics", "ADMIN", "moderator")
        _seed_post("user-a", "user-a", "APPROVED", "Normal")
        _seed_comment("user-b", "user-b", "FLAGGED_FOR_REVIEW", "Hate Speech")
        token = create_access_token(data={"sub": admin["id"], "role": "ADMIN"})

        response = client.get("/api/v1/admin/analytics", headers={"Authorization": f"Bearer {token}"})

        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["total_moderation_items"], 2)
        self.assertEqual(data["approved_count"], 1)
        self.assertEqual(data["flagged_count"], 1)
        self.assertEqual(data["pending_manual_reviews"], 1)
        self.assertEqual(data["hate_speech_count"], 1)
        self.assertEqual(sum(bucket["count"] for bucket in data["confidence_distribution"]), 2)

    def test_mark_reviewed_clears_pending_count_without_rewriting_final_status(self):
        admin = _seed_user("admin-mark-reviewed", "ADMIN", "moderator")
        post = _seed_post("post-author", "post-author", "FLAGGED_FOR_REVIEW", "Offensive")
        token = create_access_token(data={"sub": admin["id"], "role": "ADMIN"})
        headers = {"Authorization": f"Bearer {token}"}

        action = client.post(
            f"/api/v1/admin/review/{post['id']}",
            headers=headers,
            json={"action": "MARK_REVIEWED"},
        )
        analytics = client.get("/api/v1/admin/analytics", headers=headers).json()
        queue = client.get("/api/v1/admin/queue", headers=headers).json()

        self.assertEqual(action.status_code, 200)
        self.assertEqual(action.json()["moderation_status"], "FLAGGED_FOR_REVIEW")
        self.assertEqual(analytics["flagged_count"], 1)
        self.assertEqual(analytics["pending_manual_reviews"], 0)
        self.assertEqual(queue, [])

    def test_login_uses_http_only_session_cookie_and_logout_clears_it(self):
        user = _seed_user("cookie-user", "USER", "cookieuser")
        response = client.post("/api/v1/auth/login", json={"email": user["email"], "password": "password123"})

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("access_token", response.json())
        cookie_header = response.headers["set-cookie"].lower()
        self.assertIn("httponly", cookie_header)
        self.assertIn("samesite=strict", cookie_header)
        self.assertEqual(client.get("/api/v1/dashboard/me").status_code, 200)
        logout = client.post("/api/v1/auth/logout")
        self.assertEqual(logout.status_code, 204)
        self.assertEqual(client.get("/api/v1/dashboard/me").status_code, 401)

    def test_inactive_account_session_is_rejected(self):
        user = _seed_user("inactive-user", "USER", "inactive")
        user["is_active"] = False
        token = create_access_token(data={"sub": user["id"], "role": "USER"})
        response = client.get("/api/v1/dashboard/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 401)

    def test_cookie_session_rejects_untrusted_origin_for_mutations(self):
        user = _seed_user("csrf-user", "USER", "csrf")
        token = create_access_token(data={"sub": user["id"], "role": "USER"})
        client.cookies.set("moderation_session", token, path="/api/v1")
        response = client.post(
            "/api/v1/privacy/delete-account",
            headers={"Origin": "https://attacker.example"},
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_review_updates_post_and_log(self):
        admin = _seed_user("admin-review", "ADMIN", "reviewadmin")
        post = _seed_post("other-user", "other", status="FLAGGED_FOR_REVIEW", label="Hate Speech")
        admin_token = create_access_token(data={"sub": admin["id"], "role": "ADMIN"})

        response = client.post(
            f"/api/v1/admin/review/{post['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"action": "APPROVED", "confirm_action": True, "review_notes": "False positive"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["moderation_status"], "APPROVED")

        log = next(l for l in db_manager._collections["moderation_logs"] if l["post_id"] == post["id"])
        self.assertIsNotNone(log.get("human_review"))
        self.assertEqual(log["human_review"]["review_action"], "OVERRIDDEN_APPROVE")

    def test_appeal_only_own_post(self):
        owner = _seed_user("owner-id", "USER", "owner")
        other = _seed_user("other-id", "USER", "other")
        post = _seed_post(owner["id"], "owner", status="BLOCKED")
        other_token = create_access_token(data={"sub": other["id"], "role": "USER"})

        response = client.post(
            f"/api/v1/posts/{post['id']}/appeal",
            headers={"Authorization": f"Bearer {other_token}"},
            json={"reason": "This was a mistake"},
        )
        self.assertEqual(response.status_code, 403)

    def test_new_appeal_reopens_a_previously_reviewed_post(self):
        owner = _seed_user("appeal-owner", "USER", "owner")
        post = _seed_post(owner["id"], "owner", status="BLOCKED")
        post["admin_reviewed"] = True
        token = create_access_token(data={"sub": owner["id"], "role": "USER"})
        response = client.post(
            f"/api/v1/posts/{post['id']}/appeal",
            headers={"Authorization": f"Bearer {token}"},
            json={"reason": "Please review this"},
        )
        dashboard = client.get("/api/v1/dashboard/me", headers={"Authorization": f"Bearer {token}"}).json()

        self.assertEqual(response.status_code, 200)
        self.assertFalse(post["admin_reviewed"])
        self.assertEqual(dashboard["stats"]["pending_review_posts"], 1)

    def test_public_post_feed_never_exposes_unapproved_statuses(self):
        _seed_post("feed-author", "author", status="BLOCKED", label="Hate Speech")
        approved = _seed_post("feed-author", "author", status="APPROVED", label="Normal")
        self.assertEqual(client.get("/api/v1/posts?status_filter=BLOCKED").status_code, 400)
        response = client.get("/api/v1/posts")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()], [approved["id"]])

    def test_privacy_requests_are_account_scoped_and_admin_handled(self):
        owner = _seed_user("privacy-owner", "USER", "owner")
        other = _seed_user("privacy-other", "USER", "other")
        admin = _seed_user("privacy-admin", "ADMIN", "privacyadmin")
        owner_token = create_access_token(data={"sub": owner["id"], "role": "USER"})
        other_token = create_access_token(data={"sub": other["id"], "role": "USER"})
        admin_token = create_access_token(data={"sub": admin["id"], "role": "ADMIN"})

        submitted = client.post(
            "/api/v1/privacy/requests",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"request_type": "PRIVACY_CONCERN", "description": "Please explain this record."},
        )
        self.assertEqual(submitted.status_code, 201)
        request_id = submitted.json()["id"]
        self.assertEqual(client.get("/api/v1/privacy/requests/me", headers={"Authorization": f"Bearer {other_token}"}).json(), [])
        unauthorized = client.get("/api/v1/admin/privacy-requests", headers={"Authorization": f"Bearer {other_token}"})
        self.assertEqual(unauthorized.status_code, 403)

        queue = client.get("/api/v1/admin/privacy-requests", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(queue.status_code, 200)
        self.assertEqual(queue.json()[0]["requester_reference"], owner["id"])
        self.assertNotIn("email", queue.json()[0])
        updated = client.patch(
            f"/api/v1/admin/privacy-requests/{request_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": "RESOLVED", "response": "Your request was reviewed."},
        )
        self.assertEqual(updated.status_code, 200)
        mine = client.get("/api/v1/privacy/requests/me", headers={"Authorization": f"Bearer {owner_token}"})
        self.assertEqual(mine.json()[0]["response"], "Your request was reviewed.")

    def test_profile_correction_requires_current_password_and_updates_actual_account(self):
        owner = _seed_user("profile-owner", "USER", "profileuser")
        token = create_access_token(data={"sub": owner["id"], "role": "USER"})
        response = client.patch(
            "/api/v1/auth/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={"username": "corrected-user", "current_password": "password123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(owner["username"], "corrected-user")
        rejected = client.patch(
            "/api/v1/auth/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={"email": "new@example.com", "current_password": "wrong-pass"},
        )
        self.assertEqual(rejected.status_code, 403)

    def test_data_export_contains_only_current_users_records(self):
        owner = _seed_user("export-owner", "USER", "owner")
        other = _seed_user("export-other", "USER", "other")
        own_post = _seed_post(owner["id"], "owner")
        _seed_post(other["id"], "other")
        own_comment = _seed_comment(owner["id"], "owner")
        _seed_comment(other["id"], "other")
        db_manager._collections["consent_records"].append({"id": "owner-consent", "user_id": owner["id"], "consent_type": "analytics_cookies"})
        db_manager._collections["consent_records"].append({"id": "other-consent", "user_id": other["id"], "consent_type": "analytics_cookies"})
        token = create_access_token(data={"sub": owner["id"], "role": "USER"})
        response = client.get("/api/v1/privacy/export-data", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual([row["id"] for row in body["posts"]], [own_post["id"]])
        self.assertEqual([row["id"] for row in body["comments"]], [own_comment["id"]])
        self.assertEqual([row["id"] for row in body["consent_preferences"]], ["owner-consent"])
        self.assertNotIn("password_hash", str(body))

    def test_account_deletion_requires_confirmation_and_removes_owned_records(self):
        owner = _seed_user("delete-owner", "USER", "deleteuser")
        own_post = _seed_post(owner["id"], "deleteuser")
        own_comment = _seed_comment(owner["id"], "deleteuser")
        db_manager._collections["consent_records"].append({"id": "delete-consent", "user_id": owner["id"]})
        db_manager._collections["privacy_requests"].append({"id": "delete-request", "user_id": owner["id"]})
        db_manager._collections["audit_logs"].append({"id": "delete-audit", "actor_id": owner["id"], "resource_id": own_post["id"], "details": "Comment created for post " + own_post["id"]})
        token = create_access_token(data={"sub": owner["id"], "role": "USER"})
        headers = {"Authorization": f"Bearer {token}"}
        rejected = client.post("/api/v1/privacy/delete-account", headers=headers, json={"confirm_deletion": False})
        self.assertEqual(rejected.status_code, 400)
        deleted = client.post("/api/v1/privacy/delete-account", headers=headers, json={"confirm_deletion": True})
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(any(user["id"] == owner["id"] for user in db_manager._collections["users"]))
        self.assertFalse(any(item["id"] in {own_post["id"], own_comment["id"]} for item in db_manager._collections["posts"] + db_manager._collections["comments"]))
        self.assertEqual(db_manager._collections["consent_records"], [])
        self.assertEqual(db_manager._collections["privacy_requests"], [])
        audit = next(item for item in db_manager._collections["audit_logs"] if item["id"] == "delete-audit")
        self.assertEqual(audit["actor_id"], "deleted-user")
        self.assertIsNone(audit["resource_id"])
        self.assertNotIn(own_post["id"], audit["details"])


if __name__ == "__main__":
    unittest.main()
