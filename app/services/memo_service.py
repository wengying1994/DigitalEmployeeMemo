"""
Memo service for business logic related to leader memos.
"""
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    ForbiddenException,
    MemoNotFoundException,
    ResourceNotFoundException,
)
from app.core.logger import LoggerMixin, audit_log, OperationType
from app.models import Memo, MemoStatus, MemoType, Task, User
from app.models.conflict_report import ConflictReport, ConflictStatus
from app.models.reminder import Reminder, ReminderStatus
from app.schemas.memo import MemoUpdate, LeaderDashboard


class MemoService(LoggerMixin):
    """Service for memo-related business logic."""

    def __init__(self, db: AsyncSession):
        """
        Initialize memo service.

        Args:
            db: Database session
        """
        self.db = db

    async def get_memo_by_id(
        self,
        memo_id: int,
        current_user: User
    ) -> Memo:
        """
        Get a memo by ID.

        Args:
            memo_id: Memo ID
            current_user: Current authenticated user

        Returns:
            Memo instance
        """
        result = await self.db.execute(
            select(Memo).where(Memo.id == memo_id)
        )
        memo = result.scalar_one_or_none()

        if not memo:
            raise MemoNotFoundException(memo_id)

        # Access control
        if current_user.role != "leader":
            # Must be the memo recipient or a collaborator
            if memo.user_id != current_user.id:
                # Check if user is a collaborator
                from app.models.collaborator import Collaborator
                collab_result = await self.db.execute(
                    select(Collaborator).where(
                        and_(
                            Collaborator.memo_id == memo_id,
                            Collaborator.user_id == current_user.id
                        )
                    )
                )
                if not collab_result.scalar_one_or_none():
                    raise ForbiddenException()

        return memo

    async def get_leader_pending_memos(
        self,
        current_user: User,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Memo], int]:
        """
        Get pending memos for the leader.

        Args:
            current_user: Current authenticated user (must be leader)
            page: Page number
            page_size: Items per page

        Returns:
            Tuple of (memos list, total count)
        """
        if current_user.role != "leader":
            raise ForbiddenException()

        query = select(Memo).where(
            and_(
                Memo.user_id == current_user.id,
                Memo.status.in_([MemoStatus.UNREAD, MemoStatus.READ])
            )
        )

        # Count
        count_query = select(Memo.id).where(
            and_(
                Memo.user_id == current_user.id,
                Memo.status.in_([MemoStatus.UNREAD, MemoStatus.READ])
            )
        )
        count_result = await self.db.execute(count_query)
        total = len(count_result.scalars().all())

        # Paginate
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(Memo.created_at.desc())

        result = await self.db.execute(query)
        memos = result.scalars().all()

        return list(memos), total

    async def get_memos(
        self,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        memo_type: Optional[str] = None
    ) -> Tuple[List[Memo], int]:
        """
        Get memos for current user.

        Args:
            current_user: Current authenticated user
            page: Page number
            page_size: Items per page
            status: Filter by status
            memo_type: Filter by type

        Returns:
            Tuple of (memos list, total count)
        """
        # Build query based on user role
        if current_user.role == "leader":
            # Leaders see their own memos and ones they're collaborated on
            query = select(Memo).where(
                or_(
                    Memo.user_id == current_user.id,
                    Memo.id.in_(
                        select(Reminder.memo_id).where(
                            Reminder.target_user_id == current_user.id
                        )
                    )
                )
            )
        else:
            # Non-leaders only see memos they're collaborated on
            from app.models.collaborator import Collaborator
            query = select(Memo).join(
                Collaborator,
                Memo.id == Collaborator.memo_id
            ).where(Collaborator.user_id == current_user.id)

        # Apply filters
        if status:
            query = query.where(Memo.status == status)
        if memo_type:
            query = query.where(Memo.memo_type == memo_type)

        # Count
        count_result = await self.db.execute(
            select(Memo.id).where(
                or_(
                    Memo.user_id == current_user.id,
                    Memo.id.in_(
                        select(Reminder.memo_id).where(
                            Reminder.target_user_id == current_user.id
                        )
                    )
                )
            )
        )
        total = len(count_result.scalars().all())

        # Paginate
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(Memo.created_at.desc())

        result = await self.db.execute(query)
        memos = result.scalars().all()

        return list(memos), total

    async def update_memo_status(
        self,
        memo_id: int,
        status: str,
        current_user: User
    ) -> Memo:
        """
        Update memo read status.

        Args:
            memo_id: Memo ID
            status: New status
            current_user: Current authenticated user

        Returns:
            Updated memo
        """
        memo = await self.get_memo_by_id(memo_id, current_user)

        # Only memo recipient can update status
        if memo.user_id != current_user.id and current_user.role != "leader":
            raise ForbiddenException()

        old_status = memo.status
        memo.status = status

        # Update read_at if marking as read
        if status == MemoStatus.READ and old_status == MemoStatus.UNREAD:
            memo.read_at = datetime.utcnow()

        # If resolving, also update related conflict
        if status == MemoStatus.RESOLVED and memo.memo_type == MemoType.CONFLICT:
            conflict_result = await self.db.execute(
                select(ConflictReport).where(ConflictReport.id == memo.related_id)
            )
            conflict = conflict_result.scalar_one_or_none()
            if conflict:
                conflict.status = ConflictStatus.RESOLVED
                conflict.decision_made_at = datetime.utcnow()
                conflict.decision_maker_id = current_user.id

            # Cancel pending reminders
            reminders_result = await self.db.execute(
                select(Reminder).where(
                    and_(
                        Reminder.memo_id == memo_id,
                        Reminder.status == ReminderStatus.PENDING
                    )
                )
            )
            for reminder in reminders_result.scalars().all():
                reminder.status = ReminderStatus.CANCELLED

        await self.db.flush()

        # Audit log
        audit_log.log(
            operation=OperationType.UPDATE,
            user_id=current_user.id,
            resource_type="memo",
            resource_id=memo.id,
            dept_id=current_user.dept_id,
            details={"old_status": old_status, "new_status": status}
        )

        self.logger.info(
            f"Memo {memo_id} status updated from {old_status} to {status} by user {current_user.id}"
        )
        return memo

    async def get_leader_dashboard(
        self,
        current_user: User
    ) -> LeaderDashboard:
        """
        Get leader dashboard statistics.

        Args:
            current_user: Current authenticated user (must be leader)

        Returns:
            Dashboard statistics
        """
        if current_user.role != "leader":
            raise ForbiddenException()

        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Count pending memos
        pending_memos_result = await self.db.execute(
            select(Memo).where(
                and_(
                    Memo.user_id == current_user.id,
                    Memo.status == MemoStatus.UNREAD
                )
            )
        )
        pending_memos = list(pending_memos_result.scalars().all())

        # Count unread memos
        unread_memos_result = await self.db.execute(
            select(Memo).where(
                and_(
                    Memo.user_id == current_user.id,
                    Memo.status == MemoStatus.UNREAD
                )
            )
        )
        unread_count = len(unread_memos_result.scalars().all())

        # Count resolved today
        resolved_today_result = await self.db.execute(
            select(Memo).where(
                and_(
                    Memo.user_id == current_user.id,
                    Memo.status == MemoStatus.RESOLVED,
                    Memo.updated_at >= today_start
                )
            )
        )
        resolved_today = len(resolved_today_result.scalars().all())

        # Count pending conflicts
        pending_conflicts_result = await self.db.execute(
            select(ConflictReport).where(
                ConflictReport.status == ConflictStatus.PENDING
            )
        )
        pending_conflicts = list(pending_conflicts_result.scalars().all())

        # Count urgent conflicts
        from app.models.conflict_report import UrgencyLevel
        urgent_conflicts = [
            c for c in pending_conflicts
            if c.urgency_level in [UrgencyLevel.HIGH, UrgencyLevel.CRITICAL]
        ]

        # Count tasks
        tasks_result = await self.db.execute(
            select(Task).where(Task.is_deleted == False)
        )
        tasks = list(tasks_result.scalars().all())

        # Get recent memos
        recent_memos_result = await self.db.execute(
            select(Memo)
            .where(Memo.user_id == current_user.id)
            .order_by(Memo.created_at.desc())
            .limit(5)
        )
        recent_memos = list(recent_memos_result.scalars().all())

        # Get urgent conflicts
        urgent_conflicts_result = await self.db.execute(
            select(ConflictReport)
            .where(
                and_(
                    ConflictReport.status == ConflictStatus.PENDING,
                    ConflictReport.urgency_level.in_([UrgencyLevel.HIGH, UrgencyLevel.CRITICAL])
                )
            )
            .order_by(ConflictReport.created_at.desc())
            .limit(5)
        )
        urgent_conflicts_list = list(urgent_conflicts_result.scalars().all())

        return LeaderDashboard(
            pending_memos_count=len(pending_memos),
            unread_memos_count=unread_count,
            resolved_today_count=resolved_today,
            pending_conflicts_count=len(pending_conflicts),
            urgent_conflicts_count=len(urgent_conflicts),
            tasks_in_progress_count=sum(1 for t in tasks if t.status == "in_progress"),
            tasks_coordinating_count=sum(1 for t in tasks if t.status == "coordinating"),
            tasks_near_deadline_count=sum(
                1 for t in tasks
                if t.deadline and t.deadline <= now + timedelta(days=3)
            ),
            recent_memos=recent_memos,
            urgent_conflicts=urgent_conflicts_list
        )
