"""
Message model for bidirectional messaging between users.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Message(Base, TimestampMixin):
    """
    Message model representing a bidirectional memo/note between users.

    Attributes:
        id: Unique identifier
        sender_id: User ID of the sender
        receiver_id: User ID of the receiver (null for broadcast)
        title: Message title
        content: Message content
        is_read: Whether the message has been read
        read_at: When the message was read
    """

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sender_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Sender user ID"
    )
    receiver_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Receiver user ID (null for broadcast)"
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Message title"
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Message content"
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether message has been read"
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When message was read"
    )

    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_messages")

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, sender_id={self.sender_id}, receiver_id={self.receiver_id}, is_read={self.is_read})>"
