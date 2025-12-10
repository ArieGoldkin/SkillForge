"""Application-wide constants for configuration and limits.

This module centralizes all magic numbers and string literals used throughout
the application to improve maintainability and consistency.
"""

# HTTP Status Codes
HTTP_OK = 200
HTTP_NOT_FOUND = 404
HTTP_ERROR_THRESHOLD = 400
HTTP_RATE_LIMITED = 429
HTTP_SERVER_ERROR_THRESHOLD = 500

# Timeout Configuration (in seconds)
DEFAULT_TIMEOUT = 30.0  # Default HTTP client timeout
EMBEDDING_TIMEOUT = 120.0  # Embedding service timeout (longer for large texts)
DB_TIMEOUT = 5.0  # Database connection timeout
DB_TEST_TIMEOUT = 10.0  # Database timeout in tests (longer for CI/CD)

# Text and Message Limits
MAX_ERROR_MESSAGE_LENGTH = 100  # Maximum length for error messages in responses
MAX_ERROR_MESSAGE_LENGTH_LONG = 200  # Maximum length for error messages in logs
MAX_TITLE_PREVIEW_LENGTH = 100  # Maximum length for title preview in logs
MAX_MODELS_PREVIEW_COUNT = 5  # Maximum number of models to show in error messages
SUPERVISOR_CONTENT_PREVIEW_LENGTH = 2000  # Maximum content length for supervisor prompt

# Retry Configuration
MAX_RETRY_ATTEMPTS = 3  # Maximum number of retry attempts
RETRY_MULTIPLIER_EMBEDDING = 2  # Exponential backoff multiplier for embeddings
RETRY_MIN_WAIT_EMBEDDING = 2  # Minimum wait time for embedding retries (seconds)
RETRY_MAX_WAIT_EMBEDDING = 16  # Maximum wait time for embedding retries (seconds)
# Test mode: Faster retries to avoid slow tests
RETRY_MIN_WAIT_EMBEDDING_TEST = 0.5  # Faster retries in tests (seconds)
RETRY_MAX_WAIT_EMBEDDING_TEST = 2  # Shorter max wait in tests (seconds)
RETRY_MULTIPLIER_JINA = 1  # Exponential backoff multiplier for Jina Reader
RETRY_MIN_WAIT_JINA = 1  # Minimum wait time for Jina retries (seconds)
RETRY_MAX_WAIT_JINA = 10  # Maximum wait time for Jina retries (seconds)
RETRY_MIN_WAIT_JINA_TEST = 0.5  # Faster retries in tests (seconds)
RETRY_MAX_WAIT_JINA_TEST = 2  # Shorter max wait in tests (seconds)

# Database Connection Pool Configuration
DB_POOL_SIZE = 5  # Number of connections to maintain in pool
DB_MAX_OVERFLOW = 10  # Maximum number of connections beyond pool_size
DB_POOL_RECYCLE = 3600  # Recycle connections after 1 hour (seconds)

# Content Types
CONTENT_TYPE_ARTICLE = "article"
CONTENT_TYPE_VIDEO = "video"
CONTENT_TYPE_REPO = "repo"

# Default Values
DEFAULT_TITLE = "Untitled"  # Default title when extraction fails to find one

# UUID Configuration
UUID_NAMESPACE_DNS = (
    "6ba7b810-9dad-11d1-80b4-00c04fd430c8"  # DNS namespace for deterministic UUID generation
)

# SSE Event Throttling
SSE_EVENT_THROTTLE_MS = 500  # Minimum time between SSE events (milliseconds)
SSE_EVENT_THROTTLE_CHARS = 50  # Minimum characters between SSE events

# Search Configuration
SEARCH_TOP_K_MIN = 1  # Minimum number of search results
SEARCH_TOP_K_MAX = 100  # Maximum number of search results
SEARCH_QUERY_MAX_LENGTH = 1000  # Maximum search query length in characters

# Re-ranking Configuration
RERANK_ALPHA = 0.3  # Weight for base retrieval score (RRF/semantic/keyword)
RERANK_BETA = 0.5  # Weight for LLM relevance score
RERANK_GAMMA = 0.2  # Weight for structural prior score (metadata-based)
RERANK_DEFAULT_TIMEOUT = 5.0  # Default timeout for re-ranking in seconds
RERANK_DEFAULT_CANDIDATES = 50  # Default number of candidates to consider
RERANK_DEFAULT_FINAL_COUNT = 10  # Default number of results after re-ranking
RERANK_MODEL = (
    "gpt-4o-mini"  # Cost-effective model for re-ranking (fallback if gpt-5-nano unavailable)
)

# Structural Prior Weights (for metadata-based scoring)
STRUCTURAL_WEIGHT_SECTION_PRESENT = 0.10  # Boost for having explicit section title
STRUCTURAL_WEIGHT_PATH_DEPTH_PENALTY = 0.05  # Penalty per extra path level beyond 2
STRUCTURAL_WEIGHT_POSITION_EARLY = 0.10  # Boost for chunks in first 20% of section
STRUCTURAL_WEIGHT_POSITION_LATE = -0.05  # Penalty for chunks in last 20% of section
STRUCTURAL_WEIGHT_CODE_BLOCK = 0.05  # Boost for code block chunks
STRUCTURAL_WEIGHT_HEADING = 0.10  # Boost for heading chunks
STRUCTURAL_PATH_DEPTH_THRESHOLD = 2  # Path depth above this triggers penalty
STRUCTURAL_POSITION_EARLY_THRESHOLD = 0.2  # First 20% of section considered "early"
STRUCTURAL_POSITION_LATE_THRESHOLD = 0.8  # Last 20% of section considered "late"
