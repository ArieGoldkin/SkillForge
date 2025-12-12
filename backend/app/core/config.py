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
    LOG_LEVEL: str = Field(
        default="INFO",
        description=(
            "Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL. "
            "SECURITY: DEBUG can expose sensitive information. Use INFO or higher in production."
        ),
    )
    API_V1_PREFIX: str = Field(default="/api/v1", description="API v1 prefix")

    # Server
    HOST: str = Field(
        default="127.0.0.1",
        description=(
            "Server host address. "
            "SECURITY: 0.0.0.0 allows external connections and is not allowed in production."
        ),
    )
    PORT: int = Field(default=8500, description="Server port")
    RELOAD: bool = Field(
        default=False,
        description=(
            "Enable auto-reload on code changes. "
            "SECURITY: Must be false in production (security risk if enabled)."
        ),
    )

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
        default="gemini-2.5-flash",
        description=(
            "Primary LLM identifier. Supports formats like 'gemini-2.5-flash', "
            "'gpt-5-mini', 'claude-sonnet-4', or provider-prefixed "
            "values. Default uses Gemini 2.5 Flash for development (fast, cost-effective). "
            "For production, use 'gemini-2.5-flash' ($0.15/$0.30 per 1M tokens - recommended, "
            "fastest response times) or 'claude-opus-4-5-20251101' ($5/$25 - best for agents, "
            "48-76% fewer tokens). Verified from reporter-accuracy project."
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
    LLM_MAX_RETRIES: int = Field(
        default=3,
        description=(
            "Maximum number of retry attempts for LLM API calls. "
            "Uses LangChain's built-in retry mechanism via max_retries parameter. "
            "Defaults to 3. Set to 0 to disable retries."
        ),
    )

    # Embedding Configuration
    EMBEDDING_DIMENSIONS: int = Field(
        default=1536,
        description=("Expected embedding dimensions (1536 for OpenAI text-embedding-3-small)"),
    )
    CHUNK_WINDOW_SHORT: int = Field(default=900, description="Token window for short docs")
    CHUNK_WINDOW_LONG: int = Field(default=600, description="Token window for long docs")
    CHUNK_OVERLAP_PCT: float = Field(default=0.12, description="Overlap ratio for chunk windows")
    DOC_LENGTH_THRESHOLD: int = Field(default=4000, description="Token threshold for long docs")
    ENABLE_SUMMARIES: bool = Field(
        default=False, description="Enable section summaries for routing"
    )
    ENABLE_COARSE_TO_FINE: bool = Field(
        default=False, description="Enable coarse-to-fine retrieval"
    )
    DEDUP_ENABLED: bool = Field(default=True, description="Enable shingle deduplication for chunks")
    MAX_CHUNKS_COARSE: int = Field(default=500, description="Cap coarse chunks per doc")
    MAX_CHUNKS_FINE: int = Field(default=2000, description="Cap fine chunks per doc")

    # Content Extraction (to be used in Task 1.4.2)
    JINA_API_KEY: str | None = Field(default=None, description="Jina AI API key (optional for dev)")

    # Telemetry & Metrics Configuration
    METRICS_ENABLED: bool = Field(
        default=True,
        description="Enable metrics collection and emission via structlog",
    )
    METRICS_FLUSH_INTERVAL: int = Field(
        default=60,
        description="Interval in seconds for emitting metrics summaries",
    )

    # Rate Limiting Configuration (Token Bucket)
    RATE_LIMIT_TOKENS_PER_MINUTE: int = Field(
        default=10000,
        description="Maximum sustained API request rate (tokens per minute)",
    )
    RATE_LIMIT_BURST_CAPACITY: int = Field(
        default=2000,
        description="Maximum burst capacity for rate limiter",
    )

    # Adaptive Batch Sizing Configuration
    BATCH_SIZE_INITIAL: int = Field(
        default=20,
        description="Initial batch size for embedding requests",
    )
    BATCH_SIZE_MIN: int = Field(
        default=1,
        description="Minimum batch size (floor during backpressure)",
    )
    BATCH_SIZE_MAX: int = Field(
        default=100,
        description="Maximum batch size (ceiling during healthy periods)",
    )
    BATCH_DECREASE_FACTOR_429: float = Field(
        default=0.5,
        description="Batch size multiplier on 429 rate limit (0.5 = halve)",
    )
    BATCH_DECREASE_FACTOR_5XX: float = Field(
        default=0.75,
        description="Batch size multiplier on 5xx server error (0.75 = reduce 25%)",
    )
    BATCH_INCREASE_FACTOR: float = Field(
        default=1.1,
        description="Batch size multiplier during healthy periods (1.1 = increase 10%)",
    )
    BATCH_COOLDOWN_SECONDS: float = Field(
        default=30.0,
        description="Minimum seconds between batch size adjustments",
    )
    BATCH_HEALTHY_WINDOW_SECONDS: float = Field(
        default=300.0,
        description="Duration of healthy operation required before increasing batch size",
    )

    # Error Tracking Configuration (Sliding Window)
    ERROR_RATE_WINDOW_SECONDS: int = Field(
        default=60,
        description="Time window for error rate calculation",
    )
    ERROR_RATE_THRESHOLD_PERCENT: float = Field(
        default=5.0,
        description="Error rate percentage threshold for triggering backoff",
    )

    # Vector Validation Configuration
    VECTOR_VALIDATION_ENABLED: bool = Field(
        default=True,
        description="Enable embedding vector validation (dimension, NaN, zero checks)",
    )
    VECTOR_ZERO_THRESHOLD: float = Field(
        default=1e-10,
        description="Threshold below which a vector is considered zero/invalid",
    )

    # Chunking Configuration (Issue #215)
    CHUNK_MAX_TOKENS: int = Field(
        default=7500,
        description="Hard limit for tokens per chunk (below 8K OpenAI API limit)",
    )
    CHUNK_PREFER_SEMANTIC_BREAKS: bool = Field(
        default=True,
        description="Prefer breaking at paragraph/heading boundaries when chunking",
    )

    # Deduplication Configuration (Issue #215)
    DEDUP_CHECK_DATABASE: bool = Field(
        default=True,
        description="Check database for existing hashes before embedding",
    )
    DEDUP_HASH_INCLUDES_MODEL: bool = Field(
        default=True,
        description="Include model and version in hash to trigger re-embedding on model upgrade",
    )

    # PII Screening Configuration (Issue #220)
    PII_SCREENING_ENABLED: bool = Field(
        default=False,
        description="Enable PII detection before embedding (default: false for dev)",
    )
    PII_SENSITIVITY_LEVEL: str = Field(
        default="medium",
        description="Detection sensitivity: low (email), medium (+phone/SSN), high (+API keys)",
    )
    PII_ACTION: str = Field(
        default="flag",
        description="Action on PII detection: flag (continue with metadata) or reject (fail)",
    )
    PII_REJECT_THRESHOLD: float = Field(
        default=0.3,
        description="Reject if PII density exceeds threshold (0.0-1.0)",
    )

    # Cleanup Configuration (Issue #220)
    CLEANUP_ENABLED: bool = Field(
        default=True,
        description="Enable scheduled cleanup jobs",
    )
    CLEANUP_DRAFT_TTL_DAYS: int = Field(
        default=7,
        description="Days before draft analyses are auto-deleted",
    )
    CLEANUP_BATCH_SIZE: int = Field(
        default=1000,
        description="Batch size for cleanup operations",
    )

    model_config = SettingsConfigDict(
        env_file=_get_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment is one of allowed values.

        Note: 'e2e' is a special environment for end-to-end testing that
        behaves like development but with E2E-specific configurations.
        """
        allowed = {"development", "staging", "production", "e2e"}
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
        """Validate required variables and security settings in production environment."""
        if not self.is_production():
            return self

        # Require DATABASE_URL in production
        if not self.DATABASE_URL:
            error_msg = "DATABASE_URL is required in production environment"
            raise ValueError(error_msg)

        # Validate database URL doesn't contain weak passwords
        if self.DATABASE_URL:
            weak_passwords = ["devpass", "password", "pass", "123456", "admin", "test"]
            url_lower = self.DATABASE_URL.lower()
            for weak_pwd in weak_passwords:
                if weak_pwd in url_lower:
                    error_msg = (
                        f"SECURITY: Weak password detected in DATABASE_URL. "
                        f"Production databases must use strong passwords. "
                        f"Found weak pattern: '{weak_pwd}'"
                    )
                    raise ValueError(error_msg)

        # Validate HOST is not 0.0.0.0 in production (security risk)
        if self.HOST == "0.0.0.0":
            error_msg = (
                "SECURITY: HOST=0.0.0.0 is not allowed in production. "
                "Use 127.0.0.1 or a specific IP address with proper firewall rules."
            )
            raise ValueError(error_msg)

        # Validate RELOAD is disabled in production
        if self.RELOAD:
            error_msg = (
                "SECURITY: RELOAD=true is not allowed in production. "
                "Auto-reload is a security risk in production environments."
            )
            raise ValueError(error_msg)

        # Validate LOG_LEVEL is not DEBUG in production
        if self.LOG_LEVEL == "DEBUG":
            error_msg = (
                "SECURITY: LOG_LEVEL=DEBUG is not allowed in production. "
                "DEBUG logging can expose sensitive information. Use INFO or higher."
            )
            raise ValueError(error_msg)

        # Validate CORS_ORIGINS doesn't allow all origins in production
        if "*" in self.CORS_ORIGINS or len(self.CORS_ORIGINS) == 0:
            error_msg = (
                "SECURITY: CORS_ORIGINS must specify exact origins in production. "
                "Never use ['*'] or empty list. Specify your frontend URL(s)."
            )
            raise ValueError(error_msg)

        return self

    @model_validator(mode="after")
    def validate_llm_configuration(self) -> "Settings":
        """Ensure LLM provider/API key configuration is valid."""
        # Skip validation in development/e2e if API key is not set (allows local dev without API keys)
        if self.is_development() or self.is_e2e():
            return self

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

    def is_e2e(self) -> bool:
        """Check if running in E2E testing environment."""
        return self.ENVIRONMENT == "e2e"

    def is_non_production(self) -> bool:
        """Check if running in any non-production environment (dev, e2e, staging)."""
        return not self.is_production()

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
