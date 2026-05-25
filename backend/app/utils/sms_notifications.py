"""Twilio SMS helpers with clear errors for geo / sender mismatches."""

import os
import logging
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

load_dotenv()

logger = logging.getLogger(__name__)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = (os.getenv("TWILIO_PHONE_NUMBER") or "").strip()
TWILIO_MESSAGING_SERVICE_SID = (os.getenv("TWILIO_MESSAGING_SERVICE_SID") or "").strip()


@dataclass
class SmsSendResult:
    success: bool
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    user_hint: Optional[str] = None


def is_sms_configured() -> bool:
    """True when Twilio credentials and a sender (number or messaging service) are set."""
    has_sender = bool(TWILIO_PHONE_NUMBER or TWILIO_MESSAGING_SERVICE_SID)
    return bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and has_sender)


def _region_from_e164(phone: str) -> Optional[str]:
    """Rough region from E.164 prefix for compatibility checks."""
    if not phone or not phone.startswith("+"):
        return None
    if phone.startswith("+91"):
        return "IN"
    if phone.startswith("+1"):
        return "US"
    if phone.startswith("+44"):
        return "GB"
    if phone.startswith("+61"):
        return "AU"
    return "OTHER"


def _sender_region() -> Optional[str]:
    if TWILIO_MESSAGING_SERVICE_SID:
        return None  # Messaging Service handles routing; skip pre-check
    if TWILIO_PHONE_NUMBER:
        return _region_from_e164(TWILIO_PHONE_NUMBER)
    return None


def check_sms_route_compatible(to_phone: str) -> Optional[str]:
    """
    Return a user-facing hint when sender/recipient regions likely conflict (e.g. US → India).
    """
    sender = _sender_region()
    recipient = _region_from_e164(to_phone)
    if sender == "US" and recipient == "IN":
        return (
            "Your Twilio sender is a US number (+1) but the profile mobile is India (+91). "
            "In Twilio Console go to Messaging → Settings → Geo permissions and enable India, "
            "OR buy an Indian Twilio number and set TWILIO_PHONE_NUMBER to it (e.g. +91…). "
            "Trial accounts must also verify the recipient number under Phone Numbers → Verified Caller IDs."
        )
    return None


def _hint_for_twilio_error(code: Optional[int], message: str, to_phone: str) -> str:
    if code == 21659 or "country mismatch" in message.lower():
        geo_hint = check_sms_route_compatible(to_phone)
        if geo_hint:
            return geo_hint
        return (
            "Twilio rejected the SMS: the 'From' number is not valid for this destination. "
            "Use a Twilio number that matches the recipient country, or enable that country under "
            "Messaging → Geo permissions in Twilio Console."
        )
    if code == 21211:
        return "Invalid mobile number format. Use +country code on your Profile (e.g. +919876543210)."
    if code == 21608 or code == 21610:
        return (
            "This number is not verified on your Twilio trial account. Add it under "
            "Twilio Console → Phone Numbers → Verified Caller IDs, or upgrade the account."
        )
    return (
        "SMS could not be delivered. Check TWILIO_PHONE_NUMBER (must be a number you own in Twilio) "
        "or set TWILIO_MESSAGING_SERVICE_SID. Try email reset instead."
    )


def send_sms_detailed(to_phone: str, message: str) -> SmsSendResult:
    """Send SMS and return structured result with optional user_hint."""
    if not is_sms_configured():
        logger.warning(
            "Twilio not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and "
            "TWILIO_PHONE_NUMBER or TWILIO_MESSAGING_SERVICE_SID in backend/.env"
        )
        return SmsSendResult(
            success=False,
            user_hint="SMS is not configured on this server (missing Twilio env variables).",
        )

    route_hint = check_sms_route_compatible(to_phone)
    if route_hint:
        logger.warning(f"SMS route likely incompatible: {to_phone[:4]}*** — {route_hint[:80]}…")

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        create_kwargs = {"body": message, "to": to_phone}
        if TWILIO_MESSAGING_SERVICE_SID:
            create_kwargs["messaging_service_sid"] = TWILIO_MESSAGING_SERVICE_SID
        else:
            create_kwargs["from_"] = TWILIO_PHONE_NUMBER

        message_obj = client.messages.create(**create_kwargs)
        logger.info(f"SMS sent successfully to {to_phone}. SID: {message_obj.sid}")
        return SmsSendResult(success=True)

    except TwilioRestException as e:
        err_msg = e.msg or str(e)
        logger.error(f"Failed to send SMS to {to_phone}: [{e.code}] {err_msg}")
        return SmsSendResult(
            success=False,
            error_code=e.code,
            error_message=err_msg,
            user_hint=_hint_for_twilio_error(e.code, err_msg, to_phone),
        )
    except Exception as e:
        logger.error(f"Failed to send SMS to {to_phone}: {str(e)}")
        return SmsSendResult(
            success=False,
            error_message=str(e),
            user_hint=_hint_for_twilio_error(None, str(e), to_phone),
        )


def send_sms(to_phone: str, message: str) -> bool:
    """Send SMS notification using Twilio (bool wrapper for existing callers)."""
    return send_sms_detailed(to_phone, message).success


def send_budget_alert_sms(
    phone_number: str,
    budget_name: str,
    current_spend: float,
    budget_amount: float,
    utilization: float,
):
    threshold_amount = budget_amount * (utilization / 100)
    message = (
        f"[Zenith Cloud Platform] Budget Alert: '{budget_name}' has reached {utilization:.1f}% "
        f"utilization (${threshold_amount:.2f} threshold). Current spend: ${current_spend:.2f} "
        f"of ${budget_amount:.2f} allocated. Review your cloud resources to optimize costs."
    )
    return send_sms(phone_number, message)


def send_budget_exceeded_sms(
    phone_number: str,
    budget_name: str,
    current_spend: float,
    budget_amount: float,
):
    overage = current_spend - budget_amount
    message = (
        f"[Zenith Cloud Platform] URGENT: Budget '{budget_name}' exceeded! "
        f"Current spend: ${current_spend:.2f} | Budget limit: ${budget_amount:.2f} | "
        f"Overage: ${overage:.2f}. Immediate action recommended."
    )
    return send_sms(phone_number, message)
