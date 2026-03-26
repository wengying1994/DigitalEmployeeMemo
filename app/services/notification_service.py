"""
Notification service for sending notifications via various channels.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.celery_app import celery_app
from app.core.logger import LoggerMixin
from app.models import User
from app.tasks.notification_tasks import send_email_task, send_in_app_notification_task


class NotificationService(LoggerMixin):
    """Service for sending notifications through various channels."""

    def __init__(self):
        """Initialize notification service."""
        pass

    async def send_immediate_reminder(
        self,
        user_id: int,
        memo_id: int
    ) -> None:
        """
        Send immediate reminder for a new memo.

        Args:
            user_id: Target user ID
            memo_id: Related memo ID
        """
        self.logger.info(f"Sending immediate reminder to user {user_id} for memo {memo_id}")

        # Send in-app notification immediately
        send_in_app_notification_task.delay(user_id, memo_id, "immediate")

        # Also send email if enabled
        from app.config import settings
        if settings.NOTIFICATION_EMAIL_ENABLED:
            send_email_task.delay(user_id, memo_id, "immediate")

    async def send_scheduled_reminder(
        self,
        user_id: int,
        memo_id: int,
        stage: str
    ) -> None:
        """
        Send a scheduled reminder.

        Args:
            user_id: Target user ID
            memo_id: Related memo ID
            stage: Reminder stage (2h, 24h, 48h, 72h)
        """
        self.logger.info(
            f"Sending {stage} reminder to user {user_id} for memo {memo_id}"
        )

        send_in_app_notification_task.delay(user_id, memo_id, stage)

        from app.config import settings
        if settings.NOTIFICATION_EMAIL_ENABLED:
            send_email_task.delay(user_id, memo_id, stage)

    async def notify_conflict_resolution(
        self,
        conflict_id: int,
        decision_content: str,
        notify_dept_ids: Optional[List[int]] = None
    ) -> None:
        """
        Notify relevant parties about a conflict resolution.

        Args:
            conflict_id: Conflict ID
            decision_content: Decision content
            notify_dept_ids: Department IDs to notify
        """
        from app.db.session import get_db_context
        from sqlalchemy import select

        async with get_db_context() as db:
            # Get conflict to find related departments
            from app.models import ConflictReport
            result = await db.execute(
                select(ConflictReport).where(ConflictReport.id == conflict_id)
            )
            conflict = result.scalar_one_or_none()

            if not conflict:
                self.logger.warning(f"Conflict {conflict_id} not found for notification")
                return

            # Get task
            from app.models import Task
            task_result = await db.execute(
                select(Task).where(Task.id == conflict.task_id)
            )
            task = task_result.scalar_one_or_none()

            # Notify reporter
            send_in_app_notification_task.delay(
                conflict.reporter_user_id,
                conflict.memo_id,
                "conflict_resolved",
                {"decision_content": decision_content}
            )

            # Notify lead department
            if task:
                lead_user_result = await db.execute(
                    select(User).where(User.dept_id == task.lead_dept_id)
                )
                lead_users = lead_user_result.scalars().all()

                for user in lead_users:
                    send_in_app_notification_task.delay(
                        user.id,
                        conflict.memo_id,
                        "conflict_resolved",
                        {
                            "decision_content": decision_content,
                            "task_title": task.title
                        }
                    )

    async def notify_assignment_update(
        self,
        assignment_id: int,
        dept_id: int,
        update_type: str
    ) -> None:
        """
        Notify department about assignment updates.

        Args:
            assignment_id: Assignment ID
            dept_id: Department ID
            update_type: Type of update
        """
        from app.db.session import get_db_context
        from sqlalchemy import select

        async with get_db_context() as db:
            # Get department users
            users_result = await db.execute(
                select(User).where(User.dept_id == dept_id)
            )
            users = users_result.scalars().all()

            for user in users:
                send_in_app_notification_task.delay(
                    user.id,
                    None,
                    f"assignment_{update_type}",
                    {"assignment_id": assignment_id}
                )

    async def notify_task_created(
        self,
        task_id: int,
        lead_dept_id: int
    ) -> None:
        """
        Notify lead department about new task.

        Args:
            task_id: Task ID
            lead_dept_id: Lead department ID
        """
        from app.db.session import get_db_context
        from sqlalchemy import select

        async with get_db_context() as db:
            # Get department users
            users_result = await db.execute(
                select(User).where(User.dept_id == lead_dept_id)
            )
            users = users_result.scalars().all()

            for user in users:
                send_in_app_notification_task.delay(
                    user.id,
                    None,
                    "task_created",
                    {"task_id": task_id}
                )

    async def send_bulk_notification(
        self,
        user_ids: List[int],
        notification_type: str,
        data: Dict[str, Any]
    ) -> None:
        """
        Send notification to multiple users.

        Args:
            user_ids: List of user IDs
            notification_type: Type of notification
            data: Notification data
        """
        for user_id in user_ids:
            send_in_app_notification_task.delay(user_id, None, notification_type, data)
