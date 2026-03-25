"""
Memo API routes.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_leader_user, get_pagination_params
from app.core.exceptions import ForbiddenException
from app.core.security import Permission, check_permission
from app.db.session import get_db
from app.models import User, User as UserModel, Task
from app.schemas.memo import (
    MemoUpdate,
    MemoReadStatusUpdate,
    MemoDecision,
    MemoResponse,
    MemoDetail,
    MemoListResponse,
)
from app.services.memo_service import MemoService
from app.services.conflict_service import ConflictService
from app.schemas.conflict import ConflictDecision


router = APIRouter()


def get_memo_service(db: AsyncSession = Depends(get_db)) -> MemoService:
    """Get memo service instance."""
    service = MemoService(db)
    service.db = db  # Ensure service has db reference
    return service


@router.get("/leader/pending", response_model=MemoListResponse)
async def get_leader_pending_memos(
    current_user: User = Depends(get_leader_user),
    service: MemoService = Depends(get_memo_service),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
) -> MemoListResponse:
    """
    Get pending memos for the current leader.

    Only leaders can access this endpoint.

    - **page**: Page number
    - **page_size**: Items per page
    """
    memos_list, total = await service.get_leader_pending_memos(
        current_user=current_user,
        page=page,
        page_size=page_size
    )

    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return MemoListResponse(
        items=[MemoResponse.model_validate(m) for m in memos_list],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("", response_model=MemoListResponse)
async def get_memos(
    current_user: User = Depends(get_current_user),
    service: MemoService = Depends(get_memo_service),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    memo_type: Optional[str] = Query(None)
) -> MemoListResponse:
    """
    Get memos for current user.

    - **page**: Page number
    - **page_size**: Items per page
    - **status**: Filter by status (unread/read/resolved)
    - **memo_type**: Filter by type (conflict/approval/info)
    """
    memos_list, total = await service.get_memos(
        current_user=current_user,
        page=page,
        page_size=page_size,
        status=status,
        memo_type=memo_type
    )

    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return MemoListResponse(
        items=[MemoResponse.model_validate(m) for m in memos_list],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/{memo_id}", response_model=MemoDetail)
async def get_memo(
    memo_id: int,
    current_user: User = Depends(get_current_user),
    service: MemoService = Depends(get_memo_service)
) -> MemoDetail:
    """
    Get a memo by ID.
    """
    memo = await service.get_memo_by_id(memo_id, current_user)

    # Build response with additional info
    leader_result = await service.db.execute(
        select(UserModel).where(UserModel.id == memo.user_id)
    )
    leader = leader_result.scalar_one_or_none()

    task = None
    if memo.related_task_id:
        task_result = await service.db.execute(
            select(Task).where(Task.id == memo.related_task_id)
        )
        task = task_result.scalar_one_or_none()

    conflict_id = None
    if memo.memo_type == "conflict" and memo.related_id:
        conflict_id = memo.related_id

    return MemoDetail(
        id=memo.id,
        user_id=memo.user_id,
        title=memo.title,
        content=memo.content,
        full_memo_text=memo.full_memo_text,
        memo_type=memo.memo_type,
        related_id=memo.related_id,
        related_task_id=memo.related_task_id,
        status=memo.status,
        read_at=memo.read_at,
        created_at=memo.created_at,
        updated_at=memo.updated_at,
        leader_name=leader.name if leader else None,
        task_title=task.title if task else None,
        conflict_id=conflict_id,
        reminders_count=0
    )


@router.put("/{memo_id}/read-status", response_model=MemoResponse)
async def update_memo_read_status(
    memo_id: int,
    status_update: MemoReadStatusUpdate,
    current_user: User = Depends(get_current_user),
    service: MemoService = Depends(get_memo_service)
) -> MemoResponse:
    """
    Update memo read status.

    This is used to mark a memo as read, which stops reminders.

    - **status**: New status (unread/read/resolved)
    """
    memo = await service.update_memo_status(
        memo_id=memo_id,
        status=status_update.status,
        current_user=current_user
    )
    return MemoResponse.model_validate(memo)


@router.post("/{memo_id}/decision", response_model=MemoResponse)
async def make_decision(
    memo_id: int,
    decision: MemoDecision,
    current_user: User = Depends(get_leader_user),
    service: MemoService = Depends(get_memo_service)
) -> MemoResponse:
    """
    Make a decision on a memo (conflict).

    Only leaders can make decisions.

    - **decision_content**: The decision made
    - **notify_departments**: Department IDs to notify
    """
    if not check_permission(current_user.role, Permission.CAN_DECIDE_MEMO):
        raise ForbiddenException(message="You don't have permission to make decisions")

    # Get memo first
    memo = await service.get_memo_by_id(memo_id, current_user)

    # Update memo status to resolved
    memo = await service.update_memo_status(
        memo_id=memo_id,
        status="resolved",
        current_user=current_user
    )

    # If this is a conflict memo, also update the conflict
    if memo.memo_type == "conflict" and memo.related_id:
        async with service.db.begin():
            conflict_service = ConflictService(service.db)
            await conflict_service.resolve_conflict(
                conflict_id=memo.related_id,
                decision=ConflictDecision(
                    decision_content=decision.decision_content,
                    notify_departments=decision.notify_departments
                ),
                current_user=current_user
            )

    return MemoResponse.model_validate(memo)
