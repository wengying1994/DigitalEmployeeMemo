"""
User Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema with common fields."""
    name: str = Field(..., min_length=1, max_length=100, description="User's full name")
    email: EmailStr = Field(..., description="User email address")
    phone: Optional[str] = Field(None, max_length=20, description="User phone number")
    dept_id: Optional[int] = Field(None, description="Department ID")


class UserCreate(UserBase):
    """Schema for creating a new user."""
    role: str = Field(default="member", description="User role: leader, dept_head, member")
    created_by: Optional[int] = Field(None, description="Creator user ID")


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    dept_id: Optional[int] = None
    role: Optional[str] = None


class UserResponse(UserBase):
    """Schema for user response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    created_at: datetime
    updated_at: datetime


class UserBrief(BaseModel):
    """Brief user info for embedding in other responses."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: str
    dept_id: Optional[int] = None
