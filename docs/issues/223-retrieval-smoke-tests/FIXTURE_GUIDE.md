# Retrieval Smoke Test Fixture Guide

This guide explains how to create, modify, and extend test fixtures for the retrieval smoke test suite.

## Overview

Fixtures are JSON files that define test documents and queries for deterministic, reproducible smoke tests. They enable:

- **Offline testing** without live API calls (when using cached embeddings)
- **Consistent test data** across all test runs
- **Easy extension** for new test scenarios

## File Locations

```
backend/tests/smoke/retrieval/fixtures/
├── documents.json       # Test document corpus
├── queries.json         # Test queries with expected results
└── embeddings_cache.json # Pre-computed embeddings (optional, for CI)
```

---

## Document Fixtures (`documents.json`)

### Structure

```json
{
  "version": "1.0",
  "generated": "2025-12-10",
  "documents": [
    {
      "id": "unique-doc-id",
      "title": "Document Title",
      "content_type": "article|tutorial|api_docs",
      "bucket": "short|long",
      "language": "en",
      "tags": ["tag1", "tag2"],
      "sections": [
        {
          "id": "doc-id/section-slug",
          "title": "Section Title",
          "content": "Section content...",
          "granularity": "coarse|fine",
          "parent_section": "doc-id/parent-section"  // Only for fine sections
        }
      ]
    }
  ]
}
```

### Field Descriptions

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique document identifier (kebab-case) |
| `title` | Yes | Human-readable document title |
| `content_type` | Yes | Document type: `article`, `tutorial`, `api_docs` |
| `bucket` | Yes | Size bucket: `short` (<2000 tokens) or `long` (>4000 tokens) |
| `language` | Yes | ISO language code (e.g., `en`) |
| `tags` | Yes | Keywords for filtering and categorization |
| `sections` | Yes | Array of content sections |

### Section Fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique section ID (format: `doc-id/section-slug`) |
| `title` | Yes | Section heading |
| `content` | Yes | Section text content |
| `granularity` | Yes | `coarse` (section-level) or `fine` (paragraph-level) |
| `parent_section` | For fine | Reference to parent coarse section ID |

### Granularity Levels

**Coarse (Sections)**
- Top-level content divisions
- ~200-500 words each
- Standalone, self-contained topics

**Fine (Paragraphs)**
- Subsections within coarse sections
- ~50-150 words each
- Must reference `parent_section`

Example hierarchy:
```
langchain-agents/tools (coarse)
├── langchain-agents/tools/decorator-usage (fine)
└── langchain-agents/tools/best-practices (fine)
```

---

## Query Fixtures (`queries.json`)

### Structure

```json
{
  "version": "1.0",
  "generated": "2025-12-10",
  "queries": [
    {
      "id": "q-unique-id",
      "query": "Search query text",
      "modes": ["semantic", "keyword", "hybrid"],
      "category": "specific|broad|negative|edge|coarse-to-fine",
      "expected_chunks": ["doc-id/section-id"],
      "min_score": 0.6,
      "max_score": null,
      "description": "What this query tests"
    }
  ]
}
```

### Field Descriptions

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique query identifier |
| `query` | Yes | The search query text |
| `modes` | Yes | Supported search modes |
| `category` | Yes | Test category (see below) |
| `expected_chunks` | Yes | Section IDs that should be returned |
| `min_score` | No | Minimum acceptable similarity score |
| `max_score` | No | Maximum acceptable score (for negative tests) |
| `description` | Yes | Human-readable test description |

### Query Categories

| Category | Purpose | Score Threshold |
|----------|---------|-----------------|
| `specific` | Targeted queries that should find exact matches | High (0.6-0.8) |
| `broad` | General queries matching multiple sections | Medium (0.4-0.6) |
| `negative` | Queries that should NOT match (different domain) | Low (<0.4) |
| `edge` | Edge cases (short queries, special chars) | Varies |
| `coarse-to-fine` | Hierarchical retrieval tests | Medium (0.4-0.6) |

### Coarse-to-Fine Query Fields

For `category: "coarse-to-fine"`, additional fields are available:

| Field | Description |
|-------|-------------|
| `granularity` | `coarse`, `fine`, or `both` |
| `expected_fine_chunks` | Fine sections to find after coarse stage |
| `expected_coarse_parent` | Parent section for fine queries |

Example:
```json
{
  "id": "q-c2f-tools-coarse",
  "query": "How to create custom tools for LangChain agents",
  "modes": ["semantic", "hybrid"],
  "category": "coarse-to-fine",
  "expected_chunks": ["langchain-agents/tools"],
  "expected_fine_chunks": ["langchain-agents/tools/decorator-usage"],
  "granularity": "coarse",
  "min_score": 0.6
}
```

