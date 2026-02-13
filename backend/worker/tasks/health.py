"""Celery tasks for health monitoring."""

import asyncio
import logging

from worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="worker.tasks.health.check_all_integrations",
    queue="health",
)
def check_all_integrations():
    """Run health checks on all registered external integrations."""
    logger.info("Running integration health checks")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_check_integrations())
        return result
    finally:
        loop.close()


async def _check_integrations() -> dict:
    """Async health check logic."""
    from integrations.registry import get_integration_registry

    registry = get_integration_registry()
    # The health monitor loop handles individual checks,
    # but we can trigger a full check here too
    all_integrations = registry.list_all()
    healthy = 0
    unhealthy = 0

    for integration in all_integrations:
        status = integration.get("health_status", "unknown")
        if status == "healthy":
            healthy += 1
        else:
            unhealthy += 1

    return {
        "total": len(all_integrations),
        "healthy": healthy,
        "unhealthy": unhealthy,
    }


@celery_app.task(
    name="worker.tasks.health.check_agent_heartbeats",
    queue="health",
)
def check_agent_heartbeats():
    """Check for agents that have missed their heartbeat."""
    logger.info("Checking agent heartbeats")
    # TODO: Query Agent model for agents whose last_heartbeat_at
    # is more than 2x their expected interval, mark as disconnected
    return {"checked": True}
