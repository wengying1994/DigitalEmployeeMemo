"""
Conflict API routes.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_leader_user, get_pagination_params
from app.core.exceptions import ForbiddenException
from app.core.security import Permission, check_permission
from app.db.session import get_db
from app.models import User, Task, User as UserModel, Department
from app.schemas.conflict import (
    ConflictCreate,
    ConflictUpdate,
    ConflictDecision,
    ConflictResponse,
    ConflictDetail,
    ConflictListResponse,
)
from app.services.conflict_service import ConflictService


router = APIRouter()


def get_conflict_service(db: AsyncSession = Depends(get_db)) -> ConflictService:
    """Get conflict service instance."""
    service = ConflictService(db)
    service.db = db  # Ensure service has db reference
    return service


@router.post("", response_model=ConflictResponse, status_code=201)
async def create_conflict(
    conflict_data: ConflictCreate,
    current_user: User = Depends(get_current_user),
    service: ConflictService = Depends(get_conflict_service)
) -> ConflictResponse:
    """
    Report a new conflict.

    Only the lead department or leaders can report conflicts.
    This will automatically create a memo for the leader.

    - **task_id**: Related task ID
    - **conflict_summary**: Brief summary of the conflict
    - **conflict_details**: Detailed info (JSON)
    - **proposed_solutions**: Proposed solutions (JSON)
    - **urgency_level**: Urgency (low/medium/high/critical)
    - **need_decision_by**: Decision deadline
    """
    if not check_permission(current_user.role, Permission.CAN_REPORT_CONFLICT):
        raise ForbiddenException(message="You don't have permission to report conflicts")

    conflict = await service.create_conflict(conflict_data, current_user)
    return ConflictResponse.model_validate(conflict)


@router.get("", response_model=ConflictListResponse)
async def get_conflicts(
    current_user: User = Depends(get_current_user),
    service: ConflictService = Depends(get_conflict_service),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    urgency_level: Optional[str] = Query(None),
    task_id: Optional[int] = Query(None)
) -> ConflictListResponse:
    """
    Get conflicts with pagination and filters.

    Leaders can see all conflicts.
    Regular users can only see conflicts related to their tasks.

    - **page**: Page number
    - **page_size**: Items per page
    - **status**: Filter by status (pending/resolved/escalated)
    - **urgency_level**: Filter by urgency
    - **task_id**: Filter by task
    """
    conflicts_list, total = await service.get_conflicts(
        current_user=current_user,
        page=page,
        page_size=page_size,
        status=status,
        urgency_level=urgency_level,
        task_id=task_id
    )

    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return ConflictListResponse(
        items=[ConflictResponse.model_validate(c) for c in conflicts_list],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/{conflict_id}", response_model=ConflictDetail)
async def get_conflict(
    conflict_id: int,
    current_user: User = Depends(get_current_user),
    service: ConflictService = Depends(get_conflict_service)
) -> ConflictDetail:
    """
    Get a conflict by ID.
    """
    conflict = await service.get_conflict_by_id(conflict_id, current_user)

    # Build response with additional info
    task_result = await service.db.execute(
        select(Task).where(Task.id == conflict.task_id)
    )
    task = task_result.scalar_one_or_none()

    reporter_result = await service.db.execute(
        select(UserModel).where(UserModel.id == conflict.reporter_user_id)
    )
    reporter = reporter_result.scalar_one_or_none()

    reporter_dept_result = await service.db.execute(
        select(Department).where(Department.id == conflict.reporter_dept_id)
    )
    reporter_dept = reporter_dept_result.scalar_one_or_none()

    decision_maker = None
    if conflict.decision_maker_id:
        dm_result = await service.db.execute(
            select(UserModel).where(UserModel.id == conflict.decision_maker_id)
        )
        decision_maker = dm_result.scalar_one_or_none()

    memo_id = None
    if conflict.memo:
        memo_id = conflict.memo.id

    return ConflictDetail(
        id=conflict.id,
        task_id=conflict.task_id,
        reporter_user_id=conflict.reporter_user_id,
        reporter_dept_id=conflict.reporter_dept_id,
        conflict_summary=conflict.conflict_summary,
        conflict_details=conflict.conflict_details,
        proposed_solutions=conflict.proposed_solutions,
        urgency_level=conflict.urgency_level,
        need_decision_by=conflict.need_decision_by,
        decision_made_at=conflict.decision_made_at,
        decision_content=conflict.decision_content,
        decision_maker_id=conflict.decision_maker_id,
        status=conflict.status,
        created_at=conflict.created_at,
        updated_at=conflict.updated_at,
        task_title=task.title if task else None,
        reporter_user_name=reporter.name if reporter else None,
        reporter_dept_name=reporter_dept.name if reporter_dept else None,
        decision_maker_name=decision_maker.name if decision_maker else None,
        memo_id=memo_id
    )


@router.put("/{conflict_id}", response_model=ConflictResponse)
async def update_conflict(
    conflict_id: int,
    conflict_data: ConflictUpdate,
    current_user: User = Depends(get_current_user),
    service: ConflictService = Depends(get_conflict_service)
) -> ConflictResponse:
    """
    Update a conflict report.
    """
    if not check_permission(current_user.role, Permission.CAN_REPORT_CONFLICT):
        raise ForbiddenException(message="You don't have permission to update conflicts")

    conflict = await service.get_conflict_by_id(conflict_id, current_user)

    # Update fields
    update_dict = conflict_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(conflict, field, value)

    await service.db.flush()
    await service.db.refresh(conflict)

    return ConflictResponse.model_validate(conflict)


@router.post("/{conflict_id}/decision", response_model=ConflictResponse)
async def resolve_conflict(
    conflict_id: int,
    decision: ConflictDecision,
    current_user: User = Depends(get_leader_user),
    service: ConflictService = Depends(get_conflict_service)
) -> ConflictResponse:
    """
    Make a decision on a conflict.

    Only leaders can resolve conflicts.

    - **decision_content**: The decision made
    - **solution_selected**: Selected solution (JSON)
    - **notify_departments**: Department IDs to notify
    """
    if not check_permission(current_user.role, Permission.CAN_RESOLVE_CONFLICT):
        raise ForbiddenException(message="You don't have permission to resolve conflicts")

    conflict = await service.resolve_conflict(conflict_id, decision, current_user)
    return ConflictResponse.model_validate(conflict)


@router.post("/{conflict_id}/escalate", response_model=ConflictResponse)
async def escalate_conflict(
    conflict_id: int,
    current_user: User = Depends(get_current_user),
    service: ConflictService = Depends(get_conflict_service)
) -> ConflictResponse:
    """
    Escalate a conflict to higher authority.
    """
    if not check_permission(current_user.role, Permission.CAN_REPORT_CONFLICT):
        raise ForbiddenException(message="You don't have permission to escalate conflicts")

    conflict = await service.escalate_conflict(conflict_id, current_user)
    return ConflictResponse.model_validate(conflict)
