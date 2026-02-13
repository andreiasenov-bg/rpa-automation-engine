"""RPA Automation Engine - FastAPI Application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from api.v1.router import api_v1_router
from api.routes import health
from db.database import init_db
from integrations.claude_client import get_claude_client
from integrations.registry import get_integration_registry
from workflow.checkpoint import CheckpointManager
from workflow.recovery import RecoveryService
from workflow.engine import get_workflow_engine
from triggers.manager import get_trigger_manager
from notifications.manager import get_notification_manager
from core.logging_config import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    settings = get_settings()
    setup_logging()
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

    print(f"[startup] {settings.APP_NAME} v{settings.APP_VERSION} started ({settings.ENVIRONMENT})")
    yield
    # Shutdown
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

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Root health check (unversioned — for load balancers / k8s probes)
    app.include_router(health.router, prefix="/api", tags=["Health"])

    # Versioned API — all business endpoints under /api/v1
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    return app


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
    from db.session import AsyncSessionLocal
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

            # Dispatch to Celery worker
            from worker.tasks.workflow import execute_workflow
            execute_workflow.delay(
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
