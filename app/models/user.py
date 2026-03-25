"""
User model for authentication and authorization.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """
    User model representing system users.

    Attributes:
        id: Unique identifier
        name: User's full name
        dept_id: Department ID the user belongs to
        role: User role (leader/dept_head/member)
        email: User's email address
        phone: User's phone number
        created_by: ID of user who created this user
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="User's full name")
    dept_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Department ID"
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="member",
        comment="User role: leader, dept_head, or member"
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="User email address"
    )
    phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="User phone number"
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Creator user ID"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Soft delete timestamp"
    )
    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relationships
    department = relationship("Department", back_populates="users", foreign_keys=[dept_id])
    created_tasks = relationship("Task", back_populates="creator", foreign_keys="Task.created_by")
    created_memos = relationship("Memo", back_populates="leader")
    reminders = relationship("Reminder", back_populates="target_user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name='{self.name}', role='{self.role}')>"
