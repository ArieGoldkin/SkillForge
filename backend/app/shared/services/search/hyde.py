"""HyDE (Hypothetical Document Embeddings) for improved semantic retrieval.

This module implements HyDE to address vocabulary mismatch in semantic search.
Instead of embedding the raw query directly, HyDE generates a hypothetical
answer document using an LLM, then embeds that document. The hypothetical
document uses vocabulary similar to actual documents in the corpus, improving
retrieval for abstract or conceptual queries.

Issue #602: HyDE for Vocabulary Mismatch Resolution
Target: Improve retrieval pass rate from 87% to 92%

Problem Example:
    Query: "scaling async data pipelines"
    Actual docs use: "event-driven messaging", "Apache Kafka", "message brokers"
    → Direct embedding fails due to vocabulary mismatch

HyDE Solution:
    Query: "scaling async data pipelines"
    → Generate: "To scale asynchronous data pipelines, use event-driven
       messaging with Apache Kafka. Message brokers provide..."
    → Embed the hypothetical document instead
    → Now matches docs using similar terminology

Architecture (Option B - Per-Concept HyDE):
    1. Takes decomposed concepts from QueryDecomposer
    2. Generates hypothetical document for each concept in parallel
    3. Embeds hypothetical documents
    4. Returns enhanced embeddings for semantic search

Example:
    >>> hyde = HyDEService(embedding_service)
    >>> result = await hyde.generate("scaling async data pipelines")
    >>> # Use result.embedding for semantic search

"""

from __future__ import annotations

import asyncio
import hashlib
import re
import time
from enum import Enum
from typing import TYPE_CHECKING, Literal, cast

from pydantic import BaseModel, Field, ValidationError

from app.core.logging import get_logger
from app.core.tracing import traced_tool, update_current_observation
from app.shared.services.llm.factory import get_llm_provider

# Exception types for error handling (same as decomposer)
LLM_ERRORS = (
    ValueError,
    TypeError,
    RuntimeError,
    ValidationError,
    TimeoutError,
    ConnectionError,
)

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from app.shared.services.embeddings.service import EmbeddingService
    from app.shared.services.llm.ollama_provider import OllamaProvider

# Type alias for LLM providers (cloud + local)
type LLMProvider = BaseChatModel | OllamaProvider

logger = get_logger(__name__)


# -----------------------------------------------------------------------------
# Configuration Constants
# -----------------------------------------------------------------------------

# HyDE generation settings
HYDE_MAX_TOKENS = 150  # Keep hypothetical docs concise
HYDE_TIMEOUT_SECONDS = 3.0  # Timeout before fallback to direct embedding
HYDE_TEMPERATURE = 0.3  # Low temp for consistency, some creativity

# Cache settings
HYDE_CACHE_L1_SIZE = 500  # In-memory cache entries
HYDE_CACHE_L1_TTL = 300  # 5 minutes TTL

# Security settings
HYDE_MAX_QUERY_LENGTH = 500  # Max chars before truncation


# -----------------------------------------------------------------------------
# Pydantic Schemas
# -----------------------------------------------------------------------------


class HyDESource(str, Enum):
    """Source of hypothetical document generation."""

    CACHE_L1 = "cache_l1"
    CACHE_L2 = "cache_l2"
    LLM = "llm"
    FALLBACK = "fallback"  # Direct embedding on LLM failure


class HypotheticalDocument(BaseModel):
    """LLM output schema for hypothetical document generation."""

    document: str = Field(
        ...,
        min_length=20,
        max_length=1000,
        description="Hypothetical document that answers the query",
    )


class HyDEResult(BaseModel):
    """Result of HyDE generation."""

    original_query: str = Field(..., description="The original search query/concept")
    hypothetical_doc: str = Field(
        ..., description="Generated hypothetical document (or original query if fallback)"
    )
    embedding: list[float] = Field(..., description="Embedding of the hypothetical document")
    source: HyDESource = Field(..., description="How the result was obtained")
    latency_ms: float = Field(..., description="Time taken for HyDE generation in ms")


