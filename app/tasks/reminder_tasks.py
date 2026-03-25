"""
Reminder Celery tasks for scheduling and processing reminders.
"""
from datetime import datetime, timedelta

from app.core.celery_app import celery_app
from app.core.logger import get_logger
from app.config import settings


logger = get_logger(__name__)


@celery_app.task(name="app.tasks.reminder_tasks.check_pending_conflicts")
def check_pending_conflicts() -> dict:
    """
    Periodic task to check pending conflicts and generate reminders.

    This task runs every 5 minutes via Celery Beat.
    It checks all pending conflicts and creates appropriate reminders
    based on the configured reminder policy.

    Reminder stages:
    - immediate: Sent immediately when conflict is reported
    - 2h: 2 hours after creation if still unread
    - 24h: 24 hours after creation if still unread
    - 48h: 48 hours after creation if still unread (with escalation)
    - 72h: 72 hours after creation (final escalation)
    """
    from app.db.session import get_db_context
    from sqlalchemy import select, and_
    from app.models import ConflictReport, ConflictStatus, Memo, MemoStatus, Reminder, ReminderStatus, ReminderTriggerType

    logger.info("Starting check_pending_conflicts task")

    try:
        policy = settings.get_reminder_policy()
        now = datetime.utcnow()

        with get_db_context() as db:
            # Get all pending conflicts
            result = db.execute(
                select(ConflictReport).where(
                    ConflictReport.status == ConflictStatus.PENDING
                )
            )
            pending_conflicts = result.scalars().all()

            created_reminders = 0
            for conflict in pending_conflicts:
                # Get associated memo
                memo_result = db.execute(
                    select(Memo).where(
                        and_(
                            Memo.related_id == conflict.id,
                            Memo.memo_type == "conflict"
                        )
                    )
                )
                memo = memo_result.scalar_one_or_none()

                if not memo:
                    continue

                # Skip if memo is already resolved
                if memo.status == MemoStatus.RESOLVED:
                    continue

                # Calculate time since memo creation
                time_since_created = now - memo.created_at
                time_since_created_seconds = time_since_created.total_seconds()

                # Check which reminders should be created based on policy
                for stage_name, config in policy.items():
                    if stage_name == "immediate":
                        continue  # Already handled separately

                    delay = config.get("delay", 0)
                    methods = config.get("methods", ["in_app"])
                    escalate_to = config.get("escalate_to")

                    # Check if this stage's delay has passed
                    if time_since_created_seconds >= delay:
                        # Check if reminder for this stage already exists
                        existing_result = db.execute(
                            select(Reminder).where(
                                and_(
                                    Reminder.memo_id == memo.id,
                                    Reminder.trigger_type == ReminderTriggerType.CONDITION
                                )
                            )
                        )
                        existing_reminders = existing_result.scalars().all()

                        stage_exists = any(
                            r.reminder_methods and r.reminder_methods.get("stage") == stage_name
                            for r in existing_reminders
                        )

                        if not stage_exists:
                            # Create new reminder
                            reminder = Reminder(
                                target_user_id=memo.user_id,
                                memo_id=memo.id,
                                trigger_type=ReminderTriggerType.CONDITION,
                                trigger_time=now,  # Send immediately when triggered
                                reminder_methods={
                                    "methods": methods,
                                    "stage": stage_name,
                                    "escalate_to": escalate_to
                                },
                                status=ReminderStatus.PENDING
                            )
                            db.add(reminder)
                            created_reminders += 1

                            logger.info(
                                f"Created {stage_name} reminder for conflict {conflict.id}, "
                                f"memo {memo.id}"
                            )

            db.commit()
            logger.info(f"check_pending_conflicts completed. Created {created_reminders} reminders")

            return {
                "status": "completed",
                "pending_conflicts": len(pending_conflicts),
                "reminders_created": created_reminders
            }

    except Exception as e:
        logger.error(f"Error in check_pending_conflicts: {str(e)}")
        raise


