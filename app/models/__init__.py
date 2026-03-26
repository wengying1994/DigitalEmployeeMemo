"""
Database models package.
All models are exported here for easy imports.
"""
from app.models.department import Department
from app.models.message import Message
from app.models.user import User

__all__ = [
    # User
    "User",
    # Department
    "Department",
    # Message
    "Message",
]
