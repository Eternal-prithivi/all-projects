from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from datetime import datetime
from ..database.mongo_client import get_database
from .email_service import email_service
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/api/contact", tags=["contact"])
DB = get_database()

class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str

@router.post("/submit")
async def submit_contact_form(contact: ContactRequest):
    """
    Submit a contact form message.
    Stores the submission in MongoDB and sends email notifications.
    """
    try:
        # Store in MongoDB
        submission = {
            "name": contact.name,
            "email": contact.email,
            "subject": contact.subject,
            "message": contact.message,
            "timestamp": datetime.utcnow(),
            "status": "unread",
            "replied": False
        }
        
        result = DB["contact_submissions"].insert_one(submission)
        
        # Send email notifications (non-blocking - don't fail if email fails)
        try:
            # Send notification to admin
            email_service.send_contact_notification(submission)
            
            # Send auto-reply to user
            email_service.send_auto_reply(submission)
        except Exception as email_error:
            logger.warning(f"Email notification failed (non-critical): {email_error}")
        
        return {
            "success": True,
            "message": "Thank you for contacting us! We'll respond within 24 hours.",
            "submission_id": str(result.inserted_id)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit contact form: {str(e)}")

@router.get("/admin/submissions")
async def get_contact_submissions(limit: int = 50):
    """
    Get all contact form submissions (admin only).
    TODO: Add authentication/authorization
    """
    try:
        submissions = list(
            DB["contact_submissions"]
            .find()
            .sort("timestamp", -1)
            .limit(limit)
        )
        
        # Convert ObjectId to string for JSON serialization
        for submission in submissions:
            submission["_id"] = str(submission["_id"])
            submission["timestamp"] = submission["timestamp"].isoformat()
        
        return {
            "total": len(submissions),
            "submissions": submissions
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch submissions: {str(e)}")
