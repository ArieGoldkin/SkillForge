"""Unit tests for HyDEService and HyDECache.

Issue #602: HyDE for Vocabulary Mismatch Resolution
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.shared.services.search.hyde import (
    HYDE_CACHE_L1_SIZE,
    HYDE_CACHE_L1_TTL,
    BatchHyDEResult,
    HyDECache,
    HyDEResult,
    HyDEService,
    HyDESource,
    HypotheticalDocument,
)


@pytest.mark.unit
class TestHyDECache:
    """Tests for the HyDECache class."""

    @pytest.mark.asyncio
    async def test_l1_cache_hit(self):
        """Test L1 in-memory cache returns cached hypothetical document."""
        cache = HyDECache(l1_maxsize=100, l1_ttl=300)

        query = "scaling async data pipelines"
        doc = "To scale asynchronous data pipelines, use event-driven messaging..."

        # Store in cache
        await cache.set(query, doc)

        # Retrieve from cache
        result = await cache.get(query)

        assert result == doc
        assert cache.last_hit_tier == "l1"

    @pytest.mark.asyncio
    async def test_l1_cache_miss(self):
        """Test L1 cache miss returns None."""
        cache = HyDECache()

        result = await cache.get("nonexistent query")

        assert result is None
        assert cache.last_hit_tier == "miss"

    @pytest.mark.asyncio
    async def test_cache_key_normalization(self):
        """Test that cache keys are normalized (case-insensitive)."""
        cache = HyDECache()

        doc = "This is a hypothetical document..."
        await cache.set("Scaling Async Pipelines", doc)

        # Should find with different casing
        result = await cache.get("scaling async pipelines")

        assert result == doc

    @pytest.mark.asyncio
    async def test_cache_key_whitespace_normalization(self):
        """Test that cache keys are normalized (whitespace)."""
        cache = HyDECache()

        doc = "Hypothetical document content"
        await cache.set("  query with spaces  ", doc)

        # Should find with trimmed whitespace
        result = await cache.get("query with spaces")

        assert result == doc

    @pytest.mark.asyncio
    async def test_cache_eviction(self):
        """Test that cache evicts oldest entries when full."""
        # Small cache for testing eviction
        cache = HyDECache(l1_maxsize=10, l1_ttl=300)

        # Fill cache beyond capacity
        for i in range(15):
            await cache.set(f"query {i}", f"document {i}")

        # After exceeding 10, eviction removes 10% (1 entry)
        # So we should have at most 14 entries
        assert len(cache._l1_cache) <= 14

    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """Test that expired entries are not returned."""
        # Very short TTL for testing
        cache = HyDECache(l1_maxsize=100, l1_ttl=0)

        await cache.set("query", "document")

        # Entry should be expired immediately
        result = await cache.get("query")

        assert result is None

    def test_clear_cache(self):
        """Test that clear() removes all entries."""
        cache = HyDECache()
        cache._l1_cache["key1"] = ("doc1", 12345.0)
        cache._l1_cache["key2"] = ("doc2", 12346.0)

        cache.clear()

        assert len(cache._l1_cache) == 0

    def test_default_config_values(self):
        """Test that default config values are applied."""
        cache = HyDECache()

        assert cache.l1_maxsize == HYDE_CACHE_L1_SIZE
        assert cache.l1_ttl == HYDE_CACHE_L1_TTL


@pytest.mark.unit
class TestHyDEService:
    """Tests for the HyDEService class."""

    @pytest.fixture
    def mock_embedding_service(self):
        """Create a mock embedding service."""
        service = MagicMock()
        service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        return service

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM for HyDE generation."""
        llm = MagicMock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.return_value = HypotheticalDocument(
            document="To scale asynchronous data pipelines, use event-driven messaging "
            "with Apache Kafka. Message brokers provide reliable..."
        )
        llm.with_structured_output.return_value = structured_llm
        return llm

    @pytest.mark.asyncio
    async def test_generate_llm_success(self, mock_embedding_service, mock_llm):
        """Test successful HyDE generation via LLM."""
        hyde = HyDEService(
            embedding_service=mock_embedding_service,
            llm=mock_llm,
        )

        result = await hyde.generate("scaling async data pipelines")

        assert result.original_query == "scaling async data pipelines"
        assert result.source == HyDESource.LLM
        assert len(result.hypothetical_doc) > 50
        assert "event-driven" in result.hypothetical_doc
        assert len(result.embedding) == 1536
        mock_llm.with_structured_output.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_cache_hit(self, mock_embedding_service, mock_llm):
        """Test HyDE generation returns cached document."""
        cache = HyDECache()
        cached_doc = "Cached hypothetical document about pipelines..."
        await cache.set("scaling async data pipelines", cached_doc)

        hyde = HyDEService(
            embedding_service=mock_embedding_service,
            llm=mock_llm,
            cache=cache,
        )

        result = await hyde.generate("scaling async data pipelines")

        assert result.source == HyDESource.CACHE_L1
        assert result.hypothetical_doc == cached_doc
        # LLM should NOT be called when cache hits
        mock_llm.with_structured_output.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_caches_result(self, mock_embedding_service, mock_llm):
        """Test that generated documents are cached."""
        cache = HyDECache()
        hyde = HyDEService(
            embedding_service=mock_embedding_service,
            llm=mock_llm,
            cache=cache,
        )

        await hyde.generate("scaling async data pipelines")

        # Verify document was cached
        cached = await cache.get("scaling async data pipelines")
        assert cached is not None
        assert "event-driven" in cached

    @pytest.mark.asyncio
    async def test_generate_llm_failure_fallback(self, mock_embedding_service):
        """Test fallback to original query when LLM fails."""
        mock_llm = MagicMock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.side_effect = ValueError("LLM error")
        mock_llm.with_structured_output.return_value = structured_llm

        hyde = HyDEService(
            embedding_service=mock_embedding_service,
            llm=mock_llm,
        )

        result = await hyde.generate("scaling async pipelines")

        # Should fall back to original query
        assert result.hypothetical_doc == "scaling async pipelines"
        assert result.source == HyDESource.FALLBACK
        # Embedding should still be generated
        assert len(result.embedding) == 1536

    @pytest.mark.asyncio
    async def test_generate_timeout_fallback(self, mock_embedding_service):
        """Test fallback to original query when LLM times out."""
        mock_llm = MagicMock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.side_effect = TimeoutError("LLM timeout")
        mock_llm.with_structured_output.return_value = structured_llm

        hyde = HyDEService(
            embedding_service=mock_embedding_service,
            llm=mock_llm,
        )

        result = await hyde.generate("scaling async pipelines")

        # Should fall back to original query
        assert result.hypothetical_doc == "scaling async pipelines"
        assert result.source == HyDESource.FALLBACK

    @pytest.mark.asyncio
    async def test_generate_fallback_not_cached(self, mock_embedding_service):
        """Test that fallback results are not cached."""
        mock_llm = MagicMock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.side_effect = ValueError("LLM error")
        mock_llm.with_structured_output.return_value = structured_llm

        cache = HyDECache()
        hyde = HyDEService(
            embedding_service=mock_embedding_service,
            llm=mock_llm,
            cache=cache,
        )

        await hyde.generate("test query")

        # Fallback results should NOT be cached
        cached = await cache.get("test query")
        assert cached is None

    # -------------------------------------------------------------------------
    # Lazy-loading property tests
    # -------------------------------------------------------------------------

    def test_llm_property_lazy_loading(self, mock_embedding_service):
        """Test that LLM is not instantiated until accessed."""
        hyde = HyDEService(embedding_service=mock_embedding_service)

        # Private attribute should be None before access
        assert hyde._llm is None

        # Accessing the property should trigger lazy loading
        llm = hyde.llm

        # Should now be set
        assert llm is not None
        assert hyde._llm is not None

    def test_llm_property_returns_same_instance(self, mock_embedding_service):
        """Test that LLM property returns the same instance on subsequent access."""
        hyde = HyDEService(embedding_service=mock_embedding_service)

        llm1 = hyde.llm
        llm2 = hyde.llm

        # Should be the exact same instance
        assert llm1 is llm2

    def test_llm_property_respects_constructor_override(self, mock_embedding_service, mock_llm):
        """Test that constructor-provided LLM is used instead of lazy loading."""
        hyde = HyDEService(
            embedding_service=mock_embedding_service,
            llm=mock_llm,
        )

        # Should use the provided LLM
        assert hyde.llm is mock_llm
        assert hyde._llm is mock_llm

    def test_cache_property_lazy_loading(self, mock_embedding_service):
        """Test that cache is not instantiated until accessed."""
        hyde = HyDEService(embedding_service=mock_embedding_service)

        # Private attribute should be None before access
        assert hyde._cache is None

        # Accessing the property should trigger lazy loading
        cache = hyde.cache

        # Should now be set
        assert cache is not None
        assert hyde._cache is not None
        assert isinstance(cache, HyDECache)

    def test_cache_property_respects_constructor_override(self, mock_embedding_service):
        """Test that constructor-provided cache is used instead of lazy loading."""
        mock_cache = HyDECache()
        hyde = HyDEService(
            embedding_service=mock_embedding_service,
            cache=mock_cache,
        )

        # Should use the provided cache
        assert hyde.cache is mock_cache
        assert hyde._cache is mock_cache


