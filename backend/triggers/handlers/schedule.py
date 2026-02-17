"""Schedule trigger handler.

Uses cron expressions to trigger workflows on a schedule.
Integrates with the existing Schedule model and Celery beat.
"""

import logging
from typing import Optional

from celery.schedules import crontab

from triggers.base import BaseTriggerHandler, TriggerResult, TriggerTypeEnum

logger = logging.getLogger(__name__)


def _crontab_from_string(expr: str) -> crontab:
    """Parse a standard 5-field cron expression into a Celery crontab.

    Fields: minute hour day_of_month month_of_year day_of_week
    """
    parts = expr.strip().split()
    if len(parts) < 5:
        raise ValueError(f"Expected 5 cron fields, got {len(parts)}")
    return crontab(
        minute=parts[0],
        hour=parts[1],
        day_of_month=parts[2],
        month_of_year=parts[3],
        day_of_week=parts[4],
    )


class ScheduleTriggerHandler(BaseTriggerHandler):
    """Handler for cron-based scheduled triggers.

    Config schema:
        {
            "cron": "0 9 * * MON",          # standard cron expression
            "timezone": "Europe/Sofia",       # IANA timezone
            "max_concurrent": 1,              # max concurrent executions
            "catch_up": false,                # run missed executions on startup
            "jitter_seconds": 0               # random delay to avoid thundering herd
        }
    """

    trigger_type = TriggerTypeEnum.SCHEDULE

    def __init__(self):
        self._active: dict[str, dict] = {}

    async def start(self, trigger_id: str, config: dict) -> TriggerResult:
        """Register a scheduled trigger with Celery beat."""
        is_valid, error = self.validate_config(config)
        if not is_valid:
            return TriggerResult(
                success=False,
                message=f"Invalid config: {error}",
                trigger_id=trigger_id,
                error=error,
            )

        self._active[trigger_id] = config

        # Dynamically add to Celery beat schedule
        try:
            from worker.celery_app import celery_app

            schedule_key = f"trigger_{trigger_id}"
            celery_app.conf.beat_schedule[schedule_key] = {
                "task": "worker.tasks.triggers.fire_trigger",
                "schedule": _crontab_from_string(config["cron"]),
                "args": [trigger_id],
                "options": {"queue": "triggers"},
            }
            logger.info(
                "Registered schedule trigger %s with cron '%s'",
                trigger_id,
                config["cron"],
            )
        except Exception as exc:
            logger.error("Failed to register Celery beat schedule: %s", exc)
            return TriggerResult(
                success=False,
                message=f"Failed to register schedule: {exc}",
                trigger_id=trigger_id,
                error=str(exc),
            )

        return TriggerResult(
            success=True,
            message=f"Schedule registered: {config.get('cron', '???')}",
            trigger_id=trigger_id,
        )

    async def stop(self, trigger_id: str) -> TriggerResult:
        """Unregister a scheduled trigger."""
        self._active.pop(trigger_id, None)

        # Remove from Celery beat
        try:
            from worker.celery_app import celery_app

            schedule_key = f"trigger_{trigger_id}"
            celery_app.conf.beat_schedule.pop(schedule_key, None)
            logger.info("Unregistered schedule trigger %s", trigger_id)
        except Exception as exc:
            logger.warning("Could not remove from Celery beat: %s", exc)

        return TriggerResult(
            success=True,
            message="Schedule unregistered",
            trigger_id=trigger_id,
        )

    async def test(self, config: dict) -> TriggerResult:
        """Validate schedule configuration."""
        is_valid, error = self.validate_config(config)
        if not is_valid:
            return TriggerResult(
                success=False,
                message=f"Invalid config: {error}",
                trigger_id="test",
                error=error,
            )
        return TriggerResult(
            success=True,
            message=f"Schedule '{config.get('cron')}' is valid",
            trigger_id="test",
        )

    def validate_config(self, config: dict) -> tuple[bool, Optional[str]]:
        """Validate cron config."""
        if not isinstance(config, dict):
            return False, "Config must be a dict"
        cron = config.get("cron")
        if not cron:
            return False, "Missing required field: cron"
        parts = cron.strip().split()
        if len(parts) not in (5, 6):
            return False, f"Invalid cron expression (expected 5-6 fields, got {len(parts)})"
        # Validate by trying to parse
        try:
            _crontab_from_string(cron)
        except Exception as exc:
            return False, f"Invalid cron expression: {exc}"
        return True, None
