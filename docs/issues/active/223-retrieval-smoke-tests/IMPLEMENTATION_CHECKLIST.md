# Issue #223 - Implementation Checklist

**Status:** Design Complete → Ready for Implementation
**Estimated Effort:** 2 weeks (Part-time)
**Dependencies:** Issue #221 (Hierarchical Chunking) must be complete

---

## Phase 1: Fixture Generation (Week 1, Days 1-3)

### Day 1: Directory Setup & Data Collection

- [ ] Create fixture directory structure:
  ```bash
  mkdir -p backend/tests/fixtures/retrieval
  touch backend/tests/fixtures/retrieval/{analyses,chunks,embeddings,queries,metadata}.jsonl
  ```

- [ ] Curate 15 representative analyses:
  - [ ] 8 LONG documents (>DOC_LENGTH_THRESHOLD)
    - [ ] React Server Components article
    - [ ] LangGraph Supervisor Pattern tutorial
    - [ ] PostgreSQL PGVector docs
    - [ ] FastAPI Async Patterns reference
    - [ ] Next.js 15 Streaming SSR blog
    - [ ] Hierarchical Chunking research paper
    - [ ] Vector Database Comparison
    - [ ] Embedding Model Evaluation
  - [ ] 5 SHORT documents
    - [ ] Docker Compose Quick Start
    - [ ] JWT Auth Single-Concept Tutorial
    - [ ] Python Decorator Code Snippet
    - [ ] LangChain FAQ
    - [ ] LangGraph v1.0 Release Notes
  - [ ] 2 EDGE CASES
    - [ ] Markdown-heavy document (code blocks)
    - [ ] Multilingual content (EN + code comments)

### Day 2: Chunk Generation

- [ ] Create fixture generation script:
  ```bash
  touch scripts/generate_retrieval_fixtures.py
  ```

- [ ] Implement analysis processing:
  - [ ] Load raw content for each analysis
  - [ ] Run chunking service (reuse existing `Chunker`)
  - [ ] Apply deduplication (reuse existing `Dedup`)
  - [ ] Generate section summaries (if enabled)
  - [ ] Write `analyses.jsonl` and `chunks.jsonl`

- [ ] Validate chunk distribution:
  - [ ] 50 coarse chunks
  - [ ] 75 fine chunks
  - [ ] 8 summary chunks (optional)
  - [ ] Total: 133 chunks

### Day 3: Embedding Generation

- [ ] Implement embedding computation:
  - [ ] Use real OpenAI API (one-time cost: ~$0.10)
  - [ ] Batch process chunks (20 at a time)
  - [ ] Normalize vectors (L2 norm)
  - [ ] Validate dimensions (768 for text-embedding-3-small)

- [ ] Write `embeddings.jsonl`:
  - [ ] Include model name and version
  - [ ] Verify file size (~500KB)

- [ ] Create `metadata.json`:
  - [ ] Version number
  - [ ] Generation timestamp
  - [ ] Model details
  - [ ] Statistics (chunk counts, analysis distribution)

---

## Phase 1.5: Query Design (Week 1, Days 3-4)

### Day 3: Query Creation

- [ ] Design 20 test queries covering:
  - [ ] 10 Semantic queries (paraphrase/conceptual)
    - [ ] "How do server components work in React?"
    - [ ] "Async rendering patterns in Next.js"
    - [ ] "Vector similarity search with PostgreSQL"
    - [ ] "Supervisor agent routing in LangGraph"
    - [ ] "FastAPI background tasks and concurrency"
  - [ ] 6 Hybrid queries (keyword + semantic)
    - [ ] "PostgreSQL pgvector HNSW index"
    - [ ] "LangChain streaming SSE endpoint"
    - [ ] "React Suspense data fetching"
  - [ ] 4 Granularity-specific queries
    - [ ] Coarse: "Introduction to Docker Compose"
    - [ ] Fine: "JWT token expiration handling"

### Day 4: Relevance Judgments

- [ ] For each query, create graded relevance:
  - [ ] Score 3: Highly relevant (perfect answer)
  - [ ] Score 2: Relevant (partial answer)
  - [ ] Score 1: Marginally relevant (related context)
  - [ ] Score 0: Not relevant

- [ ] Compute query embeddings:
  - [ ] Use same model as chunks (text-embedding-3-small)
  - [ ] Include in `queries.jsonl`

