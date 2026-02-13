"""Application configuration."""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Settings
    APP_NAME: str = "RPA Automation Engine"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # Database Settings
    DATABASE_URL: str = "sqlite+aiosqlite:///./test.db"
    SQLALCHEMY_ECHO: bool = False

    # Redis Settings
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security Settings
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ENCRYPTION_KEY: str = "your-encryption-key-must-be-32-bytes-base64-encoded"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Claude AI Settings
    ANTHROPIC_API_KEY: str = ""
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
    ALLOWED_ORIGINS: list = ["http://localhost:3000", "http://localhost:8080"]
    ALLOW_CREDENTIALS: bool = True
    ALLOW_METHODS: list = ["*"]
    ALLOW_HEADERS: list = ["*"]

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
