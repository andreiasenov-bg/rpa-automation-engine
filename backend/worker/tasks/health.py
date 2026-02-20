"""Celery tasks for health monitoring."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from worker.celery_app import celery_app
import sys
if "/app" not in sys.path:
    sys.path.insert(0, "/app")

logger = logging.getLogger(__name__)

# Agents that haven't sent a heartbeat in this many minutes are marked disconnected
HEARTBEAT_TIMEOUT_MINUTES = 5


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
    """Check for agents that have missed their heartbeat and mark as disconnected."""
    logger.info("Checking agent heartbeats")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_check_heartbeats())
        return result
    finally:
        loop.close()


async def _check_heartbeats() -> dict:
    """Query Agent model for stale heartbeats and mark agents as disconnected."""
    from sqlalchemy import select, update, and_
    from db.session import AsyncSessionLocal
    from db.models.agent import Agent
    from core.constants import AgentStatus

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=HEARTBEAT_TIMEOUT_MINUTES)
    stats = {"checked": 0, "disconnected": 0}

    async with AsyncSessionLocal() as session:
        # Find active agents whose heartbeat is stale
        result = await session.execute(
            select(Agent).where(
                and_(
                    Agent.status == AgentStatus.ACTIVE.value,
                    Agent.is_deleted == False,
                    Agent.last_heartbeat_at != None,
                    Agent.last_heartbeat_at < cutoff,
                )
            )
        )
        stale_agents = result.scalars().all()
        stats["checked"] = len(stale_agents)

        for agent in stale_agents:
            agent.status = AgentStatus.DISCONNECTED.value
            stats["disconnected"] += 1
            logger.warning(
                "Agent '%s' (%s) marked disconnected — last heartbeat: %s",
                agent.name,
                agent.id,
                agent.last_heartbeat_at,
            )

        if stale_agents:
            await session.commit()
            logger.info(
                "Marked %d agent(s) as disconnected (heartbeat timeout: %d min)",
                stats["disconnected"],
                HEARTBEAT_TIMEOUT_MINUTES,
            )

    return stats
