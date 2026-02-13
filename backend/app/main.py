"""RPA Automation Engine - FastAPI Application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from api.routes import auth, health, workflows, executions, agents, users, credentials, schedules, analytics
from db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    settings = get_settings()
    await init_db()
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} started ({settings.ENVIRONMENT})")
    yield
    # Shutdown
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

    return app


app = create_app()