---

## Adding New Test Scenarios

### 1. Add a New Document

```json
{
  "id": "new-topic",
  "title": "New Topic Guide",
  "content_type": "article",
  "bucket": "short",
  "language": "en",
  "tags": ["new", "topic"],
  "sections": [
    {
      "id": "new-topic/intro",
      "title": "Introduction",
      "content": "Overview of the new topic...",
      "granularity": "coarse"
    }
  ]
}
```

### 2. Add Queries for the Document

```json
{
  "id": "q-new-topic-specific",
  "query": "How does new topic work?",
  "modes": ["semantic", "hybrid"],
  "category": "specific",
  "expected_chunks": ["new-topic/intro"],
  "min_score": 0.6,
  "description": "Should find new topic introduction"
}
```

### 3. Validate Fixtures

Run the validation command:

```bash
cd backend
poetry run python -c "
from tests.smoke.retrieval.fixtures import FixtureLoader
loader = FixtureLoader()
errors = loader.validate()
print('Errors:', errors if errors else 'None - fixtures valid!')
"
```

---

## Threshold Configuration

Thresholds are defined in `conftest.py`:

```python
THRESHOLDS = {
    "semantic": {
        "specific": {"min_recall": 0.70, "min_mrr": 0.60, "min_ndcg": 0.65},
        "broad": {"min_recall": 0.50, "min_mrr": 0.40, "min_ndcg": 0.45},
        "negative": {"max_score": 0.40},
    },
    "keyword": {
        "specific": {"min_recall": 0.60, "min_mrr": 0.50, "min_ndcg": 0.55},
        "edge": {"min_recall": 0.50, "min_mrr": 0.40, "min_ndcg": 0.45},
    },
    "hybrid": {
        "specific": {"min_recall": 0.75, "min_mrr": 0.65, "min_ndcg": 0.70},
        "broad": {"min_recall": 0.55, "min_mrr": 0.45, "min_ndcg": 0.50},
    },
}
```

### Metric Definitions

| Metric | Description | Formula |
|--------|-------------|---------|
| **Recall@k** | Fraction of relevant items in top-k | `relevant_in_k / total_relevant` |
| **MRR** | Mean Reciprocal Rank | `1 / rank_of_first_relevant` |
| **NDCG@k** | Normalized Discounted Cumulative Gain | `DCG / IDCG` |
| **Precision@k** | Fraction of top-k that are relevant | `relevant_in_k / k` |

---

## Best Practices

### Document Content

1. **Be realistic** - Use content similar to actual SkillForge documents
2. **Cover diversity** - Include different content types and topics
3. **Proper sizing** - Short docs <2000 tokens, long docs >4000 tokens
4. **Clear sections** - Each section should be self-contained

### Query Design

1. **Specific queries** - Should match 1-2 specific sections
2. **Broad queries** - Should match 3-5 related sections
3. **Negative queries** - Use completely unrelated domains
4. **Edge cases** - Test short queries, special characters, typos

### Hierarchy Testing

1. **Parent-child relationships** - Fine sections must reference parent
2. **Path navigation** - Use `path` field for traversal
3. **Two-stage queries** - Test coarse → fine drill-down

---

## Running Smoke Tests

```bash
# All smoke tests
cd backend
poetry run pytest tests/smoke/retrieval/ -v

# By search mode
poetry run pytest tests/smoke/retrieval/ -m "smoke and semantic" -v
poetry run pytest tests/smoke/retrieval/ -m "smoke and keyword" -v
poetry run pytest tests/smoke/retrieval/ -m "smoke and hybrid" -v
poetry run pytest tests/smoke/retrieval/ -m "smoke and coarse_to_fine" -v

# Quick validation (no output)
poetry run pytest tests/smoke/retrieval/ -q
```

---

## Troubleshooting

### "Query references unknown section"

The query's `expected_chunks` contains a section ID not in `documents.json`.

**Fix:** Add the missing section or correct the section ID.

### "Duplicate ID" error

Two documents or queries share the same ID.

**Fix:** Ensure all IDs are unique across documents and queries.

### "Invalid bucket" error

Document bucket is not `short` or `long`.

**Fix:** Set bucket to one of the valid values.

### Low recall scores

Queries not finding expected documents.

**Fix:**
1. Check that content contains relevant keywords
2. Verify section IDs in expected_chunks
3. Lower min_score threshold for broad queries

---

**Last Updated:** December 10, 2025
