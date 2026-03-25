"""
Department model for organizational structure.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Department(Base, TimestampMixin):
    """
    Department model representing organizational units.

    Attributes:
        id: Unique identifier
        name: Department name
        leader_id: ID of the department leader (user)
        description: Department description
    """

    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Department name"
    )
    leader_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Department leader user ID"
    )
    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Department description"
    )

    # Relationships
    users = relationship("User", back_populates="department", foreign_keys="User.dept_id")
    leader = relationship("User", foreign_keys=[leader_id])
    tasks_as_lead = relationship("Task", back_populates="lead_department", foreign_keys="Task.lead_dept_id")
    assignments = relationship("Assignment", back_populates="department")
    feedbacks = relationship("Feedback", back_populates="department")

    def __repr__(self) -> str:
        return f"<Department(id={self.id}, name='{self.name}')>"
