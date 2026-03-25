"""
Task model for project/task management.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class TaskStatus:
    """Task status constants."""
    COORDINATING = "coordinating"      # Coordinating between departments
    IN_PROGRESS = "in_progress"        # Task is being worked on
    COMPLETED = "completed"           # Task is completed
    CANCELLED = "cancelled"           # Task was cancelled


class TaskPriority:
    """Task priority constants."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Task(Base, TimestampMixin):
    """
    Task model representing projects/tasks assigned to departments.

    Attributes:
        id: Unique identifier
        title: Task title
        description: Task description
        lead_dept_id: The leading department responsible for coordination
        deadline: Expected delivery date
        priority: Task priority (low/medium/high/urgent)
        status: Current status (coordinating/in_progress/completed)
        deliverables: Expected deliverables (JSON)
        created_by: ID of user who created the task
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Task title"
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Task description"
    )
    lead_dept_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Lead department ID"
    )
    deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Expected deadline"
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TaskPriority.MEDIUM,
        comment="Priority: low, medium, high, urgent"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TaskStatus.COORDINATING,
        index=True,
        comment="Status: coordinating, in_progress, completed, cancelled"
    )
    deliverables: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Expected deliverables as JSON"
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Creator user ID"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Soft delete timestamp"
    )
    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relationships
    creator = relationship("User", back_populates="created_tasks", foreign_keys=[created_by])
    lead_department = relationship("Department", back_populates="tasks_as_lead", foreign_keys=[lead_dept_id])
    assignments = relationship("Assignment", back_populates="task", cascade="all, delete-orphan")
    conflict_reports = relationship("ConflictReport", back_populates="task", cascade="all, delete-orphan")
    memos = relationship("Memo", back_populates="related_task")

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title='{self.title}', status='{self.status}')>"
