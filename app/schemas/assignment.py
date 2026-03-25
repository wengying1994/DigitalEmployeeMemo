"""
Assignment Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AssignmentBase(BaseModel):
    """Base assignment schema with common fields."""
    dept_id: int = Field(..., description="Assigned department ID")
    assigned_tasks: Optional[Dict[str, Any]] = Field(None, description="Task items")
    deadline: Optional[datetime] = Field(None, description="Assignment deadline")
    dependencies: Optional[Dict[str, Any]] = Field(None, description="Dependencies")
    resources_needed: Optional[Dict[str, Any]] = Field(None, description="Resources needed")


class AssignmentCreate(AssignmentBase):
    """Schema for creating a new assignment."""
    task_id: int = Field(..., description="Parent task ID")


class AssignmentUpdate(BaseModel):
    """Schema for updating an assignment."""
    assigned_tasks: Optional[Dict[str, Any]] = None
    deadline: Optional[datetime] = None
    dependencies: Optional[Dict[str, Any]] = None
    resources_needed: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class AssignmentResponse(AssignmentBase):
    """Schema for assignment response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    status: str
    created_at: datetime
    updated_at: datetime


class AssignmentDetail(AssignmentResponse):
    """Detailed assignment response with related info."""
    dept_name: Optional[str] = None
    task_title: Optional[str] = None
    feedbacks: List["FeedbackResponse"] = []


class AssignmentListResponse(BaseModel):
    """Schema for assignment list with pagination."""
    items: List[AssignmentResponse]
    total: int
    page: int
    page_size: int
    pages: int


# Import for type hint
from app.schemas.feedback import FeedbackResponse

AssignmentDetail.model_rebuild()
