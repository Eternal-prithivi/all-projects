"""Signup trust: disposable email blocking and optional CAPTCHA verification."""

from __future__ import annotations

import os
from typing import Optional

from fastapi import HTTPException

# Common disposable domains — extend via DISPOSABLE_EMAIL_DOMAINS env (comma-separated)
_BUILTIN_DISPOSABLE = frozenset(
    {
        "mailinator.com",
        "guerrillamail.com",
        "tempmail.com",
        "10minutemail.com",
        "throwaway.email",
        "yopmail.com",
        "trashmail.com",
        "getnada.com",
        "sharklasers.com",
    }
)


def _disposable_domains() -> frozenset[str]:
    extra = os.getenv("DISPOSABLE_EMAIL_DOMAINS", "")
    domains = set(_BUILTIN_DISPOSABLE)
    for part in extra.split(","):
        d = part.strip().lower()
        if d:
            domains.add(d)
    return frozenset(domains)


def is_disposable_email(email: str) -> bool:
    if not email or "@" not in email:
        return False
    domain = email.split("@")[-1].lower().strip()
    return domain in _disposable_domains()


def assert_email_allowed(email: str) -> None:
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email address")
    if is_disposable_email(email):
        raise HTTPException(
            status_code=400,
            detail="Disposable email addresses are not allowed. Use a permanent email.",
        )


def verify_turnstile_token(token: Optional[str], remote_ip: Optional[str] = None) -> None:
    """Verify Cloudflare Turnstile when TURNSTILE_SECRET_KEY is configured."""
    secret = os.getenv("TURNSTILE_SECRET_KEY", "").strip()
    if not secret:
        return
    if not token:
        raise HTTPException(status_code=400, detail="CAPTCHA verification required")
    try:
        import httpx
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="CAPTCHA verification unavailable") from exc

    payload = {"secret": secret, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip
    with httpx.Client(timeout=10.0) as client:
        res = client.post("https://challenges.cloudflare.com/turnstile/v0/siteverify", data=payload)
    data = res.json()
    if not data.get("success"):
        raise HTTPException(status_code=400, detail="CAPTCHA verification failed")


def email_verification_required() -> bool:
    """
    Whether new signups must verify inbox before login / platform cloud use.

    Precedence: REQUIRE_EMAIL_VERIFICATION env > platform_settings flag > env default.
    """
    from app.utils.config import settings

    explicit = getattr(settings, "REQUIRE_EMAIL_VERIFICATION", None)
    if explicit is not None:
        return bool(explicit)

    from app.database.mongo_client import get_database

    doc = get_database()["platform_settings"].find_one({"_id": "platform_config"}) or {}
    if "require_email_verification" in doc:
        return bool(doc["require_email_verification"])

    env = (getattr(settings, "ENVIRONMENT", None) or os.getenv("ENVIRONMENT", "development")).lower()
    return env in ("production", "staging")