@pytest.mark.unit
class TestBatchHyDEGeneration:
    """Tests for the generate_batch method."""

    @pytest.fixture
    def mock_embedding_service(self):
        """Create a mock embedding service."""
        service = MagicMock()
        service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        return service

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM that generates different docs for different queries."""
        llm = MagicMock()
        structured_llm = AsyncMock()

        async def generate_doc(prompt: str):
            if "scaling" in prompt.lower():
                return HypotheticalDocument(
                    document="Scaling systems requires horizontal and vertical strategies..."
                )
            if "async" in prompt.lower():
                return HypotheticalDocument(
                    document="Async patterns include event-driven messaging..."
                )
            return HypotheticalDocument(document="General technical documentation...")

        structured_llm.ainvoke = generate_doc
        llm.with_structured_output.return_value = structured_llm
        return llm

    @pytest.mark.asyncio
    async def test_generate_batch_empty_list(self, mock_embedding_service, mock_llm):
        """Test batch generation with empty concepts list."""
        hyde = HyDEService(
            embedding_service=mock_embedding_service,
            llm=mock_llm,
        )

        result = await hyde.generate_batch([])

        assert result.results == []
        assert result.total_latency_ms >= 0
        assert result.cache_hits == 0
        assert result.llm_calls == 0

    @pytest.mark.asyncio
    async def test_generate_batch_multiple_concepts(self, mock_embedding_service, mock_llm):
        """Test batch generation with multiple concepts."""
        hyde = HyDEService(
            embedding_service=mock_embedding_service,
            llm=mock_llm,
        )

        concepts = ["scaling distributed systems", "async patterns"]
        result = await hyde.generate_batch(concepts)

        assert len(result.results) == 2
        assert result.llm_calls == 2
        assert result.cache_hits == 0
        assert all(r.source == HyDESource.LLM for r in result.results)

    @pytest.mark.asyncio
    async def test_generate_batch_with_cache_hits(self, mock_embedding_service, mock_llm):
        """Test batch generation with some cache hits."""
        cache = HyDECache()
        await cache.set("scaling distributed systems", "Cached scaling doc...")

        hyde = HyDEService(
            embedding_service=mock_embedding_service,
            llm=mock_llm,
            cache=cache,
        )

        concepts = ["scaling distributed systems", "async patterns"]
        result = await hyde.generate_batch(concepts)

        assert len(result.results) == 2
        assert result.cache_hits == 1
        assert result.llm_calls == 1

    @pytest.mark.asyncio
    async def test_generate_batch_parallel_execution(self, mock_embedding_service, mock_llm):
        """Test that batch generation executes in parallel."""
        import asyncio

        call_times = []

        async def track_time(*args, **kwargs):
            call_times.append(asyncio.get_event_loop().time())
            await asyncio.sleep(0.01)  # Small delay to make timing measurable
            return HypotheticalDocument(document="Test document...")

        mock_llm.with_structured_output.return_value.ainvoke = track_time

        hyde = HyDEService(
            embedding_service=mock_embedding_service,
            llm=mock_llm,
        )

        concepts = ["concept1", "concept2", "concept3"]
        await hyde.generate_batch(concepts)

        # All calls should start at approximately the same time (parallel)
        # The time difference between first and last should be small
        if len(call_times) >= 2:
            time_spread = max(call_times) - min(call_times)
            # If sequential, spread would be > 0.02s (2 x 0.01s delays)
            # If parallel, spread should be < 0.01s
            assert time_spread < 0.02


@pytest.mark.unit
class TestHyDEResult:
    """Tests for HyDEResult Pydantic model."""

    def test_valid_result(self):
        """Test creating a valid HyDE result."""
        result = HyDEResult(
            original_query="test query",
            hypothetical_doc="This is a hypothetical document...",
            embedding=[0.1] * 1536,
            source=HyDESource.LLM,
            latency_ms=150.5,
        )

        assert result.original_query == "test query"
        assert len(result.hypothetical_doc) > 0
        assert len(result.embedding) == 1536
        assert result.source == HyDESource.LLM
        assert result.latency_ms == 150.5

    def test_fallback_result(self):
        """Test creating a fallback result."""
        result = HyDEResult(
            original_query="test query",
            hypothetical_doc="test query",  # Same as original on fallback
            embedding=[0.1] * 1536,
            source=HyDESource.FALLBACK,
            latency_ms=5.0,
        )

        assert result.source == HyDESource.FALLBACK
        assert result.original_query == result.hypothetical_doc


@pytest.mark.unit
class TestBatchHyDEResult:
    """Tests for BatchHyDEResult Pydantic model."""

    def test_valid_batch_result(self):
        """Test creating a valid batch result."""
        individual_results = [
            HyDEResult(
                original_query=f"query{i}",
                hypothetical_doc=f"doc{i}",
                embedding=[0.1] * 1536,
                source=HyDESource.LLM,
                latency_ms=100.0,
            )
            for i in range(3)
        ]

        batch = BatchHyDEResult(
            results=individual_results,
            total_latency_ms=150.0,
            cache_hits=1,
            llm_calls=2,
        )

        assert len(batch.results) == 3
        assert batch.total_latency_ms == 150.0
        assert batch.cache_hits == 1
        assert batch.llm_calls == 2


@pytest.mark.unit
class TestHypotheticalDocument:
    """Tests for HypotheticalDocument Pydantic model."""

    def test_valid_document(self):
        """Test creating a valid hypothetical document."""
        doc = HypotheticalDocument(
            document="This is a detailed hypothetical document that explains the topic."
        )

        assert len(doc.document) >= 20

    def test_document_too_short(self):
        """Test that very short documents are rejected."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            HypotheticalDocument(document="Too short")

    def test_document_max_length(self):
        """Test that document respects max length."""
        # Should accept document at max length (1000 chars)
        long_doc = "a" * 1000
        doc = HypotheticalDocument(document=long_doc)
        assert len(doc.document) == 1000

        # Should reject document over max length
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            HypotheticalDocument(document="a" * 1001)
