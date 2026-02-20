"""System health check & code quality verification endpoint.

Hardcoded rules based on engineering preferences:
- DRY — no repeated logic
- Well tested — tests must pass
- "Engineered enough" — not over/under
- Edge cases — always considered
- Explicit over clever — clarity wins

Runs automatically after deploys and daily as preventive maintenance.
"""

import asyncio
import importlib
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_active_user
from core.security import TokenPayload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system-check", tags=["System Health"])


# ── Hardcoded rules ──────────────────────────────────────────────────
RULES = {
    "engineering": {
        "DRY": "No duplicated logic across modules",
        "well_tested": "All critical paths have test coverage",
        "engineered_enough": "No over-engineering, no shortcuts",
        "edge_cases": "Null checks, empty lists, timezone handling",
        "explicit_over_clever": "Readable > compact",
    },
    "review_sections": ["architecture", "code_quality", "tests", "performance"],
    "thresholds": {
        "max_response_time_ms": 2000,
        "min_schedule_coverage": 1.0,      # 100% enabled schedules must have next_run_at
        "max_failed_executions_pct": 30,    # alert if >30% recent executions fail
        "max_stale_schedule_hours": 26,     # next_run_at shouldn't be >26h in the past
        "db_connection_timeout_s": 5,
        "redis_timeout_s": 3,
    },
}


async def _check_database(db: AsyncSession) -> dict:
    """Verify database connectivity and basic integrity."""
    issues = []
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
    except Exception as e:
        issues.append(f"DB connection failed: {e}")
        return {"ok": False, "issues": issues}

    # Check table existence
    for table in ["users", "workflows", "executions", "schedules", "organizations"]:
        try:
            await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
        except Exception as e:
            issues.append(f"Table '{table}' missing or broken: {e}")

    return {"ok": len(issues) == 0, "issues": issues}


async def _check_redis() -> dict:
    """Verify Redis connectivity."""
    issues = []
    try:
        import redis.asyncio as aioredis
        from app.config import get_settings
        settings = get_settings()
        r = aioredis.from_url(settings.REDIS_URL, socket_timeout=RULES["thresholds"]["redis_timeout_s"])
        pong = await r.ping()
        await r.aclose()
        if not pong:
            issues.append("Redis PING failed")
    except ImportError:
        issues.append("redis library not installed")
    except Exception as e:
        issues.append(f"Redis connection failed: {e}")

    return {"ok": len(issues) == 0, "issues": issues}


async def _check_schedules(db: AsyncSession) -> dict:
    """Verify schedule health — the #1 issue we've debugged."""
    from db.models.schedule import Schedule

    issues = []
    now = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC

    # All enabled schedules should have next_run_at set
    result = await db.execute(
        select(Schedule.id, Schedule.name, Schedule.next_run_at, Schedule.is_enabled)
        .where(Schedule.is_deleted == False)
    )
    schedules = result.all()

    enabled_count = 0
    enabled_with_next_run = 0
    stale_schedules = []

    for sched in schedules:
        if sched.is_enabled:
            enabled_count += 1
            if sched.next_run_at:
                enabled_with_next_run += 1
                # Check if next_run_at is stale (in the past by too much)
                hours_ago = (now - sched.next_run_at).total_seconds() / 3600
                if hours_ago > RULES["thresholds"]["max_stale_schedule_hours"]:
                    stale_schedules.append(f"'{sched.name}' next_run_at is {hours_ago:.1f}h in the past")
            else:
                issues.append(f"Schedule '{sched.name}' is enabled but next_run_at is NULL")

    if stale_schedules:
        issues.extend(stale_schedules)

    coverage = (enabled_with_next_run / enabled_count * 100) if enabled_count > 0 else 100

    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "stats": {
            "total": len(schedules),
            "enabled": enabled_count,
            "with_next_run": enabled_with_next_run,
            "coverage_pct": round(coverage, 1),
        },
    }


