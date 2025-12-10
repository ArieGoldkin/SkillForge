# Issue #223: Retrieval Smoke Tests

**Status:** In Progress
**Branch:** `feature/223-retrieval-smoke-tests`
**Sprint:** Sprint 8 - Embeddings & Search
**Priority:** MEDIUM
**Estimated Points:** 3

---

## Summary

Add a lightweight offline retrieval smoke test suite to validate chunking, semantic search, hybrid search, and coarse-to-fine retrieval. The suite catches regressions quickly and provides confidence that the retrieval pipeline works correctly.

## Goals

1. **Validate Core Retrieval** - Ensure semantic, keyword, and hybrid search return expected results
2. **Catch Regressions** - Fail fast when changes break retrieval quality
3. **CI Integration** - Run automatically on every PR to prevent broken merges
4. **Minimal Overhead** - Fast execution (<30s) with small fixture set

## Architecture Overview

```
                    SMOKE TEST ARCHITECTURE
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐      │
│   │   FIXTURES  │────▶│   RUNNER    │────▶│   REPORT    │      │
│   │  (JSON/YAML)│     │   (pytest)  │     │  (JSON/MD)  │      │
│   └─────────────┘     └─────────────┘     └─────────────┘      │
│         │                   │                   │               │
│         ▼                   ▼                   ▼               │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐      │
│   │  Documents  │     │  SearchSvc  │     │  Metrics    │      │
│   │  + Queries  │     │  + ChunkRep │     │  Recall@k   │      │
│   │  + Expected │     │  + EmbedSvc │     │  MRR, P/F   │      │
│   └─────────────┘     └─────────────┘     └─────────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Dependencies

This smoke test suite validates work from completed Sprint 8 issues:

| Issue | Feature | Status |
|-------|---------|--------|
| #215 | Embedding Pipeline | ✅ Complete |
| #216 | Retrieval & Search API | ✅ Complete |
| #217 | Re-ranker | ✅ Complete |
| #221 | Hierarchical Chunking | ✅ Complete |

## File Structure

```
backend/
├── tests/
│   └── smoke/
│       └── retrieval/
│           ├── __init__.py
│           ├── conftest.py              # Smoke test fixtures
│           ├── test_semantic_search.py  # Semantic search tests
│           ├── test_keyword_search.py   # Keyword search tests
│           ├── test_hybrid_search.py    # Hybrid search tests
│           ├── test_coarse_to_fine.py   # Two-stage retrieval tests
│           └── fixtures/
│               ├── documents.json       # Test documents
│               ├── queries.json         # Test queries + expected results
│               └── embeddings_cache.json # Pre-computed embeddings (optional)
├── scripts/
│   └── smoke_test_retrieval.py          # CLI runner script
└── pyproject.toml                       # Add smoke test markers
```

## Fixture Design

### Document Fixtures (`fixtures/documents.json`)

```json
{
  "documents": [
    {
      "id": "doc-fastapi-auth",
      "title": "FastAPI Authentication Guide",
      "content_type": "article",
      "bucket": "short",
      "sections": [
        {
          "title": "Introduction",
          "content": "FastAPI provides built-in OAuth2 support..."
        },
        {
          "title": "OAuth2 with Password Flow",
          "content": "To implement OAuth2 password flow, first create..."
        }
      ]
    },
    {
      "id": "doc-langchain-agents",
      "title": "LangChain Agent Tutorial",
      "content_type": "tutorial",
      "bucket": "long",
      "sections": [...]
    }
  ]
}
```

### Query Fixtures (`fixtures/queries.json`)

```json
{
  "queries": [
    {
      "id": "q-oauth2-basic",
      "query": "How to implement OAuth2 authentication?",
      "modes": ["semantic", "hybrid"],
      "expected_chunks": ["doc-fastapi-auth/oauth2-password-flow"],
      "min_score": 0.7,
      "category": "specific"
    },
    {
      "id": "q-negative-unrelated",
      "query": "kubernetes deployment strategies",
      "modes": ["semantic", "keyword", "hybrid"],
      "expected_chunks": [],
      "max_results": 0,
      "category": "negative"
    }
  ]
}
```

### Document Buckets

| Bucket | Token Range | Purpose |
|--------|-------------|---------|
| `short` | < 2000 tokens | Simple documents, single topic |
| `long` | > 4000 tokens | Complex documents, multiple sections |

## Test Categories

### 1. Positive Tests (SHOULD find)
- Specific queries matching document content
- Broad queries matching multiple chunks
- Multi-concept queries requiring semantic understanding

### 2. Negative Tests (should NOT find)
- Unrelated queries (different domain)
- Queries for non-existent content

### 3. Edge Cases
- Empty query handling (should error)
- Special characters in queries
- Very long queries (near 1000 char limit)

### 4. Mode-Specific Tests
- **Semantic**: Synonyms and paraphrases should match
- **Keyword**: Exact term matching
- **Hybrid**: Best of both worlds
- **Coarse-to-Fine**: Section → paragraph retrieval

## Metrics

### Primary Metrics

| Metric | Formula | Threshold |
|--------|---------|-----------|
| **Recall@5** | (relevant in top 5) / (total relevant) | ≥ 0.8 |
| **MRR** | Mean Reciprocal Rank | ≥ 0.6 |
| **Pass Rate** | (passed queries) / (total queries) | 100% |

### Computation

```python
def compute_recall_at_k(results: list, expected: list, k: int = 5) -> float:
    """Compute Recall@k metric."""
    top_k_ids = [r.chunk_id for r in results[:k]]
    relevant_found = len(set(top_k_ids) & set(expected))
    return relevant_found / len(expected) if expected else 1.0

