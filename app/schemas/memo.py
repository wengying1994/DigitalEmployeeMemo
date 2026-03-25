"""
Memo Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class MemoBase(BaseModel):
    """Base memo schema with common fields."""
    title: str = Field(..., min_length=1, max_length=255, description="Memo title")
    content: Optional[Dict[str, Any]] = Field(None, description="Structured content")
    full_memo_text: Optional[str] = Field(None, description="Full memo text")
    memo_type: str = Field(default="info", description="Memo type: conflict, approval, info")


class MemoCreate(MemoBase):
    """Schema for creating a new memo."""
    user_id: int = Field(..., description="Leader user ID")
    related_id: Optional[int] = Field(None, description="Related entity ID")
    related_task_id: Optional[int] = Field(None, description="Related task ID")


class MemoUpdate(BaseModel):
    """Schema for updating a memo."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[Dict[str, Any]] = None
    full_memo_text: Optional[str] = None
    status: Optional[str] = None


class MemoReadStatusUpdate(BaseModel):
    """Schema for updating memo read status."""
    status: str = Field(..., description="Status: unread, read, resolved")


class MemoDecision(BaseModel):
    """Schema for making a decision on a memo (conflict)."""
    decision_content: str = Field(..., description="Decision content")
    notify_departments: Optional[List[int]] = Field(None, description="Department IDs to notify")


class MemoResponse(MemoBase):
    """Schema for memo response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    related_id: Optional[int] = None
    related_task_id: Optional[int] = None
    status: str
    read_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class MemoDetail(MemoResponse):
    """Detailed memo response with related info."""
    leader_name: Optional[str] = None
    task_title: Optional[str] = None
    conflict_id: Optional[int] = None
    reminders_count: int = 0


class MemoListResponse(BaseModel):
    """Schema for memo list with pagination."""
    items: List[MemoResponse]
    total: int
    page: int
    page_size: int
    pages: int


class LeaderDashboard(BaseModel):
    """Schema for leader dashboard statistics."""
    pending_memos_count: int = 0
    unread_memos_count: int = 0
    resolved_today_count: int = 0
    pending_conflicts_count: int = 0
    urgent_conflicts_count: int = 0
    tasks_in_progress_count: int = 0
    tasks_coordinating_count: int = 0
    tasks_near_deadline_count: int = 0
    recent_memos: List[MemoResponse] = []
    urgent_conflicts: List["ConflictResponse"] = []


# Import for type hint
from app.schemas.conflict import ConflictResponse

LeaderDashboard.model_rebuild()
