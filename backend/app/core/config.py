"""Application settings loaded from environment variables."""

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_env_file() -> str:
    """Get environment file path, preferring .env.test for tests."""
    # Check if ENV_FILE is explicitly set
    if env_file := os.environ.get("ENV_FILE"):
        return env_file

    # Check if we're in test mode and .env.test exists
    test_env = Path(__file__).parent.parent / ".env.test"
    if test_env.exists() and (
        os.environ.get("PYTEST_CURRENT_TEST")
        or os.environ.get("ENVIRONMENT") == "testing"
    ):
        return str(test_env)

    # Default to .env
    return ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    ENVIRONMENT: str = Field(default="development", description="Runtime environment")
    LOG_LEVEL: str = Field(default="DEBUG", description="Logging level")
    API_V1_PREFIX: str = Field(default="/api/v1", description="API v1 prefix")

    # Server
    HOST: str = Field(default="127.0.0.1", description="Server host")
    PORT: int = Field(default=8500, description="Server port")
    RELOAD: bool = Field(default=True, description="Enable auto-reload")

    # CORS
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:5173"],
        description="Allowed CORS origins",
    )

    # Database (to be used in Task 1.2.5)
    DATABASE_URL: str | None = Field(
        default=None,
        description="PostgreSQL connection string",
    )

    # LLM Configuration (to be used in Task 1.5.2)
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL",
    )
    OLLAMA_MODEL: str = Field(default="llama3.1:8b", description="Ollama model name")

    # Embedding Configuration (to be used in Task 1.5.2)
    OLLAMA_EMBEDDING_MODEL: str = Field(
        default="nomic-embed-text",
        description="Ollama embedding model for vector generation",
    )
    EMBEDDING_DIMENSIONS: int = Field(
        default=768,
        description=(
            "Expected embedding dimensions "
            "(768 for nomic-embed-text, 1536 for OpenAI text-embedding-3-small)"
        ),
    )

    # Content Extraction (to be used in Task 1.4.2)
    JINA_API_KEY: str | None = Field(default=None, description="Jina AI API key (optional for dev)")

    model_config = SettingsConfigDict(
        env_file=_get_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment is one of allowed values."""
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            msg = f"ENVIRONMENT must be one of {allowed}"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def validate_production_requirements(self) -> "Settings":
        """Validate required variables in production environment."""
        if self.ENVIRONMENT == "production" and not self.DATABASE_URL:
            error_msg = "DATABASE_URL is required in production environment"
            raise ValueError(error_msg)
        return self

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"

    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.ENVIRONMENT == "staging"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Uses LRU cache to avoid reloading configuration on every access.
    Cache is cleared in tests via fixtures.
    """
    return Settings()


settings = get_settings()
