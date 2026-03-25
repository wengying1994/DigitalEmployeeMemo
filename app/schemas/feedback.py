"""
Feedback Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class FeedbackBase(BaseModel):
    """Base feedback schema with common fields."""
    feedback_type: str = Field(..., description="Feedback type: agree, disagree, need_discussion")
    reason: Optional[str] = Field(None, description="Reason for feedback")
    proposed_changes: Optional[Dict[str, Any]] = Field(None, description="Proposed changes")
    attachments: Optional[Dict[str, Any]] = Field(None, description="Attachments")


class FeedbackCreate(FeedbackBase):
    """Schema for creating a new feedback."""
    assignment_id: int = Field(..., description="Related assignment ID")


class FeedbackResponse(FeedbackBase):
    """Schema for feedback response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    assignment_id: int
    dept_id: int
    created_at: datetime
    updated_at: datetime


class FeedbackDetail(FeedbackResponse):
    """Detailed feedback response with related info."""
    dept_name: Optional[str] = None
    assignment_task_title: Optional[str] = None


class FeedbackListResponse(BaseModel):
    """Schema for feedback list with pagination."""
    items: List[FeedbackResponse]
    total: int
    page: int
    page_size: int
    pages: int
