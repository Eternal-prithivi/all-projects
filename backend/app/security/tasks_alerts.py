from celery import shared_task
from datetime import datetime
from typing import Any, Dict, List

from app.database.mongo_client import get_database
from app.contact.email_service import EmailService
from app.utils.sms_notifications import send_sms
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


@shared_task(name="check_security_alerts")
def check_security_alerts() -> Dict[str, Any]:
    """
    Daily security alert pipeline (email + SMS).

    Sends alerts to users who have security alerts enabled in notification settings.
    Zero-cost friendly: uses Gmail SMTP + Twilio (if configured).
    """
    DB = get_database()
    users = DB["users"]
    secure_files = DB["secure_files"]
    activity = DB["activity_log"]

    email_service = EmailService()

    alerted_users: List[str] = []
    total_alerts_sent = 0

    cursor = users.find({}, {"username": 1, "email": 1, "phone": 1, "settings.notifications": 1})
    for user in cursor:
        username = user.get("username")
        if not username:
            continue

        notif = (user.get("settings", {}) or {}).get("notifications", {}) or {}
        if notif.get("security_alerts", True) is not True:
            continue

        count = secure_files.count_documents(
            {"owner_username": username, "is_sensitive": True, "is_encrypted": False}
        )
        if count <= 0:
            continue

        # Email
        to_email = user.get("email")
        email_ok = False
        if to_email:
            email_ok = email_service.send_security_alert(
                to_email=to_email,
                username=username,
                unencrypted_sensitive_count=int(count),
            )

        # SMS (optional)
        phone = user.get("phone")
        sms_ok = False
        if phone:
            sms_ok = send_sms(
                phone,
                f"[Zenith Security Alert] {count} sensitive file(s) not encrypted. Open Security page to protect your data.",
            )

        if email_ok or sms_ok:
            alerted_users.append(username)
            total_alerts_sent += 1

            activity.insert_one(
                {
                    "username": username,
                    "action": "Security Alert Sent",
                    "description": f"Sent security alert (email={email_ok}, sms={sms_ok}) for {count} unencrypted sensitive file(s).",
                    "timestamp": datetime.utcnow(),
                    "ip": "system",
                }
            )

    logger.info(f"Security alerts complete. Users alerted: {len(alerted_users)}")
    return {"success": True, "users_alerted": alerted_users, "alerts_sent": total_alerts_sent}

