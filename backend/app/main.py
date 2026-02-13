"""RPA Automation Engine - FastAPI Application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from api.routes import auth, health, workflows, executions, agents, users, credentials, schedules, analytics, ai
from db.database import init_db
from integrations.claude_client import get_claude_client
from workflow.checkpoint import CheckpointManager
from workflow.recovery import RecoveryService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    settings = get_settings()
    await init_db()

    # Connect to Claude AI
    claude = await get_claude_client()
    if claude.is_configured:
        print(f"🤖 Claude AI connected (model: {settings.CLAUDE_MODEL})")
    else:
        print("⚠️  Claude AI not configured (set ANTHROPIC_API_KEY to enable)")

    # Recover interrupted executions from previous run
    try:
        checkpoint_mgr = CheckpointManager()
        recovery_svc = RecoveryService(checkpoint_manager=checkpoint_mgr)
        results = await recovery_svc.recover_all()
        recovered = sum(1 for r in results if r.recovered)
        if recovered > 0:
            print(f"🔄 Recovered {recovered} interrupted execution(s)")
        else:
            print("✅ No interrupted executions to recover")
    except Exception as e:
        print(f"⚠️  Recovery scan skipped: {e}")

    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} started")
    yield
    # Shutdown
    if claude.is_connected:
        await claude.disconnect()
    print("👋 Application shutting down...")


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

    # Register API routes
    app.include_router(health.router, prefix="/api", tags=["Health"])
    app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
    app.include_router(users.router, prefix="/api/users", tags=["Users"])
    app.include_router(workflows.router, prefix="/api/workflows", tags=["Workflows"])
    app.include_router(executions.router, prefix="/api/executions", tags=["Executions"])
    app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
    app.include_router(credentials.router, prefix="/api/credentials", tags=["Credentials"])
    app.include_router(schedules.router, prefix="/api/schedules", tags=["Schedules"])
    app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
    app.include_router(ai.router, prefix="/api/ai", tags=["AI - Claude Integration"])

    return app


app = create_app()
