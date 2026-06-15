from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr

from app.admin.routes_admin import verify_admin
from jose import JWTError, jwt

from app.database.mongo_client import get_users_collection
from app.utils.config import settings
from app.support import service as support_service
from app.users.user_model import UserInDB
from app.utils.logger import setup_logger
from ..database.mongo_client import get_database
from .email_service import email_service

optional_bearer = HTTPBearer(auto_error=False)

logger = setup_logger(__name__)
router = APIRouter(prefix="/api/contact", tags=["contact"])
contact_limiter = Limiter(key_func=get_remote_address)
DB = get_database()


class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str


def _optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_bearer),
) -> Optional[UserInDB]:
    if not credentials:
        return None
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        username = payload.get("sub")
        if not username:
            return None
        user_data = get_users_collection().find_one({"username": username})
        if not user_data:
            return None
        return UserInDB(**user_data)
    except JWTError:
        return None


@router.post("/submit")
@contact_limiter.limit("3/hour")
async def submit_contact_form(
    request: Request,
    contact: ContactRequest,
    current_user: Optional[UserInDB] = Depends(_optional_user),
):
    """
    Submit a contact form message — creates a support ticket + first message.
    """
    try:
        legacy_submission = {
            "name": contact.name,
            "email": contact.email,
            "subject": contact.subject,
            "message": contact.message,
            "timestamp": datetime.utcnow(),
            "status": "unread",
            "replied": False,
        }
        legacy_result = DB["contact_submissions"].insert_one(legacy_submission)

        user_id = current_user.username if current_user else None
        ticket = support_service.create_ticket_from_contact(
            name=contact.name,
            email=str(contact.email),
            subject=contact.subject,
            message=contact.message,
            user_id=user_id,
            legacy_submission_id=legacy_result.inserted_id,
        )

        ref_code = ticket.get("reference_code")
        if ref_code:
            DB["contact_submissions"].update_one(
                {"_id": legacy_result.inserted_id},
                {"$set": {"reference_code": ref_code, "ticket_id": str(ticket["_id"])}},
            )

        email_payload = support_service.ticket_to_email_submission(
            ticket, contact.message
        )

        try:
            email_service.send_contact_notification(email_payload)
            email_service.send_auto_reply(email_payload)
        except Exception as email_error:
            logger.warning(f"Email notification failed (non-critical): {email_error}")

        return {
            "success": True,
            "message": "Thank you for contacting us! We'll respond within 24 hours.",
            "submission_id": str(legacy_result.inserted_id),
            "ticket_id": str(ticket["_id"]),
            "reference_code": ref_code,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit contact form: {str(e)}")


@router.get("/admin/submissions")
async def get_contact_submissions(
    limit: int = 50,
    admin_user=Depends(verify_admin),
):
    """Legacy submissions list — admin only. Prefer /api/admin/support/tickets."""
    try:
        submissions = list(
            DB["contact_submissions"]
            .find()
            .sort("timestamp", -1)
            .limit(limit)
        )

        for submission in submissions:
            submission["_id"] = str(submission["_id"])
            submission["timestamp"] = submission["timestamp"].isoformat()

        return {
            "total": len(submissions),
            "submissions": submissions,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch submissions: {str(e)}")
