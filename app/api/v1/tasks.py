"""
Task API routes.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_leader_user, get_pagination_params
from app.core.exceptions import ForbiddenException
from app.core.security import Permission, check_permission
from app.db.session import get_db
from app.models import User, Department
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskDetail,
    TaskListResponse,
)
from app.services.task_service import TaskService


router = APIRouter()


def get_task_service(db: AsyncSession = Depends(get_db)) -> TaskService:
    """Get task service instance."""
    service = TaskService(db)
    service.db = db  # Ensure service has db reference
    return service


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_leader_user),
    service: TaskService = Depends(get_task_service)
) -> TaskResponse:
    """
    Create a new task.

    Only leaders can create tasks.

    - **title**: Task title (required)
    - **description**: Task description
    - **lead_dept_id**: Lead department ID (required)
    - **deadline**: Expected deadline
    - **priority**: Priority level (low/medium/high/urgent)
    - **deliverables**: Expected deliverables (JSON)
    """
    # Permission check
    if not check_permission(current_user.role, Permission.CAN_CREATE_TASK):
        raise ForbiddenException(message="You don't have permission to create tasks")

    task = await service.create_task(task_data, current_user)
    return TaskResponse.model_validate(task)


@router.get("", response_model=TaskListResponse)
async def get_tasks(
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    lead_dept_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None)
) -> TaskListResponse:
    """
    Get tasks with pagination and filters.

    Regular users can only see tasks their department is involved in.
    Leaders can see all tasks.

    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **status**: Filter by status (coordinating/in_progress/completed)
    - **priority**: Filter by priority (low/medium/high/urgent)
    - **lead_dept_id**: Filter by lead department
    - **search**: Search in title and description
    """
    tasks_list, total = await service.get_tasks(
        current_user=current_user,
        page=page,
        page_size=page_size,
        status=status,
        priority=priority,
        lead_dept_id=lead_dept_id,
        search=search
    )

    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return TaskListResponse(
        items=[TaskResponse.model_validate(t) for t in tasks_list],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/{task_id}", response_model=TaskDetail)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service)
) -> TaskDetail:
    """
    Get a task by ID.

    Returns task details including assignments.
    """
    task = await service.get_task_by_id(task_id, current_user, load_assignments=True)

    # Build response with additional info
    dept_result = await service.db.execute(
        select(Department).where(Department.id == task.lead_dept_id)
    )
    dept = dept_result.scalar_one_or_none()

    return TaskDetail(
        id=task.id,
        title=task.title,
        description=task.description,
        lead_dept_id=task.lead_dept_id,
        deadline=task.deadline,
        priority=task.priority,
        status=task.status,
        deliverables=task.deliverables,
        created_by=task.created_by,
        created_at=task.created_at,
        updated_at=task.updated_at,
        is_deleted=task.is_deleted,
        lead_dept_name=dept.name if dept else None,
        creator_name=current_user.name,
        assignments=[],  # Would populate from load
        conflict_count=0
    )


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    current_user: User = Depends(get_leader_user),
    service: TaskService = Depends(get_task_service)
) -> TaskResponse:
    """
    Update a task.

    Only leaders can update tasks.
    """
    if not check_permission(current_user.role, Permission.CAN_UPDATE_TASK):
        raise ForbiddenException(message="You don't have permission to update tasks")

    task = await service.update_task(task_id, task_data, current_user)
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_leader_user),
    service: TaskService = Depends(get_task_service)
) -> None:
    """
    Delete a task (soft delete).

    Only leaders can delete tasks.
    """
    if not check_permission(current_user.role, Permission.CAN_DELETE_TASK):
        raise ForbiddenException(message="You don't have permission to delete tasks")

    await service.delete_task(task_id, current_user)
