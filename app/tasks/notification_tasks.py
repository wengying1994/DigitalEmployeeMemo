"""
Notification Celery tasks for sending various types of notifications.
"""
from datetime import datetime

from app.core.celery_app import celery_app
from app.core.logger import get_logger
from app.config import settings


logger = get_logger(__name__)


def get_user_email(user_id: int) -> str | None:
    """Get user email from database."""
    from app.db.session import get_db_context
    from sqlalchemy import select
    from app.models import User

    with get_db_context() as db:
        result = db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        return user.email if user else None


def get_user_name(user_id: int) -> str | None:
    """Get user name from database."""
    from app.db.session import get_db_context
    from sqlalchemy import select
    from app.models import User

    with get_db_context() as db:
        result = db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        return user.name if user else None


@celery_app.task(name="app.tasks.notification_tasks.send_in_app_notification")
def send_in_app_notification_task(
    user_id: int,
    memo_id: int | None,
    trigger_type: str,
    extra_data: dict | None = None
) -> dict:
    """
    Send an in-app notification to a user.

    Args:
        user_id: Target user ID
        memo_id: Related memo ID (if applicable)
        trigger_type: Type of trigger (immediate, 2h, 24h, etc.)
        extra_data: Additional data to include

    Returns:
        Result dictionary
    """
    from app.db.session import get_db_context
    from sqlalchemy import select, and_
    from app.models import Memo, Reminder, ReminderStatus

    logger.info(f"Sending in-app notification to user {user_id} for memo {memo_id}, trigger: {trigger_type}")

    try:
        user_name = get_user_name(user_id)

        with get_db_context() as db:
            # Create in-app notification record
            # In a real system, you might have a separate Notification model
            # For now, we'll just log it

            memo_text = ""
            if memo_id:
                result = db.execute(
                    select(Memo).where(Memo.id == memo_id)
                )
                memo = result.scalar_one_or_none()
                if memo:
                    memo_text = f": {memo.title}"

            notification_message = f"通知{Get_notification_title(trigger_type)}{memo_text}"

            # Update reminder if exists
            if memo_id:
                reminder_result = db.execute(
                    select(Reminder).where(
                        and_(
                            Reminder.memo_id == memo_id,
                            Reminder.target_user_id == user_id,
                            Reminder.status == ReminderStatus.PENDING
                        )
                    )
                )
                reminder = reminder_result.scalar_one_or_none()
                if reminder:
                    reminder.last_sent_at = datetime.utcnow()

            db.commit()

        logger.info(
            f"In-app notification sent to user {user_id} ({user_name}). "
            f"Message: {notification_message}"
        )

        return {
            "status": "sent",
            "user_id": user_id,
            "method": "in_app",
            "trigger_type": trigger_type,
            "message": notification_message
        }

    except Exception as e:
        logger.error(f"Error sending in-app notification to user {user_id}: {str(e)}")
        return {
            "status": "error",
            "user_id": user_id,
            "error": str(e)
        }


def Get_notification_title(trigger_type: str) -> str:
    """Get notification title based on trigger type."""
    titles = {
        "immediate": "有新消息",
        "2h": "您有未处理的备忘录（2小时前提醒）",
        "24h": "您有未处理的备忘录（24小时前提醒）",
        "48h": "您有未处理的备忘录（48小时前提醒）",
        "72h": "紧急：您有未处理的备忘录（72小时前提醒）",
        "conflict_resolved": "冲突已解决",
        "task_created": "新任务通知",
        "assignment_update": "分工更新通知",
    }
    return titles.get(trigger_type, "您有新通知")


