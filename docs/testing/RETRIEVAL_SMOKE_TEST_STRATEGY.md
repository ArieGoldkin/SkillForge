# Retrieval Smoke Test Suite - Testing Strategy

**Version:** 1.0  
**Date:** December 10, 2025  
**Purpose:** Comprehensive testing strategy for semantic, hybrid, and coarse-to-fine retrieval validation  
**Related Issues:** #223 (Retrieval Smoke Tests), #221 (Hierarchical Chunking), #216 (Retrieval & Search API)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Test Categories](#test-categories)
3. [Fixture Requirements](#fixture-requirements)
4. [Metrics & Thresholds](#metrics--thresholds)
5. [Test Isolation](#test-isolation)
6. [Implementation Guide](#implementation-guide)
7. [Test Data Specification](#test-data-specification)
8. [Maintenance & Evolution](#maintenance--evolution)

---

## Executive Summary

This testing strategy defines a **lightweight, offline-first smoke test suite** for validating retrieval quality across three search modes:

1. **Semantic Search** - Vector similarity using embeddings (cosine similarity)
2. **Hybrid Search** - Combined semantic + BM25/full-text (RRF fusion)
3. **Coarse-to-Fine Retrieval** - Two-stage hierarchical retrieval (sections → paragraphs)

### Goals

- **Fast feedback** - Run in CI/CD without external API calls (< 30 seconds)
- **Regression detection** - Catch quality degradation before production
- **Smoke test focus** - Validate core functionality, not exhaustive quality metrics
- **Deterministic** - Reproducible results with frozen embeddings

### Non-Goals

- Full evaluation harness (covered by Issue #219)
- A/B testing between embedding models
- Production load testing
- Comprehensive relevance tuning

---

## Test Categories

### 1. Positive Tests - Expected Matches

**Purpose:** Verify queries find relevant chunks with acceptable scores.

#### 1.1 Semantic Search - Conceptual Similarity

| Test Case | Query | Expected Match | Min Score | Rationale |
|-----------|-------|----------------|-----------|-----------|
| **Exact Concept Match** | "OAuth2 authentication" | Chunk containing "OAuth2 authentication implementation" | 0.85 | Direct semantic overlap |
| **Synonym Match** | "machine learning" | Chunk containing "ML models" or "artificial intelligence" | 0.70 | Semantic equivalence |
| **Paraphrase Match** | "how to deploy containers" | Chunk containing "Docker deployment guide" | 0.65 | Intent-based similarity |
| **Multi-Concept Query** | "React hooks useState" | Chunk discussing React hooks API with useState examples | 0.75 | Multiple related concepts |
| **Technical Term Match** | "binary quantization" | Chunk explaining quantization techniques | 0.80 | Domain-specific terminology |

#### 1.2 Hybrid Search - Keyword + Semantic

| Test Case | Query | Expected Match | Min Score | Rationale |
|-----------|-------|----------------|-----------|-----------|
| **Keyword Boost** | "FastAPI OAuth2" | Chunk with exact "FastAPI" + "OAuth2" tokens | 0.90 | Keyword match boosts RRF score |
| **Fuzzy + Semantic** | "postgress database" | Chunk about PostgreSQL (handles typo semantically) | 0.60 | Hybrid resilience to typos |
| **Long-Tail Query** | "debugging CORS errors in FastAPI" | Chunk with CORS troubleshooting steps | 0.70 | Multi-term keyword + semantic fusion |

#### 1.3 Coarse-to-Fine Retrieval - Hierarchical

| Test Case | Query | Expected Behavior | Validation |
|-----------|-------|-------------------|------------|
| **Section Constraint** | "LangGraph state management" | Coarse: Finds "LangGraph Architecture" section → Fine: Returns specific state management paragraphs | Fine results have path starting with coarse section |
| **Noise Reduction** | "supervisor pattern" | Coarse: Top 5 sections include "Agent Design Patterns" → Fine: Excludes unrelated paragraphs from other sections | Fine results limited to top 5 coarse paths |
| **Granularity Validation** | "implementation example" | Coarse: Returns section-level summaries → Fine: Returns paragraph-level chunks | Coarse chunks have `granularity="coarse"`, Fine have `granularity="fine"` |

---

### 2. Negative Tests - Expected Non-Matches

**Purpose:** Verify queries do NOT match irrelevant chunks.

| Test Case | Query | Should NOT Match | Max Score | Rationale |
|-----------|-------|------------------|-----------|-----------|
| **Unrelated Concept** | "OAuth2" | Chunk about "CSS styling best practices" | 0.40 | No semantic overlap |
| **Same Domain, Different Topic** | "React hooks" | Chunk about "Vue.js composition API" | 0.55 | Related framework but different API |
| **Common Words Only** | "how to use" | Generic chunks with only common stop words | 0.30 | Stop word filtering required |
| **Opposite Meaning** | "synchronous API calls" | Chunk about "async/await patterns" | 0.50 | Antonym should score lower |

---

### 3. Edge Cases

**Purpose:** Handle degenerate inputs gracefully without crashes.

| Test Case | Input | Expected Behavior | Pass Criteria |
|-----------|-------|-------------------|---------------|
| **Empty Query** | `""` | Raise `ValueError` with message "Search query cannot be empty" | Exception raised, no DB query executed |
| **Whitespace-Only Query** | `"   \n\t  "` | Raise `ValueError` | Same as empty query |
| **Very Long Query** | 1001 characters | Raise `ValueError` with message "Query exceeds maximum length" | Validation before embedding generation |
| **Special Characters** | `"@#$%^&*()"` | Return empty results gracefully | No crashes, empty list returned |
| **Non-ASCII Characters** | `"Привет мир"` (Russian) | Process normally if language supported, else empty results | No encoding errors |
| **SQL Injection Attempt** | `"' OR 1=1 --"` | Treated as literal search text, no SQL injection | Parameterized queries protect |
| **XSS Attempt** | `"<script>alert('xss')</script>"` | Escaped in snippets, no execution | Snippet HTML-escapes user input |

---

### 4. Performance Tests - Latency Thresholds

**Purpose:** Ensure queries meet acceptable latency targets.

| Metric | Target (p95) | Measurement | Pass Criteria |
|--------|--------------|-------------|---------------|
| **Semantic Search** | < 100ms | Time from embedding generation to result return | 95% of queries under 100ms |
| **Hybrid Search** | < 150ms | Time including both semantic + keyword search | 95% of queries under 150ms |
| **Coarse Search** | < 80ms | Coarse-only query (section-level) | 95% of queries under 80ms |
| **Fine Search (Constrained)** | < 120ms | Fine search within 5 coarse sections | 95% of queries under 120ms |
| **Full Coarse-to-Fine** | < 200ms | Coarse (80ms) + Fine (120ms) combined | 95% of queries under 200ms |

**Note:** These are **smoke test thresholds** for regression detection. Full load testing in Issue #218 (Telemetry).

---

## Fixture Requirements

### Minimum Test Corpus

**Total Documents:** 10-15 documents  
**Total Chunks:** ~100-150 chunks (coarse + fine)  
**Embedding Dimensions:** 1536 (text-embedding-3-small)

### Document Variety

| Document Type | Count | Purpose | Example Content |
|---------------|-------|---------|-----------------|
| **Technical Tutorial** | 3 | Multi-section with headings, code examples | "FastAPI Authentication Tutorial" (OAuth2, JWT, sessions) |
| **API Documentation** | 3 | Endpoint descriptions, parameters, responses | "REST API Reference" (GET /users, POST /login) |
| **Architecture Guide** | 2 | High-level system design, diagrams, patterns | "LangGraph Agent Patterns" (supervisor, worker nodes) |
| **Troubleshooting Guide** | 2 | Common errors, solutions, debugging tips | "CORS Error Fixes" (preflight, headers) |
| **Concept Explanation** | 2 | Abstract concepts without code | "Vector Embeddings Explained" (semantic search, cosine similarity) |
| **Mixed Content** | 3 | Combination of text, code, lists, tables | "React Hooks Best Practices" (text + code examples) |

### Query Variety

| Query Type | Count | Example | Purpose |
|------------|-------|---------|---------|
| **Single Keyword** | 5 | "OAuth2" | Test basic keyword matching |
| **Two-Word Phrase** | 5 | "React hooks" | Test phrase matching |
| **Technical Term** | 5 | "binary quantization" | Test domain-specific vocabulary |
| **Natural Language** | 5 | "how to deploy containers" | Test intent understanding |
| **Multi-Concept** | 5 | "FastAPI authentication JWT" | Test multi-term relevance |
| **Negative Examples** | 5 | Queries that should NOT match specific chunks | Test precision |

**Total Queries:** 30 test cases

### Expected Results Format

```python
ExpectedResult = {
    "query": str,
    "mode": "semantic" | "keyword" | "hybrid" | "coarse_to_fine",
    "expected_matches": [
        {
            "chunk_id": str,  # Or chunk content hash for lookup
            "min_score": float,  # Minimum acceptable similarity/rank score
            "max_rank": int,  # Must appear in top N results (e.g., top 5)
        }
    ],
    "expected_non_matches": [
        {
            "chunk_id": str,
            "max_score": float,  # Should score below this threshold
        }
    ],
    "metadata_assertions": {
        "coarse_to_fine": {
            "coarse_paths": ["Section A", "Section B"],  # Expected coarse sections
            "fine_count_min": int,  # Minimum fine results
            "fine_count_max": int,  # Maximum fine results
        }
    }
}
```

---

## Metrics & Thresholds

### Smoke Test Metrics (Issue #223)

**Focus:** Binary pass/fail for core functionality.

| Metric | Threshold | Measurement | Failure Action |
|--------|-----------|-------------|----------------|
| **Hit Rate** | ≥ 90% | % of queries finding at least 1 expected match | Block PR, investigate query/embedding drift |
| **Top-5 Precision** | ≥ 80% | % of expected matches in top 5 results | Warning, check ranking degradation |
| **Non-Match Precision** | ≥ 95% | % of expected non-matches scoring below threshold | Block PR, check false positives |
| **Zero-Result Rate** | ≤ 5% | % of valid queries returning 0 results | Warning, check index health |
| **Latency p95** | See Performance Tests table | 95th percentile query latency | Warning, check query plan/index |

### Full Evaluation Metrics (Issue #219)

**Not in smoke tests** - requires labeled dataset and A/B testing infrastructure:

- Mean Average Precision (MAP)
- Normalized Discounted Cumulative Gain (NDCG@k)
- Mean Reciprocal Rank (MRR)
- Recall@k (with ground truth labels)
- F1 score for relevance classification

### Handling Flaky Tests

#### Flakiness Sources

1. **Floating-point variance** - Cosine similarity scores may vary by ±0.01 due to numerical precision
2. **RRF score instability** - Small changes in keyword vs semantic ranking can shift hybrid scores
3. **Tie-breaking non-determinism** - Multiple chunks with identical scores may return in different order

#### Mitigation Strategies

| Strategy | Implementation | Example |
|----------|----------------|---------|
| **Score Tolerance** | Use `assert score >= threshold - 0.02` instead of exact match | `assert result.score >= 0.85 - 0.02` |
| **Rank Bands** | Check if result is in top N instead of exact rank | "Must be in top 5" not "Must be rank 3" |
| **Frozen Embeddings** | Pre-compute and store embeddings in fixtures | Load from `fixtures/embeddings.json` |
| **Multiple Runs** | Retry test 3 times if failure due to score variance | Use `@pytest.mark.flaky(reruns=3, reruns_delay=0)` |
| **Deterministic Tie-Breaking** | Sort by chunk_id when scores are equal | `ORDER BY score DESC, chunk_id ASC` |
| **Skip in CI** | Mark unstable tests with `@pytest.mark.skipif(CI, reason="flaky")` | Only for truly non-deterministic tests |

#### Flaky Test Detection

```python
# Mark tests that check exact floating-point scores
@pytest.mark.tolerance(0.02)  # Custom marker
def test_semantic_search_oauth2():
    results = await search_service.search("OAuth2", mode="semantic")
    # Passes if score is 0.85 ± 0.02
    assert_score_near(results[0].score, 0.85, tolerance=0.02)
```

---

## Test Isolation

### Principle: **Never Touch Production Data**

All smoke tests run against **isolated, ephemeral test databases** with fixtures.

### Strategy 1: In-Memory SQLite (Fastest, Limited)

**Use Case:** Unit tests for search service logic, snippet generation, score normalization.

**Limitations:**
- No `pgvector` extension (vector similarity requires mocking)
- No `tsvector` full-text search (keyword search requires mocking)
- No real RRF fusion (hybrid search requires mocking)

**Example:**

```python
@pytest.fixture
def in_memory_db():
    """SQLite in-memory database for fast unit tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine
```

**Suitable For:**
- Query validation (empty query, max length)
- Filter conversion logic
- Snippet generation and highlighting
- Error handling (embedding errors, DB errors)

---

### Strategy 2: PostgreSQL Test Container (Realistic, Slower)

**Use Case:** Integration tests for actual vector search, full-text search, RRF fusion.

**Requirements:**
- Docker running locally or in CI
- `pgvector` extension enabled
- Test database isolated from dev/prod

**Setup:**

```python
import pytest
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL container with pgvector for integration tests."""
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        # Wait for pgvector extension
        engine = create_async_engine(postgres.get_connection_url())
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        yield postgres
```

**Fixture Loading:**

```python
@pytest.fixture
async def populated_db(postgres_container):
    """Load test fixtures into PostgreSQL container."""
    db_url = postgres_container.get_connection_url()
    engine = create_async_engine(db_url)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Load fixtures from JSON/YAML
        fixtures = load_fixtures("tests/fixtures/retrieval_corpus.json")
        for chunk in fixtures["chunks"]:
            await conn.execute(
                insert(AnalysisChunk).values(**chunk)
            )
    
    yield engine
    
    # Cleanup happens automatically when container exits
```

**Suitable For:**
- Semantic search (actual vector similarity)
- Hybrid search (RRF fusion with real scores)
- Coarse-to-fine retrieval (hierarchical queries)
- Performance benchmarks (latency thresholds)

---

### Strategy 3: Dedicated Test Database (CI/CD)

**Use Case:** CI pipeline with persistent test DB for faster setup.

**Setup:**

```yaml
# .github/workflows/test-retrieval.yml
services:
  postgres:
    image: pgvector/pgvector:pg16
    env:
      POSTGRES_DB: skillforge_test
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_pass
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5

env:
  DATABASE_URL: postgresql+asyncpg://test_user:test_pass@localhost:5432/skillforge_test
```

**Fixture Management:**

```python
# tests/conftest.py
@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Create test database and load fixtures once per session."""
    if os.getenv("CI"):
        # CI has dedicated test DB
        db_url = os.getenv("DATABASE_URL")
    else:
        # Local uses Docker container
        db_url = await start_local_test_db()
    
    await create_tables(db_url)
    await load_fixtures(db_url, "tests/fixtures/retrieval_corpus.json")
    
    yield db_url
    
    # Cleanup
    await drop_tables(db_url)
```

**Cleanup Strategy:**

```python
@pytest.fixture(autouse=True)
async def cleanup_between_tests(db_session):
    """Truncate tables between tests to ensure isolation."""
    yield  # Run test
    
    # Cleanup after test
    async with db_session.begin():
        await db_session.execute(text("TRUNCATE analysis_chunks CASCADE"))
        await db_session.commit()
```

---

### Comparison: Test Isolation Strategies

| Strategy | Speed | Realism | pgvector | Setup Complexity | CI-Friendly |
|----------|-------|---------|----------|------------------|-------------|
| **In-Memory SQLite** | ⚡⚡⚡ Fast (< 1s) | ⚠️ Limited | ❌ No | ✅ Minimal | ✅ Yes |
| **PostgreSQL Container** | ⚡⚡ Medium (5-10s) | ✅ High | ✅ Yes | ⚙️ Moderate | ✅ Yes (Docker required) |
| **Dedicated Test DB** | ⚡⚡⚡ Fast (< 3s) | ✅ High | ✅ Yes | ⚙️ Moderate | ✅ Yes (service config) |

**Recommendation:** Use **Strategy 1 (SQLite) for unit tests**, **Strategy 2 (Container) for local integration tests**, **Strategy 3 (Dedicated DB) for CI pipeline**.

---

## Implementation Guide

### File Structure

```
backend/tests/
├── fixtures/
│   ├── retrieval_corpus.json          # Test documents + chunks + embeddings
│   ├── expected_results.yaml          # Query → Expected matches mapping
│   └── embeddings/
│       ├── oauth2_tutorial.npy        # Pre-computed embeddings (frozen)
│       └── fastapi_docs.npy
├── smoke/
│   ├── conftest.py                    # Shared fixtures for smoke tests
│   ├── test_semantic_search.py        # Semantic search smoke tests
│   ├── test_hybrid_search.py          # Hybrid search smoke tests
│   ├── test_coarse_to_fine.py         # Coarse-to-fine retrieval smoke tests
│   └── test_edge_cases.py             # Empty query, special chars, etc.
├── integration/
│   └── test_retrieval_integration.py  # Full-stack retrieval tests (API → DB)
└── helpers/
    ├── assertions.py                  # Custom assertions (assert_score_near, assert_in_top_k)
    └── fixtures_loader.py             # Load JSON/YAML fixtures into DB
```

---

### Test Fixture Example

**`tests/fixtures/retrieval_corpus.json`**

```json
{
  "documents": [
    {
      "doc_id": "oauth2_tutorial",
      "title": "FastAPI OAuth2 Authentication Tutorial",
      "url": "https://example.com/oauth2-tutorial",
      "content_type": "tutorial",
      "chunks": [
        {
          "chunk_id": "oauth2_tutorial_intro_coarse",
          "granularity": "coarse",
          "path": ["Introduction"],
          "section_title": "Introduction",
          "chunk_idx": 0,
          "chunk_total": 3,
          "content": "This tutorial covers OAuth2 authentication in FastAPI. OAuth2 is an industry-standard protocol for authorization.",
          "hash": "abc123...",
          "embedding_file": "embeddings/oauth2_tutorial_intro_coarse.npy"
        },
        {
          "chunk_id": "oauth2_tutorial_intro_fine_1",
          "granularity": "fine",
          "path": ["Introduction", "What is OAuth2"],
          "section_title": "What is OAuth2",
          "chunk_idx": 0,
          "chunk_total": 5,
          "content": "OAuth2 is a protocol that allows third-party applications to grant limited access to user accounts without exposing passwords.",
          "hash": "def456...",
          "embedding_file": "embeddings/oauth2_tutorial_intro_fine_1.npy"
        }
      ]
    }
  ],
  "queries": [
    {
      "query_id": "q_oauth2_exact",
      "query_text": "OAuth2 authentication",
      "mode": "semantic",
      "expected_matches": [
        {
          "chunk_id": "oauth2_tutorial_intro_coarse",
          "min_score": 0.85,
          "max_rank": 3
        }
      ],
      "expected_non_matches": [
        {
          "chunk_id": "css_styling_guide_intro",
          "max_score": 0.40
        }
      ]
    }
  ]
}
```

---

### Sample Test Implementation

**`tests/smoke/test_semantic_search.py`**

```python
"""Smoke tests for semantic search."""

import pytest
from app.services.search import SearchService
from app.schemas.search import SearchMode
from tests.helpers.assertions import assert_score_near, assert_in_top_k
from tests.helpers.fixtures_loader import load_expected_results


@pytest.fixture
def expected_results():
    """Load expected results from fixtures."""
    return load_expected_results("tests/fixtures/expected_results.yaml")


@pytest.mark.asyncio
async def test_semantic_search_exact_match(search_service, expected_results):
    """Test semantic search finds exact conceptual match with high score."""
    query_spec = expected_results["q_oauth2_exact"]
    
    results = await search_service.search(
        query=query_spec["query_text"],
        mode=SearchMode.SEMANTIC,
        top_k=10,
    )
    
    # Assertion 1: At least 1 result returned
    assert len(results) > 0, "Semantic search returned no results"
    
    # Assertion 2: Expected chunk is in top 3
    expected_chunk_id = query_spec["expected_matches"][0]["chunk_id"]
    assert_in_top_k(results, expected_chunk_id, k=3)
    
    # Assertion 3: Score is above threshold (with tolerance)
    result = next(r for r in results if r.chunk_id == expected_chunk_id)
    min_score = query_spec["expected_matches"][0]["min_score"]
    assert_score_near(result.score, min_score, tolerance=0.02, direction=">=")


@pytest.mark.asyncio
async def test_semantic_search_non_match(search_service, expected_results):
    """Test semantic search does NOT match unrelated content."""
    query_spec = expected_results["q_oauth2_exact"]
    
    results = await search_service.search(
        query=query_spec["query_text"],
        mode=SearchMode.SEMANTIC,
        top_k=10,
    )
    
    # Assertion: Unrelated chunk has low score
    non_match_id = query_spec["expected_non_matches"][0]["chunk_id"]
    max_allowed_score = query_spec["expected_non_matches"][0]["max_score"]
    
    non_match_result = next(
        (r for r in results if r.chunk_id == non_match_id),
        None
    )
    
    if non_match_result:
        assert non_match_result.score < max_allowed_score, (
            f"Non-match chunk scored too high: {non_match_result.score} "
            f"(max allowed: {max_allowed_score})"
        )
```

---

### Custom Assertion Helpers

**`tests/helpers/assertions.py`**

```python
"""Custom assertions for retrieval smoke tests."""

from typing import Literal


def assert_score_near(
    actual: float,
    expected: float,
    tolerance: float = 0.02,
    direction: Literal[">=", "<=", "=="] = "==",
):
    """Assert score is near expected value within tolerance.
    
    Args:
        actual: Actual score from search result.
        expected: Expected score from fixture.
        tolerance: Allowed variance (default ±0.02 for floating-point).
        direction: Comparison direction:
            - ">=" for minimum score threshold
            - "<=" for maximum score threshold
            - "==" for exact match (with tolerance)
    """
    if direction == ">=":
        assert actual >= expected - tolerance, (
            f"Score {actual:.3f} is below threshold {expected:.3f} "
            f"(tolerance: {tolerance:.3f})"
        )
    elif direction == "<=":
        assert actual <= expected + tolerance, (
            f"Score {actual:.3f} is above threshold {expected:.3f} "
            f"(tolerance: {tolerance:.3f})"
        )
    elif direction == "==":
        assert abs(actual - expected) <= tolerance, (
            f"Score {actual:.3f} differs from expected {expected:.3f} "
            f"by more than tolerance {tolerance:.3f}"
        )


def assert_in_top_k(results: list, chunk_id: str, k: int):
    """Assert chunk appears in top-k results.
    
    More resilient than exact rank checking.
    """
    top_k_ids = [r.chunk_id for r in results[:k]]
    assert chunk_id in top_k_ids, (
        f"Chunk {chunk_id} not found in top {k} results. "
        f"Top {k} were: {top_k_ids}"
    )


def assert_metadata_field(result, field: str, expected_value):
    """Assert metadata field matches expected value."""
    actual_value = getattr(result.metadata, field, None)
    assert actual_value == expected_value, (
        f"Metadata field '{field}' was {actual_value}, expected {expected_value}"
    )


def assert_snippet_contains(result, query_term: str):
    """Assert snippet contains highlighted query term."""
    assert f"<mark>{query_term}</mark>" in result.snippet, (
        f"Snippet does not contain highlighted term '<mark>{query_term}</mark>'. "
        f"Snippet: {result.snippet}"
    )
```

---

## Test Data Specification

### Corpus Size Guidelines

| Environment | Documents | Chunks | Total Size | Purpose |
|-------------|-----------|--------|------------|---------|
| **Smoke Tests (CI)** | 10-15 | 100-150 | ~500KB | Fast regression detection |
| **Integration Tests** | 50-100 | 500-1000 | ~5MB | Realistic load, RRF stability |
| **Full Evaluation** | 1000+ | 10000+ | ~50MB | Issue #219, A/B testing |

### Embedding Storage

**Frozen Embeddings** - Pre-compute embeddings and store as NumPy arrays to avoid API calls.

**File Format:**

```
tests/fixtures/embeddings/
├── oauth2_tutorial_intro_coarse.npy  # shape: (1536,)
├── oauth2_tutorial_intro_fine_1.npy
└── embeddings_manifest.json          # Maps chunk_id → embedding file
```

**Loading:**

```python
import numpy as np

def load_embedding(chunk_id: str) -> list[float]:
    """Load pre-computed embedding from fixture."""
    manifest = load_json("tests/fixtures/embeddings/embeddings_manifest.json")
    embedding_path = manifest[chunk_id]
    embedding = np.load(embedding_path)
    return embedding.tolist()
```

**Generating Fixtures (One-Time Setup):**

```bash
# Generate embeddings for test corpus (run once, commit results)
python scripts/generate_test_embeddings.py \
    --corpus tests/fixtures/retrieval_corpus.json \
    --output tests/fixtures/embeddings/ \
    --model text-embedding-3-small
```

---

### Query-Result Pairing Format

**`tests/fixtures/expected_results.yaml`**

```yaml
queries:
  - query_id: q_oauth2_exact
    query_text: "OAuth2 authentication"
    mode: semantic
    expected_matches:
      - chunk_id: oauth2_tutorial_intro_coarse
        min_score: 0.85
        max_rank: 3
        metadata_checks:
          section: "Introduction"
          granularity: "coarse"
    expected_non_matches:
      - chunk_id: css_styling_guide_intro
        max_score: 0.40
    performance:
      max_latency_ms: 100

  - query_id: q_hybrid_fastapi
    query_text: "FastAPI OAuth2"
    mode: hybrid
    expected_matches:
      - chunk_id: oauth2_tutorial_intro_coarse
        min_score: 0.90  # Higher due to keyword boost
        max_rank: 1
    expected_non_matches: []
    performance:
      max_latency_ms: 150

  - query_id: q_coarse_to_fine_state_management
    query_text: "LangGraph state management"
    mode: coarse_to_fine
    expected_coarse_sections:
      - "LangGraph Architecture"
      - "Agent Design Patterns"
    expected_fine_results:
      min_count: 3
      max_count: 10
      must_include_chunks:
        - langgraph_arch_state_fine_2
    fine_path_constraint:
      must_start_with: ["LangGraph Architecture"]
    performance:
      max_latency_ms: 200
```

---

## Maintenance & Evolution

### When to Update Smoke Tests

| Trigger | Action | Example |
|---------|--------|---------|
| **New Search Mode Added** | Add new test file | `test_re_rank_search.py` for Issue #217 |
| **Embedding Model Changed** | Regenerate frozen embeddings + adjust thresholds | Switching from text-embedding-3-small → ada-002 |
| **Schema Migration** | Update fixtures to match new `AnalysisChunk` schema | Adding `language` field |
| **Query Format Change** | Update expected results YAML | Supporting filters in queries |
| **Performance Regression** | Adjust latency thresholds | If p95 increases from 80ms → 100ms after optimization |

### Versioning Test Fixtures

**Use semantic versioning for fixtures:**

```
tests/fixtures/
├── v1.0/
│   ├── retrieval_corpus.json
│   └── expected_results.yaml
├── v1.1/  # Added language field
│   ├── retrieval_corpus.json
│   └── expected_results.yaml
└── current -> v1.1  # Symlink to latest
```

**Fixture Version in Conftest:**

```python
FIXTURE_VERSION = "v1.1"

@pytest.fixture
def retrieval_corpus():
    return load_json(f"tests/fixtures/{FIXTURE_VERSION}/retrieval_corpus.json")
```

### CI Integration

**GitHub Actions Workflow:**

```yaml
name: Retrieval Smoke Tests

on:
  pull_request:
    paths:
      - 'backend/app/services/search/**'
      - 'backend/app/db/repositories/chunk_repository.py'
      - 'backend/tests/smoke/**'

jobs:
  smoke-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_DB: skillforge_test
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s

    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install poetry
          poetry install --with dev
      
      - name: Run retrieval smoke tests
        env:
          DATABASE_URL: postgresql+asyncpg://test_user:test_pass@localhost:5432/skillforge_test
        run: |
          cd backend
          poetry run pytest tests/smoke/ \
            --verbose \
            --tb=short \
            --maxfail=3 \
            --timeout=300
      
      - name: Upload test report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: smoke-test-report
          path: backend/test-results/
```

---

## Appendix: Full Test Matrix

### Test Coverage Summary

| Category | Test Cases | File | Priority |
|----------|------------|------|----------|
| Semantic Search - Positive | 5 | `test_semantic_search.py` | HIGH |
| Semantic Search - Negative | 5 | `test_semantic_search.py` | MEDIUM |
| Hybrid Search - Positive | 3 | `test_hybrid_search.py` | HIGH |
| Hybrid Search - RRF Fusion | 2 | `test_hybrid_search.py` | MEDIUM |
| Coarse-to-Fine - Hierarchical | 3 | `test_coarse_to_fine.py` | HIGH |
| Coarse-to-Fine - Noise Reduction | 2 | `test_coarse_to_fine.py` | MEDIUM |
| Edge Cases - Invalid Input | 7 | `test_edge_cases.py` | HIGH |
| Performance - Latency | 5 | `test_performance.py` | MEDIUM |
| **Total** | **32** | **5 files** | - |

### Estimated Execution Time

- **Unit Tests (SQLite):** ~5 seconds (edge cases, validation)
- **Integration Tests (PostgreSQL):** ~20 seconds (semantic, hybrid, coarse-to-fine)
- **Performance Tests:** ~5 seconds (latency measurements)
- **Total Smoke Suite:** **~30 seconds**

---

## Summary

This testing strategy provides a **lightweight, deterministic, offline-first** smoke test suite for validating retrieval quality across semantic, hybrid, and coarse-to-fine search modes. Key design principles:

1. **Fast feedback** - < 30 seconds in CI/CD
2. **Deterministic** - Frozen embeddings, tolerance-based assertions
3. **Isolated** - No production data, ephemeral test databases
4. **Maintainable** - Versioned fixtures, clear test data specs
5. **Actionable** - Clear pass/fail criteria with regression detection

This strategy focuses on **smoke testing** (Issue #223) while leaving comprehensive evaluation metrics (MAP, NDCG, MRR) to the full evaluation harness (Issue #219).

---

**Next Steps:**

1. Create fixture corpus (`tests/fixtures/retrieval_corpus.json`)
2. Generate frozen embeddings (`scripts/generate_test_embeddings.py`)
3. Implement test files (`tests/smoke/*.py`)
4. Integrate into CI/CD pipeline (`.github/workflows/retrieval-smoke-tests.yml`)
5. Document expected results (`tests/fixtures/expected_results.yaml`)

**Related Issues:**
- #223 - Retrieval Smoke Tests (this strategy)
- #221 - Hierarchical Chunking (coarse-to-fine retrieval)
- #216 - Retrieval & Search API (API layer integration)
- #219 - Eval Harness (full evaluation metrics)
- #218 - Telemetry & Metrics (performance monitoring)
