"""
Message API routes for bidirectional messaging.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import ForbiddenException
from app.db.session import get_db
from app.models import User
from app.schemas.message import (
    MessageCreate,
    MessageUpdate,
    MessageResponse,
    MessageDetail,
    MessageListResponse,
)
from app.services.message_service import MessageService


router = APIRouter()


def get_message_service(db: AsyncSession = Depends(get_db)) -> MessageService:
    """Get message service instance."""
    return MessageService(db)


@router.post("", response_model=MessageResponse, status_code=201)
async def create_message(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    service: MessageService = Depends(get_message_service)
) -> MessageResponse:
    """
    Send a new message.

    - **title**: Message title
    - **content**: Message content
    - **receiver_id**: Receiver user ID (null for broadcast to leaders)
    """
    message = await service.create_message(message_data, current_user)
    return MessageResponse.model_validate(message)


@router.get("", response_model=MessageListResponse)
async def get_messages(
    current_user: User = Depends(get_current_user),
    service: MessageService = Depends(get_message_service),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    direction: Optional[str] = Query(None, description="Filter: sent, received, or all")
) -> MessageListResponse:
    """
    Get messages for the current user.

    - **page**: Page number
    - **page_size**: Items per page
    - **direction**: Filter by "sent" or "received"
    """
    if direction and direction not in ["sent", "received"]:
        direction = None

    messages, total = await service.get_messages(
        current_user=current_user,
        page=page,
        page_size=page_size,
        direction=direction
    )

    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return MessageListResponse(
        items=[MessageResponse.model_validate(m) for m in messages],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/{message_id}", response_model=MessageDetail)
async def get_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    service: MessageService = Depends(get_message_service)
) -> MessageDetail:
    """
    Get a message by ID.
    """
    message = await service.get_message_by_id(message_id, current_user)

    # Get sender and receiver names
    from sqlalchemy import select
    from app.models import User as UserModel

    sender_result = await service.db.execute(
        select(UserModel.name).where(UserModel.id == message.sender_id)
    )
    sender_name = sender_result.scalar_one_or_none()

    receiver_name = None
    if message.receiver_id:
        receiver_result = await service.db.execute(
            select(UserModel.name).where(UserModel.id == message.receiver_id)
        )
        receiver_name = receiver_result.scalar_one_or_none()

    return MessageDetail(
        id=message.id,
        sender_id=message.sender_id,
        receiver_id=message.receiver_id,
        title=message.title,
        content=message.content,
        is_read=message.is_read,
        read_at=message.read_at,
        created_at=message.created_at,
        updated_at=message.updated_at,
        sender_name=sender_name,
        receiver_name=receiver_name
    )


@router.put("/{message_id}/read", response_model=MessageResponse)
async def mark_message_read(
    message_id: int,
    current_user: User = Depends(get_current_user),
    service: MessageService = Depends(get_message_service)
) -> MessageResponse:
    """
    Mark a message as read.
    """
    message = await service.mark_as_read(message_id, current_user)
    return MessageResponse.model_validate(message)


@router.delete("/{message_id}", status_code=204)
async def delete_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    service: MessageService = Depends(get_message_service)
) -> None:
    """
    Delete a message. Only the sender can delete.
    """
    await service.delete_message(message_id, current_user)
