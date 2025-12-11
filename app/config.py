"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env file and override existing env vars
load_dotenv(override=True)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = True
    app_secret_key: str = Field(default="dev-secret-key-change-in-production")

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Claude Agent SDK
    anthropic_api_key: str = Field(default="")

    # Vercel Deployment
    vercel_token: str = Field(default="")
    vercel_team_id: str | None = None
    vercel_deploy_real: bool = False  # Set to True to enable real Vercel deployment

    # Optional: Redis
    redis_url: str | None = None

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["console", "json"] = "console"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
