"""
Assignment service for business logic related to work assignments.
"""
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    AssignmentNotFoundException,
    ForbiddenException,
    NotLeadDepartmentException,
    ResourceNotFoundException,
    ValidationException,
)
from app.core.logger import LoggerMixin, audit_log, OperationType
from app.models import Assignment, AssignmentStatus, Task, User, Department
from app.models.feedback import Feedback
from app.schemas.assignment import AssignmentCreate, AssignmentUpdate


class AssignmentService(LoggerMixin):
    """Service for assignment-related business logic."""

    def __init__(self, db: AsyncSession):
        """
        Initialize assignment service.

        Args:
            db: Database session
        """
        self.db = db

    async def create_assignment(
        self,
        task_id: int,
        assignment_data: AssignmentCreate,
        current_user: User
    ) -> Assignment:
        """
        Create a new assignment for a task.

        Args:
            task_id: Parent task ID
            assignment_data: Assignment creation data
            current_user: Current authenticated user

        Returns:
            Created assignment instance
        """
        # Get task
        task_result = await self.db.execute(
            select(Task).where(
                and_(
                    Task.id == task_id,
                    Task.is_deleted == False
                )
            )
        )
        task = task_result.scalar_one_or_none()
        if not task:
            from app.core.exceptions import TaskNotFoundException
            raise TaskNotFoundException(task_id)

        # Check if current user's department is the lead department
        if task.lead_dept_id != current_user.dept_id:
            raise NotLeadDepartmentException()

        # Verify department exists
        dept = await self.db.get(Department, assignment_data.dept_id)
        if not dept:
            raise ResourceNotFoundException("Department", assignment_data.dept_id)

        # Create assignment
        assignment = Assignment(
            task_id=task_id,
            dept_id=assignment_data.dept_id,
            assigned_tasks=assignment_data.assigned_tasks,
            deadline=assignment_data.deadline,
            dependencies=assignment_data.dependencies,
            resources_needed=assignment_data.resources_needed,
            status=AssignmentStatus.PENDING
        )

        self.db.add(assignment)
        await self.db.flush()
        await self.db.refresh(assignment)

        # Audit log
        audit_log.log(
            operation=OperationType.CREATE,
            user_id=current_user.id,
            resource_type="assignment",
            resource_id=assignment.id,
            dept_id=current_user.dept_id,
            details={
                "task_id": task_id,
                "assigned_dept_id": assignment_data.dept_id
            }
        )

        self.logger.info(
            f"Assignment created: {assignment.id} for task {task_id} by user {current_user.id}"
        )
        return assignment

    async def get_assignment_by_id(
        self,
        assignment_id: int,
        current_user: User,
        load_feedbacks: bool = False
    ) -> Assignment:
        """
        Get an assignment by ID with access control.

        Args:
            assignment_id: Assignment ID
            current_user: Current authenticated user
            load_feedbacks: Whether to load feedbacks

        Returns:
            Assignment instance
        """
        query = select(Assignment).where(Assignment.id == assignment_id)

        if load_feedbacks:
            query = query.options(selectinload(Assignment.feedbacks))

        result = await self.db.execute(query)
        assignment = result.scalar_one_or_none()

        if not assignment:
            raise AssignmentNotFoundException(assignment_id)

        # Get task to check access
        task_result = await self.db.execute(
            select(Task).where(Task.id == assignment.task_id)
        )
        task = task_result.scalar_one_or_none()

        # Access control
        if current_user.role != "leader":
            # Must be lead department or assigned department
            if task.lead_dept_id != current_user.dept_id and \
               assignment.dept_id != current_user.dept_id:
                raise ForbiddenException()

        return assignment

    async def get_task_assignments(
        self,
        task_id: int,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None
    ) -> Tuple[List[Assignment], int]:
        """
        Get assignments for a task.

        Args:
            task_id: Task ID
            current_user: Current authenticated user
            page: Page number
            page_size: Items per page
            status: Filter by status

        Returns:
            Tuple of (assignments list, total count)
        """
        # Verify task exists
        task_result = await self.db.execute(
            select(Task).where(
                and_(
                    Task.id == task_id,
                    Task.is_deleted == False
                )
            )
        )
        task = task_result.scalar_one_or_none()
        if not task:
            from app.core.exceptions import TaskNotFoundException
            raise TaskNotFoundException(task_id)

        # Access control
        if current_user.role != "leader":
            if task.lead_dept_id != current_user.dept_id:
                # Check if user is in any assigned department
                user_dept_assignment = await self.db.execute(
                    select(Assignment).where(
                        and_(
                            Assignment.task_id == task_id,
                            Assignment.dept_id == current_user.dept_id
                        )
                    )
                )
                if not user_dept_assignment.scalar_one_or_none():
                    raise ForbiddenException()

        query = select(Assignment).where(Assignment.task_id == task_id)

        if status:
            query = query.where(Assignment.status == status)

        # Count
        count_result = await self.db.execute(
            select(Assignment.id).where(Assignment.task_id == task_id)
        )
        total = len(count_result.scalars().all())

        # Paginate
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(Assignment.created_at.desc())

        result = await self.db.execute(query)
        assignments = result.scalars().all()

        return list(assignments), total

    async def update_assignment(
        self,
        assignment_id: int,
        assignment_data: AssignmentUpdate,
        current_user: User
    ) -> Assignment:
        """
        Update an assignment.

        Args:
            assignment_id: Assignment ID
            assignment_data: Update data
            current_user: Current authenticated user

        Returns:
            Updated assignment instance
        """
        assignment = await self.get_assignment_by_id(assignment_id, current_user)

        # Check if user's department is lead department of the task
        task_result = await self.db.execute(
            select(Task).where(Task.id == assignment.task_id)
        )
        task = task_result.scalar_one_or_none()

        if task.lead_dept_id != current_user.dept_id and current_user.role != "leader":
            raise NotLeadDepartmentException()

        # Update fields
        update_dict = assignment_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(assignment, field, value)

        await self.db.flush()
        await self.db.refresh(assignment)

        # Audit log
        audit_log.log(
            operation=OperationType.UPDATE,
            user_id=current_user.id,
            resource_type="assignment",
            resource_id=assignment.id,
            dept_id=current_user.dept_id,
            details=update_dict
        )

        self.logger.info(f"Assignment updated: {assignment.id} by user {current_user.id}")
        return assignment

    async def get_assignment_statistics(self, task_id: int) -> dict:
        """
        Get assignment statistics for a task.

        Args:
            task_id: Task ID

        Returns:
            Statistics dictionary
        """
        result = await self.db.execute(
            select(Assignment).where(Assignment.task_id == task_id)
        )
        assignments = result.scalars().all()

        return {
            "total": len(assignments),
            "pending": sum(1 for a in assignments if a.status == AssignmentStatus.PENDING),
            "agreed": sum(1 for a in assignments if a.status == AssignmentStatus.AGREED),
            "disputed": sum(1 for a in assignments if a.status == AssignmentStatus.DISPUTED),
        }
