"""Application settings loaded from environment variables.

This module provides the Settings class for managing application configuration
using Pydantic Settings. Configuration is loaded from environment variables or
a .env file, with special handling for test environments.

Key Features:
    - Environment-aware configuration (development, staging, production)
    - Automatic .env file loading with test environment support
    - Cached settings instance for performance
    - Type-safe configuration with validation
    - Production requirement validation

Settings Pattern:
    The Settings class uses Pydantic Settings which automatically loads values
    from environment variables. The get_settings() function provides a cached
    instance to avoid reloading configuration on every access.

Environment File Loading:
    - Production/Development: Loads from .env file
    - Tests: Automatically loads from .env.test if PYTEST_CURRENT_TEST is set
    - Explicit override: ENV_FILE environment variable takes precedence

Example:
    ```python
    from app.core.config import settings, get_settings

    # Use cached global instance
    if settings.ENVIRONMENT == "development":
        print("Running in development mode")

    # Or get fresh instance (cache cleared in tests)
    settings = get_settings()
    ```

"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Final

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LLM_PROVIDER_ALIAS_MAP: Final[dict[str, str]] = {
    "openai": "openai",
    "gpt": "openai",
    "gpt4": "openai",
    "gpt5": "openai",
    "anthropic": "anthropic",
    "claude": "anthropic",
    "sonnet": "anthropic",
    "google": "google_genai",
    "gemini": "google_genai",
    "google_genai": "google_genai",
    "grok": "xai",
    "xai": "xai",
    "composer": "perplexity",
    "perplexity": "perplexity",
    "kimi": "moonshot",
    "moonshot": "moonshot",
    "groq": "groq",
    "deepseek": "deepseek",
    "deepseek-v3": "deepseek",
}

LLM_PROVIDER_API_FIELDS: Final[dict[str, str]] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google_genai": "GOOGLE_API_KEY",
    "xai": "XAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}


def _canonical_provider(raw_provider: str | None) -> str | None:
    if not raw_provider:
        return None
    normalized = raw_provider.strip().lower()
    if not normalized:
        return None
    return LLM_PROVIDER_ALIAS_MAP.get(normalized, normalized)


def _split_provider_from_model(model_identifier: str) -> tuple[str | None, str]:
    """Return (provider, model_name) if provider prefix is embedded in identifier."""
    identifier = model_identifier.strip()
    if not identifier:
        return None, identifier

    for separator in ("/", ":"):
        if separator in identifier:
            prefix, remainder = identifier.split(separator, 1)
            canonical = _canonical_provider(prefix)
            if canonical:
                return canonical, remainder.strip()
            # Only treat separator as provider delimiter if prefix is recognized
            # otherwise keep searching / fall through

    return None, identifier


def _infer_provider_from_model(model_identifier: str) -> str | None:
    """Infer provider from model identifier using prefix heuristics."""
    embedded_provider, _ = _split_provider_from_model(model_identifier)
    if embedded_provider:
        return embedded_provider

    normalized = "".join(ch if ch.isalnum() else " " for ch in model_identifier.strip().lower())
    tokens = normalized.split()
    if not tokens:
        return None

    first_token = tokens[0]
    for alias, canonical in LLM_PROVIDER_ALIAS_MAP.items():
        if first_token.startswith(alias):
            return canonical

    return None


def _get_env_file() -> str:
    """Get environment file path, preferring .env.test for tests.

    This function is called at class definition time, so it checks
    environment variables that are set before the Settings class is imported.
    For tests, pytest sets PYTEST_CURRENT_TEST automatically, and conftest.py
    sets ENV_FILE before any tests run.
    """
    # Check if ENV_FILE is explicitly set (set by conftest.py for tests)
    if env_file := os.environ.get("ENV_FILE"):
        return env_file

    # Check if we're in test mode and .env.test exists
    # PYTEST_CURRENT_TEST is automatically set by pytest when running tests
    test_env = Path(__file__).parent.parent / ".env.test"
    if test_env.exists() and os.environ.get("PYTEST_CURRENT_TEST"):
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

    # Multi-provider LLM configuration
    LLM_MODEL: str = Field(
        default="gpt-5-mini",
        description=(
            "Primary LLM identifier. Supports formats like 'gpt-5-mini', "
            "'claude-sonnet-4', 'gemini-2.0-flash', or provider-prefixed "
            "values. Default uses GPT-5 Mini for development. "
            "For production, use 'gpt-5-mini' ($0.25/$2.00 - recommended, "
            "newer + cheaper than GPT-4o Mini) or 'gpt-5' ($1.25/$10.00 - "
            "5x more expensive but maximum quality). Verified November 24, 2025."
        ),
    )
    LLM_PROVIDER: str | None = Field(
        default=None,
        description=(
            "Optional override for the LLM provider (e.g., openai, anthropic, "
            "google_genai). When omitted, the provider is inferred "
            "from LLM_MODEL."
        ),
    )
    OPENAI_API_KEY: str | None = Field(
        default=None,
        description="OpenAI API key (required when using OpenAI models).",
    )
    ANTHROPIC_API_KEY: str | None = Field(
        default=None,
        description="Anthropic API key (required when using Anthropic models).",
    )
    GOOGLE_API_KEY: str | None = Field(
        default=None,
        description="Google API key (required when using Gemini models).",
    )
    XAI_API_KEY: str | None = Field(
        default=None,
        description="xAI API key (required when using Grok models).",
    )
    DEEPSEEK_API_KEY: str | None = Field(
        default=None,
        description="DeepSeek API key (required when using DeepSeek models).",
    )
    LLM_TEMPERATURE: float | None = Field(
        default=None,
        description=(
            "Temperature for LLM responses (0.0-2.0). Lower = more deterministic, "
            "higher = more creative. Defaults to model provider's default if not set."
        ),
    )
    LLM_MAX_TOKENS: int | None = Field(
        default=None,
        description=(
            "Maximum tokens in LLM response. Limits response length. "
            "Defaults to model provider's default if not set."
        ),
    )
    LLM_TIMEOUT: float | None = Field(
        default=60.0,
        description=(
            "Timeout in seconds for LLM API calls. Defaults to 60s. "
            "Set to None to use model provider's default."
        ),
    )
    LLM_RETRY_DELAY_BASE: float = Field(
        default=1.0,
        description=(
            "Base delay in seconds for retry exponential backoff. "
            "Smaller values = faster retries. Default 1.0s (1s, 2s, 4s). "
            "Use 0.1 for test environments (0.1s, 0.2s, 0.4s)."
        ),
    )

    # Embedding Configuration
    EMBEDDING_DIMENSIONS: int = Field(
        default=1536,
        description=("Expected embedding dimensions (1536 for OpenAI text-embedding-3-small)"),
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

    @field_validator("LLM_MODEL")
    @classmethod
    def validate_llm_model(cls, v: str) -> str:
        """Ensure LLM model identifier is not empty."""
        if not v or not v.strip():
            msg = "LLM_MODEL cannot be empty"
            raise ValueError(msg)
        return v.strip()

    @model_validator(mode="after")
    def validate_production_requirements(self) -> "Settings":
        """Validate required variables in production environment."""
        if self.ENVIRONMENT == "production" and not self.DATABASE_URL:
            error_msg = "DATABASE_URL is required in production environment"
            raise ValueError(error_msg)
        return self

    @model_validator(mode="after")
    def validate_llm_configuration(self) -> "Settings":
        """Ensure LLM provider/API key configuration is valid."""
        provider = self.resolved_llm_provider()
        api_field = LLM_PROVIDER_API_FIELDS.get(provider)
        if api_field and not getattr(self, api_field):
            msg = (
                f"{api_field} is required when using provider '{provider}'. "
                "Set it via environment variables or in the .env file."
            )
            raise ValueError(msg)
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

    def resolved_llm_provider(self) -> str:
        """Return canonical provider name for the configured LLM."""
        provider = _canonical_provider(self.LLM_PROVIDER)
        if provider:
            return provider

        inferred = _infer_provider_from_model(self.LLM_MODEL)
        if inferred:
            return inferred

        msg = (
            "Unable to determine LLM provider from LLM_MODEL. "
            "Set LLM_PROVIDER or provide LLM_MODEL in 'provider:model' format."
        )
        raise ValueError(msg)

    def resolved_llm_model_name(self) -> str:
        """Return model identifier without embedded provider prefix."""
        _, model_name = _split_provider_from_model(self.LLM_MODEL)
        return model_name.strip()


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Uses LRU cache to avoid reloading configuration on every access.
    Cache is cleared in tests via fixtures.
    """
    return Settings()


settings = get_settings()
