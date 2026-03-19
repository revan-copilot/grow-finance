"""
Pydantic schemas for notifications.
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class NotificationBase(BaseModel):
    """
    Base schema for notifications.
    """
    type: str
    title: str
    message: str
    link: Optional[str] = None

class NotificationRead(NotificationBase):
    """
    Schema for reading a notification.
    """
    id: int
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class NotificationUpdate(BaseModel):
    """
    Schema for updating a notification (e.g., marking as read).
    """
    is_read: bool

class NotificationList(BaseModel):
    """
    Schema for a list of notifications with unread count.
    """
    data: List[NotificationRead]
    unread_count: int
