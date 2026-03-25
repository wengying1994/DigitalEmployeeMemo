"""
Reminder API routes.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_leader_user
from app.db.session import get_db
from app.models import User, User as UserModel, Memo
from app.schemas.reminder import (
    ReminderCreate,
    ReminderUpdate,
    ReminderResponse,
    ReminderDetail,
    ReminderListResponse,
    ReminderTest,
)
from app.services.reminder_service import ReminderService
from app.tasks.notification_tasks import send_test_notification


router = APIRouter()


def get_reminder_service(db: AsyncSession = Depends(get_db)) -> ReminderService:
    """Get reminder service instance."""
    service = ReminderService(db)
    service.db = db  # Ensure service has db reference
    return service


@router.get("", response_model=ReminderListResponse)
async def get_my_reminders(
    current_user: User = Depends(get_current_user),
    service: ReminderService = Depends(get_reminder_service),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None)
) -> ReminderListResponse:
    """
    Get reminders for current user.

    - **page**: Page number
    - **page_size**: Items per page
    - **status**: Filter by status (pending/sent/failed/cancelled)
    """
    reminders_list, total = await service.get_user_reminders(
        current_user=current_user,
        page=page,
        page_size=page_size,
        status=status
    )

    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return ReminderListResponse(
        items=[ReminderResponse.model_validate(r) for r in reminders_list],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/{reminder_id}", response_model=ReminderDetail)
async def get_reminder(
    reminder_id: int,
    current_user: User = Depends(get_current_user),
    service: ReminderService = Depends(get_reminder_service)
) -> ReminderDetail:
    """
    Get a reminder by ID.
    """
    reminder = await service.get_reminder_by_id(reminder_id, current_user)

    # Build response with additional info
    target_result = await service.db.execute(
        select(UserModel).where(UserModel.id == reminder.target_user_id)
    )
    target = target_result.scalar_one_or_none()

    memo_result = await service.db.execute(
        select(Memo).where(Memo.id == reminder.memo_id)
    )
    memo = memo_result.scalar_one_or_none()

    return ReminderDetail(
        id=reminder.id,
        target_user_id=reminder.target_user_id,
        memo_id=reminder.memo_id,
        trigger_type=reminder.trigger_type,
        trigger_time=reminder.trigger_time,
        reminder_methods=reminder.reminder_methods,
        status=reminder.status,
        retry_count=reminder.retry_count,
        last_sent_at=reminder.last_sent_at,
        sent_at=reminder.sent_at,
        created_at=reminder.created_at,
        updated_at=reminder.updated_at,
        target_user_name=target.name if target else None,
        memo_title=memo.title if memo else None
    )


@router.post("/test", status_code=201)
async def test_reminder(
    test_data: ReminderTest,
    current_user: User = Depends(get_leader_user)
) -> dict:
    """
    Test sending a reminder (for development/testing only).

    Only leaders can use this endpoint.

    - **user_id**: Target user ID
    - **method**: Reminder method (in_app/email/wechat/sms)
    - **message**: Custom message
    """
    # Send test notification
    send_test_notification.delay(
        user_id=test_data.user_id,
        method=test_data.method,
        message=test_data.message or "This is a test notification"
    )

    return {
        "code": 0,
        "message": "Test notification sent",
        "data": {
            "user_id": test_data.user_id,
            "method": test_data.method
        }
    }