class BatchHyDEResult(BaseModel):
    """Result of batch HyDE generation for multiple concepts."""

    results: list[HyDEResult] = Field(..., description="HyDE results for each input concept")
    total_latency_ms: float = Field(..., description="Total time for batch processing")
    cache_hits: int = Field(default=0, description="Number of cache hits")
    llm_calls: int = Field(default=0, description="Number of LLM calls made")


# -----------------------------------------------------------------------------
# Security: PII Sanitization and Prompt Injection Defense
# -----------------------------------------------------------------------------


class HyDESafetyValidator:
    """Security validator for HyDE query processing.

    Implements defense-in-depth for LLM safety:
    1. PII Sanitization - Strips UUIDs, emails, and sensitive patterns
    2. Prompt Injection Detection - Blocks common injection attempts
    3. Length Limiting - Prevents token abuse

    Issue #602: Security hardening for HyDE embeddings

    """

    # PII patterns to redact (compiled for performance)
    UUID_PATTERN = re.compile(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        re.IGNORECASE,
    )
    EMAIL_PATTERN = re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        re.IGNORECASE,
    )
    # Metadata field patterns that shouldn't be in LLM prompts
    METADATA_PATTERN = re.compile(
        r"\b(user_id|tenant_id|api_key|auth_token|password|secret)\s*[=:]\s*\S+",
        re.IGNORECASE,
    )

    # Prompt injection patterns (case-insensitive)
    _INJECTION_PATTERNS: tuple[str, ...] = (
        r"ignore\s+(the\s+)?(previous|all|above|prior)(\s+(previous|all|above|prior))?\s+instructions?",
        r"forget\s+(everything|all|previous)",
        r"you\s+are\s+now\s+(in\s+)?admin",
        r"system\s*:\s*",
        r"assistant\s*:\s*",
        r"<\s*system\s*>",
        r"<\s*/?\s*instructions?\s*>",
        r"\]\s*\[\s*system",
    )
    _INJECTION_REGEX = re.compile(
        "|".join(_INJECTION_PATTERNS),
        re.IGNORECASE,
    )

    @classmethod
    def sanitize_query(cls, query: str, max_length: int = HYDE_MAX_QUERY_LENGTH) -> str:
        """Sanitize query by removing PII and sensitive patterns.

        Args:
            query: Raw user query
            max_length: Maximum allowed query length

        Returns:
            Sanitized query safe for LLM processing.

        """
        if not query:
            return query

        # Step 1: Truncate if too long
        result = query[:max_length] if len(query) > max_length else query

        # Step 2: Redact UUIDs
        result = cls.UUID_PATTERN.sub("[REDACTED_ID]", result)

        # Step 3: Redact emails
        result = cls.EMAIL_PATTERN.sub("[REDACTED_EMAIL]", result)

        # Step 4: Redact metadata patterns
        result = cls.METADATA_PATTERN.sub("[REDACTED_FIELD]", result)

        # Step 5: Normalize whitespace
        return " ".join(result.split())

    @classmethod
    def detect_injection(cls, query: str) -> bool:
        """Detect potential prompt injection attempts.

        Args:
            query: Query to check for injection patterns

        Returns:
            True if injection pattern detected, False otherwise

        """
        if not query:
            return False

        return bool(cls._INJECTION_REGEX.search(query))

    @classmethod
    def validate_and_sanitize(
        cls, query: str, max_length: int = HYDE_MAX_QUERY_LENGTH
    ) -> tuple[str, bool, list[str]]:
        """Full validation and sanitization pipeline.

        Args:
            query: Raw user query
            max_length: Maximum allowed query length

        Returns:
            Tuple of (sanitized_query, is_safe, list_of_issues)

        """
        issues: list[str] = []

        # Check for injection first
        if cls.detect_injection(query):
            issues.append("prompt_injection_detected")
            logger.warning(
                "hyde_injection_detected",
                query_preview=query[:50],
            )
            # Return original query - let the service decide to fallback
            return query, False, issues

        # Sanitize PII
        sanitized = cls.sanitize_query(query, max_length)

        # Track if any sanitization occurred
        if sanitized != query:
            if len(query) > max_length:
                issues.append("query_truncated")
            if "[REDACTED_ID]" in sanitized:
                issues.append("uuid_redacted")
            if "[REDACTED_EMAIL]" in sanitized:
                issues.append("email_redacted")
            if "[REDACTED_FIELD]" in sanitized:
                issues.append("metadata_redacted")

            logger.info(
                "hyde_query_sanitized",
                original_length=len(query),
                sanitized_length=len(sanitized),
                issues=issues,
            )

        return sanitized, True, issues


