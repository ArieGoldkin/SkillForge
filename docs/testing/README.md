# SkillForge Testing Documentation

This directory contains comprehensive testing strategies and architectures for the SkillForge project.

## Quick Navigation

### Retrieval & Search Testing

| Document | Purpose | Use When |
|----------|---------|----------|
| **[RETRIEVAL_SMOKE_TEST_STRATEGY.md](./RETRIEVAL_SMOKE_TEST_STRATEGY.md)** | Complete testing strategy for retrieval smoke tests | Implementing Issue #223, designing test cases, setting up CI/CD |
| **[RETRIEVAL_TEST_ARCHITECTURE.md](./RETRIEVAL_TEST_ARCHITECTURE.md)** | Visual architecture diagrams and flows | Understanding test execution flow, database isolation strategies |

---

## Retrieval Smoke Test Suite Overview

### What It Tests

- **Semantic Search** - Vector similarity using embeddings (cosine similarity)
- **Hybrid Search** - Combined semantic + BM25/full-text (RRF fusion)
- **Coarse-to-Fine Retrieval** - Two-stage hierarchical retrieval (sections → paragraphs)

### Key Features

- **Fast** - < 30 seconds total execution time
- **Deterministic** - Frozen embeddings, no external API calls
- **Isolated** - PostgreSQL test containers, never touches production
- **CI-Friendly** - GitHub Actions integration with comprehensive reporting

### Test Categories

| Category | Test Count | Purpose | Priority |
|----------|------------|---------|----------|
| Positive Tests | 13 | Verify queries find relevant chunks | HIGH |
| Negative Tests | 5 | Verify queries don't match irrelevant chunks | MEDIUM |
| Edge Cases | 7 | Handle degenerate inputs gracefully | HIGH |
| Performance Tests | 5 | Ensure latency meets thresholds | MEDIUM |
| **Total** | **32** | **Complete smoke test coverage** | - |

---

## Quick Start

### 1. Read the Strategy

Start with [RETRIEVAL_SMOKE_TEST_STRATEGY.md](./RETRIEVAL_SMOKE_TEST_STRATEGY.md) for:
- Test category definitions
- Fixture requirements
- Metrics & thresholds
- Implementation guide

### 2. Visualize the Architecture

Review [RETRIEVAL_TEST_ARCHITECTURE.md](./RETRIEVAL_TEST_ARCHITECTURE.md) for:
- Test flow diagrams
- Database isolation strategies
- Fixture data flow
- CI/CD integration

### 3. Implementation Checklist

- [ ] Create fixture corpus (`tests/fixtures/retrieval_corpus.json`)
- [ ] Generate frozen embeddings (`scripts/generate_test_embeddings.py`)
- [ ] Implement test files (`tests/smoke/*.py`)
- [ ] Create custom assertions (`tests/helpers/assertions.py`)
- [ ] Set up CI/CD workflow (`.github/workflows/retrieval-smoke-tests.yml`)

---

## Key Metrics & Thresholds

### Smoke Test Pass Criteria

| Metric | Threshold | Failure Action |
|--------|-----------|----------------|
| Hit Rate | ≥ 90% | Block PR |
| Top-5 Precision | ≥ 80% | Warning |
| Non-Match Precision | ≥ 95% | Block PR |
| Zero-Result Rate | ≤ 5% | Warning |
| Latency p95 | See performance table | Warning |

### Performance Targets (p95)

| Search Mode | Target | Baseline | Alert Threshold |
|-------------|--------|----------|-----------------|
| Semantic Search | < 100ms | 80ms | > 120ms (FAIL) |
| Hybrid Search | < 150ms | 130ms | > 180ms (FAIL) |
| Coarse-to-Fine | < 200ms | 170ms | > 240ms (FAIL) |

---

## Test Isolation Strategies

### Strategy Comparison

| Strategy | Speed | Realism | pgvector | Use Case |
|----------|-------|---------|----------|----------|
| **In-Memory SQLite** | ⚡⚡⚡ < 1s | ⚠️ Limited | ❌ | Unit tests (validation, snippets) |
| **PostgreSQL Container** | ⚡⚡ 5-10s | ✅ High | ✅ | Local integration tests |
| **Dedicated Test DB** | ⚡⚡⚡ < 3s | ✅ High | ✅ | CI pipeline |

**Recommendation:** Use SQLite for unit tests, Container for local integration, Dedicated DB for CI.

---

## File Structure

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
│   ├── test_semantic_search.py        # Semantic search smoke tests (10 tests)
│   ├── test_hybrid_search.py          # Hybrid search smoke tests (5 tests)
│   ├── test_coarse_to_fine.py         # Coarse-to-fine retrieval (5 tests)
│   └── test_edge_cases.py             # Edge cases (12 tests)
├── integration/
│   └── test_retrieval_integration.py  # Full-stack retrieval tests (API → DB)
└── helpers/
    ├── assertions.py                  # Custom assertions
    └── fixtures_loader.py             # Load JSON/YAML fixtures into DB
```

---

## Related Issues

- **#223** - Retrieval Smoke Tests (this strategy document)
- **#221** - Hierarchical Chunking (coarse-to-fine retrieval implementation)
- **#216** - Retrieval & Search API (API layer integration)
- **#219** - Eval Harness (full evaluation metrics: MAP, NDCG, MRR)
- **#218** - Telemetry & Metrics (performance monitoring)
- **#217** - Re-ranker (search result re-ranking)

---

## Additional Resources

### Internal Documentation

- [/docs/CURRENT_STATUS.md](/docs/CURRENT_STATUS.md) - Sprint 8 progress (Embeddings & Search)
- [/docs/issues/221-hierarchical-chunking/README.md](/docs/issues/221-hierarchical-chunking/README.md) - Chunking implementation details

### External References

- [pgvector Documentation](https://github.com/pgvector/pgvector) - PostgreSQL vector extension
- [testcontainers-python](https://testcontainers-python.readthedocs.io/) - Docker test containers
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/) - Async test support

---

## Maintenance

### When to Update

| Trigger | Action |
|---------|--------|
| New search mode added | Add new test file (e.g., `test_re_rank_search.py`) |
| Embedding model changed | Regenerate frozen embeddings + adjust thresholds |
| Schema migration | Update fixtures to match new `AnalysisChunk` schema |
| Performance regression | Adjust latency thresholds in expected results |

### Versioning

Fixtures use semantic versioning (`tests/fixtures/v1.0/`, `v1.1/`, etc.) with symlink to `current/`.

---

## Questions?

For implementation questions, see:
- [RETRIEVAL_SMOKE_TEST_STRATEGY.md](./RETRIEVAL_SMOKE_TEST_STRATEGY.md) - Complete strategy with examples
- [RETRIEVAL_TEST_ARCHITECTURE.md](./RETRIEVAL_TEST_ARCHITECTURE.md) - Visual diagrams and flows

For architecture questions, see:
- `/docs/ARCHITECTURE.md` - System architecture
- `/docs/issues/221-hierarchical-chunking/README.md` - Chunking design

---

**Last Updated:** December 10, 2025  
**Version:** 1.0  
**Sprint:** Sprint 8 - Embeddings & Search
