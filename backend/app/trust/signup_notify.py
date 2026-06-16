"""Notify platform owner when a new account is created."""

import os
from datetime import datetime
from typing import Optional

from app.contact.email_service import EmailService
from app.trust.signup_guards import is_test_environment, is_test_signup_email
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
    if is_test_environment():
        logger.debug("Skipping signup notify in test environment for %s", username)
        return

    notify_to: Optional[str] = None
    if is_test_signup_email(email):
        test_inbox = os.getenv("TEST_SIGNUP_NOTIFY_EMAIL", "").strip()
        if not test_inbox:
            logger.debug("Skipping signup notify for test address %s", email)
            return
        notify_to = test_inbox

    try:
        EmailService().send_new_user_signup_notification(
            username=username,
            email=email,
            source=source,
            created_at=datetime.utcnow(),
            created_by=created_by,
            to_email=notify_to,
        )
    except Exception as exc:
        logger.warning("Signup notification failed for %s: %s", username, exc)
