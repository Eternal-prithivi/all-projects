"""Persisted in-app notifications per user."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId

from app.database.mongo_client import get_database

COLLECTION = "user_notifications"
NOTIFICATION_RETENTION_DAYS = 180


def _col():
    return get_database()[COLLECTION]


def ensure_notification_indexes() -> None:
    col = _col()
    try:
        col.create_index([("username", 1), ("created_at", -1)], background=True)
        col.create_index(
            "created_at",
            expireAfterSeconds=NOTIFICATION_RETENTION_DAYS * 86400,
            background=True,
        )
    except Exception:
        pass


def create_notification(
    username: str,
    *,
    title: str,
    message: str,
    type: str = "info",
    link: Optional[str] = None,
) -> str:
    doc = {
        "username": username,
        "title": title,
        "message": message,
        "type": type,
        "link": link,
        "read": False,
        "created_at": datetime.utcnow(),
    }
    result = _col().insert_one(doc)
    return str(result.inserted_id)


def _serialize(doc: dict) -> Dict[str, Any]:
    return {
        "id": str(doc["_id"]),
        "title": doc.get("title"),
        "message": doc.get("message"),
        "type": doc.get("type", "info"),
        "link": doc.get("link"),
        "read": bool(doc.get("read")),
        "created_at": doc.get("created_at").isoformat() + "Z"
        if doc.get("created_at")
        else None,
    }


def _build_query(
    username: str,
    *,
    read_filter: str = "all",
    type_filter: str = "all",
) -> Dict[str, Any]:
    query: Dict[str, Any] = {"username": username}
    if read_filter == "unread":
        query["read"] = False
    elif read_filter == "read":
        query["read"] = True
    if type_filter and type_filter != "all":
        query["type"] = type_filter
    return query


def count_unread(username: str) -> int:
    return _col().count_documents({"username": username, "read": False})


def list_notifications_paginated(
    username: str,
    *,
    limit: int = 20,
    skip: int = 0,
    read_filter: str = "all",
    type_filter: str = "all",
) -> Tuple[List[Dict[str, Any]], int, int]:
    """Returns (items, total_matching, unread_count)."""
    col = _col()
    query = _build_query(username, read_filter=read_filter, type_filter=type_filter)
    limit = max(5, min(limit, 50))
    skip = max(0, skip)

    total = col.count_documents(query)
    unread = count_unread(username)
    cursor = col.find(query).sort("created_at", -1).skip(skip).limit(limit)
    items = [_serialize(doc) for doc in cursor]
    return items, total, unread


def list_recent_notifications(username: str, limit: int = 8) -> Tuple[List[Dict[str, Any]], int]:
    """Recent notifications for bell dropdown."""
    limit = max(1, min(limit, 20))
    col = _col()
    unread = count_unread(username)
    cursor = (
        col.find({"username": username})
        .sort("created_at", -1)
        .limit(limit)
    )
    return [_serialize(doc) for doc in cursor], unread


def list_notifications(username: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Backward-compatible full list (capped)."""
    items, _, _ = list_notifications_paginated(username, limit=limit, skip=0)
    return items


def mark_read(username: str, notification_id: str) -> bool:
    try:
        oid = ObjectId(notification_id)
    except Exception:
        return False
    result = _col().update_one(
        {"_id": oid, "username": username},
        {"$set": {"read": True, "read_at": datetime.utcnow()}},
    )
    return result.modified_count > 0


def mark_all_read(username: str) -> int:
    result = _col().update_many(
        {"username": username, "read": False},
        {"$set": {"read": True, "read_at": datetime.utcnow()}},
    )
    return result.modified_count


def delete_notification(username: str, notification_id: str) -> bool:
    try:
        oid = ObjectId(notification_id)
    except Exception:
        return False
    result = _col().delete_one({"_id": oid, "username": username})
    return result.deleted_count > 0


def clear_all(username: str) -> int:
    result = _col().delete_many({"username": username})
    return result.deleted_count
