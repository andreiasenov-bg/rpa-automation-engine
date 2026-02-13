"""Schedule trigger handler.

Uses cron expressions to trigger workflows on a schedule.
Integrates with the existing Schedule model and Celery beat.
"""

from typing import Optional

from triggers.base import BaseTriggerHandler, TriggerResult, TriggerTypeEnum


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

        # TODO: Register with Celery beat dynamically
        # celery_app.conf.beat_schedule[f"trigger_{trigger_id}"] = {
        #     "task": "tasks.execute_trigger",
        #     "schedule": crontab_from_string(config["cron"]),
        #     "args": [trigger_id],
        # }

        return TriggerResult(
            success=True,
            message=f"Schedule registered: {config.get('cron', '???')}",
            trigger_id=trigger_id,
        )

    async def stop(self, trigger_id: str) -> TriggerResult:
        """Unregister a scheduled trigger."""
        self._active.pop(trigger_id, None)

        # TODO: Remove from Celery beat
        # celery_app.conf.beat_schedule.pop(f"trigger_{trigger_id}", None)

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
        return True, None
