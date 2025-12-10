# Issue #223 Quick Reference

## Commands

```bash
# Run all smoke tests
cd backend
poetry run pytest tests/smoke/retrieval/ -v

# Run specific search mode
poetry run pytest tests/smoke/retrieval/test_semantic_search.py -v
poetry run pytest tests/smoke/retrieval/test_hybrid_search.py -v

# Run with coverage
poetry run pytest tests/smoke/retrieval/ --cov=app/services/search

# Generate report
poetry run python scripts/smoke_test_retrieval.py --format markdown --output report.md

# CI mode (strict)
poetry run pytest tests/smoke/retrieval/ -v --tb=short -x
```

## Test Markers

```python
# In test files
@pytest.mark.smoke           # Smoke test marker
@pytest.mark.asyncio         # Async test
@pytest.mark.slow            # Slower tests (skip in quick runs)
```

```bash
# Run only smoke tests
poetry run pytest -m smoke

# Skip slow tests
poetry run pytest -m "smoke and not slow"
```

## Metrics Thresholds

| Metric | Pass | Fail |
|--------|------|------|
| Recall@5 | ≥ 0.8 | < 0.8 |
| MRR | ≥ 0.6 | < 0.6 |
| Pass Rate | 100% | < 100% |
| Max Latency | < 500ms | ≥ 500ms |

## File Locations

```
backend/
├── tests/smoke/retrieval/
│   ├── conftest.py              # Fixtures setup
│   ├── test_semantic_search.py  # Semantic tests
│   ├── test_keyword_search.py   # Keyword tests
│   ├── test_hybrid_search.py    # Hybrid tests
│   ├── test_coarse_to_fine.py   # Two-stage tests
│   ├── metrics.py               # Metrics computation
│   ├── reporter.py              # Report generation
│   └── fixtures/
│       ├── documents.json       # Test documents
│       └── queries.json         # Test queries
├── scripts/
│   └── smoke_test_retrieval.py  # CLI runner
└── docs/issues/223-*/
    ├── README.md                # Main documentation
    ├── ARCHITECTURE.md          # System design
    ├── FIXTURES.md              # Fixture design
    └── QUICK_REFERENCE.md       # This file
```

## Query Categories

| Category | Purpose | Expected Behavior |
|----------|---------|-------------------|
| `specific` | Exact content match | High recall, high score |
| `broad` | Multiple matches | Moderate recall, varied scores |
| `negative` | No relevant content | Empty or low-score results |
| `edge` | Boundary conditions | Graceful handling |

## Search Modes

| Mode | Mechanism | Best For |
|------|-----------|----------|
| `semantic` | Vector similarity (cosine) | Synonyms, paraphrases |
| `keyword` | Full-text (tsvector) | Exact terms, acronyms |
| `hybrid` | RRF fusion (k=60) | General queries |
| `coarse-to-fine` | Two-stage | Long documents |

## Common Issues

### Test Fails with "No chunks found"
- Check database is running with pgvector
- Verify fixtures were loaded in conftest
- Check `DATABASE_URL` environment variable

### Low Recall Scores
- Review expected_chunks in queries.json
- Check if document content matches query intent
- Verify embeddings were generated correctly

### Timeout Errors
- Increase timeout in conftest (default 2s)
- Check database connection pool settings
- Verify no conflicting database operations

## Environment Variables

```bash
# Required
DATABASE_URL=postgresql://user:pass@localhost:5432/skillforge_test
OPENAI_API_KEY=sk-...

# Optional
SMOKE_TEST_TIMEOUT=30           # Max test duration (seconds)
SMOKE_TEST_VERBOSE=true         # Detailed logging
EMBEDDING_CACHE_ENABLED=true    # Use cached embeddings
```

## Adding New Tests

### 1. Add Document Fixture
```json
// fixtures/documents.json
{
  "id": "new-doc",
  "title": "New Document Title",
  "content_type": "article",
  "bucket": "short",
  "sections": [
    {
      "id": "new-doc/section1",
      "title": "Section Title",
      "content": "Section content..."
    }
  ]
}
```

### 2. Add Query Fixture
```json
// fixtures/queries.json
{
  "id": "q-new-query",
  "query": "search query text",
  "modes": ["semantic", "hybrid"],
  "category": "specific",
  "expected_chunks": ["new-doc/section1"],
  "min_score": 0.7
}
```

### 3. Run Validation
```bash
poetry run python -c "from tests.smoke.retrieval.fixtures.loader import FixtureLoader; FixtureLoader().validate()"
```

## CI Integration

### GitHub Actions Trigger Paths
```yaml
paths:
  - 'backend/app/services/search/**'
  - 'backend/app/services/chunking/**'
  - 'backend/app/db/repositories/chunk_repository.py'
  - 'backend/tests/smoke/**'
```

### Required Secrets
- `OPENAI_API_KEY` - For embedding generation

### Exit Codes
- `0` - All tests passed
- `1` - Test failures
- `2` - Setup/configuration error

---

**Version:** 1.0 | **Updated:** December 10, 2025
