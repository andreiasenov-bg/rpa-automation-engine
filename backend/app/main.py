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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    settings = get_settings()
    await init_db()

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

    Called when a trigger fires. Creates an execution and runs the workflow.

    Args:
        event: TriggerEvent from the trigger manager
        engine: WorkflowEngine instance

    Returns:
        execution_id
    """
    from uuid import uuid4
    execution_id = str(uuid4())

    # TODO: Load workflow definition from DB
    # TODO: Create Execution record in DB
    # TODO: Run engine.execute() in background task

    return execution_id


app = create_app()
