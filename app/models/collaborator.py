"""
Collaborator model for memo access control.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class PermissionLevel:
    """Permission level constants for memo collaborators."""
    VIEW = "view"     # Can only view
    EDIT = "edit"     # Can view and edit


class Collaborator(Base, TimestampMixin):
    """
    Collaborator model representing users who have access to a memo.

    Attributes:
        memo_id: Related memo ID
        user_id: User ID who has access
        permission: Permission level (view/edit)
        added_by: ID of user who added this collaborator
        added_at: When the collaborator was added
    """

    __tablename__ = "collaborators"

    memo_id: Mapped[int] = mapped_column(
        ForeignKey("memos.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
        comment="Memo ID"
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
        comment="Collaborator user ID"
    )
    permission: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PermissionLevel.VIEW,
        comment="Permission: view, edit"
    )
    added_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who added this collaborator"
    )

    # Relationships
    memo = relationship("Memo", back_populates="collaborators")
    user = relationship("User", foreign_keys=[user_id])
    adder = relationship("User", foreign_keys=[added_by])

    def __repr__(self) -> str:
        return f"<Collaborator(memo_id={self.memo_id}, user_id={self.user_id}, permission='{self.permission}')>"
