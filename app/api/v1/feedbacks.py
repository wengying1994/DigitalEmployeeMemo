"""
Feedback API routes.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_pagination_params
from app.db.session import get_db
from app.models import User, Department, Assignment, Task
from app.schemas.feedback import (
    FeedbackCreate,
    FeedbackResponse,
    FeedbackDetail,
    FeedbackListResponse,
)
from app.services.feedback_service import FeedbackService


router = APIRouter()


def get_feedback_service(db: AsyncSession = Depends(get_db)) -> FeedbackService:
    """Get feedback service instance."""
    service = FeedbackService(db)
    service.db = db  # Ensure service has db reference
    return service


@router.post("/assignments/{assignment_id}/feedback", response_model=FeedbackResponse, status_code=201)
async def create_feedback(
    assignment_id: int,
    feedback_data: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    service: FeedbackService = Depends(get_feedback_service)
) -> FeedbackResponse:
    """
    Submit feedback for an assignment.

    Only the department assigned to the assignment can submit feedback.

    - **assignment_id**: Assignment ID
    - **feedback_type**: Type (agree/disagree/need_discussion)
    - **reason**: Reason for feedback
    - **proposed_changes**: Proposed changes (JSON)
    - **attachments**: Attachments (JSON)
    """
    feedback = await service.create_feedback(assignment_id, feedback_data, current_user)
    return FeedbackResponse.model_validate(feedback)


@router.get("/assignments/{assignment_id}/feedbacks", response_model=FeedbackListResponse)
async def get_assignment_feedbacks(
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    service: FeedbackService = Depends(get_feedback_service),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
) -> FeedbackListResponse:
    """
    Get feedbacks for an assignment.

    - **assignment_id**: Assignment ID
    - **page**: Page number
    - **page_size**: Items per page
    """
    feedbacks_list, total = await service.get_assignment_feedbacks(
        assignment_id=assignment_id,
        current_user=current_user,
        page=page,
        page_size=page_size
    )

    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return FeedbackListResponse(
        items=[FeedbackResponse.model_validate(f) for f in feedbacks_list],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/feedbacks/my", response_model=FeedbackListResponse)
async def get_my_feedbacks(
    current_user: User = Depends(get_current_user),
    service: FeedbackService = Depends(get_feedback_service),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    feedback_type: Optional[str] = Query(None)
) -> FeedbackListResponse:
    """
    Get feedbacks submitted by current user's department.

    - **page**: Page number
    - **page_size**: Items per page
    - **feedback_type**: Filter by feedback type
    """
    feedbacks_list, total = await service.get_department_feedbacks(
        current_user=current_user,
        page=page,
        page_size=page_size,
        feedback_type=feedback_type
    )

    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return FeedbackListResponse(
        items=[FeedbackResponse.model_validate(f) for f in feedbacks_list],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/{feedback_id}", response_model=FeedbackDetail)
async def get_feedback(
    feedback_id: int,
    current_user: User = Depends(get_current_user),
    service: FeedbackService = Depends(get_feedback_service)
) -> FeedbackDetail:
    """
    Get a feedback by ID.
    """
    feedback = await service.get_feedback_by_id(feedback_id, current_user)

    # Build response with additional info
    dept_result = await service.db.execute(
        select(Department).where(Department.id == feedback.dept_id)
    )
    dept = dept_result.scalar_one_or_none()

    assignment_result = await service.db.execute(
        select(Assignment).where(Assignment.id == feedback.assignment_id)
    )
    assignment = assignment_result.scalar_one_or_none()

    task_title = None
    if assignment:
        task_result = await service.db.execute(
            select(Task).where(Task.id == assignment.task_id)
        )
        task = task_result.scalar_one_or_none()
        task_title = task.title if task else None

    return FeedbackDetail(
        id=feedback.id,
        assignment_id=feedback.assignment_id,
        dept_id=feedback.dept_id,
        feedback_type=feedback.feedback_type,
        reason=feedback.reason,
        proposed_changes=feedback.proposed_changes,
        attachments=feedback.attachments,
        created_at=feedback.created_at,
        updated_at=feedback.updated_at,
        dept_name=dept.name if dept else None,
        assignment_task_title=task_title
    )
