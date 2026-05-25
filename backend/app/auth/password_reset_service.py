"""Password reset via email link or SMS OTP — uses profile recovery contacts only."""

import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal, Optional, Tuple

from app.database.mongo_client import get_database
from app.auth.auth_utils import get_password_hash
from app.contact.email_service import EmailService
from app.utils.sms_notifications import (
    check_sms_route_compatible,
    is_sms_configured,
    send_sms_detailed,
)
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

RESET_COLLECTION = "password_reset_requests"
EMAIL_TOKEN_HOURS = 1
SMS_OTP_MINUTES = 10
MAX_SMS_ATTEMPTS = 5

GENERIC_MESSAGE = (
    "If an account exists and the details match our records, you will receive reset instructions shortly."
)


@dataclass
class ForgotPasswordResult:
    sent: bool
    account_matched: bool
    hint: Optional[str] = None


def _hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def normalize_phone_e164(phone: str) -> Optional[str]:
    """
    Normalize to E.164 for Twilio. Requires +country code or 10-digit IN mobile.
    """
    if not phone or not phone.strip():
        return None

    raw = phone.strip()
    if raw.startswith("+"):
        digits = re.sub(r"\D", "", raw)
        if len(digits) >= 10:
            return f"+{digits}"
        return None

    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        return f"+91{digits}"
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return None


def _find_user_by_identifier(identifier: str) -> Optional[dict]:
    """Look up user by username, primary email, or recovery email."""
    users = get_database()["users"]
    identifier = identifier.strip()
    if not identifier:
        return None

    if "@" in identifier:
        normalized = _normalize_email(identifier)
        return users.find_one(
            {
                "$or": [
                    {"email": {"$regex": f"^{re.escape(identifier)}$", "$options": "i"}},
                    {"recovery_email": {"$regex": f"^{re.escape(identifier)}$", "$options": "i"}},
                ]
            }
        )

    return users.find_one({"username": identifier})


def identifier_matches_account(user: dict, identifier: str) -> bool:
    """
    Ensure the value typed on forgot-password belongs to this account.
    Prevents sending resets to a random email that isn't on file.
    """
    ident = identifier.strip()
    if not ident:
        return False

    username = user.get("username", "")
    primary_email = _normalize_email(user.get("email", "") or "")
    recovery_email = _normalize_email(user.get("recovery_email", "") or "")

    if "@" in ident:
        typed = _normalize_email(ident)
        allowed = {primary_email}
        if recovery_email:
            allowed.add(recovery_email)
        return typed in allowed

    return ident.lower() == username.lower()


def _get_password_reset_email_destination(user: dict) -> Optional[str]:
    """Recovery email is used for reset when set; otherwise primary registration email."""
    recovery = (user.get("recovery_email") or "").strip()
    if recovery:
        return recovery
    return (user.get("email") or "").strip() or None


def _get_sms_destination_phone(user: dict) -> Optional[str]:
    """Primary mobile first, then alternate recovery mobile."""
    for field in ("phone", "recovery_phone"):
        raw = (user.get(field) or "").strip()
        if not raw:
            continue
        normalized = normalize_phone_e164(raw)
        if normalized:
            return normalized
        logger.warning(
            f"User {user.get('username')}: invalid phone format in '{field}' — use +country code (e.g. +919876543210)"
        )
    return None


def request_password_reset_email(identifier: str, frontend_url: str) -> ForgotPasswordResult:
    user = _find_user_by_identifier(identifier)
    if not user:
        return ForgotPasswordResult(sent=False, account_matched=False)

    if not identifier_matches_account(user, identifier):
        return ForgotPasswordResult(
            sent=False,
            account_matched=True,
            hint=(
                "That address doesn't match this account. Use your registered email, "
                "recovery email (from Profile), or your username."
            ),
        )

    dest_email = _get_password_reset_email_destination(user)
    if not dest_email:
        return ForgotPasswordResult(
            sent=False,
            account_matched=True,
            hint="No email on file. Add a recovery email under Profile → Password recovery.",
        )

    token = secrets.token_urlsafe(32)
    token_hash = _hash_value(token)
    now = datetime.utcnow()

    coll = get_database()[RESET_COLLECTION]
    coll.delete_many({"username": user["username"], "method": "email"})
    coll.insert_one(
        {
            "username": user["username"],
            "method": "email",
            "token_hash": token_hash,
            "expires_at": now + timedelta(hours=EMAIL_TOKEN_HOURS),
            "used": False,
            "created_at": now,
            "target": dest_email,
        }
    )

    reset_link = f"{frontend_url.rstrip('/')}/reset-password?token={token}"
    email_service = EmailService()
    sent = email_service.send_password_reset(
        to_email=dest_email,
        username=user["username"],
        reset_link=reset_link,
        expires_hours=EMAIL_TOKEN_HOURS,
    )
    if sent:
        logger.info(f"Password reset email sent to {dest_email} for user {user['username']}")
        return ForgotPasswordResult(sent=True, account_matched=True)

    logger.error(f"Password reset email failed for user {user['username']}")
    return ForgotPasswordResult(
        sent=False,
        account_matched=True,
        hint="Could not send email. Check Gmail settings on the server or try SMS if you have a mobile number on file.",
    )


