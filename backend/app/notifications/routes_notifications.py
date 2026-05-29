from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.auth_utils import get_current_user
from app.notifications import service as notification_service
from app.users.user_model import UserInDB

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class CreateNotificationBody(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=2000)
    type: str = Field(default="info")
    link: Optional[str] = None


@router.post("")
def create_notification(
    body: CreateNotificationBody,
    current_user: UserInDB = Depends(get_current_user),
):
    nid = notification_service.create_notification(
        current_user.username,
        title=body.title,
        message=body.message,
        type=body.type,
        link=body.link,
    )
    return {"id": nid, "success": True}


@router.get("")
def list_my_notifications(current_user: UserInDB = Depends(get_current_user)):
    items = notification_service.list_notifications(current_user.username)
    unread = sum(1 for n in items if not n["read"])
    return {"notifications": items, "unread_count": unread}


@router.patch("/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    current_user: UserInDB = Depends(get_current_user),
):
    if not notification_service.mark_read(current_user.username, notification_id):
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"success": True}


@router.post("/mark-all-read")
def mark_all_notifications_read(current_user: UserInDB = Depends(get_current_user)):
    count = notification_service.mark_all_read(current_user.username)
    return {"success": True, "updated": count}


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: str,
    current_user: UserInDB = Depends(get_current_user),
):
    if not notification_service.delete_notification(current_user.username, notification_id):
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"success": True}


@router.delete("")
def clear_notifications(current_user: UserInDB = Depends(get_current_user)):
    count = notification_service.clear_all(current_user.username)
    return {"success": True, "deleted": count}
