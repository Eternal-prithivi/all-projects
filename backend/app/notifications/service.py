"""Persisted in-app notifications per user."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.database.mongo_client import get_database

COLLECTION = "user_notifications"


def _col():
    return get_database()[COLLECTION]


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


def list_notifications(username: str, limit: int = 100) -> List[Dict[str, Any]]:
    cursor = (
        _col()
        .find({"username": username})
        .sort("created_at", -1)
        .limit(limit)
    )
    items = []
    for doc in cursor:
        items.append(
            {
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
        )
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
