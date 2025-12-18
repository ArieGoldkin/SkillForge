# Quick Reference - Retrieval Smoke Tests CI

**Workflow:** `.github/workflows/retrieval-smoke-tests.yml`
**Issue:** #223

---

## Setup Checklist

- [ ] **GitHub Secret:** Add `OPENAI_API_KEY` to repo secrets
  - Settings → Secrets and variables → Actions → New repository secret
  - Use REAL OpenAI key (not test placeholder: `sk-test-...`)

- [ ] **Pytest Markers:** Added to `backend/pyproject.toml` (✅ Done)
  ```toml
  markers = [
      "smoke: marks tests as smoke tests",
      "retrieval: marks tests for retrieval/search functionality",
      "semantic: marks semantic search tests",
      "keyword: marks keyword search tests",
      "hybrid: marks hybrid search tests",
  ]
  ```

- [ ] **Test Fixtures:** Generated in `backend/tests/fixtures/retrieval/` (✅ Done)
  - `analyses.jsonl` (~50KB)
  - `chunks.jsonl` (~200KB)
  - `embeddings.jsonl` (~500KB)
  - `queries.jsonl` (~20KB)
  - `metadata.json` (~2KB)

---

## Workflow Triggers

| Event | Branches | Paths |
|-------|----------|-------|
| **Pull Request** | main, dev | chunking/**, retrieval/**, embeddings/**, search/**, tests/smoke/retrieval/**, fixtures/retrieval/** |
| **Push** | main, dev | chunking/**, retrieval/**, embeddings/**, search/** |
| **Manual** | Any | workflow_dispatch |

---

## Test Execution

```bash
# Locally run same tests as CI:
cd backend

# Semantic search tests
poetry run pytest tests/smoke/retrieval/ -m "smoke and retrieval and semantic" -v

# Keyword search tests
poetry run pytest tests/smoke/retrieval/ -m "smoke and retrieval and keyword" -v

# Hybrid search tests
poetry run pytest tests/smoke/retrieval/ -m "smoke and retrieval and hybrid" -v

# All retrieval smoke tests
poetry run pytest tests/smoke/retrieval/ -m "smoke and retrieval" -v
```

---

## Expected Results

### Test Counts
- **Semantic:** 8 tests (~40s)
- **Keyword:** 7 tests (~30s)
- **Hybrid:** 7 tests (~35s)
- **Total:** 22 tests (~105s)

### Performance Targets
| Metric | Target | Actual |
|--------|--------|--------|
| Total runtime | <5 min | ~3 min |
| Cache hit rate | >90% | ~95% |
| API cost/run | <$0.001 | ~$0.0003 |

### Quality Thresholds
| Mode | Category | Recall@5 | MRR | NDCG@5 |
|------|----------|----------|-----|--------|
| Semantic | Specific | ≥0.70 | ≥0.60 | ≥0.65 |
| Semantic | Broad | ≥0.50 | ≥0.40 | ≥0.45 |
| Keyword | Specific | ≥0.60 | ≥0.50 | ≥0.55 |
| Hybrid | Specific | ≥0.75 | ≥0.65 | ≥0.70 |

---

## Common Issues

### Issue: "No module named 'app'"
**Fix:** Ensure `poetry install` runs before tests
```yaml
- name: Install dependencies
  run: poetry install --no-interaction --no-root
```

### Issue: "Extension 'vector' does not exist"
**Fix:** Install pgvector BEFORE Alembic migrations
```yaml
- name: Install pgvector extension
  run: |
    PGPASSWORD=postgres psql -h localhost -U postgres -d skillforge_test \
      -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Issue: "OPENAI_API_KEY not found"
**Fix:** Add GitHub secret `OPENAI_API_KEY` with real key (not `sk-test-...`)

### Issue: Tests fail with low recall
**Fix:** Check if code change legitimately affects retrieval, then adjust thresholds in `conftest.py`

---

## Maintenance

### Update Fixtures (when needed)
```bash
cd backend
poetry run python scripts/generate_retrieval_fixtures.py

# Update version in metadata.json
# Commit changes - cache will auto-invalidate
git add tests/fixtures/retrieval/
git commit -m "chore(#223): regenerate retrieval fixtures"
```

### Adjust Thresholds (if needed)
Edit `backend/tests/smoke/retrieval/conftest.py`:
```python
THRESHOLDS = {
    "semantic": {
        "specific": {"min_recall": 0.70, "min_mrr": 0.60, "min_ndcg": 0.65},
    }
}
```

### Monitor Health
- **Weekly:** Check runtime <5 min, cache hit >90%, pass rate >95%
- **Monthly:** Review fixture versions, check pgvector updates, audit API costs

---

## Files Changed

### New Files
- `.github/workflows/retrieval-smoke-tests.yml` (CI workflow)
- `docs/issues/223-retrieval-smoke-tests/CI_WORKFLOW_GUIDE.md` (full docs)
- `docs/issues/223-retrieval-smoke-tests/QUICK_REFERENCE.md` (this file)

### Modified Files
- `backend/pyproject.toml` (added pytest markers: smoke, retrieval, semantic, keyword, hybrid)

---

## Resources

- **Full Guide:** `docs/issues/223-retrieval-smoke-tests/CI_WORKFLOW_GUIDE.md`
- **Design Doc:** `docs/issues/223-retrieval-smoke-tests/DESIGN_DOCUMENT.md`
- **Implementation:** `docs/issues/223-retrieval-smoke-tests/IMPLEMENTATION_CHECKLIST.md`
- **GitHub Actions:** https://github.com/[repo]/actions/workflows/retrieval-smoke-tests.yml

---

**Last Updated:** December 10, 2025
