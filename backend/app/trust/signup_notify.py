"""Notify platform owner when a new account is created."""

from datetime import datetime
from typing import Optional

from app.contact.email_service import EmailService
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def notify_new_user_signup(
    *,
    username: str,
    email: str,
    source: str,
    created_by: Optional[str] = None,
) -> None:
    """Best-effort admin alert; never raises."""
    try:
        EmailService().send_new_user_signup_notification(
            username=username,
            email=email,
            source=source,
            created_at=datetime.utcnow(),
            created_by=created_by,
        )
    except Exception as exc:
        logger.warning("Signup notification failed for %s: %s", username, exc)
