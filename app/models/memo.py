"""
Memo model for leader notifications and decisions.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class MemoType:
    """Memo type constants."""
    CONFLICT = "conflict"      # Conflict report memo
    APPROVAL = "approval"     # Approval request memo
    INFO = "info"             # General information memo


class MemoStatus:
    """Memo status constants."""
    UNREAD = "unread"     # Not yet read
    READ = "read"         # Has been read
    RESOLVED = "resolved" # Resolved/decided


class Memo(Base, TimestampMixin):
    """
    Memo model representing leader memos/notifications.

    Attributes:
        id: Unique identifier
        user_id: Leader user ID who should see this memo
        title: Memo title
        content: Memo content (JSON for structured data)
        full_memo_text: Full memo text for display
        memo_type: Type of memo (conflict/approval/info)
        related_id: ID of related entity (e.g., conflict_id)
        related_task_id: Related task ID
        status: Current status (unread/read/resolved)
        read_at: When the memo was read
    """

    __tablename__ = "memos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Leader user ID"
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Memo title"
    )
    content: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Structured content as JSON"
    )
    full_memo_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Full memo text for display"
    )
    memo_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=MemoType.INFO,
        index=True,
        comment="Memo type: conflict, approval, info"
    )
    related_id: Mapped[int | None] = mapped_column(
        nullable=True,
        index=True,
        comment="Related entity ID (e.g., conflict_id)"
    )
    related_task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Related task ID"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=MemoStatus.UNREAD,
        index=True,
        comment="Status: unread, read, resolved"
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When memo was read"
    )

    # Relationships
    leader = relationship("User", back_populates="created_memos")
    related_task = relationship("Task", back_populates="memos")
    related_conflict = relationship("ConflictReport", back_populates="memo", uselist=False, foreign_keys="ConflictReport.memo_id")
    collaborators = relationship("Collaborator", back_populates="memo", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="memo", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Memo(id={self.id}, user_id={self.user_id}, type='{self.memo_type}', status='{self.status}')>"
