"""
Pydantic schemas package.
All schemas are exported here for easy imports.
"""
from app.schemas.message import (
    MessageCreate,
    MessageUpdate,
    MessageResponse,
    MessageDetail,
    MessageListResponse,
)
from app.schemas.user import UserBase, UserCreate, UserResponse, UserUpdate, UserBrief

__all__ = [
    # User
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserBrief",
    # Message
    "MessageCreate",
    "MessageUpdate",
    "MessageResponse",
    "MessageDetail",
    "MessageListResponse",
]
