"""
Assignment API routes.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_pagination_params
from app.core.exceptions import ForbiddenException
from app.core.security import Permission, check_permission
from app.db.session import get_db
from app.models import User, Department, Task
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentUpdate,
    AssignmentResponse,
    AssignmentDetail,
    AssignmentListResponse,
)
from app.services.assignment_service import AssignmentService


router = APIRouter()


def get_assignment_service(db: AsyncSession = Depends(get_db)) -> AssignmentService:
    """Get assignment service instance."""
    service = AssignmentService(db)
    service.db = db  # Ensure service has db reference
    return service


@router.post("/tasks/{task_id}/assignments", response_model=AssignmentResponse, status_code=201)
async def create_assignment(
    task_id: int,
    assignment_data: AssignmentCreate,
    current_user: User = Depends(get_current_user),
    service: AssignmentService = Depends(get_assignment_service)
) -> AssignmentResponse:
    """
    Create a new assignment for a task.

    Only the lead department of the task can create assignments.

    - **task_id**: Parent task ID
    - **dept_id**: Assigned department ID
    - **assigned_tasks**: Task items (JSON)
    - **deadline**: Assignment deadline
    - **dependencies**: Dependencies (JSON)
    - **resources_needed**: Resources needed (JSON)
    """
    # Permission check - must be lead department or leader
    assignment = await service.create_assignment(task_id, assignment_data, current_user)
    return AssignmentResponse.model_validate(assignment)


@router.get("/tasks/{task_id}/assignments", response_model=AssignmentListResponse)
async def get_task_assignments(
    task_id: int,
    current_user: User = Depends(get_current_user),
    service: AssignmentService = Depends(get_assignment_service),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None)
) -> AssignmentListResponse:
    """
    Get assignments for a task.

    - **task_id**: Task ID
    - **page**: Page number
    - **page_size**: Items per page
    - **status**: Filter by status (pending/agreed/disputed)
    """
    assignments_list, total = await service.get_task_assignments(
        task_id=task_id,
        current_user=current_user,
        page=page,
        page_size=page_size,
        status=status
    )

    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return AssignmentListResponse(
        items=[AssignmentResponse.model_validate(a) for a in assignments_list],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/{assignment_id}", response_model=AssignmentDetail)
async def get_assignment(
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    service: AssignmentService = Depends(get_assignment_service)
) -> AssignmentDetail:
    """
    Get an assignment by ID.
    """
    assignment = await service.get_assignment_by_id(assignment_id, current_user, load_feedbacks=True)

    # Build response with additional info
    dept_result = await service.db.execute(
        select(Department).where(Department.id == assignment.dept_id)
    )
    dept = dept_result.scalar_one_or_none()

    task_result = await service.db.execute(
        select(Task).where(Task.id == assignment.task_id)
    )
    task = task_result.scalar_one_or_none()

    return AssignmentDetail(
        id=assignment.id,
        task_id=assignment.task_id,
        dept_id=assignment.dept_id,
        assigned_tasks=assignment.assigned_tasks,
        deadline=assignment.deadline,
        dependencies=assignment.dependencies,
        resources_needed=assignment.resources_needed,
        status=assignment.status,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
        dept_name=dept.name if dept else None,
        task_title=task.title if task else None,
        feedbacks=[]  # Would populate from load
    )


@router.put("/{assignment_id}", response_model=AssignmentResponse)
async def update_assignment(
    assignment_id: int,
    assignment_data: AssignmentUpdate,
    current_user: User = Depends(get_current_user),
    service: AssignmentService = Depends(get_assignment_service)
) -> AssignmentResponse:
    """
    Update an assignment.

    Only the lead department can update assignments.
    """
    assignment = await service.update_assignment(assignment_id, assignment_data, current_user)
    return AssignmentResponse.model_validate(assignment)
