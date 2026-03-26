"""
Message service for business logic related to bidirectional messaging.
"""
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, ResourceNotFoundException
from app.core.logger import LoggerMixin, audit_log, OperationType
from app.models import User
from app.models.message import Message
from app.schemas.message import MessageCreate, MessageUpdate


class MessageService(LoggerMixin):
    """Service for message-related business logic."""

    def __init__(self, db: AsyncSession):
        """
        Initialize message service.

        Args:
            db: Database session
        """
        self.db = db

    async def create_message(
        self,
        message_data: MessageCreate,
        current_user: User
    ) -> Message:
        """
        Create a new message.

        Args:
            message_data: Message creation data
            current_user: Current authenticated user

        Returns:
            Created message instance
        """
        # Permission check: employees can only send to leaders
        if current_user.role != "leader" and message_data.receiver_id:
            # Check if receiver is a leader
            receiver_result = await self.db.execute(
                select(User).where(User.id == message_data.receiver_id)
            )
            receiver = receiver_result.scalar_one_or_none()
            if receiver and receiver.role != "leader":
                raise ForbiddenException(message="员工只能给领导发送消息")

        message = Message(
            sender_id=current_user.id,
            receiver_id=message_data.receiver_id,
            title=message_data.title,
            content=message_data.content,
            is_read=False
        )

        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)

        # Audit log
        audit_log.log(
            operation=OperationType.CREATE,
            user_id=current_user.id,
            resource_type="message",
            resource_id=message.id,
            dept_id=current_user.dept_id,
            details={
                "receiver_id": message_data.receiver_id,
                "title": message_data.title
            }
        )

        self.logger.info(f"Message {message.id} created by user {current_user.id}")

        return message

    async def get_message_by_id(
        self,
        message_id: int,
        current_user: User
    ) -> Message:
        """
        Get a message by ID with access control.

        Args:
            message_id: Message ID
            current_user: Current authenticated user

        Returns:
            Message instance

        Raises:
            ResourceNotFoundException: If message not found
            ForbiddenException: If user has no access
        """
        result = await self.db.execute(
            select(Message).where(Message.id == message_id)
        )
        message = result.scalar_one_or_none()

        if not message:
            raise ResourceNotFoundException("Message", message_id)

        # Access control: sender or receiver can view
        if message.sender_id != current_user.id and message.receiver_id != current_user.id:
            raise ForbiddenException(message="您没有权限查看此消息")

        return message

    async def get_messages(
        self,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
        direction: Optional[str] = None  # "sent", "received", or None for all
    ) -> Tuple[List[Message], int]:
        """
        Get messages for the current user.

        Args:
            current_user: Current authenticated user
            page: Page number
            page_size: Items per page
            direction: Filter by "sent" or "received"

        Returns:
            Tuple of (messages list, total count)
        """
        if direction == "sent":
            query = select(Message).where(Message.sender_id == current_user.id)
            count_query = select(Message.id).where(Message.sender_id == current_user.id)
        elif direction == "received":
            query = select(Message).where(Message.receiver_id == current_user.id)
            count_query = select(Message.id).where(Message.receiver_id == current_user.id)
        else:
            # All messages: sent or received by current user
            query = select(Message).where(
                or_(
                    Message.sender_id == current_user.id,
                    Message.receiver_id == current_user.id
                )
            )
            count_query = select(Message.id).where(
                or_(
                    Message.sender_id == current_user.id,
                    Message.receiver_id == current_user.id
                )
            )

        # Count
        count_result = await self.db.execute(count_query)
        total = len(count_result.scalars().all())

        # Paginate
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(Message.created_at.desc())

        result = await self.db.execute(query)
        messages = list(result.scalars().all())

        return messages, total

    async def mark_as_read(
        self,
        message_id: int,
        current_user: User
    ) -> Message:
        """
        Mark a message as read.

        Args:
            message_id: Message ID
            current_user: Current authenticated user

        Returns:
            Updated message instance
        """
        message = await self.get_message_by_id(message_id, current_user)

        # Only receiver can mark as read
        if message.receiver_id and message.receiver_id != current_user.id:
            raise ForbiddenException(message="只有接收者可以标记消息为已读")

        message.is_read = True
        message.read_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(message)

        return message

    async def delete_message(
        self,
        message_id: int,
        current_user: User
    ) -> None:
        """
        Delete a message (soft delete by marking as read as a form of archive).

        Args:
            message_id: Message ID
            current_user: Current authenticated user
        """
        message = await self.get_message_by_id(message_id, current_user)

        # Only sender can delete
        if message.sender_id != current_user.id:
            raise ForbiddenException(message="只有发送者可以删除消息")

        await self.db.delete(message)
        await self.db.flush()