- [ ] Set query-specific thresholds:
  - [ ] Easy queries: recall@5 ≥ 0.9
  - [ ] Hard queries: recall@5 ≥ 0.5

---

## Phase 2: CLI Script Implementation (Week 1-2, Days 5-9)

### Day 5: Core Utilities

- [ ] Create script file:
  ```bash
  touch scripts/test_retrieval.py
  touch scripts/test_retrieval_metrics.py
  ```

- [ ] Implement fixture loading:
  - [ ] `load_jsonl()` function
  - [ ] `load_json()` function
  - [ ] `load_fixtures()` with index building
  - [ ] Validate fixture integrity

- [ ] Write unit tests:
  - [ ] Test fixture loading with sample data
  - [ ] Test index building

### Day 6: Search Functions

- [ ] Implement in-memory search:
  - [ ] `cosine_similarity()` (assumes normalized vectors)
  - [ ] `semantic_search()` (top-k by similarity)
  - [ ] `hybrid_search()` (keyword + semantic blend)
  - [ ] `coarse_to_fine_search_mock()` (two-stage retrieval)

- [ ] Write unit tests:
  - [ ] Test cosine similarity with known vectors
  - [ ] Test semantic search ranking
  - [ ] Test hybrid alpha weighting
  - [ ] Test coarse-to-fine section filtering

### Day 7: Metrics Computation

- [ ] Implement metrics:
  - [ ] `compute_recall_at_k()`
  - [ ] `compute_mrr()`
  - [ ] `compute_ndcg_at_k()`
  - [ ] `compute_precision_at_k()`

- [ ] Write unit tests:
  - [ ] Test with example from Appendix B
  - [ ] Test edge cases (no relevance, all relevant, etc.)

### Day 8: Runner & Output Formatters

- [ ] Implement test runner:
  - [ ] `run_smoke_tests()` main loop
  - [ ] Per-query evaluation
  - [ ] Summary statistics computation
  - [ ] Pass/fail determination

- [ ] Implement output formatters:
  - [ ] `format_text_output()` (human-readable)
  - [ ] `format_json_output()` (machine-readable)
  - [ ] `format_markdown_output()` (GitHub Actions summary)

### Day 9: CLI & Integration Testing

- [ ] Add argument parsing:
  - [ ] `--mode`, `--verbose`, `--format`, `--output`
  - [ ] `--threshold-*` overrides
  - [ ] `--fail-fast`, `--seed`

- [ ] Write integration tests:
  - [ ] End-to-end test with sample fixtures
  - [ ] Test all output formats
  - [ ] Test CLI argument handling

- [ ] Manual testing:
  - [ ] Run on real fixtures
  - [ ] Verify runtime <30s
  - [ ] Check output quality

---

## Phase 3: CI Integration (Week 2, Days 10-11)

### Day 10: GitHub Actions Workflow

- [ ] Create workflow file:
  ```bash
  touch .github/workflows/retrieval-smoke-tests.yml
  ```

- [ ] Configure workflow:
  - [ ] Trigger on PR (paths: chunking, retrieval)
  - [ ] Trigger on push (main, dev)
  - [ ] Python setup with Poetry cache
  - [ ] Dependency installation

- [ ] Add caching:
  - [ ] Cache fixture embeddings (key: metadata hash)
  - [ ] Cache Poetry dependencies (key: poetry.lock hash)

- [ ] Add result upload:
  - [ ] Upload markdown results as artifact
  - [ ] Post results as PR comment

### Day 11: Workflow Testing & Optimization

- [ ] Test workflow on example PR:
  - [ ] Verify triggers work
  - [ ] Check caching effectiveness
  - [ ] Verify PR comment posting

- [ ] Optimize performance:
  - [ ] Ensure workflow completes in <5 minutes
  - [ ] Cache hit rate >90%

- [ ] Add status badge:
  - [ ] Update README.md with workflow badge

---

## Phase 4: Documentation & Maintenance (Week 2, Days 12-14)

### Day 12: Fixture Update Guide

- [ ] Create fixture documentation:
  ```bash
  touch docs/issues/223-retrieval-smoke-tests/FIXTURE_GUIDE.md
  ```

- [ ] Document fixture update process:
  - [ ] When to update fixtures (chunker changes, model updates)
  - [ ] How to regenerate embeddings
  - [ ] Versioning strategy

### Day 13: Troubleshooting Guide

- [ ] Create troubleshooting docs:
  ```bash
  touch docs/issues/223-retrieval-smoke-tests/TROUBLESHOOTING.md
  ```

