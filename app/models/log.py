"""
Log model for operation audit trail.
"""
from datetime import datetime

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class OperationType:
    """Operation type constants for audit log."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    READ = "read"
    SUBMIT = "submit"
    APPROVE = "approve"
    REJECT = "reject"
    ESCALATE = "escalate"
    NOTIFY = "notify"


class Log(Base, TimestampMixin):
    """
    Log model for operation audit trail.

    Attributes:
        id: Unique identifier
        user_id: User who performed the operation
        dept_id: Department of the user
        operation: Type of operation
        resource_type: Type of resource operated on
        resource_id: ID of the resource
        details: Additional operation details (JSON)
        ip_address: Client IP address
    """

    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        nullable=True,
        index=True,
        comment="User who performed the operation"
    )
    dept_id: Mapped[int | None] = mapped_column(
        nullable=True,
        index=True,
        comment="Department of the user"
    )
    operation: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Operation type"
    )
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Resource type"
    )
    resource_id: Mapped[int | None] = mapped_column(
        nullable=True,
        index=True,
        comment="Resource ID"
    )
    details: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional details as JSON"
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
        comment="Client IP address"
    )

    def __repr__(self) -> str:
        return f"<Log(id={self.id}, operation='{self.operation}', resource_type='{self.resource_type}')>"
