from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
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


class UpdateNotificationBody(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    message: Optional[str] = Field(default=None, min_length=1, max_length=2000)
    type: Optional[str] = None
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
def list_my_notifications(
    limit: int = Query(20, ge=5, le=50),
    skip: int = Query(0, ge=0),
    read: str = Query("all"),
    type: str = Query("all"),
    current_user: UserInDB = Depends(get_current_user),
):
    if read not in ("all", "unread", "read"):
        raise HTTPException(status_code=400, detail="read must be all, unread, or read")
    items, total, unread = notification_service.list_notifications_paginated(
        current_user.username,
        limit=limit,
        skip=skip,
        read_filter=read,
        type_filter=type,
    )
    return {
        "notifications": items,
        "total": total,
        "unread_count": unread,
        "limit": limit,
        "skip": skip,
        "has_more": (skip + limit) < total,
        "read": read,
        "type": type,
    }


@router.get("/recent")
def list_recent_notifications(
    limit: int = Query(8, ge=1, le=20),
    current_user: UserInDB = Depends(get_current_user),
):
    items, unread = notification_service.list_recent_notifications(
        current_user.username,
        limit=limit,
    )
    return {"notifications": items, "unread_count": unread}


@router.patch("/{notification_id}")
def update_notification(
    notification_id: str,
    body: UpdateNotificationBody,
    current_user: UserInDB = Depends(get_current_user),
):
    if not notification_service.update_notification(
        current_user.username,
        notification_id,
        title=body.title,
        message=body.message,
        type=body.type,
        link=body.link,
    ):
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"success": True}


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
