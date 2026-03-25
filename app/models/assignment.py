"""
Assignment model for work distribution among departments.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class AssignmentStatus:
    """Assignment status constants."""
    PENDING = "pending"      # Awaiting department feedback
    AGREED = "agreed"        # Department agreed to the assignment
    DISPUTED = "disputed"     # Department has disputes


class Assignment(Base, TimestampMixin):
    """
    Assignment model representing work assigned to a department.

    Attributes:
        id: Unique identifier
        task_id: Parent task ID
        dept_id: Department ID this assignment is for
        assigned_tasks: JSON containing task items for this department
        deadline: Deadline for this department's work
        dependencies: JSON containing dependencies on other assignments
        resources_needed: JSON containing required resources
        status: Current status (pending/agreed/disputed)
    """

    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent task ID"
    )
    dept_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Assigned department ID"
    )
    assigned_tasks: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Task items as JSON: [{title, description, estimated_hours}]"
    )
    deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Assignment deadline"
    )
    dependencies: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Dependencies as JSON: [{assignment_id, description}]"
    )
    resources_needed: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Resources needed as JSON: [{resource_type, quantity, notes}]"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AssignmentStatus.PENDING,
        index=True,
        comment="Status: pending, agreed, disputed"
    )

    # Relationships
    task = relationship("Task", back_populates="assignments")
    department = relationship("Department", back_populates="assignments")
    feedbacks = relationship("Feedback", back_populates="assignment", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Assignment(id={self.id}, task_id={self.task_id}, dept_id={self.dept_id}, status='{self.status}')>"
