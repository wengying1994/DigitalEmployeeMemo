"""
Celery application configuration.
Sets up Celery with Redis as broker and result backend.
"""
from celery import Celery
from celery.schedules import crontab

from app.config import settings


def create_celery_app() -> Celery:
    """
    Create and configure the Celery application instance.

    Returns:
        Configured Celery app instance
    """
    celery_app = Celery(
        "digital_employee_memo",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_BACKEND_URL,
        include=[
            "app.tasks.reminder_tasks",
            "app.tasks.notification_tasks",
        ]
    )

    # Celery configuration
    celery_app.conf.update(
        # Task serialization
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,

        # Task execution settings
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_time_limit=300,  # 5 minutes max per task
        task_soft_time_limit=240,  # 4 minutes soft limit

        # Result backend settings
        result_expires=3600,  # Results expire after 1 hour
        result_persistent=True,

        # Worker settings
        worker_prefetch_multiplier=1,
        worker_concurrency=4,

        # Beat schedule for periodic tasks
        beat_schedule={
            "check-pending-conflicts": {
                "task": "app.tasks.reminder_tasks.check_pending_conflicts",
                "schedule": crontab(minute="*/5"),  # Every 5 minutes
                "description": "Check pending conflicts and generate reminders",
            },
            "process-overdue-memos": {
                "task": "app.tasks.reminder_tasks.process_overdue_memos",
                "schedule": crontab(minute="*/15"),  # Every 15 minutes
                "description": "Process overdue memos and escalate",
            },
        },
    )

    return celery_app


# Create the celery app instance
celery_app = create_celery_app()
