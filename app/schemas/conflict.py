"""
Conflict Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ConflictBase(BaseModel):
    """Base conflict schema with common fields."""
    conflict_summary: str = Field(..., min_length=1, max_length=255, description="Brief summary")
    conflict_details: Optional[Dict[str, Any]] = Field(None, description="Detailed conflict info")
    proposed_solutions: Optional[Dict[str, Any]] = Field(None, description="Proposed solutions")
    urgency_level: str = Field(default="medium", description="Urgency: low, medium, high, critical")
    need_decision_by: Optional[datetime] = Field(None, description="Decision deadline")


class ConflictCreate(ConflictBase):
    """Schema for creating a new conflict report."""
    task_id: int = Field(..., description="Related task ID")


class ConflictUpdate(BaseModel):
    """Schema for updating a conflict report."""
    conflict_summary: Optional[str] = Field(None, min_length=1, max_length=255)
    conflict_details: Optional[Dict[str, Any]] = None
    proposed_solutions: Optional[Dict[str, Any]] = None
    urgency_level: Optional[str] = None
    need_decision_by: Optional[datetime] = None
    status: Optional[str] = None


class ConflictDecision(BaseModel):
    """Schema for making a decision on a conflict."""
    decision_content: str = Field(..., description="Decision content")
    solution_selected: Optional[Dict[str, Any]] = Field(None, description="Selected solution if any")
    notify_departments: Optional[List[int]] = Field(None, description="Department IDs to notify")


class ConflictResponse(ConflictBase):
    """Schema for conflict response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    reporter_user_id: int
    reporter_dept_id: int
    status: str
    decision_made_at: Optional[datetime] = None
    decision_content: Optional[str] = None
    decision_maker_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class ConflictDetail(ConflictResponse):
    """Detailed conflict response with related info."""
    task_title: Optional[str] = None
    reporter_user_name: Optional[str] = None
    reporter_dept_name: Optional[str] = None
    decision_maker_name: Optional[str] = None
    memo_id: Optional[int] = None


class ConflictListResponse(BaseModel):
    """Schema for conflict list with pagination."""
    items: List[ConflictResponse]
    total: int
    page: int
    page_size: int
    pages: int
