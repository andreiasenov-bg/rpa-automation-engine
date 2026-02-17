"""Celery application configuration.

This module sets up the Celery app with:
- Redis as broker and result backend
- Task routing to specialized queues
- Serialization and timezone settings
- Beat schedule for periodic tasks
- Auto-discovery of task modules
"""

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "rpa_engine",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task routing — different queues for different workloads
    task_routes={
        "worker.tasks.workflow.*": {"queue": "workflows"},
        "worker.tasks.triggers.*": {"queue": "triggers"},
        "worker.tasks.notifications.*": {"queue": "notifications"},
        "worker.tasks.health.*": {"queue": "health"},
        "worker.tasks.ai.*": {"queue": "ai"},
        "worker.tasks.*": {"queue": "default"},
    },

    # Default queue
    task_default_queue="default",

    # Result expiration (24 hours)
    result_expires=86400,

    # Task execution limits
    task_soft_time_limit=300,   # 5 min soft limit (raises SoftTimeLimitExceeded)
    task_time_limit=600,        # 10 min hard limit (kills the task)
    task_acks_late=True,        # Acknowledge after execution (safer)
    worker_prefetch_multiplier=1,  # One task at a time per worker process

    # Retry
    task_reject_on_worker_lost=True,
    task_acks_on_failure_or_timeout=True,

    # Beat schedule for periodic tasks
    beat_schedule={
        "health-check-integrations": {
            "task": "worker.tasks.health.check_all_integrations",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
            "options": {"queue": "health"},
        },
        "cleanup-old-executions": {
            "task": "worker.tasks.maintenance.cleanup_old_data",
            "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
            "options": {"queue": "default"},
        },
        "agent-heartbeat-check": {
            "task": "worker.tasks.health.check_agent_heartbeats",
            "schedule": crontab(minute="*/2"),  # Every 2 minutes
            "options": {"queue": "health"},
        },
        "poll-schedules": {
            "task": "worker.tasks.schedule_poller.poll_schedules",
            "schedule": crontab(minute="*/1"),  # Every minute
            "options": {"queue": "triggers"},
        },
    },

    # Auto-discover task modules
    include=[
        "worker.tasks.workflow",
        "worker.tasks.triggers",
        "worker.tasks.notifications",
        "worker.tasks.health",
        "worker.tasks.maintenance",
        "worker.tasks.schedule_poller",
    ],
)
