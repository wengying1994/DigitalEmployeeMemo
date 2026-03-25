"""
Unit tests for TaskService.
"""
from datetime import datetime

import pytest
from sqlalchemy import select

from app.models import User, Department, Task, TaskStatus, TaskPriority
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.task_service import TaskService


class TestTaskService:
    """Tests for TaskService."""

    @pytest.mark.asyncio
    async def test_create_task(self, async_db_session):
        """Test creating a task."""
        # Create department first
        dept = Department(id=1, name="Test Dept", leader_id=1)
        async_db_session.add(dept)

        # Create user
        user = User(
            id=1,
            name="Test User",
            email="test@example.com",
            role="leader",
            dept_id=1
        )
        async_db_session.add(user)
        await async_db_session.flush()

        service = TaskService(async_db_session)
        task_data = TaskCreate(
            title="New Task",
            description="Task description",
            lead_dept_id=1,
            deadline=datetime.utcnow(),
            priority="high"
        )

        task = await service.create_task(task_data, user)

        assert task.id is not None
        assert task.title == "New Task"
        assert task.description == "Task description"
        assert task.lead_dept_id == 1
        assert task.priority == "high"
        assert task.status == TaskStatus.COORDINATING
        assert task.created_by == user.id

    @pytest.mark.asyncio
    async def test_get_task_by_id(self, async_db_session):
        """Test getting a task by ID."""
        # Setup: create department, user, and task
        dept = Department(id=1, name="Test Dept", leader_id=1)
        async_db_session.add(dept)

        user = User(id=1, name="Test User", email="test@example.com", role="leader", dept_id=1)
        async_db_session.add(user)

        task = Task(
            title="Test Task",
            description="Description",
            lead_dept_id=1,
            created_by=1,
            status=TaskStatus.COORDINATING
        )
        async_db_session.add(task)
        await async_db_session.flush()

        service = TaskService(async_db_session)
        result = await service.get_task_by_id(task.id, user)

        assert result.id == task.id
        assert result.title == "Test Task"

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, async_db_session):
        """Test getting a non-existent task."""
        from app.core.exceptions import TaskNotFoundException

        dept = Department(id=1, name="Test Dept", leader_id=1)
        async_db_session.add(dept)

        user = User(id=1, name="Test User", email="test@example.com", role="leader", dept_id=1)
        async_db_session.add(user)
        await async_db_session.flush()

        service = TaskService(async_db_session)

        with pytest.raises(TaskNotFoundException):
            await service.get_task_by_id(9999, user)

    @pytest.mark.asyncio
    async def test_update_task(self, async_db_session):
        """Test updating a task."""
        # Setup
        dept = Department(id=1, name="Test Dept", leader_id=1)
        async_db_session.add(dept)

        user = User(id=1, name="Test User", email="test@example.com", role="leader", dept_id=1)
        async_db_session.add(user)

        task = Task(
            title="Original Title",
            description="Original description",
            lead_dept_id=1,
            created_by=1,
            status=TaskStatus.COORDINATING
        )
        async_db_session.add(task)
        await async_db_session.flush()

        service = TaskService(async_db_session)
        update_data = TaskUpdate(
            title="Updated Title",
            status=TaskStatus.IN_PROGRESS
        )

        updated = await service.update_task(task.id, update_data, user)

        assert updated.title == "Updated Title"
        assert updated.status == TaskStatus.IN_PROGRESS
        # Description should remain unchanged
        assert updated.description == "Original description"

    @pytest.mark.asyncio
    async def test_delete_task_soft_delete(self, async_db_session):
        """Test soft deleting a task."""
        # Setup
        dept = Department(id=1, name="Test Dept", leader_id=1)
        async_db_session.add(dept)

        user = User(id=1, name="Test User", email="test@example.com", role="leader", dept_id=1)
        async_db_session.add(user)

        task = Task(
            title="Task to Delete",
            description="Will be deleted",
            lead_dept_id=1,
            created_by=1,
            status=TaskStatus.COORDINATING
        )
        async_db_session.add(task)
        await async_db_session.flush()
        task_id = task.id

        service = TaskService(async_db_session)
        await service.delete_task(task_id, user)
        await async_db_session.flush()

        # Verify soft delete
        result = await async_db_session.execute(
            select(Task).where(Task.id == task_id)
        )
        deleted_task = result.scalar_one_or_none()

        assert deleted_task is not None
        assert deleted_task.is_deleted is True
        assert deleted_task.deleted_at is not None

    @pytest.mark.asyncio
    async def test_get_tasks_with_pagination(self, async_db_session):
        """Test getting tasks with pagination."""
        # Setup: create multiple tasks
        dept = Department(id=1, name="Test Dept", leader_id=1)
        async_db_session.add(dept)

        user = User(id=1, name="Test User", email="test@example.com", role="leader", dept_id=1)
        async_db_session.add(user)

        for i in range(15):
            task = Task(
                title=f"Task {i}",
                description=f"Description {i}",
                lead_dept_id=1,
                created_by=1,
                status=TaskStatus.COORDINATING
            )
            async_db_session.add(task)

        await async_db_session.flush()

        service = TaskService(async_db_session)

        # Get first page
        tasks, total = await service.get_tasks(user, page=1, page_size=10)

        assert len(tasks) == 10
        assert total == 15

        # Get second page
        tasks, total = await service.get_tasks(user, page=2, page_size=10)

        assert len(tasks) == 5
        assert total == 15

    @pytest.mark.asyncio
    async def test_get_tasks_with_filters(self, async_db_session):
        """Test getting tasks with status filter."""
        # Setup
        dept = Department(id=1, name="Test Dept", leader_id=1)
        async_db_session.add(dept)

        user = User(id=1, name="Test User", email="test@example.com", role="leader", dept_id=1)
        async_db_session.add(user)

        # Create tasks with different statuses
        for status in [TaskStatus.COORDINATING, TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED]:
            task = Task(
                title=f"Task {status}",
                description="Test",
                lead_dept_id=1,
                created_by=1,
                status=status
            )
            async_db_session.add(task)

        await async_db_session.flush()

        service = TaskService(async_db_session)

        # Filter by status
        tasks, total = await service.get_tasks(user, status=TaskStatus.IN_PROGRESS)

        assert len(tasks) == 1
        assert total == 1
        assert tasks[0].status == TaskStatus.IN_PROGRESS
