# Issue #601: Query Decomposition Testing Strategy

**Version:** 1.0  
**Date:** December 29, 2025  
**Status:** Design Complete  
**Author:** Code Quality Reviewer

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Feature Overview](#feature-overview)
3. [Testing Pyramid](#testing-pyramid)
4. [Unit Tests](#unit-tests)
5. [Integration Tests](#integration-tests)
6. [Evaluation Tests](#evaluation-tests)
7. [Test Fixtures & Mocking](#test-fixtures--mocking)
8. [Implementation Plan](#implementation-plan)
9. [Acceptance Criteria](#acceptance-criteria)

---

## Executive Summary

### Purpose
Design comprehensive testing strategy for query decomposition pipeline (Issue #601) that validates:
- Multi-concept query detection (heuristic + LLM)
- Concept extraction quality (2-4 independent concepts)
- Parallel retrieval correctness
- RRF fusion ranking
- End-to-end improvement on 40 failing multi-concept queries

### Testing Approach
**Pyramid Structure:**
```
         /\
        /E2\     Evaluation Tests (10 queries, real system)
       /----\
      / Int  \   Integration Tests (5 scenarios, mocked LLM)
     /--------\
    /   Unit   \ Unit Tests (30+ cases, pure functions)
   /------------\
```

### Key Metrics
- **Unit Test Coverage:** 95%+ for query analyzer, RRF fusion, cache logic
- **Integration Test Coverage:** 80%+ for full pipeline with mocked LLM
- **Evaluation Baseline:** Recall@5 improvement ≥15% on multi-concept queries
- **Regression Protection:** Zero degradation on existing single-concept queries

---

## Feature Overview

### Query Decomposition Pipeline

```
┌──────────────────────────────────────────────────────────────┐
│                    User Query                                 │
│              "React hooks and state management"               │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     v
┌──────────────────────────────────────────────────────────────┐
│  STEP 1: Query Analyzer (Heuristic + LLM)                    │
│  - Heuristic: "and", "vs", "versus" patterns                 │
│  - LLM: Structured output with ConceptList Pydantic schema   │
│  Output: is_multi_concept = True                             │
│          concepts = ["React hooks", "state management"]      │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     v
┌──────────────────────────────────────────────────────────────┐
│  STEP 2: Parallel Retrieval (asyncio.gather)                 │
│  - Concept 1: search("React hooks") → [chunk_a, chunk_b]     │
│  - Concept 2: search("state management") → [chunk_c, chunk_d]│
└────────────────────┬─────────────────────────────────────────┘
                     │
                     v
┌──────────────────────────────────────────────────────────────┐
│  STEP 3: RRF Fusion                                           │
│  - Merge results using Reciprocal Rank Fusion (k=60)         │
│  - Final ranking: [chunk_a, chunk_c, chunk_b, chunk_d]       │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     v
┌──────────────────────────────────────────────────────────────┐
│  STEP 4: Cache & Return                                       │
│  - Cache key: SHA256(original_query + "decomposed")          │
│  - Return top_k results with metadata                        │
└──────────────────────────────────────────────────────────────┘
```

### Design Decisions
1. **Heuristic First:** Fast path for obvious multi-concept queries (< 1ms)
2. **LLM Fallback:** Structured output with Pydantic validation (200-500ms)
3. **Parallel Retrieval:** asyncio.gather for 2-4x speedup
4. **RRF Fusion:** Standard algorithm (k=60) from test_hybrid_fusion.py
5. **Cache Strategy:** Separate cache entries for decomposed vs original queries

---

## Testing Pyramid

### Layer 1: Unit Tests (30+ tests, <1s runtime)

**Coverage:**
- Query analyzer heuristics (pattern matching)
- LLM response parsing (Pydantic validation)
- RRF fusion algorithm (ranking correctness)
- Cache key generation (SHA256 determinism)
- Concept extraction edge cases

**Test Files:**
```
backend/tests/unit/services/search/
├── test_query_analyzer.py            (15 tests)
├── test_concept_extraction.py        (10 tests)
├── test_decomposition_cache.py       (5 tests)
└── test_rrf_fusion_extended.py       (5 tests - extend existing)
```

### Layer 2: Integration Tests (5 scenarios, <5s runtime)

**Coverage:**
- Full decomposition pipeline with mocked LLM
- Multi-concept retrieval vs single-concept retrieval
- Fallback when LLM fails/times out
- Parallel retrieval correctness
- Cache hit/miss scenarios

**Test Files:**
```
backend/tests/integration/services/search/
├── test_decomposition_pipeline.py    (3 tests)
└── test_decomposition_fallback.py    (2 tests)
```

### Layer 3: Evaluation Tests (10 queries, <30s runtime)

**Coverage:**
- Before/after comparison on 40 failing multi-concept queries (sample 10)
- Regression check on 20 passing single-concept queries (sample 5)
- Metrics: Recall@5, MRR, NDCG@10, P@1

**Test Files:**
```
backend/tests/smoke/retrieval/
└── test_decomposition_eval.py        (1 test with 10 queries)
```

---

## Unit Tests

### 1. Query Analyzer Heuristics

**File:** `backend/tests/unit/services/search/test_query_analyzer.py`

```python
"""Unit tests for query decomposition analyzer."""

import pytest
from app.shared.services.search.query_analyzer import QueryAnalyzer


@pytest.mark.unit
class TestHeuristicDetection:
    """Tests for heuristic-based multi-concept detection."""

    @pytest.fixture
    def analyzer(self):
        """Create QueryAnalyzer without LLM dependency."""
        return QueryAnalyzer(enable_llm=False)

    def test_detect_multi_concept_with_and(self, analyzer):
        """Query with 'and' should be detected as multi-concept."""
        query = "React hooks and state management"
        result = analyzer.detect_multi_concept(query)
        
        assert result.is_multi_concept is True
        assert result.confidence >= 0.8
        assert result.detection_method == "heuristic"

    def test_detect_multi_concept_with_vs(self, analyzer):
        """Query with 'vs' should be detected as multi-concept."""
        query = "PostgreSQL vs MySQL performance"
        result = analyzer.detect_multi_concept(query)
        
        assert result.is_multi_concept is True
        assert result.confidence >= 0.8
        assert "vs" in result.patterns_matched

    def test_detect_multi_concept_with_versus(self, analyzer):
        """Query with 'versus' should be detected as multi-concept."""
        query = "React versus Vue framework comparison"
        result = analyzer.detect_multi_concept(query)
        
        assert result.is_multi_concept is True
        assert "versus" in result.patterns_matched

    def test_single_concept_query(self, analyzer):
        """Single concept query should not trigger heuristic."""
        query = "How to use React hooks"
        result = analyzer.detect_multi_concept(query)
        
        assert result.is_multi_concept is False
        assert result.confidence < 0.5

    def test_empty_query(self, analyzer):
        """Empty query should return False."""
        query = ""
        result = analyzer.detect_multi_concept(query)
        
        assert result.is_multi_concept is False
        assert result.confidence == 0.0

    def test_heuristic_with_common_words(self, analyzer):
        """Query with 'and' in common phrases should not trigger."""
        query = "command and control patterns"  # Not multi-concept
        result = analyzer.detect_multi_concept(query)
        
        # Should require additional signals beyond just 'and'
        assert result.confidence < 0.9  # Lower confidence

    def test_multiple_separators(self, analyzer):
        """Query with multiple separators should boost confidence."""
        query = "React vs Vue and Angular comparison"
        result = analyzer.detect_multi_concept(query)
        
        assert result.is_multi_concept is True
        assert result.confidence >= 0.9
        assert len(result.patterns_matched) >= 2

    def test_case_insensitive_detection(self, analyzer):
        """Pattern detection should be case insensitive."""
        query = "React AND State Management"
        result = analyzer.detect_multi_concept(query)
        
        assert result.is_multi_concept is True

    def test_special_characters_handling(self, analyzer):
        """Query with special chars should not break detection."""
        query = "OAuth2 vs. JWT (authentication tokens)"
        result = analyzer.detect_multi_concept(query)
        
        assert result.is_multi_concept is True

    def test_long_query_with_multiple_concepts(self, analyzer):
        """Long query with clear concepts should be detected."""
        query = "How to implement React hooks for state management and side effects in Next.js applications"
        result = analyzer.detect_multi_concept(query)
        
        assert result.is_multi_concept is True


@pytest.mark.unit
class TestConceptExtraction:
    """Tests for concept extraction from multi-concept queries."""

    @pytest.fixture
    def analyzer(self):
        return QueryAnalyzer(enable_llm=False)

    def test_extract_concepts_with_and(self, analyzer):
        """Extract concepts separated by 'and'."""
        query = "React hooks and state management"
        concepts = analyzer.extract_concepts_heuristic(query)
        
        assert len(concepts) == 2
        assert "React hooks" in concepts
        assert "state management" in concepts

    def test_extract_concepts_with_vs(self, analyzer):
        """Extract concepts separated by 'vs'."""
        query = "PostgreSQL vs MySQL"
        concepts = analyzer.extract_concepts_heuristic(query)
        
        assert len(concepts) == 2
        assert "PostgreSQL" in concepts
        assert "MySQL" in concepts

    def test_extract_concepts_cleans_extra_whitespace(self, analyzer):
        """Extracted concepts should be trimmed."""
        query = "React   and    Vue"
        concepts = analyzer.extract_concepts_heuristic(query)
        
        assert concepts == ["React", "Vue"]
        assert "   " not in concepts[0]

    def test_extract_concepts_removes_duplicates(self, analyzer):
        """Duplicate concepts should be deduplicated."""
        query = "React vs Vue and React frameworks"
        concepts = analyzer.extract_concepts_heuristic(query)
        
        # Should only include "React" once
        assert len([c for c in concepts if "React" in c]) == 1

    def test_extract_concepts_max_4_concepts(self, analyzer):
        """Should limit to 4 concepts max."""
        query = "A and B vs C and D and E and F"
        concepts = analyzer.extract_concepts_heuristic(query)
        
        assert len(concepts) <= 4


### 2. LLM-based Concept Extraction

**File:** `backend/tests/unit/services/search/test_concept_extraction.py`

```python
"""Unit tests for LLM-based concept extraction."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from pydantic import BaseModel

from app.shared.services.search.query_analyzer import QueryAnalyzer, ConceptList


class TestLLMConceptExtraction:
    """Tests for LLM-based concept extraction with mocked LLM."""

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM that returns structured ConceptList."""
        llm = AsyncMock()
        # Mock ainvoke to return ConceptList Pydantic model
        llm.ainvoke = AsyncMock()
        return llm

    @pytest.fixture
    def analyzer(self, mock_llm):
        """Create QueryAnalyzer with mocked LLM."""
        analyzer = QueryAnalyzer(enable_llm=True)
        analyzer.llm = mock_llm
        return analyzer

    @pytest.mark.asyncio
    async def test_llm_extracts_two_concepts(self, analyzer, mock_llm):
        """LLM should extract 2 concepts from multi-concept query."""
        query = "How React hooks differ from class components"
        
        # Mock LLM response
        mock_llm.ainvoke.return_value = ConceptList(
            concepts=["React hooks", "class components"],
            is_multi_concept=True,
            confidence=0.9
        )
        
        result = await analyzer.extract_concepts_llm(query)
        
        assert result.is_multi_concept is True
        assert len(result.concepts) == 2
        assert "React hooks" in result.concepts
        assert "class components" in result.concepts
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_llm_handles_single_concept(self, analyzer, mock_llm):
        """LLM should detect single-concept queries."""
        query = "How to use React hooks"
        
        mock_llm.ainvoke.return_value = ConceptList(
            concepts=["React hooks"],
            is_multi_concept=False,
            confidence=0.3
        )
        
        result = await analyzer.extract_concepts_llm(query)
        
        assert result.is_multi_concept is False
        assert len(result.concepts) == 1

    @pytest.mark.asyncio
    async def test_llm_timeout_fallback(self, analyzer, mock_llm):
        """LLM timeout should fallback to heuristic extraction."""
        query = "React vs Vue"
        
        # Simulate timeout
        import asyncio
        mock_llm.ainvoke.side_effect = asyncio.TimeoutError()
        
        result = await analyzer.extract_concepts_llm(query, fallback_heuristic=True)
        
        # Should fallback to heuristic
        assert result.is_multi_concept is True
        assert len(result.concepts) == 2
        assert result.detection_method == "heuristic_fallback"

    @pytest.mark.asyncio
    async def test_llm_validation_error_fallback(self, analyzer, mock_llm):
        """LLM invalid response should fallback to heuristic."""
        query = "React and Vue"
        
        from pydantic import ValidationError
        mock_llm.ainvoke.side_effect = ValidationError.from_exception_data(
            "Invalid", [{"type": "missing", "loc": ("concepts",), "msg": "Field required"}]
        )
        
        result = await analyzer.extract_concepts_llm(query, fallback_heuristic=True)
        
        assert result.detection_method == "heuristic_fallback"

    @pytest.mark.asyncio
    async def test_llm_caching(self, analyzer, mock_llm):
        """LLM results should be cached by query hash."""
        query = "React hooks and state management"
        
        mock_llm.ainvoke.return_value = ConceptList(
            concepts=["React hooks", "state management"],
            is_multi_concept=True,
            confidence=0.9
        )
        
        # First call
        result1 = await analyzer.extract_concepts_llm(query)
        # Second call (should hit cache)
        result2 = await analyzer.extract_concepts_llm(query)
        
        # LLM should only be called once
        assert mock_llm.ainvoke.call_count == 1
        assert result1.concepts == result2.concepts

    @pytest.mark.asyncio
    async def test_llm_prompt_structure(self, analyzer, mock_llm):
        """LLM should receive properly structured prompt."""
        query = "React vs Vue frameworks"
        
        mock_llm.ainvoke.return_value = ConceptList(
            concepts=["React", "Vue"],
            is_multi_concept=True,
            confidence=0.9
        )
        
        await analyzer.extract_concepts_llm(query)
        
        # Verify prompt includes query and instructions
        call_args = mock_llm.ainvoke.call_args
        prompt = call_args[0][0]  # First positional argument
        
        assert query in str(prompt)
        assert "extract" in str(prompt).lower()
        assert "independent concepts" in str(prompt).lower()

    @pytest.mark.asyncio
    async def test_llm_max_4_concepts_enforced(self, analyzer, mock_llm):
        """LLM should return max 4 concepts even if it tries to return more."""
        query = "Compare A, B, C, D, E frameworks"
        
        # LLM tries to return 5 concepts
        mock_llm.ainvoke.return_value = ConceptList(
            concepts=["A", "B", "C", "D", "E"],
            is_multi_concept=True,
            confidence=0.8
        )
        
        result = await analyzer.extract_concepts_llm(query)
        
        # Should be truncated to 4
        assert len(result.concepts) <= 4


### 3. RRF Fusion Extended Tests

**File:** `backend/tests/unit/services/search/test_rrf_fusion_extended.py`

```python
"""Extended tests for RRF fusion with decomposed queries."""

import pytest
from app.shared.services.search.hybrid_fusion import reciprocal_rank_fusion


@pytest.mark.unit
class TestRRFWithDecomposedQueries:
    """Tests for RRF fusion specific to decomposed query scenarios."""

    def test_fusion_two_concept_results(self):
        """Fuse results from 2 concept-specific searches."""
        concept1_results = [("chunk_a", 0.95), ("chunk_b", 0.85)]
        concept2_results = [("chunk_c", 0.92), ("chunk_d", 0.80)]
        
        fused = reciprocal_rank_fusion([concept1_results, concept2_results])
        
        # All chunks should be present
        chunk_ids = {chunk_id for chunk_id, _ in fused}
        assert chunk_ids == {"chunk_a", "chunk_b", "chunk_c", "chunk_d"}

    def test_fusion_overlapping_chunks(self):
        """Chunks appearing in multiple concept results should rank higher."""
        concept1_results = [("chunk_shared", 0.90), ("chunk_a", 0.80)]
        concept2_results = [("chunk_shared", 0.85), ("chunk_b", 0.75)]
        
        fused = reciprocal_rank_fusion([concept1_results, concept2_results])
        
        # chunk_shared should be first (appears in both)
        assert fused[0][0] == "chunk_shared"

    def test_fusion_with_empty_concept_results(self):
        """Handle case where one concept returns no results."""
        concept1_results = [("chunk_a", 0.90), ("chunk_b", 0.80)]
        concept2_results = []  # No results
        
        fused = reciprocal_rank_fusion([concept1_results, concept2_results])
        
        # Should still return concept1 results
        assert len(fused) == 2
        assert fused[0][0] == "chunk_a"

    def test_fusion_four_concepts(self):
        """Fuse results from 4 concepts (max case)."""
        results = [
            [("chunk_1", 0.9)],
            [("chunk_2", 0.8)],
            [("chunk_3", 0.7)],
            [("chunk_4", 0.6)]
        ]
        
        fused = reciprocal_rank_fusion(results)
        
        assert len(fused) == 4

    def test_fusion_score_ordering(self):
        """Verify RRF scoring produces expected ordering."""
        concept1_results = [("chunk_a", 1.0), ("chunk_b", 0.9)]
        concept2_results = [("chunk_b", 1.0), ("chunk_c", 0.8)]
        
        fused = reciprocal_rank_fusion([concept1_results, concept2_results], k=60)
        
        # chunk_b appears in both at high ranks -> should be first
        # chunk_a: 1/(60+1) = 0.0164
        # chunk_b: 1/(60+1) + 1/(60+1) = 0.0328
        # chunk_c: 1/(60+2) = 0.0161
        assert fused[0][0] == "chunk_b"


### 4. Cache Key Generation Tests

**File:** `backend/tests/unit/services/search/test_decomposition_cache.py`

```python
"""Unit tests for decomposition cache key generation."""

import pytest
from hashlib import sha256

from app.shared.services.search.decomposition_cache import generate_cache_key


@pytest.mark.unit
class TestDecompositionCache:
    """Tests for cache key generation and collision avoidance."""

    def test_cache_key_deterministic(self):
        """Same query should produce same cache key."""
        query = "React hooks and state management"
        
        key1 = generate_cache_key(query, decomposed=True)
        key2 = generate_cache_key(query, decomposed=True)
        
        assert key1 == key2

    def test_cache_key_different_for_decomposed_vs_original(self):
        """Decomposed and original query should have different keys."""
        query = "React hooks and state management"
        
        key_decomposed = generate_cache_key(query, decomposed=True)
        key_original = generate_cache_key(query, decomposed=False)
        
        assert key_decomposed != key_original

    def test_cache_key_collision_resistance(self):
        """Similar queries should have different keys."""
        query1 = "React hooks and state"
        query2 = "React hooks and state management"
        
        key1 = generate_cache_key(query1, decomposed=True)
        key2 = generate_cache_key(query2, decomposed=True)
        
        assert key1 != key2

    def test_cache_key_sha256_format(self):
        """Cache key should be valid SHA256 hex string."""
        query = "test query"
        key = generate_cache_key(query, decomposed=True)
        
        # SHA256 hex is 64 chars
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    def test_cache_key_empty_query(self):
        """Empty query should still produce valid key."""
        query = ""
        key = generate_cache_key(query, decomposed=True)
        
        assert len(key) == 64


---

## Integration Tests

### 1. Full Decomposition Pipeline

**File:** `backend/tests/integration/services/search/test_decomposition_pipeline.py`

```python
"""Integration tests for full query decomposition pipeline."""

import pytest
from unittest.mock import AsyncMock, patch

from app.shared.services.search.decomposition_service import DecompositionService
from app.shared.services.search.query_analyzer import ConceptList


@pytest.mark.integration
class TestDecompositionPipeline:
    """End-to-end tests for query decomposition with mocked LLM."""

    @pytest.fixture
    async def mock_search_service(self):
        """Mock SearchService that returns concept-specific results."""
        search_service = AsyncMock()
        
        async def mock_search(query: str, **kwargs):
            # Return different results based on query
            if "React hooks" in query:
                return [("chunk_react_hooks_1", 0.95), ("chunk_react_hooks_2", 0.85)]
            elif "state management" in query:
                return [("chunk_state_mgmt_1", 0.92), ("chunk_state_mgmt_2", 0.80)]
            else:
                return [("chunk_generic_1", 0.70)]
        
        search_service.semantic_search = AsyncMock(side_effect=mock_search)
        return search_service

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM for concept extraction."""
        llm = AsyncMock()
        llm.ainvoke = AsyncMock(return_value=ConceptList(
            concepts=["React hooks", "state management"],
            is_multi_concept=True,
            confidence=0.9
        ))
        return llm

    @pytest.fixture
    async def decomposition_service(self, mock_search_service, mock_llm):
        """Create DecompositionService with mocked dependencies."""
        service = DecompositionService(
            search_service=mock_search_service,
            llm=mock_llm,
            enable_decomposition=True
        )
        return service

    @pytest.mark.asyncio
    async def test_multi_concept_query_decomposed(self, decomposition_service, mock_search_service):
        """Multi-concept query should trigger decomposition and parallel retrieval."""
        query = "React hooks and state management"
        
        results = await decomposition_service.search(query, top_k=10)
        
        # Should call search twice (once per concept)
        assert mock_search_service.semantic_search.call_count == 2
        
        # Results should contain chunks from both concepts
        result_ids = {chunk_id for chunk_id, _ in results}
        assert "chunk_react_hooks_1" in result_ids
        assert "chunk_state_mgmt_1" in result_ids

    @pytest.mark.asyncio
    async def test_single_concept_query_not_decomposed(self, decomposition_service, mock_search_service):
        """Single-concept query should NOT trigger decomposition."""
        with patch.object(decomposition_service.analyzer, 'detect_multi_concept') as mock_detect:
            mock_detect.return_value.is_multi_concept = False
            
            query = "How to use React hooks"
            results = await decomposition_service.search(query, top_k=10)
            
            # Should only call search once (original query)
            assert mock_search_service.semantic_search.call_count == 1

    @pytest.mark.asyncio
    async def test_parallel_retrieval_faster_than_sequential(self, decomposition_service):
        """Parallel retrieval should be faster than sequential."""
        import time
        from unittest.mock import AsyncMock
        
        # Mock search with artificial delay
        async def slow_search(query: str, **kwargs):
            await asyncio.sleep(0.1)  # 100ms delay
            return [("chunk", 0.9)]
        
        decomposition_service.search_service.semantic_search = AsyncMock(side_effect=slow_search)
        
        query = "React vs Vue"
        
        start = time.time()
        results = await decomposition_service.search(query, top_k=10)
        duration = time.time() - start
        
        # With parallel execution, should take ~100ms (not 200ms)
        assert duration < 0.15  # Allow 50ms overhead

    @pytest.mark.asyncio
    async def test_rrf_fusion_ordering(self, decomposition_service, mock_search_service):
        """RRF fusion should properly order results from multiple concepts."""
        # Set up mock to return overlapping results
        async def mock_search_with_overlap(query: str, **kwargs):
            if "React" in query:
                return [("chunk_shared", 0.90), ("chunk_react", 0.85)]
            else:
                return [("chunk_shared", 0.88), ("chunk_vue", 0.82)]
        
        mock_search_service.semantic_search = AsyncMock(side_effect=mock_search_with_overlap)
        
        query = "React vs Vue"
        results = await decomposition_service.search(query, top_k=10)
        
        # chunk_shared should be ranked highest (appears in both)
        assert results[0][0] == "chunk_shared"


### 2. Fallback Handling

**File:** `backend/tests/integration/services/search/test_decomposition_fallback.py`

```python
"""Integration tests for decomposition fallback scenarios."""

import pytest
from unittest.mock import AsyncMock, patch
import asyncio

from app.shared.services.search.decomposition_service import DecompositionService


@pytest.mark.integration
class TestDecompositionFallback:
    """Tests for fallback behavior when LLM fails."""

    @pytest.fixture
    async def search_service(self):
        """Mock search service."""
        service = AsyncMock()
        service.semantic_search = AsyncMock(return_value=[("chunk", 0.9)])
        return service

    @pytest.mark.asyncio
    async def test_llm_timeout_fallback_to_heuristic(self, search_service):
        """LLM timeout should fallback to heuristic extraction."""
        llm = AsyncMock()
        llm.ainvoke = AsyncMock(side_effect=asyncio.TimeoutError())
        
        service = DecompositionService(
            search_service=search_service,
            llm=llm,
            enable_decomposition=True
        )
        
        query = "React vs Vue"
        results = await service.search(query, top_k=10)
        
        # Should still decompose using heuristic
        # Search should be called twice (once per concept)
        assert search_service.semantic_search.call_count == 2

    @pytest.mark.asyncio
    async def test_llm_error_fallback_to_single_query(self, search_service):
        """Critical LLM error should fallback to single query search."""
        llm = AsyncMock()
        llm.ainvoke = AsyncMock(side_effect=Exception("LLM service unavailable"))
        
        service = DecompositionService(
            search_service=search_service,
            llm=llm,
            enable_decomposition=True,
            fallback_to_single_query=True  # Graceful degradation
        )
        
        query = "React vs Vue"
        results = await service.search(query, top_k=10)
        
        # Should fallback to single query (no decomposition)
        assert search_service.semantic_search.call_count == 1
        assert len(results) > 0  # Should still return results


---

## Evaluation Tests

### Before/After Comparison on Multi-Concept Queries

**File:** `backend/tests/smoke/retrieval/test_decomposition_eval.py`

```python
"""Evaluation tests for query decomposition impact on retrieval quality."""

import pytest
from typing import List, Tuple

from app.shared.services.search.search_service import SearchService
from app.shared.services.search.decomposition_service import DecompositionService
from tests.smoke.retrieval.fixtures import load_multi_concept_queries


@pytest.mark.smoke
@pytest.mark.evaluation
class TestDecompositionEvaluation:
    """Before/after evaluation of query decomposition on retrieval quality."""

    @pytest.fixture
    def multi_concept_queries(self) -> List[dict]:
        """Load 10 sample multi-concept queries from failing set."""
        return load_multi_concept_queries()[:10]  # Sample 10 from 40

    @pytest.fixture
    async def baseline_search(self, session, embedding_service):
        """Baseline SearchService without decomposition."""
        return SearchService(
            session=session,
            embedding_service=embedding_service,
            enable_decomposition=False
        )

    @pytest.fixture
    async def decomposition_search(self, session, embedding_service, llm):
        """DecompositionService with query decomposition enabled."""
        return DecompositionService(
            search_service=SearchService(session, embedding_service),
            llm=llm,
            enable_decomposition=True
        )

    @pytest.mark.asyncio
    async def test_recall_at_5_improvement(
        self,
        multi_concept_queries,
        baseline_search,
        decomposition_search
    ):
        """Query decomposition should improve Recall@5 by ≥15% on multi-concept queries."""
        baseline_scores = []
        decomposition_scores = []
        
        for query_data in multi_concept_queries:
            query = query_data["query"]
            expected_chunks = query_data["expected_chunks"]
            
            # Baseline results
            baseline_results = await baseline_search.semantic_search(query, top_k=5)
            baseline_recall = compute_recall_at_k(baseline_results, expected_chunks, k=5)
            baseline_scores.append(baseline_recall)
            
            # Decomposition results
            decomp_results = await decomposition_search.search(query, top_k=5)
            decomp_recall = compute_recall_at_k(decomp_results, expected_chunks, k=5)
            decomposition_scores.append(decomp_recall)
        
        # Compute mean scores
        baseline_mean = sum(baseline_scores) / len(baseline_scores)
        decomp_mean = sum(decomposition_scores) / len(decomposition_scores)
        
        # Improvement should be ≥15%
        improvement = (decomp_mean - baseline_mean) / baseline_mean if baseline_mean > 0 else 0
        
        print(f"\n=== Recall@5 Evaluation ===")
        print(f"Baseline mean:       {baseline_mean:.3f}")
        print(f"Decomposition mean:  {decomp_mean:.3f}")
        print(f"Improvement:         {improvement:.1%}")
        
        assert improvement >= 0.15, f"Expected ≥15% improvement, got {improvement:.1%}"

    @pytest.mark.asyncio
    async def test_mrr_improvement(
        self,
        multi_concept_queries,
        baseline_search,
        decomposition_search
    ):
        """Query decomposition should improve MRR (Mean Reciprocal Rank)."""
        baseline_mrr_scores = []
        decomposition_mrr_scores = []
        
        for query_data in multi_concept_queries:
            query = query_data["query"]
            expected_chunks = query_data["expected_chunks"]
            
            baseline_results = await baseline_search.semantic_search(query, top_k=10)
            baseline_mrr = compute_mrr(baseline_results, expected_chunks)
            baseline_mrr_scores.append(baseline_mrr)
            
            decomp_results = await decomposition_search.search(query, top_k=10)
            decomp_mrr = compute_mrr(decomp_results, expected_chunks)
            decomposition_mrr_scores.append(decomp_mrr)
        
        baseline_mean_mrr = sum(baseline_mrr_scores) / len(baseline_mrr_scores)
        decomp_mean_mrr = sum(decomposition_mrr_scores) / len(decomposition_mrr_scores)
        
        print(f"\n=== MRR Evaluation ===")
        print(f"Baseline MRR:       {baseline_mean_mrr:.3f}")
        print(f"Decomposition MRR:  {decomp_mean_mrr:.3f}")
        
        # MRR should improve
        assert decomp_mean_mrr > baseline_mean_mrr

    @pytest.mark.asyncio
    async def test_no_regression_on_single_concept_queries(
        self,
        baseline_search,
        decomposition_search
    ):
        """Decomposition should NOT degrade single-concept query performance."""
        single_concept_queries = [
            {"query": "How to use React hooks", "expected_chunks": ["chunk_react_hooks_guide"]},
            {"query": "PostgreSQL indexing best practices", "expected_chunks": ["chunk_pg_indexing"]},
            {"query": "LangGraph supervisor agent", "expected_chunks": ["chunk_langgraph_supervisor"]},
            {"query": "FastAPI async endpoints", "expected_chunks": ["chunk_fastapi_async"]},
            {"query": "OAuth2 token validation", "expected_chunks": ["chunk_oauth2_tokens"]},
        ]
        
        baseline_scores = []
        decomposition_scores = []
        
        for query_data in single_concept_queries:
            query = query_data["query"]
            expected = query_data["expected_chunks"]
            
            baseline_results = await baseline_search.semantic_search(query, top_k=5)
            baseline_recall = compute_recall_at_k(baseline_results, expected, k=5)
            baseline_scores.append(baseline_recall)
            
            decomp_results = await decomposition_search.search(query, top_k=5)
            decomp_recall = compute_recall_at_k(decomp_results, expected, k=5)
            decomposition_scores.append(decomp_recall)
        
        baseline_mean = sum(baseline_scores) / len(baseline_scores)
        decomp_mean = sum(decomposition_scores) / len(decomposition_scores)
        
        print(f"\n=== Regression Check (Single-Concept Queries) ===")
        print(f"Baseline mean:       {baseline_mean:.3f}")
        print(f"Decomposition mean:  {decomp_mean:.3f}")
        print(f"Difference:          {decomp_mean - baseline_mean:.3f}")
        
        # Allow up to 2% degradation (within measurement noise)
        degradation = (baseline_mean - decomp_mean) / baseline_mean if baseline_mean > 0 else 0
        assert degradation <= 0.02, f"Unexpected degradation: {degradation:.1%}"


# Helper functions for metrics
def compute_recall_at_k(
    results: List[Tuple[str, float]],
    expected_chunks: List[str],
    k: int = 5
) -> float:
    """Compute Recall@k: fraction of expected chunks found in top-k."""
    top_k_ids = {chunk_id for chunk_id, _ in results[:k]}
    expected_set = set(expected_chunks)
    
    if not expected_set:
        return 0.0
    
    hits = len(top_k_ids & expected_set)
    return hits / len(expected_set)


def compute_mrr(
    results: List[Tuple[str, float]],
    expected_chunks: List[str]
) -> float:
    """Compute Mean Reciprocal Rank (MRR)."""
    expected_set = set(expected_chunks)
    
    for rank, (chunk_id, _) in enumerate(results, start=1):
        if chunk_id in expected_set:
            return 1.0 / rank
    
    return 0.0
```

---

## Test Fixtures & Mocking

### LLM Mocking Strategy

**Pattern:** Use `AsyncMock` with structured Pydantic responses

```python
from unittest.mock import AsyncMock
from pydantic import BaseModel

class ConceptList(BaseModel):
    """Pydantic model for LLM concept extraction output."""
    concepts: List[str]
    is_multi_concept: bool
    confidence: float

@pytest.fixture
def mock_llm():
    """Mock LLM that returns ConceptList."""
    llm = AsyncMock()
    llm.ainvoke = AsyncMock(
        return_value=ConceptList(
            concepts=["React hooks", "state management"],
            is_multi_concept=True,
            confidence=0.9
        )
    )
    return llm
```

### Parallel Retrieval Testing

**Pattern:** Mock `asyncio.gather` timing

```python
import asyncio
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_parallel_execution():
    """Verify parallel retrieval is faster than sequential."""
    
    async def slow_search(query: str):
        await asyncio.sleep(0.1)  # 100ms delay
        return [("chunk", 0.9)]
    
    search_service = AsyncMock()
    search_service.semantic_search = AsyncMock(side_effect=slow_search)
    
    # Time parallel execution
    start = time.time()
    results = await asyncio.gather(
        search_service.semantic_search("concept1"),
        search_service.semantic_search("concept2")
    )
    duration = time.time() - start
    
    # Should take ~100ms (not 200ms)
    assert duration < 0.15  # Allow 50ms overhead
```

### Evaluation Fixtures

**File:** `backend/tests/smoke/retrieval/fixtures/multi_concept_queries.json`

```json
{
  "version": "1.0",
  "source": "Issue #601 - Failing multi-concept queries",
  "queries": [
    {
      "query": "React hooks and state management patterns",
      "expected_chunks": [
        "react_hooks_guide",
        "state_management_redux",
        "hooks_vs_classes"
      ],
      "difficulty": "medium",
      "min_recall@5": 0.67
    },
    {
      "query": "PostgreSQL vs MySQL performance comparison",
      "expected_chunks": [
        "postgres_performance",
        "mysql_performance",
        "db_comparison_benchmark"
      ],
      "difficulty": "easy",
      "min_recall@5": 0.80
    }
  ]
}
```

---

## Implementation Plan

### Phase 1: Unit Tests (Week 1, Days 1-3)

**Tasks:**
1. Implement `test_query_analyzer.py` (15 tests)
2. Implement `test_concept_extraction.py` (10 tests)
3. Implement `test_decomposition_cache.py` (5 tests)
4. Extend `test_rrf_fusion_extended.py` (5 tests)

**Deliverables:**
- 35 unit tests passing
- Coverage ≥95% for query analyzer and cache modules

**Acceptance Criteria:**
- All tests pass in <1s
- No mocked dependencies (pure functions)
- Clear, descriptive test names following pytest conventions

---

### Phase 2: Integration Tests (Week 1, Days 4-5)

**Tasks:**
1. Implement `test_decomposition_pipeline.py` (3 tests)
2. Implement `test_decomposition_fallback.py` (2 tests)
3. Set up LLM mocking infrastructure

**Deliverables:**
- 5 integration tests passing
- Mocked LLM returns structured Pydantic models

**Acceptance Criteria:**
- Tests run in <5s total
- LLM calls properly mocked (no real API calls)
- Parallel retrieval timing validated

---

### Phase 3: Evaluation Tests (Week 2, Days 1-2)

**Tasks:**
1. Create `multi_concept_queries.json` fixture (40 queries, use 10 for tests)
2. Implement `test_decomposition_eval.py` (3 test scenarios)
3. Run baseline comparison
4. Document before/after metrics

**Deliverables:**
- 3 evaluation tests
- Metrics report showing ≥15% Recall@5 improvement
- Regression check showing <2% degradation on single-concept queries

**Acceptance Criteria:**
- Tests run in <30s
- Clear pass/fail thresholds
- Metrics output in markdown format for documentation

---

### Phase 4: CI Integration (Week 2, Days 3-4)

**Tasks:**
1. Add tests to CI workflow
2. Create test coverage report
3. Document test strategy in `docs/testing/DECOMPOSITION_TESTS.md`

**Deliverables:**
- CI workflow updated
- Coverage report ≥90% overall
- Test strategy documentation

**Acceptance Criteria:**
- All tests pass in CI
- Coverage badge updated
- Documentation reviewed

---

## Acceptance Criteria

### Unit Tests
- [ ] 35+ unit tests implemented
- [ ] Coverage ≥95% for query analyzer, concept extraction, cache
- [ ] All tests pass in <1s
- [ ] No external dependencies (pure functions)

### Integration Tests
- [ ] 5 integration tests implemented
- [ ] LLM properly mocked with Pydantic schemas
- [ ] Parallel retrieval timing verified
- [ ] Fallback scenarios tested

### Evaluation Tests
- [ ] Recall@5 improvement ≥15% on multi-concept queries
- [ ] MRR improvement demonstrated
- [ ] Regression check: <2% degradation on single-concept queries
- [ ] Tests run in <30s

### Documentation
- [ ] Test strategy documented
- [ ] Fixture format documented
- [ ] Metrics interpretation guide created
- [ ] CI integration documented

### Quality Gates
- [ ] All tests pass in CI
- [ ] Coverage ≥90% overall
- [ ] No skipped tests
- [ ] Test execution <2 minutes total

---

## Appendices

### Appendix A: Test Naming Conventions

```python
# Pattern: test_{function}_{scenario}_{expected_outcome}
def test_detect_multi_concept_with_and_returns_true()
def test_llm_timeout_fallback_uses_heuristic()
def test_rrf_fusion_overlapping_chunks_ranked_highest()
```

### Appendix B: Pytest Markers

```python
@pytest.mark.unit         # Pure functions, no I/O
@pytest.mark.integration  # Multiple components, mocked external deps
@pytest.mark.smoke        # Evaluation tests, real system
@pytest.mark.slow         # Tests >5s (opt-in for local dev)
@pytest.mark.asyncio      # Async tests
```

### Appendix C: Coverage Targets

```
Module                           Coverage Target
---------------------------------------------
query_analyzer.py                95%
concept_extraction.py            95%
decomposition_cache.py           95%
decomposition_service.py         85%
hybrid_fusion.py                 90% (extended)
```

---

**End of Testing Strategy Document**
