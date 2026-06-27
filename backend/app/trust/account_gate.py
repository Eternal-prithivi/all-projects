"""
Unified account health gate for resource-creating APIs.

Blocks suspended/banned users, expired subscriptions, unverified email (platform cloud),
and platform budget circuit breaker trips.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException

from app.billing.platform_spend import assert_platform_budget_available
from app.database.mongo_client import get_database
from app.payments.subscription_service import get_effective_plan_id, get_user_subscription
from app.trust.signup_guards import email_verification_required
from app.auth.auth_utils import get_current_user
from app.users.user_model import User, UserInDB
from app.utils.config import settings


def _platform_settings() -> dict:
    return get_database()["platform_settings"].find_one({"_id": "platform_config"}) or {}


def _owner_usernames() -> set[str]:
    raw = getattr(settings, "PLATFORM_OWNER_USERNAMES", "") or ""
    return {u.strip() for u in raw.split(",") if u.strip()}


def assert_account_active(user: User) -> None:
    users = get_database()["users"]
    doc = users.find_one({"username": user.username}) or {}
    status = (doc.get("status") or "active").lower()
    if status in ("suspended", "banned"):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "ACCOUNT_SUSPENDED",
                "message": f"Account is {status}. Contact support.",
            },
        )
    if doc.get("deleted") or status == "deleted":
        raise HTTPException(status_code=401, detail="Account not found")


def assert_subscription_allows_usage(username: str) -> None:
    if username in _owner_usernames():
        return
    sub = get_user_subscription(username)
    status = (sub.get("status") or "active").lower()
    plan_id = get_effective_plan_id(username)
    if plan_id == "free":
        return
    period_end = sub.get("current_period_end")
    if period_end and isinstance(period_end, datetime) and datetime.utcnow() > period_end:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "SUBSCRIPTION_EXPIRED",
                "message": "Subscription expired. Renew or downgrade to free tier.",
            },
        )
    if status in ("past_due", "canceled") and period_end:
        grace_days = int(getattr(settings, "SUBSCRIPTION_GRACE_DAYS", 3) or 3)
        if isinstance(period_end, datetime):
            grace_end = period_end
            from datetime import timedelta

            grace_end = period_end + timedelta(days=grace_days)
            if datetime.utcnow() > grace_end:
                raise HTTPException(
                    status_code=402,
                    detail={
                        "code": "SUBSCRIPTION_EXPIRED",
                        "message": "Payment overdue. Update billing to continue.",
                    },
                )


def assert_email_verified_for_platform(username: str, email_verified: bool) -> None:
    if username in _owner_usernames():
        return
    if not email_verification_required():
        return
    if not email_verified:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "VERIFICATION_REQUIRED",
                "message": "Verify your email before using platform cloud resources.",
            },
        )


def assert_maintenance_allows_writes(user: User) -> None:
    plat = _platform_settings()
    if not plat.get("maintenance_mode"):
        return
    role = getattr(user, "role", None) or "user"
    if role == "admin":
        return
    raise HTTPException(
        status_code=503,
        detail={
            "code": "MAINTENANCE_MODE",
            "message": "Platform is in maintenance mode. Try again later.",
        },
    )


def require_healthy_account(
    user: User = Depends(get_current_user),
) -> User:
    assert_account_active(user)
    assert_maintenance_allows_writes(user)
    return user


def require_platform_resource_access(
    user: User = Depends(get_current_user),
) -> User:
    """Gate VM, storage upload, and provision on platform or BYOC resources."""
    require_healthy_account(user)
    assert_subscription_allows_usage(user.username)
    users_col = get_database()["users"]
    doc = users_col.find_one({"username": user.username}, {"email_verified": 1}) or {}
    assert_email_verified_for_platform(user.username, bool(doc.get("email_verified", True)))
    assert_platform_budget_available(user.username)
    return user


def _assert_admin_portal_access(user: UserInDB) -> None:
    """Shared admin-portal gate: role, production 2FA enrollment, session 2FA verify."""
    role = getattr(user, "role", None)
    if role != "admin":
        raise HTTPException(
            status_code=403,
            detail={
                "code": "ADMIN_REQUIRED",
                "message": "Access denied. Admin privileges required.",
            },
        )

    username = getattr(user, "username", "") or ""
    is_owner = username in _owner_usernames()
    if is_owner:
        return

    two_fa_enabled = bool(getattr(user, "two_fa_enabled", False))
    two_fa_verified = bool(getattr(user, "two_fa_verified", False))
    env = (getattr(settings, "ENVIRONMENT", "development") or "development").lower()

    if env == "production" and not is_owner and not two_fa_enabled:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "ADMIN_2FA_REQUIRED",
                "message": "Platform admins must enable two-factor authentication in Settings.",
                "setup_path": "/dashboard/security-settings",
            },
        )

    if two_fa_enabled and not two_fa_verified:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "ADMIN_2FA_VERIFY",
                "message": "Complete two-factor authentication to access the admin portal.",
                "setup_path": "/dashboard/security-settings",
            },
        )


def require_admin_for_portal(
    user: UserInDB = Depends(get_current_user),
) -> UserInDB:
    _assert_admin_portal_access(user)
    return user


def require_admin_with_2fa(
    user: UserInDB = Depends(get_current_user),
) -> UserInDB:
    """Legacy alias — same gate as admin portal routes."""
    _assert_admin_portal_access(user)
    return user
