"""
ConflictReport model for tracking conflicts between departments.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ConflictStatus:
    """Conflict status constants."""
    PENDING = "pending"        # Awaiting decision
    RESOLVED = "resolved"     # Resolved by leader
    ESCALATED = "escalated"   # Escalated to higher authority


class UrgencyLevel:
    """Urgency level constants."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConflictReport(Base, TimestampMixin):
    """
    ConflictReport model representing conflicts that need leadership resolution.

    Attributes:
        id: Unique identifier
        task_id: Related task ID
        reporter_user_id: User who reported the conflict
        reporter_dept_id: Department of the reporter
        conflict_summary: Brief summary of the conflict
        conflict_details: Detailed conflict information (JSON)
        proposed_solutions: JSON containing proposed solutions
        urgency_level: Urgency level (low/medium/high/critical)
        need_decision_by: Deadline for decision
        decision_made_at: When the decision was made
        decision_content: The actual decision made
        decision_maker_id: User ID of the decision maker
        status: Current status (pending/resolved/escalated)
    """

    __tablename__ = "conflict_reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Related task ID"
    )
    reporter_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reporter user ID"
    )
    reporter_dept_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reporter department ID"
    )
    conflict_summary: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Brief summary of the conflict"
    )
    conflict_details: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Detailed conflict info as JSON"
    )
    proposed_solutions: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Proposed solutions as JSON: [{solution_id, description, pros, cons}]"
    )
    urgency_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=UrgencyLevel.MEDIUM,
        index=True,
        comment="Urgency: low, medium, high, critical"
    )
    need_decision_by: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Decision deadline"
    )
    decision_made_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When decision was made"
    )
    decision_content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Decision content"
    )
    decision_maker_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Decision maker user ID"
    )
    memo_id: Mapped[int | None] = mapped_column(
        ForeignKey("memos.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,
        comment="Related memo ID"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ConflictStatus.PENDING,
        index=True,
        comment="Status: pending, resolved, escalated"
    )

    # Relationships
    task = relationship("Task", back_populates="conflict_reports")
    reporter_user = relationship("User", foreign_keys=[reporter_user_id])
    reporter_department = relationship("Department", foreign_keys=[reporter_dept_id])
    decision_maker = relationship("User", foreign_keys=[decision_maker_id])
    memo = relationship("Memo", back_populates="related_conflict", uselist=False, foreign_keys=[memo_id])

    def __repr__(self) -> str:
        return f"<ConflictReport(id={self.id}, task_id={self.task_id}, status='{self.status}')>"
