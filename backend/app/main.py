"""RPA Automation Engine - FastAPI Application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from api.v1.router import api_v1_router
from api.routes import health
from api.routes.ws import router as ws_router
from db.database import init_db
from integrations.claude_client import get_claude_client
from integrations.registry import get_integration_registry
from workflow.checkpoint import CheckpointManager
from workflow.recovery import RecoveryService
from workflow.engine import get_workflow_engine
from triggers.manager import get_trigger_manager
from notifications.manager import get_notification_manager
from core.logging_config import setup_logging
from core.middleware import RequestTrackingMiddleware, setup_exception_handlers
from core.metrics import MetricsMiddleware, metrics_router
from core.rate_limit import RateLimitMiddleware
from core.profiler import ProfilerMiddleware
from api.routes import profiler as profiler_routes
from api.routes import api_health as api_health_routes
from core.security_scanner import check_secrets_on_startup
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Standard security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store"

        # Additional headers for production
        settings = get_settings()
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    settings = get_settings()
    setup_logging()

    # Validate secrets are not using defaults in production
    try:
        settings.validate_secrets()
    except RuntimeError as e:
        print(f"[startup] FATAL: {e}")
        raise

    # Security scan â blocks startup in production if critical secrets found
    try:
        check_secrets_on_startup()
    except RuntimeError as e:
        print(f"[startup] FATAL: {e}")
        raise
    except Exception as e:
        print(f"[startup] Security scan warning: {e}")

    await init_db()

    # Initialize Notification Manager
    notif_mgr = get_notification_manager()
    # Channels are configured via environment or admin API later
    print("[startup] Notification manager ready")

    # Connect to Claude AI
    claude = await get_claude_client()
    if claude.is_configured:
        print(f"[startup] Claude AI connected (model: {settings.CLAUDE_MODEL})")
    else:
        print("[startup] Claude AI not configured (set ANTHROPIC_API_KEY to enable)")

    # Load external API integrations and start health monitoring
    integration_registry = get_integration_registry()
    try:
        await integration_registry.load_all(db_session=None)
        await integration_registry.start_health_monitor()
        count = len(integration_registry.list_all())
        if count > 0:
            print(f"[startup] Loaded {count} API integration(s), health monitor active")
        else:
            print("[startup] Integration registry ready (no APIs configured yet)")
    except Exception as e:
        print(f"[startup] Integration registry warning: {e}")

    # Initialize Workflow Engine
    engine = get_workflow_engine()
    print("[startup] Workflow execution engine ready")

    # Initialize Trigger Manager and connect to workflow engine
    trigger_mgr = get_trigger_manager()
    trigger_mgr.set_event_callback(
        lambda event: _handle_trigger_event(event, engine)
    )
    try:
        loaded = await trigger_mgr.load_from_db(db_session=None)
        print(f"[startup] Trigger manager ready ({loaded} trigger(s) loaded)")
    except Exception as e:
        print(f"[startup] Trigger manager warning: {e}")

    # Recover interrupted executions from previous run
    try:
        checkpoint_mgr = CheckpointManager()
        recovery_svc = RecoveryService(checkpoint_manager=checkpoint_mgr)
        results = await recovery_svc.recover_all()
        recovered = sum(1 for r in results if r.recovered)
        if recovered > 0:
            print(f"[startup] Recovered {recovered} interrupted execution(s)")
        else:
            print("[startup] No interrupted executions to recover")
    except Exception as e:
        print(f"[startup] Recovery scan skipped: {e}")

    # Start in-process schedule poller (replaces Celery beat dependency)
    _schedule_poller_stop = _start_schedule_poller()
    print("[startup] Schedule poller thread started (60s interval)")

    print(f"[startup] {settings.APP_NAME} v{settings.APP_VERSION} started ({settings.ENVIRONMENT})")
    yield
    # Shutdown
    _schedule_poller_stop.set()
    await integration_registry.stop_health_monitor()
    if claude.is_connected:
        await claude.disconnect()
    print("[shutdown] Application shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Enterprise-grade RPA platform with visual workflow editor, "
                    "multi-tenant support, and autonomous operation.",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # Prometheus metrics middleware (outermost â measures all requests)
    app.add_middleware(MetricsMiddleware)

    # Rate limiting middleware
    app.add_middleware(RateLimitMiddleware)

    # Request tracking middleware
    app.add_middleware(RequestTrackingMiddleware)

    # Profiler middleware (CPU, memory, duration tracking)
    app.add_middleware(ProfilerMiddleware)

    # Security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    )

    # Global exception handlers
    setup_exception_handlers(app)

    # Root health check (unversioned â for load balancers / k8s probes)
    app.include_router(health.router, prefix="/api", tags=["Health"])

    # Versioned API â all business endpoints under /api/v1
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    # WebSocket endpoint (not under /api/v1 â mounted directly on the app)
    app.include_router(ws_router)

    # Profiler & API Health Monitor
    app.include_router(profiler_routes.router, prefix="/api/v1", tags=["Profiler"])
    app.include_router(api_health_routes.router, prefix="/api/v1", tags=["API Health"])

    # Prometheus metrics (unauthenticated â for scrapers)
    app.include_router(metrics_router)

    return app


def _start_schedule_poller() -> "threading.Event":
    """Launch a daemon thread that polls schedules every 60 seconds.

    This runs inside the FastAPI/uvicorn process â no Celery beat needed.
    Returns a threading.Event that can be set to stop the poller.
    """
    import threading
    import asyncio
    import logging
    import time

    stop_event = threading.Event()
    logger = logging.getLogger("schedule-poller")

    def _poller_loop():
        """Background thread: poll schedules every 60s."""
        logger.info("[schedule-poller] Background thread started")
        # Wait a few seconds for app to fully start
        time.sleep(5)

        while not stop_event.is_set():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(_poll_and_dispatch_schedules())
                if result.get("dispatched", 0) > 0:
                    logger.info(f"[schedule-poller] {result}")
            except Exception as e:
                logger.error(f"[schedule-poller] Error: {e}", exc_info=True)
            finally:
                loop.close()

            # Wait 60 seconds (interruptible)
            stop_event.wait(timeout=60)

        logger.info("[schedule-poller] Background thread stopped")

    async def _poll_and_dispatch_schedules() -> dict:
        """Find due schedules and launch workflow executions."""
        from datetime import datetime, timezone, timedelta
        from uuid import uuid4
        from sqlalchemy import select, and_
        from db.session import AsyncSessionLocal
        from db.models.schedule import Schedule
        from db.models.workflow import Workflow
        from db.models.execution import Execution
        from worker.run_workflow import launch_workflow_thread

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        dispatched = 0

        async with AsyncSessionLocal() as session:
            stmt = (
                select(Schedule)
                .where(Schedule.is_enabled == True)       # noqa: E712
                .where(Schedule.is_deleted == False)       # noqa: E712
                .where(Schedule.next_run_at != None)       # noqa: E711
                .where(Schedule.next_run_at <= now)
            )
            result = await session.execute(stmt)
            due_schedules = result.scalars().all()

            for schedule in due_schedules:
                try:
                    wf_result = await session.execute(
                        select(Workflow).where(Workflow.id == schedule.workflow_id)
                    )
                    workflow = wf_result.scalar_one_or_none()
                    if not workflow or not workflow.is_enabled:
                        continue

                    execution_id = str(uuid4())
                    execution = Execution(
                        id=execution_id,
                        organization_id=schedule.organization_id,
                        workflow_id=schedule.workflow_id,
                        trigger_type="schedule",
                        status="pending",
                    )
                    session.add(execution)

                    # Compute next_run_at
                    try:
                        from croniter import croniter
                        from zoneinfo import ZoneInfo
                        tz_obj = ZoneInfo(schedule.timezone)
                        now_local = datetime.now(tz_obj)
                        cron = croniter(schedule.cron_expression, now_local)
                        next_local = cron.get_next(datetime)
                        schedule.next_run_at = next_local.astimezone(
                            ZoneInfo("UTC")
                        ).replace(tzinfo=None)
                    except Exception:
                        schedule.next_run_at = now + timedelta(seconds=60)

                    await session.commit()

                    launch_workflow_thread(
                        execution_id=execution_id,
                        workflow_id=str(schedule.workflow_id),
                        organization_id=str(schedule.organization_id),
                        definition=workflow.definition or {},
                        trigger_payload={"schedule_id": str(schedule.id)},
                    )
                    dispatched += 1
                    logger.info(
                        f"[schedule-poller] Dispatched '{schedule.name}' "
                        f"â {execution_id}, next: {schedule.next_run_at}"
                    )
                except Exception as e:
                    logger.error(f"[schedule-poller] {schedule.id}: {e}", exc_info=True)
                    await session.rollback()

        return {"dispatched": dispatched}

    t = threading.Thread(target=_poller_loop, daemon=True, name="schedule-poller")
    t.start()
    return stop_event


async def _handle_trigger_event(event, engine) -> str:
    """Bridge between TriggerManager and WorkflowEngine.

    Called when a trigger fires. Dispatches workflow execution
    to Celery worker for async background processing.

    Args:
        event: TriggerEvent from the trigger manager
        engine: WorkflowEngine instance

    Returns:
        execution_id
    """
    import logging
    from uuid import uuid4
    from db.database import AsyncSessionLocal
    from sqlalchemy import select

    logger = logging.getLogger(__name__)
    execution_id = str(uuid4())

    try:
        # Load workflow definition from DB
        async with AsyncSessionLocal() as session:
            from db.models.workflow import Workflow
            from db.models.execution import Execution

            result = await session.execute(
                select(Workflow).where(
                    Workflow.id == event.workflow_id,
                    Workflow.is_deleted == False,
                )
            )
            workflow = result.scalar_one_or_none()

            if not workflow:
                logger.error(f"Trigger fired for non-existent workflow: {event.workflow_id}")
                return execution_id

            if not workflow.is_enabled:
                logger.warning(f"Trigger fired for disabled workflow: {event.workflow_id}")
                return execution_id

            # Create Execution record
            execution = Execution(
                id=execution_id,
                organization_id=event.organization_id,
                workflow_id=event.workflow_id,
                trigger_type=event.trigger_type,
                status="pending",
            )
            session.add(execution)
            await session.commit()

            # Run directly in background thread (reliable, no Celery needed)
            from worker.run_workflow import launch_workflow_thread
            launch_workflow_thread(
                execution_id=execution_id,
                workflow_id=event.workflow_id,
                organization_id=event.organization_id,
                definition=workflow.definition or {},
                variables={},
                trigger_payload=event.payload,
            )

            logger.info(f"Trigger dispatched: {event.trigger_id} -> execution {execution_id}")

    except Exception as e:
        logger.error(f"Trigger event handling failed: {e}", exc_info=True)

    return execution_id


app = create_app()
