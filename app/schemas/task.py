"""
Task Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TaskBase(BaseModel):
    """Base task schema with common fields."""
    title: str = Field(..., min_length=1, max_length=255, description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    deadline: Optional[datetime] = Field(None, description="Expected deadline")
    priority: str = Field(default="medium", description="Priority: low, medium, high, urgent")
    deliverables: Optional[Dict[str, Any]] = Field(None, description="Expected deliverables")


class TaskCreate(TaskBase):
    """Schema for creating a new task."""
    lead_dept_id: int = Field(..., description="Lead department ID")


class TaskUpdate(BaseModel):
    """Schema for updating a task."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    priority: Optional[str] = None
    deliverables: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class TaskResponse(TaskBase):
    """Schema for task response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_dept_id: int
    status: str
    created_by: int
    created_at: datetime
    updated_at: datetime
    is_deleted: bool


class TaskDetail(TaskResponse):
    """Detailed task response with related info."""
    lead_dept_name: Optional[str] = None
    creator_name: Optional[str] = None
    assignments: List["AssignmentResponse"] = []
    conflict_count: int = 0


class TaskListResponse(BaseModel):
    """Schema for task list with pagination."""
    items: List[TaskResponse]
    total: int
    page: int
    page_size: int
    pages: int


# Import for type hint
from app.schemas.assignment import AssignmentResponse

TaskDetail.model_rebuild()
