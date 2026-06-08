"""MongoDB access for support tickets."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.database.mongo_client import get_database
from app.support.constants import (
    MESSAGES_COLLECTION,
    OTP_COLLECTION,
    TICKETS_COLLECTION,
)

_indexes_ensured = False


def _db():
    return get_database()


def ensure_support_indexes() -> None:
    global _indexes_ensured
    if _indexes_ensured:
        return
    db = _db()
    tickets = db[TICKETS_COLLECTION]
    tickets.create_index("reference_code", unique=True)
    tickets.create_index("requester_email")
    tickets.create_index("user_id")
    tickets.create_index([("status", 1), ("last_message_at", -1)])
    db[MESSAGES_COLLECTION].create_index([("ticket_id", 1), ("created_at", 1)])
    db[OTP_COLLECTION].create_index([("reference_code", 1), ("email", 1)])
    db[OTP_COLLECTION].create_index("expires_at", expireAfterSeconds=0)
    _indexes_ensured = True


def make_reference_code(ticket_id: ObjectId) -> str:
    clean = str(ticket_id).replace("-", "").upper()
    suffix = clean[-8:] if len(clean) >= 8 else clean
    return f"ZN-{suffix}"


def insert_ticket(doc: Dict[str, Any]) -> ObjectId:
    ensure_support_indexes()
    result = _db()[TICKETS_COLLECTION].insert_one(doc)
    ref = make_reference_code(result.inserted_id)
    _db()[TICKETS_COLLECTION].update_one(
        {"_id": result.inserted_id},
        {"$set": {"reference_code": ref}},
    )
    doc["reference_code"] = ref
    return result.inserted_id


def insert_message(doc: Dict[str, Any]) -> ObjectId:
    ensure_support_indexes()
    return _db()[MESSAGES_COLLECTION].insert_one(doc).inserted_id


def find_ticket_by_reference(reference_code: str) -> Optional[Dict[str, Any]]:
    ensure_support_indexes()
    return _db()[TICKETS_COLLECTION].find_one(
        {"reference_code": reference_code.upper().strip()}
    )


def find_ticket_by_id(ticket_id: str | ObjectId) -> Optional[Dict[str, Any]]:
    ensure_support_indexes()
    oid = ticket_id if isinstance(ticket_id, ObjectId) else ObjectId(ticket_id)
    return _db()[TICKETS_COLLECTION].find_one({"_id": oid})


def list_tickets_for_user(*, email: str, username: Optional[str]) -> List[Dict[str, Any]]:
    ensure_support_indexes()
    email_norm = email.strip().lower()
    query: Dict[str, Any] = {"$or": [{"requester_email": email_norm}]}
    if username:
        query["$or"].append({"user_id": username})
    cursor = (
        _db()[TICKETS_COLLECTION]
        .find(query)
        .sort("last_message_at", -1)
        .limit(100)
    )
    return list(cursor)


def list_tickets_admin(
    *,
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[List[Dict[str, Any]], int]:
    ensure_support_indexes()
    query: Dict[str, Any] = {}
    if status:
        query["status"] = status
    if search:
        s = search.strip()
        query["$or"] = [
            {"reference_code": {"$regex": s, "$options": "i"}},
            {"requester_email": {"$regex": s, "$options": "i"}},
            {"requester_name": {"$regex": s, "$options": "i"}},
        ]
    coll = _db()[TICKETS_COLLECTION]
    total = coll.count_documents(query)
    items = list(
        coll.find(query).sort("last_message_at", -1).skip(skip).limit(limit)
    )
    return items, total


def get_messages(ticket_id: ObjectId) -> List[Dict[str, Any]]:
    ensure_support_indexes()
    return list(
        _db()[MESSAGES_COLLECTION]
        .find({"ticket_id": ticket_id})
        .sort("created_at", 1)
    )


def update_ticket(ticket_id: ObjectId, fields: Dict[str, Any]) -> None:
    ensure_support_indexes()
    _db()[TICKETS_COLLECTION].update_one({"_id": ticket_id}, {"$set": fields})


def upsert_otp(doc: Dict[str, Any]) -> None:
    ensure_support_indexes()
    coll = _db()[OTP_COLLECTION]
    coll.delete_many(
        {"reference_code": doc["reference_code"], "email": doc["email"]}
    )
    coll.insert_one(doc)


def find_otp(reference_code: str, email: str) -> Optional[Dict[str, Any]]:
    ensure_support_indexes()
    return _db()[OTP_COLLECTION].find_one(
        {
            "reference_code": reference_code.upper().strip(),
            "email": email.strip().lower(),
        }
    )


def delete_otp(reference_code: str, email: str) -> None:
    _db()[OTP_COLLECTION].delete_many(
        {
            "reference_code": reference_code.upper().strip(),
            "email": email.strip().lower(),
        }
    )


def serialize_ticket(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(doc["_id"]),
        "reference_code": doc.get("reference_code"),
        "status": doc.get("status"),
        "category": doc.get("category"),
        "subject": doc.get("subject"),
        "requester_name": doc.get("requester_name"),
        "requester_email": doc.get("requester_email"),
        "user_id": doc.get("user_id"),
        "assigned_to": doc.get("assigned_to"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
        "last_message_at": doc.get("last_message_at"),
        "resolved_at": doc.get("resolved_at"),
    }


def serialize_message(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(doc["_id"]),
        "ticket_id": str(doc["ticket_id"]),
        "author_type": doc.get("author_type"),
        "author_id": doc.get("author_id"),
        "author_name": doc.get("author_name"),
        "body": doc.get("body"),
        "created_at": doc.get("created_at"),
        "email_sent": doc.get("email_sent", False),
    }
