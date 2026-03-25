"""
Conflict service for business logic related to conflict reports.
"""
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    ConflictAlreadyResolvedException,
    ConflictNotFoundException,
    ForbiddenException,
    ResourceNotFoundException,
    TaskNotFoundException,
)
from app.core.logger import LoggerMixin, audit_log, OperationType
from app.models import Memo, MemoStatus, MemoType, Task, User
from app.models.conflict_report import ConflictReport, ConflictStatus, UrgencyLevel
from app.schemas.conflict import ConflictCreate, ConflictDecision, ConflictUpdate
from app.services.memo_service import MemoService
from app.services.notification_service import NotificationService


class ConflictService(LoggerMixin):
    """Service for conflict-related business logic."""

    def __init__(self, db: AsyncSession):
        """
        Initialize conflict service.

        Args:
            db: Database session
        """
        self.db = db
        self.memo_service = MemoService(db)
        self.notification_service = NotificationService()

    async def create_conflict(
        self,
        conflict_data: ConflictCreate,
        current_user: User
    ) -> ConflictReport:
        """
        Create a new conflict report and auto-generate a memo.

        Args:
            conflict_data: Conflict creation data
            current_user: Current authenticated user

        Returns:
            Created conflict report instance
        """
        # Verify task exists
        task_result = await self.db.execute(
            select(Task).where(
                and_(
                    Task.id == conflict_data.task_id,
                    Task.is_deleted == False
                )
            )
        )
        task = task_result.scalar_one_or_none()
        if not task:
            raise TaskNotFoundException(conflict_data.task_id)

        # Access control: must be lead department or leader
        if current_user.role != "leader" and task.lead_dept_id != current_user.dept_id:
            raise ForbiddenException()

        # Get task creator (who should receive the memo)
        task_creator_result = await self.db.execute(
            select(User).where(User.id == task.created_by)
        )
        task_creator = task_creator_result.scalar_one_or_none()

        # Determine who should receive the memo (task creator or their department leader)
        memo_recipient_id = task.created_by
        if task_creator and task_creator.role != "leader":
            # If task creator is not a leader, the memo goes to their department leader
            if task_creator.dept_id:
                dept_leader_result = await self.db.execute(
                    select(User).where(
                        and_(
                            User.dept_id == task_creator.dept_id,
                            User.role == "leader"
                        )
                    )
                )
                dept_leader = dept_leader_result.scalar_one_or_none()
                if dept_leader:
                    memo_recipient_id = dept_leader.id

        # Create conflict report
        conflict = ConflictReport(
            task_id=conflict_data.task_id,
            reporter_user_id=current_user.id,
            reporter_dept_id=current_user.dept_id,
            conflict_summary=conflict_data.conflict_summary,
            conflict_details=conflict_data.conflict_details,
            proposed_solutions=conflict_data.proposed_solutions,
            urgency_level=conflict_data.urgency_level,
            need_decision_by=conflict_data.need_decision_by,
            status=ConflictStatus.PENDING
        )

        self.db.add(conflict)
        await self.db.flush()
        await self.db.refresh(conflict)

        # Auto-generate memo for the leader
        memo_title = f"冲突报告：{conflict_data.conflict_summary[:50]}"
        if len(conflict_data.conflict_summary) > 50:
            memo_title += "..."

        memo_content = {
            "conflict_id": conflict.id,
            "task_id": conflict_data.task_id,
            "task_title": task.title,
            "reporter_user_id": current_user.id,
            "reporter_user_name": current_user.name,
            "reporter_dept_id": current_user.dept_id,
            "conflict_summary": conflict_data.conflict_summary,
            "conflict_details": conflict_data.conflict_details,
            "proposed_solutions": conflict_data.proposed_solutions,
            "urgency_level": conflict_data.urgency_level,
            "need_decision_by": conflict_data.need_decision_by.isoformat() if conflict_data.need_decision_by else None,
        }

        memo = Memo(
            user_id=memo_recipient_id,
            title=memo_title,
            content=memo_content,
            full_memo_text=self._generate_memo_text(task, conflict, current_user),
            memo_type=MemoType.CONFLICT,
            related_id=conflict.id,
            related_task_id=conflict_data.task_id,
            status=MemoStatus.UNREAD
        )

        self.db.add(memo)
        await self.db.flush()
        await self.db.refresh(memo)

        # Link memo to conflict
        conflict.memo = memo

        await self.db.flush()

        # Audit log
        audit_log.log(
            operation=OperationType.CREATE,
            user_id=current_user.id,
            resource_type="conflict_report",
            resource_id=conflict.id,
            dept_id=current_user.dept_id,
            details={
                "task_id": conflict_data.task_id,
                "urgency_level": conflict_data.urgency_level
            }
        )

        self.logger.info(
            f"Conflict report created: {conflict.id} for task {conflict_data.task_id} "
            f"by user {current_user.id}, memo {memo.id} created for user {memo_recipient_id}"
        )

        # Trigger immediate reminder
        await self.notification_service.send_immediate_reminder(memo_recipient_id, memo.id)

        return conflict

    def _generate_memo_text(
        self,
        task: Task,
        conflict: ConflictReport,
        reporter: User
    ) -> str:
        """Generate full memo text from conflict details."""
        lines = [
            f"【冲突报告】",
            f"",
            f"任务：{task.title}",
            f"上报人：{reporter.name}",
            f"冲突摘要：{conflict.conflict_summary}",
            f"",
        ]

        if conflict.conflict_details:
            lines.append("冲突详情：")
            details = conflict.conflict_details if isinstance(conflict.conflict_details, dict) else {}
            for key, value in details.items():
                lines.append(f"  {key}: {value}")
            lines.append("")

        if conflict.proposed_solutions:
            lines.append("建议方案：")
            solutions = conflict.proposed_solutions if isinstance(conflict.proposed_solutions, list) else []
            for i, sol in enumerate(solutions, 1):
                if isinstance(sol, dict):
                    lines.append(f"  {i}. {sol.get('description', 'N/A')}")
            lines.append("")

        if conflict.need_decision_by:
            lines.append(f"请在 {conflict.need_decision_by.strftime('%Y-%m-%d %H:%M')} 前做出决策。")
        else:
            lines.append("请尽快做出决策。")

        return "\n".join(lines)

    async def get_conflict_by_id(
        self,
        conflict_id: int,
        current_user: User
    ) -> ConflictReport:
        """
        Get a conflict by ID.

        Args:
            conflict_id: Conflict ID
            current_user: Current authenticated user

        Returns:
            ConflictReport instance
        """
        result = await self.db.execute(
            select(ConflictReport).where(ConflictReport.id == conflict_id)
        )
        conflict = result.scalar_one_or_none()

        if not conflict:
            raise ConflictNotFoundException(conflict_id)

        # Access control
        if current_user.role != "leader":
            # Must be involved in the task
            task_result = await self.db.execute(
                select(Task).where(Task.id == conflict.task_id)
            )
            task = task_result.scalar_one_or_none()

            if task.lead_dept_id != current_user.dept_id and \
               conflict.reporter_dept_id != current_user.dept_id:
                raise ForbiddenException()

        return conflict

    async def get_conflicts(
        self,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        urgency_level: Optional[str] = None,
        task_id: Optional[int] = None
    ) -> Tuple[List[ConflictReport], int]:
        """
        Get conflicts with pagination and filters.

        Args:
            current_user: Current authenticated user
            page: Page number
            page_size: Items per page
            status: Filter by status
            urgency_level: Filter by urgency
            task_id: Filter by task

        Returns:
            Tuple of (conflicts list, total count)
        """
        query = select(ConflictReport)

        # Access control
        if current_user.role != "leader":
            # Get tasks where user's department is involved
            task_query = select(Task.id).where(
                or_(
                    Task.lead_dept_id == current_user.dept_id,
                    Task.created_by == current_user.id
                )
            )
            query = query.where(
                or_(
                    ConflictReport.task_id.in_(task_query),
                    ConflictReport.reporter_dept_id == current_user.dept_id
                )
            )

        # Apply filters
        if status:
            query = query.where(ConflictReport.status == status)
        if urgency_level:
            query = query.where(ConflictReport.urgency_level == urgency_level)
        if task_id:
            query = query.where(ConflictReport.task_id == task_id)

        # Count
        count_query = select(ConflictReport.id)
        if status:
            count_query = count_query.where(ConflictReport.status == status)
        if urgency_level:
            count_query = count_query.where(ConflictReport.urgency_level == urgency_level)
        if task_id:
            count_query = count_query.where(ConflictReport.task_id == task_id)
        count_result = await self.db.execute(count_query)
        total = len(count_result.scalars().all())

        # Paginate
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(ConflictReport.created_at.desc())

        result = await self.db.execute(query)
        conflicts = result.scalars().all()

        return list(conflicts), total

    async def resolve_conflict(
        self,
        conflict_id: int,
        decision: ConflictDecision,
        current_user: User
    ) -> ConflictReport:
        """
        Resolve a conflict with a decision.

        Args:
            conflict_id: Conflict ID
            decision: Decision data
            current_user: Current authenticated user (must be leader)

        Returns:
            Updated conflict report
        """
        # Only leaders can resolve conflicts
        if current_user.role != "leader":
            raise ForbiddenException()

        conflict = await self.get_conflict_by_id(conflict_id, current_user)

        if conflict.status == ConflictStatus.RESOLVED:
            raise ConflictAlreadyResolvedException()

        # Update conflict
        conflict.decision_content = decision.decision_content
        conflict.decision_made_at = datetime.utcnow()
        conflict.decision_maker_id = current_user.id
        conflict.status = ConflictStatus.RESOLVED

        # Update related memo
        if conflict.memo:
            conflict.memo.status = MemoStatus.RESOLVED

        await self.db.flush()

        # Audit log
        audit_log.log(
            operation=OperationType.APPROVE,
            user_id=current_user.id,
            resource_type="conflict_report",
            resource_id=conflict.id,
            dept_id=current_user.dept_id,
            details={"decision_content": decision.decision_content}
        )

        self.logger.info(
            f"Conflict {conflict_id} resolved by user {current_user.id}"
        )

        # Notify relevant departments
        await self.notification_service.notify_conflict_resolution(
            conflict_id=conflict_id,
            decision_content=decision.decision_content,
            notify_dept_ids=decision.notify_departments
        )

        return conflict

    async def escalate_conflict(
        self,
        conflict_id: int,
        current_user: User
    ) -> ConflictReport:
        """
        Escalate a conflict to higher authority.

        Args:
            conflict_id: Conflict ID
            current_user: Current authenticated user

        Returns:
            Updated conflict report
        """
        conflict = await self.get_conflict_by_id(conflict_id, current_user)

        if conflict.status == ConflictStatus.RESOLVED:
            raise ConflictAlreadyResolvedException()

        conflict.status = ConflictStatus.ESCALATED

        await self.db.flush()

        # Audit log
        audit_log.log(
            operation=OperationType.ESCALATE,
            user_id=current_user.id,
            resource_type="conflict_report",
            resource_id=conflict.id,
            dept_id=current_user.dept_id
        )

        self.logger.info(f"Conflict {conflict_id} escalated by user {current_user.id}")
        return conflict

    async def get_pending_conflicts_for_reminder(
        self,
        check_time: datetime
    ) -> List[ConflictReport]:
        """
        Get pending conflicts that need reminders.

        Args:
            check_time: Current time to check against

        Returns:
            List of conflicts needing reminders
        """
        query = select(ConflictReport).where(
            and_(
                ConflictReport.status == ConflictStatus.PENDING,
                or_(
                    ConflictReport.need_decision_by.is_(None),
                    ConflictReport.need_decision_by > check_time
                )
            )
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())
