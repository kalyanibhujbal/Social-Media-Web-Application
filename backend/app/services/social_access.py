from app.core.database import db_manager


def _accepted_follow_query(follower_id: str, following_id: str | None = None) -> dict:
    query = {
        "follower_id": follower_id,
        "$or": [{"status": "ACCEPTED"}, {"status": {"$exists": False}}],
    }
    if following_id is not None:
        query["following_id"] = following_id
    return query


async def get_user(user_id: str) -> dict | None:
    if db_manager.use_mongo and db_manager.db is not None:
        return await db_manager.db["users"].find_one({"id": user_id})
    return next(
        (row for row in db_manager._collections.get("users", []) if row.get("id") == user_id),
        None,
    )


async def is_approved_follower(follower_id: str, following_id: str) -> bool:
    query = _accepted_follow_query(follower_id, following_id)
    if db_manager.use_mongo and db_manager.db is not None:
        return await db_manager.db["follows"].find_one(query) is not None
    return any(
        row.get("follower_id") == follower_id
        and row.get("following_id") == following_id
        and row.get("status", "ACCEPTED") == "ACCEPTED"
        for row in db_manager._collections.get("follows", [])
    )


async def can_view_profile_content(user: dict, viewer_id: str | None) -> bool:
    if not user.get("is_private", False) or viewer_id == user.get("id"):
        return True
    return bool(viewer_id and await is_approved_follower(viewer_id, user["id"]))


async def can_view_post(post: dict, viewer_id: str | None) -> bool:
    author = await get_user(post.get("author_id", ""))
    return bool(author and author.get("is_active", True) and await can_view_profile_content(author, viewer_id))


async def visible_author_ids(viewer_id: str | None = None, *, public_only: bool = False) -> set[str]:
    if db_manager.use_mongo and db_manager.db is not None:
        users = await db_manager.db["users"].find(
            {"is_active": {"$ne": False}, "is_private": {"$ne": True}},
            {"id": 1},
        ).to_list(length=None)
        author_ids = {row["id"] for row in users if row.get("id")}
        if public_only or not viewer_id:
            return author_ids
        follows = await db_manager.db["follows"].find(
            _accepted_follow_query(viewer_id),
            {"following_id": 1},
        ).to_list(length=None)
        following_ids = {row["following_id"] for row in follows if row.get("following_id")}
        if following_ids:
            followed_users = await db_manager.db["users"].find(
                {"id": {"$in": list(following_ids)}, "is_active": {"$ne": False}},
                {"id": 1},
            ).to_list(length=None)
            author_ids.update(row["id"] for row in followed_users if row.get("id"))
        user = await get_user(viewer_id)
        if user and user.get("is_active", True):
            author_ids.add(viewer_id)
        return author_ids

    users = db_manager._collections.get("users", [])
    author_ids = {
        row["id"]
        for row in users
        if row.get("id") and row.get("is_active", True) and not row.get("is_private", False)
    }
    if public_only or not viewer_id:
        return author_ids
    active_user_ids = {
        row["id"]
        for row in users
        if row.get("id") and row.get("is_active", True)
    }
    author_ids.update(
        row["following_id"]
        for row in db_manager._collections.get("follows", [])
        if row.get("follower_id") == viewer_id
        and row.get("following_id")
        and row.get("following_id") in active_user_ids
        and row.get("status", "ACCEPTED") == "ACCEPTED"
    )
    user = await get_user(viewer_id)
    if user and user.get("is_active", True):
        author_ids.add(viewer_id)
    return author_ids
