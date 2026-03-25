"""
Reminder Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ReminderBase(BaseModel):
    """Base reminder schema with common fields."""
    trigger_type: str = Field(default="immediate", description="Trigger type: immediate, scheduled, condition")
    trigger_time: datetime = Field(..., description="When to trigger the reminder")
    reminder_methods: Optional[Dict[str, Any]] = Field(None, description="Reminder methods")


class ReminderCreate(ReminderBase):
    """Schema for creating a new reminder."""
    target_user_id: int = Field(..., description="Target user ID")
    memo_id: int = Field(..., description="Related memo ID")


class ReminderUpdate(BaseModel):
    """Schema for updating a reminder."""
    trigger_time: Optional[datetime] = None
    reminder_methods: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class ReminderResponse(ReminderBase):
    """Schema for reminder response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    target_user_id: int
    memo_id: int
    status: str
    retry_count: int
    last_sent_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ReminderDetail(ReminderResponse):
    """Detailed reminder response with related info."""
    target_user_name: Optional[str] = None
    memo_title: Optional[str] = None


class ReminderTest(BaseModel):
    """Schema for testing reminder sending."""
    user_id: int = Field(..., description="Target user ID")
    method: str = Field(default="in_app", description="Reminder method: in_app, email, wechat, sms")
    message: Optional[str] = Field(None, description="Custom message")


class ReminderListResponse(BaseModel):
    """Schema for reminder list with pagination."""
    items: List[ReminderResponse]
    total: int
    page: int
    page_size: int
    pages: int