@celery_app.task(name="app.tasks.reminder_tasks.process_overdue_memos")
def process_overdue_memos() -> dict:
    """
    Periodic task to process overdue memos and escalate.

    This task runs every 15 minutes via Celery Beat.
    It checks for memos that are past their need_decision_by date
    and escalates them according to policy.
    """
    from app.db.session import get_db_context
    from sqlalchemy import select, and_
    from app.models import Memo, MemoStatus, ConflictReport, ConflictStatus

    logger.info("Starting process_overdue_memos task")

    try:
        now = datetime.utcnow()

        with get_db_context() as db:
            # Get unresolved conflict memos that are past deadline
            result = db.execute(
                select(Memo).where(
                    and_(
                        Memo.memo_type == "conflict",
                        Memo.status.in_([MemoStatus.UNREAD, MemoStatus.READ]),
                        Memo.id.in_(
                            select(ConflictReport.id).where(
                                and_(
                                    ConflictReport.status == ConflictStatus.PENDING,
                                    ConflictReport.need_decision_by < now
                                )
                            )
                        )
                    )
                )
            )
            overdue_memos = result.scalars().all()

            escalated_count = 0
            for memo in overdue_memos:
                # Get related conflict
                conflict_result = db.execute(
                    select(ConflictReport).where(ConflictReport.id == memo.related_id)
                )
                conflict = conflict_result.scalar_one_or_none()

                if conflict and conflict.status == ConflictStatus.PENDING:
                    # Escalate the conflict
                    conflict.status = ConflictStatus.ESCALATED
                    escalated_count += 1

                    logger.warning(
                        f"Escalating overdue conflict {conflict.id}, "
                        f"memo {memo.id}, deadline was {conflict.need_decision_by}"
                    )

                    # Here you would trigger escalation notifications
                    # (e.g., notify secretary, superior, etc.)

            db.commit()
            logger.info(f"process_overdue_memos completed. Escalated {escalated_count} conflicts")

            return {
                "status": "completed",
                "overdue_memos": len(overdue_memos),
                "escalated": escalated_count
            }

    except Exception as e:
        logger.error(f"Error in process_overdue_memos: {str(e)}")
        raise


@celery_app.task(name="app.tasks.reminder_tasks.send_scheduled_reminders")
def send_scheduled_reminders(reminder_id: int) -> dict:
    """
    Task to send a specific scheduled reminder.

    Args:
        reminder_id: The reminder ID to send

    Returns:
        Result dictionary
    """
    from app.db.session import get_db_context
    from sqlalchemy import select, and_
    from app.models import Reminder, ReminderStatus, Memo, MemoStatus

    logger.info(f"Starting send_scheduled_reminders for reminder {reminder_id}")

    try:
        with get_db_context() as db:
            # Get the reminder
            result = db.execute(
                select(Reminder).where(Reminder.id == reminder_id)
            )
            reminder = result.scalar_one_or_none()

            if not reminder:
                logger.warning(f"Reminder {reminder_id} not found")
                return {"status": "not_found", "reminder_id": reminder_id}

            if reminder.status != ReminderStatus.PENDING:
                logger.info(f"Reminder {reminder_id} is not pending (status: {reminder.status})")
                return {"status": "skipped", "reason": "not_pending"}

            # Get the memo
            memo_result = db.execute(
                select(Memo).where(Memo.id == reminder.memo_id)
            )
            memo = memo_result.scalar_one_or_none()

            if not memo:
                logger.warning(f"Memo {reminder.memo_id} not found for reminder {reminder_id}")
                reminder.status = ReminderStatus.CANCELLED
                db.commit()
                return {"status": "error", "reason": "memo_not_found"}

            # Skip if memo is already resolved
            if memo.status == MemoStatus.RESOLVED:
                reminder.status = ReminderStatus.CANCELLED
                db.commit()
                return {"status": "skipped", "reason": "memo_resolved"}

            # Send notification based on methods
            methods = reminder.reminder_methods.get("methods", ["in_app"]) if reminder.reminder_methods else ["in_app"]
            stage = reminder.reminder_methods.get("stage", "unknown") if reminder.reminder_methods else "unknown"

            from app.tasks.notification_tasks import send_in_app_notification_task, send_email_task

            for method in methods:
                if method == "in_app":
                    send_in_app_notification_task.delay(
                        reminder.target_user_id,
                        reminder.memo_id,
                        stage
                    )
                elif method == "email":
                    send_email_task.delay(
                        reminder.target_user_id,
                        reminder.memo_id,
                        stage
                    )
                # Add more methods as needed (wechat, sms, etc.)

            # Mark reminder as sent
            reminder.status = ReminderStatus.SENT
            reminder.sent_at = datetime.utcnow()
            db.commit()

            logger.info(f"Scheduled reminder {reminder_id} sent successfully")

            return {
                "status": "sent",
                "reminder_id": reminder_id,
                "methods": methods,
                "stage": stage
            }

    except Exception as e:
        logger.error(f"Error sending scheduled reminder {reminder_id}: {str(e)}")
        raise