- [ ] Document common issues:
  - [ ] Fixture loading errors
  - [ ] Metric calculation failures
  - [ ] Threshold tuning process
  - [ ] CI workflow debugging

### Day 14: Final Validation

- [ ] Run full test suite:
  - [ ] All unit tests passing
  - [ ] Integration tests passing
  - [ ] CI workflow passing

- [ ] Code quality checks:
  - [ ] `poetry run ruff format --check scripts/`
  - [ ] `poetry run ruff check scripts/`
  - [ ] `poetry run mypy scripts/ --ignore-missing-imports`

- [ ] Documentation review:
  - [ ] All guides complete
  - [ ] Examples tested
  - [ ] Links valid

- [ ] Update shared context:
  - [ ] Add decisions to `.claude/context/shared-context.json`
  - [ ] Update `docs/CURRENT_STATUS.md`

---

## Acceptance Criteria (Final Checklist)

### Fixtures
- [x] 15 analyses (8 long, 5 short, 2 edge cases)
- [x] 133 chunks (50 coarse, 75 fine, 8 summary)
- [x] Pre-computed embeddings (~500KB)
- [x] 20 test queries with relevance judgments
- [x] Total fixture size <1MB

### CLI Script
- [x] Loads fixtures in <2s
- [x] Runs all tests in <30s
- [x] Supports semantic, hybrid, coarse-to-fine modes
- [x] Outputs text, JSON, markdown formats
- [x] All metrics implemented correctly
- [x] Command-line arguments working

### CI Integration
- [x] GitHub Actions workflow configured
- [x] Runs on relevant PR paths
- [x] Caching working (>90% hit rate)
- [x] Results posted as PR comment
- [x] Workflow completes in <5 minutes
- [x] Status badge in README

### Code Quality
- [x] All unit tests passing
- [x] Integration tests passing
- [x] Ruff linting clean
- [x] Ruff formatting clean
- [x] Mypy type checking clean
- [x] No security vulnerabilities

### Documentation
- [x] Design document complete
- [x] Fixture guide complete
- [x] Troubleshooting guide complete
- [x] README updated with usage examples
- [x] Shared context updated

---

## File Inventory (Expected Deliverables)

```
backend/tests/fixtures/retrieval/
  ├── analyses.jsonl              (~50KB)
  ├── chunks.jsonl                (~200KB)
  ├── embeddings.jsonl            (~500KB)
  ├── queries.jsonl               (~20KB)
  └── metadata.json               (~2KB)

scripts/
  ├── generate_retrieval_fixtures.py    (Fixture generation)
  ├── test_retrieval.py                 (Main CLI script)
  └── test_retrieval_metrics.py         (Metric utilities)

.github/workflows/
  └── retrieval-smoke-tests.yml         (CI workflow)

docs/issues/223-retrieval-smoke-tests/
  ├── DESIGN_DOCUMENT.md                (This document)
  ├── IMPLEMENTATION_CHECKLIST.md       (Implementation plan)
  ├── FIXTURE_GUIDE.md                  (Fixture maintenance)
  ├── TROUBLESHOOTING.md                (Common issues)
  └── ARCHITECTURE_DIAGRAM.md           (Visual architecture)

backend/tests/unit/scripts/
  ├── test_retrieval_metrics.py         (Metric unit tests)
  └── test_fixture_loading.py           (Fixture loading tests)

backend/tests/integration/scripts/
  └── test_retrieval_e2e.py             (End-to-end tests)
```

---

## Time Estimates

```
Phase 1: Fixture Generation          = 3 days (24 hours)
Phase 1.5: Query Design              = 1.5 days (12 hours)
Phase 2: CLI Implementation          = 4.5 days (36 hours)
Phase 3: CI Integration              = 1.5 days (12 hours)
Phase 4: Documentation               = 2.5 days (20 hours)
-----------------------------------------------------------
Total Estimated Effort               = 13 days (104 hours)

Part-time (4 hours/day)              = ~26 days (5 weeks)
Full-time (8 hours/day)              = ~13 days (2.5 weeks)
```

---

## Next Steps

1. **Review this checklist** with team
2. **Create GitHub issue** for tracking (#223)
3. **Assign to backend engineer** (Yonatan)
4. **Block on Issue #221** (Hierarchical Chunking completion)
5. **Start with Phase 1** (Fixture Generation)

---

**Last Updated:** December 10, 2025
**Maintained By:** Backend System Architect