def request_password_reset_sms(identifier: str) -> ForgotPasswordResult:
    user = _find_user_by_identifier(identifier)
    if not user:
        return ForgotPasswordResult(sent=False, account_matched=False)

    if not identifier_matches_account(user, identifier):
        return ForgotPasswordResult(
            sent=False,
            account_matched=True,
            hint=(
                "That address doesn't match this account. Use your registered email, "
                "recovery email, or username — then we text the mobile saved on your Profile."
            ),
        )

    if not is_sms_configured():
        return ForgotPasswordResult(
            sent=False,
            account_matched=True,
            hint=(
                "SMS reset is not configured on this server (Twilio missing in .env). "
                "Use the email link option, or ask your administrator to set TWILIO_* variables."
            ),
        )

    phone = _get_sms_destination_phone(user)
    if not phone:
        return ForgotPasswordResult(
            sent=False,
            account_matched=True,
            hint=(
                "No valid mobile number on your profile. Open Profile → Password recovery and add "
                "Mobile number (use +country code, e.g. +919876543210). Optionally add an alternate mobile."
            ),
        )

    otp = f"{secrets.randbelow(1_000_000):06d}"
    otp_hash = _hash_value(otp)
    now = datetime.utcnow()

    coll = get_database()[RESET_COLLECTION]
    coll.delete_many({"username": user["username"], "method": "sms"})
    coll.insert_one(
        {
            "username": user["username"],
            "method": "sms",
            "token_hash": otp_hash,
            "expires_at": now + timedelta(minutes=SMS_OTP_MINUTES),
            "used": False,
            "attempts": 0,
            "created_at": now,
            "target": phone[-4:],  # last 4 digits only for audit
        }
    )

    route_hint = check_sms_route_compatible(phone)
    if route_hint:
        return ForgotPasswordResult(sent=False, account_matched=True, hint=route_hint)

    message = (
        f"[Zenith] Your password reset code is {otp}. "
        f"It expires in {SMS_OTP_MINUTES} minutes. Do not share this code."
    )
    sms_result = send_sms_detailed(phone, message)
    if sms_result.success:
        logger.info(f"Password reset SMS sent to {phone[:4]}*** for user {user['username']}")
        return ForgotPasswordResult(sent=True, account_matched=True)

    logger.error(f"Password reset SMS failed for user {user['username']} to {phone[:4]}***")
    return ForgotPasswordResult(
        sent=False,
        account_matched=True,
        hint=sms_result.user_hint or "SMS could not be delivered. Try the email reset link instead.",
    )


def _get_valid_reset_record(
    *,
    method: Literal["email", "sms"],
    secret: str,
    username: Optional[str] = None,
) -> Tuple[Optional[dict], Optional[str]]:
    coll = get_database()[RESET_COLLECTION]
    secret_hash = _hash_value(secret)

    query = {"method": method, "token_hash": secret_hash, "used": False}
    if username and method == "sms":
        query["username"] = username

    record = coll.find_one(query)
    if not record:
        return None, "Invalid or expired reset request. Please request a new one."

    if record.get("expires_at") and record["expires_at"] < datetime.utcnow():
        return None, "This reset link or code has expired. Please request a new one."

    if method == "sms":
        attempts = record.get("attempts", 0)
        if attempts >= MAX_SMS_ATTEMPTS:
            return None, "Too many attempts. Please request a new code."

    return record, None


def complete_password_reset(
    *,
    new_password: str,
    method: Literal["email", "sms"],
    token: Optional[str] = None,
    otp: Optional[str] = None,
    identifier: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    if len(new_password) < 8:
        return False, "Password must be at least 8 characters."

    secret = token if method == "email" else otp
    if not secret:
        return False, "Missing reset token or code."

    username = None
    if method == "sms":
        if not identifier:
            return False, "Email or username is required when using SMS code."
        user = _find_user_by_identifier(identifier)
        if not user or not identifier_matches_account(user, identifier):
            return False, "Invalid or expired reset code."
        username = user["username"]

    record, err = _get_valid_reset_record(method=method, secret=secret, username=username)
    if err:
        if method == "sms" and record is None and identifier:
            coll = get_database()[RESET_COLLECTION]
            user = _find_user_by_identifier(identifier)
            if user:
                coll.update_one(
                    {"username": user["username"], "method": "sms", "used": False},
                    {"$inc": {"attempts": 1}},
                )
        return False, err

    users = get_database()["users"]
    new_hash = get_password_hash(new_password)
    users.update_one(
        {"username": record["username"]},
        {
            "$set": {"hashed_password": new_hash, "updated_at": datetime.utcnow()},
            "$unset": {"password": ""},
        },
    )

    coll = get_database()[RESET_COLLECTION]
    coll.update_one({"_id": record["_id"]}, {"$set": {"used": True, "used_at": datetime.utcnow()}})

    activity = get_database()["activity_log"]
    activity.insert_one(
        {
            "username": record["username"],
            "action": "Password Reset",
            "description": f"Password reset completed via {method}",
            "timestamp": datetime.utcnow(),
            "ip": "system",
        }
    )

    logger.info(f"Password reset completed for {record['username']} via {method}")
    return True, None
