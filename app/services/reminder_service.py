"""
Reminder service for business logic related to reminders.
"""
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundException
from app.core.logger import LoggerMixin, audit_log, OperationType
from app.models import Memo, Reminder, ReminderStatus, ReminderTriggerType, User
from app.schemas.reminder import ReminderCreate


class ReminderService(LoggerMixin):
    """Service for reminder-related business logic."""

    def __init__(self, db: AsyncSession):
        """
        Initialize reminder service.

        Args:
            db: Database session
        """
        self.db = db

    async def create_reminder(
        self,
        reminder_data: ReminderCreate,
        current_user: User
    ) -> Reminder:
        """
        Create a new reminder.

        Args:
            reminder_data: Reminder creation data
            current_user: Current authenticated user

        Returns:
            Created reminder instance
        """
        # Verify target user exists
        target_user = await self.db.get(User, reminder_data.target_user_id)
        if not target_user:
            raise ResourceNotFoundException("User", reminder_data.target_user_id)

        # Verify memo exists
        memo = await self.db.get(Memo, reminder_data.memo_id)
        if not memo:
            raise ResourceNotFoundException("Memo", reminder_data.memo_id)

        # Create reminder
        reminder = Reminder(
            target_user_id=reminder_data.target_user_id,
            memo_id=reminder_data.memo_id,
            trigger_type=reminder_data.trigger_type,
            trigger_time=reminder_data.trigger_time,
            reminder_methods=reminder_data.reminder_methods,
            status=ReminderStatus.PENDING
        )

        self.db.add(reminder)
        await self.db.flush()
        await self.db.refresh(reminder)

        # Audit log
        audit_log.log(
            operation=OperationType.CREATE,
            user_id=current_user.id,
            resource_type="reminder",
            resource_id=reminder.id,
            dept_id=current_user.dept_id,
            details={
                "target_user_id": reminder_data.target_user_id,
                "memo_id": reminder_data.memo_id
            }
        )

        self.logger.info(
            f"Reminder created: {reminder.id} for memo {reminder_data.memo_id} "
            f"to user {reminder_data.target_user_id}"
        )
        return reminder

    async def get_reminder_by_id(
        self,
        reminder_id: int,
        current_user: User
    ) -> Reminder:
        """
        Get a reminder by ID.

        Args:
            reminder_id: Reminder ID
            current_user: Current authenticated user

        Returns:
            Reminder instance
        """
        result = await self.db.execute(
            select(Reminder).where(Reminder.id == reminder_id)
        )
        reminder = result.scalar_one_or_none()

        if not reminder:
            from app.core.exceptions import ResourceNotFoundException
            raise ResourceNotFoundException("Reminder", reminder_id)

        # Access control: only target user or leaders can view
        if reminder.target_user_id != current_user.id and current_user.role != "leader":
            from app.core.exceptions import ForbiddenException
            raise ForbiddenException()

        return reminder

    async def get_user_reminders(
        self,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None
    ) -> Tuple[List[Reminder], int]:
        """
        Get reminders for current user.

        Args:
            current_user: Current authenticated user
            page: Page number
            page_size: Items per page
            status: Filter by status

        Returns:
            Tuple of (reminders list, total count)
        """
        query = select(Reminder).where(Reminder.target_user_id == current_user.id)

        if status:
            query = query.where(Reminder.status == status)

        # Count
        count_query = select(Reminder.id).where(Reminder.target_user_id == current_user.id)
        if status:
            count_query = count_query.where(Reminder.status == status)
        count_result = await self.db.execute(count_query)
        total = len(count_result.scalars().all())

        # Paginate
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(Reminder.trigger_time.asc())

        result = await self.db.execute(query)
        reminders = result.scalars().all()

        return list(reminders), total

    async def get_pending_reminders(
        self,
        check_time: datetime
    ) -> List[Reminder]:
        """
        Get all pending reminders that should be sent.

        Args:
            check_time: Current time to check against

        Returns:
            List of reminders to send
        """
        query = select(Reminder).where(
            and_(
                Reminder.status == ReminderStatus.PENDING,
                Reminder.trigger_time <= check_time
            )
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def mark_reminder_sent(
        self,
        reminder_id: int,
        success: bool = True
    ) -> Reminder:
        """
        Mark a reminder as sent.

        Args:
            reminder_id: Reminder ID
            success: Whether sending was successful

        Returns:
            Updated reminder
        """
        reminder = await self.db.get(Reminder, reminder_id)
        if not reminder:
            from app.core.exceptions import ResourceNotFoundException
            raise ResourceNotFoundException("Reminder", reminder_id)

        if success:
            reminder.status = ReminderStatus.SENT
            reminder.sent_at = datetime.utcnow()
        else:
            reminder.retry_count += 1
            reminder.last_sent_at = datetime.utcnow()

            # Mark as failed if too many retries
            if reminder.retry_count >= 3:
                reminder.status = ReminderStatus.FAILED

        await self.db.flush()
        await self.db.refresh(reminder)

        self.logger.info(
            f"Reminder {reminder_id} marked as {'sent' if success else 'failed'} "
            f"(retry count: {reminder.retry_count})"
        )
        return reminder

    async def cancel_reminder(
        self,
        reminder_id: int,
        current_user: User
    ) -> Reminder:
        """
        Cancel a reminder.

        Args:
            reminder_id: Reminder ID
            current_user: Current authenticated user

        Returns:
            Updated reminder
        """
        reminder = await self.get_reminder_by_id(reminder_id, current_user)

        # Only target user or system can cancel
        if reminder.target_user_id != current_user.id and current_user.role != "leader":
            from app.core.exceptions import ForbiddenException
            raise ForbiddenException()

        reminder.status = ReminderStatus.CANCELLED
        await self.db.flush()

        self.logger.info(f"Reminder {reminder_id} cancelled by user {current_user.id}")
        return reminder

    async def create_scheduled_reminders(
        self,
        memo_id: int,
        target_user_id: int,
        policy: dict
    ) -> List[Reminder]:
        """
        Create scheduled reminders based on policy.

        Args:
            memo_id: Memo ID
            target_user_id: Target user ID
            policy: Reminder policy configuration

        Returns:
            List of created reminders
        """
        created_reminders = []
        now = datetime.utcnow()

        # Get memo to determine base time
        memo = await self.db.get(Memo, memo_id)
        if not memo:
            return []

        # Use created_at as base time
        base_time = memo.created_at

        for stage_name, config in policy.items():
            if stage_name == "immediate":
                # Already handled separately
                continue

            delay = config.get("delay", 0)
            methods = config.get("methods", ["in_app"])

            trigger_time = base_time + timedelta(seconds=delay)

            # Skip if trigger time is in the past
            if trigger_time <= now:
                continue

            reminder = Reminder(
                target_user_id=target_user_id,
                memo_id=memo_id,
                trigger_type=ReminderTriggerType.CONDITION,
                trigger_time=trigger_time,
                reminder_methods={"methods": methods, "stage": stage_name},
                status=ReminderStatus.PENDING
            )

            self.db.add(reminder)
            created_reminders.append(reminder)

        if created_reminders:
            await self.db.flush()

        self.logger.info(
            f"Created {len(created_reminders)} scheduled reminders for memo {memo_id}"
        )
        return created_reminders