@celery_app.task(name="app.tasks.notification_tasks.send_email")
def send_email_task(
    user_id: int,
    memo_id: int | None,
    trigger_type: str
) -> dict:
    """
    Send an email notification to a user.

    Args:
        user_id: Target user ID
        memo_id: Related memo ID (if applicable)
        trigger_type: Type of trigger

    Returns:
        Result dictionary
    """
    logger.info(f"Sending email notification to user {user_id} for memo {memo_id}")

    try:
        user_email = get_user_email(user_id)
        user_name = get_user_name(user_id)

        if not user_email:
            logger.warning(f"User {user_id} has no email address")
            return {
                "status": "error",
                "user_id": user_id,
                "error": "no_email"
            }

        # In production, you would use a real email service
        # For now, we just log the email content
        subject = f"【DigitalEmployeeMemo】{Get_notification_title(trigger_type)}"

        email_content = f"""
        尊敬的 {user_name}，

        {Get_email_body(trigger_type, memo_id)}

        ---
        DigitalEmployeeMemo 系统
        此邮件由系统自动发送，请勿回复。
        """

        if settings.DEBUG:
            # In debug mode, just log the email
            logger.info(f"[EMAIL] To: {user_email}")
            logger.info(f"[EMAIL] Subject: {subject}")
            logger.info(f"[EMAIL] Body:\n{email_content}")
        else:
            # In production, you would send the email via SMTP or email service
            # Example with aiotrasmit or similar:
            # await send_email(user_email, subject, email_content)
            pass

        return {
            "status": "sent",
            "user_id": user_id,
            "email": user_email,
            "method": "email",
            "trigger_type": trigger_type
        }

    except Exception as e:
        logger.error(f"Error sending email to user {user_id}: {str(e)}")
        return {
            "status": "error",
            "user_id": user_id,
            "error": str(e)
        }


def Get_email_body(trigger_type: str, memo_id: int | None) -> str:
    """Get email body based on trigger type."""
    base_body = ""

    if trigger_type in ["immediate", "2h", "24h", "48h", "72h"]:
        base_body = "您有一条新的备忘录需要处理。请尽快登录系统查看并处理。"

        if memo_id:
            base_body += f"\n\n备忘录ID: {memo_id}"

        if trigger_type == "72h":
            base_body += "\n\n【紧急】该备忘录已超过72小时未处理，已自动升级处理。"

    elif trigger_type == "conflict_resolved":
        base_body = "您上报的冲突已得到解决，请查看决策结果。"

    elif trigger_type == "task_created":
        base_body = "您有一个新的任务需要关注。"

    return base_body


@celery_app.task(name="app.tasks.notification_tasks.send_test_notification")
def send_test_notification(
    user_id: int,
    method: str,
    message: str
) -> dict:
    """
    Send a test notification.

    Args:
        user_id: Target user ID
        method: Notification method (in_app, email, etc.)
        message: Test message

    Returns:
        Result dictionary
    """
    logger.info(f"Sending test notification to user {user_id} via {method}")

    try:
        user_name = get_user_name(user_id)

        if method == "in_app":
            # Simulate in-app notification
            logger.info(f"[TEST NOTIFICATION] To: {user_name} (ID: {user_id})")
            logger.info(f"[TEST NOTIFICATION] Message: {message}")

            return {
                "status": "sent",
                "user_id": user_id,
                "method": "in_app",
                "message": message
            }

        elif method == "email":
            user_email = get_user_email(user_id)
            if not user_email:
                return {
                    "status": "error",
                    "user_id": user_id,
                    "error": "no_email"
                }

            logger.info(f"[TEST EMAIL] To: {user_email}")
            logger.info(f"[TEST EMAIL] Subject: 【测试邮件】{message}")

            return {
                "status": "sent",
                "user_id": user_id,
                "email": user_email,
                "method": "email",
                "message": message
            }

        else:
            return {
                "status": "error",
                "method": method,
                "error": "unsupported_method"
            }

    except Exception as e:
        logger.error(f"Error sending test notification to user {user_id}: {str(e)}")
        return {
            "status": "error",
            "user_id": user_id,
            "error": str(e)
        }


@celery_app.task(name="app.tasks.notification_tasks.notify_conflict_update")
def notify_conflict_update(
    conflict_id: int,
    notify_user_ids: list[int],
    notification_type: str,
    extra_data: dict | None = None
) -> dict:
    """
    Notify multiple users about a conflict update.

    Args:
        conflict_id: Conflict ID
        notify_user_ids: List of user IDs to notify
        notification_type: Type of notification
        extra_data: Additional data

    Returns:
        Result dictionary
    """
    logger.info(f"Notifying {len(notify_user_ids)} users about conflict {conflict_id}")

    sent_count = 0
    failed_count = 0

    for user_id in notify_user_ids:
        try:
            send_in_app_notification_task.delay(
                user_id=user_id,
                memo_id=None,
                trigger_type=notification_type,
                extra_data=extra_data
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to notify user {user_id}: {str(e)}")
            failed_count += 1

    return {
        "status": "completed",
        "conflict_id": conflict_id,
        "sent": sent_count,
        "failed": failed_count
    }