def compute_mrr(results: list, expected: list) -> float:
    """Compute Mean Reciprocal Rank."""
    for i, result in enumerate(results, start=1):
        if result.chunk_id in expected:
            return 1.0 / i
    return 0.0
```

## CLI Script Design

### Usage

```bash
# Run all smoke tests
poetry run python scripts/smoke_test_retrieval.py

# Run specific mode
poetry run python scripts/smoke_test_retrieval.py --mode semantic

# Generate markdown report
poetry run python scripts/smoke_test_retrieval.py --format markdown --output report.md

# CI mode (strict, exit code based)
poetry run python scripts/smoke_test_retrieval.py --ci
```

### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--mode` | all | Search mode: semantic, keyword, hybrid, coarse-to-fine, all |
| `--format` | json | Output format: json, markdown, table |
| `--output` | stdout | Output file path |
| `--ci` | false | CI mode: strict thresholds, non-zero exit on failure |
| `--verbose` | false | Show detailed per-query results |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All tests passed |
| 1 | One or more tests failed |
| 2 | Configuration/setup error |

## CI Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/smoke-tests.yml
name: Retrieval Smoke Tests

on:
  pull_request:
    paths:
      - 'backend/app/services/search/**'
      - 'backend/app/services/chunking/**'
      - 'backend/app/db/repositories/chunk_repository.py'
      - 'backend/tests/smoke/**'

jobs:
  smoke-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: skillforge_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

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
          poetry install

      - name: Run smoke tests
        env:
          DATABASE_URL: postgresql://postgres:test@localhost:5432/skillforge_test
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          cd backend
          poetry run pytest tests/smoke/retrieval/ -v --tb=short

      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: smoke-test-results
          path: backend/smoke_test_report.json
```

### Caching Strategy

For faster CI runs, pre-compute embeddings for fixture documents:

```python
# scripts/generate_fixture_embeddings.py
async def cache_embeddings():
    """Pre-compute embeddings for all fixture documents."""
    documents = load_fixtures("fixtures/documents.json")
    embedding_service = EmbeddingService()

    cache = {}
    for doc in documents:
        for section in doc["sections"]:
            text = section["content"]
            embedding = await embedding_service.generate_embedding(text)
            cache[f"{doc['id']}/{section['title']}"] = embedding

    save_cache("fixtures/embeddings_cache.json", cache)
```

## Implementation Plan

### Phase 1: Foundation (Day 1)
- [ ] Create directory structure
- [ ] Write fixture loader utilities
- [ ] Implement basic conftest.py with database setup

### Phase 2: Fixtures (Day 1-2)
- [ ] Create 5-8 test documents covering different content types
- [ ] Write 15-20 test queries with expected results
- [ ] Add document bucket classification (short/long)

### Phase 3: Test Implementation (Day 2-3)
- [ ] `test_semantic_search.py` - 5-8 test cases
- [ ] `test_keyword_search.py` - 5-8 test cases
- [ ] `test_hybrid_search.py` - 5-8 test cases
- [ ] `test_coarse_to_fine.py` - 3-5 test cases

### Phase 4: CLI & CI (Day 3)
- [ ] Implement `smoke_test_retrieval.py` CLI script
- [ ] Add GitHub Actions workflow
- [ ] Add pytest markers for smoke tests

### Phase 5: Documentation (Day 3)
- [ ] Update this README with final implementation details
- [ ] Add usage examples to main project docs

## Acceptance Criteria

- [ ] Smoke tests run locally with `pytest tests/smoke/retrieval/`
- [ ] Smoke tests run in CI on relevant PR changes
- [ ] Tests cover semantic, keyword, hybrid, and coarse-to-fine modes
- [ ] Fixtures include both short and long documents
- [ ] Pass/fail based on Recall@5 ≥ 0.8 threshold
- [ ] CLI script generates JSON and Markdown reports
- [ ] Documentation complete with usage examples

## References

- [SearchService Implementation](../../../backend/app/services/search/search_service.py)
- [ChunkRepository](../../../backend/app/db/repositories/chunk_repository.py)
- [Search Schemas](../../../backend/app/schemas/search.py)
- [Existing Search Tests](../../../backend/tests/unit/services/search/test_search_service.py)

---

**Created:** December 10, 2025
**Author:** Claude Code
**Last Updated:** December 10, 2025
