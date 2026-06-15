"""Short-lived SSO exchange codes — avoid passing JWTs in browser URLs."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException

from app.database.mongo_client import get_database

_TTL_SECONDS = 120


def _collection():
    return get_database()["sso_exchange_codes"]


def ensure_sso_exchange_indexes() -> None:
    col = _collection()
    col.create_index("expires_at", expireAfterSeconds=0)
    col.create_index("code", unique=True)


def create_sso_exchange_code(username: str) -> str:
    code = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    _collection().insert_one(
        {
            "code": code,
            "username": username,
            "created_at": now,
            "expires_at": now + timedelta(seconds=_TTL_SECONDS),
            "used": False,
        }
    )
    return code


def consume_sso_exchange_code(code: str) -> str:
    if not code or len(code) < 16:
        raise HTTPException(status_code=400, detail="Invalid SSO exchange code")
    doc = _collection().find_one_and_update(
        {"code": code, "used": False, "expires_at": {"$gt": datetime.utcnow()}},
        {"$set": {"used": True, "used_at": datetime.utcnow()}},
    )
    if not doc:
        raise HTTPException(status_code=400, detail="SSO exchange code expired or already used")
    return str(doc["username"])
