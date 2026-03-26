"""
Message Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class MessageBase(BaseModel):
    """Base message schema with common fields."""
    title: str = Field(..., min_length=1, max_length=255, description="Message title")
    content: str = Field(..., min_length=1, description="Message content")
    receiver_id: Optional[int] = Field(None, description="Receiver user ID (null for broadcast)")


class MessageCreate(MessageBase):
    """Schema for creating a new message."""
    pass


class MessageUpdate(BaseModel):
    """Schema for updating a message."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = Field(None, min_length=1)


class MessageResponse(MessageBase):
    """Schema for message response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender_id: int
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class MessageDetail(MessageResponse):
    """Detailed message response with user info."""
    sender_name: Optional[str] = None
    receiver_name: Optional[str] = None


class MessageListResponse(BaseModel):
    """Schema for message list with pagination."""
    items: List[MessageResponse]
    total: int
    page: int
    page_size: int
    pages: int