# -----------------------------------------------------------------------------
# HyDE Prompt Template
# -----------------------------------------------------------------------------

HYDE_PROMPT_TEMPLATE = """You are a technical documentation expert. Given a search query, write a short, factual document that would answer this query. Write as if this document exists in a technical knowledge base.

Query: "{query}"

Write a concise hypothetical document (2-4 sentences) that directly addresses this query. Use technical terminology that would appear in actual documentation. Do not say "this document explains" or similar meta-text - just write the content directly.

Document:"""


# -----------------------------------------------------------------------------
# HyDE Service
# -----------------------------------------------------------------------------


class HyDEService:
    """Generates hypothetical document embeddings for improved retrieval.

    This service implements HyDE (Hypothetical Document Embeddings) which:
    1. Takes a query or concept
    2. Generates a hypothetical document that would answer it
    3. Embeds the hypothetical document instead of the raw query
    4. Returns the embedding for semantic search

    The hypothetical document uses vocabulary similar to actual documents,
    bridging the vocabulary gap between user queries and corpus content.

    Attributes:
        embedding_service: Service for generating embeddings
        llm: Language model for generating hypothetical documents
        cache: Optional HyDE cache for performance

    Example:
        >>> hyde = HyDEService(embedding_service)
        >>> result = await hyde.generate("scaling async pipelines")
        >>> # result.embedding now captures "event-driven", "Kafka" vocabulary

    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        llm: LLMProvider | None = None,
        cache: HyDECache | None = None,
    ) -> None:
        """Initialize HyDEService with dependencies.

        Args:
            embedding_service: Required for embedding hypothetical documents
            llm: Language model override (defaults to factory selection)
            cache: HyDE cache (created if not provided)

        """
        self.embedding_service = embedding_service
        self._llm = llm
        self._cache = cache

        logger.info("hyde_service_initialized")

    @property
    def llm(self) -> LLMProvider:
        """Lazy-load LLM provider."""
        if self._llm is None:
            # Use reasoning model for document generation
            self._llm = get_llm_provider(task_type="reasoning")
        return self._llm

    @property
    def cache(self) -> HyDECache:
        """Lazy-load HyDE cache."""
        if self._cache is None:
            self._cache = HyDECache()
        return self._cache

    @traced_tool("hyde_generate", tags=["search", "hyde", "embedding"])
    async def generate(self, query: str) -> HyDEResult:
        """Generate hypothetical document embedding for a single query.

        This is the main entry point for single-query HyDE. It:
        1. Checks cache for previously generated documents
        2. Generates hypothetical document if not cached
        3. Embeds the hypothetical document
        4. Returns the embedding for search

        Args:
            query: The search query or concept

        Returns:
            HyDEResult with hypothetical document and embedding

        """
        start_time = time.perf_counter()
        query = query.strip()

        # Step 1: Check cache
        cached_doc = await self.cache.get(query)
        if cached_doc is not None:
            # Generate embedding for cached doc
            embedding = await self.embedding_service.generate_embedding(cached_doc)
            latency_ms = (time.perf_counter() - start_time) * 1000

            source = (
                HyDESource.CACHE_L1 if self.cache.last_hit_tier == "l1" else HyDESource.CACHE_L2
            )

            # Langfuse: Record cache hit metrics
            update_current_observation(
                metadata={
                    "cache_hit": True,
                    "source": source.value,
                    "latency_ms": round(latency_ms, 2),
                }
            )

            logger.info(
                "hyde_cache_hit",
                query=query[:100],
                source=source.value,
                latency_ms=latency_ms,
            )

            return HyDEResult(
                original_query=query,
                hypothetical_doc=cached_doc,
                embedding=embedding,
                source=source,
                latency_ms=latency_ms,
            )

        # Step 2: Generate hypothetical document
        hypothetical_doc = await self._generate_hypothetical(query)
        source = HyDESource.LLM if hypothetical_doc != query else HyDESource.FALLBACK

        # Step 3: Cache the generated doc (if not fallback)
        if source == HyDESource.LLM:
            await self.cache.set(query, hypothetical_doc)

        # Step 4: Generate embedding
        embedding = await self.embedding_service.generate_embedding(hypothetical_doc)

        latency_ms = (time.perf_counter() - start_time) * 1000

        # Langfuse: Record generation metrics
        update_current_observation(
            metadata={
                "cache_hit": False,
                "source": source.value,
                "latency_ms": round(latency_ms, 2),
                "hypothetical_doc_length": len(hypothetical_doc),
                "security_fallback": source == HyDESource.FALLBACK,
            }
        )

        logger.info(
            "hyde_generated",
            query=query[:100],
            hypothetical_len=len(hypothetical_doc),
            source=source.value,
            latency_ms=latency_ms,
        )

        return HyDEResult(
            original_query=query,
            hypothetical_doc=hypothetical_doc,
            embedding=embedding,
            source=source,
            latency_ms=latency_ms,
        )

    @traced_tool("hyde_generate_batch", tags=["search", "hyde", "batch"])
    async def generate_batch(self, concepts: list[str]) -> BatchHyDEResult:
        """Generate hypothetical document embeddings for multiple concepts.

        This is the recommended method for multi-concept queries (Option B).
        It processes all concepts in parallel for optimal latency.

        Args:
            concepts: List of concepts to generate HyDE embeddings for

        Returns:
            BatchHyDEResult with all results and aggregate stats

        """
        start_time = time.perf_counter()

        if not concepts:
            return BatchHyDEResult(
                results=[],
                total_latency_ms=0,
                cache_hits=0,
                llm_calls=0,
            )

        # Process all concepts in parallel
        results = await asyncio.gather(
            *[self.generate(concept) for concept in concepts],
            return_exceptions=False,
        )

        # Calculate stats
        cache_hits = sum(
            1 for r in results if r.source in (HyDESource.CACHE_L1, HyDESource.CACHE_L2)
        )
        llm_calls = sum(1 for r in results if r.source == HyDESource.LLM)
        fallbacks = sum(1 for r in results if r.source == HyDESource.FALLBACK)
        total_latency_ms = (time.perf_counter() - start_time) * 1000

        # Langfuse: Record batch metrics
        update_current_observation(
            metadata={
                "num_concepts": len(concepts),
                "cache_hits": cache_hits,
                "llm_calls": llm_calls,
                "security_fallbacks": fallbacks,
                "total_latency_ms": round(total_latency_ms, 2),
                "cache_hit_rate": round(cache_hits / len(concepts), 2) if concepts else 0,
            }
        )

        logger.info(
            "hyde_batch_complete",
            num_concepts=len(concepts),
            cache_hits=cache_hits,
            llm_calls=llm_calls,
            total_latency_ms=total_latency_ms,
        )

        return BatchHyDEResult(
            results=results,
            total_latency_ms=total_latency_ms,
            cache_hits=cache_hits,
            llm_calls=llm_calls,
        )

    async def _generate_hypothetical(self, query: str) -> str:
        """Generate a hypothetical document using LLM.

        Includes security hardening (Issue #602):
        1. PII sanitization (UUIDs, emails, metadata)
        2. Prompt injection detection and blocking
        3. Query length limiting

        Args:
            query: The search query to generate a document for

        Returns:
            Hypothetical document text, or original query on failure

        """
        # Security: Validate and sanitize query before LLM processing
        sanitized_query, is_safe, _issues = HyDESafetyValidator.validate_and_sanitize(query)

        if not is_safe:
            # Injection detected - fall back to direct embedding without LLM
            logger.warning(
                "hyde_security_fallback",
                reason="prompt_injection_detected",
                query_preview=query[:50],
            )
            return query

        # Use sanitized query in prompt
        prompt = HYDE_PROMPT_TEMPLATE.format(query=sanitized_query)

        try:
            # Use structured output for consistent parsing
            llm_with_structure = self.llm.with_structured_output(HypotheticalDocument)

            # Wrap with timeout to prevent indefinite hangs
            async with asyncio.timeout(HYDE_TIMEOUT_SECONDS):
                raw_result = await llm_with_structure.ainvoke(prompt)

            result = cast("HypotheticalDocument", raw_result)
            return result.document

        except TimeoutError:
            logger.warning(
                "hyde_generation_timeout",
                timeout_seconds=HYDE_TIMEOUT_SECONDS,
                query=query[:100],
            )
            # Fallback: return original query for direct embedding
            return query

        except LLM_ERRORS as e:
            logger.warning(
                "hyde_generation_failed",
                error=str(e),
                query=query[:100],
            )
            # Fallback: return original query for direct embedding
            return query


# -----------------------------------------------------------------------------
# HyDE Cache
# -----------------------------------------------------------------------------


class HyDECache:
    """Two-tier cache for HyDE hypothetical documents.

    L1: In-memory dict with TTL for exact query matches
    L2: Redis semantic cache for similar queries (future enhancement)

    Similar to DecompositionCache but caches generated documents
    rather than extracted concepts.

    """

    def __init__(
        self,
        l1_maxsize: int = HYDE_CACHE_L1_SIZE,
        l1_ttl: int = HYDE_CACHE_L1_TTL,
    ) -> None:
        """Initialize HyDE cache.

        Args:
            l1_maxsize: Maximum L1 cache entries
            l1_ttl: L1 TTL in seconds

        """
        self.l1_maxsize = l1_maxsize
        self.l1_ttl = l1_ttl
        self.last_hit_tier: Literal["l1", "l2", "miss"] = "miss"

        # L1: Simple dict with timestamps
        self._l1_cache: dict[str, tuple[str, float]] = {}

        logger.debug(
            "hyde_cache_initialized",
            l1_maxsize=l1_maxsize,
            l1_ttl=l1_ttl,
        )

    def _normalize_query(self, query: str) -> str:
        """Normalize query for cache key generation."""
        return query.strip().lower()

    def _cache_key(self, query: str) -> str:
        """Generate cache key from normalized query."""
        normalized = self._normalize_query(query)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    async def get(self, query: str) -> str | None:
        """Look up hypothetical document in cache.

        Args:
            query: The original query

        Returns:
            Cached hypothetical document or None if not found

        """
        cache_key = self._cache_key(query)
        current_time = time.time()

        # Check L1
        if cache_key in self._l1_cache:
            doc, timestamp = self._l1_cache[cache_key]
            if current_time - timestamp < self.l1_ttl:
                self.last_hit_tier = "l1"
                return doc
            # Expired, remove it
            del self._l1_cache[cache_key]

        # L2 semantic cache would go here (Redis)
        # For now, just return None
        self.last_hit_tier = "miss"
        return None

    async def set(self, query: str, hypothetical_doc: str) -> None:
        """Store hypothetical document in cache.

        Args:
            query: The original query
            hypothetical_doc: Generated hypothetical document to cache

        """
        cache_key = self._cache_key(query)
        current_time = time.time()

        # Store in L1
        self._l1_cache[cache_key] = (hypothetical_doc, current_time)

        # Evict oldest entries if over capacity
        if len(self._l1_cache) > self.l1_maxsize:
            # Simple eviction: remove oldest 10%
            sorted_keys = sorted(
                self._l1_cache.keys(),
                key=lambda k: self._l1_cache[k][1],
            )
            for key in sorted_keys[: self.l1_maxsize // 10]:
                del self._l1_cache[key]

        # L2 Redis storage would go here
        logger.debug(
            "hyde_doc_cached",
            cache_key=cache_key,
            doc_length=len(hypothetical_doc),
        )

    def clear(self) -> None:
        """Clear all cached entries."""
        self._l1_cache.clear()
        logger.info("hyde_cache_cleared")
