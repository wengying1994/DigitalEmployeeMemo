"""
Configuration management using Pydantic Settings.
Loads configuration from environment variables and .env file.
"""
import json
from functools import lru_cache
from typing import Any, Dict, List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/digital_employee_memo",
        description="PostgreSQL database URL for async operations"
    )
    DATABASE_URL_SYNC: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/digital_employee_memo",
        description="PostgreSQL database URL for sync operations (Alembic)"
    )

    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL for caching and pub/sub"
    )

    # Celery
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Celery broker URL"
    )
    CELERY_BACKEND_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Celery result backend URL"
    )

    # Security
    SECRET_KEY: str = Field(
        default="change-this-secret-key-in-production",
        description="Secret key for cryptographic operations"
    )
    DEBUG: bool = Field(default=True, description="Debug mode flag")

    # Application
    APP_HOST: str = Field(default="0.0.0.0", description="Application host")
    APP_PORT: int = Field(default=8000, description="Application port")
    API_V1_PREFIX: str = Field(default="/api/v1", description="API v1 prefix")

    # Reminder Policy (JSON string)
    REMINDER_POLICY: str = Field(
        default='{"immediate":{"delay":0,"methods":["in_app"]},"2h":{"delay":7200,"methods":["in_app","email"]},"24h":{"delay":86400,"methods":["in_app","email"]},"48h":{"delay":172800,"methods":["in_app","email","wechat"]},"72h":{"delay":259200,"methods":["in_app","email","wechat","sms"],"escalate_to":"secretary"}}',
        description="Reminder policy configuration as JSON"
    )

    # Notification Settings
    NOTIFICATION_EMAIL_ENABLED: bool = Field(
        default=True,
        description="Enable email notifications"
    )
    EMAIL_HOST: str = Field(default="smtp.example.com", description="SMTP host")
    EMAIL_PORT: int = Field(default=587, description="SMTP port")
    EMAIL_USER: str = Field(default="", description="SMTP user")
    EMAIL_PASSWORD: str = Field(default="", description="SMTP password")
    EMAIL_FROM: str = Field(default="notification@example.com", description="Email sender address")

    # Default Leader
    DEFAULT_LEADER_ID: int = Field(default=1, description="Default leader user ID")

    def get_reminder_policy(self) -> Dict[str, Any]:
        """Parse and return the reminder policy as a dictionary."""
        try:
            return json.loads(self.REMINDER_POLICY)
        except json.JSONDecodeError:
            # Default policy if JSON is invalid
            return {
                "immediate": {"delay": 0, "methods": ["in_app"]},
                "2h": {"delay": 7200, "methods": ["in_app", "email"]},
                "24h": {"delay": 86400, "methods": ["in_app", "email"]},
                "48h": {"delay": 172800, "methods": ["in_app", "email", "wechat"]},
                "72h": {"delay": 259200, "methods": ["in_app", "email", "wechat", "sms"], "escalate_to": "secretary"}
            }

    @property
    def reminder_policy_dict(self) -> Dict[str, Any]:
        """Property accessor for reminder policy."""
        return self.get_reminder_policy()


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()


# Global settings instance
settings = get_settings()
