"""
Task service for business logic related to tasks.
"""
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    ResourceNotFoundException,
    TaskNotFoundException,
    ValidationException,
)
from app.core.logger import LoggerMixin, audit_log, OperationType
from app.models import Task, TaskStatus, User, Department
from app.models.assignment import Assignment
from app.models.conflict_report import ConflictReport
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService(LoggerMixin):
    """Service for task-related business logic."""

    def __init__(self, db: AsyncSession):
        """
        Initialize task service.

        Args:
            db: Database session
        """
        self.db = db

    async def create_task(
        self,
        task_data: TaskCreate,
        current_user: User
    ) -> Task:
        """
        Create a new task.

        Args:
            task_data: Task creation data
            current_user: Current authenticated user

        Returns:
            Created task instance
        """
        # Verify lead department exists
        lead_dept = await self.db.get(Department, task_data.lead_dept_id)
        if not lead_dept:
            raise ResourceNotFoundException("Department", task_data.lead_dept_id)

        # Create task
        task = Task(
            title=task_data.title,
            description=task_data.description,
            lead_dept_id=task_data.lead_dept_id,
            deadline=task_data.deadline,
            priority=task_data.priority,
            deliverables=task_data.deliverables,
            created_by=current_user.id,
            status=TaskStatus.COORDINATING
        )

        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)

        # Audit log
        audit_log.log(
            operation=OperationType.CREATE,
            user_id=current_user.id,
            resource_type="task",
            resource_id=task.id,
            dept_id=current_user.dept_id,
            details={"title": task.title, "lead_dept_id": task.lead_dept_id}
        )

        self.logger.info(f"Task created: {task.id} by user {current_user.id}")
        return task

    async def get_task_by_id(
        self,
        task_id: int,
        current_user: User,
        load_assignments: bool = False
    ) -> Task:
        """
        Get a task by ID with access control.

        Args:
            task_id: Task ID
            current_user: Current authenticated user
            load_assignments: Whether to load assignments

        Returns:
            Task instance

        Raises:
            TaskNotFoundException: If task not found
        """
        query = select(Task).where(
            and_(
                Task.id == task_id,
                Task.is_deleted == False
            )
        )

        if load_assignments:
            query = query.options(selectinload(Task.assignments))

        result = await self.db.execute(query)
        task = result.scalar_one_or_none()

        if not task:
            raise TaskNotFoundException(task_id)

        # Access control: user must be leader, or their department must be involved
        if current_user.role != "leader":
            # Check if user's department is lead or has assignments
            if task.lead_dept_id != current_user.dept_id:
                has_assignment = False
                if load_assignments:
                    has_assignment = any(
                        a.dept_id == current_user.dept_id for a in task.assignments
                    )
                else:
                    assignment_result = await self.db.execute(
                        select(Assignment).where(
                            and_(
                                Assignment.task_id == task_id,
                                Assignment.dept_id == current_user.dept_id
                            )
                        )
                    )
                    has_assignment = assignment_result.scalar_one_or_none() is not None

                if not has_assignment:
                    from app.core.exceptions import ForbiddenException
                    raise ForbiddenException()

        return task

    async def get_tasks(
        self,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        lead_dept_id: Optional[int] = None,
        search: Optional[str] = None
    ) -> Tuple[List[Task], int]:
        """
        Get tasks with pagination and filters.

        Args:
            current_user: Current authenticated user
            page: Page number
            page_size: Items per page
            status: Filter by status
            priority: Filter by priority
            lead_dept_id: Filter by lead department
            search: Search in title/description

        Returns:
            Tuple of (tasks list, total count)
        """
        query = select(Task).where(Task.is_deleted == False)

        # Access control for non-leaders
        if current_user.role != "leader":
            # Users can see tasks where their department is lead or has assignments
            subquery = select(Assignment.task_id).where(
                Assignment.dept_id == current_user.dept_id
            )
            query = query.where(
                or_(
                    Task.lead_dept_id == current_user.dept_id,
                    Task.id.in_(subquery)
                )
            )

        # Apply filters
        if status:
            query = query.where(Task.status == status)
        if priority:
            query = query.where(Task.priority == priority)
        if lead_dept_id:
            query = query.where(Task.lead_dept_id == lead_dept_id)
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Task.title.ilike(search_pattern),
                    Task.description.ilike(search_pattern)
                )
            )

        # Count total
        count_result = await self.db.execute(
            select(Task.id).where(Task.is_deleted == False)
        )
        total = len(count_result.scalars().all())

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(Task.created_at.desc())

        result = await self.db.execute(query)
        tasks = result.scalars().all()

        return list(tasks), total

    async def update_task(
        self,
        task_id: int,
        task_data: TaskUpdate,
        current_user: User
    ) -> Task:
        """
        Update a task.

        Args:
            task_id: Task ID
            task_data: Update data
            current_user: Current authenticated user

        Returns:
            Updated task instance
        """
        task = await self.get_task_by_id(task_id, current_user)

        # Update fields
        update_dict = task_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(task, field, value)

        await self.db.flush()
        await self.db.refresh(task)

        # Audit log
        audit_log.log(
            operation=OperationType.UPDATE,
            user_id=current_user.id,
            resource_type="task",
            resource_id=task.id,
            dept_id=current_user.dept_id,
            details=update_dict
        )

        self.logger.info(f"Task updated: {task.id} by user {current_user.id}")
        return task

    async def delete_task(
        self,
        task_id: int,
        current_user: User
    ) -> None:
        """
        Soft delete a task.

        Args:
            task_id: Task ID
            current_user: Current authenticated user
        """
        task = await self.get_task_by_id(task_id, current_user)

        # Soft delete
        task.is_deleted = True
        task.deleted_at = datetime.utcnow()

        await self.db.flush()

        # Audit log
        audit_log.log(
            operation=OperationType.DELETE,
            user_id=current_user.id,
            resource_type="task",
            resource_id=task.id,
            dept_id=current_user.dept_id
        )

        self.logger.info(f"Task deleted: {task.id} by user {current_user.id}")

    async def get_task_statistics(self, current_user: User) -> dict:
        """
        Get task statistics for dashboard.

        Args:
            current_user: Current authenticated user

        Returns:
            Statistics dictionary
        """
        query = select(Task).where(Task.is_deleted == False)

        # Access control
        if current_user.role != "leader":
            query = query.where(Task.lead_dept_id == current_user.dept_id)

        result = await self.db.execute(query)
        tasks = result.scalars().all()

        stats = {
            "total": len(tasks),
            "coordinating": sum(1 for t in tasks if t.status == TaskStatus.COORDINATING),
            "in_progress": sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS),
            "completed": sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
            "near_deadline": sum(
                1 for t in tasks
                if t.deadline and t.deadline <= datetime.utcnow()
            ),
        }

        return stats
