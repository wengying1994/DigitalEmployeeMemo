"""
Feedback model for department responses to assignments.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class FeedbackType:
    """Feedback type constants."""
    AGREE = "agree"                # Department agrees with the assignment
    DISAGREE = "disagree"          # Department disagrees
    NEED_DISCUSSION = "need_discussion"  # Needs further discussion


class Feedback(Base, TimestampMixin):
    """
    Feedback model representing department feedback on assignments.

    Attributes:
        id: Unique identifier
        assignment_id: Related assignment ID
        dept_id: Department providing the feedback
        feedback_type: Type of feedback (agree/disagree/need_discussion)
        reason: Reason for the feedback
        proposed_changes: JSON containing proposed changes
        attachments: JSON containing attachment references
    """

    __tablename__ = "feedbacks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Related assignment ID"
    )
    dept_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Department providing feedback"
    )
    feedback_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
        comment="Feedback type: agree, disagree, need_discussion"
    )
    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Reason for feedback"
    )
    proposed_changes: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Proposed changes as JSON: [{field, current_value, proposed_value, rationale}]"
    )
    attachments: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Attachments as JSON: [{file_id, file_name, file_url}]"
    )

    # Relationships
    assignment = relationship("Assignment", back_populates="feedbacks")
    department = relationship("Department", back_populates="feedbacks")

    def __repr__(self) -> str:
        return f"<Feedback(id={self.id}, assignment_id={self.assignment_id}, type='{self.feedback_type}')>"
