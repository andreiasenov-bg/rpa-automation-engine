"""Application configuration."""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Settings
    APP_NAME: str = "RPA Automation Engine"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production

    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # Database Settings
    DATABASE_URL: str = "sqlite+aiosqlite:///./test.db"
    SQLALCHEMY_ECHO: bool = False
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    # Redis Settings
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security Settings
    # MUST be set in environment for production; defaults only safe for development
    SECRET_KEY: str = ""
    ENCRYPTION_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Claude AI Settings
    # Accepts either ANTHROPIC_API_KEY or CHAT_API_KEY (for backward compat)
    ANTHROPIC_API_KEY: str = ""
    CHAT_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-sonnet-4-5-20250929"
    CLAUDE_MAX_TOKENS: int = 4096
    CLAUDE_TEMPERATURE: float = 0.3
    CLAUDE_TIMEOUT: int = 120
    CLAUDE_MAX_RETRIES: int = 3
    CLAUDE_RETRY_DELAY: float = 1.0
    CLAUDE_SYSTEM_PROMPT: str = (
        "You are an AI assistant integrated into an RPA automation engine. "
        "You help analyze data, make decisions, process documents, "
        "generate content, and provide intelligent automation support. "
        "Be precise, structured, and action-oriented in your responses."
    )

    # CORS Settings
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8080"
    ALLOW_CREDENTIALS: bool = True
    ALLOW_METHODS: list = ["*"]
    ALLOW_HEADERS: list = ["*"]

    # Firebase Cloud Messaging (FCM) Settings
    FCM_SERVICE_ACCOUNT_JSON: str = ""  # Path to Firebase service account JSON
    FCM_PROJECT_ID: str = ""  # Firebase project ID

    # Storage Settings
    STORAGE_PATH: str = "./storage"  # Base path for workflow files (results, icons, docs)

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse ALLOWED_ORIGINS string into a list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    def validate_secrets(self) -> None:
        """Validate that critical secrets are not using defaults in production.

        Raises:
            RuntimeError: If production environment has empty or default SECRET_KEY/ENCRYPTION_KEY
        """
        if self.is_production:
            if not self.SECRET_KEY:
                raise RuntimeError(
                    "CRITICAL: SECRET_KEY environment variable must be set in production. "
                    "Do not use default values."
                )
            if not self.ENCRYPTION_KEY:
                raise RuntimeError(
                    "CRITICAL: ENCRYPTION_KEY environment variable must be set in production. "
                    "Do not use default values."
                )

    class Config:
        """Pydantic config."""

        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings.

    Uses caching to ensure settings are loaded only once.

    Returns:
        Settings object with all configuration values
    """
    return Settings()
