"""
Feedback service for business logic related to department feedback.
"""
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    AssignmentNotFoundException,
    FeedbackNotFoundException,
    ForbiddenException,
    ResourceNotFoundException,
)
from app.core.logger import LoggerMixin, audit_log, OperationType
from app.models import Assignment, AssignmentStatus, Feedback, FeedbackType, Task, User
from app.schemas.feedback import FeedbackCreate


class FeedbackService(LoggerMixin):
    """Service for feedback-related business logic."""

    def __init__(self, db: AsyncSession):
        """
        Initialize feedback service.

        Args:
            db: Database session
        """
        self.db = db

    async def create_feedback(
        self,
        assignment_id: int,
        feedback_data: FeedbackCreate,
        current_user: User
    ) -> Feedback:
        """
        Create feedback for an assignment.

        Args:
            assignment_id: Assignment ID
            feedback_data: Feedback creation data
            current_user: Current authenticated user

        Returns:
            Created feedback instance
        """
        # Get assignment
        assignment_result = await self.db.execute(
            select(Assignment).where(Assignment.id == assignment_id)
        )
        assignment = assignment_result.scalar_one_or_none()
        if not assignment:
            raise AssignmentNotFoundException(assignment_id)

        # Access control: only the assigned department can submit feedback
        if assignment.dept_id != current_user.dept_id and current_user.role != "leader":
            raise ForbiddenException()

        # Create feedback
        feedback = Feedback(
            assignment_id=assignment_id,
            dept_id=current_user.dept_id,
            feedback_type=feedback_data.feedback_type,
            reason=feedback_data.reason,
            proposed_changes=feedback_data.proposed_changes,
            attachments=feedback_data.attachments
        )

        self.db.add(feedback)
        await self.db.flush()

        # Update assignment status based on feedback type
        if feedback_data.feedback_type == FeedbackType.AGREE:
            assignment.status = AssignmentStatus.AGREED
        elif feedback_data.feedback_type == FeedbackType.DISAGREE:
            assignment.status = AssignmentStatus.DISPUTED
        elif feedback_data.feedback_type == FeedbackType.NEED_DISCUSSION:
            assignment.status = AssignmentStatus.DISPUTED

        await self.db.flush()
        await self.db.refresh(feedback)

        # Audit log
        audit_log.log(
            operation=OperationType.SUBMIT,
            user_id=current_user.id,
            resource_type="feedback",
            resource_id=feedback.id,
            dept_id=current_user.dept_id,
            details={
                "assignment_id": assignment_id,
                "feedback_type": feedback_data.feedback_type
            }
        )

        self.logger.info(
            f"Feedback created: {feedback.id} for assignment {assignment_id} "
            f"by user {current_user.id}"
        )
        return feedback

    async def get_feedback_by_id(
        self,
        feedback_id: int,
        current_user: User
    ) -> Feedback:
        """
        Get a feedback by ID.

        Args:
            feedback_id: Feedback ID
            current_user: Current authenticated user

        Returns:
            Feedback instance
        """
        result = await self.db.execute(
            select(Feedback).where(Feedback.id == feedback_id)
        )
        feedback = result.scalar_one_or_none()

        if not feedback:
            raise FeedbackNotFoundException(feedback_id)

        # Get assignment to check access
        assignment_result = await self.db.execute(
            select(Assignment).where(Assignment.id == feedback.assignment_id)
        )
        assignment = assignment_result.scalar_one_or_none()

        # Access control
        if current_user.role != "leader":
            # Must be lead department or feedback's department
            task_result = await self.db.execute(
                select(Task).where(Task.id == assignment.task_id)
            )
            task = task_result.scalar_one_or_none()

            if task.lead_dept_id != current_user.dept_id and \
               feedback.dept_id != current_user.dept_id:
                raise ForbiddenException()

        return feedback

    async def get_assignment_feedbacks(
        self,
        assignment_id: int,
        current_user: User,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Feedback], int]:
        """
        Get feedbacks for an assignment.

        Args:
            assignment_id: Assignment ID
            current_user: Current authenticated user
            page: Page number
            page_size: Items per page

        Returns:
            Tuple of (feedbacks list, total count)
        """
        # Verify assignment exists
        assignment_result = await self.db.execute(
            select(Assignment).where(Assignment.id == assignment_id)
        )
        assignment = assignment_result.scalar_one_or_none()
        if not assignment:
            raise AssignmentNotFoundException(assignment_id)

        # Access control
        if current_user.role != "leader":
            task_result = await self.db.execute(
                select(Task).where(Task.id == assignment.task_id)
            )
            task = task_result.scalar_one_or_none()

            if task.lead_dept_id != current_user.dept_id and \
               assignment.dept_id != current_user.dept_id:
                raise ForbiddenException()

        query = select(Feedback).where(Feedback.assignment_id == assignment_id)

        # Count
        count_result = await self.db.execute(
            select(Feedback.id).where(Feedback.assignment_id == assignment_id)
        )
        total = len(count_result.scalars().all())

        # Paginate
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(Feedback.created_at.desc())

        result = await self.db.execute(query)
        feedbacks = result.scalars().all()

        return list(feedbacks), total

    async def get_department_feedbacks(
        self,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
        feedback_type: Optional[str] = None
    ) -> Tuple[List[Feedback], int]:
        """
        Get feedbacks submitted by current user's department.

        Args:
            current_user: Current authenticated user
            page: Page number
            page_size: Items per page
            feedback_type: Filter by feedback type

        Returns:
            Tuple of (feedbacks list, total count)
        """
        query = select(Feedback).where(Feedback.dept_id == current_user.dept_id)

        if feedback_type:
            query = query.where(Feedback.feedback_type == feedback_type)

        # Count
        count_query = select(Feedback.id).where(Feedback.dept_id == current_user.dept_id)
        if feedback_type:
            count_query = count_query.where(Feedback.feedback_type == feedback_type)
        count_result = await self.db.execute(count_query)
        total = len(count_result.scalars().all())

        # Paginate
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(Feedback.created_at.desc())

        result = await self.db.execute(query)
        feedbacks = result.scalars().all()

        return list(feedbacks), total
