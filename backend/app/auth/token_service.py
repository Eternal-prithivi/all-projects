"""Refresh token issuance and rotation."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

from fastapi import HTTPException
from jose import jwt, JWTError

from app.database.mongo_client import get_database
from app.utils.config import settings

REFRESH_TOKEN_DAYS = 14


def _collection():
    return get_database()["refresh_tokens"]


def ensure_refresh_token_indexes() -> None:
    col = _collection()
    col.create_index("token_hash", unique=True)
    col.create_index("expires_at", expireAfterSeconds=0)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_refresh_token(username: str) -> str:
    raw = secrets.token_urlsafe(48)
    now = datetime.utcnow()
    expires = now + timedelta(days=REFRESH_TOKEN_DAYS)
    _collection().insert_one(
        {
            "username": username,
            "token_hash": _hash_token(raw),
            "created_at": now,
            "expires_at": expires,
            "revoked": False,
        }
    )
    return raw


def issue_token_pair(username: str) -> Tuple[str, str]:
    from app.auth.auth_utils import create_access_token

    access = create_access_token({"sub": username})
    refresh = create_refresh_token(username)
    return access, refresh


def rotate_refresh_token(raw_refresh: str) -> Tuple[str, str]:
    token_hash = _hash_token(raw_refresh)
    doc = _collection().find_one(
        {"token_hash": token_hash, "revoked": False, "expires_at": {"$gt": datetime.utcnow()}}
    )
    if not doc:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    username = doc["username"]
    _collection().update_one({"_id": doc["_id"]}, {"$set": {"revoked": True, "revoked_at": datetime.utcnow()}})
    return issue_token_pair(username)


def revoke_refresh_tokens(username: str) -> int:
    res = _collection().update_many(
        {"username": username, "revoked": False},
        {"$set": {"revoked": True, "revoked_at": datetime.utcnow()}},
    )
    return int(res.modified_count)
