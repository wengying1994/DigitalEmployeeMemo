"""
Reminder model for tracking notification schedules.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ReminderTriggerType:
    """Reminder trigger type constants."""
    IMMEDIATE = "immediate"           # Send immediately
    SCHEDULED = "scheduled"           # Scheduled at specific time
    CONDITION = "condition"           # Triggered by condition (e.g., 24h unread)


class ReminderStatus:
    """Reminder status constants."""
    PENDING = "pending"       # Not yet sent
    SENT = "sent"             # Successfully sent
    FAILED = "failed"        # Failed to send
    CANCELLED = "cancelled"   # Cancelled


class Reminder(Base, TimestampMixin):
    """
    Reminder model representing scheduled notifications.

    Attributes:
        id: Unique identifier
        target_user_id: User who should receive the reminder
        memo_id: Related memo ID
        trigger_type: How the reminder is triggered
        trigger_time: When to send the reminder
        reminder_methods: JSON array of methods to use
        status: Current status
        retry_count: Number of retry attempts
        last_sent_at: When the reminder was last sent
        sent_at: When the reminder was successfully sent
    """

    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    target_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Target user ID"
    )
    memo_id: Mapped[int] = mapped_column(
        ForeignKey("memos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Related memo ID"
    )
    trigger_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ReminderTriggerType.IMMEDIATE,
        comment="Trigger type: immediate, scheduled, condition"
    )
    trigger_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="When to trigger the reminder"
    )
    reminder_methods: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Methods as JSON: [{method: 'email', address: '...'}]"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ReminderStatus.PENDING,
        index=True,
        comment="Status: pending, sent, failed, cancelled"
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of retry attempts"
    )
    last_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last attempt timestamp"
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Successful send timestamp"
    )

    # Relationships
    target_user = relationship("User", back_populates="reminders")
    memo = relationship("Memo", back_populates="reminders")

    def __repr__(self) -> str:
        return f"<Reminder(id={self.id}, target_user_id={self.target_user_id}, status='{self.status}')>"