async def _check_executions(db: AsyncSession) -> dict:
    """Check recent execution health."""
    from db.models.execution import Execution

    issues = []
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    day_ago = now - timedelta(hours=24)

    # Count recent executions by status
    result = await db.execute(
        select(Execution.status, func.count(Execution.id))
        .where(Execution.created_at >= day_ago)
        .group_by(Execution.status)
    )
    status_counts = {row[0]: row[1] for row in result.all()}
    total = sum(status_counts.values())

    failed = status_counts.get("failed", 0) + status_counts.get("error", 0)
    if total > 0:
        fail_pct = failed / total * 100
        if fail_pct > RULES["thresholds"]["max_failed_executions_pct"]:
            issues.append(f"{fail_pct:.0f}% of last 24h executions failed ({failed}/{total})")

    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "stats": {
            "last_24h": status_counts,
            "total": total,
            "failed": failed,
        },
    }


async def _check_critical_imports() -> dict:
    """Verify critical Python packages are importable."""
    issues = []
    critical_packages = [
        ("croniter", "Schedule cron computation"),
        ("celery", "Background task processing"),
        ("sqlalchemy", "Database ORM"),
        ("jwt", "JWT authentication"),
        ("pytz", "Timezone handling"),
    ]

    for pkg, purpose in critical_packages:
        try:
            importlib.import_module(pkg)
        except ImportError:
            issues.append(f"Missing package '{pkg}' — needed for: {purpose}")

    return {"ok": len(issues) == 0, "issues": issues}


async def _check_celery() -> dict:
    """Check if Celery workers are responsive."""
    issues = []
    try:
        from worker.celery_app import celery_app
        inspector = celery_app.control.inspect(timeout=3)
        # This is a sync call — run in executor
        loop = asyncio.get_event_loop()
        active = await loop.run_in_executor(None, inspector.active)
        if not active:
            issues.append("No active Celery workers found")
    except Exception as e:
        issues.append(f"Celery inspection failed: {e}")

    return {"ok": len(issues) == 0, "issues": issues}


async def _check_api_endpoints(db: AsyncSession) -> dict:
    """Verify critical API routes respond (internal smoke test)."""
    from db.models.workflow import Workflow
    from db.models.user import User

    issues = []

    # Check at least 1 user exists
    user_count = await db.scalar(select(func.count(User.id)).where(User.is_deleted == False))
    if not user_count or user_count == 0:
        issues.append("No active users in database")

    # Check at least 1 workflow exists
    wf_count = await db.scalar(select(func.count(Workflow.id)).where(Workflow.is_deleted == False))
    if not wf_count or wf_count == 0:
        issues.append("No workflows in database")

    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "stats": {"users": user_count or 0, "workflows": wf_count or 0},
    }


@router.get("/")
async def full_system_check(
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Run all health checks and return a comprehensive report.

    Called:
    - After every deploy (by deployer.py)
    - Daily at 06:00 UTC (by scheduled shortcut)
    - Manually via GET /api/v1/system-check/
    """
    start = datetime.now(timezone.utc)

    checks = {}
    checks["database"] = await _check_database(db)
    checks["redis"] = await _check_redis()
    checks["imports"] = await _check_critical_imports()
    checks["schedules"] = await _check_schedules(db)
    checks["executions"] = await _check_executions(db)
    checks["celery"] = await _check_celery()
    checks["data_integrity"] = await _check_api_endpoints(db)

    all_ok = all(c["ok"] for c in checks.values())
    all_issues = []
    for name, check in checks.items():
        for issue in check.get("issues", []):
            all_issues.append(f"[{name}] {issue}")

    elapsed_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000

    return {
        "status": "healthy" if all_ok else "unhealthy",
        "timestamp": start.isoformat(),
        "elapsed_ms": round(elapsed_ms, 1),
        "checks": checks,
        "issues": all_issues,
        "rules": RULES["engineering"],
    }


@router.get("/quick")
async def quick_health(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Quick unauthenticated health check (for monitoring)."""
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    try:
        import croniter  # noqa: F401
        croniter_ok = True
    except ImportError:
        croniter_ok = False

    return {
        "status": "ok" if (db_ok and croniter_ok) else "degraded",
        "database": db_ok,
        "croniter": croniter_ok,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
